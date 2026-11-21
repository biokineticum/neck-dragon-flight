"""E2E Test Framework package.

Provides fixtures, process runners, assertions, and test base classes for
opaque-box testing of the First-Person Dragon Flying Game.
"""

from .assertions import (
    assert_angle_in_bounds,
    assert_control_mode,
    assert_deadzone_applied,
    assert_decay_rate,
    assert_jitter_suppressed,
    assert_packet_rate,
    assert_packet_schema,
    assert_state_transition,
    assert_vector_close,
)
from .config import (
    ACTION_CALIBRATE,
    ACTION_RESET_GAME,
    ACTION_STEER_DOWN,
    ACTION_STEER_LEFT,
    ACTION_STEER_RIGHT,
    ACTION_STEER_UP,
    CHUNK_LENGTH_METERS,
    CRUISE_SPEED_MPS,
    DEFAULT_GODOT_CONSOLE_PATH,
    DEFAULT_GODOT_GUI_PATH,
    GODOT_PROJECT_DIR,
    MAX_DIVE_SPEED_MPS,
    MIN_CLIMB_SPEED_MPS,
    PACKET_TIMEOUT_SEC,
    PROJECT_ROOT,
    TARGET_FPS,
    UDP_HOST,
    UDP_PORT,
)
from .godot_runner import GodotDiscovery, GodotProcessManager
from .test_base import OpaqueBoxTestCase
from .tracker_runner import TrackerProcessManager
from .udp_fixture import (
    CapturedPacket,
    FallbackInputSimulator,
    MockUdpBroadcaster,
    TelemetryPacket,
    UdpTelemetryCapture,
)

__all__ = [
    # Config
    "PROJECT_ROOT",
    "GODOT_PROJECT_DIR",
    "DEFAULT_GODOT_CONSOLE_PATH",
    "DEFAULT_GODOT_GUI_PATH",
    "UDP_HOST",
    "UDP_PORT",
    "PACKET_TIMEOUT_SEC",
    "TARGET_FPS",
    "CRUISE_SPEED_MPS",
    "MAX_DIVE_SPEED_MPS",
    "MIN_CLIMB_SPEED_MPS",
    "CHUNK_LENGTH_METERS",
    "ACTION_STEER_UP",
    "ACTION_STEER_DOWN",
    "ACTION_STEER_LEFT",
    "ACTION_STEER_RIGHT",
    "ACTION_CALIBRATE",
    "ACTION_RESET_GAME",
    # Assertions
    "assert_packet_schema",
    "assert_angle_in_bounds",
    "assert_packet_rate",
    "assert_vector_close",
    "assert_state_transition",
    "assert_control_mode",
    "assert_jitter_suppressed",
    "assert_deadzone_applied",
    "assert_decay_rate",
    # Fixtures & Runners
    "TelemetryPacket",
    "CapturedPacket",
    "MockUdpBroadcaster",
    "UdpTelemetryCapture",
    "FallbackInputSimulator",
    "GodotDiscovery",
    "GodotProcessManager",
    "TrackerProcessManager",
    "OpaqueBoxTestCase",
]
