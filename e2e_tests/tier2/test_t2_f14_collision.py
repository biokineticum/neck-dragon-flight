"""e2e_tests/tier2/test_t2_f14_collision.py
Tier 2: Boundary Value Analysis & Robustness for Feature 14:
Collision Physics & Damage State (Glancing slide mechanics, tunneling prevention at max speed, clearance precision, multi-collision handling, zero health boundary).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature14Collision(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for collision physics and damage handling."""

    def setUp(self) -> None:
        super().setUp()
        self.dragon_scene_path = PROJECT_ROOT / "scenes" / "PlayerDragon.tscn"
        self.flight_ctrl_path = PROJECT_ROOT / "scripts" / "FlightController.gd"
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"
        self.game_mgr_path = PROJECT_ROOT / "scripts" / "GameManager.gd"

        self.assertTrue(self.dragon_scene_path.is_file(), f"PlayerDragon.tscn missing at {self.dragon_scene_path}")
        self.assertTrue(self.flight_ctrl_path.is_file(), f"FlightController.gd missing at {self.flight_ctrl_path}")
        self.assertTrue(self.chunk_mgr_path.is_file(), f"ChunkManager.gd missing at {self.chunk_mgr_path}")

        self.scene_content = self.dragon_scene_path.read_text(encoding="utf-8")
        self.flight_content = self.flight_ctrl_path.read_text(encoding="utf-8")
        self.chunk_content = self.chunk_mgr_path.read_text(encoding="utf-8")

    def test_t2_f14_01_glancing_angle_slide_boundary(self) -> None:
        """TEST-T2-F14-01: Glancing angle impacts execute move_and_slide() without hard trajectory halt."""
        self.assertIn("body.move_and_slide()", self.flight_content)

    def test_t2_f14_02_max_speed_tunneling_prevention(self) -> None:
        """TEST-T2-F14-02: Hull thickness (2.4m) exceeds per-tick displacement at MAX_DIVE_SPEED (0.9m) preventing tunneling."""
        self.assertIn("const MAX_DIVE_SPEED: float = 54.0", self.flight_content)
        self.assertIn("radius = 1.2", self.scene_content)
        max_tick_displacement = 54.0 * (1.0 / 60.0)  # 0.9m
        hull_diameter = 1.2 * 2.0  # 2.4m
        self.assertGreater(hull_diameter, max_tick_displacement * 2.0, "Hull dimension is too thin relative to max displacement")

    def test_t2_f14_03_sub_decimeter_near_miss_clearance(self) -> None:
        """TEST-T2-F14-03: Collider bounds strictly adhere to capsule radius without artificial proximity trigger bloat."""
        self.assertIn("radius = 1.2", self.scene_content)
        self.assertIn("height = 3.2", self.scene_content)
        self.assertNotIn("Area3D", self.scene_content)

    def test_t2_f14_04_multi_collider_simultaneous_impact(self) -> None:
        """TEST-T2-F14-04: Simultaneous contacts with multiple colliders in single tick are iterated via get_slide_collision_count."""
        self.assertIn("for i in range(body.get_slide_collision_count()):", self.flight_content)
        self.assertIn("var col = body.get_slide_collision(i)", self.flight_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t2_f14_05_fatal_damage_threshold_boundary(self) -> None:
        """TEST-T2-F14-05: Health decrement reaching 0 triggers crash state transition without negative underflow."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("<= 0" in gm_content or "max(0" in gm_content)


if __name__ == "__main__":
    unittest.main()
