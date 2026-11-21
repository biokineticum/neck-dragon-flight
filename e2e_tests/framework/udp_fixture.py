"""Opaque-box synthetic UDP telemetry injection and capture harness.

Provides:
- TelemetryPacket & CapturedPacket data models.
- MockUdpBroadcaster: High-precision threaded sender simulating flight maneuvers and faults.
- UdpTelemetryCapture: Threaded non-blocking receiver validating schema, frequency, and jitter.
- FallbackInputSimulator: JSON event trace generator for headless fallback input testing.
"""

import dataclasses
import json
import math
import queue
import random
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .assertions import (
    assert_angle_in_bounds,
    assert_packet_rate,
    assert_packet_schema,
)
from .config import (
    MAX_DATAGRAM_BYTES,
    MAX_PACKET_RATE_HZ,
    MIN_PACKET_RATE_HZ,
    SOCKET_BUFFER_SIZE,
    TARGET_FPS,
    UDP_HOST,
    UDP_PORT,
)


def _is_finite_number(val: Any) -> bool:
    """Returns True if val is a non-bool finite numeric float or int."""
    return isinstance(val, (int, float)) and not isinstance(val, bool) and not math.isnan(val) and not math.isinf(val)


@dataclasses.dataclass
class TelemetryPacket:
    """Represents a validated telemetry datagram matching Interface Contract 1."""

    pitch: float = 0.0  # [-35.0, 35.0] degrees
    yaw: float = 0.0    # [-45.0, 45.0] degrees
    roll: float = 0.0   # [-35.0, 35.0] degrees
    calibrated: bool = True
    tracking: bool = True
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch": round(float(self.pitch), 4),
            "yaw": round(float(self.yaw), 4),
            "roll": round(float(self.roll), 4),
            "calibrated": bool(self.calibrated),
            "tracking": bool(self.tracking),
            "timestamp": time.time() if self.timestamp <= 0.0 else float(self.timestamp),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryPacket":
        return cls(
            pitch=float(data.get("pitch", 0.0)),
            yaw=float(data.get("yaw", 0.0)),
            roll=float(data.get("roll", 0.0)),
            calibrated=bool(data.get("calibrated", False)),
            tracking=bool(data.get("tracking", False)),
            timestamp=float(data.get("timestamp", 0.0)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TelemetryPacket":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> "TelemetryPacket":
        return cls.from_json(raw_bytes.decode("utf-8"))


@dataclasses.dataclass
class CapturedPacket:
    """Record of a datagram received by UdpTelemetryCapture."""

    raw_bytes: bytes
    received_at: float
    payload: Optional[Dict[str, Any]] = None
    parse_error: Optional[str] = None
    pitch: Optional[float] = None
    yaw: Optional[float] = None
    roll: Optional[float] = None
    calibrated: Optional[bool] = None
    tracking: Optional[bool] = None
    timestamp: Optional[float] = None
    inter_packet_dt: Optional[float] = None


class MockUdpBroadcaster:
    """Threaded UDP telemetry injector simulating head tracking at 30-60 Hz.

    Runs on a daemon background thread. Provides atomic state manipulation,
    parameterized trajectory sequences, and adversarial fault injection.
    """

    def __init__(
        self,
        host: str = UDP_HOST,
        port: int = UDP_PORT,
        target_fps: float = TARGET_FPS,
    ):
        self.host = host
        self.port = port
        self.target_fps = target_fps
        self._target_dt = 1.0 / target_fps if target_fps > 0 else (1.0 / 60.0)

        self._socket: Optional[socket.socket] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Telemetry State
        self._current_packet = TelemetryPacket()
        self._sequence_fn: Optional[Callable[[float], TelemetryPacket]] = None
        self._sequence_start_time: float = 0.0

        # Fault Injection Flags
        self._dropout_probability: float = 0.0
        self._silence_until: float = 0.0
        self._disconnected: bool = False
        self._jitter_sigma_deg: float = 0.0
        self._timing_jitter_ms: float = 0.0
        self._out_of_bounds_override: Optional[Tuple[float, float, float]] = None
        self._raw_override_bytes: Optional[bytes] = None

        self._packets_sent_count: int = 0

    @property
    def packets_sent(self) -> int:
        return self._packets_sent_count

    def start(self) -> "MockUdpBroadcaster":
        """Initializes the UDP socket and launches the transmission thread."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self
            if self._socket is None:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                except Exception:
                    pass
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="MockUdpBroadcaster")
            self._thread.start()
        return self

    def stop(self, timeout: float = 1.0) -> None:
        """Signals the background sender loop to terminate and joins thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

    def __enter__(self) -> "MockUdpBroadcaster":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    # --------------------------------------------------------------------------
    # Telemetry Control Methods
    # --------------------------------------------------------------------------
    def set_telemetry(
        self,
        pitch: float = 0.0,
        yaw: float = 0.0,
        roll: float = 0.0,
        calibrated: bool = True,
        tracking: bool = True,
    ) -> None:
        """Sets the current static telemetry broadcast state."""
        with self._lock:
            self._sequence_fn = None
            self._out_of_bounds_override = None
            self._raw_override_bytes = None
            self._current_packet = TelemetryPacket(
                pitch=pitch,
                yaw=yaw,
                roll=roll,
                calibrated=calibrated,
                tracking=tracking,
                timestamp=0.0,
            )

    def set_neutral(self) -> None:
        """Sets level flight neutral telemetry."""
        self.set_telemetry(pitch=0.0, yaw=0.0, roll=0.0, calibrated=True, tracking=True)

    def set_dive(self, pitch: float = -30.0) -> None:
        """Sets sustained dive pitch."""
        self.set_telemetry(pitch=pitch, yaw=0.0, roll=0.0, calibrated=True, tracking=True)

    def set_climb(self, pitch: float = 30.0) -> None:
        """Sets sustained climb pitch."""
        self.set_telemetry(pitch=pitch, yaw=0.0, roll=0.0, calibrated=True, tracking=True)

    def set_sharp_yaw(self, yaw: float = 40.0) -> None:
        """Sets sharp left (negative) or right (positive) turn."""
        self.set_telemetry(pitch=0.0, yaw=yaw, roll=0.0, calibrated=True, tracking=True)

    def set_banking(self, yaw: float = 25.0, roll: float = 25.0) -> None:
        """Sets coordinated turn with yaw and roll."""
        self.set_telemetry(pitch=0.0, yaw=yaw, roll=roll, calibrated=True, tracking=True)

    def set_tracking(self, tracking: bool) -> None:
        """Updates the tracking detection flag."""
        with self._lock:
            self._current_packet.tracking = tracking

    # --------------------------------------------------------------------------
    # Scripted Flight Trajectories
    # --------------------------------------------------------------------------
    def play_sequence(self, sequence_fn: Callable[[float], TelemetryPacket]) -> None:
        """Sets a dynamic trajectory generator function f(elapsed_seconds) -> TelemetryPacket."""
        with self._lock:
            self._sequence_fn = sequence_fn
            self._sequence_start_time = time.perf_counter()

    def play_roll_slalom(self, amplitude: float = 30.0, frequency_hz: float = 1.0) -> None:
        """Generates alternating sinusoidal banking: roll = A * sin(2*pi*f*t)."""
        def _slalom(elapsed: float) -> TelemetryPacket:
            current_roll = amplitude * math.sin(2.0 * math.pi * frequency_hz * elapsed)
            current_yaw = current_roll * 0.8
            return TelemetryPacket(
                pitch=0.0,
                yaw=current_yaw,
                roll=current_roll,
                calibrated=True,
                tracking=True,
            )
        self.play_sequence(_slalom)

    def play_dive_and_recover(
        self,
        dive_pitch: float = -30.0,
        ramp_time: float = 0.5,
        hold_time: float = 2.0,
        recover_time: float = 0.5,
    ) -> None:
        """Generates dive transition, sustained dive, and recovery to level flight."""
        def _dive(elapsed: float) -> TelemetryPacket:
            if elapsed < ramp_time:
                frac = elapsed / ramp_time
                p = dive_pitch * frac
            elif elapsed < ramp_time + hold_time:
                p = dive_pitch
            elif elapsed < ramp_time + hold_time + recover_time:
                sub_elapsed = elapsed - (ramp_time + hold_time)
                frac = 1.0 - (sub_elapsed / recover_time)
                p = dive_pitch * frac
            else:
                p = 0.0
            return TelemetryPacket(pitch=p, yaw=0.0, roll=0.0, calibrated=True, tracking=True)
        self.play_sequence(_dive)

    # --------------------------------------------------------------------------
    # Adversarial & Fault Injection
    # --------------------------------------------------------------------------
    def set_packet_dropout(self, probability: float) -> None:
        """Simulates random packet loss with probability in [0.0, 1.0]."""
        with self._lock:
            self._dropout_probability = max(0.0, min(1.0, probability))

    def pause_for(self, duration_sec: float) -> None:
        """Completely silences transmission for duration_sec (to trigger >0.5s timeout)."""
        with self._lock:
            self._silence_until = max(self._silence_until, time.perf_counter() + duration_sec)

    def disconnect(self) -> None:
        """Silences transmission indefinitely without closing socket."""
        with self._lock:
            self._disconnected = True

    def reconnect(self) -> None:
        """Resumes active transmission."""
        with self._lock:
            self._disconnected = False
            self._silence_until = 0.0

    def set_out_of_bounds(self, pitch: float = 999.0, yaw: float = -999.0, roll: float = 500.0) -> None:
        """Forces out-of-range angles to test engine clamping logic."""
        with self._lock:
            self._out_of_bounds_override = (pitch, yaw, roll)

    def set_jitter(self, angle_sigma_deg: float = 2.0, timing_jitter_ms: float = 5.0) -> None:
        """Injects Gaussian noise on angles and timing jitter on transmission."""
        with self._lock:
            self._jitter_sigma_deg = angle_sigma_deg
            self._timing_jitter_ms = timing_jitter_ms

    def send_malformed(self, raw_bytes: bytes) -> None:
        """Directly sends a one-off malformed datagram (e.g. invalid JSON)."""
        with self._lock:
            if self._socket:
                try:
                    self._socket.sendto(raw_bytes, (self.host, self.port))
                    self._packets_sent_count += 1
                except Exception:
                    pass

    def send_burst(self, count: int = 100, interval_sec: float = 0.0) -> int:
        """Transmits count packets immediately to test buffer draining capacity."""
        sent = 0
        with self._lock:
            sock = self._socket
        if not sock:
            return 0

        pkt = TelemetryPacket(pitch=0.0, yaw=0.0, roll=0.0, calibrated=True, tracking=True)
        for _ in range(count):
            pkt.timestamp = time.time()
            try:
                sock.sendto(pkt.to_bytes(), (self.host, self.port))
                sent += 1
                self._packets_sent_count += 1
            except Exception:
                break
            if interval_sec > 0:
                time.sleep(interval_sec)
        return sent

    # --------------------------------------------------------------------------
    # Internal Sender Loop
    # --------------------------------------------------------------------------
    def _run_loop(self) -> None:
        t_next = time.perf_counter()

        while not self._stop_event.is_set():
            t_now = time.perf_counter()

            # High-precision cadence sleep
            dt_sleep = t_next - t_now
            if dt_sleep > 0.001:
                time.sleep(dt_sleep)
                t_now = time.perf_counter()

            # Schedule next packet
            t_next += self._target_dt
            # Catch up if behind by > 5 intervals
            if t_now - t_next > 5 * self._target_dt:
                t_next = t_now + self._target_dt

            with self._lock:
                if self._disconnected:
                    continue
                if t_now < self._silence_until:
                    continue
                if self._dropout_probability > 0.0 and random.random() < self._dropout_probability:
                    continue
                if not self._socket:
                    continue

                # Determine packet to send
                if self._sequence_fn:
                    elapsed = t_now - self._sequence_start_time
                    pkt = self._sequence_fn(elapsed)
                else:
                    pkt = dataclasses.replace(self._current_packet)

                # Apply overrides / jitter
                if self._out_of_bounds_override:
                    pkt.pitch, pkt.yaw, pkt.roll = self._out_of_bounds_override

                if self._jitter_sigma_deg > 0.0:
                    pkt.pitch += random.gauss(0.0, self._jitter_sigma_deg)
                    pkt.yaw += random.gauss(0.0, self._jitter_sigma_deg)
                    pkt.roll += random.gauss(0.0, self._jitter_sigma_deg)

                pkt.timestamp = time.time()
                data = pkt.to_bytes()

            # Send over socket
            try:
                self._socket.sendto(data, (self.host, self.port))
                self._packets_sent_count += 1
            except Exception:
                pass


class UdpTelemetryCapture:
    """Threaded UDP receiver capturing and validating telemetry from Python or Godot.

    Binds to 127.0.0.1:42425 with SO_REUSEADDR and 1MB buffer. Collects packets into
    a thread-safe queue and provides statistical and schema validation methods.
    """

    def __init__(
        self,
        host: str = UDP_HOST,
        port: int = UDP_PORT,
        buffer_size: int = 10000,
    ):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size

        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._all_packets: List[CapturedPacket] = []
        self._lock = threading.Lock()
        self._last_received_time: float = 0.0

    @property
    def total_received(self) -> int:
        with self._lock:
            return len(self._all_packets)

    def start(self) -> "UdpTelemetryCapture":
        """Binds the UDP receiver socket and launches background consumer thread."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
            except Exception:
                pass
            sock.bind((self.host, self.port))
            sock.settimeout(0.2)
            self._socket = sock

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="UdpTelemetryCapture")
            self._thread.start()
        return self

    def stop(self, timeout: float = 1.0) -> None:
        """Signals background receiver loop to stop and closes socket."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

    def __enter__(self) -> "UdpTelemetryCapture":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def clear(self) -> None:
        """Clears both the queue and the historical packet store."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._all_packets.clear()
            self._last_received_time = 0.0

    def wait_for_packet(self, timeout: float = 2.0) -> CapturedPacket:
        """Waits for and returns the next received packet; raises TimeoutError on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f"No UDP packet received on {self.host}:{self.port} within {timeout}s")

    def collect_packets(self, count: int, timeout: float = 3.0) -> List[CapturedPacket]:
        """Collects exactly count packets within timeout; raises TimeoutError if insufficient."""
        collected: List[CapturedPacket] = []
        deadline = time.time() + timeout
        while len(collected) < count and time.time() < deadline:
            remaining = max(0.01, deadline - time.time())
            try:
                pkt = self._queue.get(timeout=remaining)
                collected.append(pkt)
            except queue.Empty:
                break

        if len(collected) < count:
            raise TimeoutError(
                f"Collected {len(collected)}/{count} packets within {timeout}s timeout"
            )
        return collected

    def get_latest(self) -> Optional[CapturedPacket]:
        """Drains any buffered packets and returns the most recent one received."""
        latest = None
        while True:
            try:
                latest = self._queue.get_nowait()
            except queue.Empty:
                break
        if latest is None:
            with self._lock:
                if self._all_packets:
                    latest = self._all_packets[-1]
        return latest

    def get_all_collected(self) -> List[CapturedPacket]:
        """Returns a snapshot copy of all received packets."""
        with self._lock:
            return list(self._all_packets)

    # --------------------------------------------------------------------------
    # Statistical & Assertion Helpers
    # --------------------------------------------------------------------------
    def compute_fps(self, packets: Optional[List[CapturedPacket]] = None) -> float:
        """Computes transmission frequency (FPS) across packet arrival timestamps."""
        target_list = packets if packets is not None else self.get_all_collected()
        if len(target_list) < 2:
            return 0.0

        ts_list = [p.received_at for p in target_list]
        duration = ts_list[-1] - ts_list[0]
        if duration <= 0:
            return 0.0
        return (len(ts_list) - 1) / duration

    def compute_jitter(self, packets: Optional[List[CapturedPacket]] = None) -> Dict[str, float]:
        """Calculates standard deviation of pitch, yaw, and roll angles in degrees.

        Filters valid packets using finite numeric checks so non-numeric or malformed
        packets in buffer history do not raise TypeError.
        """
        target_list = packets if packets is not None else self.get_all_collected()
        valid = [
            p for p in target_list
            if _is_finite_number(p.pitch) and _is_finite_number(p.yaw) and _is_finite_number(p.roll)
        ]
        if len(valid) < 3:
            return {"pitch_std": 0.0, "yaw_std": 0.0, "roll_std": 0.0}

        def _std(vals: List[float]) -> float:
            if len(vals) < 2:
                return 0.0
            mean = sum(vals) / len(vals)
            var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
            return math.sqrt(var)

        return {
            "pitch_std": _std([float(p.pitch) for p in valid if _is_finite_number(p.pitch)]),
            "yaw_std": _std([float(p.yaw) for p in valid if _is_finite_number(p.yaw)]),
            "roll_std": _std([float(p.roll) for p in valid if _is_finite_number(p.roll)]),
        }

    def assert_schema(self, packet: CapturedPacket) -> None:
        """Validates that a captured datagram conforms strictly to Interface Contract 1."""
        if packet.parse_error:
            raise AssertionError(f"Packet has parse error: {packet.parse_error}")
        if not packet.payload:
            raise AssertionError("Packet has empty payload")
        assert_packet_schema(packet.payload)

    def assert_fps(
        self,
        expected_min: float = MIN_PACKET_RATE_HZ,
        expected_max: float = MAX_PACKET_RATE_HZ,
        packets: Optional[List[CapturedPacket]] = None,
    ) -> float:
        """Asserts that measured packet arrival rate falls within acceptable bounds."""
        target_list = packets if packets is not None else self.get_all_collected()
        if len(target_list) < 5:
            raise AssertionError(f"Insufficient packets to compute FPS ({len(target_list)})")
        ts = [p.received_at for p in target_list]
        return assert_packet_rate(ts, min_hz=expected_min, max_hz=expected_max)

    def assert_jitter_suppression(
        self,
        max_std_deg: float = 0.5,
        packets: Optional[List[CapturedPacket]] = None,
    ) -> None:
        """Asserts that stationary telemetry jitter standard deviation is <= max_std_deg."""
        jitters = self.compute_jitter(packets)
        for axis, std in jitters.items():
            if math.isnan(std) or math.isinf(std):
                raise AssertionError(f"Axis {axis} jitter std is not finite: {std}")
            if std > max_std_deg:
                raise AssertionError(
                    f"Axis {axis} jitter std {std:.4f}° exceeds allowed maximum {max_std_deg:.4f}°"
                )

    # --------------------------------------------------------------------------
    # Internal Receiver Loop
    # --------------------------------------------------------------------------
    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                data, _ = self._socket.recvfrom(MAX_DATAGRAM_BYTES)
            except (socket.timeout, OSError):
                continue

            now = time.time()
            inter_dt = (now - self._last_received_time) if self._last_received_time > 0 else None
            self._last_received_time = now

            captured = CapturedPacket(
                raw_bytes=data,
                received_at=now,
                inter_packet_dt=inter_dt,
            )

            # Try parsing JSON
            try:
                text = data.decode("utf-8")
                payload = json.loads(text)
                captured.payload = payload
                captured.pitch = payload.get("pitch")
                captured.yaw = payload.get("yaw")
                captured.roll = payload.get("roll")
                captured.calibrated = payload.get("calibrated")
                captured.tracking = payload.get("tracking")
                captured.timestamp = payload.get("timestamp")
            except Exception as e:
                captured.parse_error = str(e)

            with self._lock:
                self._all_packets.append(captured)

            try:
                self._queue.put_nowait(captured)
            except queue.Full:
                pass


class FallbackInputSimulator:
    """Generates timed input action traces for headless fallback input testing.

    Exports JSON trace files for Godot headless runner input replay.
    """

    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def add_action_press(self, time_sec: float, action: str, strength: float = 1.0) -> "FallbackInputSimulator":
        """Adds a simulated keyboard action press at time_sec."""
        self._events.append({
            "time_sec": round(float(time_sec), 3),
            "type": "action_press",
            "action": action,
            "strength": float(strength),
        })
        return self

    def add_action_release(self, time_sec: float, action: str) -> "FallbackInputSimulator":
        """Adds a simulated keyboard action release at time_sec."""
        self._events.append({
            "time_sec": round(float(time_sec), 3),
            "type": "action_release",
            "action": action,
        })
        return self

    def add_mouse_motion(self, time_sec: float, relative_x: float, relative_y: float) -> "FallbackInputSimulator":
        """Adds simulated mouse motion event at time_sec."""
        self._events.append({
            "time_sec": round(float(time_sec), 3),
            "type": "mouse_motion",
            "relative_x": float(relative_x),
            "relative_y": float(relative_y),
        })
        return self

    def get_events(self) -> List[Dict[str, Any]]:
        """Returns sorted list of events by time_sec."""
        return sorted(self._events, key=lambda e: e["time_sec"])

    def export_trace(self, filepath: Union[str, Path]) -> Path:
        """Serializes the trace to a JSON file."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.get_events(), f, indent=2)
        return p

    @classmethod
    def generate_keyboard_override_trace(cls) -> "FallbackInputSimulator":
        """Pre-built trace: Turn left via 'A' key at t=1.0s, release at t=2.5s."""
        sim = cls()
        sim.add_action_press(1.0, "steer_left", 1.0)
        sim.add_action_release(2.5, "steer_left")
        return sim

    @classmethod
    def generate_slalom_keyboard_trace(cls) -> "FallbackInputSimulator":
        """Pre-built trace: Alternating keyboard turns left and right."""
        sim = cls()
        sim.add_action_press(0.5, "steer_left", 1.0)
        sim.add_action_release(1.5, "steer_left")
        sim.add_action_press(1.8, "steer_right", 1.0)
        sim.add_action_release(2.8, "steer_right")
        sim.add_action_press(3.1, "steer_left", 1.0)
        sim.add_action_release(4.1, "steer_left")
        return sim

    @classmethod
    def generate_emergency_evasion_trace(cls) -> "FallbackInputSimulator":
        """Pre-built trace: Emergency climb up ('W') and hard bank left ('A')."""
        sim = cls()
        sim.add_action_press(0.2, "steer_up", 1.0)
        sim.add_action_press(0.2, "steer_left", 1.0)
        sim.add_action_release(2.0, "steer_left")
        sim.add_action_release(2.5, "steer_up")
        return sim
