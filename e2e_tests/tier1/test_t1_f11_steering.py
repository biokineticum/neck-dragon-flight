"""e2e_tests/tier1/test_t1_f11_steering.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 11:
Coordinated Banking & Pitch Steering (Turn banking kinematics, yaw rate, pitch climb/dive, manual roll blending).
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


class TestTier1Feature11Steering(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for coordinated banking and pitch steering kinematics."""

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

    def test_t1_f11_01_coordinated_left_turn_banking(self) -> None:
        """TEST-T1-F11-01: Full left turn input banks dragon roll into turn up to -42.0°."""
        self.assertIn("const MAX_BANK_ANGLE_DEG: float = 42.0", self.content)
        self.assertIn("const MAX_YAW_RATE_DPS: float = 38.0", self.content)
        self.assertIn("target_roll_rad = yaw_in * deg_to_rad(MAX_BANK_ANGLE_DEG)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Left turn: Roll = -42.00 deg" in l for l in logs))
            self.assertTrue(any("Coordinated banking to ±42° and orthonormal basis preservation verified" in l for l in logs))

    def test_t1_f11_02_coordinated_right_turn_banking(self) -> None:
        """TEST-T1-F11-02: Full right turn input rotates heading and banks roll up to +42.0°."""
        self.assertIn("current_heading -= yaw_in * yaw_rate_rad * delta", self.content)
        self.assertIn("current_heading = wrapf(current_heading, -PI, PI)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Right turn: Roll = 41.99 deg" in l for l in logs))

    def test_t1_f11_03_direct_pitch_climb_response(self) -> None:
        """TEST-T1-F11-03: Full climb input sets pitch angle toward +32.0°."""
        self.assertIn("const MAX_PITCH_DEG: float = 32.0", self.content)
        self.assertIn("target_pitch_rad = pitch_in * deg_to_rad(MAX_PITCH_DEG)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Pitch: 32.00 deg" in l for l in logs))

    def test_t1_f11_04_direct_pitch_dive_response(self) -> None:
        """TEST-T1-F11-04: Full dive input sets pitch angle toward -32.0°."""
        self.assertIn("current_pitch = clampf(current_pitch, deg_to_rad(-MAX_PITCH_DEG), deg_to_rad(MAX_PITCH_DEG))", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Pitch: -32.00 deg" in l for l in logs))

    def test_t1_f11_05_manual_roll_override_blending(self) -> None:
        """TEST-T1-F11-05: Manual roll input blends with coordinated yaw roll within MAX_BANK_ANGLE_DEG."""
        self.assertIn("yaw_in * deg_to_rad(MAX_BANK_ANGLE_DEG) + roll_in * deg_to_rad(15.0)", self.content)
        self.assertIn("current_roll = lerp_angle(current_roll, target_roll_rad, clampf(roll_response_speed * delta, 0.0, 1.0))", self.content)


if __name__ == "__main__":
    unittest.main()
