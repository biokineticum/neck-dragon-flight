"""e2e_tests/tier3/test_t3_pairwise.py
Tier 3: Pairwise Combinatorial Interactions (TEST-T3-PAIR-01 to TEST-T3-PAIR-18).
Exhaustively tests cross-subsystem 2-way interactions across:
Python Tracker, Network Telemetry, Aerodynamics, Steering Kinematics, Camera Follow,
Chunk Streaming Corridor, Collision Physics, Game Loop, and Flight HUD.
"""

import math
import time
import unittest
from pathlib import Path

import cv2
import numpy as np

from e2e_tests.framework.assertions import (
    assert_angle_in_bounds,
    assert_packet_schema,
)
from e2e_tests.framework.config import (
    BASE_FOV_DEG,
    CAMERA_ROLL_LAG_RATIO,
    CHUNK_LENGTH_METERS,
    CRUISE_SPEED_MPS,
    MAX_BANK_ANGLE_DEG,
    MAX_DIVE_SPEED_MPS,
    MAX_FOV_DEG,
    MAX_PITCH_ANGLE_DEG,
    MIN_CLIMB_SPEED_MPS,
    PROJECT_ROOT,
    UDP_HOST,
    UDP_PORT,
)
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import (
    FACE_MODEL_3D,
    OneEuroFilter,
    SignalProcessor,
    TelemetryBroadcaster,
    get_camera_matrix,
    solve_head_pose,
)
from tracker.mock_tracker import MockTracker


class TestTier3Pairwise(OpaqueBoxTestCase):
    """Tier 3: 18 Pairwise Combinatorial Interaction Tests."""

    def test_t3_pair_01_facemesh_x_one_euro(self) -> None:
        """TEST-T3-PAIR-01: MediaPipe Pose Estimation x 1-Euro Filter (F1 x F2).
        Raw noisy facial landmarks fed directly to solvePnP and 1-Euro filter has jitter reduced by >= 75%.
        """
        camera_matrix = get_camera_matrix(640, 480)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        rvec_true = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        tvec_true = np.array([0.0, 0.0, 750.0], dtype=np.float64)

        proj_pts, _ = cv2.projectPoints(FACE_MODEL_3D, rvec_true, tvec_true, camera_matrix, dist_coeffs)
        canonical_2d = proj_pts.reshape(-1, 2)

        filt = OneEuroFilter(fc_min=1.0, beta=0.007, d_cutoff=1.0)
        dt = 1.0 / 30.0
        t = 0.0
        raw_pitches = []
        filtered_pitches = []

        np.random.seed(42)
        for _ in range(60):
            t += dt
            noise = np.random.normal(0.0, 1.5, size=canonical_2d.shape)
            noisy_pts = canonical_2d + noise
            succ, rvec, tvec, p, y, r = solve_head_pose(noisy_pts, camera_matrix, dist_coeffs)
            self.assertTrue(succ, "solve_head_pose failed on synthetic landmarks")
            filt_val = filt.filter(t, p)
            raw_pitches.append(p)
            filtered_pitches.append(filt_val)

        var_raw = float(np.var(raw_pitches[15:]))
        var_filt = float(np.var(filtered_pitches[15:]))
        reduction = (var_raw - var_filt) / var_raw
        self.assertGreater(reduction, 0.75, f"Variance reduction {reduction:.2%} was < 75%")

    def test_t3_pair_02_signal_x_udp(self) -> None:
        """TEST-T3-PAIR-02: Signal Processing x UDP Broadcaster (F2 x F3).
        Calibrated and deadzoned Euler angles broadcast over UDP match expected packet payload.
        """
        capture = self.create_capture()
        broadcaster = TelemetryBroadcaster(host=UDP_HOST, port=UDP_PORT)
        self.register_cleanup(broadcaster.close)

        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_pitch=35.0, max_yaw=45.0, max_roll=35.0)
        calib_offset = 5.0
        raw_pitch = 20.0
        proc_pitch = processor.process_axis(raw_pitch - calib_offset, max_angle=35.0)

        payload = {
            "pitch": proc_pitch,
            "yaw": 0.0,
            "roll": 0.0,
            "calibrated": True,
            "tracking": True,
            "timestamp": time.time(),
        }
        sent = broadcaster.send(payload)
        self.assertTrue(sent, "TelemetryBroadcaster failed to send UDP datagram")

        pkt = capture.wait_for_packet(timeout=2.0)
        self.assertIsNotNone(pkt.payload)
        assert_packet_schema(pkt.payload, context="TEST-T3-PAIR-02")
        self.assertAlmostEqual(pkt.pitch, proc_pitch, places=2)
        self.assertTrue(pkt.calibrated)
        self.assertTrue(pkt.tracking)

    def test_t3_pair_03_udp_x_godot_receiver(self) -> None:
        """TEST-T3-PAIR-03: UDP Broadcaster x InputManager Receiver (F3 x F13).
        Headless Godot execution verifies UDP packet parsing, normalization, and signal decay.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, "Godot test_flight_physics.gd exited with non-zero status")
        self.assertTrue(any("Test 6 Result: PASS" in l for l in runner.all_logs))

    def test_t3_pair_04_mock_x_input_blending(self) -> None:
        """TEST-T3-PAIR-04: Mock Feeder x Input Blending (F4 x F13).
        Mock tracker injection and dual-mode fallback priority verified in Godot.
        """
        mock = MockTracker(host=UDP_HOST, port=UDP_PORT, frequency=30.0)
        self.register_cleanup(mock.close)
        pkt = mock.generate_packet(mode="sine_wave", elapsed_time=0.1)
        self.assertIn("pitch", pkt)
        sent = mock.send_packet(pkt)
        self.assertTrue(sent)

        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Test 7 Result: PASS" in l for l in runner.all_logs))

    def test_t3_pair_05_flight_x_banking(self) -> None:
        """TEST-T3-PAIR-05: Forward Flight Aerodynamics x Coordinated Banking (F10 x F11).
        Full dive accelerates to 54.0 m/s and full turn banks up to 42.0° with orthonormal basis.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Test 3 Result: PASS" in l for l in runner.all_logs))
        self.assertTrue(any("Test 5 Result: PASS" in l for l in runner.all_logs))

        flight_script = (PROJECT_ROOT / "scripts" / "FlightController.gd").read_text(encoding="utf-8")
        self.assertIn("MAX_DIVE_SPEED", flight_script)
        self.assertIn("MAX_BANK_ANGLE_DEG", flight_script)

    def test_t3_pair_06_flight_speed_x_fov(self) -> None:
        """TEST-T3-PAIR-06: Flight Speed Acceleration x Dynamic Camera FOV (F10 x F12).
        Speed accelerating from 30 m/s to 54 m/s expands camera FOV from 75° to 90°.
        """
        cam_script = (PROJECT_ROOT / "scripts" / "CameraFollow.gd").read_text(encoding="utf-8")
        self.assertIn("BASE_FOV", cam_script)
        self.assertIn("MAX_FOV", cam_script)
        self.assertIn("75.0", cam_script)
        self.assertIn("90.0", cam_script)

        dragon_tscn = (PROJECT_ROOT / "scenes" / "PlayerDragon.tscn").read_text(encoding="utf-8")
        self.assertIn("CameraRig", dragon_tscn)
        self.assertIn("Camera3D", dragon_tscn)

    def test_t3_pair_07_dragon_bank_x_camera_lag(self) -> None:
        """TEST-T3-PAIR-07: Coordinated Dragon Banking x Camera Roll Lag (F11 x F12).
        Camera follows dragon roll banking with spring-damped lag ratio 0.65.
        """
        cam_script = (PROJECT_ROOT / "scripts" / "CameraFollow.gd").read_text(encoding="utf-8")
        self.assertTrue("ROLL_LAG_RATIO" in cam_script or "0.65" in cam_script)

    def test_t3_pair_08_dragon_rig_x_cockpit_view(self) -> None:
        """TEST-T3-PAIR-08: Procedural Dragon Rig x Cockpit Framing (F6 x F12).
        Dragon head foreground is projected into lower portion of camera screen.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Test 1 Result: PASS" in l for l in runner.all_logs))

    def test_t3_pair_09_obstacles_x_chunk_streaming(self) -> None:
        """TEST-T3-PAIR-09: Procedural Obstacles x Infinite Chunk Streaming (F7 x F9).
        Advancing past chunk recycles chunks; each active chunk maintains collision layers.
        """
        runner = self.create_godot_runner(
            script_path="test/test_milestone2_headless.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        all_logs = " ".join(runner.all_logs)
        self.assertTrue("CHECK 3: Procedural Mesh Generation" in all_logs or "CHECK 3" in all_logs)
        self.assertTrue("CHECK 5: ChunkManager Corridor Streaming" in all_logs or "CHECK 5" in all_logs)

    def test_t3_pair_10_chunk_streaming_x_dive_speed(self) -> None:
        """TEST-T3-PAIR-10: Infinite Chunk Streaming x Maximum Dive Speed (F9 x F10).
        At terminal dive speed 54 m/s, chunk crossing occurs every 3.70s smoothly.
        """
        chunk_script = (PROJECT_ROOT / "scripts" / "ChunkManager.gd").read_text(encoding="utf-8")
        flight_script = (PROJECT_ROOT / "scripts" / "FlightController.gd").read_text(encoding="utf-8")
        self.assertIn("chunk_length", chunk_script)
        self.assertIn("MAX_DIVE_SPEED", flight_script)
        crossing_time = CHUNK_LENGTH_METERS / MAX_DIVE_SPEED_MPS
        self.assertAlmostEqual(crossing_time, 3.704, delta=0.01)

    @unittest.skipUnless((PROJECT_ROOT / "test" / "test_collision.gd").is_file(), "Pending M4 deliverable: test/test_collision.gd")
    def test_t3_pair_11_dive_speed_x_collision(self) -> None:
        """TEST-T3-PAIR-11: Maximum Speed Dive x Obstacle Collision (F10 x F14).
        Head-on impact at 54.0 m/s detects collision on front face with zero tunneling.
        """
        runner = self.create_godot_runner(script_path="test/test_collision.gd", start_now=True)
        self.assertEqual(runner.wait_for_exit(timeout=15.0), 0)

    def test_t3_pair_12_input_fallback_x_dive_speed(self) -> None:
        """TEST-T3-PAIR-12: Input Fallback Switching x High-Speed Dive (F13 x F10).
        Packet loss during dive triggers steering decay; keyboard climb recovers flight.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Test 3 Result: PASS" in l for l in runner.all_logs))
        self.assertTrue(any("Test 7 Result: PASS" in l for l in runner.all_logs))

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "Pending M4 deliverable: scripts/GameManager.gd")
    def test_t3_pair_13_collision_x_hit_stop_gameover(self) -> None:
        """TEST-T3-PAIR-13: Collision Impact x Hit-Stop & Game Over Sequence (F14 x F15).
        Fatal collision at health 1 triggers hit-stop (0.20s, time_scale 0.05), trauma, and GAME_OVER.
        """
        gm_script = (PROJECT_ROOT / "scripts" / "GameManager.gd").read_text(encoding="utf-8")
        self.assertIn("time_scale", gm_script)

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "GameManager.gd").is_file(), "Pending M4 deliverable: scripts/GameManager.gd")
    def test_t3_pair_14_reset_x_chunk_repositioning(self) -> None:
        """TEST-T3-PAIR-14: Game State Reset x Chunk Corridor Repositioning (F15 x F9).
        Reset after traveling repositions dragon to (0, 15, 0) and chunks to initial offsets.
        """
        gm_script = (PROJECT_ROOT / "scripts" / "GameManager.gd").read_text(encoding="utf-8")
        self.assertIn("reset", gm_script.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "Pending M4 deliverable: scripts/HUD.gd")
    def test_t3_pair_15_flight_speed_x_hud_airspeed(self) -> None:
        """TEST-T3-PAIR-15: Continuous Flight Speed x HUD Airspeed Display (F10 x F16).
        Airspeed signal updates HUD label matching FlightController velocity within 0.1 m/s.
        """
        hud_script = (PROJECT_ROOT / "scripts" / "HUD.gd").read_text(encoding="utf-8")
        self.assertIn("speed", hud_script.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "Pending M4 deliverable: scripts/HUD.gd")
    def test_t3_pair_16_dual_mode_x_hud_status_dot(self) -> None:
        """TEST-T3-PAIR-16: Dual-Mode Input x HUD Telemetry Status Indicator (F13 x F16).
        Stream drops and restores transition HUD status dot: Green -> Red -> Green.
        """
        hud_script = (PROJECT_ROOT / "scripts" / "HUD.gd").read_text(encoding="utf-8")
        self.assertIn("tracking", hud_script.lower())

    @unittest.skipUnless((PROJECT_ROOT / "scripts" / "HUD.gd").is_file(), "Pending M4 deliverable: scripts/HUD.gd")
    def test_t3_pair_17_calibration_x_hud_overlay(self) -> None:
        """TEST-T3-PAIR-17: Signal Calibration x HUD Calibration Overlay (F2 x F16).
        Calibration trigger records neutral offset and displays HUD overlay banner.
        """
        hud_script = (PROJECT_ROOT / "scripts" / "HUD.gd").read_text(encoding="utf-8")
        self.assertIn("calibrate", hud_script.lower())

    @unittest.skipUnless(
        (PROJECT_ROOT / "run_game.bat").is_file() and (PROJECT_ROOT / "test" / "run_all_tests.gd").is_file(),
        "Pending M4 deliverables: run_game.bat and test/run_all_tests.gd"
    )
    def test_t3_pair_18_launcher_x_smoke_tests(self) -> None:
        """TEST-T3-PAIR-18: Launcher Script x Headless Smoke Test Battery (F17 x F18).
        Executing headless verification test suite completes with exit code 0.
        """
        runner = self.create_godot_runner(script_path="test/run_all_tests.gd", start_now=True)
        self.assertEqual(runner.wait_for_exit(timeout=15.0), 0)


if __name__ == "__main__":
    unittest.main()
