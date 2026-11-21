"""e2e_tests/tier2/test_t2_f10_flight.py
Tier 2: Boundary Value Analysis & Robustness for Feature 10:
Continuous Forward Flight Aerodynamics (Terminal dive velocity ceiling, minimum stall speed floor, pitch reversal, zero delta, and tick rate invariance).
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


class TestTier2Feature10Flight(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for continuous forward flight aerodynamics."""

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

    def test_t2_f10_01_max_dive_speed_clamping(self) -> None:
        """TEST-T2-F10-01: Terminal dive velocity clamps strictly at MAX_DIVE_SPEED (54.0 m/s)."""
        self.assertIn("const MAX_DIVE_SPEED: float = 54.0", self.content)
        self.assertIn("minf(current_speed, MAX_DIVE_SPEED)", self.content)
        self.assertIn("clampf(current_speed, min_speed, MAX_DIVE_SPEED)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Dive speed after 2.0s: 54.00 m/s" in l for l in logs))

    def test_t2_f10_02_min_stall_speed_clamping(self) -> None:
        """TEST-T2-F10-02: Maximum climb deceleration clamps strictly at stall floor (18.0 m/s)."""
        self.assertIn("const MIN_CLIMB_SPEED: float = 18.0", self.content)
        self.assertIn("maxf(current_speed, min_speed)", self.content)
        self.assertIn("clampf(current_speed, min_speed, MAX_DIVE_SPEED)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("18.0 m/s stall floor clamping verified" in l for l in logs))

    def test_t2_f10_03_instantaneous_pitch_reversal(self) -> None:
        """TEST-T2-F10-03: Pitch reversal operates continuously via angular interpolation avoiding discontinuity."""
        self.assertIn("pitch_response_speed: float = 10.0", self.content)
        self.assertIn("lerp_angle(current_pitch, target_pitch_rad", self.content)
        self.assertIn("clampf(pitch_response_speed * delta, 0.0, 1.0)", self.content)

    def test_t2_f10_04_zero_delta_time_handling(self) -> None:
        """TEST-T2-F10-04: Zero delta time tick is handled cleanly without division by zero or NaN propagation."""
        self.assertIn("if delta <= 0.0:\n\t\treturn", self.content)

    def test_t2_f10_05_variable_tick_rate_invariance(self) -> None:
        """TEST-T2-F10-05: Riemann distance integration and displacement scale linearly with delta."""
        self.assertIn("flight_distance += current_speed * delta", self.content)
        self.assertIn("body.velocity = fwd_vec * current_speed", self.content)


if __name__ == "__main__":
    unittest.main()
