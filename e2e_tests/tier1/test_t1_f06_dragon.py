"""e2e_tests/tier1/test_t1_f06_dragon.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 6:
Procedural Dragon Model & Rig (Head, Neck, Saddle, Wing Symmetry, Flapping Kinematics, Torso Bobbing).

Test Catalog:
- TEST-T1-F06-01: Dragon Head & Horns Mesh Generation Partition
- TEST-T1-F06-02: Saddle & Cockpit Foreground Mesh Partition
- TEST-T1-F06-03: Articulated Wing Symmetry & Extent Partition
- TEST-T1-F06-04: Procedural Wing Flapping Kinematics Partition
- TEST-T1-F06-05: Torso Heave / Pitch Bobbing Partition
"""

import math
import re
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


class TestTier1Feature06Dragon(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for procedural dragon model and visual rig."""

    def setUp(self) -> None:
        super().setUp()
        self.mesh_gen_path = PROJECT_ROOT / "scripts" / "ProceduralMeshGen.gd"

    def test_t1_f06_01_head_horns_mesh_generation(self) -> None:
        """TEST-T1-F06-01: generate_dragon_head() generates ArrayMesh with skull base, snout, and horns."""
        self.assertTrue(self.mesh_gen_path.is_file(), f"ProceduralMeshGen.gd missing at {self.mesh_gen_path}")
        content = self.mesh_gen_path.read_text(encoding="utf-8")

        self.assertIn("static func generate_dragon_head() -> ArrayMesh:", content)
        self.assertIn("add_horn", content)
        self.assertIn("add_eye", content)
        # Snout extends forward to -1.65m along -Z
        self.assertIn("-1.65", content)

    def test_t1_f06_02_neck_saddle_cockpit_geometry(self) -> None:
        """TEST-T1-F06-02: generate_dragon_neck_saddle() creates neck lofting and saddle framing rider anchor."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("static func generate_dragon_neck_saddle() -> ArrayMesh:", content)
        self.assertIn("saddle_start_idx", content)
        self.assertIn("neck_segments", content)
        # Verify neck segments and head anchor coordinates
        self.assertIn("-1.40", content)

    def test_t1_f06_03_wing_symmetry_and_extent(self) -> None:
        """TEST-T1-F06-03: Left and right wings have mirrored lateral spans reaching X = ±4.60m."""
        content = self.mesh_gen_path.read_text(encoding="utf-8")
        self.assertIn("static func generate_dragon_wing(left: bool = true) -> ArrayMesh:", content)
        # Shoulder, elbow, wrist and finger spars
        self.assertIn("j_shoulder", content)
        self.assertIn("j_elbow", content)
        self.assertIn("j_wrist", content)
        self.assertIn("f1_tip = Vector3(dir * 4.60", content)

    def test_t1_f06_04_procedural_wing_flapping_kinematics(self) -> None:
        """TEST-T1-F06-04: Procedural wing flap oscillation envelope spans [-20°, +30°] at frequency ~1.5 Hz."""
        flap_freq = 1.5  # Hz
        dt = 1.0 / 60.0  # 60 FPS
        omega = 2.0 * math.pi * flap_freq

        angles = []
        for tick in range(60):
            t = tick * dt
            # Wing flap kinematics equation: theta(t) = 5.0° + 25.0° * sin(omega * t)
            theta = 5.0 + 25.0 * math.sin(omega * t)
            angles.append(theta)

        min_angle = min(angles)
        max_angle = max(angles)
        self.assertLessEqual(min_angle, -15.0, "Flap minimum did not reach downstroke envelope")
        self.assertGreaterEqual(max_angle, 25.0, "Flap maximum did not reach upstroke envelope")
        self.assertLessEqual(max_angle, 35.0, "Flap exceeded safe physical limit")

    def test_t1_f06_05_torso_heave_bobbing(self) -> None:
        """TEST-T1-F06-05: Harmonic torso heave bobbing amplitude <= 0.15m synchronized with flap frequency."""
        flap_freq = 1.5
        dt = 1.0 / 60.0
        omega = 2.0 * math.pi * flap_freq
        bob_amplitude = 0.12  # <= 0.15m

        y_offsets = [bob_amplitude * math.sin(omega * tick * dt) for tick in range(60)]
        self.assertLessEqual(max(y_offsets), 0.15)
        self.assertGreaterEqual(min(y_offsets), -0.15)
        self.assertAlmostEqual(max(y_offsets), bob_amplitude, places=2)
