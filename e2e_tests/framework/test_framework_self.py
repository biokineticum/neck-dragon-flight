"""Framework self-test verification suite.

Proves that:
1. MockUdpBroadcaster and UdpTelemetryCapture communicate cleanly over 127.0.0.1:42425.
2. Custom assertions catch both valid states and invalid/adversarial mutations.
3. FallbackInputSimulator exports valid JSON input traces.
4. GodotDiscovery locates the Godot 4.7.2 console binary and GodotProcessManager captures stdout.
"""

import json
import math
import tempfile
import time
from pathlib import Path

from e2e_tests.framework.assertions import (
    assert_angle_in_bounds,
    assert_control_mode,
    assert_deadzone_applied,
    assert_decay_rate,
    assert_jitter_suppressed,
    assert_packet_rate,
    assert_packet_schema,
    assert_state_transition,
    assert_vector_close,
)
from e2e_tests.framework.config import (
    CHUNK_LENGTH_METERS,
    CRUISE_SPEED_MPS,
    DEFAULT_GODOT_CONSOLE_PATH,
    MAX_BANK_ANGLE_DEG,
    MAX_DIVE_SPEED_MPS,
    MAX_PITCH_ANGLE_DEG,
    MIN_CLIMB_SPEED_MPS,
    PACKET_TIMEOUT_SEC,
    PROJECT_ROOT,
    UDP_HOST,
    UDP_PORT,
)
from e2e_tests.framework.godot_runner import GodotDiscovery, GodotProcessManager
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from e2e_tests.framework.tracker_runner import TrackerProcessManager
from e2e_tests.framework.udp_fixture import (
    CapturedPacket,
    FallbackInputSimulator,
    MockUdpBroadcaster,
    TelemetryPacket,
    UdpTelemetryCapture,
)


class TestConfig(OpaqueBoxTestCase):
    """Verifies environment configuration and physical constraint constants."""

    def test_network_and_physics_constants(self):
        self.assertEqual(UDP_HOST, "127.0.0.1")
        self.assertEqual(UDP_PORT, 42425)
        self.assertEqual(PACKET_TIMEOUT_SEC, 0.50)

        # Physics limits
        self.assertEqual(CRUISE_SPEED_MPS, 30.0)
        self.assertEqual(MAX_DIVE_SPEED_MPS, 54.0)
        self.assertEqual(MIN_CLIMB_SPEED_MPS, 18.0)
        self.assertEqual(MAX_BANK_ANGLE_DEG, 42.0)
        self.assertEqual(MAX_PITCH_ANGLE_DEG, 32.0)
        self.assertEqual(CHUNK_LENGTH_METERS, 200.0)

    def test_project_root_exists(self):
        self.assertTrue(PROJECT_ROOT.exists(), f"PROJECT_ROOT does not exist: {PROJECT_ROOT}")


class TestAssertions(OpaqueBoxTestCase):
    """Verifies domain assertions against valid and invalid inputs."""

    def test_packet_schema_valid_and_invalid(self):
        valid = {
            "pitch": 10.5,
            "yaw": -5.0,
            "roll": 2.0,
            "calibrated": True,
            "tracking": True,
            "timestamp": time.time(),
        }
        # Should not raise
        assert_packet_schema(valid)

        # Missing key
        invalid_missing = dict(valid)
        del invalid_missing["pitch"]
        with self.assertRaises(AssertionError):
            assert_packet_schema(invalid_missing)

        # Non-numeric pitch
        invalid_type = dict(valid, pitch="not_a_number")
        with self.assertRaises(AssertionError):
            assert_packet_schema(invalid_type)

        # NaN pitch
        invalid_nan = dict(valid, pitch=float("nan"))
        with self.assertRaises(AssertionError):
            assert_packet_schema(invalid_nan)

        # Non-bool tracking
        invalid_tracking = dict(valid, tracking="yes")
        with self.assertRaises(AssertionError):
            assert_packet_schema(invalid_tracking)

        # Bool pitch (Python bool inherits from int, must be rejected)
        invalid_bool_pitch = dict(valid, pitch=True)
        with self.assertRaises(AssertionError):
            assert_packet_schema(invalid_bool_pitch)

    def test_angle_in_bounds(self):
        assert_angle_in_bounds(0.0, 0.0, 0.0)
        assert_angle_in_bounds(-35.0, 45.0, 35.0)

        with self.assertRaises(AssertionError):
            assert_angle_in_bounds(35.1, 0.0, 0.0)
        with self.assertRaises(AssertionError):
            assert_angle_in_bounds(0.0, -45.1, 0.0)
        with self.assertRaises(AssertionError):
            assert_angle_in_bounds(0.0, 0.0, 35.1)

    def test_packet_rate(self):
        # 60 Hz timestamps: 61 packets across 1.0s
        ts_60hz = [i * (1.0 / 60.0) for i in range(61)]
        rate = assert_packet_rate(ts_60hz, min_hz=55.0, max_hz=65.0)
        self.assertAlmostEqual(rate, 60.0, places=1)

        # Too slow (10 Hz)
        ts_10hz = [i * 0.1 for i in range(11)]
        with self.assertRaises(AssertionError):
            assert_packet_rate(ts_10hz, min_hz=30.0, max_hz=60.0)

    def test_vector_close(self):
        assert_vector_close([0.0, 15.0, 0.0], [0.0, 15.0001, -0.0001], tol=0.01)
        with self.assertRaises(AssertionError):
            assert_vector_close([0.0, 15.0, 0.0], [0.0, 16.0, 0.0], tol=0.1)

    def test_state_transition(self):
        history = ["FLYING", "CRASHING", "GAME_OVER"]
        assert_state_transition(history, ["FLYING", "CRASHING"])
        assert_state_transition(history, ["FLYING", "GAME_OVER"])

        with self.assertRaises(AssertionError):
            assert_state_transition(history, ["GAME_OVER", "FLYING"])

    def test_control_mode(self):
        assert_control_mode("WEBCAM", "WEBCAM")
        assert_control_mode("KEYBOARD_MOUSE", "KEYBOARD_MOUSE")
        assert_control_mode("BLENDED", "BLENDED")

        with self.assertRaises(AssertionError):
            assert_control_mode("UNKNOWN_MODE", "WEBCAM")
        with self.assertRaises(AssertionError):
            assert_control_mode("WEBCAM", "KEYBOARD_MOUSE")

    def test_jitter_suppressed(self):
        # Low noise (std ~ 0.1 deg)
        low_jitter = [0.0, 0.1, -0.1, 0.05, -0.05, 0.08]
        assert_jitter_suppressed(low_jitter, max_std_deg=0.5)

        # High noise (std ~ 2.0 deg)
        high_jitter = [0.0, 3.0, -3.0, 2.5, -2.8, 1.9]
        with self.assertRaises(AssertionError):
            assert_jitter_suppressed(high_jitter, max_std_deg=0.5)

        # NaN / Inf non-finite values
        with self.assertRaises(AssertionError):
            assert_jitter_suppressed([0.0, float("nan"), 0.1])
        with self.assertRaises(AssertionError):
            assert_jitter_suppressed([0.0, float("inf"), 0.1])

    def test_deadzone_applied(self):
        assert_deadzone_applied(1.5, 0.0, threshold=2.0)
        assert_deadzone_applied(-1.8, 0.0, threshold=2.0)

        with self.assertRaises(AssertionError):
            assert_deadzone_applied(1.0, 0.5, threshold=2.0)

    def test_decay_rate(self):
        # Angle decaying from 8.0 to 0.0 over 1.0s -> decay = 8.0/s
        samples = [(0.0, 8.0), (0.5, 4.0), (1.0, 0.0)]
        measured = assert_decay_rate(samples, expected_rate=8.0, tol=1.0)
        self.assertAlmostEqual(measured, 8.0, places=1)


class TestUdpFixtures(OpaqueBoxTestCase):
    """Verifies live UDP transmission and capture over 127.0.0.1:42425."""

    def test_telemetry_packet_serialization(self):
        pkt = TelemetryPacket(pitch=12.5, yaw=-8.25, roll=1.0, calibrated=True, tracking=True)
        raw = pkt.to_bytes()
        reconstructed = TelemetryPacket.from_bytes(raw)
        self.assertAlmostEqual(reconstructed.pitch, 12.5, places=3)
        self.assertAlmostEqual(reconstructed.yaw, -8.25, places=3)
        self.assertAlmostEqual(reconstructed.roll, 1.0, places=3)
        self.assertTrue(reconstructed.calibrated)
        self.assertTrue(reconstructed.tracking)
        self.assertGreater(reconstructed.timestamp, 0.0)

    def test_broadcaster_and_capture_live_transmission(self):
        capture = self.create_capture()
        broadcaster = self.create_broadcaster(target_fps=60.0, start_now=False)
        broadcaster.set_telemetry(pitch=-15.0, yaw=10.0, roll=-5.0, calibrated=True, tracking=True)
        broadcaster.start()

        packets = capture.collect_packets(count=15, timeout=2.0)
        self.assertGreaterEqual(len(packets), 15)

        first = packets[0]
        capture.assert_schema(first)
        self.assertAlmostEqual(first.pitch, -15.0, places=2)
        self.assertAlmostEqual(first.yaw, 10.0, places=2)
        self.assertAlmostEqual(first.roll, -5.0, places=2)
        self.assertTrue(first.calibrated)
        self.assertTrue(first.tracking)

    def test_dynamic_telemetry_change(self):
        capture = self.create_capture()
        broadcaster = self.create_broadcaster()

        # Step 1: Neutral
        broadcaster.set_neutral()
        time.sleep(0.1)
        pkt1 = capture.wait_for_packet(timeout=1.0)
        self.assertAlmostEqual(pkt1.pitch, 0.0, places=2)

        # Step 2: Dive
        broadcaster.set_dive(-30.0)
        time.sleep(0.1)
        # Drain older packets
        latest = capture.get_latest()
        self.assertIsNotNone(latest)
        self.assertAlmostEqual(latest.pitch, -30.0, places=2)

    def test_burst_transmission_integrity(self):
        capture = self.create_capture()
        broadcaster = self.create_broadcaster(start_now=True)

        sent = broadcaster.send_burst(count=50)
        self.assertEqual(sent, 50)

        packets = capture.collect_packets(count=30, timeout=2.0)
        self.assertGreaterEqual(len(packets), 30)
        for p in packets:
            self.assertIsNone(p.parse_error)

    def test_malformed_packet_handling(self):
        capture = self.create_capture()
        broadcaster = self.create_broadcaster(start_now=False)
        capture.clear()

        # Inject malformed bytes
        broadcaster.send_malformed(b'{"pitch": 15.0, invalid_json')
        pkt = capture.wait_for_packet(timeout=1.0)
        self.assertIsNotNone(pkt.parse_error)
        self.assertIsNone(pkt.pitch)

    def test_compute_jitter_robust_to_non_numeric(self):
        capture = self.create_capture(start_now=False)
        p1 = CapturedPacket(raw_bytes=b"", received_at=1.0, pitch=0.0, yaw=0.0, roll=0.0)
        p2 = CapturedPacket(raw_bytes=b"", received_at=2.0, pitch="invalid", yaw=None, roll=0.1)
        p3 = CapturedPacket(raw_bytes=b"", received_at=3.0, pitch=True, yaw=0.0, roll=0.0)
        p4 = CapturedPacket(raw_bytes=b"", received_at=4.0, pitch=0.1, yaw=-0.1, roll=0.05)
        p5 = CapturedPacket(raw_bytes=b"", received_at=5.0, pitch=-0.1, yaw=0.1, roll=-0.05)
        jitters = capture.compute_jitter([p1, p2, p3, p4, p5])
        self.assertIn("pitch_std", jitters)
        self.assertFalse(math.isnan(jitters["pitch_std"]))
        self.assertFalse(math.isinf(jitters["pitch_std"]))
        self.assertGreater(jitters["pitch_std"], 0.0)

    def test_out_of_bounds_injection(self):
        capture = self.create_capture()
        broadcaster = self.create_broadcaster()

        broadcaster.set_out_of_bounds(pitch=999.0, yaw=-999.0, roll=500.0)
        time.sleep(0.1)
        latest = capture.get_latest()
        self.assertIsNotNone(latest)
        self.assertAlmostEqual(latest.pitch, 999.0, places=1)
        # Verify custom assertion catches out of bounds
        with self.assertRaises(AssertionError):
            assert_angle_in_bounds(latest.pitch, latest.yaw, latest.roll)

    def test_pause_silence_timeout(self):
        capture = self.create_capture()
        broadcaster = self.create_broadcaster()

        # Let a packet arrive
        pkt_before = capture.wait_for_packet(timeout=1.0)
        self.assertIsNotNone(pkt_before)

        # Clear queue and pause broadcaster for 0.3s
        capture.clear()
        broadcaster.pause_for(0.3)

        # Queue should be empty during pause
        with self.assertRaises(TimeoutError):
            capture.wait_for_packet(timeout=0.15)

        # After pause finishes, packets resume automatically
        time.sleep(0.2)
        pkt_after = capture.wait_for_packet(timeout=1.0)
        self.assertIsNotNone(pkt_after)


class TestFallbackInputSimulator(OpaqueBoxTestCase):
    """Verifies timed fallback event trace generation and serialization."""

    def test_trace_export_and_content(self):
        sim = FallbackInputSimulator()
        sim.add_action_press(0.5, "steer_left", 1.0)
        sim.add_action_release(1.5, "steer_left")
        sim.add_mouse_motion(2.0, 15.0, -10.0)

        events = sim.get_events()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["action"], "steer_left")
        self.assertEqual(events[0]["time_sec"], 0.5)

        with tempfile.TemporaryDirectory() as tmp_dir:
            trace_path = Path(tmp_dir) / "test_trace.json"
            exported = sim.export_trace(trace_path)
            self.assertTrue(exported.is_file())

            with open(exported, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 3)
            self.assertEqual(data[2]["type"], "mouse_motion")

    def test_prebuilt_traces(self):
        t1 = FallbackInputSimulator.generate_keyboard_override_trace().get_events()
        t2 = FallbackInputSimulator.generate_slalom_keyboard_trace().get_events()
        t3 = FallbackInputSimulator.generate_emergency_evasion_trace().get_events()

        self.assertGreaterEqual(len(t1), 2)
        self.assertGreaterEqual(len(t2), 6)
        self.assertGreaterEqual(len(t3), 4)


class TestGodotRunner(OpaqueBoxTestCase):
    """Verifies Godot binary discovery and subprocess execution."""

    def test_godot_binary_discovery(self):
        binary = GodotDiscovery.find_binary()
        self.assertTrue(binary.is_file(), f"Discovered Godot binary does not exist: {binary}")
        self.assertIn("Godot", binary.name)

    def test_godot_headless_version_execution(self):
        runner = self.create_godot_runner(extra_args=["--version"])
        matched = runner.wait_for_pattern("4.", timeout=5.0)
        self.assertIsNotNone(matched, f"Godot did not output version 4.x. Logs: {runner.all_logs}")


class TestTrackerRunner(OpaqueBoxTestCase):
    """Verifies TrackerProcessManager initialization and teardown."""

    def test_tracker_process_manager_init(self):
        tracker = TrackerProcessManager(use_mock=True)
        self.assertIsNotNone(tracker.target_script)


class TestCliPatternFallback(OpaqueBoxTestCase):
    """Verifies regex error recovery and substring matching fallback in CLI runner."""

    def test_pattern_regex_error_fallback(self):
        from e2e_tests.run_e2e_tests import build_filtered_suite
        # Unclosed bracket or unescaped leading star will raise re.error
        suite_star = build_filtered_suite(tier_choice="framework", pattern="*malformed*")
        tests_star = [t.id() for t in suite_star]
        self.assertTrue(any("test_malformed_packet_handling" in tid for tid in tests_star))

        suite_bracket = build_filtered_suite(tier_choice="framework", pattern="[malformed")
        tests_bracket = [t.id() for t in suite_bracket]
        # Must execute without re.error crash
        self.assertIsInstance(tests_bracket, list)
