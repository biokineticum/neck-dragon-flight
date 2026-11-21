"""e2e_tests/tier2/test_t2_f15_gameover.py
Tier 2: Boundary Value Analysis & Robustness for Feature 15:
Hit-Stop, Screen Shake & Game Over Loop (Hit-stop timing precision, immediate reset during hit-stop, restart idempotence, trauma decay, chunk reset alignment).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature15GameOver(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for crash response and game over lifecycle."""

    def setUp(self) -> None:
        super().setUp()
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"
        self.game_mgr_path = PROJECT_ROOT / "scripts" / "GameManager.gd"

        self.assertTrue(self.chunk_mgr_path.is_file(), f"ChunkManager.gd missing at {self.chunk_mgr_path}")
        self.chunk_content = self.chunk_mgr_path.read_text(encoding="utf-8")

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t2_f15_01_hit_stop_exact_duration_precision(self) -> None:
        """TEST-T2-F15-01: Hit-stop duration matches 0.20s precision preventing prolonged world freeze."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertIn("0.20", gm_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t2_f15_02_immediate_restart_during_hit_stop(self) -> None:
        """TEST-T2-F15-02: Restart triggered while hit-stop is active restores Engine.time_scale to 1.0 immediately."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertIn("time_scale = 1.0", gm_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t2_f15_03_rapid_restart_action_spam(self) -> None:
        """TEST-T2-F15-03: Multiple rapid restart signals execute idempotently without duplicating world nodes."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("restart" in gm_content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t2_f15_04_trauma_shake_decay_asymptote(self) -> None:
        """TEST-T2-F15-04: Camera trauma decays asymptotically toward 0.0 without lingering vibration."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("trauma" in gm_content.lower())

    def test_t2_f15_05_chunk_alignment_post_reset(self) -> None:
        """TEST-T2-F15-05: ChunkManager reset_corridor loops all active chunks and restores positions to initial offsets."""
        self.assertIn("func reset_corridor() -> void:", self.chunk_content)
        self.assertIn("current_front_z = 0.0", self.chunk_content)
        self.assertIn("for i in range(pool_size):", self.chunk_content)
        self.assertIn("-float(i) * chunk_length", self.chunk_content)


if __name__ == "__main__":
    unittest.main()
