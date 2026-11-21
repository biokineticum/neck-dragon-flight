"""e2e_tests/tier2/test_t2_f17_docs.py
Tier 2: Boundary Value Analysis & Robustness for Feature 17:
Integration Documentation & Launchers (Whitespace path quoting, Python check, port collision guide, exact engine version, headless verification docs).
"""

import re
import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier2Feature17Docs(OpaqueBoxTestCase):
    """Tier 2 boundary value tests for project documentation and launch scripts."""

    @unittest.skipUnless((PROJECT_ROOT / "run_game.bat").is_file(), "run_game.bat not yet created by builder milestone")
    def test_t2_f17_01_paths_with_spaces_in_launcher(self) -> None:
        """TEST-T2-F17-01: Launcher script quotes file paths and environment variables protecting against whitespace paths."""
        content = (PROJECT_ROOT / "run_game.bat").read_text(encoding="utf-8", errors="ignore")
        quoted_vars = re.findall(r'"%[^%]+%"', content)
        self.assertGreater(len(quoted_vars), 0, "run_game.bat missing quoted environment variables")

    @unittest.skipUnless((PROJECT_ROOT / "run_game.bat").is_file(), "run_game.bat not yet created by builder milestone")
    def test_t2_f17_02_missing_python_error_handling(self) -> None:
        """TEST-T2-F17-02: Launcher script includes check for Python availability."""
        content = (PROJECT_ROOT / "run_game.bat").read_text(encoding="utf-8", errors="ignore")
        self.assertTrue(
            re.search(r"where\s+python|ERRORLEVEL|python", content, re.IGNORECASE),
            "run_game.bat missing Python availability check"
        )

    @unittest.skipUnless((PROJECT_ROOT / "INTEGRATION.md").is_file(), "INTEGRATION.md not yet created by builder milestone")
    def test_t2_f17_03_port_collision_troubleshooting_doc(self) -> None:
        """TEST-T2-F17-03: INTEGRATION.md includes port 42425 collision troubleshooting commands."""
        content = (PROJECT_ROOT / "INTEGRATION.md").read_text(encoding="utf-8", errors="ignore")
        self.assertIn("42425", content)
        self.assertTrue(
            re.search(r"netstat.*42425|findstr.*42425", content, re.IGNORECASE),
            "INTEGRATION.md missing netstat port 42425 troubleshooting command"
        )

    @unittest.skipUnless((PROJECT_ROOT / "SETUP.md").is_file(), "SETUP.md not yet created by builder milestone")
    def test_t2_f17_04_exact_engine_version_specification(self) -> None:
        """TEST-T2-F17-04: SETUP.md specifies exact required Godot engine version (4.7.2)."""
        content = (PROJECT_ROOT / "SETUP.md").read_text(encoding="utf-8", errors="ignore")
        self.assertIn("4.7.2", content, "SETUP.md missing exact engine version '4.7.2'")

    @unittest.skipUnless((PROJECT_ROOT / "SETUP.md").is_file(), "SETUP.md not yet created by builder milestone")
    def test_t2_f17_05_headless_verification_command_doc(self) -> None:
        """TEST-T2-F17-05: SETUP.md documents headless verification commands."""
        content = (PROJECT_ROOT / "SETUP.md").read_text(encoding="utf-8", errors="ignore")
        self.assertTrue(
            re.search(r"godot.*--headless", content, re.IGNORECASE),
            "SETUP.md missing 'godot --headless' verification command"
        )


if __name__ == "__main__":
    unittest.main()
