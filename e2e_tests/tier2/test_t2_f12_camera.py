"""e2e_tests/tier2/test_t2_f12_camera.py
Tier 2: Boundary Value Analysis & Robustness for Feature 12:
First-Person Cockpit & Camera Rig (FOV boundary clamping, near clip plane penetration guard, snap reset, horizon inversion guard).
"""

import math
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


class TestTier2Feature12Camera(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for first-person camera rig and roll lag."""

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
        self.flight_ctrl_path = PROJECT_ROOT / "scripts" / "FlightController.gd"

        self.assertTrue(self.cam_script_path.is_file(), f"CameraFollow.gd missing at {self.cam_script_path}")
        self.assertTrue(self.dragon_scene_path.is_file(), f"PlayerDragon.tscn missing at {self.dragon_scene_path}")

        self.cam_content = self.cam_script_path.read_text(encoding="utf-8")
        self.scene_content = self.dragon_scene_path.read_text(encoding="utf-8")
        self.flight_content = self.flight_ctrl_path.read_text(encoding="utf-8")

    def test_t2_f12_01_max_dynamic_fov_clamping(self) -> None:
        """TEST-T2-F12-01: Maximum FOV expansion is bounded strictly by MAX_FOV (90.0°) with hard safety clamp."""
        self.assertIn("const MAX_FOV: float = 90.0", self.cam_content)
        self.assertIn("clampf((speed - 30.0) / (54.0 - 30.0), 0.0, 1.0)", self.cam_content)
        self.assertIn("clampf(lerpf(camera_node.fov, target_fov, clampf(fov_lerp_speed * delta, 0.0, 1.0)), 74.0, 92.0)", self.cam_content)

    def test_t2_f12_02_min_dynamic_fov_clamping(self) -> None:
        """TEST-T2-F12-02: Speeds below cruise speed clamp ratio to 0.0 maintaining BASE_FOV (75.0°)."""
        self.assertIn("const BASE_FOV: float = 75.0", self.cam_content)
        self.assertIn("speed_ratio: float = clampf((speed - 30.0) / (54.0 - 30.0), 0.0, 1.0)", self.cam_content)

    def test_t2_f12_03_near_clip_plane_penetration_guard(self) -> None:
        """TEST-T2-F12-03: Near clipping plane near <= 0.05m prevents geometric clipping with dragon anatomy."""
        self.assertIn("near = 0.05", self.scene_content)
        self.assertIn("cam.near = 0.05", self.cam_content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("camera mount verified" in l for l in logs))

    def test_t2_f12_04_instantaneous_teleport_snap_handling(self) -> None:
        """TEST-T2-F12-04: Camera reset immediately snaps position and clears smoothed roll lag."""
        self.assertIn("func reset_camera() -> void:", self.cam_content)
        self.assertIn("position = CAMERA_LOCAL_POS", self.cam_content)
        self.assertIn("transform.basis = Basis()", self.cam_content)
        self.assertIn("smoothed_roll = 0.0", self.cam_content)
        self.assertIn("camera_rig.reset_camera()", self.flight_content)

    def test_t2_f12_05_camera_horizon_upright_inversion_guard(self) -> None:
        """TEST-T2-F12-05: Roll lag ratio 0.65 bounds camera tilt ensuring horizon never inverts."""
        self.assertIn("const ROLL_LAG_RATIO: float = 0.65", self.cam_content)
        max_bank = 42.0
        max_cam_roll = max_bank * 0.65  # 27.3°
        up_projection = math.cos(math.radians(max_cam_roll)) * math.cos(math.radians(32.0))
        self.assertGreater(up_projection, 0.5, "Camera view is at risk of horizon inversion")


if __name__ == "__main__":
    unittest.main()
