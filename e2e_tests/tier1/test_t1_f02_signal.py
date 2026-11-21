"""e2e_tests/tier1/test_t1_f02_signal.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 2:
Signal Processing Pipeline (1-Euro Filter, Deadzone, Sensitivity Scaling, Calibration).

Test Catalog:
- TEST-T1-F02-01: Micro-Jitter Rejection Partition (1-Euro filter variance reduction >= 80%)
- TEST-T1-F02-02: Continuous Deadzone Partition (Angles in [-2.0°, +2.0°] evaluate to 0.0°)
- TEST-T1-F02-03: Monotonic Sensitivity Scaling Partition
- TEST-T1-F02-04: Neutral Pose Calibration Offset Partition
- TEST-T1-F02-05: Step Response Damping & Settling Partition
"""

import numpy as np

from e2e_tests.framework.assertions import (
    assert_deadzone_applied,
    assert_jitter_suppressed,
)
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import OneEuroFilter, SignalProcessor


class TestTier1Feature02Signal(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for signal processing pipeline."""

    def test_t1_f02_01_micro_jitter_rejection(self) -> None:
        """TEST-T1-F02-01: 1-Euro filter attenuates stationary Gaussian micro-jitter (sigma=1.5°) by >= 80%."""
        np.random.seed(42)
        filt = OneEuroFilter(t0=0.0, x0=0.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        dt = 1.0 / 30.0
        t = 0.0
        raw_values = []
        filtered_values = []

        for _ in range(120):
            t += dt
            noise = float(np.random.normal(0.0, 1.5))
            raw_values.append(noise)
            filtered_values.append(filt.filter(t, noise))

        var_raw = float(np.var(raw_values))
        var_filt = float(np.var(filtered_values[30:]))
        reduction = (var_raw - var_filt) / var_raw

        self.assertGreaterEqual(reduction, 0.80, f"Variance reduction {reduction:.2%} was < 80%")
        assert_jitter_suppressed(filtered_values[30:], max_std_deg=0.5, context="TEST-T1-F02-01")

    def test_t1_f02_02_continuous_deadzone(self) -> None:
        """TEST-T1-F02-02: Input angles within [-2.0°, +2.0°] produce exactly 0.0° output."""
        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_pitch=35.0, max_yaw=45.0, max_roll=35.0)
        angles_in_deadzone = [-2.0, -1.8, -1.0, 0.0, 0.5, 1.5, 2.0]
        for a in angles_in_deadzone:
            out = processor.process_axis(a, max_angle=35.0)
            assert_deadzone_applied(a, out, threshold=2.0, context="TEST-T1-F02-02")
            self.assertEqual(out, 0.0)

    def test_t1_f02_03_sensitivity_scaling_monotonic(self) -> None:
        """TEST-T1-F02-03: Angles outside deadzone scale smoothly and monotonically non-decreasing in [0.0, max_angle]."""
        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_pitch=35.0)
        angles = np.linspace(2.1, 35.0, 100)
        outputs = [processor.process_axis(float(a), max_angle=35.0) for a in angles]

        self.assertGreater(outputs[0], 0.0)
        self.assertAlmostEqual(outputs[-1], 35.0, places=3)
        diffs = np.diff(outputs)
        self.assertTrue(np.all(diffs >= -1e-9), "Non-monotonic increase in sensitivity curve")

    def test_t1_f02_04_neutral_pose_calibration_offset(self) -> None:
        """TEST-T1-F02-04: Baseline pose with static offset (+12.0°) zeroes out after calibration."""
        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_pitch=35.0)
        raw_pitch = 12.0
        calib_offset = 12.0
        rel_pitch = raw_pitch - calib_offset
        out = processor.process_axis(rel_pitch, max_angle=35.0)
        self.assertEqual(out, 0.0, "Calibrated neutral pose did not evaluate to 0.0°")

        new_raw = 20.0
        new_rel = new_raw - calib_offset  # +8.0°
        new_out = processor.process_axis(new_rel, max_angle=35.0)
        self.assertGreater(new_out, 0.0)

    def test_t1_f02_05_step_response_damping(self) -> None:
        """TEST-T1-F02-05: Instantaneous step input (0° -> 20°) reaches >= 95% target quickly without overshoot (> 105%)."""
        filt = OneEuroFilter(t0=0.0, x0=0.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        dt = 1.0 / 30.0
        t = 0.0
        target = 20.0
        outputs = []

        # Settle filter at 0.0 for 10 ticks
        for _ in range(10):
            t += dt
            filt.filter(t, 0.0)

        settled_index = None
        for i in range(30):
            t += dt
            out = filt.filter(t, target)
            outputs.append(out)
            if out >= 0.95 * target and settled_index is None:
                settled_index = i

        self.assertIsNotNone(settled_index, "Filter did not reach 95% target")
        self.assertLessEqual(settled_index, 10, f"Filter took {settled_index} samples (expected <= 10)")
        self.assertLessEqual(max(outputs), 1.05 * target, "Step response exhibited excessive overshoot")
