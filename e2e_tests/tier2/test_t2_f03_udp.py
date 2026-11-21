"""e2e_tests/tier2/test_t2_f03_udp.py
Tier 2: Boundary Value Analysis & Corner Cases for Feature 3:
Local UDP Broadcaster (Rate boundaries, flood bursts, MTU payload size, port collisions, rebinding).

Test Catalog:
- TEST-T2-F03-01: Minimum Update Rate Boundary (30 Hz)
- TEST-T2-F03-02: Burst Flood Rate Boundary (120 Hz Burst)
- TEST-T2-F03-03: Maximum Datagram Buffer Size Boundary (< 512 bytes)
- TEST-T2-F03-04: Port In-Use Collision Handling (WSAEADDRINUSE / OSError)
- TEST-T2-F03-05: Immediate Port Re-bind Lifecycle
"""

import json
import socket
import time

from e2e_tests.framework.config import MAX_DATAGRAM_BYTES, UDP_HOST, UDP_PORT
from e2e_tests.framework.test_base import OpaqueBoxTestCase
from tracker.head_tracker import TelemetryBroadcaster


class TestTier2Feature03Udp(OpaqueBoxTestCase):
    """Tier 2 boundary value analysis for UDP telemetry broadcaster."""

    def test_t2_f03_01_minimum_update_rate_boundary(self) -> None:
        """TEST-T2-F03-01: Broadcaster configured at lower spec bound (30 Hz) generates >= 28 packets/s."""
        capture = self.create_capture()
        broadcaster = self.create_broadcaster(target_fps=30.0)
        broadcaster.set_neutral()

        packets = capture.collect_packets(count=15, timeout=2.0)
        self.assertGreaterEqual(len(packets), 15)
        measured_fps = capture.compute_fps(packets=packets)
        self.assertGreaterEqual(measured_fps, 28.0, f"Measured FPS {measured_fps:.2f} < 28.0 Hz")

    def test_t2_f03_02_burst_flood_rate_boundary(self) -> None:
        """TEST-T2-F03-02: Transmitting high-frequency burst (120 packets) executes cleanly without socket errors."""
        broadcaster = TelemetryBroadcaster(host=UDP_HOST, port=UDP_PORT)
        self.register_cleanup(broadcaster.close)

        payload = {
            "pitch": 5.0,
            "yaw": -5.0,
            "roll": 2.0,
            "calibrated": True,
            "tracking": True,
            "timestamp": time.time(),
        }
        for _ in range(120):
            success = broadcaster.send(payload)
            self.assertTrue(success, "Broadcaster send failed during high-frequency burst")

    def test_t2_f03_03_maximum_datagram_buffer_size(self) -> None:
        """TEST-T2-F03-03: Serialized JSON packet payload length strictly < 512 bytes."""
        payload = {
            "pitch": -34.9999999999,
            "yaw": 44.9999999999,
            "roll": -34.9999999999,
            "calibrated": True,
            "tracking": True,
            "timestamp": 1731600000.1234567,
        }
        raw_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.assertLess(
            len(raw_bytes),
            MAX_DATAGRAM_BYTES,
            f"Datagram length {len(raw_bytes)} exceeded maximum buffer limit {MAX_DATAGRAM_BYTES} bytes",
        )

    def test_t2_f03_04_port_in_use_collision_handling(self) -> None:
        """TEST-T2-F03-04: Binding second listener socket to active port raises OSError / AddressInUse."""
        self._ensure_port_clean(UDP_HOST, UDP_PORT, retries=15, delay=0.1)

        s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s1.bind((UDP_HOST, UDP_PORT))
        except OSError:
            time.sleep(0.3)
            s1.bind((UDP_HOST, UDP_PORT))
        self.register_cleanup(s1.close)

        s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.register_cleanup(s2.close)

        # On Windows without SO_REUSEADDR, binding to an in-use port raises OSError (WSAEADDRINUSE)
        with self.assertRaises(OSError, msg="Second socket bound to port without raising collision"):
            s2.bind((UDP_HOST, UDP_PORT))

    def test_t2_f03_05_immediate_port_rebind_lifecycle(self) -> None:
        """TEST-T2-F03-05: Closing socket with SO_REUSEADDR allows immediate rebinding within 50ms without timeout."""
        self._ensure_port_clean(UDP_HOST, UDP_PORT, retries=15, delay=0.1)
        s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s1.bind((UDP_HOST, UDP_PORT))
        s1.close()

        # Re-bind immediately (< 50ms)
        s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.register_cleanup(s2.close)
        s2.bind((UDP_HOST, UDP_PORT))
        self.assertEqual(s2.getsockname(), (UDP_HOST, UDP_PORT))
