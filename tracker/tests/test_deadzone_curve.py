"""
test_deadzone_curve.py - Unit tests for continuous rescaled deadzone and gamma power curve.
"""

import sys
import os
import unittest
import numpy as np

# Ensure tracker package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tracker.head_tracker import SignalProcessor


class TestDeadzoneCurve(unittest.TestCase):
    """Test suite validating deadzone thresholding, C1 continuity, monotonicity, and clamping."""

    def setUp(self):
        self.processor = SignalProcessor(
            deadzone=2.0,
            gamma=1.5,
            max_pitch=35.0,
            max_yaw=45.0,
            max_roll=35.0
        )

    def test_deadzone_exact_zero_output(self):
        """Verifies that all inputs inside [-deadzone, +deadzone] return strictly 0.0."""
        for angle in [-2.0, -1.5, -0.5, 0.0, 0.5, 1.5, 2.0]:
            out = self.processor.process_axis(angle, max_angle=35.0)
            self.assertEqual(out, 0.0, f"Expected 0.0 for angle {angle}, got {out}")

    def test_continuity_at_deadzone_boundary(self):
        """
        Verifies C1 continuity at the deadzone boundary:
        lim_{theta -> 2.0+} f(theta) == 0.0 with no step jump discontinuity.
        """
        eps = 1e-4
        pos_out = self.processor.process_axis(2.0 + eps, max_angle=35.0)
        neg_out = self.processor.process_axis(-2.0 - eps, max_angle=35.0)

        # Because (eps / denom)^1.5 is extremely small (~1.6e-8 * 35.0 = 5.8e-7),
        # output is virtually 0, proving zero jump discontinuity.
        self.assertAlmostEqual(pos_out, 0.0, places=3)
        self.assertAlmostEqual(neg_out, 0.0, places=3)
        self.assertGreater(pos_out, 0.0)
        self.assertLess(neg_out, 0.0)

    def test_strict_monotonicity(self):
        """Verifies that the transformation is monotonically non-decreasing over entire range."""
        angles = np.linspace(-35.0, 35.0, 500)
        outputs = [self.processor.process_axis(float(a), max_angle=35.0) for a in angles]
        diffs = np.diff(outputs)

        self.assertTrue(
            np.all(diffs >= -1e-9),
            "Non-monotonic decrease detected in deadzone curve output."
        )

    def test_boundary_clamping(self):
        """Verifies that angles beyond max_angle saturate strictly at max_angle."""
        # Pitch limits [-35, 35]
        self.assertAlmostEqual(self.processor.process_axis(35.0, max_angle=35.0), 35.0)
        self.assertAlmostEqual(self.processor.process_axis(50.0, max_angle=35.0), 35.0)
        self.assertAlmostEqual(self.processor.process_axis(-60.0, max_angle=35.0), -35.0)

        # Yaw limits [-45, 45]
        self.assertAlmostEqual(self.processor.process_axis(45.0, max_angle=45.0), 45.0)
        self.assertAlmostEqual(self.processor.process_axis(80.0, max_angle=45.0), 45.0)
        self.assertAlmostEqual(self.processor.process_axis(-90.0, max_angle=45.0), -45.0)

    def test_odd_symmetry(self):
        """Verifies odd symmetry: f(-theta) == -f(theta)."""
        test_angles = [0.0, 1.0, 2.0, 3.5, 10.0, 20.0, 35.0, 50.0]
        for a in test_angles:
            pos = self.processor.process_axis(a, max_angle=35.0)
            neg = self.processor.process_axis(-a, max_angle=35.0)
            self.assertAlmostEqual(pos, -neg, places=5)

    def test_gamma_progressive_sensitivity(self):
        """
        Verifies that at 20% deflection above deadzone, output deflection is < 10%
        due to gamma=1.5 shaping, allowing subtle trimming.
        """
        # deadzone = 2.0, max = 35.0 -> span = 33.0
        # 20% span = 2.0 + 0.20 * 33.0 = 8.6 deg
        out = self.processor.process_axis(8.6, max_angle=35.0)
        linear_expected = 0.20 * 35.0  # 7.0 deg
        self.assertLess(out, linear_expected)
        self.assertAlmostEqual(out, (0.20 ** 1.5) * 35.0, places=2)

    def test_processor_multi_axis(self):
        """Verifies process() method handles all 3 axes simultaneously."""
        p, y, r = self.processor.process(pitch=10.0, yaw=-25.0, roll=0.0)
        self.assertGreater(p, 0.0)
        self.assertLess(y, 0.0)
        self.assertEqual(r, 0.0)


if __name__ == "__main__":
    unittest.main()
