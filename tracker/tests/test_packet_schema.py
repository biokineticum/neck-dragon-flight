"""
test_packet_schema.py - Validates Interface Contract 1 telemetry packet compliance.
"""

import sys
import os
import json
import time
import unittest
from typing import Dict, Any

# Ensure tracker package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tracker.mock_tracker import MockTracker


def validate_packet_schema(packet: Dict[str, Any]) -> bool:
    """
    Validates packet structure strictly against Interface Contract 1:
    - Keys: pitch, yaw, roll, calibrated, tracking, timestamp
    - Types: pitch, yaw, roll, timestamp -> (int, float)
             calibrated, tracking -> bool
    - Limits: pitch in [-35.0, 35.0]
              yaw in [-45.0, 45.0]
              roll in [-35.0, 35.0]
    """
    required_keys = {"pitch", "yaw", "roll", "calibrated", "tracking", "timestamp"}
    if not isinstance(packet, dict):
        return False
    if not required_keys.issubset(packet.keys()):
        return False
    if not isinstance(packet["pitch"], (int, float)):
        return False
    if not isinstance(packet["yaw"], (int, float)):
        return False
    if not isinstance(packet["roll"], (int, float)):
        return False
    if not isinstance(packet["calibrated"], bool):
        return False
    if not isinstance(packet["tracking"], bool):
        return False
    if not isinstance(packet["timestamp"], (int, float)):
        return False
    if not (-35.0 <= packet["pitch"] <= 35.0):
        return False
    if not (-45.0 <= packet["yaw"] <= 45.0):
        return False
    if not (-35.0 <= packet["roll"] <= 35.0):
        return False
    return True


class TestPacketSchema(unittest.TestCase):
    """Test suite for telemetry packet schema conformance."""

    def test_valid_packet_schema(self):
        pkt = {
            "pitch": 15.0,
            "yaw": -20.5,
            "roll": 5.25,
            "calibrated": True,
            "tracking": True,
            "timestamp": time.time()
        }
        self.assertTrue(validate_packet_schema(pkt))

    def test_json_roundtrip_fidelity(self):
        pkt = {
            "pitch": -32.5,
            "yaw": 44.0,
            "roll": 0.0,
            "calibrated": False,
            "tracking": True,
            "timestamp": round(time.time(), 4)
        }
        raw_bytes = json.dumps(pkt, separators=(',', ':')).encode("utf-8")
        decoded = json.loads(raw_bytes.decode("utf-8"))
        self.assertEqual(decoded["pitch"], -32.5)
        self.assertEqual(decoded["yaw"], 44.0)
        self.assertEqual(decoded["roll"], 0.0)
        self.assertFalse(decoded["calibrated"])
        self.assertTrue(decoded["tracking"])
        self.assertTrue(validate_packet_schema(decoded))

    def test_mock_tracker_all_modes_schema_conformance(self):
        tracker = MockTracker(amplitude=30.0, period=2.0)
        modes = [
            "neutral", "dive", "climb", "roll_left", "roll_right",
            "yaw_left", "yaw_right", "sine_wave", "spiral", "step",
            "tracking_loss", "uncalibrated"
        ]

        for mode in modes:
            for elapsed in [0.0, 0.5, 1.0, 1.5, 2.0]:
                pkt = tracker.generate_packet(mode, elapsed_time=elapsed)
                self.assertTrue(
                    validate_packet_schema(pkt),
                    f"Mode '{mode}' at t={elapsed} produced invalid packet: {pkt}"
                )

    def test_rejection_of_missing_keys(self):
        incomplete = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "tracking": True}
        self.assertFalse(validate_packet_schema(incomplete))

    def test_rejection_of_out_of_range_values(self):
        base = {
            "pitch": 0.0, "yaw": 0.0, "roll": 0.0,
            "calibrated": True, "tracking": True, "timestamp": time.time()
        }
        self.assertFalse(validate_packet_schema({**base, "pitch": 35.1}))
        self.assertFalse(validate_packet_schema({**base, "pitch": -35.1}))
        self.assertFalse(validate_packet_schema({**base, "yaw": 45.1}))
        self.assertFalse(validate_packet_schema({**base, "yaw": -45.1}))
        self.assertFalse(validate_packet_schema({**base, "roll": 35.1}))
        self.assertFalse(validate_packet_schema({**base, "roll": -35.1}))

    def test_rejection_of_invalid_types(self):
        base = {
            "pitch": 0.0, "yaw": 0.0, "roll": 0.0,
            "calibrated": True, "tracking": True, "timestamp": time.time()
        }
        self.assertFalse(validate_packet_schema({**base, "pitch": "0.0"}))
        self.assertFalse(validate_packet_schema({**base, "calibrated": 1}))  # bool required
        self.assertFalse(validate_packet_schema({**base, "tracking": "true"}))


if __name__ == "__main__":
    unittest.main()
