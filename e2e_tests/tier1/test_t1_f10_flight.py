"""e2e_tests/tier1/test_t1_f10_flight.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 10:
Continuous Forward Flight Aerodynamics (Cruise velocity, dive acceleration, climb deceleration, drag recovery, distance accumulation).
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


class TestTier1Feature10Flight(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for continuous forward flight aerodynamics."""

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

    def test_t1_f10_01_cruise_velocity_level_flight(self) -> None:
        """TEST-T1-F10-01: Flight maintaining level pitch sustains cruise speed 30.0 m/s ± 1.0 m/s."""
        self.assertIn("const CRUISE_SPEED: float = 30.0", self.content)
        self.assertIn("var current_speed: float = 30.0", self.content)
        self.assertIn("body.velocity = fwd_vec * current_speed", self.content)
        self.assertIn("speed_changed.emit(current_speed, min_speed, MAX_DIVE_SPEED)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Continuous forward flight along -Z verified at 30.0 m/s" in l for l in logs))

    def test_t1_f10_02_dive_acceleration(self) -> None:
        """TEST-T1-F10-02: Sustained dive pitch input accelerates speed monotonically toward 54.0 m/s."""
        self.assertIn("const MAX_DIVE_SPEED: float = 54.0", self.content)
        self.assertIn("const ACCELERATION_DIVE: float = 12.0", self.content)
        self.assertIn("current_speed += dive_strength * ACCELERATION_DIVE * delta", self.content)
        self.assertIn("minf(current_speed, MAX_DIVE_SPEED)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Dive speed after 2.0s: 54.00 m/s" in l for l in logs))
            self.assertTrue(any("Dive acceleration to 54.0 m/s and level drag recovery verified" in l for l in logs))

    def test_t1_f10_03_climb_deceleration(self) -> None:
        """TEST-T1-F10-03: Sustained climb pitch input decelerates speed monotonically toward 18.0 m/s."""
        self.assertIn("const MIN_CLIMB_SPEED: float = 18.0", self.content)
        self.assertIn("const DECELERATION_CLIMB: float = 8.0", self.content)
        self.assertIn("current_speed -= climb_strength * DECELERATION_CLIMB * delta", self.content)
        self.assertIn("maxf(current_speed, min_speed)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Climb speed after 2.0s: 18.00 m/s" in l for l in logs))
            self.assertTrue(any("18.0 m/s stall floor clamping verified" in l for l in logs))

    def test_t1_f10_04_speed_recovery_to_cruise(self) -> None:
        """TEST-T1-F10-04: Aerodynamic drag returns overspeed back toward cruise speed (30 m/s)."""
        self.assertIn("const DRAG_DECELERATION: float = 4.0", self.content)
        self.assertIn("current_speed = move_toward(current_speed, CRUISE_SPEED, DRAG_DECELERATION * delta)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Speed after 1.0s level recovery: 50.00 m/s" in l for l in logs))

    def test_t1_f10_05_distance_traveled_accumulation(self) -> None:
        """TEST-T1-F10-05: Steady flight accumulates forward distance matching flight speed integral."""
        self.assertIn("flight_distance += current_speed * delta", self.content)
        self.assertIn("distance_updated.emit(flight_distance)", self.content)
        self.assertIn("func get_flight_distance() -> float:", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Distance: 30.00 m" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
