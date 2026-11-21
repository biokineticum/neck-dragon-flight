# Dragon Flight: High-Mountain Realm

[Wersja polska](README.md)

A peaceful dragon flight game set in a mountainous realm. Fly using a keyboard
and mouse or head movements tracked by a webcam. The project combines a Godot
game with a Python face-tracking module.

## Gameplay

The world includes a valley, mountains, forests, a lake, a river and waterfall,
as well as settlements, animals and flocks of birds. Weather changes during
flight, accompanied by ambient nature sounds. Flight is peaceful: hitting the
terrain does not reduce health or end the game.

Hearts are scattered through the air in different directions. Fly through them
to collect them. Every five hearts trigger fireworks, and you can continue
collecting afterward. A counter on screen shows your progress.

## Requirements

- Windows 10 or 11 for the included launcher.
- Godot 4.7.2, available as the `godot` command or specified by `GODOT_BIN`.
- Python 3.11 and the dependencies in `tracker\requirements.txt` for head tracking.
- A webcam and operating-system camera permission if using head tracking.

The webcam and Python are not required when launching Godot directly and
playing with a keyboard and mouse.

## Running the game

### With head tracking

1. Install Godot and Python and add them to your system `PATH`.
2. Install the dependencies from the project directory:

   ```cmd
   python -m pip install -r tracker\requirements.txt
   ```

3. Run `run_game.bat`. It starts the tracker and the game, then stops the
   tracker when the game closes. If dependencies are missing, the launcher
   attempts to install them.
4. Sit in front of the camera and start flying using the button on the start
   screen, `Space`, or `Enter`. Press `C` to calibrate your head position.

If Godot is not on `PATH`, set the executable path and run the launcher from
the same Command Prompt window:

```cmd
set "GODOT_BIN=C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe"
run_game.bat
```

Adjust the path to match your Godot installation.

### Without a webcam

Run this from the project directory:

```cmd
godot --path .
```

Alternatively, import `project.godot` in the Godot project manager and run
the main scene.

### Running the tracker separately

Run these commands in separate terminals:

```cmd
python tracker\head_tracker.py
```

```cmd
godot --path .
```

## Controls

| Control | Action |
| --- | --- |
| `W` or up arrow | Climb |
| `S` or down arrow | Dive |
| `A` or left arrow | Turn left |
| `D` or right arrow | Turn right |
| `Q` or left mouse button | Bank left |
| `E` or right mouse button | Bank right |
| `C` | Calibrate the neutral head position |
| `O` | Open or close settings |
| `R` | Restart the flight and reset the heart counter |

Head movements control climb, turning and banking. Keyboard or mouse input
temporarily takes priority; after release, control smoothly returns to the
webcam if tracking is active. Sensitivity and axis inversion can be adjusted
in the game settings.

## Camera and configuration

The tracker uses OpenCV and MediaPipe to detect the face and estimate head
orientation. It sends angles and tracking status as JSON over UDP to the local
address `127.0.0.1:42425`. The game receives them in `InputManager.gd`;
manual controls remain available if the signal is lost.

Tracker settings are in `tracker\tracker_config.json`. The `camera_id` field
selects the camera, and `preview` enables or disables the preview window.
Edit the file before starting the tracker.

If the camera does not work:

1. Check that it is not covered or disabled with a physical button.
2. Allow desktop apps to access the camera in Windows settings and close other
   programs that may be using it.
3. Check the launcher output and change `camera_id` if necessary.
4. Make sure your face is visible and well lit.

The `KEYBOARD / MOUSE` status indicates manual control, not necessarily a
camera failure. You can start flying manually without waiting for the tracker.

## Project structure

| Path | Contents |
| --- | --- |
| `project.godot` | Project configuration and input mappings |
| `scenes\` | Main scene, dragon and user interface |
| `scripts\` | Flight, world, input, weather and heart collection logic |
| `materials\` | Materials, shaders and environment |
| `tracker\` | Head tracking, configuration and Python tests |
| `test\` | Headless Godot tests |
| `e2e_tests\` | Additional integration tests |
| `run_game.bat` | Windows launcher for the game and tracker |

## Tests

Run the Godot test suite from the project directory:

```cmd
godot --headless --path . -s test\run_all_tests.gd
```

Run the tracker tests:

```cmd
python -m pytest tracker\tests -q
```

For more information, see [SETUP.md](SETUP.md) and
[INTEGRATION.md](INTEGRATION.md).
