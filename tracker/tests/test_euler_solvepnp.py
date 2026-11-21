"""
test_euler_solvepnp.py - Validation tests for 3D landmark reprojection and solvePnP Euler recovery.
"""

import sys
import os
import unittest
import numpy as np
import cv2

# Ensure tracker package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tracker.head_tracker import (
    FACE_MODEL_3D,
    get_camera_matrix,
    solve_head_pose
)


class TestEulerSolvePnP(unittest.TestCase):
    """Test suite verifying 3D face model solvePnP pose estimation and Euler decomposition."""

    def setUp(self):
        self.width = 640
        self.height = 480
        self.camera_matrix = get_camera_matrix(self.width, self.height)
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        self.tvec_gt = np.array([0.0, 0.0, 750.0], dtype=np.float64)

    def _project_ground_truth(self, target_pitch: float, target_yaw: float, target_roll: float) -> np.ndarray:
        """
        Projects 3D face model points to 2D using ground truth angles mapped to camera coordinates:
        raw_pitch = -target_pitch
        raw_yaw = -target_yaw
        raw_roll = -target_roll
        """
        raw_p = np.radians(-target_pitch)
        raw_y = np.radians(-target_yaw)
        raw_r = np.radians(-target_roll)

        Rx = np.array([
            [1.0, 0.0, 0.0],
            [0.0, np.cos(raw_p), -np.sin(raw_p)],
            [0.0, np.sin(raw_p), np.cos(raw_p)]
        ], dtype=np.float64)

        Ry = np.array([
            [np.cos(raw_y), 0.0, np.sin(raw_y)],
            [0.0, 1.0, 0.0],
            [-np.sin(raw_y), 0.0, np.cos(raw_y)]
        ], dtype=np.float64)

        Rz = np.array([
            [np.cos(raw_r), -np.sin(raw_r), 0.0],
            [np.sin(raw_r), np.cos(raw_r), 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # Composite rotation R = Rz * Ry * Rx (matching RQDecomp3x3 order)
        R_gt = Rz @ Ry @ Rx
        rvec_gt, _ = cv2.Rodrigues(R_gt)

        pts_2d, _ = cv2.projectPoints(
            FACE_MODEL_3D, rvec_gt, self.tvec_gt, self.camera_matrix, self.dist_coeffs
        )
        return pts_2d.reshape(-1, 2)

    def test_neutral_frontal_pose(self):
        """Verifies that neutral forward gaze evaluates exactly to (0.0, 0.0, 0.0)."""
        pts_2d = self._project_ground_truth(target_pitch=0.0, target_yaw=0.0, target_roll=0.0)
        success, rvec, tvec, pitch, yaw, roll = solve_head_pose(
            pts_2d, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, 0.0, places=2)
        self.assertAlmostEqual(yaw, 0.0, places=2)
        self.assertAlmostEqual(roll, 0.0, places=2)

    def test_isolated_pitch_climb_and_dive(self):
        """Verifies isolated pitch movements (Positive = Climb, Negative = Dive)."""
        # Test climb (+15.0 deg)
        pts_climb = self._project_ground_truth(target_pitch=15.0, target_yaw=0.0, target_roll=0.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(
            pts_climb, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, 15.0, places=1)
        self.assertAlmostEqual(yaw, 0.0, places=1)
        self.assertAlmostEqual(roll, 0.0, places=1)

        # Test dive (-15.0 deg)
        pts_dive = self._project_ground_truth(target_pitch=-15.0, target_yaw=0.0, target_roll=0.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(
            pts_dive, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, -15.0, places=1)
        self.assertAlmostEqual(yaw, 0.0, places=1)
        self.assertAlmostEqual(roll, 0.0, places=1)

    def test_isolated_yaw_right_and_left(self):
        """Verifies isolated yaw movements (Positive = Turn Right, Negative = Turn Left)."""
        # Test turn right (+20.0 deg)
        pts_right = self._project_ground_truth(target_pitch=0.0, target_yaw=20.0, target_roll=0.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(
            pts_right, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, 0.0, places=1)
        self.assertAlmostEqual(yaw, 20.0, places=1)
        self.assertAlmostEqual(roll, 0.0, places=1)

        # Test turn left (-20.0 deg)
        pts_left = self._project_ground_truth(target_pitch=0.0, target_yaw=-20.0, target_roll=0.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(
            pts_left, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, 0.0, places=1)
        self.assertAlmostEqual(yaw, -20.0, places=1)
        self.assertAlmostEqual(roll, 0.0, places=1)

    def test_isolated_roll_right_and_left(self):
        """Verifies isolated roll movements (Positive = Tilt Right, Negative = Tilt Left)."""
        # Test tilt right (+12.0 deg)
        pts_roll_r = self._project_ground_truth(target_pitch=0.0, target_yaw=0.0, target_roll=12.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(
            pts_roll_r, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, 0.0, places=1)
        self.assertAlmostEqual(yaw, 0.0, places=1)
        self.assertAlmostEqual(roll, 12.0, places=1)

        # Test tilt left (-12.0 deg)
        pts_roll_l = self._project_ground_truth(target_pitch=0.0, target_yaw=0.0, target_roll=-12.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(
            pts_roll_l, self.camera_matrix, self.dist_coeffs
        )
        self.assertTrue(success)
        self.assertAlmostEqual(pitch, 0.0, places=1)
        self.assertAlmostEqual(yaw, 0.0, places=1)
        self.assertAlmostEqual(roll, -12.0, places=1)

    def test_combined_multi_axis_rotation(self):
        """Verifies recovery accuracy for simultaneous 3-axis compound rotation."""
        test_cases = [
            (10.0, -15.0, 8.0),
            (-12.0, 18.0, -6.0),
            (20.0, 25.0, 15.0)
        ]
        for exp_p, exp_y, exp_r in test_cases:
            pts = self._project_ground_truth(exp_p, exp_y, exp_r)
            success, _, _, act_p, act_y, act_r = solve_head_pose(
                pts, self.camera_matrix, self.dist_coeffs
            )
            self.assertTrue(success)
            self.assertAlmostEqual(act_p, exp_p, places=1, msg=f"Pitch mismatch on ({exp_p},{exp_y},{exp_r})")
            self.assertAlmostEqual(act_y, exp_y, places=1, msg=f"Yaw mismatch on ({exp_p},{exp_y},{exp_r})")
            self.assertAlmostEqual(act_r, exp_r, places=1, msg=f"Roll mismatch on ({exp_p},{exp_y},{exp_r})")

    def test_non_finite_and_invalid_landmarks_rejection(self):
        """
        Verifies that passing NaN or Inf arrays in image_points, as well as None
        or malformed arrays, returns (False, None, None, 0.0, 0.0, 0.0) cleanly
        without raising cv2.error or other unhandled exceptions.
        """
        # All NaN points
        nan_pts = np.full((6, 2), np.nan, dtype=np.float64)
        success, rvec, tvec, p, y, r = solve_head_pose(nan_pts, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))

        # All +Inf points
        inf_pts = np.full((6, 2), np.inf, dtype=np.float64)
        success, rvec, tvec, p, y, r = solve_head_pose(inf_pts, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))

        # All -Inf points
        ninf_pts = np.full((6, 2), -np.inf, dtype=np.float64)
        success, rvec, tvec, p, y, r = solve_head_pose(ninf_pts, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))

        # Single NaN in an otherwise valid landmark array
        single_nan_pts = self._project_ground_truth(0.0, 0.0, 0.0)
        single_nan_pts[0, 0] = np.nan
        success, rvec, tvec, p, y, r = solve_head_pose(single_nan_pts, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))

        # Single Inf in an otherwise valid landmark array
        single_inf_pts = self._project_ground_truth(0.0, 0.0, 0.0)
        single_inf_pts[3, 1] = np.inf
        success, rvec, tvec, p, y, r = solve_head_pose(single_inf_pts, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))

        # None input
        success, rvec, tvec, p, y, r = solve_head_pose(None, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))

        # Malformed / wrong shape array
        wrong_shape_pts = np.zeros((4, 2), dtype=np.float64)
        success, rvec, tvec, p, y, r = solve_head_pose(wrong_shape_pts, self.camera_matrix, self.dist_coeffs)
        self.assertFalse(success)
        self.assertIsNone(rvec)
        self.assertIsNone(tvec)
        self.assertEqual((p, y, r), (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
