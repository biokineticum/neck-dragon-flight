"""e2e_tests/tier1/test_t1_f05_project.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 5:
Godot 4.7.2 Project Configuration (project.godot, layers, input actions, headless check, viewport).

Test Catalog:
- TEST-T1-F05-01: Main Scene Configuration Partition
- TEST-T1-F05-02: Physics Collision Layer Names Partition (Environment / Player)
- TEST-T1-F05-03: Custom Input Map Action Bindings Partition
- TEST-T1-F05-04: Headless Launch & Validation Partition
- TEST-T1-F05-05: Viewport Resolution & Stretch Mode Partition
"""

import re
import unittest

from e2e_tests.framework.config import PROJECT_GODOT, PROJECT_ROOT
from e2e_tests.framework.godot_runner import GodotDiscovery
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def is_godot_available() -> bool:
    """Checks whether the Godot executable is discovered on the host system."""
    try:
        GodotDiscovery.find_binary()
        return True
    except FileNotFoundError:
        return False


class TestTier1Feature05Project(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for Godot project configuration."""

    def test_t1_f05_01_main_scene_config(self) -> None:
        """TEST-T1-F05-01: project.godot specifies application/run/main_scene pointing to res://scenes/Main.tscn."""
        self.assertTrue(PROJECT_GODOT.is_file(), f"project.godot missing at {PROJECT_GODOT}")
        content = PROJECT_GODOT.read_text(encoding="utf-8")
        match = re.search(r'run/main_scene\s*=\s*"res://([^"]+)"', content)
        self.assertIsNotNone(match, "run/main_scene entry missing in project.godot")
        scene_path = match.group(1)
        self.assertEqual(scene_path, "scenes/Main.tscn", "Expected main scene 'scenes/Main.tscn'")

    def test_t1_f05_02_physics_collision_layers(self) -> None:
        """TEST-T1-F05-02: 3D physics collision layers configured with Layer 1='Environment' and Layer 2='Player'."""
        self.assertTrue(PROJECT_GODOT.is_file())
        content = PROJECT_GODOT.read_text(encoding="utf-8")
        self.assertIn('3d_physics/layer_1="Environment"', content)
        self.assertIn('3d_physics/layer_2="Player"', content)

    def test_t1_f05_03_input_map_actions(self) -> None:
        """TEST-T1-F05-03: Flight steering actions, calibrate, and restart/reset defined with mapped keys."""
        self.assertTrue(PROJECT_GODOT.is_file())
        content = PROJECT_GODOT.read_text(encoding="utf-8")

        required_actions = [
            "steer_pitch_up",
            "steer_pitch_down",
            "steer_yaw_left",
            "steer_yaw_right",
            "steer_roll_left",
            "steer_roll_right",
            "calibrate",
            "restart",
        ]
        for act in required_actions:
            self.assertIn(f"{act}={{", content, f"Action '{act}' missing in project.godot input map")

        self.assertIn("physical_keycode", content, "Input action mappings missing physical keycode definitions")

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t1_f05_04_headless_launch_validation(self) -> None:
        """TEST-T1-F05-04: Headless Godot engine compiles project files without script syntax/parse errors."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, f"Headless execution failed. Logs: {runner.all_logs}")

    def test_t1_f05_05_viewport_resolution_stretch(self) -> None:
        """TEST-T1-F05-05: Viewport resolution defined as 1280x720 with canvas_items stretch mode."""
        self.assertTrue(PROJECT_GODOT.is_file())
        content = PROJECT_GODOT.read_text(encoding="utf-8")
        self.assertIn("viewport_width=1280", content)
        self.assertIn("viewport_height=720", content)
        self.assertIn("resizable=true", content)
        self.assertIn('window/stretch/mode="canvas_items"', content)
        self.assertIn('window/stretch/aspect="expand"', content)
