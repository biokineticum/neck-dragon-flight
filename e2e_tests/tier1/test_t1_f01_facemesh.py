"""e2e_tests/tier1/test_t1_f01_facemesh.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 1:
MediaPipe FaceMesh & SolvePnP Pose Estimation.

Test Catalog:
- TEST-T1-F01-01: Center Neutral Gaze Partition
- TEST-T1-F01-02: Pitch Up Look Partition (Climb)
- TEST-T1-F01-03: Pitch Down Look Partition (Dive)
- TEST-T1-F01-04: Yaw Left/Right Turn Partition
- TEST-T1-F01-05: No Face Present / Missing Landmarks Partition
"""

import cv2
import numpy as np

from e2e_tests.framework.assertions import assert_angle_in_bounds
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import (
    FACE_MODEL_3D,
    get_camera_matrix,
    solve_head_pose,
)


class TestTier1Feature01FaceMesh(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for head pose estimation."""

    def setUp(self) -> None:
        super().setUp()
        self.width = 640
        self.height = 480
        self.camera_matrix = get_camera_matrix(self.width, self.height)
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        self.tvec_gt = np.array([0.0, 0.0, 750.0], dtype=np.float64)

    def _project_landmarks(self, target_pitch: float, target_yaw: float, target_roll: float) -> np.ndarray:
        """Projects 3D face model points to 2D image coordinates using target Euler angles."""
        raw_p = np.radians(-target_pitch)
        raw_y = np.radians(-target_yaw)
        raw_r = np.radians(-target_roll)

        Rx = np.array(
            [[1.0, 0.0, 0.0],
             [0.0, np.cos(raw_p), -np.sin(raw_p)],
             [0.0, np.sin(raw_p), np.cos(raw_p)]],
            dtype=np.float64,
        )
        Ry = np.array(
            [[np.cos(raw_y), 0.0, np.sin(raw_y)],
             [0.0, 1.0, 0.0],
             [-np.sin(raw_y), 0.0, np.cos(raw_y)]],
            dtype=np.float64,
        )
        Rz = np.array(
            [[np.cos(raw_r), -np.sin(raw_r), 0.0],
             [np.sin(raw_r), np.cos(raw_r), 0.0],
             [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )

        R = Rz @ Ry @ Rx
        rvec, _ = cv2.Rodrigues(R)
        pts_2d, _ = cv2.projectPoints(FACE_MODEL_3D, rvec, self.tvec_gt, self.camera_matrix, self.dist_coeffs)
        return pts_2d.reshape(-1, 2)

    def test_t1_f01_01_center_neutral_gaze(self) -> None:
        """TEST-T1-F01-01: Center neutral gaze evaluates to pitch/yaw/roll within [-5.0°, +5.0°]."""
        pts = self._project_landmarks(target_pitch=0.0, target_yaw=0.0, target_roll=0.0)
        success, rvec, tvec, pitch, yaw, roll = solve_head_pose(pts, self.camera_matrix, self.dist_coeffs)

        self.assertTrue(success, "Pose estimation failed on neutral gaze")
        self.assertIsNotNone(rvec)
        self.assertIsNotNone(tvec)
        assert_angle_in_bounds(pitch, yaw, roll, context="TEST-T1-F01-01")
        self.assertAlmostEqual(pitch, 0.0, delta=2.0)
        self.assertAlmostEqual(yaw, 0.0, delta=2.0)
        self.assertAlmostEqual(roll, 0.0, delta=2.0)

    def test_t1_f01_02_pitch_up_look(self) -> None:
        """TEST-T1-F01-02: Pitch up look evaluates to positive pitch in [+15.0°, +30.0°] (Climb)."""
        pts = self._project_landmarks(target_pitch=20.0, target_yaw=0.0, target_roll=0.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(pts, self.camera_matrix, self.dist_coeffs)

        self.assertTrue(success, "Pose estimation failed on pitch up look")
        self.assertGreaterEqual(pitch, 15.0)
        self.assertLessEqual(pitch, 30.0)
        self.assertAlmostEqual(yaw, 0.0, delta=3.0)
        self.assertAlmostEqual(roll, 0.0, delta=3.0)

    def test_t1_f01_03_pitch_down_look(self) -> None:
        """TEST-T1-F01-03: Pitch down look evaluates to negative pitch in [-30.0°, -15.0°] (Dive)."""
        pts = self._project_landmarks(target_pitch=-20.0, target_yaw=0.0, target_roll=0.0)
        success, _, _, pitch, yaw, roll = solve_head_pose(pts, self.camera_matrix, self.dist_coeffs)

        self.assertTrue(success, "Pose estimation failed on pitch down look")
        self.assertLessEqual(pitch, -15.0)
        self.assertGreaterEqual(pitch, -30.0)
        self.assertAlmostEqual(yaw, 0.0, delta=3.0)
        self.assertAlmostEqual(roll, 0.0, delta=3.0)

    def test_t1_f01_04_yaw_left_right_turn(self) -> None:
        """TEST-T1-F01-04: Left turn gives negative yaw [-35°, -15°], right turn gives positive yaw [+15°, +35°]."""
        pts_left = self._project_landmarks(target_pitch=0.0, target_yaw=-25.0, target_roll=0.0)
        success_l, _, _, _, yaw_l, _ = solve_head_pose(pts_left, self.camera_matrix, self.dist_coeffs)
        self.assertTrue(success_l, "Pose estimation failed on left yaw turn")
        self.assertLessEqual(yaw_l, -15.0)
        self.assertGreaterEqual(yaw_l, -35.0)

        pts_right = self._project_landmarks(target_pitch=0.0, target_yaw=25.0, target_roll=0.0)
        success_r, _, _, _, yaw_r, _ = solve_head_pose(pts_right, self.camera_matrix, self.dist_coeffs)
        self.assertTrue(success_r, "Pose estimation failed on right yaw turn")
        self.assertGreaterEqual(yaw_r, 15.0)
        self.assertLessEqual(yaw_r, 35.0)

    def test_t1_f01_05_no_face_present(self) -> None:
        """TEST-T1-F01-05: Missing or blank face input safely returns success=False and 0.0° angles without exception."""
        # 1. No face detected (None landmarks)
        success_none, rvec_none, tvec_none, p_none, y_none, r_none = solve_head_pose(
            None, self.camera_matrix, self.dist_coeffs
        )
        self.assertFalse(success_none, "Expected failure on None landmarks")
        self.assertIsNone(rvec_none)
        self.assertIsNone(tvec_none)
        self.assertEqual((p_none, y_none, r_none), (0.0, 0.0, 0.0))

        # 2. Corrupt / invalid non-finite landmarks (e.g. occlusion)
        nan_pts = np.full((6, 2), np.nan, dtype=np.float64)
        success_nan, rvec_nan, tvec_nan, p_nan, y_nan, r_nan = solve_head_pose(
            nan_pts, self.camera_matrix, self.dist_coeffs
        )
        self.assertFalse(success_nan, "Expected failure on NaN landmarks")
        self.assertIsNone(rvec_nan)
        self.assertIsNone(tvec_nan)
        self.assertEqual((p_nan, y_nan, r_nan), (0.0, 0.0, 0.0))
