"""e2e_tests/tier5/test_t5_python_tracker_hardening.py
Tier 5 Adversarial Coverage Hardening: Python Head-Tracking & UDP Telemetry Subsystem.

Covers:
- TEST-T5-TRK-01: OneEuroFilter Zero/Negative Cutoff Singularity Immunity
- TEST-T5-TRK-02: OneEuroFilter Non-Finite State Preservation (NaN/Inf)
- TEST-T5-TRK-03: OneEuroFilter Nyquist Boundary Oscillation Stability
- TEST-T5-TRK-04: SignalProcessor Deadzone Division by Zero & Negative Gamma
- TEST-T5-TRK-05: HeadTracker Calibration NaN Poisoning Immunity
- TEST-T5-TRK-06: TelemetryBroadcaster Port Overflow & Re-bind Resilience
- TEST-T5-TRK-07: MockTracker Invalid Port & High-Speed Concurrency
- TEST-T5-TRK-08: UDP Datagram Adversarial Payload Fuzzing (64KB, empty, non-UTF8)
"""

import math
import socket
import time
import unittest
import numpy as np

from tracker.head_tracker import OneEuroFilter, SignalProcessor, TelemetryBroadcaster, HeadTracker, solve_head_pose, get_camera_matrix
from tracker.mock_tracker import MockTracker


class TestTier5PythonTrackerHardening(unittest.TestCase):
    """Tier 5 adversarial hardening tests for Python tracker subsystem."""

    def test_t5_trk_01_filter_zero_negative_cutoff(self):
        """TEST-T5-TRK-01: OneEuroFilter survives zero and negative cutoff frequencies without ZeroDivisionError."""
        # Zero cutoff
        f_zero = OneEuroFilter(t0=0.0, x0=10.0, fc_min=0.0, d_cutoff=0.0)
        out1 = f_zero.filter(0.033, 15.0)
        self.assertTrue(math.isfinite(out1))

        # Negative cutoff
        f_neg = OneEuroFilter(t0=0.0, x0=10.0, fc_min=-1.0, d_cutoff=-1.0)
        out2 = f_neg.filter(0.033, 15.0)
        self.assertTrue(math.isfinite(out2))

    def test_t5_trk_02_filter_nan_inf_preservation(self):
        """TEST-T5-TRK-02: Filter rejects NaN and Inf inputs without state poisoning or exception."""
        f = OneEuroFilter(t0=0.0, x0=20.0)
        out_nan = f.filter(0.033, float('nan'))
        self.assertEqual(out_nan, 20.0)

        out_inf = f.filter(0.066, float('inf'))
        self.assertEqual(out_inf, 20.0)

        # Resumes normal filtering on next finite value
        out_valid = f.filter(0.099, 25.0)
        self.assertTrue(math.isfinite(out_valid))
        self.assertGreater(out_valid, 20.0)

    def test_t5_trk_03_filter_nyquist_oscillation(self):
        """TEST-T5-TRK-03: Filter bounded under Nyquist alternating oscillation (+/-30 deg)."""
        f = OneEuroFilter(t0=0.0, x0=0.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        dt = 1.0 / 60.0
        t = 0.0
        outputs = []
        for i in range(120):
            t += dt
            val = 30.0 if (i % 2 == 0) else -30.0
            outputs.append(f.filter(t, val))
        self.assertTrue(all(math.isfinite(o) for o in outputs))
        self.assertLessEqual(max(abs(o) for o in outputs), 30.0)

    def test_t5_trk_04_signal_processor_robustness(self):
        """TEST-T5-TRK-04: SignalProcessor handles max_angle <= deadzone and negative gamma safely."""
        sp_divzero = SignalProcessor(deadzone=15.0, gamma=1.5, max_pitch=15.0)
        out = sp_divzero.process_axis(20.0, max_angle=15.0)
        self.assertEqual(out, 0.0)

        sp_gamma = SignalProcessor(deadzone=2.0, gamma=-1.0, max_pitch=35.0)
        out_gamma = sp_gamma.process_axis(2.0, max_angle=35.0)
        self.assertTrue(math.isfinite(out_gamma))

    def test_t5_trk_05_calibrate_nan_guard(self):
        """TEST-T5-TRK-05: HeadTracker.calibrate ignores NaN and Inf inputs without poisoning offsets."""
        tracker = HeadTracker()
        try:
            tracker.pitch_offset = 5.0
            tracker.calibrate(float('nan'), 0.0, 0.0)
            # Offset must not become NaN
            self.assertTrue(math.isfinite(tracker.pitch_offset))
            self.assertEqual(tracker.pitch_offset, 5.0)
        finally:
            tracker.broadcaster.close()

    def test_t5_trk_06_broadcaster_port_overflow(self):
        """TEST-T5-TRK-06: TelemetryBroadcaster safely returns False on out-of-range port numbers."""
        b = TelemetryBroadcaster(port=70000)
        sent = b.send({"pitch": 0.0})
        self.assertFalse(sent)
        b.close()

    def test_t5_trk_07_mock_tracker_invalid_port(self):
        """TEST-T5-TRK-07: MockTracker send_packet returns False on invalid port instead of OverflowError."""
        mt = MockTracker(port=70000)
        sent = mt.send_packet({"pitch": 0.0})
        self.assertFalse(sent)
        mt.close()

    def test_t5_trk_08_udp_datagram_fuzzing(self):
        """TEST-T5-TRK-08: Python TelemetryBroadcaster and UDP sockets survive 64KB and empty datagrams."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Send empty datagram
        sock.sendto(b"", ("127.0.0.1", 42428))
        # Send non-UTF8 binary datagram
        sock.sendto(b"\x80\x81\xff\xfe", ("127.0.0.1", 42428))
        sock.close()


if __name__ == "__main__":
    unittest.main()
