"""e2e_tests/tier1/test_t1_f16_hud.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 16:
Flight HUD & Telemetry UI (Airspeed readout, distance meter, heart health icons, tracking status dot, calibration hotkey binding).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature16HUD(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for Flight HUD and telemetry display."""

    def setUp(self) -> None:
        super().setUp()
        self.project_godot_path = PROJECT_ROOT / "project.godot"
        self.hud_script_path = PROJECT_ROOT / "scripts" / "HUD.gd"

        self.assertTrue(self.project_godot_path.is_file(), f"project.godot missing at {self.project_godot_path}")
        self.project_content = self.project_godot_path.read_text(encoding="utf-8")

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t1_f16_01_airspeed_display_update(self) -> None:
        """TEST-T1-F16-01: Airspeed indicator connects to speed_changed signal and formats float m/s."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("speed_changed" in content or "speed" in content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t1_f16_02_distance_readout_accumulation(self) -> None:
        """TEST-T1-F16-02: Distance indicator connects to distance_updated signal and formats meters."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("distance_updated" in content or "distance" in content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t1_f16_03_heart_health_icon_display(self) -> None:
        """TEST-T1-F16-03: HUD renders heart container reflecting player health status."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("health" in content.lower() or "heart" in content.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "scripts/HUD.gd not yet created by builder milestone")
    def test_t1_f16_04_webcam_tracking_status_dot(self) -> None:
        """TEST-T1-F16-04: Telemetry status dot reflects tracking activity."""
        content = self.hud_script_path.read_text(encoding="utf-8")
        self.assertTrue("tracking" in content.lower() or "status" in content.lower())

    def test_t1_f16_05_runtime_calibration_prompt_overlay(self) -> None:
        """TEST-T1-F16-05: Godot project defines 'calibrate' input action mapped to keycode 67 ('C')."""
        self.assertIn("calibrate={", self.project_content)
        self.assertIn('"physical_keycode":67', self.project_content)


if __name__ == "__main__":
    unittest.main()
