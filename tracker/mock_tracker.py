"""
mock_tracker.py - Synthetic UDP Telemetry Packet Injector for Dragon Flight

Milestone 1: Programmable synthetic head tracking data generator for
headless integration tests, CI pipelines, and manual flight physics tuning.

Supports both a high-level programmatic API (MockTracker class) and a CLI interface.
"""

import os
import sys
import json
import time
import math
import socket
import argparse
import threading
from typing import Optional, Callable, Dict, Any


class MockTracker:
    """
    Programmable synthetic UDP packet generator simulating player head movements.
    Adheres strictly to Interface Contract 1.
    """
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 42425,
        frequency: float = 30.0,
        amplitude: float = 20.0,
        period: float = 2.0
    ):
        self.host = str(host)
        self.port = int(port)
        self.frequency = float(frequency)
        self.amplitude = float(amplitude)
        self.period = float(period)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except OSError:
                pass
        self.sock.setblocking(False)

        self._running = False
        self._thread: Optional[threading.Thread] = None

    def generate_packet(self, mode: str, elapsed_time: float, **kwargs) -> Dict[str, Any]:
        """
        Generates a synthetic telemetry dictionary according to the requested trajectory mode.
        Clamps all angles to Interface Contract 1 schema limits.
        """
        amp = float(kwargs.get("amplitude", self.amplitude))
        period = float(kwargs.get("period", self.period))
        omega = (2.0 * math.pi) / max(0.001, period)

        pitch = 0.0
        yaw = 0.0
        roll = 0.0
        calibrated = True
        tracking = True

        mode_clean = mode.strip().lower()

        if mode_clean == "neutral":
            pass
        elif mode_clean == "dive":
            pitch = -amp
        elif mode_clean == "climb":
            pitch = amp
        elif mode_clean == "roll_left":
            roll = -amp
        elif mode_clean == "roll_right":
            roll = amp
        elif mode_clean == "yaw_left":
            yaw = -amp
        elif mode_clean == "yaw_right":
            yaw = amp
        elif mode_clean == "sine_wave":
            pitch = amp * math.sin(omega * elapsed_time)
            roll = (amp * 0.5) * math.sin(omega * elapsed_time)
        elif mode_clean == "spiral":
            pitch = amp * math.sin(omega * elapsed_time)
            yaw = amp * math.cos(omega * elapsed_time)
            roll = (amp * 0.7) * math.sin(omega * elapsed_time + math.pi / 4.0)
        elif mode_clean == "step":
            step_time = float(kwargs.get("step_time", 1.0))
            if elapsed_time >= step_time:
                pitch = float(kwargs.get("target_pitch", amp))
                yaw = float(kwargs.get("target_yaw", 0.0))
                roll = float(kwargs.get("target_roll", 0.0))
        elif mode_clean == "tracking_loss":
            tracking = False
        elif mode_clean == "uncalibrated":
            calibrated = False
        else:
            raise ValueError(
                f"Unknown mock trajectory mode '{mode}'. Valid modes: "
                "neutral, dive, climb, roll_left, roll_right, yaw_left, yaw_right, "
                "sine_wave, spiral, step, tracking_loss, uncalibrated."
            )

        # Enforce strict boundary clamping per Interface Contract 1
        pitch = max(-35.0, min(35.0, pitch))
        yaw = max(-45.0, min(45.0, yaw))
        roll = max(-35.0, min(35.0, roll))

        return {
            "pitch": round(float(pitch), 3),
            "yaw": round(float(yaw), 3),
            "roll": round(float(roll), 3),
            "calibrated": calibrated,
            "tracking": tracking,
            "timestamp": round(time.time(), 4)
        }

    def send_packet(self, packet: Dict[str, Any]) -> bool:
        """Encodes and transmits a telemetry datagram."""
        try:
            payload = json.dumps(packet, separators=(',', ':')).encode("utf-8")
            self.sock.sendto(payload, (self.host, self.port))
            return True
        except (socket.error, OSError, OverflowError, TypeError, ValueError):
            return False

    def run(
        self,
        mode: str = "neutral",
        duration: Optional[float] = 5.0,
        loop: bool = False,
        on_packet_sent: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs
    ) -> None:
        """
        Synchronous packet broadcast loop paced at target frequency.
        """
        self._running = True
        interval = 1.0 / max(1.0, self.frequency)
        t_start = time.perf_counter()
        next_tick = t_start

        try:
            while self._running:
                now = time.perf_counter()
                elapsed = now - t_start

                if not loop and duration is not None and duration > 0 and elapsed >= duration:
                    break

                packet = self.generate_packet(mode, elapsed, **kwargs)
                self.send_packet(packet)

                if on_packet_sent:
                    on_packet_sent(packet)

                next_tick += interval
                delay = next_tick - time.perf_counter()
                if delay > 0.0005:
                    time.sleep(delay)
                elif delay < -interval:
                    next_tick = time.perf_counter()
        finally:
            self._running = False

    def start_background(
        self,
        mode: str = "neutral",
        duration: Optional[float] = None,
        on_packet_sent: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs
    ) -> threading.Thread:
        """
        Starts synthetic packet broadcast on a daemon background thread.
        """
        if self._running:
            raise RuntimeError("MockTracker background thread is already active.")

        should_loop = (duration is None or duration <= 0)
        self._thread = threading.Thread(
            target=self.run,
            kwargs={
                "mode": mode,
                "duration": duration,
                "loop": should_loop,
                "on_packet_sent": on_packet_sent,
                **kwargs
            },
            daemon=True
        )
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        """Signals background broadcast loop to stop and waits for exit."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

    def close(self) -> None:
        """Stops background loop and closes UDP socket."""
        self.stop()
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic UDP Head-Tracking Feeder")
    parser.add_argument(
        "--mode", type=str, default="neutral",
        choices=[
            "neutral", "dive", "climb", "roll_left", "roll_right",
            "yaw_left", "yaw_right", "sine_wave", "spiral", "step",
            "tracking_loss", "uncalibrated"
        ],
        help="Trajectory mode to simulate"
    )
    parser.add_argument("--duration", type=float, default=5.0, help="Run duration in seconds (<=0 for infinite)")
    parser.add_argument("--frequency", type=float, default=30.0, help="Transmission frequency in Hz (default: 30)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Target UDP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=42425, help="Target UDP port (default: 42425)")
    parser.add_argument("--amplitude", type=float, default=20.0, help="Maneuver amplitude in degrees (default: 20)")
    parser.add_argument("--period", type=float, default=2.0, help="Sine/spiral wave period in seconds (default: 2)")
    parser.add_argument("--step-time", type=float, default=1.0, help="Time before transition in step mode (default: 1)")
    parser.add_argument("--loop", action="store_true", help="Run indefinitely until interrupted")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print sent packets to stdout")

    args = parser.parse_args()

    if not (1 <= args.port <= 65535):
        print(f"[ERROR] Port must be between 1 and 65535 (got {args.port}).", file=sys.stderr)
        sys.exit(1)

    tracker = MockTracker(
        host=args.host,
        port=args.port,
        frequency=args.frequency,
        amplitude=args.amplitude,
        period=args.period
    )

    def print_packet(pkt: Dict[str, Any]) -> None:
        print(f"[SENT] pitch={pkt['pitch']:+6.1f}, yaw={pkt['yaw']:+6.1f}, roll={pkt['roll']:+6.1f}, "
              f"calib={pkt['calibrated']}, track={pkt['tracking']}, t={pkt['timestamp']}")

    callback = print_packet if args.verbose else None

    print(f"[INFO] MockTracker broadcasting mode '{args.mode}' to {args.host}:{args.port} at {args.frequency} Hz...")
    if args.loop or args.duration <= 0:
        print("[INFO] Running in loop mode. Press Ctrl+C to terminate.")
    else:
        print(f"[INFO] Running for {args.duration:.1f} seconds...")

    try:
        tracker.run(
            mode=args.mode,
            duration=args.duration,
            loop=args.loop,
            on_packet_sent=callback,
            step_time=args.step_time
        )
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
    finally:
        tracker.close()
        print("[INFO] MockTracker finished.")


if __name__ == "__main__":
    main()
