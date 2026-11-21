"""e2e_tests/tier1/test_t1_f13_input.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 13:
Dual-Mode Input Blending (Pure webcam telemetry, keyboard override priority, crossfade release, UDP packet timeout, steering decay).
"""

import unittest
from pathlib import Path
from typing import List, Optional

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.godot_runner import GodotDiscovery, GodotProcessManager
from e2e_tests.framework.test_base import OpaqueBoxTestCase


def is_godot_available() -> bool:
    try:
        GodotDiscovery.find_binary()
        return True
    except FileNotFoundError:
        return False


class TestTier1Feature13Input(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for dual-mode input blending."""

    _cached_engine_logs: Optional[List[str]] = None

    @classmethod
    def get_engine_logs(cls) -> List[str]:
        if cls._cached_engine_logs is None:
            if not is_godot_available():
                return []
            manager = GodotProcessManager(script_path="test/test_flight_physics.gd")
            manager.start()
            manager.wait_for_exit(timeout=15.0)
            cls._cached_engine_logs = list(manager.all_logs)
        return cls._cached_engine_logs

    def setUp(self) -> None:
        super().setUp()
        self.input_mgr_path = PROJECT_ROOT / "scripts" / "InputManager.gd"
        self.assertTrue(self.input_mgr_path.is_file(), f"InputManager.gd missing at {self.input_mgr_path}")
        self.content = self.input_mgr_path.read_text(encoding="utf-8")

    def test_t1_f13_01_pure_webcam_mode(self) -> None:
        """TEST-T1-F13-01: Valid telemetry packet sets WEBCAM control mode and normalizes angles."""
        self.assertIn("const UDP_PORT: int = 42425", self.content)
        self.assertIn("func process_json_packet(text: String) -> bool:", self.content)
        self.assertIn('current_control_mode = "WEBCAM"', self.content)
        self.assertIn("func is_webcam_active() -> bool:", self.content)
        self.assertIn("func get_control_mode() -> String:", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Injected packet -> Active: true, Mode: WEBCAM" in l for l in logs))
            self.assertTrue(any("UDP packet injection, normalization, and signal decay verified" in l for l in logs))

    def test_t1_f13_02_keyboard_override_priority(self) -> None:
        """TEST-T1-F13-02: Manual keyboard/mouse input takes immediate 100% authority override."""
        self.assertIn("if is_manual_pressed:", self.content)
        self.assertIn("manual_controls_were_active = true", self.content)
        self.assertIn("is_crossfading = false", self.content)
        self.assertIn('current_control_mode = "KEYBOARD_MOUSE"', self.content)
        self.assertIn("final_pitch = manual_pitch", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Key pressed -> Mode: KEYBOARD_MOUSE" in l for l in logs))

    def test_t1_f13_03_keyboard_release_crossfade(self) -> None:
        """TEST-T1-F13-03: Releasing manual controls executes smooth 0.35s crossfade back to webcam telemetry."""
        self.assertIn("const CROSSFADE_DURATION: float = 0.35", self.content)
        self.assertIn('current_control_mode = "BLENDED"', self.content)
        self.assertIn("clampf(crossfade_time / CROSSFADE_DURATION, 0.0, 1.0)", self.content)
        self.assertIn("final_yaw = lerpf(blend_start_yaw, webcam_yaw, t)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("During crossfade (0.10s) -> Mode: BLENDED" in l for l in logs))
            self.assertTrue(any("After crossfade (0.43s) -> Mode: WEBCAM" in l for l in logs))
            self.assertTrue(any("Dual-mode priority override and 0.35s crossfade verified" in l for l in logs))

    def test_t1_f13_04_udp_stream_timeout_detection(self) -> None:
        """TEST-T1-F13-04: Silence exceeding PACKET_TIMEOUT_SEC (0.50s) marks head-tracking inactive."""
        self.assertIn("const PACKET_TIMEOUT_SEC: float = 0.50", self.content)
        self.assertIn("if time_since_last_packet > PACKET_TIMEOUT_SEC:", self.content)
        self.assertIn("head_tracking_active = false", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("After 0.60s silence -> Active: false" in l for l in logs))

    def test_t1_f13_05_steering_decay_on_signal_loss(self) -> None:
        """TEST-T1-F13-05: Telemetry timeout smoothly decays steering inputs toward neutral at DECAY_RATE (8.0/s)."""
        self.assertIn("const DECAY_RATE: float = 8.0", self.content)
        self.assertIn("webcam_pitch = move_toward(webcam_pitch, 0.0, DECAY_RATE * delta)", self.content)
        self.assertIn("webcam_yaw = move_toward(webcam_yaw, 0.0, DECAY_RATE * delta)", self.content)
        self.assertIn("webcam_roll = move_toward(webcam_roll, 0.0, DECAY_RATE * delta)", self.content)

        if is_godot_available():
            logs = self.get_engine_logs()
            self.assertTrue(any("Decayed yaw: 0.0000" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
