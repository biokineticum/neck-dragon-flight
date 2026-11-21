"""e2e_tests/tier1/test_t1_f18_smoke.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 18:
Headless Smoke Test Battery (Master runner, flight physics smoke, collision physics smoke, mock input smoke, summary reporting).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature18Smoke(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for programmatic smoke test harness."""

    def setUp(self) -> None:
        super().setUp()
        self.flight_test_path = PROJECT_ROOT / "test" / "test_flight_physics.gd"
        self.assertTrue(self.flight_test_path.is_file(), f"test_flight_physics.gd missing at {self.flight_test_path}")

    @unittest.skipUnless((PROJECT_ROOT / "test" / "run_all_tests.gd").is_file(), "test/run_all_tests.gd not yet created by builder milestone")
    def test_t1_f18_01_master_smoke_test_runner_invocation(self) -> None:
        """TEST-T1-F18-01: Master smoke test runner executes headless and exits with code 0."""
        runner = self.create_godot_runner(script_path="test/run_all_tests.gd", start_now=True)
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)

    def test_t1_f18_02_flight_physics_smoke_test(self) -> None:
        """TEST-T1-F18-02: Flight physics headless test suite executes and passes with code 0."""
        runner = self.create_godot_runner(script_path="test/test_flight_physics.gd", start_now=True)
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertIn("ALL FLIGHT PHYSICS TESTS PASSED", "".join(runner.all_logs))

    @unittest.skipUnless((PROJECT_ROOT / "test" / "test_collision.gd").is_file(), "test/test_collision.gd not yet created by builder milestone")
    def test_t1_f18_03_collision_physics_smoke_test(self) -> None:
        """TEST-T1-F18-03: Collision physics headless test executes and passes with code 0."""
        runner = self.create_godot_runner(script_path="test/test_collision.gd", start_now=True)
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)

    @unittest.skipUnless((PROJECT_ROOT / "test" / "test_input_mock.gd").is_file(), "test/test_input_mock.gd not yet created by builder milestone")
    def test_t1_f18_04_mock_input_smoke_test(self) -> None:
        """TEST-T1-F18-04: Mock input headless test executes and passes with code 0."""
        runner = self.create_godot_runner(script_path="test/test_input_mock.gd", start_now=True)
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)

    @unittest.skipUnless((PROJECT_ROOT / "test" / "run_all_tests.gd").is_file(), "test/run_all_tests.gd not yet created by builder milestone")
    def test_t1_f18_05_smoke_test_summary_reporting(self) -> None:
        """TEST-T1-F18-05: Master smoke battery logs aggregate summary report upon completion."""
        runner = self.create_godot_runner(script_path="test/run_all_tests.gd", start_now=True)
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        logs = "".join(runner.all_logs)
        self.assertTrue("passed" in logs.lower() and "failed" in logs.lower())


if __name__ == "__main__":
    unittest.main()
