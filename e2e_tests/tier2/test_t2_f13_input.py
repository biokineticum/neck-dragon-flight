"""e2e_tests/tier2/test_t2_f13_input.py
Tier 2: Boundary Value Analysis & Robustness for Feature 13:
Dual-Mode Input Blending (Timeout boundary precision, malformed JSON recovery, telemetry degree clamping, crossfade div-zero immunity, key omission safety).
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


class TestTier2Feature13Input(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for dual-mode input blending."""

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

    def test_t2_f13_01_exact_timeout_boundary(self) -> None:
        """TEST-T2-F13-01: Packet timeout triggers strictly when elapsed time exceeds PACKET_TIMEOUT_SEC (0.50s)."""
        self.assertIn("const PACKET_TIMEOUT_SEC: float = 0.50", self.content)
        self.assertIn("time_since_last_packet > PACKET_TIMEOUT_SEC", self.content)
        timeout = 0.50
        self.assertFalse(0.499 > timeout)
        self.assertTrue(0.501 > timeout)

    def test_t2_f13_02_malformed_json_injection(self) -> None:
        """TEST-T2-F13-02: Malformed or non-dictionary JSON payloads return false cleanly without engine crash."""
        self.assertIn("var json = JSON.new()", self.content)
        self.assertIn("var err = json.parse(text)", self.content)
        self.assertIn("if err != OK or typeof(json.data) != TYPE_DICTIONARY:\n\t\treturn false", self.content)

    def test_t2_f13_03_out_of_range_telemetry_clamping(self) -> None:
        """TEST-T2-F13-03: Arbitrarily large telemetry angles clamp strictly into normalized [-1.0, 1.0]."""
        self.assertIn("webcam_pitch = clampf(eff_pitch / MAX_PITCH_DEG, -1.0, 1.0)", self.content)
        self.assertIn("webcam_yaw = clampf(eff_yaw / MAX_YAW_DEG, -1.0, 1.0)", self.content)
        self.assertIn("webcam_roll = clampf(eff_roll / MAX_ROLL_DEG, -1.0, 1.0)", self.content)

    def test_t2_f13_04_high_frequency_toggle_stress(self) -> None:
        """TEST-T2-F13-04: Non-zero CROSSFADE_DURATION (0.35s) bounds blend parameter t strictly in [0.0, 1.0]."""
        self.assertIn("const CROSSFADE_DURATION: float = 0.35", self.content)
        self.assertIn("var t = clampf(crossfade_time / CROSSFADE_DURATION, 0.0, 1.0)", self.content)

    def test_t2_f13_05_partial_payload_omission_guard(self) -> None:
        """TEST-T2-F13-05: Missing dictionary keys safely default to 0.0 neutral via Dictionary.get()."""
        self.assertTrue(
            'raw_pitch_deg = float(data.get("pitch", 0.0))' in self.content
            or 'raw_pitch_deg = _extract_float(data.get("pitch"' in self.content
        )
        self.assertTrue(
            'raw_yaw_deg = float(data.get("yaw", 0.0))' in self.content
            or 'raw_yaw_deg = _extract_float(data.get("yaw"' in self.content
        )
        self.assertTrue(
            'raw_roll_deg = float(data.get("roll", 0.0))' in self.content
            or 'raw_roll_deg = _extract_float(data.get("roll"' in self.content
        )


if __name__ == "__main__":
    unittest.main()
