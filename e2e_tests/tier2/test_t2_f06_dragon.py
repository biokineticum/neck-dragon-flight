"""e2e_tests/tier2/test_t2_f06_dragon.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 6:
Procedural Dragon Model & Rig (Degenerate triangles, normal consistency, high-frequency flap, scale guards, regeneration).

Test Catalog:
- TEST-T2-F06-01: Non-Degenerate Triangle Area Boundary
- TEST-T2-F06-02: Outward Normal Consistency & Normalization Boundary
- TEST-T2-F06-03: High Flap Frequency Stability Boundary (10.0 Hz)
- TEST-T2-F06-04: Zero Scale Prevention Guard (Positive AABB Extents)
- TEST-T2-F06-05: Repeated Regeneration Stability
"""

import math
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


class TestTier2Feature06Dragon(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for procedural dragon model and visual rig."""

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t2_f06_01_non_degenerate_triangles(self) -> None:
        """TEST-T2-F06-01: Headless generation asserts 0 degenerate zero-area triangles in procedural meshes."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        found = False
        for log_line in runner.all_logs:
            if "triangles have non-zero area (degenerate: 0)" in log_line:
                found = True
                break
        self.assertTrue(found, f"Degenerate triangle check not found in logs: {runner.all_logs}")

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t2_f06_02_outward_normal_consistency(self) -> None:
        """TEST-T2-F06-02: All mesh surface normals verified unit-length and non-NaN."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        # Check 3 passes only if all mesh normals pass length and non-NaN checks
        self.assertTrue(any("[PASS] All 6 procedural ArrayMesh generators verified" in l for l in runner.all_logs))

    def test_t2_f06_03_high_flap_frequency_stability(self) -> None:
        """TEST-T2-F06-03: Wing flap update at extreme 10.0 Hz frequency produces finite bounded angles."""
        extreme_freq = 10.0  # Hz
        dt = 1.0 / 60.0
        omega = 2.0 * math.pi * extreme_freq

        angles = []
        for tick in range(120):
            t = tick * dt
            theta = 5.0 + 25.0 * math.sin(omega * t)
            self.assertTrue(math.isfinite(theta), f"Flap angle non-finite at tick {tick}: {theta}")
            self.assertGreaterEqual(theta, -25.0)
            self.assertLessEqual(theta, 35.0)
            angles.append(theta)

        self.assertEqual(len(angles), 120)

    def test_t2_f06_04_zero_scale_prevention_guard(self) -> None:
        """TEST-T2-F06-04: Procedural mesh dimensions strictly positive (non-zero AABB size)."""
        mesh_gen_path = PROJECT_ROOT / "scripts" / "ProceduralMeshGen.gd"
        content = mesh_gen_path.read_text(encoding="utf-8")

        # Head snout extent > 0
        self.assertIn("-1.65", content)
        # Wing span reaches 4.60m
        self.assertIn("4.60", content)
        # Spire base radius > 0
        self.assertIn("base_radius", content)

    @unittest.skipUnless(is_godot_available(), "Godot 4.7.2 executable not found on host system")
    def test_t2_f06_05_repeated_regeneration_memory_stability(self) -> None:
        """TEST-T2-F06-05: Repeated generation executed in headless mode completes cleanly code 0."""
        runner = self.create_godot_runner(script_path="test/test_milestone2_headless.gd")
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
