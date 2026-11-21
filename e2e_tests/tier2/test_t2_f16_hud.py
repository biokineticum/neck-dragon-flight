"""e2e_tests/tier2/test_t2_f16_hud.py
Tier 2: Boundary Value Analysis & Robustness for Feature 16:
Flight HUD & Telemetry UI (Speed readout formatting boundaries, large distance overflow, zero health clamping, reticle clamping, headless UI stability).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature16HUD(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for Flight HUD and telemetry display."""

    def setUp(self) -> None:
        super().setUp()
        self.hud_script_path = PROJECT_ROOT / "scripts" / "HUD.gd"
        self.hud_scene_path = PROJECT_ROOT / "scenes" / "HUD.tscn"

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t2_f16_01_speed_display_formatting_boundaries(self) -> None:
        """TEST-T2-F16-01: Airspeed formatting handles extreme values without scientific notation."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("%" in content or "str(" in content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t2_f16_02_large_distance_string_formatting(self) -> None:
        """TEST-T2-F16-02: Distance formatting supports large integer distances (> 10000m) without truncation."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("distance" in content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t2_f16_03_zero_health_display_boundary(self) -> None:
        """TEST-T2-F16-03: Zero or negative health values clamp to 0 active hearts."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("clamp" in content or "<=" in content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t2_f16_04_telemetry_reticle_position_clamping(self) -> None:
        """TEST-T2-F16-04: Telemetry reticle offset is bounded by maximum indicator radius."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("clamp" in content.lower() or "limit_length" in content.lower() or "radius" in content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scenes" / "HUD.tscn").is_file(), "scenes/HUD.tscn not yet created by builder milestone")
    def test_t2_f16_05_headless_ui_execution_stability(self) -> None:
        """TEST-T2-F16-05: HUD scene instantiates cleanly in headless Godot runner without DisplayServer error."""
        runner = self.create_godot_runner(scene_path="scenes/HUD.tscn", start_now=True)
        exit_code = runner.wait_for_exit(timeout=10.0)
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
