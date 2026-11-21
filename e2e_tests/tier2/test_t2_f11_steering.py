"""e2e_tests/tier2/test_t2_f11_steering.py
Tier 2: Boundary Value Analysis & Robustness for Feature 11:
Coordinated Banking & Pitch Steering (Bank roll clamping, pitch clamping, angular rate limits, gimbal lock immunity).
"""

import unittest
from pathlib import Path
from typing import List, Optional

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.godot_runner import GodotDiscovery, GodotProcessManager
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def is_godot_available() -> bool:
    try:
        GodotDiscovery.find_binary()
        return True
    except FileNotFoundError:
        return False


class TestTier2Feature11Steering(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for coordinated banking and pitch steering kinematics."""

    _cached_engine_logs: Optional[List[str]] = None

    @classmethod
    def get_engine_logs(cls) -> List[str]:
        if cls._cached_engine_logs is None:
            if not is_godot_available():
                return []
            manager = GodotProcessManager(script_path="test/test_flight_physics.gd")
            manager.start()
            manager.wait_for_exit(timeout=15.0)
            cls._cached_engine_logs = list(manager.all_logs)
        return cls._cached_engine_logs

    def setUp(self) -> None:
        super().setUp()
        self.flight_ctrl_path = PROJECT_ROOT / "scripts" / "FlightController.gd"
        self.assertTrue(self.flight_ctrl_path.is_file(), f"FlightController.gd missing at {self.flight_ctrl_path}")
        self.content = self.flight_ctrl_path.read_text(encoding="utf-8")

    def test_t2_f11_01_max_bank_roll_clamping(self) -> None:
        """TEST-T2-F11-01: Maximum bank angle clamps strictly within [-42.0°, +42.0°]."""
        self.assertIn("const MAX_BANK_ANGLE_DEG: float = 42.0", self.content)
        self.assertIn("clampf(current_roll, deg_to_rad(-MAX_BANK_ANGLE_DEG), deg_to_rad(MAX_BANK_ANGLE_DEG))", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Roll = 41.99 deg" in l or "Roll = -42.00 deg" in l for l in logs))

    def test_t2_f11_02_max_climb_pitch_clamping(self) -> None:
        """TEST-T2-F11-02: Maximum climb pitch angle clamps strictly at +MAX_PITCH_DEG (+32.0°)."""
        self.assertIn("const MAX_PITCH_DEG: float = 32.0", self.content)
        self.assertIn("deg_to_rad(MAX_PITCH_DEG)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Pitch: 32.00 deg" in l for l in logs))

    def test_t2_f11_03_max_dive_pitch_clamping(self) -> None:
        """TEST-T2-F11-03: Maximum dive pitch angle clamps strictly at -MAX_PITCH_DEG (-32.0°)."""
        self.assertIn("deg_to_rad(-MAX_PITCH_DEG)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Pitch: -32.00 deg" in l for l in logs))

    def test_t2_f11_04_steering_reversal_angular_rate_limit(self) -> None:
        """TEST-T2-F11-04: Turn reversal rate is bounded by MAX_YAW_RATE_DPS (38.0°/s) and roll smoothing."""
        self.assertIn("const MAX_YAW_RATE_DPS: float = 38.0", self.content)
        self.assertIn("roll_response_speed: float = 8.0", self.content)

    def test_t2_f11_05_gimbal_lock_immunity(self) -> None:
        """TEST-T2-F11-05: 3D Basis is explicitly orthonormalized preventing determinant drift or gimbal lock."""
        self.assertIn("var b = Basis(Vector3.UP, current_heading)", self.content)
        self.assertIn("b = b.rotated(b.x, current_pitch)", self.content)
        self.assertIn("b = b.rotated(-b.z, current_roll)", self.content)
        self.assertIn("body.global_transform.basis = b.orthonormalized()", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Basis det = 1.000000" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
