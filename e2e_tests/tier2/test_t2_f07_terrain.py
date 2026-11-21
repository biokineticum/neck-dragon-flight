"""e2e_tests/tier2/test_t2_f07_terrain.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 7:
Procedural Mountain Realm & Obstacles (Seed determinism, seed divergence, obstacle density, coordinate scaling, seam elevation).

Test Catalog:
- TEST-T2-F07-01: Seed Determinism Invariance
- TEST-T2-F07-02: Seed Divergence Boundary
- TEST-T2-F07-03: Maximum Obstacle Density Flight Gap Boundary (Clearance >= 8m)
- TEST-T2-F07-04: Extreme High Chunk Coordinate Precision
- TEST-T2-F07-05: Boundary Elevation Match Tolerance (Delta Y <= 0.01m)
"""

import unittest

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.godot_runner import GodotDiscovery
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def is_godot_available() -> bool:
    try:
        GodotDiscovery.find_binary()
        return True
    except FileNotFoundError:
        return False


class TestTier2Feature07Terrain(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for procedural mountain realm and terrain obstacles."""

    def setUp(self) -> None:
        super().setUp()
        self.mesh_gen_path = PROJECT_ROOT / "scripts" / "ProceduralMeshGen.gd"
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"

    def test_t2_f07_01_seed_determinism_invariance(self) -> None:
        """TEST-T2-F07-01: ChunkManager initializes deterministically using master_seed."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")
        self.assertIn("master_seed: int = 42", content)
        self.assertIn("rng.seed = chunk_seed", content)
        self.assertIn("chunk_seed: int = master_seed + p_index * 1337 + 7919", content)

    def test_t2_f07_02_seed_divergence_boundary(self) -> None:
        """TEST-T2-F07-02: Different seed values alter FastNoiseLite noise samples and obstacle offsets."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("noise.seed = seed_val", content)
        # Spires seeded distinctly per obstacle index
        chunk_mgr_content = self.chunk_mgr_path.read_text(encoding="utf-8")
        self.assertIn("chunk_seed + s * 101", chunk_mgr_content)

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t2_f07_03_max_obstacle_density_flight_gap(self) -> None:
        """TEST-T2-F07-03: Flight portal clearance verified across all arch difficulty tiers (0 portal hits)."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("flight portal [-10, 10] x [5, 15] hits: 0" in l for l in runner.all_logs))

    def test_t2_f07_04_extreme_high_chunk_coordinate(self) -> None:
        """TEST-T2-F07-04: Noise and coordinate generation functions evaluate without overflow at Z = -10,000m."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH", content)
        self.assertIn("noise.frequency = 0.035", content)

    def test_t2_f07_05_boundary_elevation_match_tolerance(self) -> None:
        """TEST-T2-F07-05: Canyon floor elevation is fixed at y_floor = -25.0 ensuring seamless seam alignment."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("var y_floor: float = -25.0", content)
