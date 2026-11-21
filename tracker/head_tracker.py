"""
head_tracker.py - Real-Time Webcam Head-Tracking Subsystem for Dragon Flight

Milestone 1: Production-ready 3D head pose estimation, signal processing,
and UDP telemetry broadcasting for Godot game engine integration.

Pipeline Architecture:
    OpenCV VideoCapture -> MediaPipe FaceMesh (468 landmarks)
    -> 6 Canonical Anthropometric Landmarks
    -> cv2.solvePnP (Camera-Aligned Model, Iterative + Extrinsic Guess)
    -> Rodrigues + RQDecomp3x3 Euler Angle Decomposition
    -> Coordinate Inversion (Interface Contract 1 Compliance)
    -> Neutral Posture Calibration Zero-Offset
    -> 1-Euro Adaptive Low-Pass Filter
    -> Continuous Rescaled Deadzone & Non-linear Power Curve
    -> JSON UDP Broadcast on 127.0.0.1:42425 (RatePaced)
    -> OpenCV HUD Overlay with 3D Projected Axes (Optional GUI)
"""

import os
import sys
import json
import time
import math
import socket
import argparse
from typing import Dict, Any, Tuple, Optional, List

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Default Configuration & 3D Canonical Anthropometric Face Model
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 42425,
    "camera_id": 0,
    "frame_width": 640,
    "frame_height": 480,
    "target_fps": 30,
    "deadzone_degrees": 0.8,
    "max_angle_degrees": 25.0,
    "max_pitch": 35.0,
    "max_yaw": 45.0,
    "max_roll": 35.0,
    "sensitivity_pitch": 1.8,
    "sensitivity_yaw": 1.8,
    "sensitivity_roll": 1.5,
    "gamma": 1.0,
    "one_euro_filter": {
        "fc_min": 1.5,
        "beta": 0.015,
        "d_cutoff": 1.0
    },
    "preview": True,
    "mirror_preview": True,
    "invert_yaw": True,
    "invert_roll": True
}

# 6 Canonical MediaPipe FaceMesh indices
# 1: Nose tip, 152: Chin, 33: Anatomical right eye, 263: Anatomical left eye,
# 61: Anatomical right lip, 291: Anatomical left lip
LANDMARK_INDICES: List[int] = [1, 152, 33, 263, 61, 291]

# Camera-Aligned 3D Anthropometric Model (mm)
# Origin (0,0,0) at nose tip.
# +X: Viewer's right (anatomical left eye)
# +Y: Downwards (towards chin)
# +Z: Recessed away into the head
FACE_MODEL_3D: np.ndarray = np.array([
    [  0.0,   0.0,   0.0],  # 1: Nose tip
    [  0.0, 110.0,  35.0],  # 152: Chin (+Y down, +Z recessed)
    [-65.0, -50.0,  35.0],  # 33: Anatomical right eye (-X camera left, -Y up, +Z recessed)
    [ 65.0, -50.0,  35.0],  # 263: Anatomical left eye (+X camera right, -Y up, +Z recessed)
    [-40.0,  55.0,  30.0],  # 61: Anatomical right lip corner (-X camera left, +Y down, +Z recessed)
    [ 40.0,  55.0,  30.0]   # 291: Anatomical left lip corner (+X camera right, +Y down, +Z recessed)
], dtype=np.float64)


# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads JSON tracker configuration with recursive fallback to DEFAULT_CONFIG.
    Creates default configuration file if the target file does not exist.
    """
    if config_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "tracker_config.json")

    config = dict(DEFAULT_CONFIG)

    if not os.path.exists(config_path):
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except OSError:
            pass
        return config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
            if isinstance(user_cfg, dict):
                for k, v in user_cfg.items():
                    if k == "one_euro_filter" and isinstance(v, dict):
                        config["one_euro_filter"] = {
                            **DEFAULT_CONFIG["one_euro_filter"],
                            **v
                        }
                    else:
                        config[k] = v
    except (json.JSONDecodeError, OSError) as err:
        print(f"[WARN] Failed to read config from {config_path} ({err}). Using defaults.", file=sys.stderr)

    return config


# ---------------------------------------------------------------------------
# Camera Intrinsics & Pose Estimation Functions
# ---------------------------------------------------------------------------

def get_camera_matrix(frame_width: int, frame_height: int) -> np.ndarray:
    """Estimates pinhole camera intrinsic matrix based on frame dimensions."""
    focal_length = float(frame_width)
    center_x = float(frame_width) / 2.0
    center_y = float(frame_height) / 2.0
    return np.array([
        [focal_length, 0.0, center_x],
        [0.0, focal_length, center_y],
        [0.0, 0.0, 1.0]
    ], dtype=np.float64)


def solve_head_pose(
    image_points: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: Optional[np.ndarray] = None,
    prev_rvec: Optional[np.ndarray] = None,
    prev_tvec: Optional[np.ndarray] = None
) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray], float, float, float]:
    """
    Computes 3D head pose and Euler angles using cv2.solvePnP.
    Returns:
        (success, rvec, tvec, pitch, yaw, roll)
        where pitch, yaw, roll strictly adhere to Interface Contract 1:
        Positive Pitch = Climb, Negative Pitch = Dive
        Positive Yaw = Turn Right, Negative Yaw = Turn Left
        Positive Roll = Tilt Right, Negative Roll = Tilt Left
    """
    if dist_coeffs is None:
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    # Check landmark finiteness and structure prior to solvePnP
    if image_points is None or not isinstance(image_points, np.ndarray):
        return False, None, None, 0.0, 0.0, 0.0

    if image_points.shape != (6, 2) or not np.all(np.isfinite(image_points)):
        return False, None, None, 0.0, 0.0, 0.0

    use_guess = (prev_rvec is not None and prev_tvec is not None)
    try:
        if use_guess:
            rvec = prev_rvec.copy()
            tvec = prev_tvec.copy()
            success, rvec, tvec = cv2.solvePnP(
                FACE_MODEL_3D, image_points, camera_matrix, dist_coeffs,
                rvec=rvec, tvec=tvec, useExtrinsicGuess=True,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
        else:
            success, rvec, tvec = cv2.solvePnP(
                FACE_MODEL_3D, image_points, camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
    except (cv2.error, Exception):
        return False, None, None, 0.0, 0.0, 0.0

    if not success or rvec is None or tvec is None:
        return False, None, None, 0.0, 0.0, 0.0

    if not (np.all(np.isfinite(rvec)) and np.all(np.isfinite(tvec))):
        return False, None, None, 0.0, 0.0, 0.0

    try:
        # Convert rotation vector to 3x3 rotation matrix
        R, _ = cv2.Rodrigues(rvec)

        # RQ Decomposition factors R into Euler rotation angles
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(R)
        raw_pitch = float(angles[0])
        raw_yaw = float(angles[1])
        raw_roll = float(angles[2])

        if not (math.isfinite(raw_pitch) and math.isfinite(raw_yaw) and math.isfinite(raw_roll)):
            return False, None, None, 0.0, 0.0, 0.0

        # Sign convention mapping to Interface Contract 1:
        # Look Up (Climb): raw_pitch < 0 -> pitch = -raw_pitch > 0
        # Turn Right: raw_yaw < 0 -> yaw = -raw_yaw > 0
        # Tilt Right: raw_roll < 0 -> roll = -raw_roll > 0
        pitch = -raw_pitch
        yaw = -raw_yaw
        roll = -raw_roll

        return True, rvec, tvec, pitch, yaw, roll
    except (cv2.error, Exception):
        return False, None, None, 0.0, 0.0, 0.0


# ---------------------------------------------------------------------------
# Signal Processing: 1-Euro Filter & Deadzone Shaping
# ---------------------------------------------------------------------------

class OneEuroFilter:
    """
    1-Euro adaptive low-pass filter for noisy human input signals.
    Casiez et al., CHI 2012.
    """
    def __init__(
        self,
        t0: Optional[float] = None,
        x0: Optional[float] = None,
        dx0: float = 0.0,
        fc_min: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0
    ):
        self.fc_min = float(fc_min)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.t_prev = float(t0) if (t0 is not None and math.isfinite(t0)) else None
        self.x_prev = float(x0) if (x0 is not None and math.isfinite(x0)) else None
        self.dx_prev = float(dx0) if math.isfinite(dx0) else 0.0

    def reset(self, t: Optional[float] = None, x: Optional[float] = None, dx: float = 0.0) -> None:
        """Reset internal filter state."""
        self.t_prev = float(t) if (t is not None and math.isfinite(t)) else None
        self.x_prev = float(x) if (x is not None and math.isfinite(x)) else None
        self.dx_prev = float(dx) if math.isfinite(dx) else 0.0

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        """Compute exponential smoothing factor alpha with singularity guard."""
        safe_cutoff = max(1e-4, float(cutoff))
        safe_dt = max(1e-6, float(dt))
        tau = 1.0 / (2.0 * math.pi * safe_cutoff)
        denom = 1.0 + tau / safe_dt
        if denom <= 0.0:
            return 1.0
        return min(1.0, max(0.0, 1.0 / denom))

    def filter(self, t: float, x: float) -> float:
        """Filter input value x at monotonic timestamp t."""
        if not math.isfinite(x):
            # Reject NaN / Inf input; preserve existing state without poisoning
            return self.x_prev if (self.x_prev is not None and math.isfinite(self.x_prev)) else 0.0

        if self.t_prev is None or self.x_prev is None:
            self.t_prev = float(t)
            self.x_prev = float(x)
            self.dx_prev = 0.0
            return float(x)

        dt = float(t - self.t_prev)
        if dt <= 0.0:
            dt = 1e-4
        elif dt > 0.5:
            # Significant pause or camera stall; reset filter baseline
            self.t_prev = float(t)
            self.x_prev = float(x)
            self.dx_prev = 0.0
            return float(x)

        # 1. Estimate and smooth derivative
        dx = (x - self.x_prev) / dt
        alpha_d = self._alpha(self.d_cutoff, dt)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # 2. Dynamic cutoff frequency based on velocity
        fc = self.fc_min + self.beta * abs(dx_hat)
        alpha_x = self._alpha(fc, dt)
        x_hat = alpha_x * x + (1.0 - alpha_x) * self.x_prev

        # 3. Update history only if values are finite
        if math.isfinite(x_hat) and math.isfinite(dx_hat):
            self.t_prev = float(t)
            self.x_prev = float(x_hat)
            self.dx_prev = float(dx_hat)
            return float(x_hat)
        else:
            return self.x_prev if (self.x_prev is not None and math.isfinite(self.x_prev)) else 0.0


class SignalProcessor:
    """
    Applies continuous rescaled deadzone, non-linear gamma power curve, and limit clamping.
    Eliminates first-order step discontinuities at the deadzone boundary.
    """
    def __init__(
        self,
        deadzone: float = 2.0,
        gamma: float = 1.5,
        max_pitch: float = 35.0,
        max_yaw: float = 45.0,
        max_roll: float = 35.0
    ):
        self.deadzone = max(0.0, float(deadzone))
        self.gamma = max(0.01, float(gamma))
        self.max_pitch = float(max_pitch)
        self.max_yaw = float(max_yaw)
        self.max_roll = float(max_roll)

    def process_axis(self, angle: float, max_angle: float) -> float:
        """
        Rescales an angle outside deadzone to [0.0, max_angle] using gamma shaping.
        Guarantees exact 0.0 inside deadzone and strict saturation at max_angle.
        """
        if not math.isfinite(angle):
            return 0.0

        abs_angle = abs(angle)
        if abs_angle <= self.deadzone:
            return 0.0

        sign = 1.0 if angle >= 0.0 else -1.0
        denom = max_angle - self.deadzone
        if denom <= 0.0:
            return 0.0

        norm = (abs_angle - self.deadzone) / denom
        norm = min(1.0, max(0.0, norm))
        curved = norm ** self.gamma
        out = sign * curved * max_angle

        # Clamp to bounds
        return max(-max_angle, min(max_angle, out))

    def process(self, pitch: float, yaw: float, roll: float) -> Tuple[float, float, float]:
        """Processes all three axes with their respective interface bounds."""
        p = self.process_axis(pitch, self.max_pitch)
        y = self.process_axis(yaw, self.max_yaw)
        r = self.process_axis(roll, self.max_roll)
        return p, y, r


# ---------------------------------------------------------------------------
# Rate Pacing & UDP Telemetry Broadcaster
# ---------------------------------------------------------------------------

class RatePacer:
    """High-precision drift-free frame rate pacing loop."""
    def __init__(self, target_fps: float):
        self.target_fps = float(target_fps)
        self.period = 1.0 / max(1.0, self.target_fps)
        self.next_time = time.perf_counter()

    def sleep(self) -> None:
        self.next_time += self.period
        now = time.perf_counter()
        remaining = self.next_time - now
        if remaining > 0.0005:
            time.sleep(remaining)
        elif remaining < -self.period:
            # Resync if execution stalled by more than one full period
            self.next_time = time.perf_counter()


class TelemetryBroadcaster:
    """High-speed non-blocking UDP telemetry broadcaster emitting JSON datagrams."""
    def __init__(self, host: str = "127.0.0.1", port: int = 42425):
        self.host = str(host)
        self.port = int(port)
        self.dest_addr = (self.host, self.port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Windows-specific fix for ICMP Port Unreachable error 10054
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except OSError:
                pass
        self.sock.setblocking(False)

    def send(self, payload: Dict[str, Any]) -> bool:
        """Serializes payload to UTF-8 JSON and transmits UDP datagram."""
        try:
            data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            self.sock.sendto(data, self.dest_addr)
            return True
        except (BlockingIOError, socket.error, OSError, OverflowError, TypeError, ValueError):
            return False

    def close(self) -> None:
        """Closes the UDP socket safely."""
        try:
            self.sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Visual HUD & 3D Axes Projection
# ---------------------------------------------------------------------------

def draw_hud(
    frame: np.ndarray,
    pitch: float,
    yaw: float,
    roll: float,
    calibrated: bool,
    tracking: bool,
    fps: float,
    rvec: Optional[np.ndarray] = None,
    tvec: Optional[np.ndarray] = None,
    camera_matrix: Optional[np.ndarray] = None,
    dist_coeffs: Optional[np.ndarray] = None,
    mirrored: bool = False
) -> None:
    """Renders semi-transparent HUD overlay and 3D projected coordinate axes."""
    h, w = frame.shape[:2]

    # Draw 3D coordinate axes from nose tip if pose is available
    if rvec is not None and tvec is not None and camera_matrix is not None:
        if dist_coeffs is None:
            dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        axis_length = 75.0  # mm
        axis_points = np.array([
            [0.0, 0.0, 0.0],              # Origin (nose tip)
            [axis_length, 0.0, 0.0],      # X axis: Right (Red)
            [0.0, axis_length, 0.0],      # Y axis: Down (Green)
            [0.0, 0.0, -axis_length]      # Z axis: Forward towards player (Blue)
        ], dtype=np.float64)

        try:
            proj_pts, _ = cv2.projectPoints(axis_points, rvec, tvec, camera_matrix, dist_coeffs)
            proj_pts = proj_pts.reshape(-1, 2).astype(int)

            if mirrored:
                proj_pts[:, 0] = w - 1 - proj_pts[:, 0]

            p_origin = tuple(proj_pts[0])
            p_x = tuple(proj_pts[1])
            p_y = tuple(proj_pts[2])
            p_z = tuple(proj_pts[3])

            cv2.line(frame, p_origin, p_x, (0, 0, 255), 3)  # Red: X (Camera Right)
            cv2.line(frame, p_origin, p_y, (0, 255, 0), 3)  # Green: Y (Camera Down)
            cv2.line(frame, p_origin, p_z, (255, 0, 0), 3)  # Blue: Z (Pointing Out)
        except Exception:
            pass

    # Semi-transparent HUD box
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (330, 168), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # Direction annotations
    p_dir = "CLIMB" if pitch > 0.5 else ("DIVE" if pitch < -0.5 else "CENTER")
    y_dir = "RIGHT" if yaw > 0.5 else ("LEFT" if yaw < -0.5 else "CENTER")
    r_dir = "BANK R" if roll > 0.5 else ("BANK L" if roll < -0.5 else "LEVEL")

    # HUD Text items
    status_color = (0, 255, 0) if tracking else (0, 0, 255)
    calib_str = "CALIBRATED ('C' to re-zero)" if calibrated else "PRESS 'C' TO CALIBRATE"
    calib_color = (0, 255, 128) if calibrated else (0, 165, 255)

    cv2.putText(frame, f"HEAD TRACKER - {fps:.1f} FPS", (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(frame, f"Pitch: {pitch:+6.1f} deg  [{p_dir}]", (20, 56),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 255), 1)
    cv2.putText(frame, f"Yaw:   {yaw:+6.1f} deg  [{y_dir}]", (20, 78),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 255, 200), 1)
    cv2.putText(frame, f"Roll:  {roll:+6.1f} deg  [{r_dir}]", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 200), 1)
    cv2.putText(frame, calib_str, (20, 124),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, calib_color, 1)
    cv2.putText(frame, f"Tracking: {'ACTIVE' if tracking else 'LOST'}", (20, 142),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1)
    cv2.putText(frame, f"Mirror: {'ON' if mirrored else 'OFF'} ('M') | Invert: ('I')", (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 255, 180), 1)


# ---------------------------------------------------------------------------
# Main HeadTracker Application Class
# ---------------------------------------------------------------------------

class HeadTracker:
    """
    Encapsulates camera capture, landmark detection, pose extraction,
    signal conditioning, and UDP telemetry streaming.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        self.config = config if config is not None else load_config(config_path)

        # Network parameters
        self.host = self.config.get("host", "127.0.0.1")
        self.port = int(self.config.get("port", 42425))
        self.broadcaster = TelemetryBroadcaster(self.host, self.port)

        # Video & performance settings
        self.camera_id = int(self.config.get("camera_id", 0))
        self.frame_width = int(self.config.get("frame_width", 640))
        self.frame_height = int(self.config.get("frame_height", 480))
        self.target_fps = float(self.config.get("target_fps", 30))
        self.preview = bool(self.config.get("preview", True))
        self.mirror_preview = bool(self.config.get("mirror_preview", True))
        self.invert_yaw = bool(self.config.get("invert_yaw", True))
        self.invert_roll = bool(self.config.get("invert_roll", True))
        self.sensitivity_pitch = float(self.config.get("sensitivity_pitch", 1.8))
        self.sensitivity_yaw = float(self.config.get("sensitivity_yaw", 1.8))
        self.sensitivity_roll = float(self.config.get("sensitivity_roll", 1.5))

        # Camera intrinsics
        self.camera_matrix = get_camera_matrix(self.frame_width, self.frame_height)
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # Signal processing parameters
        self.deadzone = float(self.config.get("deadzone_degrees", 2.0))
        self.gamma = float(self.config.get("gamma", 1.5))
        self.max_pitch = float(self.config.get("max_pitch", 35.0))
        self.max_yaw = float(self.config.get("max_yaw", 45.0))
        self.max_roll = float(self.config.get("max_roll", 35.0))

        # Filters
        filter_cfg = self.config.get("one_euro_filter", {})
        fc_min = float(filter_cfg.get("fc_min", 1.0))
        beta = float(filter_cfg.get("beta", 0.007))
        d_cutoff = float(filter_cfg.get("d_cutoff", 1.0))

        self.filter_pitch = OneEuroFilter(fc_min=fc_min, beta=beta, d_cutoff=d_cutoff)
        self.filter_yaw = OneEuroFilter(fc_min=fc_min, beta=beta, d_cutoff=d_cutoff)
        self.filter_roll = OneEuroFilter(fc_min=fc_min, beta=beta, d_cutoff=d_cutoff)

        self.processor = SignalProcessor(
            deadzone=self.deadzone,
            gamma=self.gamma,
            max_pitch=self.max_pitch,
            max_yaw=self.max_yaw,
            max_roll=self.max_roll
        )

        # Calibration state
        self.calibrated = False
        self.pitch_offset = 0.0
        self.yaw_offset = 0.0
        self.roll_offset = 0.0
        self._initial_calib_samples: List[Tuple[float, float, float]] = []

        # Tracking state
        self.prev_rvec: Optional[np.ndarray] = None
        self.prev_tvec: Optional[np.ndarray] = None
        self._running = False

    def calibrate(self, raw_pitch: float, raw_yaw: float, raw_roll: float) -> None:
        """Calibrates neutral orientation offset and resets 1-Euro filters."""
        if not (math.isfinite(raw_pitch) and math.isfinite(raw_yaw) and math.isfinite(raw_roll)):
            print("[WARN] Calibrate rejected non-finite orientation angles.", file=sys.stderr)
            return

        self.pitch_offset = raw_pitch
        self.yaw_offset = raw_yaw
        self.roll_offset = raw_roll
        self.calibrated = True

        # Reset filter baselines so calibration does not produce transient lag
        t_now = time.perf_counter()
        self.filter_pitch.reset(t_now, 0.0)
        self.filter_yaw.reset(t_now, 0.0)
        self.filter_roll.reset(t_now, 0.0)
        print(f"[CALIB] Zero-offset established: pitch={self.pitch_offset:+.2f}, yaw={self.yaw_offset:+.2f}, roll={self.roll_offset:+.2f}")

    def run(self) -> bool:
        """Main execution loop capturing video, tracking face, and streaming UDP packets."""
        try:
            import mediapipe as mp
        except ImportError:
            print("[ERROR] Google mediapipe is not installed. Please install requirements.", file=sys.stderr)
            self.broadcaster.close()
            return False

        if not hasattr(mp, "solutions") or not hasattr(mp.solutions, "face_mesh"):
            print("[ERROR] MediaPipe FaceMesh is unavailable. Install tracker/requirements.txt.", file=sys.stderr)
            self.broadcaster.close()
            return False
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
        if not cap.isOpened() and sys.platform == "win32":
            cap.release()
            print(f"[WARN] DirectShow could not open camera {self.camera_id}; trying the default backend.")
            cap = cv2.VideoCapture(self.camera_id, cv2.CAP_ANY)

        if not cap.isOpened():
            print(f"[ERROR] Could not open camera {self.camera_id}. Check Windows camera privacy settings and whether another app is using it.", file=sys.stderr)
            cap.release()
            face_mesh.close()
            self.broadcaster.close()
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        pacer = RatePacer(self.target_fps)
        self._running = True

        fps_timer = time.perf_counter()
        fps_counter = 0
        current_fps = float(self.target_fps)
        last_frame_time = time.monotonic()
        success = True

        window_name = "Dragon Flight - Head Tracker"
        if self.preview:
            try:
                cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
            except Exception as e:
                print(f"[WARN] Failed to initialize GUI window ({e}). Running in background mode.")
                self.preview = False

        print(f"[INFO] HeadTracker running. Streaming to {self.host}:{self.port} at {self.target_fps} FPS. Press 'C' to calibrate, 'Q' to quit.")

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret or frame is None:
                    if time.monotonic() - last_frame_time > 5.0:
                        print(f"[ERROR] Camera {self.camera_id} opened but stopped delivering frames.", file=sys.stderr)
                        success = False
                        break
                    pacer.sleep()
                    continue

                last_frame_time = time.monotonic()
                t_now = time.perf_counter()

                # Calculate live FPS
                fps_counter += 1
                if t_now - fps_timer >= 1.0:
                    current_fps = fps_counter / (t_now - fps_timer)
                    fps_counter = 0
                    fps_timer = t_now

                # MediaPipe RGB processing (pass-by-reference optimization)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_rgb.flags.writeable = False
                results = face_mesh.process(frame_rgb)
                frame_rgb.flags.writeable = True

                tracking_active = False
                final_pitch, final_yaw, final_roll = 0.0, 0.0, 0.0

                if results.multi_face_landmarks:
                    tracking_active = True
                    landmarks = results.multi_face_landmarks[0].landmark
                    h, w = frame.shape[:2]

                    # Extract 6 canonical 2D pixel landmarks
                    image_points = np.array([
                        [landmarks[idx].x * w, landmarks[idx].y * h]
                        for idx in LANDMARK_INDICES
                    ], dtype=np.float64)

                    # Solve 3D head pose
                    success, rvec, tvec, raw_p, raw_y, raw_r = solve_head_pose(
                        image_points,
                        self.camera_matrix,
                        self.dist_coeffs,
                        self.prev_rvec,
                        self.prev_tvec
                    )

                    if (
                        success
                        and rvec is not None
                        and tvec is not None
                        and math.isfinite(raw_p)
                        and math.isfinite(raw_y)
                        and math.isfinite(raw_r)
                    ):
                        self.prev_rvec = rvec
                        self.prev_tvec = tvec

                        # Apply mirroring/inversion to yaw and roll for natural intuitive flight
                        eff_p = raw_p
                        eff_y = -raw_y if self.invert_yaw else raw_y
                        eff_r = -raw_r if self.invert_roll else raw_r

                        # Auto-calibration on startup (average first 10 stable frames)
                        if not self.calibrated:
                            self._initial_calib_samples.append((eff_p, eff_y, eff_r))
                            if len(self._initial_calib_samples) >= 10:
                                avg_p = float(np.mean([s[0] for s in self._initial_calib_samples]))
                                avg_y = float(np.mean([s[1] for s in self._initial_calib_samples]))
                                avg_r = float(np.mean([s[2] for s in self._initial_calib_samples]))
                                self.calibrate(avg_p, avg_y, avg_r)

                        # Subtract calibration neutral zero-offset with responsive sensitivity scaling
                        rel_pitch = (eff_p - self.pitch_offset) * self.sensitivity_pitch
                        rel_yaw = (eff_y - self.yaw_offset) * self.sensitivity_yaw
                        rel_roll = (eff_r - self.roll_offset) * self.sensitivity_roll

                        # 1-Euro adaptive low-pass filtering
                        filt_p = self.filter_pitch.filter(t_now, rel_pitch)
                        filt_y = self.filter_yaw.filter(t_now, rel_yaw)
                        filt_r = self.filter_roll.filter(t_now, rel_roll)

                        # Continuous deadzone & power curve shaping
                        final_pitch, final_yaw, final_roll = self.processor.process(
                            filt_p, filt_y, filt_r
                        )
                    else:
                        tracking_active = False
                        self.prev_rvec = None
                        self.prev_tvec = None
                else:
                    # Face lost; invalidate pose guess and reset filter history
                    self.prev_rvec = None
                    self.prev_tvec = None
                    self.filter_pitch.reset()
                    self.filter_yaw.reset()
                    self.filter_roll.reset()

                # Emit UDP packet strictly adhering to Interface Contract 1
                packet = {
                    "pitch": round(float(final_pitch), 3),
                    "yaw": round(float(final_yaw), 3),
                    "roll": round(float(final_roll), 3),
                    "calibrated": self.calibrated,
                    "tracking": tracking_active,
                    "timestamp": round(time.time(), 4)
                }
                self.broadcaster.send(packet)

                # Render GUI overlay if preview mode is active
                if self.preview:
                    try:
                        h_f, w_f = frame.shape[:2]
                        if self.mirror_preview:
                            display_frame = cv2.flip(frame, 1)
                            if tracking_active:
                                for pt in image_points:
                                    cv2.circle(display_frame, (w_f - 1 - int(pt[0]), int(pt[1])), 2, (0, 255, 255), -1)
                        else:
                            display_frame = frame.copy()
                            if tracking_active:
                                for pt in image_points:
                                    cv2.circle(display_frame, (int(pt[0]), int(pt[1])), 2, (0, 255, 255), -1)

                        draw_hud(
                            display_frame,
                            final_pitch, final_yaw, final_roll,
                            self.calibrated, tracking_active,
                            current_fps,
                            self.prev_rvec, self.prev_tvec,
                            self.camera_matrix, self.dist_coeffs,
                            mirrored=self.mirror_preview
                        )
                        cv2.imshow(window_name, display_frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (ord('q'), ord('Q'), 27):  # 'Q' or ESC
                            break
                        elif key in (ord('c'), ord('C')):
                            if results.multi_face_landmarks:
                                self.calibrate(eff_p, eff_y, eff_r)
                        elif key in (ord('m'), ord('M')):
                            self.mirror_preview = not self.mirror_preview
                            print(f"[INFO] Mirror view toggled: {'ON' if self.mirror_preview else 'OFF'}")
                        elif key in (ord('i'), ord('I')):
                            self.invert_yaw = not self.invert_yaw
                            print(f"[INFO] Invert yaw steering toggled: {'ON' if self.invert_yaw else 'OFF'}")
                    except Exception as e:
                        print(f"[WARN] GUI preview error ({e}). Disabling preview.")
                        self.preview = False

                pacer.sleep()

        except KeyboardInterrupt:
            print("\n[INFO] Termination requested by user.")
        finally:
            self._running = False
            cap.release()
            face_mesh.close()
            self.broadcaster.close()
            if self.preview:
                cv2.destroyAllWindows()
            print("[INFO] HeadTracker shut down cleanly.")
        return success


# ---------------------------------------------------------------------------
# CLI Argument Parser
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Dragon Flight - Python Webcam Head Tracker")
    parser.add_argument("--config", type=str, default=None, help="Path to custom JSON configuration file")
    parser.add_argument("--camera", type=int, default=None, help="Camera device index (default: 0)")
    parser.add_argument("--host", type=str, default=None, help="UDP target host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="UDP target port (default: 42425)")
    parser.add_argument("--fps", type=float, default=None, help="Target FPS (default: 30)")
    parser.add_argument("--deadzone", type=float, default=None, help="Deadzone in degrees (default: 2.0)")
    parser.add_argument("--headless", action="store_true", help="Run without preview window")

    args = parser.parse_args()

    config = load_config(args.config)
    if args.camera is not None:
        config["camera_id"] = args.camera
    if args.host is not None:
        config["host"] = args.host
    if args.port is not None:
        config["port"] = args.port
    if args.fps is not None:
        config["target_fps"] = args.fps
    if args.deadzone is not None:
        config["deadzone_degrees"] = args.deadzone
    if args.headless:
        config["preview"] = False

    tracker = HeadTracker(config)
    sys.exit(0 if tracker.run() else 1)


if __name__ == "__main__":
    main()
