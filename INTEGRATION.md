# Dragon Flight Game - Integration, Controls & Telemetry Guide

This document specifies the dual-mode control architecture, network UDP protocol, calibration procedure, sensitivity tuning, and troubleshooting instructions.

---

## 1. System Architecture

The game implements a decoupled dual-mode input architecture communicating over local UDP sockets:

```
+---------------------------+               +----------------------------------+
| PYTHON HEAD-TRACKER       |  UDP 42425    | GODOT 4.7.2 GAME ENGINE          |
| - OpenCV VideoCapture     | ------------> | - InputManager.gd (PacketPeerUDP)|
| - MediaPipe 468 FaceMesh  |  JSON Packets | - FlightController.gd            |
| - 1-Euro Jitter Filter    |  (30-60 Hz)   | - Dual-Mode Priority Crossfade   |
| - Continuous Deadzone     |               | - Keyboard/Mouse Fallback Engine |
+---------------------------+               +----------------------------------+
```

---

## 2. Flight Controls

The player steers the dragon through a mountain corridor using webcam head tracking or keyboard/mouse controls.

### Primary Controls (Webcam Head Tracking)
- **Pitch (Climb / Dive)**: Tilt head backward (look up) to climb; tilt head forward (look down) to dive.
- **Yaw (Turn Left / Right)**: Turn face left to steer left; turn face right to steer right.
- **Roll (Banking)**: Tilt head toward left ear to bank left; tilt head toward right ear to bank right.
- **Calibrate Center**: Look straight at your screen and press **`C`** on your keyboard.

### Fallback Controls (Keyboard & Mouse / WASD)
Keyboard and mouse controls operate with 100% immediate priority override:
- **Pitch**: `W` / `Up Arrow` to dive; `S` / `Down Arrow` to climb.
- **Yaw**: `A` / `Left Arrow` to steer left; `D` / `Right Arrow` to steer right.
- **Roll**: `Q` / `Left Mouse Button` to bank left; `E` / `Right Mouse Button` to bank right.
- **Boost**: `Space` (accelerates forward flight).
- **Brake**: `Shift` (decelerates to glide floor).
- **Calibrate**: `C` (physical keycode 67).
- **Restart Game**: `R` (physical keycode 82) or `Space` after crash.

---

## 3. UDP Telemetry Format (Interface Contract 1)

The Python tracker streams UTF-8 encoded JSON datagrams to `127.0.0.1:42425`:

```json
{
  "pitch": 12.5,
  "yaw": -8.4,
  "roll": 4.2,
  "calibrated": true,
  "tracking": true,
  "timestamp": 1700000000.123
}
```

### Data Fields
- `pitch` (*float*): Pitch angle in degrees `[-35.0, 35.0]`. Positive = look up / climb, negative = look down / dive.
- `yaw` (*float*): Yaw angle in degrees `[-45.0, 45.0]`. Positive = turn right, negative = turn left.
- `roll` (*float*): Roll angle in degrees `[-35.0, 35.0]`. Positive = tilt right, negative = tilt left.
- `calibrated` (*bool*): True when zero-offset calibration has been established.
- `tracking` (*bool*): True when face landmarks are actively detected.
- `timestamp` (*float*): High-resolution frame capture timestamp.

---

## 4. Dual-Mode Fallback & Timeout Scheme

- **Packet Timeout**: If no valid packet arrives for `> 0.50` seconds, `InputManager.gd` flags `head_tracking_active = false` and decays steering angles toward 0.0 at `8.0 * delta` units/second.
- **Keyboard Priority**: Any keyboard steering input immediately takes 100% control authority.
- **Seamless Crossfade**: When manual keys are released, the system smoothly crossfades back to webcam control over a `0.35` second blend window (`BLENDED` mode).

---

## 5. Runtime Calibration Procedure

1. Sit comfortably facing your webcam in normal lighting.
2. Align your head with the center of the display in a neutral forward-looking posture.
3. Press the **`C`** key on your keyboard.
4. The HUD will flash a yellow confirmation notice: `NEUTRAL POSE CALIBRATED`.
5. Offsets are recorded and subtracted from all subsequent head movements.

---

## 6. Sensitivity Tuning (`tracker/tracker_config.json`)

You can customize tracker response parameters in `tracker/tracker_config.json`:

```json
{
  "camera_id": 0,
  "frame_width": 640,
  "frame_height": 480,
  "target_fps": 60,
  "udp_host": "127.0.0.1",
  "udp_port": 42425,
  "deadzone": 2.0,
  "gamma": 1.5,
  "max_pitch": 35.0,
  "max_yaw": 45.0,
  "max_roll": 35.0,
  "one_euro_filter": {
    "fc_min": 1.0,
    "beta": 0.007,
    "d_cutoff": 1.0
  }
}
```

- `deadzone`: Angular deadband in degrees around zero (default `2.0°`).
- `gamma`: Exponential curve power (default `1.5`). Values `> 1.0` enhance fine center-aim precision while preserving full deflection.
- `fc_min` & `beta`: 1-Euro adaptive filter coefficients. Lower `fc_min` eliminates tremor jitter; higher `beta` reduces phase lag during rapid head turns.

---

## 7. Troubleshooting & Network Port Collisions

### UDP Port 42425 Already Bound
If another process or a previous tracker instance is holding port 42425:
1. Check for active listeners on Windows:
   ```cmd
   netstat -ano | findstr 42425
   ```
2. Identify the process ID (PID) from the rightmost column and terminate it:
   ```cmd
   taskkill /F /PID <PID>
   ```

### Webcam Feed Not Opening
- Confirm camera privacy settings in Windows Settings.
- Verify no other application (Zoom, Teams, Discord) is locking the webcam.
- If multiple webcams are connected, adjust `"camera_id"` in `tracker_config.json` (`0`, `1`, etc.).
