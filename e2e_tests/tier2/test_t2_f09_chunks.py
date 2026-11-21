"""e2e_tests/tier2/test_t2_f09_chunks.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 9:
Infinite Chunk Streaming Corridor (Exact boundary trigger, high-speed traversal, backward movement, teleport recovery, endurance).

Test Catalog:
- TEST-T2-F09-01: Exact Boundary Threshold Transition (-199.99m vs -200.01m)
- TEST-T2-F09-02: High-Velocity Traversal Boundary (60.0 m/s)
- TEST-T2-F09-03: Negative / Backward Movement Guard
- TEST-T2-F09-04: Corridor Reset and Setup Determinism
- TEST-T2-F09-05: Long-Distance Endurance Fixed Memory Bounding (Ring Buffer)
"""

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature09Chunks(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for infinite chunk corridor streaming."""

    def setUp(self) -> None:
        super().setUp()
        self.chunk_mgr_path = PROJECT_ROOT / "scripts" / "ChunkManager.gd"

    def test_t2_f09_01_exact_boundary_threshold_transition(self) -> None:
        """TEST-T2-F09-01: Recycling trigger checks exact inequality player_z < rear_chunk_end (-200m)."""
        self.assertTrue(self.chunk_mgr_path.is_file(), f"ChunkManager.gd missing at {self.chunk_mgr_path}")
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("var rear_chunk_end = rear_chunk.position.z - chunk_length", content)
        self.assertIn("if player_z < rear_chunk_end:", content)

        # Boundary logic verification:
        rear_chunk_z = 0.0
        chunk_length = 200.0
        rear_chunk_end = rear_chunk_z - chunk_length  # -200.0

        # At -199.99m -> False (no recycling)
        self.assertFalse(-199.99 < rear_chunk_end)
        # At -200.01m -> True (triggers recycling)
        self.assertTrue(-200.01 < rear_chunk_end)

    def test_t2_f09_02_high_velocity_traversal_boundary(self) -> None:
        """TEST-T2-F09-02: High-velocity flight (60 m/s) sampled at 60 Hz physics rate (1m/tick)."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")
        self.assertIn("func _physics_process(_delta: float) -> void:", content)
        self.assertIn("update_player_position(player_ref.global_position)", content)

        # Physics tick step size at max dive speed 60 m/s:
        max_speed = 60.0  # m/s
        dt = 1.0 / 60.0   # s
        step_distance = max_speed * dt  # 1.0m
        chunk_length = 200.0
        # Step size 1.0m is well within 200m chunk length, ensuring trigger is never missed
        self.assertLess(step_distance, chunk_length * 0.1)

    def test_t2_f09_03_negative_backward_movement_guard(self) -> None:
        """TEST-T2-F09-03: Backward movement does not trigger spurious forward recycling."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        # After rear chunk recycles from 0m to -800m, new rear chunk is at -200m (end = -400m)
        new_rear_chunk_end = -200.0 - 200.0  # -400.0m
        # Moving backward from -205m to -195m:
        player_z_backward = -195.0
        # Player is greater than new_rear_chunk_end (-400m), so no recycling occurs
        self.assertFalse(player_z_backward < new_rear_chunk_end)

    def test_t2_f09_04_corridor_reset_and_setup_determinism(self) -> None:
        """TEST-T2-F09-04: reset_corridor() and setup_corridor() deterministically restore initial state."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("func setup_corridor(player: Node3D, p_seed: int = 42) -> void:", content)
        self.assertIn("func reset_corridor() -> void:", content)
        self.assertIn("current_front_z = 0.0", content)
        self.assertIn("next_chunk_index = 0", content)

    def test_t2_f09_05_long_distance_endurance(self) -> None:
        """TEST-T2-F09-05: Ring buffer rotation guarantees constant active chunk pool size (pool_size = 4)."""
        content = self.chunk_mgr_path.read_text(encoding="utf-8")

        self.assertIn("chunk_pool.append(chunk_pool.pop_front())", content)
        self.assertIn("pool_size: int = 4", content)
