"""Python head-tracker subsystem process lifecycle manager.

Manages child processes for `head_tracker.py` and `mock_tracker.py` during E2E testing,
capturing stdout/stderr and ensuring clean termination.
"""

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

from .config import MOCK_TRACKER_SCRIPT, TRACKER_SCRIPT


class TrackerProcessManager:
    """Manages Python tracker child processes."""

    def __init__(
        self,
        use_mock: bool = False,
        script_path: Optional[Path] = None,
        extra_args: Optional[List[str]] = None,
    ):
        if script_path:
            self.target_script = Path(script_path)
        else:
            self.target_script = MOCK_TRACKER_SCRIPT if use_mock else TRACKER_SCRIPT

        self.extra_args = extra_args or []
        self.process: Optional[subprocess.Popen] = None
        self.log_queue: queue.Queue = queue.Queue()
        self.all_logs: List[str] = []
        self._reader_thread: Optional[threading.Thread] = None

    def start(self) -> "TrackerProcessManager":
        """Spawns the Python tracker script as a child process."""
        cmd = [sys.executable, str(self.target_script)] + self.extra_args

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
            target=self._read_stdout, daemon=True, name="TrackerStdoutReader"
        )
        self._reader_thread.start()
        time.sleep(0.1)  # Brief warm-up to allow socket binding
        return self

    def _read_stdout(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for line in iter(self.process.stdout.readline, ""):
            clean = line.strip()
            if clean:
                self.all_logs.append(clean)
                self.log_queue.put(clean)
        self.process.stdout.close()

    def wait_for_pattern(self, pattern: str, timeout: float = 5.0) -> Optional[str]:
        """Waits for pattern to appear in tracker log output."""
        deadline = time.time() + timeout
        for line in self.all_logs:
            if pattern in line:
                return line

        while time.time() < deadline:
            remaining = max(0.01, deadline - time.time())
            try:
                line = self.log_queue.get(timeout=remaining)
                if pattern in line:
                    return line
            except queue.Empty:
                if self.process and self.process.poll() is not None:
                    break
        return None

    def wait_for_exit(self, timeout: float = 10.0) -> int:
        """Waits for child process to terminate, raising TimeoutError if it hangs."""
        if not self.process:
            return 0
        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.terminate()
            raise TimeoutError(f"Tracker process timed out after {timeout} seconds")

    def terminate(self) -> None:
        """Terminates tracker child process cleanly."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def __enter__(self) -> "TrackerProcessManager":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
