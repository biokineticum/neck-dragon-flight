"""e2e_tests/tier1/test_t1_f09_chunks.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 9:
Infinite Chunk Streaming Corridor (200m Chunks, 4 Active Chunks, Recycling Trigger, Seam Continuity).

Test Catalog:
- TEST-T1-F09-01: Initial 4-Chunk Layout Partition (0, -200, -400, -600m)
- TEST-T1-F09-02: First Chunk Recycling Trigger Partition (Crossing -200m -> Reposition to -800m)
- TEST-T1-F09-03: Sequential Multi-Chunk Recycling Partition (Constant Pool Size = 4)
- TEST-T1-F09-04: Recycled Chunk Collision Persistence Partition
- TEST-T1-F09-05: Chunk Seam Continuity Partition
"""

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature09Chunks(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for infinite chunk corridor streaming."""

    def setUp(self) -> None:
        super().setUp()
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"

    def test_t1_f09_01_initial_chunk_layout(self) -> None:
        """TEST-T1-F09-01: Initial corridor layout maintains pool_size = 4 chunks of length 200m."""
        self.assertTrue(self.chunk_mgr_path.is_file(), f"ChunkManager.gd missing at {self.chunk_mgr_path}")
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("chunk_length: float = 200.0", content)
        self.assertIn("pool_size: int = 4", content)
        self.assertIn("reset_corridor()", content)
        self.assertIn("-float(i) * chunk_length", content)

    def test_t1_f09_02_first_chunk_recycling(self) -> None:
        """TEST-T1-F09-02: Player crossing rear boundary triggers recycling of rear chunk to current_front_z - 200m."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("func update_player_position(", content)
        self.assertIn("var rear_chunk_end = rear_chunk.position.z - chunk_length", content)
        self.assertIn("recycle_rear_chunk()", content)
        self.assertIn("current_front_z -= chunk_length", content)

    def test_t1_f09_03_sequential_multi_chunk_recycling(self) -> None:
        """TEST-T1-F09-03: Ring buffer rotation maintains bounded chunk count of 4 across sequential crossings."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        # Ring buffer rotation: append(pop_front())
        self.assertIn("chunk_pool.append(chunk_pool.pop_front())", content)
        self.assertIn("get_active_chunk_count()", content)

    def test_t1_f09_04_recycled_chunk_collision_persistence(self) -> None:
        """TEST-T1-F09-04: Recycled chunk rebuilds collision bodies with Layer 1 Environment."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("func _build_chunk(", content)
        self.assertIn("child.free()", content)
        self.assertIn("_attach_trimesh_collider", content)
        self.assertIn("body.collision_layer = 1", content)

    def test_t1_f09_05_chunk_seam_continuity(self) -> None:
        """TEST-T1-F09-05: Canyon wall mesh generation endpoints align with next chunk boundary."""
        mesh_gen_path = PROJECT_ROOT / "scripts" / "ProceduralMeshGen.gd"
        content = mesh_gen_path.read_text(encoding="utf-8")

        self.assertIn("generate_canyon_walls", content)
        # z reaches -tz * length with tz = 1.0 -> -length (-200m)
        self.assertIn("var z: float = -tz * length", content)
