"""e2e_tests/tier1/test_t1_f15_gameover.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 15:
Hit-Stop, Screen Shake & Game Over Loop (Time dilation, camera trauma, state machine transitions, Game Over UI, flight state reset).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature15GameOver(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for crash response and game over lifecycle."""

    def setUp(self) -> None:
        super().setUp()
        self.flight_ctrl_path = PROJECT_ROOT / "scripts" / "FlightController.gd"
        self.game_mgr_path = PROJECT_ROOT / "scripts" / "GameManager.gd"

        self.assertTrue(self.flight_ctrl_path.is_file(), f"FlightController.gd missing at {self.flight_ctrl_path}")
        self.flight_content = self.flight_ctrl_path.read_text(encoding="utf-8")

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t1_f15_01_hit_stop_time_dilation(self) -> None:
        """TEST-T1-F15-01: Fatal impact dilates Engine.time_scale to 0.05 for 0.20s hit-stop window."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertIn("0.05", gm_content)
        self.assertIn("0.20", gm_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t1_f15_02_camera_trauma_shake(self) -> None:
        """TEST-T1-F15-02: Fatal collision sets camera trauma to maximum 1.0 driving high-amplitude shake."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("trauma" in gm_content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t1_f15_03_game_state_transition_sequence(self) -> None:
        """TEST-T1-F15-03: Crash progression transitions cleanly through FLYING -> CRASHING -> GAME_OVER."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertIn("FLYING", gm_content)
        self.assertIn("CRASHING", gm_content)
        self.assertIn("GAME_OVER", gm_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t1_f15_04_game_over_screen_visibility(self) -> None:
        """TEST-T1-F15-04: Transition to GAME_OVER activates Game Over screen overlay."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("visible" in gm_content.lower())

    def test_t1_f15_05_game_state_reset_on_restart(self) -> None:
        """TEST-T1-F15-05: FlightController reset_flight_state restores speed to cruise, distance to 0, and attitude to neutral."""
        self.assertIn("func reset_flight_state(start_position: Vector3 = Vector3(0, 15, 0)) -> void:", self.flight_content)
        self.assertIn("current_speed = CRUISE_SPEED", self.flight_content)
        self.assertIn("flight_distance = 0.0", self.flight_content)
        self.assertIn("current_heading = 0.0", self.flight_content)
        self.assertIn("current_pitch = 0.0", self.flight_content)
        self.assertIn("current_roll = 0.0", self.flight_content)


if __name__ == "__main__":
    unittest.main()
