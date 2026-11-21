"""
test_one_euro_filter.py - Unit tests for 1-Euro adaptive low-pass filter.
"""

import sys
import os
import math
import unittest
import numpy as np

# Ensure tracker package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tracker.head_tracker import OneEuroFilter


class TestOneEuroFilter(unittest.TestCase):
    """Test suite verifying 1-Euro filter noise reduction, dynamic latency, and state reset."""

    def test_default_params_variance_reduction(self):
        """
        Verifies that with default production parameters (fc_min=1.0, beta=0.007),
        variance on stationary Gaussian noise is reduced by > 85%.
        """
        np.random.seed(42)
        dt = 1.0 / 30.0
        t = 0.0
        center_val = 15.0

        filt = OneEuroFilter(t0=t, x0=center_val, fc_min=1.0, beta=0.007, d_cutoff=1.0)
        raw_signals = []
        filtered_signals = []

        for _ in range(300):
            t += dt
            noise = np.random.normal(0.0, 1.0)
            noisy_val = center_val + noise
            raw_signals.append(noisy_val)
            filtered_signals.append(filt.filter(t, noisy_val))

        var_raw = float(np.var(raw_signals))
        var_filt = float(np.var(filtered_signals))
        reduction = (var_raw - var_filt) / var_raw

        # Theoretical attenuation at fc=1.0Hz is ~90.5%, well exceeding 85%
        self.assertGreater(reduction, 0.85, f"Variance reduction was {reduction * 100:.2f}% (expected > 85%)")

    def test_stationary_noise_std_reduction(self):
        """
        Verifies standard deviation reduction > 80% with fc_min=0.35.
        """
        np.random.seed(42)
        dt = 1.0 / 30.0
        t = 0.0
        center_val = 0.0

        filt = OneEuroFilter(t0=t, x0=center_val, fc_min=0.35, beta=0.007, d_cutoff=1.0)
        raw_signals = []
        filtered_signals = []

        for _ in range(300):
            t += dt
            noisy_val = center_val + np.random.normal(0.0, 1.0)
            raw_signals.append(noisy_val)
            filtered_signals.append(filt.filter(t, noisy_val))

        std_raw = float(np.std(raw_signals))
        std_filt = float(np.std(filtered_signals))
        reduction = (std_raw - std_filt) / std_raw

        self.assertGreater(reduction, 0.80, f"Std dev reduction was {reduction * 100:.2f}% (expected > 80%)")

    def test_step_response_latency(self):
        """
        Verifies that on a sharp step input (0 deg -> 20 deg), the adaptive
        beta coefficient increases cutoff frequency so output settles to >= 95%
        of target (19.0 deg) within <= 10 samples (<= 333 ms at 30 Hz).
        """
        dt = 1.0 / 30.0
        t = 0.0
        filt = OneEuroFilter(t0=t, x0=0.0, fc_min=1.0, beta=0.007, d_cutoff=1.0)

        step_time = 0.5
        target = 20.0
        samples_to_settle = None

        for _ in range(60):
            t += dt
            x = 0.0 if t < step_time else target
            out = filt.filter(t, x)

            if t >= step_time and samples_to_settle is None:
                if out >= 0.95 * target:
                    samples_to_settle = int(round((t - step_time) / dt))

        self.assertIsNotNone(samples_to_settle, "Step response never reached 95% target")
        self.assertLessEqual(
            samples_to_settle, 10,
            f"Step response took {samples_to_settle} samples to settle (expected <= 10)"
        )

    def test_filter_reset(self):
        """
        Verifies that reset clears previous state and derivative, starting immediately
        at new baseline without residual lag.
        """
        filt = OneEuroFilter(t0=0.0, x0=25.0, fc_min=1.0, beta=0.007)
        filt.filter(0.033, 25.0)

        # Trigger recalibration reset to 0.0
        filt.reset(0.100, 0.0)
        self.assertEqual(filt.x_prev, 0.0)
        self.assertEqual(filt.dx_prev, 0.0)

        # First sample after reset should pass new value cleanly
        out = filt.filter(0.133, 0.0)
        self.assertAlmostEqual(out, 0.0, places=4)

    def test_variable_dt_and_pause_recovery(self):
        """
        Verifies that stalls (>0.5s) re-latch without runaway derivative.
        """
        filt = OneEuroFilter(t0=0.0, x0=0.0, fc_min=1.0, beta=0.007)
        filt.filter(0.033, 1.0)

        # Pause 1.5 seconds (camera stall or background thread sleep)
        out = filt.filter(1.533, 10.0)
        # Should reset baseline to 10.0 without blowing up
        self.assertEqual(out, 10.0)
        self.assertEqual(filt.dx_prev, 0.0)

    def test_non_finite_rejection_and_clean_recovery(self):
        """
        Verifies that injecting NaN, +Inf, and -Inf does NOT poison the filter,
        internal state variables remain finite, and subsequent normal float inputs
        recover cleanly to expected filtered values.
        """
        filt = OneEuroFilter(t0=0.0, x0=0.0, fc_min=1.0, beta=0.007)
        filt.filter(0.033, 5.0)

        # 1. Inject NaN
        nan_out = filt.filter(0.066, float("nan"))
        self.assertTrue(math.isfinite(nan_out), f"NaN input leaked non-finite output: {nan_out}")
        self.assertIsNotNone(filt.x_prev)
        self.assertTrue(math.isfinite(filt.x_prev), "Filter state x_prev poisoned by NaN")
        self.assertTrue(math.isfinite(filt.dx_prev), "Filter state dx_prev poisoned by NaN")

        # 2. Inject +Inf
        inf_out = filt.filter(0.099, float("inf"))
        self.assertTrue(math.isfinite(inf_out), f"+Inf input leaked non-finite output: {inf_out}")
        self.assertTrue(math.isfinite(filt.x_prev), "Filter state x_prev poisoned by +Inf")
        self.assertTrue(math.isfinite(filt.dx_prev), "Filter state dx_prev poisoned by +Inf")

        # 3. Inject -Inf
        ninf_out = filt.filter(0.132, -float("inf"))
        self.assertTrue(math.isfinite(ninf_out), f"-Inf input leaked non-finite output: {ninf_out}")
        self.assertTrue(math.isfinite(filt.x_prev), "Filter state x_prev poisoned by -Inf")
        self.assertTrue(math.isfinite(filt.dx_prev), "Filter state dx_prev poisoned by -Inf")

        # 4. Clean recovery with subsequent normal inputs at 30 Hz
        t = 0.132
        dt = 1.0 / 30.0
        post_recovery_outputs = []
        for _ in range(10):
            t += dt
            out = filt.filter(t, 10.0)
            self.assertTrue(math.isfinite(out), f"Filter produced non-finite output post-recovery: {out}")
            post_recovery_outputs.append(out)

        # Output should converge smoothly towards 10.0 without any NaNs or jumps
        self.assertAlmostEqual(post_recovery_outputs[-1], 10.0, delta=1.5)

    def test_uninitialized_filter_handles_non_finite(self):
        """
        Verifies that an uninitialized filter receiving NaN or Inf returns 0.0
        and leaves filter state unpoisoned, ready for valid initialization.
        """
        filt = OneEuroFilter()
        out = filt.filter(0.0, float("nan"))
        self.assertEqual(out, 0.0)
        self.assertIsNone(filt.x_prev)

        # Valid initialization should succeed immediately afterwards
        valid_out = filt.filter(0.033, 12.0)
        self.assertEqual(valid_out, 12.0)
        self.assertEqual(filt.x_prev, 12.0)


if __name__ == "__main__":
    unittest.main()
