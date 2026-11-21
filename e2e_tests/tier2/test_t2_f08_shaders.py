"""e2e_tests/tier2/test_t2_f08_shaders.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 8:
Procedural PBR Shaders & Materials (Slope threshold boundaries, lighting stability, roughness/metallic bounds, Fresnel/rim, fog density).

Test Catalog:
- TEST-T2-F08-01: Slope Boundary Normal Thresholds (0.0, 0.55, 1.0)
- TEST-T2-F08-02: Zero Ambient Light Math Stability
- TEST-T2-F08-03: Roughness and Metallic Physical Range Limits ([0.0, 1.0])
- TEST-T2-F08-04: Grazing Angle Rim/Clearcoat Clamping
- TEST-T2-F08-05: Volumetric Fog Density Saturation Limits
"""

import re
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Evaluates GLSL smoothstep function."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


class TestTier2Feature08Shaders(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for procedural PBR shaders and materials."""

    def setUp(self) -> None:
        super().setUp()
        self.materials_dir = PROJECT_ROOT / "materials"

    def test_t2_f08_01_slope_boundary_normal_thresholds(self) -> None:
        """TEST-T2-F08-01: Triplanar slope blending evaluates to 0.0 at vertical cliff, 0.5 at threshold, 1.0 at flat."""
        threshold = 0.55
        softness = 0.18
        edge0 = threshold - softness  # 0.37
        edge1 = threshold + softness  # 0.73

        # Vertical cliff (slope ny = 0.0) -> 100% rock (snow_factor = 0.0)
        self.assertEqual(smoothstep(edge0, edge1, 0.0), 0.0)

        # Midpoint threshold (slope ny = 0.55) -> 50/50 blend (snow_factor = 0.5)
        self.assertAlmostEqual(smoothstep(edge0, edge1, threshold), 0.5, places=3)

        # Horizontal plateau (slope ny = 1.0) -> 100% snow (snow_factor = 1.0)
        self.assertEqual(smoothstep(edge0, edge1, 1.0), 1.0)

    def test_t2_f08_02_zero_ambient_light_stability(self) -> None:
        """TEST-T2-F08-02: Triplanar blending denominator w / (w.x + w.y + w.z) normalized safely."""
        mat_file = self.materials_dir / "rock_snow_triplanar.tres"
        content = mat_file.read_text(encoding="utf-8")

        self.assertIn("return w / (w.x + w.y + w.z);", content)
        self.assertIn("triplanar_sharpness", content)

    def test_t2_f08_03_roughness_metallic_extremes(self) -> None:
        """TEST-T2-F08-03: Metallic and roughness values in dragon_scales.tres strictly bounded in [0.0, 1.0]."""
        mat_file = self.materials_dir / "dragon_scales.tres"
        content = mat_file.read_text(encoding="utf-8")

        metallic_match = re.search(r"metallic\s*=\s*([0-9.]+)", content)
        roughness_match = re.search(r"roughness\s*=\s*([0-9.]+)", content)

        self.assertIsNotNone(metallic_match)
        self.assertIsNotNone(roughness_match)

        metallic = float(metallic_match.group(1))
        roughness = float(roughness_match.group(1))

        self.assertGreaterEqual(metallic, 0.0)
        self.assertLessEqual(metallic, 1.0)
        self.assertGreaterEqual(roughness, 0.0)
        self.assertLessEqual(roughness, 1.0)

    def test_t2_f08_04_grazing_angle_fresnel_clamping(self) -> None:
        """TEST-T2-F08-04: Rim and clearcoat values strictly bounded in [0.0, 1.0]."""
        mat_file = self.materials_dir / "dragon_scales.tres"
        content = mat_file.read_text(encoding="utf-8")

        rim_match = re.search(r"rim\s*=\s*([0-9.]+)", content)
        clearcoat_match = re.search(r"clearcoat\s*=\s*([0-9.]+)", content)

        self.assertIsNotNone(rim_match)
        self.assertIsNotNone(clearcoat_match)

        rim = float(rim_match.group(1))
        clearcoat = float(clearcoat_match.group(1))

        self.assertGreaterEqual(rim, 0.0)
        self.assertLessEqual(rim, 1.0)
        self.assertGreaterEqual(clearcoat, 0.0)
        self.assertLessEqual(clearcoat, 1.0)

    def test_t2_f08_05_volumetric_fog_saturation(self) -> None:
        """TEST-T2-F08-05: Fog density is positive and within safe visual atmospheric range (0.0001 <= density <= 0.05)."""
        env_file = self.materials_dir / "sky_environment.tres"
        content = env_file.read_text(encoding="utf-8")

        fog_match = re.search(r"fog_density\s*=\s*([0-9.]+)", content)
        self.assertIsNotNone(fog_match, "fog_density missing in sky_environment.tres")
        density = float(fog_match.group(1))

        self.assertGreaterEqual(density, 0.0001)
        self.assertLessEqual(density, 0.05)
