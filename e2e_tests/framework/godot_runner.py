"""Godot engine headless process launcher and log assertion parser.

Handles:
- Godot 4.7.2 console binary auto-discovery on Windows.
- Non-blocking real-time stdout/stderr capture in background reader thread.
- Exact and regex pattern matching on engine log streams with configurable timeouts.
- Clean process termination preventing orphaned background instances.
"""

import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Optional, Union

Union_Path_Str = Union[str, Path]

from .config import (
    DEFAULT_GODOT_CONSOLE_PATH,
    DEFAULT_GODOT_GUI_PATH,
    GODOT_PROJECT_DIR,
)


class GodotDiscovery:
    """Discovers the Godot 4.7.2 executable on the host system."""

    KNOWN_LOCATIONS = [
        DEFAULT_GODOT_CONSOLE_PATH,
        DEFAULT_GODOT_GUI_PATH,
        Path(r"C:\Program Files\Godot\Godot_v4.7.2-stable_win64_console.exe"),
        Path(r"C:\Program Files\Godot\Godot_v4.7.2-stable_win64.exe"),
        Path(r"C:\Tools\Godot\Godot_v4.7.2-stable_win64_console.exe"),
        Path(r"C:\Godot\Godot_v4.7.2-stable_win64_console.exe"),
    ]

    @classmethod
    def find_binary(cls, override_path: Optional[str] = None) -> Path:
        """Finds and returns the Path to the Godot console or GUI executable."""
        if override_path:
            p = Path(override_path)
            if p.is_file():
                return p

        # Check environment variables
        env_val = os.environ.get("GODOT_BIN") or os.environ.get("GODOT_PATH")
        if env_val:
            p = Path(env_val)
            if p.is_file():
                return p

        # Check known installation paths (console executable prioritized)
        for loc in cls.KNOWN_LOCATIONS:
            if loc.is_file():
                return loc

        # Check Windows PATH via where.exe
        try:
            where_out = subprocess.check_output(["where.exe", "godot"], text=True, stderr=subprocess.DEVNULL)
            lines = [line.strip() for line in where_out.splitlines() if line.strip()]
            # Prefer console binary
            for line in lines:
                if "console" in line.lower() and Path(line).is_file():
                    return Path(line)
            for line in lines:
                if Path(line).is_file():
                    return Path(line)
        except Exception:
            pass

        raise FileNotFoundError(
            f"Godot executable not found. Checked default path: {DEFAULT_GODOT_CONSOLE_PATH}"
        )


class GodotProcessManager:
    """Manages headless Godot process execution and non-blocking stdout log capturing."""

    def __init__(
        self,
        script_path: Optional[Union_Path_Str] = None,
        scene_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        project_dir: Optional[Path] = None,
        godot_bin: Optional[str] = None,
    ):
        self.godot_bin = GodotDiscovery.find_binary(godot_bin)
        self.script_path = script_path
        self.scene_path = scene_path
        self.extra_args = extra_args or []
        self.project_dir = project_dir or GODOT_PROJECT_DIR

        self.process: Optional[subprocess.Popen] = None
        self.log_queue: queue.Queue = queue.Queue()
        self.all_logs: List[str] = []
        self._reader_thread: Optional[threading.Thread] = None

    def start(self) -> "GodotProcessManager":
        """Spawns the headless Godot engine child process."""
        cmd = [str(self.godot_bin), "--headless", "--path", str(self.project_dir)]
        if self.scene_path:
            cmd.extend(["--scene", self.scene_path])
        if self.script_path:
            cmd.extend(["-s", str(self.script_path)])
        if self.extra_args:
            cmd.append("--")
            cmd.extend(self.extra_args)

        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )

        self._reader_thread = threading.Thread(
            target=self._read_stdout, daemon=True, name="GodotStdoutReader"
        )
        self._reader_thread.start()
        return self

    def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for line in iter(self.process.stdout.readline, ""):
            clean = line.strip()
            if clean:
                self.all_logs.append(clean)
                self.log_queue.put(clean)
        self.process.stdout.close()

    def wait_for_pattern(
        self,
        pattern: str,
        timeout: float = 5.0,
        regex: bool = False,
    ) -> Optional[str]:
        """Waits for a matching line in the engine log stream until timeout."""
        compiled_regex = re.compile(pattern) if regex else None
        deadline = time.time() + timeout

        # First check already accumulated logs
        for line in self.all_logs:
            if compiled_regex and compiled_regex.search(line):
                return line
            elif not compiled_regex and pattern in line:
                return line

        while time.time() < deadline:
            remaining = max(0.01, deadline - time.time())
            try:
                line = self.log_queue.get(timeout=remaining)
                if compiled_regex and compiled_regex.search(line):
                    return line
                elif not compiled_regex and pattern in line:
                    return line
            except queue.Empty:
                if self.process and self.process.poll() is not None:
                    break

        return None

    def wait_for_exit(self, timeout: float = 10.0) -> int:
        """Waits for the Godot process to exit, terminating it if timeout expires."""
        if not self.process:
            return 0
        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.terminate()
            raise TimeoutError(f"Godot process timed out after {timeout} seconds")

    def terminate(self) -> None:
        """Gracefully terminates the engine process, escalating to kill if needed."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def __enter__(self) -> "GodotProcessManager":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
