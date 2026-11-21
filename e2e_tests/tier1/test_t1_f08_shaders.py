"""e2e_tests/tier1/test_t1_f08_shaders.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 8:
Procedural PBR Shaders & Materials (Triplanar, Dragon Scales, Sky Environment, Headless Loading).

Test Catalog:
- TEST-T1-F08-01: Triplanar Rock/Snow Shader Resource Partition
- TEST-T1-F08-02: Triplanar Slope Angle Blending Partition
- TEST-T1-F08-03: Dragon Scale Iridescent Material Partition
- TEST-T1-F08-04: Procedural Sky & Alpine Fog Resource Partition
- TEST-T1-F08-05: Headless Material Loading Stability Partition
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.godot_runner import GodotDiscovery
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def is_godot_available() -> bool:
    try:
        GodotDiscovery.find_binary()
        return True
    except FileNotFoundError:
        return False


class TestTier1Feature08Shaders(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for procedural PBR shaders and materials."""

    def setUp(self) -> None:
        super().setUp()
        self.materials_dir = PROJECT_ROOT / "materials"

    def test_t1_f08_01_triplanar_rock_snow_material(self) -> None:
        """TEST-T1-F08-01: rock_snow_triplanar.tres exists and defines valid ShaderMaterial resource."""
        mat_file = self.materials_dir / "rock_snow_triplanar.tres"
        self.assertTrue(mat_file.is_file(), f"Missing {mat_file}")
        content = mat_file.read_text(encoding="utf-8")

        self.assertIn('type="ShaderMaterial"', content)
        self.assertIn("shader_type spatial;", content)
        self.assertIn("rock_color", content)
        self.assertIn("snow_color", content)

    def test_t1_f08_02_triplanar_slope_blending(self) -> None:
        """TEST-T1-F08-02: Shader code defines slope angle blend thresholds for rock vs snow transition."""
        mat_file = self.materials_dir / "rock_snow_triplanar.tres"
        content = mat_file.read_text(encoding="utf-8")

        self.assertIn("snow_slope_threshold", content)
        self.assertIn("snow_slope_softness", content)
        self.assertIn("triplanar_sharpness", content)
        # Verify smoothstep slope mixing based on world normal
        self.assertIn("smoothstep", content)

    def test_t1_f08_03_dragon_scales_pbr_material(self) -> None:
        """TEST-T1-F08-03: dragon_scales.tres defines StandardMaterial3D with metallic, roughness, rim, clearcoat."""
        mat_file = self.materials_dir / "dragon_scales.tres"
        self.assertTrue(mat_file.is_file(), f"Missing {mat_file}")
        content = mat_file.read_text(encoding="utf-8")

        self.assertIn('type="StandardMaterial3D"', content)
        self.assertIn("metallic = 0.25", content)
        self.assertIn("roughness = 0.3", content)
        self.assertIn("rim_enabled = true", content)
        self.assertIn("clearcoat_enabled = true", content)

    def test_t1_f08_04_sky_environment_resource(self) -> None:
        """TEST-T1-F08-04: sky_environment.tres defines Environment with ProceduralSkyMaterial and fog."""
        env_file = self.materials_dir / "sky_environment.tres"
        self.assertTrue(env_file.is_file(), f"Missing {env_file}")
        content = env_file.read_text(encoding="utf-8")

        self.assertIn('type="Environment"', content)
        self.assertIn("ProceduralSkyMaterial", content)
        self.assertIn("fog_enabled = true", content)
        self.assertIn("fog_density", content)

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t1_f08_05_headless_material_loading_stability(self) -> None:
        """TEST-T1-F08-05: All 3 material resources load without GPU shader errors in headless mode."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, f"Headless execution failed: {runner.all_logs}")
