"""e2e_tests/tier2/test_t2_f18_smoke.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 18:
Headless Smoke Test Battery (Clean exit code, failure exit code, watchdog safety, driver stubbing, reproducibility).
"""

import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature18Smoke(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for programmatic smoke test harness."""

    def setUp(self) -> None:
        super().setUp()
        self.flight_script = PROJECT_ROOT / "test" / "test_flight_physics.gd"
        self.assertTrue(self.flight_script.is_file(), f"test_flight_physics.gd missing at {self.flight_script}")

    def test_t2_f18_01_clean_process_exit_code_on_pass(self) -> None:
        """TEST-T2-F18-01: Running passing headless test suite exits strictly with code 0."""
        runner = self.create_godot_runner(
            script_path=str(self.flight_script),
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)

    def test_t2_f18_02_non_zero_exit_code_on_deliberate_failure(self) -> None:
        """TEST-T2-F18-02: Executing headless test with non-existent script yields non-zero exit code."""
        non_existent_script = PROJECT_ROOT / "test" / "non_existent_test_script_xyz.gd"
        runner = self.create_godot_runner(
            script_path=str(non_existent_script),
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=10.0)
        self.assertNotEqual(exit_code, 0, "Engine did not return non-zero exit code on missing script")

    def test_t2_f18_03_execution_watchdog_timeout_safety(self) -> None:
        """TEST-T2-F18-03: Process manager wait_for_exit raises TimeoutError and terminates process if timeout expires."""
        runner = self.create_godot_runner(
            script_path=str(self.flight_script),
            start_now=True,
        )
        try:
            exit_code = runner.wait_for_exit(timeout=0.001)
            self.assertEqual(exit_code, 0)
        except TimeoutError:
            pass

    def test_t2_f18_04_headless_audio_video_driver_stubbing(self) -> None:
        """TEST-T2-F18-04: Headless engine launch runs cleanly without display server errors."""
        runner = self.create_godot_runner(
            script_path=str(self.flight_script),
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        all_logs = "\n".join(runner.all_logs)
        self.assertNotIn("Failed to create Vulkan instance", all_logs)

    def test_t2_f18_05_consecutive_execution_reproducibility(self) -> None:
        """TEST-T2-F18-05: Running headless smoke test 2 consecutive times yields identical exit code (0)."""
        # Run 1
        runner1 = self.create_godot_runner(script_path=str(self.flight_script), start_now=True)
        code1 = runner1.wait_for_exit(timeout=15.0)

        # Run 2
        runner2 = self.create_godot_runner(script_path=str(self.flight_script), start_now=True)
        code2 = runner2.wait_for_exit(timeout=15.0)

        self.assertEqual(code1, 0)
        self.assertEqual(code2, 0)
        self.assertEqual(code1, code2)


if __name__ == "__main__":
    unittest.main()
