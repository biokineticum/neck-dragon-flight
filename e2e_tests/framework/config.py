"""Framework configuration and constants for E2E opaque-box testing.

Centralizes environment paths, network protocol definitions, flight physics constraints,
and timeout thresholds to ensure deterministic pass/fail semantics across all tiers.
"""

from pathlib import Path

# ==============================================================================
# Filesystem Paths
# ==============================================================================
PROJECT_ROOT = Path(r"c:\Users\Lenovo\Documents\test agentów")
E2E_ROOT = PROJECT_ROOT / "e2e_tests"
FRAMEWORK_ROOT = E2E_ROOT / "framework"

TRACKER_DIR = PROJECT_ROOT / "tracker"
TRACKER_SCRIPT = TRACKER_DIR / "head_tracker.py"
MOCK_TRACKER_SCRIPT = TRACKER_DIR / "mock_tracker.py"
TRACKER_REQUIREMENTS = TRACKER_DIR / "requirements.txt"

GODOT_PROJECT_DIR = PROJECT_ROOT
PROJECT_GODOT = GODOT_PROJECT_DIR / "project.godot"
MAIN_SCENE = GODOT_PROJECT_DIR / "scenes" / "Main.tscn"
SMOKE_TEST_SCRIPT = GODOT_PROJECT_DIR / "test" / "run_all_tests.gd"

SETUP_DOC = PROJECT_ROOT / "SETUP.md"
INTEGRATION_DOC = PROJECT_ROOT / "INTEGRATION.md"
RUN_GAME_BAT = PROJECT_ROOT / "run_game.bat"

# Default known location for Godot 4.7.2 console binary on Windows
DEFAULT_GODOT_CONSOLE_PATH = Path(
    r"C:\Users\Lenovo\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe"
)
DEFAULT_GODOT_GUI_PATH = Path(
    r"C:\Users\Lenovo\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64.exe"
)

# ==============================================================================
# Network Protocol Contracts (Interface Contract 1)
# ==============================================================================
UDP_HOST = "127.0.0.1"
UDP_PORT = 42425
SOCKET_BUFFER_SIZE = 1048576  # 1 MB receive buffer to prevent burst drops
MAX_DATAGRAM_BYTES = 512       # Maximum expected JSON packet size

PACKET_TIMEOUT_SEC = 0.50      # Timeout threshold after which fallback triggers
TARGET_FPS = 60.0              # Nominal telemetry broadcast rate
MIN_PACKET_RATE_HZ = 30.0      # Lower bound of acceptable rate
MAX_PACKET_RATE_HZ = 65.0      # Upper bound of acceptable rate (with timing tolerance)

REQUIRED_TELEMETRY_KEYS = {
    "pitch",
    "yaw",
    "roll",
    "calibrated",
    "tracking",
    "timestamp",
}

# ==============================================================================
# Euler Angle & Steering Constraints
# ==============================================================================
PITCH_BOUNDS_DEG = (-35.0, 35.0)  # Positive = Look Up / Climb, Negative = Look Down / Dive
YAW_BOUNDS_DEG = (-45.0, 45.0)    # Positive = Turn Right, Negative = Turn Left
ROLL_BOUNDS_DEG = (-35.0, 35.0)   # Positive = Tilt Right, Negative = Tilt Left

DEADZONE_THRESHOLD_DEG = 2.0      # Continuous deadzone threshold in degrees
SIGNAL_DECAY_RATE = 8.0           # Decay speed: angle units / second on packet timeout
KEYBOARD_OVERRIDE_CROSSFADE_SEC = 0.35  # Blending window when manual input released

# ==============================================================================
# Flight Physics Constraints
# ==============================================================================
CRUISE_SPEED_MPS = 30.0           # Nominal level flight speed
MAX_DIVE_SPEED_MPS = 54.0         # Terminal velocity in sustained dive
MIN_CLIMB_SPEED_MPS = 18.0        # Minimum flight speed during sustained climb
MAX_BANK_ANGLE_DEG = 42.0         # Maximum dragon body roll angle into turns
MAX_PITCH_ANGLE_DEG = 32.0        # Maximum pitch inclination angle
ACCELERATION_DIVE_MPS2 = 12.0     # Dive acceleration constant
DECELERATION_CLIMB_MPS2 = 8.0     # Climb deceleration constant
DRAG_DECELERATION_MPS2 = 4.0      # Aerodynamic drag recovery to cruise
MAX_ANGULAR_JERK_DPS = 180.0      # Angular rate limit (deg/sec) to avoid gimbal snapping

# ==============================================================================
# Camera & Viewport Constraints
# ==============================================================================
BASE_FOV_DEG = 75.0               # Field of view at cruise speed (30 m/s)
MAX_FOV_DEG = 90.0                # Expanded field of view at dive speed (54 m/s)
CAMERA_ROLL_LAG_RATIO = 0.65      # Spring-damper lag ratio for cockpit camera follow
CAMERA_LOCAL_POS = (0.0, 1.4, -0.2) # First-person saddle/rider local coordinates

# ==============================================================================
# Mountain Realm & Terrain Corridor
# ==============================================================================
CHUNK_LENGTH_METERS = 200.0       # Length of each procedural terrain segment
ACTIVE_CHUNK_COUNT = 4            # Exactly 4 chunks maintained in world
TOTAL_ACTIVE_RANGE_METERS = 800.0 # Active corridor window = 4 * 200m
MIN_PASSABLE_GAP_METERS = 8.0     # Minimum navigable clearance between canyon walls/spires
DRAGON_COLLISION_RADIUS_M = 1.2   # Capsule hull radius of player dragon
DRAGON_COLLISION_HEIGHT_M = 3.6   # Capsule hull height of player dragon

# ==============================================================================
# Game Rules & Health
# ==============================================================================
INITIAL_PLAYER_HEALTH = 3         # 3 hearts
HIT_STOP_DURATION_SEC = 0.20      # Hit-stop freeze frame duration on fatal impact
HIT_STOP_TIME_SCALE = 0.05        # Engine.time_scale during hit-stop
MAX_TRAUMA_SHAKE = 1.0            # Camera shake intensity on impact
INVULNERABILITY_WINDOW_SEC = 1.0  # Safe window after non-fatal impact

# ==============================================================================
# Input Action Names (Mapped in project.godot)
# ==============================================================================
ACTION_STEER_UP = "steer_up"
ACTION_STEER_DOWN = "steer_down"
ACTION_STEER_LEFT = "steer_left"
ACTION_STEER_RIGHT = "steer_right"
ACTION_CALIBRATE = "calibrate"
ACTION_RESET_GAME = "reset_game"
