"""e2e_tests/tier1/test_t1_f04_mock.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 4:
Synthetic Mock Input Feeder (CLI profiles, neutral, sine wave, step, lifecycle).

Test Catalog:
- TEST-T1-F04-01: CLI Profile Parameter Parsing Partition
- TEST-T1-F04-02: Neutral Trajectory Injection Partition
- TEST-T1-F04-03: Sinusoidal Oscillation Injection Partition
- TEST-T1-F04-04: Step Profile Injection Partition (Dive Profile)
- TEST-T1-F04-05: Background Feeder Lifecycle Partition
"""

from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.mock_tracker import MockTracker


class TestTier1Feature04Mock(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for mock tracker subsystem."""

    def test_t1_f04_01_cli_parameter_parsing(self) -> None:
        """TEST-T1-F04-01: CLI command python tracker/mock_tracker.py starts, parses args, and exits 0."""
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--mode", "neutral", "--duration", "0.5", "--frequency", "30"],
            start_now=True,
        )
        exit_code = tracker_runner.wait_for_exit(timeout=5.0)
        self.assertEqual(exit_code, 0, f"Mock tracker CLI failed with exit code {exit_code}")

    def test_t1_f04_02_neutral_trajectory_injection(self) -> None:
        """TEST-T1-F04-02: Neutral mode produces pitch=0.0, yaw=0.0, roll=0.0, tracking=True."""
        capture = self.create_capture()
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--mode", "neutral", "--duration", "1.0", "--frequency", "30"],
            start_now=True,
        )
        packets = capture.collect_packets(count=5, timeout=3.0)
        self.assertGreaterEqual(len(packets), 5, "Did not receive sufficient packets from neutral profile")
        for p in packets:
            self.assertAlmostEqual(p.pitch, 0.0, delta=0.01)
            self.assertAlmostEqual(p.yaw, 0.0, delta=0.01)
            self.assertAlmostEqual(p.roll, 0.0, delta=0.01)
            self.assertTrue(p.tracking)
            self.assertTrue(p.calibrated)
        tracker_runner.wait_for_exit(timeout=3.0)

    def test_t1_f04_03_sinusoidal_oscillation_injection(self) -> None:
        """TEST-T1-F04-03: Sine wave profile produces periodic oscillating pitch/roll spanning positive and negative."""
        capture = self.create_capture()
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--mode", "sine_wave", "--duration", "2.0", "--frequency", "30", "--amplitude", "20.0", "--period", "0.5"],
            start_now=True,
        )
        packets = capture.collect_packets(count=20, timeout=4.0)
        self.assertGreaterEqual(len(packets), 10, "Did not receive sufficient sine wave packets")
        pitches = [p.pitch for p in packets if p.pitch is not None]
        self.assertGreater(max(pitches), 5.0, "Sine wave peak did not reach expected positive amplitude")
        self.assertLess(min(pitches), -5.0, "Sine wave trough did not reach expected negative amplitude")
        tracker_runner.wait_for_exit(timeout=3.0)

    def test_t1_f04_04_step_profile_injection(self) -> None:
        """TEST-T1-F04-04: Dive profile produces sustained pitch = -20.0° for duration."""
        capture = self.create_capture()
        tracker_runner = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--mode", "dive", "--duration", "1.0", "--frequency", "30", "--amplitude", "20.0"],
            start_now=True,
        )
        packets = capture.collect_packets(count=10, timeout=3.0)
        self.assertGreaterEqual(len(packets), 5)
        for p in packets:
            self.assertAlmostEqual(p.pitch, -20.0, delta=0.5)
        tracker_runner.wait_for_exit(timeout=3.0)

    def test_t1_f04_05_background_feeder_lifecycle(self) -> None:
        """TEST-T1-F04-05: MockTracker background thread starts, emits datagrams, and cleanly terminates on stop()."""
        capture = self.create_capture()
        tracker = MockTracker(host="127.0.0.1", port=42425, frequency=30.0)
        self.register_cleanup(tracker.close)

        thread = tracker.start_background(mode="climb", duration=0.8, amplitude=15.0)
        self.assertTrue(thread.is_alive())

        packets = capture.collect_packets(count=5, timeout=2.0)
        self.assertGreaterEqual(len(packets), 5)
        for p in packets:
            self.assertAlmostEqual(p.pitch, 15.0, delta=0.5)

        tracker.stop()
        self.assertFalse(thread.is_alive(), "MockTracker thread did not shut down on stop()")
