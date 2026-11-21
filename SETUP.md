# Installation and Setup Guide

This guide provides instructions to install prerequisites, configure the Python head-tracking subsystem, import the project into Godot Engine 4.7.2, and launch the game.

---

## 1. Prerequisites

Before installing the project, verify that your workstation meets the following minimum requirements:

- **Operating System**: Windows 10 (64-bit) or Windows 11 (64-bit).
- **CPU**: Intel Core i5 / AMD Ryzen 5 or higher.
- **GPU**: Dedicated or modern integrated graphics supporting Direct3D 12, Vulkan 1.2+, or OpenGL 3.3+.
- **Webcam**: Standard USB or integrated webcam delivering at least 30 FPS at 640x480 resolution.
- **Python**: Python 3.11.x or higher (64-bit).
- **Engine**: Godot Engine version **4.7.2** (Forward+ or Compatibility renderer).

---

## 2. Engine Installation & Project Import

### Installing Godot Engine 4.7.2
1. Download Godot Engine version **4.7.2** from the official site or repository:
   - File: `Godot_v4.7.2-stable_win64.exe` (and companion `Godot_v4.7.2-stable_win64_console.exe`).
2. Extract the executable to a permanent folder on your drive (e.g., `C:\Tools\Godot\` or `C:\Program Files\Godot\`).
3. (Recommended) Add the Godot executable directory to your system `PATH` environment variable so `godot` can be called from command line.

### Importing the Project
1. Launch Godot Engine 4.7.2.
2. In the Project Manager window, click the **Import** button.
3. Browse to the project root directory: `c:\Users\Lenovo\Documents\test agentów\`.
4. Select the `project.godot` file and click **Import & Edit**.
5. Godot will scan and import all project resources, shaders, and scenes into the local cache.

---

## 3. Python Subsystem & Dependencies Setup

The head-tracking subsystem uses OpenCV and MediaPipe to detect facial landmarks and transmit telemetry via UDP.

### Setting Up Python Environment
1. Ensure Python 3.11+ is installed and registered in your Windows PATH. Verify via command prompt:
   ```cmd
   python --version
   ```
2. Open a terminal in the project root and install the required dependencies:
   ```cmd
   pip install -r tracker/requirements.txt
   ```
   The dependencies include:
   - `opencv-python>=4.8.0`
   - `mediapipe>=0.10.0`
   - `numpy>=1.24.0`

### Windows Webcam Privacy Permissions
Ensure Windows grants permission to desktop apps to access your camera:
1. Open **Windows Settings** -> **Privacy & Security** -> **Camera**.
2. Toggle **Camera access** to **On**.
3. Toggle **Let desktop apps access your camera** to **On**.
4. Test camera operation in the default Windows "Camera" app prior to launching the tracker.

---

## 4. Run Instructions

The valley includes a lake fed by a river and waterfall, clustered forests,
rocky highlands, a fly-through rock tunnel, an old watchtower and an ancient
gate. Clouds, trees, water and distant birds move over time. Weather cycles
between clear and rainy conditions; synthesized wind, water and bird ambience
adds sound. Wind responds to speed and altitude. Water and landmarks are
visual, so they do not obstruct peaceful flight.

### Option A: One-Click Launcher (Recommended)
Double-click `run_game.bat` located in the root directory. The launcher script will:
1. Verify Python availability.
2. Launch `tracker/head_tracker.py` in a separate process.
3. Launch Godot 4.7.2 running `scenes/Main.tscn`.
4. Automatically shut down background processes on exit.

### Option B: Manual Two-Terminal Execution
1. **Terminal 1 (Head Tracker)**:
   ```cmd
   python tracker/head_tracker.py
   ```
2. **Terminal 2 (Godot Game)**:
   ```cmd
   godot --path .
   ```

---

## 5. Automated Verification & Headless Testing

You can verify the integrity of the engine project, procedural generation, flight physics, and collision logic programmatically using Godot headless mode:

```cmd
godot --headless --path . -s test/run_all_tests.gd
```

Individual test suites can also be executed independently:
- Flight physics smoke test:
  ```cmd
  godot --headless --path . -s test/test_flight_physics.gd
  ```
- Collision physics and damage loop test:
  ```cmd
  godot --headless --path . -s test/test_collision.gd
  ```
- Synthetic mock input test:
  ```cmd
  godot --headless --path . -s test/test_input_mock.gd
  ```
- Procedural mesh and chunk streaming test:
  ```cmd
  godot --headless --path . -s test/test_milestone2_headless.gd
  ```
