"""e2e_tests/tier1/test_t1_f03_udp.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 3:
Local UDP Broadcaster (Port 42425, JSON Schema, Encoding, Loopback, Non-blocking).

Test Catalog:
- TEST-T1-F03-01: Nominal Datagram Transmission Partition (30-65 Hz)
- TEST-T1-F03-02: JSON Schema Conformance Partition (Interface Contract 1)
- TEST-T1-F03-03: UTF-8 Encoding Conformance Partition
- TEST-T1-F03-04: Loopback Interface Binding Partition (127.0.0.1:42425)
- TEST-T1-F03-05: Non-Blocking Fire-and-Forget Partition
"""

import json
import time

from e2e_tests.framework.assertions import (
    assert_packet_schema,
)
from e2e_tests.framework.config import UDP_HOST, UDP_PORT
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import TelemetryBroadcaster


class TestTier1Feature03Udp(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for UDP telemetry broadcaster."""

    def test_t1_f03_01_nominal_datagram_transmission(self) -> None:
        """TEST-T1-F03-01: Broadcaster transmits datagrams at nominal rate between 30 Hz and 65 Hz."""
        capture = self.create_capture()
        broadcaster = self.create_broadcaster(target_fps=60.0)
        broadcaster.set_telemetry(pitch=5.0, yaw=-5.0, roll=0.0)

        packets = capture.collect_packets(count=20, timeout=2.0)
        self.assertGreaterEqual(len(packets), 20)
        measured_rate = capture.assert_fps(expected_min=30.0, expected_max=65.0, packets=packets)
        self.assertGreaterEqual(measured_rate, 30.0)

    def test_t1_f03_02_json_schema_conformance(self) -> None:
        """TEST-T1-F03-02: Received datagram conforms strictly to Interface Contract 1 schema."""
        capture = self.create_capture()
        broadcaster = self.create_broadcaster(target_fps=30.0, start_now=False)
        broadcaster.set_telemetry(pitch=-12.5, yaw=22.0, roll=-8.0, calibrated=True, tracking=True)
        broadcaster.start()

        pkt = capture.wait_for_packet(timeout=1.5)
        self.assertIsNotNone(pkt, "Did not receive UDP packet within timeout")
        self.assertIsNone(pkt.parse_error, f"Packet had parse error: {pkt.parse_error}")
        self.assertIsNotNone(pkt.payload)
        assert_packet_schema(pkt.payload, context="TEST-T1-F03-02")
        self.assertAlmostEqual(pkt.pitch, -12.5, places=2)
        self.assertAlmostEqual(pkt.yaw, 22.0, places=2)
        self.assertAlmostEqual(pkt.roll, -8.0, places=2)
        self.assertTrue(pkt.calibrated)
        self.assertTrue(pkt.tracking)

    def test_t1_f03_03_utf8_encoding_conformance(self) -> None:
        """TEST-T1-F03-03: Datagram bytes decode cleanly as valid UTF-8 without errors."""
        capture = self.create_capture()
        broadcaster = self.create_broadcaster()
        broadcaster.set_neutral()

        pkt = capture.wait_for_packet(timeout=1.5)
        self.assertIsNotNone(pkt, "Did not receive packet")
        try:
            text = pkt.raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            self.fail(f"Datagram bytes failed UTF-8 decoding: {e}")
        self.assertIn('"pitch"', text)
        self.assertIn('"timestamp"', text)

    def test_t1_f03_04_loopback_interface_binding(self) -> None:
        """TEST-T1-F03-04: Broadcaster binds strictly to 127.0.0.1:42425 (loopback interface)."""
        broadcaster = TelemetryBroadcaster(host=UDP_HOST, port=UDP_PORT)
        self.register_cleanup(broadcaster.close)
        self.assertEqual(broadcaster.host, "127.0.0.1")
        self.assertEqual(broadcaster.port, 42425)
        self.assertEqual(broadcaster.dest_addr, ("127.0.0.1", 42425))

    def test_t1_f03_05_non_blocking_fire_and_forget(self) -> None:
        """TEST-T1-F03-05: Broadcaster sends 100 packets to unlistened port without blocking or crashing."""
        broadcaster = TelemetryBroadcaster(host=UDP_HOST, port=UDP_PORT)
        self.register_cleanup(broadcaster.close)

        payload = {
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0,
            "calibrated": True,
            "tracking": True,
            "timestamp": time.time(),
        }
        t0 = time.perf_counter()
        for _ in range(100):
            sent = broadcaster.send(payload)
            self.assertTrue(sent)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.20, f"Broadcaster send loop blocked: {elapsed:.3f}s for 100 packets")
