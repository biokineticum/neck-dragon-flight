"""Base test case for opaque-box E2E testing with automatic resource cleanup.

Guarantees clean socket binding states on 127.0.0.1:42425 before and after every test,
preventing WinError 10048 / WSAEADDRINUSE across rapid sequential test runs.
"""

import socket
import time
import unittest
from typing import Any, Callable, List, Optional

from .config import (
    DEFAULT_GODOT_CONSOLE_PATH,
    GODOT_PROJECT_DIR,
    UDP_HOST,
    UDP_PORT,
)
from .godot_runner import GodotProcessManager
from .tracker_runner import TrackerProcessManager
from .udp_fixture import (
    MockUdpBroadcaster,
    UdpTelemetryCapture,
)


class OpaqueBoxTestCase(unittest.TestCase):
    """Base class for all E2E test cases across all four tiers.

    Enforces:
    - Pre-test and post-test socket cleanliness on UDP_PORT.
    - Automatic cleanup registration for child processes and network fixtures.
    - Deterministic assertion error messages.
    """

    def setUp(self) -> None:
        super().setUp()
        self._registered_cleanups: List[Callable[[], Any]] = []
        self._ensure_port_clean(UDP_HOST, UDP_PORT)

    def tearDown(self) -> None:
        # Run all registered cleanups in reverse order
        for cleanup_fn in reversed(self._registered_cleanups):
            try:
                cleanup_fn()
            except Exception:
                pass
        self._registered_cleanups.clear()

        # Ensure port is clean after test
        self._ensure_port_clean(UDP_HOST, UDP_PORT)
        super().tearDown()

    def register_cleanup(self, cleanup_fn: Callable[[], Any]) -> None:
        """Registers a callable to be executed during tearDown."""
        self._registered_cleanups.append(cleanup_fn)

    def _ensure_port_clean(self, host: str, port: int, retries: int = 5, delay: float = 0.05) -> None:
        """Verifies that the target UDP port is free to bind, waiting if needed.

        Note: Binding without SO_REUSEADDR allows Windows Winsock to raise WSAEADDRINUSE
        (WinError 10048) if the port is actively held by another process or lingering socket.
        """
        for attempt in range(retries):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.bind((host, port))
                sock.close()
                return  # Port is clean and bindable
            except OSError:
                sock.close()
                if attempt < retries - 1:
                    time.sleep(delay)

    # --------------------------------------------------------------------------
    # Managed Factory Helpers
    # --------------------------------------------------------------------------
    def create_broadcaster(
        self,
        host: str = UDP_HOST,
        port: int = UDP_PORT,
        target_fps: float = 60.0,
        start_now: bool = True,
    ) -> MockUdpBroadcaster:
        """Creates a managed MockUdpBroadcaster with automatic teardown."""
        broadcaster = MockUdpBroadcaster(host=host, port=port, target_fps=target_fps)
        self.register_cleanup(broadcaster.stop)
        if start_now:
            broadcaster.start()
        return broadcaster

    def create_capture(
        self,
        host: str = UDP_HOST,
        port: int = UDP_PORT,
        start_now: bool = True,
    ) -> UdpTelemetryCapture:
        """Creates a managed UdpTelemetryCapture with automatic teardown."""
        capture = UdpTelemetryCapture(host=host, port=port)
        self.register_cleanup(capture.stop)
        if start_now:
            capture.start()
        return capture

    def create_godot_runner(
        self,
        script_path: Optional[str] = None,
        scene_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        godot_bin: Optional[str] = None,
        start_now: bool = True,
    ) -> GodotProcessManager:
        """Creates a managed GodotProcessManager with automatic teardown."""
        runner = GodotProcessManager(
            script_path=script_path,
            scene_path=scene_path,
            extra_args=extra_args,
            godot_bin=godot_bin,
        )
        self.register_cleanup(runner.terminate)
        if start_now:
            runner.start()
        return runner

    def create_tracker_runner(
        self,
        use_mock: bool = False,
        extra_args: Optional[List[str]] = None,
        start_now: bool = True,
    ) -> TrackerProcessManager:
        """Creates a managed TrackerProcessManager with automatic teardown."""
        tracker = TrackerProcessManager(use_mock=use_mock, extra_args=extra_args)
        self.register_cleanup(tracker.terminate)
        if start_now:
            tracker.start()
        return tracker
