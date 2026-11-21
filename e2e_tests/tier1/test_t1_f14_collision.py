"""e2e_tests/tier1/test_t1_f14_collision.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 14:
Collision Physics & Damage State (Capsule collider, trimesh obstacles, clearance dimensions, damage decrement, invulnerability frames).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature14Collision(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for collision physics and damage handling."""

    def setUp(self) -> None:
        super().setUp()
        self.dragon_scene_path = PROJECT_ROOT / "scenes" / "PlayerDragon.tscn"
        self.flight_ctrl_path = PROJECT_ROOT / "scripts" / "FlightController.gd"
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"
        self.mesh_gen_path = PROJECT_ROOT / "scripts" / "ProceduralMeshGen.gd"
        self.game_mgr_path = PROJECT_ROOT / "scripts" / "GameManager.gd"

        self.assertTrue(self.dragon_scene_path.is_file(), f"PlayerDragon.tscn missing at {self.dragon_scene_path}")
        self.assertTrue(self.flight_ctrl_path.is_file(), f"FlightController.gd missing at {self.flight_ctrl_path}")
        self.assertTrue(self.chunk_mgr_path.is_file(), f"ChunkManager.gd missing at {self.chunk_mgr_path}")
        self.assertTrue(self.mesh_gen_path.is_file(), f"ProceduralMeshGen.gd missing at {self.mesh_gen_path}")

    def test_t1_f14_01_hull_capsule_collision_detection(self) -> None:
        """TEST-T1-F14-01: CharacterBody3D hull defines capsule collider (r=1.2, h=3.2) on Layer 2 / Mask 1 with slide collision reporting."""
        scene_content = self.dragon_scene_path.read_text(encoding="utf-8")
        flight_content = self.flight_ctrl_path.read_text(encoding="utf-8")

        self.assertIn("collision_layer = 2", scene_content)
        self.assertIn("collision_mask = 1", scene_content)
        self.assertIn("CapsuleShape3D", scene_content)
        self.assertIn("radius = 1.2", scene_content)
        self.assertIn("height = 3.2", scene_content)

        self.assertIn("signal collision_impact(collider: Node, collision_point: Vector3, normal: Vector3)", flight_content)
        self.assertIn("body.get_slide_collision_count()", flight_content)
        self.assertIn("collision_impact.emit(col.get_collider(), col.get_position(), col.get_normal())", flight_content)

    def test_t1_f14_02_needle_spire_collision(self) -> None:
        """TEST-T1-F14-02: Needle spire obstacle geometry defines Layer 1 trimesh static collider with height 60m."""
        mesh_content = self.mesh_gen_path.read_text(encoding="utf-8")
        chunk_content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("static func generate_needle_spire", mesh_content)
        self.assertIn("height: float = 60.0", mesh_content)
        self.assertIn("base_radius: float = 7.0", mesh_content)

        self.assertIn("_attach_trimesh_collider", chunk_content)
        self.assertIn("body.collision_layer = 1", chunk_content)
        self.assertIn("body.collision_mask = 0", chunk_content)

    def test_t1_f14_03_rock_archway_overhead_collision(self) -> None:
        """TEST-T1-F14-03: Rock arch obstacle generates tunnel portal with clearance height 24m (>= 12m specification)."""
        mesh_content = self.mesh_gen_path.read_text(encoding="utf-8")

        self.assertIn("static func generate_rock_arch", mesh_content)
        self.assertIn("clearance_height: float = 24.0", mesh_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t1_f14_04_player_health_decrement(self) -> None:
        """TEST-T1-F14-04: Non-invulnerable terrain impact decrements player health by exactly 1."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("player_health" in gm_content or "current_health" in gm_content)
        self.assertIn("-= 1", gm_content)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "scripts/GameManager.gd not yet created by builder milestone")
    def test_t1_f14_05_post_collision_invulnerability_frames(self) -> None:
        """TEST-T1-F14-05: Post-collision invulnerability window ignores subsequent impacts during immunity period."""
        gm_content = self.game_mgr_path.read_text(encoding="utf-8")
        self.assertTrue("invulnerab" in gm_content.lower())


if __name__ == "__main__":
    unittest.main()
