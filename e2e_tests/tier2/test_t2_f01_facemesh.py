"""e2e_tests/tier2/test_t2_f01_facemesh.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 1:
MediaPipe FaceMesh & SolvePnP Pose Estimation.

Test Catalog:
- TEST-T2-F01-01: Pitch Upper Limit Clamping (+35.0°)
- TEST-T2-F01-02: Pitch Lower Limit Clamping (-35.0°)
- TEST-T2-F01-03: Yaw Extreme Clamping (±45.0°)
- TEST-T2-F01-04: Roll Extreme Clamping (±35.0°)
- TEST-T2-F01-05: Intermittent Occlusion & Recovery Corner Case
"""

import cv2
import numpy as np

from e2e_tests.framework.assertions import assert_angle_in_bounds
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import (
    FACE_MODEL_3D,
    SignalProcessor,
    get_camera_matrix,
    solve_head_pose,
)


class TestTier2Feature01FaceMesh(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for head pose estimation and limit clamping."""

    def setUp(self) -> None:
        super().setUp()
        self.width = 640
        self.height = 480
        self.camera_matrix = get_camera_matrix(self.width, self.height)
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        self.tvec_gt = np.array([0.0, 0.0, 750.0], dtype=np.float64)
        self.processor = SignalProcessor(deadzone=2.0, max_pitch=35.0, max_yaw=45.0, max_roll=35.0)

    def _project_landmarks(self, target_pitch: float, target_yaw: float, target_roll: float) -> np.ndarray:
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

    def test_t2_f01_01_pitch_upper_limit_clamping(self) -> None:
        """TEST-T2-F01-01: Pitch at and beyond +35.0° saturates cleanly at +35.0° without overflow."""
        out_boundary = self.processor.process_axis(35.0, max_angle=35.0)
        out_beyond = self.processor.process_axis(50.0, max_angle=35.0)
        self.assertAlmostEqual(out_boundary, 35.0, places=3)
        self.assertAlmostEqual(out_beyond, 35.0, places=3)
        self.assertLessEqual(out_beyond, 35.0)

    def test_t2_f01_02_pitch_lower_limit_clamping(self) -> None:
        """TEST-T2-F01-02: Pitch at and below -35.0° saturates cleanly at -35.0°."""
        out_boundary = self.processor.process_axis(-35.0, max_angle=35.0)
        out_below = self.processor.process_axis(-50.0, max_angle=35.0)
        self.assertAlmostEqual(out_boundary, -35.0, places=3)
        self.assertAlmostEqual(out_below, -35.0, places=3)
        self.assertGreaterEqual(out_below, -35.0)

    def test_t2_f01_03_yaw_extreme_clamping(self) -> None:
        """TEST-T2-F01-03: Yaw at extremes (-45.0° and +45.0°) saturates strictly within [-45.0°, +45.0°]."""
        out_pos = self.processor.process_axis(60.0, max_angle=45.0)
        out_neg = self.processor.process_axis(-60.0, max_angle=45.0)
        self.assertAlmostEqual(out_pos, 45.0, places=3)
        self.assertAlmostEqual(out_neg, -45.0, places=3)
        assert_angle_in_bounds(0.0, out_pos, 0.0)
        assert_angle_in_bounds(0.0, out_neg, 0.0)

    def test_t2_f01_04_roll_extreme_clamping(self) -> None:
        """TEST-T2-F01-04: Roll at extremes (-35.0° and +35.0°) saturates strictly within [-35.0°, +35.0°]."""
        out_pos = self.processor.process_axis(45.0, max_angle=35.0)
        out_neg = self.processor.process_axis(-45.0, max_angle=35.0)
        self.assertAlmostEqual(out_pos, 35.0, places=3)
        self.assertAlmostEqual(out_neg, -35.0, places=3)
        assert_angle_in_bounds(0.0, 0.0, out_pos)
        assert_angle_in_bounds(0.0, 0.0, out_neg)

    def test_t2_f01_05_occlusion_and_recovery(self) -> None:
        """TEST-T2-F01-05: Occlusion (lost landmarks) followed by face reacquisition recovers cleanly without NaN or jump."""
        valid_pts = self._project_landmarks(target_pitch=10.0, target_yaw=-15.0, target_roll=5.0)
        nan_pts = np.full((6, 2), np.nan, dtype=np.float64)

        # 1. Valid tracking
        s1, r1, t1, p1, y1, r_1 = solve_head_pose(valid_pts, self.camera_matrix, self.dist_coeffs)
        self.assertTrue(s1)
        self.assertAlmostEqual(p1, 10.0, delta=1.5)

        # 2. Occlusion (5 frames)
        for _ in range(5):
            s_occ, _, _, p_occ, y_occ, r_occ = solve_head_pose(nan_pts, self.camera_matrix, self.dist_coeffs)
            self.assertFalse(s_occ)
            self.assertEqual((p_occ, y_occ, r_occ), (0.0, 0.0, 0.0))

        # 3. Reacquisition
        s2, r2, t2, p2, y2, r_2 = solve_head_pose(valid_pts, self.camera_matrix, self.dist_coeffs)
        self.assertTrue(s2)
        self.assertAlmostEqual(p2, 10.0, delta=1.5)
        self.assertAlmostEqual(y2, -15.0, delta=1.5)
        self.assertAlmostEqual(r_2, 5.0, delta=1.5)
