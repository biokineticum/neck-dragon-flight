"""
test_udp_loopback.py - Integration tests for UDP datagram transmission, pacing, and socket resilience.
"""

import sys
import os
import json
import time
import socket
import unittest

# Ensure tracker package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from tracker.head_tracker import TelemetryBroadcaster, RatePacer
from tracker.mock_tracker import MockTracker


class TestUDPLoopback(unittest.TestCase):
    """Test suite validating local UDP datagram networking, rate pacing, and socket resilience."""

    def test_loopback_transmission_fidelity(self):
        """
        Verifies that UDP datagrams emitted by TelemetryBroadcaster are faithfully
        received and decoded by a local UDP listener.
        """
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", 0))  # Bind to ephemeral port
        port = recv_sock.getsockname()[1]
        recv_sock.settimeout(2.0)

        broadcaster = TelemetryBroadcaster(host="127.0.0.1", port=port)

        payload = {
            "pitch": 18.25,
            "yaw": -30.5,
            "roll": 12.0,
            "calibrated": True,
            "tracking": True,
            "timestamp": round(time.time(), 4)
        }

        sent = broadcaster.send(payload)
        self.assertTrue(sent, "Failed to send packet via broadcaster")

        data, addr = recv_sock.recvfrom(2048)
        decoded = json.loads(data.decode("utf-8"))

        self.assertEqual(decoded["pitch"], 18.25)
        self.assertEqual(decoded["yaw"], -30.5)
        self.assertEqual(decoded["roll"], 12.0)
        self.assertTrue(decoded["calibrated"])
        self.assertTrue(decoded["tracking"])
        self.assertEqual(decoded["timestamp"], payload["timestamp"])

        broadcaster.close()
        recv_sock.close()

    def test_mock_tracker_loopback(self):
        """
        Verifies that MockTracker transmits datagrams received by a UDP socket.
        """
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", 0))
        port = recv_sock.getsockname()[1]
        recv_sock.settimeout(2.0)

        with MockTracker(host="127.0.0.1", port=port, frequency=30.0, amplitude=15.0) as tracker:
            packet = tracker.generate_packet(mode="dive", elapsed_time=0.1)
            tracker.send_packet(packet)

            data, _ = recv_sock.recvfrom(2048)
            decoded = json.loads(data.decode("utf-8"))
            self.assertEqual(decoded["pitch"], -15.0)
            self.assertTrue(decoded["calibrated"])
            self.assertTrue(decoded["tracking"])

        recv_sock.close()

    def test_rate_pacer_timing(self):
        """
        Verifies that RatePacer paces frames without cumulative drift.
        30 iterations at 60 Hz (target 0.50 s) should execute in 0.50 +/- 0.08 s.
        """
        target_fps = 60.0
        pacer = RatePacer(target_fps=target_fps)
        iterations = 30

        t0 = time.perf_counter()
        for _ in range(iterations):
            pacer.sleep()
        elapsed = time.perf_counter() - t0

        expected = iterations / target_fps  # 0.50 s
        self.assertAlmostEqual(
            elapsed, expected, delta=0.08,
            msg=f"RatePacer elapsed time {elapsed:.3f}s deviated from expected {expected:.3f}s"
        )

    def test_windows_connreset_resilience(self):
        """
        Verifies that transmitting UDP packets to an unlistened localhost port does not crash
        with ConnectionResetError (WinError 10054).
        """
        # Find a port that is definitely closed
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_sock.bind(("127.0.0.1", 0))
        unused_port = temp_sock.getsockname()[1]
        temp_sock.close()

        broadcaster = TelemetryBroadcaster(host="127.0.0.1", port=unused_port)

        # Transmitting several packets to closed port should not raise unhandled exception
        try:
            for _ in range(5):
                broadcaster.send({"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "calibrated": True, "tracking": True, "timestamp": time.time()})
                time.sleep(0.01)
        except ConnectionResetError as err:
            self.fail(f"Broadcaster raised unhandled ConnectionResetError: {err}")
        finally:
            broadcaster.close()

    def test_mock_tracker_background_thread_lifecycle(self):
        """
        Verifies that MockTracker.start_background runs as daemon and cleanly shuts down.
        """
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", 0))
        port = recv_sock.getsockname()[1]
        recv_sock.settimeout(0.5)

        received_packets = []

        tracker = MockTracker(host="127.0.0.1", port=port, frequency=50.0, amplitude=10.0)
        thread = tracker.start_background(mode="sine_wave")
        self.assertTrue(thread.is_alive())

        t_start = time.time()
        while time.time() - t_start < 0.2:
            try:
                data, _ = recv_sock.recvfrom(2048)
                received_packets.append(json.loads(data.decode("utf-8")))
            except socket.timeout:
                pass

        tracker.stop()
        self.assertFalse(thread.is_alive(), "Background thread did not terminate")
        self.assertGreater(len(received_packets), 3, "Did not receive sufficient packets from background thread")

        tracker.close()
        recv_sock.close()


if __name__ == "__main__":
    unittest.main()
