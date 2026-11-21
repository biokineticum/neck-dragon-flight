"""e2e_tests/tier2/test_t2_f02_signal.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 2:
Signal Processing Pipeline (Deadzone boundary, high angular velocity, calibration extremes, dt extremes).

Test Catalog:
- TEST-T2-F02-01: Deadzone Exact Boundary Cutoff (1.999°, 2.000°, 2.001°)
- TEST-T2-F02-02: Ultra-High Angular Velocity Step (1800°/s) Stability
- TEST-T2-F02-03: Extreme Angle Calibration Corner Case (+30.0°)
- TEST-T2-F02-04: Infinitesimal Delta-Time Stability (dt = 1e-6s)
- TEST-T2-F02-05: Large Gap Interruption Recovery (dt = 5.0s)
"""

import math

from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import OneEuroFilter, SignalProcessor


class TestTier2Feature02Signal(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for signal processing pipeline."""

    def test_t2_f02_01_deadzone_exact_boundary(self) -> None:
        """TEST-T2-F02-01: Deadzone exact boundary cutoff at 1.999°, 2.000°, 2.001° (threshold = 2.0°)."""
        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_pitch=35.0)
        out_below = processor.process_axis(1.999, max_angle=35.0)
        out_exact = processor.process_axis(2.000, max_angle=35.0)
        out_above = processor.process_axis(2.001, max_angle=35.0)

        self.assertEqual(out_below, 0.0)
        self.assertEqual(out_exact, 0.0)
        self.assertGreater(out_above, 0.0)
        self.assertAlmostEqual(out_above, 0.0, places=3)  # Smooth C1 transition

    def test_t2_f02_02_ultra_high_angular_velocity(self) -> None:
        """TEST-T2-F02-02: Extreme angular step (-30° to +30° in 1 tick = 1800°/s) produces finite output without NaN."""
        filt = OneEuroFilter(t0=0.0, x0=-30.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        dt = 1.0 / 30.0
        filt.filter(dt, -30.0)

        out = filt.filter(2 * dt, 30.0)
        self.assertTrue(math.isfinite(out), f"Filter produced non-finite output: {out}")
        self.assertGreater(out, -30.0)
        self.assertLessEqual(out, 30.0)

    def test_t2_f02_03_extreme_angle_calibration(self) -> None:
        """TEST-T2-F02-03: Neutral calibration at extreme +30.0° produces correct offset and safe saturation at -35.0°."""
        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_pitch=35.0)
        calib_offset = 30.0  # Player calibrated with head tilted way up

        # Neutral pose at calibrated position
        out_calib = processor.process_axis(30.0 - calib_offset, max_angle=35.0)
        self.assertEqual(out_calib, 0.0)

        # Player looks down to -30.0° raw -> relative angle = -60.0° -> must clamp to -35.0°
        out_extreme_down = processor.process_axis(-30.0 - calib_offset, max_angle=35.0)
        self.assertEqual(out_extreme_down, -35.0)

    def test_t2_f02_04_infinitesimal_dt_stability(self) -> None:
        """TEST-T2-F02-04: Filter update with infinitesimal dt (1e-6s) avoids division by zero or NaN."""
        filt = OneEuroFilter(t0=1.0, x0=10.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        out = filt.filter(1.0 + 1e-6, 10.5)

        self.assertTrue(math.isfinite(out), f"Filter failed on infinitesimal dt: {out}")
        self.assertAlmostEqual(out, 10.0, delta=1.0)

    def test_t2_f02_05_large_gap_interruption_recovery(self) -> None:
        """TEST-T2-F02-05: Filter update after 5.0s interruption gap resets derivative and outputs target angle."""
        filt = OneEuroFilter(t0=0.0, x0=0.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        filt.filter(0.033, 0.0)

        # 5.0 seconds gap in timestamps (camera pause / lag)
        out = filt.filter(5.033, 25.0)
        self.assertTrue(math.isfinite(out))
        # After dt > 0.5s pause, filter resets state directly to new target x
        self.assertEqual(out, 25.0)
