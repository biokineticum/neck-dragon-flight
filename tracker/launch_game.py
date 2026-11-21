"""Launch the webcam tracker alongside Godot and stop it when the game exits."""

import os
from pathlib import Path
import subprocess
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent


def launch(godot_exe: str) -> int:
    tracker = None
    try:
        tracker = subprocess.Popen(
            [sys.executable, "-u", str(PROJECT_DIR / "tracker" / "head_tracker.py")],
            cwd=PROJECT_DIR,
        )
        command = [godot_exe, "--path", str(PROJECT_DIR)]
        if os.name == "nt" and Path(godot_exe).suffix.lower() in (".bat", ".cmd"):
            # cmd.exe /s strips the outer pair, leaving both paths quoted for the batch file.
            command = (
                subprocess.list2cmdline([os.environ["COMSPEC"]])
                + ' /d /s /c ""'
                + godot_exe
                + '" '
                + subprocess.list2cmdline(["--path", str(PROJECT_DIR)])
                + '"'
            )
        game = subprocess.Popen(command, cwd=PROJECT_DIR)
        tracker_reported = False
        while True:
            try:
                result = game.wait(timeout=0.5)
                return result
            except subprocess.TimeoutExpired:
                if not tracker_reported and tracker.poll() is not None:
                    print(
                        "[ERROR] The webcam tracker stopped. See the error above. "
                        "The game remains available with keyboard controls.",
                        file=sys.stderr,
                        flush=True,
                    )
                    tracker_reported = True
    except OSError as error:
        print(f"[ERROR] Could not launch tracker or Godot: {error}", file=sys.stderr)
        return 1
    finally:
        if tracker is not None and tracker.poll() is None:
            tracker.terminate()
            tracker.wait()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tracker/launch_game.py GODOT_EXECUTABLE", file=sys.stderr)
        sys.exit(2)
    sys.exit(launch(sys.argv[1]))
