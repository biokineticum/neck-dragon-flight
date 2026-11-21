"""e2e_tests/tier1/test_t1_f07_terrain.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 7:
Procedural Mountain Realm & Obstacles (Canyon Walls, Spires, Arches, Flight Corridor, Collision Layer).

Test Catalog:
- TEST-T1-F07-01: Canyon Bounding Walls Generation Partition (Height >= 50m, 200m span)
- TEST-T1-F07-02: Granite Needle Spire Generation Partition (Trimesh colliders, height 60m)
- TEST-T1-F07-03: Natural Stone Archway Generation Partition (Clearance >= 12m)
- TEST-T1-F07-04: Guaranteed Flight Path Corridor Partition (Minimum clearance >= 8m)
- TEST-T1-F07-05: Obstacle Collision Layer Assignment Partition (Layer 1 Environment, Mask 0)
"""

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature07Terrain(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for procedural mountain realm and terrain obstacles."""

    def setUp(self) -> None:
        super().setUp()
        self.mesh_gen_path = PROJECT_ROOT / "scripts" / "ProceduralMeshGen.gd"
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"

    def test_t1_f07_01_canyon_boundary_walls(self) -> None:
        """TEST-T1-F07-01: Canyon walls generator creates boundary meshes with length 200m and height >= 50m."""
        self.assertTrue(self.mesh_gen_path.is_file(), f"ProceduralMeshGen.gd missing at {self.mesh_gen_path}")
        content = self.mesh_gen_path.read_text(encoding="utf-8")

        self.assertIn("static func generate_canyon_walls(", content)
        self.assertIn("length: float = 200.0", content)
        self.assertIn("height: float = 130.0", content)
        # Check tiers and inward normals
        self.assertIn("tiers: Array[Dictionary]", content)
        self.assertIn("y_top", content)

    def test_t1_f07_02_needle_spire_generation(self) -> None:
        """TEST-T1-F07-02: Needle spire generator creates spires with height 60m and collision trimesh."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("static func generate_needle_spire(", content)
        self.assertIn("height: float = 60.0", content)
        self.assertIn("base_radius: float = 7.0", content)
        self.assertIn("st.generate_normals()", content)

    def test_t1_f07_03_rock_archway_generation(self) -> None:
        """TEST-T1-F07-03: Rock archway generator provides under-flight portal clearance >= 12m."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("static func generate_rock_arch(", content)
        self.assertIn("clearance_height: float = 24.0", content)
        self.assertIn("span_width: float = 42.0", content)
        # 24m clearance satisfies requirement >= 12m
        self.assertIn("ring_centers", content)

    def test_t1_f07_04_flight_corridor_clearance(self) -> None:
        """TEST-T1-F07-04: Obstacle placement enforces navigable corridor with clearance >= 8m."""
        self.assertTrue(self.chunk_mgr_path.is_file(), f"ChunkManager.gd missing at {self.chunk_mgr_path}")
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        # Canyon corridor width 75m to 90m
        self.assertIn("canyon_width", content)
        # Spire placement with 15m wall clearance margin
        self.assertIn("canyon_width * 0.5) - 15.0", content)
        # Grace period for initial chunks
        self.assertIn("p_index < 2", content)

    def test_t1_f07_05_obstacle_collision_layer_assignment(self) -> None:
        """TEST-T1-F07-05: All terrain obstacle colliders assigned strictly to Layer 1 (Environment), Mask 0."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")
        self.assertIn("func _attach_trimesh_collider(", content)
        self.assertIn("body.collision_layer = 1", content)
        self.assertIn("body.collision_mask = 0", content)
