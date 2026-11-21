"""Custom domain assertion helpers for opaque-box E2E testing.

Provides strict, deterministic mathematical, structural, and behavioral checks
for UDP telemetry datagrams, kinematics vectors, state machines, and timing rates.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
from .config import (
    DEADZONE_THRESHOLD_DEG,
    MAX_PACKET_RATE_HZ,
    MIN_PACKET_RATE_HZ,
    PITCH_BOUNDS_DEG,
    REQUIRED_TELEMETRY_KEYS,
    ROLL_BOUNDS_DEG,
    SIGNAL_DECAY_RATE,
    YAW_BOUNDS_DEG,
)


def assert_packet_schema(packet: Dict[str, Any], context: str = "") -> None:
    """Asserts that a dictionary conforms strictly to Interface Contract 1 schema."""
    prefix = f"[{context}] " if context else ""
    if not isinstance(packet, dict):
        raise AssertionError(f"{prefix}Expected dict payload, got {type(packet).__name__}")

    missing = REQUIRED_TELEMETRY_KEYS - set(packet.keys())
    if missing:
        raise AssertionError(f"{prefix}Telemetry packet missing required keys: {sorted(missing)}")

    for key in ("pitch", "yaw", "roll"):
        val = packet[key]
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise AssertionError(f"{prefix}Key '{key}' must be numeric (non-bool), got {type(val).__name__} ({val})")
        if math.isnan(val) or math.isinf(val):
            raise AssertionError(f"{prefix}Key '{key}' must be a finite float, got {val}")

    for key in ("calibrated", "tracking"):
        val = packet[key]
        if not isinstance(val, bool):
            raise AssertionError(f"{prefix}Key '{key}' must be boolean, got {type(val).__name__} ({val})")

    ts = packet["timestamp"]
    if not isinstance(ts, (int, float)):
        raise AssertionError(f"{prefix}Key 'timestamp' must be numeric, got {type(ts).__name__} ({ts})")
    if ts <= 0:
        raise AssertionError(f"{prefix}Key 'timestamp' must be positive, got {ts}")


def assert_angle_in_bounds(pitch: float, yaw: float, roll: float, context: str = "") -> None:
    """Asserts that Euler angles are strictly within physical bounding envelopes."""
    prefix = f"[{context}] " if context else ""
    p_min, p_max = PITCH_BOUNDS_DEG
    y_min, y_max = YAW_BOUNDS_DEG
    r_min, r_max = ROLL_BOUNDS_DEG

    if not (p_min <= pitch <= p_max):
        raise AssertionError(f"{prefix}Pitch {pitch:.3f}° exceeded range [{p_min}, {p_max}]°")
    if not (y_min <= yaw <= y_max):
        raise AssertionError(f"{prefix}Yaw {yaw:.3f}° exceeded range [{y_min}, {y_max}]°")
    if not (r_min <= roll <= r_max):
        raise AssertionError(f"{prefix}Roll {roll:.3f}° exceeded range [{r_min}, {r_max}]°")


def assert_packet_rate(
    timestamps: Sequence[float],
    min_hz: float = MIN_PACKET_RATE_HZ,
    max_hz: float = MAX_PACKET_RATE_HZ,
    context: str = "",
) -> float:
    """Calculates transmission rate across timestamps and asserts it meets requirements."""
    prefix = f"[{context}] " if context else ""
    if len(timestamps) < 2:
        raise AssertionError(f"{prefix}Need at least 2 timestamps to compute rate, got {len(timestamps)}")

    duration = timestamps[-1] - timestamps[0]
    if duration <= 0:
        raise AssertionError(f"{prefix}Invalid non-positive duration between first and last timestamp: {duration}")

    rate_hz = (len(timestamps) - 1) / duration
    if not (min_hz <= rate_hz <= max_hz):
        raise AssertionError(
            f"{prefix}Measured packet rate {rate_hz:.2f} Hz is outside allowable range [{min_hz}, {max_hz}] Hz "
            f"({len(timestamps)} packets in {duration:.3f}s)"
        )
    return rate_hz


def assert_vector_close(
    v1: Sequence[float],
    v2: Sequence[float],
    tol: float = 1e-3,
    msg: Optional[str] = None,
) -> None:
    """Asserts that two spatial vectors have Euclidean distance less than or equal to tol."""
    if len(v1) != len(v2):
        raise AssertionError(f"Vector dimensions do not match: {len(v1)} vs {len(v2)}")

    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
    if dist > tol:
        error_msg = msg or f"Vector distance {dist:.5f} exceeds tolerance {tol:.5f} (v1={v1}, v2={v2})"
        raise AssertionError(error_msg)


def assert_state_transition(
    history: List[str],
    expected_sequence: List[str],
    context: str = "",
) -> None:
    """Asserts that observed states contain or exactly follow an expected state sequence."""
    prefix = f"[{context}] " if context else ""
    if not expected_sequence:
        return

    # Check subsequence in order
    idx = 0
    for state in history:
        if state == expected_sequence[idx]:
            idx += 1
            if idx == len(expected_sequence):
                return

    raise AssertionError(
        f"{prefix}State sequence {expected_sequence} was not observed in actual history {history}"
    )


def assert_control_mode(actual_mode: str, expected_mode: str, context: str = "") -> None:
    """Asserts control mode string is one of the valid states and matches expected."""
    prefix = f"[{context}] " if context else ""
    valid_modes = {"WEBCAM", "KEYBOARD_MOUSE", "BLENDED"}
    if actual_mode not in valid_modes:
        raise AssertionError(f"{prefix}Invalid control mode '{actual_mode}'; must be one of {valid_modes}")
    if actual_mode != expected_mode:
        raise AssertionError(f"{prefix}Expected control mode '{expected_mode}', got '{actual_mode}'")


def assert_jitter_suppressed(
    angles: Sequence[float],
    max_std_deg: float = 0.5,
    context: str = "",
) -> float:
    """Calculates standard deviation of an angle series and asserts jitter suppression."""
    prefix = f"[{context}] " if context else ""
    n = len(angles)
    if n < 3:
        raise AssertionError(f"{prefix}Need at least 3 angle samples to evaluate jitter, got {n}")

    for idx, a in enumerate(angles):
        if not isinstance(a, (int, float)) or isinstance(a, bool) or math.isnan(a) or math.isinf(a):
            raise AssertionError(f"{prefix}Angle sample at index {idx} must be a finite number, got {a}")

    mean = sum(angles) / n
    variance = sum((x - mean) ** 2 for x in angles) / (n - 1)
    std_deg = math.sqrt(variance)

    if math.isnan(std_deg) or math.isinf(std_deg):
        raise AssertionError(f"{prefix}Computed jitter standard deviation is not finite: {std_deg}")

    if std_deg > max_std_deg:
        raise AssertionError(
            f"{prefix}Measured angular jitter std {std_deg:.4f}° exceeds allowed maximum {max_std_deg:.4f}°"
        )
    return std_deg


def assert_deadzone_applied(
    raw_angle: float,
    output_angle: float,
    threshold: float = DEADZONE_THRESHOLD_DEG,
    context: str = "",
) -> None:
    """Asserts that an angle within [-threshold, +threshold] produces exactly 0.0."""
    prefix = f"[{context}] " if context else ""
    if abs(raw_angle) <= threshold:
        if abs(output_angle) > 1e-6:
            raise AssertionError(
                f"{prefix}Raw angle {raw_angle}° is within deadzone ±{threshold}°, "
                f"but output was non-zero: {output_angle}"
            )


def assert_decay_rate(
    samples: List[Tuple[float, float]],
    expected_rate: float = SIGNAL_DECAY_RATE,
    tol: float = 3.0,
    context: str = "",
) -> float:
    """Verifies that an angle signal decays toward 0.0 at the expected decay rate."""
    prefix = f"[{context}] " if context else ""
    if len(samples) < 2:
        raise AssertionError(f"{prefix}Need at least 2 timed samples (t, angle) to verify decay")

    t0, a0 = samples[0]
    t1, a1 = samples[-1]
    dt = t1 - t0
    if dt <= 0:
        raise AssertionError(f"{prefix}Invalid time delta {dt} for decay calculation")

    measured_decay = abs(a0 - a1) / dt
    if abs(measured_decay - expected_rate) > tol:
        raise AssertionError(
            f"{prefix}Measured signal decay rate {measured_decay:.2f}/s deviates from expected {expected_rate}/s (tol={tol})"
        )
    return measured_decay
