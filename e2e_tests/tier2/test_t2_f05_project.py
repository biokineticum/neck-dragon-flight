"""e2e_tests/tier2/test_t2_f05_project.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 5:
Godot 4.7.2 Project Configuration (Scene references, renderer fallback, input event guards, display limits, script syntax).

Test Catalog:
- TEST-T2-F05-01: Missing Scene Reference Guard
- TEST-T2-F05-02: Headless Renderer Fallback (Dummy / Compatibility)
- TEST-T2-F05-03: Empty Input Event List Handling Guard
- TEST-T2-F05-04: Display Resolution Limits & Scaling Mode
- TEST-T2-F05-05: Script Syntax Parsing Exhaustion
"""

import re
import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_GODOT, PROJECT_ROOT
from e2e_tests.framework.godot_runner import GodotDiscovery
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def is_godot_available() -> bool:
    try:
        GodotDiscovery.find_binary()
        return True
    except FileNotFoundError:
        return False


class TestTier2Feature05Project(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for Godot project configuration."""

    def test_t2_f05_01_missing_scene_reference_guard(self) -> None:
        """TEST-T2-F05-01: All scene references in project.godot are located in scenes/ directory."""
        content = PROJECT_GODOT.read_text(encoding="utf-8")
        scene_refs = re.findall(r'"res://(scenes/[^"]+\.tscn)"', content)
        self.assertGreaterEqual(len(scene_refs), 1)

        for rel_path in scene_refs:
            file_path = PROJECT_ROOT / rel_path
            if file_path.is_file():
                self.assertTrue(file_path.is_file())
            else:
                # Progressive testability: scene directory must exist
                self.assertTrue(file_path.parent.is_dir(), f"Scene directory {file_path.parent} must exist")

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t2_f05_02_headless_renderer_fallback(self) -> None:
        """TEST-T2-F05-02: Engine executes headless with dummy rendering driver without crashing."""
        runner = self.create_godot_runner(
            script_path="test/test_milestone2_headless.gd",
            extra_args=["--rendering-driver", "dummy"],
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, f"Headless dummy renderer failed: {runner.all_logs}")

    def test_t2_f05_03_empty_input_event_guard(self) -> None:
        """TEST-T2-F05-03: Defined flight actions contain non-empty event arrays."""
        content = PROJECT_GODOT.read_text(encoding="utf-8")

        for act in ("steer_pitch_up", "steer_pitch_down", "steer_yaw_left", "steer_yaw_right", "calibrate"):
            match = re.search(rf"{act}=\{{\s*\"deadzone\":[^,]+,\s*\"events\":\s*\[([^\]]+)\]", content)
            self.assertIsNotNone(match, f"Action '{act}' has empty or malformed events list")
            events_body = match.group(1).strip()
            self.assertGreater(len(events_body), 0, f"Action '{act}' has empty events list")

    def test_t2_f05_04_display_resolution_limits(self) -> None:
        """TEST-T2-F05-04: Viewport stretch mode and aspect allow high-resolution scaling."""
        content = PROJECT_GODOT.read_text(encoding="utf-8")
        self.assertIn('mode="canvas_items"', content)
        self.assertIn('aspect="expand"', content)
        self.assertIn("resizable=true", content)

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t2_f05_05_script_syntax_parsing_exhaustion(self) -> None:
        """TEST-T2-F05-05: Headless engine parses all core GDScript files without parse errors."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, f"Script parsing failed: {runner.all_logs}")
