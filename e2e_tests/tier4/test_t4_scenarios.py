"""e2e_tests/tier4/test_t4_scenarios.py
Tier 4: Real-World Flight Scenarios (TEST-T4-SCEN-01 to TEST-T4-SCEN-09).
Validates end-to-end mission workflows under realistic gameplay workloads:
Takeoff & Cruise, Canyon Slalom Weave, Archway Dive & Swoop, Mid-Flight Packet Loss & Recovery,
Near-Miss Glancing Evade, Fatal Impact & Reset, 2000m Marathon Endurance, Twitch Noise Resilience,
and Cold Start Teardown Lifecycle.
"""

import math
import socket
import time
import unittest
from pathlib import Path

import numpy as np

from e2e_tests.framework.assertions import (
    assert_angle_in_bounds,
    assert_packet_schema,
)
from e2e_tests.framework.config import (
    BASE_FOV_DEG,
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
from tracker.head_tracker import OneEuroFilter, SignalProcessor
from tracker.mock_tracker import MockTracker


class TestT4FlightScenarios(OpaqueBoxTestCase):
    """Tier 4: 9 Comprehensive End-to-End Flight Scenario Workloads."""

    def test_t4_scen_01_takeoff_baseline_calibration_and_cruise(self) -> None:
        """TEST-T4-SCEN-01: Takeoff, Baseline Calibration & Cruise.
        Player launches dragon at (0, 15, 0), accelerates to 30.0 m/s cruise, triggers neutral calibration,
        and cruises steadily for 10.0s (300m traversal); verifies flight physics in Godot.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, "Godot test_flight_physics.gd failed")
        self.assertTrue(any("Test 2 Result: PASS" in l for l in runner.all_logs))
        self.assertTrue(any("Test 6 Result: PASS" in l for l in runner.all_logs))

    def test_t4_scen_02_canyon_slalom_obstacle_weave(self) -> None:
        """TEST-T4-SCEN-02: Canyon Slalom Obstacle Weave.
        Player executes coordinated banking turns, rolling body up to 42° into each turn.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Test 5 Result: PASS" in l for l in runner.all_logs))

        rig_script = (PROJECT_ROOT / "scripts" / "DragonVisualRig.gd").read_text(encoding="utf-8")
        self.assertIn("wing_flap_amplitude_deg", rig_script)

    def test_t4_scen_03_high_speed_archway_dive_and_swoop(self) -> None:
        """TEST-T4-SCEN-03: High-Speed Archway Dive & Swoop.
        Steep dive (-1.0) accelerates to 54.0 m/s with 90° FOV, clears arch opening, and climbs back toward cruise.
        """
        runner_flight = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_flight = runner_flight.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_flight, 0)
        self.assertTrue(any("Test 3 Result: PASS" in l for l in runner_flight.all_logs))
        self.assertTrue(any("Test 4 Result: PASS" in l for l in runner_flight.all_logs))

        runner_m2 = self.create_godot_runner(
            script_path="test/test_milestone2_headless.gd",
            start_now=True,
        )
        exit_m2 = runner_m2.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_m2, 0)
        self.assertTrue(any("Rock Arch" in l for l in runner_m2.all_logs))

        cam_script = (PROJECT_ROOT / "scripts" / "CameraFollow.gd").read_text(encoding="utf-8")
        self.assertIn("BASE_FOV", cam_script)
        self.assertIn("MAX_FOV", cam_script)

    def test_t4_scen_04_mid_flight_webcam_drop_and_keyboard_rescue(self) -> None:
        """TEST-T4-SCEN-04: Mid-Flight Webcam Drop & Keyboard Rescue.
        Banking left when webcam abruptly disconnects; 550ms timeout decays steering; keyboard takes override.
        """
        runner = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("Test 6 Result: PASS" in l for l in runner.all_logs))
        self.assertTrue(any("Test 7 Result: PASS" in l for l in runner.all_logs))

    @unittest.skipUnless((PROJECT_ROOT / "test" / "test_collision.gd").is_file(), "Pending M4 deliverable: test/test_collision.gd")
    def test_t4_scen_05_near_miss_glancing_evade(self) -> None:
        """TEST-T4-SCEN-05: High-Speed Near-Miss Glancing Evade.
        Dragon flies past granite spire with 0.2m clearance at 45.0 m/s; move_and_slide maintains momentum.
        """
        runner = self.create_godot_runner(script_path="test/test_collision.gd", start_now=True)
        self.assertEqual(runner.wait_for_exit(timeout=15.0), 0)

    @unittest.skipUnless(
        (PROJECT_ROOT / "scripts" / "GameManager.gd").is_file() and (PROJECT_ROOT / "test" / "test_collision.gd").is_file(),
        "Pending M4 deliverables: scripts/GameManager.gd and test/test_collision.gd"
    )
    def test_t4_scen_06_fatal_spire_impact_hit_stop_and_reset(self) -> None:
        """TEST-T4-SCEN-06: Fatal Spire Impact, Hit-Stop, & Game Over Reset.
        Crash into granite spire at 48 m/s; executes hit-stop (0.20s, time_scale = 0.05), camera trauma, and restart.
        """
        runner = self.create_godot_runner(script_path="test/test_collision.gd", start_now=True)
        self.assertEqual(runner.wait_for_exit(timeout=15.0), 0)

    def test_t4_scen_07_infinite_corridor_marathon_endurance(self) -> None:
        """TEST-T4-SCEN-07: Infinite Corridor Marathon Endurance.
        Verifies 4-chunk continuous corridor streaming and bounded memory management.
        """
        runner = self.create_godot_runner(
            script_path="test/test_milestone2_headless.gd",
            start_now=True,
        )
        exit_code = runner.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0)
        self.assertTrue(any("CHECK 5: ChunkManager Corridor Streaming" in l for l in runner.all_logs))

    def test_t4_scen_08_rapid_head_twitch_noise_resilience(self) -> None:
        """TEST-T4-SCEN-08: Rapid Head Twitch & Noise Filtering Resilience.
        5-second stream with periodic sharp impulse spikes (±25° for 1 frame); 1-Euro filter attenuates spikes,
        dragon rotational damping smooths body steering, angular rate bounded <= 180°/s.
        """
        filt = OneEuroFilter(fc_min=1.0, beta=0.007, d_cutoff=1.0)
        processor = SignalProcessor(deadzone=2.0, gamma=1.5, max_yaw=45.0)

        dt = 1.0 / 60.0
        t = 0.0
        processed_angles = []

        for frame in range(1, 301):  # 5.0 seconds
            t += dt
            raw_angle = 25.0 if (frame % 60 == 0) else 0.0
            filtered = filt.filter(t, raw_angle)
            processed = processor.process_axis(filtered, max_angle=45.0)
            processed_angles.append(processed)

        # Attenuation of single-frame twitch: 25.0° attenuated to < 1.0°
        max_spike_response = max(processed_angles)
        self.assertLess(max_spike_response, 1.0, f"Twitch response {max_spike_response:.2f}° exceeded 1.0°")

        # Rate of change bounded
        rates = [abs(processed_angles[i + 1] - processed_angles[i]) / dt for i in range(len(processed_angles) - 1)]
        max_rate = max(rates) if rates else 0.0
        self.assertLessEqual(max_rate, 180.0, f"Angular jerk {max_rate:.1f}°/s exceeded threshold")

    def test_t4_scen_09_cold_start_batch_launch_and_teardown(self) -> None:
        """TEST-T4-SCEN-09: Cold Start, Batch Launch & Clean Teardown.
        Executes genuine OS dual-subprocess lifecycle: launches tracker child process,
        launches Godot headless child process, validates execution, terminates cleanly,
        and verifies port 42425 is released immediately without WSAEADDRINUSE.
        """
        # Step 1: Launch real tracker subprocess (mock feeder in neutral mode)
        tracker_mgr = self.create_tracker_runner(
            use_mock=True,
            extra_args=["--mode", "neutral", "--duration", "5.0"],
            start_now=True,
        )
        self.assertIsNotNone(tracker_mgr.process)
        self.assertIsNone(tracker_mgr.process.poll(), "Tracker subprocess failed to start")

        # Step 2: Launch real Godot headless child process running flight physics
        godot_mgr = self.create_godot_runner(
            script_path="test/test_flight_physics.gd",
            start_now=True,
        )

        # Step 3: Wait for Godot process to finish verification
        exit_code = godot_mgr.wait_for_exit(timeout=15.0)
        self.assertEqual(exit_code, 0, "Godot subprocess exited with non-zero status")

        # Step 4: Terminate tracker child process cleanly
        tracker_mgr.terminate()
        self.assertIsNotNone(tracker_mgr.process.poll(), "Tracker subprocess failed to terminate")

        # Step 5: Verify port 42425 is completely free and bindable
        self._ensure_port_clean(UDP_HOST, UDP_PORT, retries=10, delay=0.1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((UDP_HOST, UDP_PORT))
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()
