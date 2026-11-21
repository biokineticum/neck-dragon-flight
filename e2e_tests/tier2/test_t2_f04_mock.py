"""e2e_tests/tier2/test_t2_f04_mock.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 4:
Synthetic Mock Input Feeder (Zero duration, fractional duration, invalid modes, port bounds).

Test Catalog:
- TEST-T2-F04-01: Zero/Near-Zero Duration Execution
- TEST-T2-F04-02: Fractional High-Precision Duration (--duration 0.2)
- TEST-T2-F04-03: Invalid Profile Mode Name Handling (Argparse rejection)
- TEST-T2-F04-04: Custom Port Upper Boundary (--port 65535)
- TEST-T2-F04-05: Port Out-of-Range Rejection (--port 70000)
"""

from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature04Mock(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for synthetic mock input feeder."""

    def test_t2_f04_01_zero_duration_execution(self) -> None:
        """TEST-T2-F04-01: Near-zero duration execution terminates immediately with code 0."""
        capture = self.create_capture()
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--duration", "0.0001", "--frequency", "30"],
            start_now=True,
        )
        exit_code = tracker_runner.wait_for_exit(timeout=3.0)
        self.assertEqual(exit_code, 0)
        self.assertLessEqual(capture.total_received, 1)

    def test_t2_f04_02_fractional_precision_duration(self) -> None:
        """TEST-T2-F04-02: CLI with --frequency 30 --duration 0.2 transmits 6 ± 2 packets and exits cleanly."""
        capture = self.create_capture()
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--duration", "0.2", "--frequency", "30"],
            start_now=True,
        )
        exit_code = tracker_runner.wait_for_exit(timeout=3.0)
        self.assertEqual(exit_code, 0)
        count = capture.total_received
        self.assertGreaterEqual(count, 4, f"Collected only {count} packets (expected >= 4)")
        self.assertLessEqual(count, 8, f"Collected {count} packets (expected <= 8)")

    def test_t2_f04_03_invalid_profile_name_handling(self) -> None:
        """TEST-T2-F04-03: Invalid profile mode name causes process to reject arguments and exit non-zero."""
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--mode", "nonexistent_mode_xyz"],
            start_now=True,
        )
        exit_code = tracker_runner.wait_for_exit(timeout=3.0)
        self.assertNotEqual(exit_code, 0, "Mock tracker should exit non-zero on invalid mode")

    def test_t2_f04_04_custom_port_upper_boundary(self) -> None:
        """TEST-T2-F04-04: Mock tracker accepts valid upper 16-bit port boundary 65535."""
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--port", "65535", "--duration", "0.2"],
            start_now=True,
        )
        exit_code = tracker_runner.wait_for_exit(timeout=3.0)
        self.assertEqual(exit_code, 0, f"Failed on port 65535: exit code {exit_code}")

    def test_t2_f04_05_port_out_of_range_rejection(self) -> None:
        """TEST-T2-F04-05: Mock tracker with out-of-range port 70000 exits non-zero."""
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--port", "70000", "--duration", "0.2"],
            start_now=True,
        )
        exit_code = tracker_runner.wait_for_exit(timeout=3.0)
        self.assertNotEqual(exit_code, 0, "Mock tracker accepted out-of-range port 70000")
