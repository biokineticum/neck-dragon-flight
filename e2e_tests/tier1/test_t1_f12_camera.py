"""e2e_tests/tier1/test_t1_f12_camera.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 12:
First-Person Cockpit & Camera Rig (Saddle vantage position, spring-damper roll lag, wing flap bobbing, dynamic FOV, foreground framing).
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


class TestTier1Feature12Camera(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for first-person camera rig and roll lag."""

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
        self.cam_script_path = PROJECT_ROOT / "scripts" / "CameraFollow.gd"
        self.dragon_scene_path = PROJECT_ROOT / "scenes" / "PlayerDragon.tscn"
        self.visual_rig_path = PROJECT_ROOT / "scripts" / "DragonVisualRig.gd"

        self.assertTrue(self.cam_script_path.is_file(), f"CameraFollow.gd missing at {self.cam_script_path}")
        self.assertTrue(self.dragon_scene_path.is_file(), f"PlayerDragon.tscn missing at {self.dragon_scene_path}")
        self.assertTrue(self.visual_rig_path.is_file(), f"DragonVisualRig.gd missing at {self.visual_rig_path}")

        self.cam_content = self.cam_script_path.read_text(encoding="utf-8")
        self.scene_content = self.dragon_scene_path.read_text(encoding="utf-8")
        self.rig_content = self.visual_rig_path.read_text(encoding="utf-8")

    def test_t1_f12_01_first_person_vantage_position(self) -> None:
        """TEST-T1-F12-01: Rider camera mounted at local position (0.0, 1.4, -0.2) in scene tree."""
        self.assertIn("const CAMERA_LOCAL_POS: Vector3 = Vector3(0.0, 1.4, -0.2)", self.cam_content)
        self.assertIn("CameraRig", self.scene_content)
        self.assertIn("1.4", self.scene_content)
        self.assertIn("-0.2", self.scene_content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Scene tree hierarchy, capsule collider, pivots, and camera mount verified" in l for l in logs))

    def test_t1_f12_02_spring_damper_roll_lag(self) -> None:
        """TEST-T1-F12-02: Camera rig implements roll lag ratio 0.65 with local counter-rotation."""
        self.assertIn("const ROLL_LAG_RATIO: float = 0.65", self.cam_content)
        self.assertIn("var target_world_roll: float = dragon_roll_deg * roll_lag_ratio", self.cam_content)
        self.assertIn("var local_roll_deg: float = smoothed_roll - dragon_roll_deg", self.cam_content)
        self.assertIn("transform.basis = Basis().rotated(Vector3(0, 0, -1), deg_to_rad(local_roll_deg))", self.cam_content)

    def test_t1_f12_03_wing_flap_bobbing_coupling(self) -> None:
        """TEST-T1-F12-03: Vertical heave bobbing is coupled to wing flap phase with amplitude <= 0.05m."""
        self.assertIn("heave_coupling_amplitude: float = 0.03", self.cam_content)
        self.assertIn("bob_y = sin(phase) * heave_coupling_amplitude", self.cam_content)
        self.assertIn("position = CAMERA_LOCAL_POS + Vector3(0.0, bob_y, 0.0)", self.cam_content)

    def test_t1_f12_04_dive_dynamic_fov_expansion(self) -> None:
        """TEST-T1-F12-04: Dynamic FOV expands from BASE_FOV (75°) to MAX_FOV (90°) scaled by speed."""
        self.assertIn("const BASE_FOV: float = 75.0", self.cam_content)
        self.assertIn("const MAX_FOV: float = 90.0", self.cam_content)
        self.assertIn("var speed_ratio: float = clampf((speed - 30.0) / (54.0 - 30.0), 0.0, 1.0)", self.cam_content)
        self.assertIn("var target_fov: float = lerpf(BASE_FOV, MAX_FOV, speed_ratio)", self.cam_content)

    def test_t1_f12_05_dragon_anatomy_foreground_framing(self) -> None:
        """TEST-T1-F12-05: Dragon head pivot (0, 0.1, -1.4) frames lower foreground relative to eye line (0, 1.4, -0.2)."""
        self.assertIn("Vector3(0.0, 0.10, -1.40)", self.rig_content)
        self.assertIn('"HeadPivot"', self.rig_content)
        self.assertIn("DragonVisualRig", self.scene_content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Test 1 Result: PASS" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
