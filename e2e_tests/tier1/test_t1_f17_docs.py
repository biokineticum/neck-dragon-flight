"""e2e_tests/tier1/test_t1_f17_docs.py
Tier 1: Category-Partition & Equivalence Class Partitioning for Feature 17:
Integration Documentation & Launchers (SETUP.md, INTEGRATION.md, tracker requirements.txt, run_game.bat, directory layout).
"""

import re
import unittest
from pathlib import Path

from e2e_tests.framework.config import PROJECT_ROOT
from e2e_tests.framework.test_base import OpaqueBoxTestCase


class TestTier1Feature17Docs(OpaqueBoxTestCase):
    """Tier 1 equivalence partition tests for project documentation and launch scripts."""

    @unittest.skipUnless((PROJECT_ROOT / "SETUP.md").is_file(), "SETUP.md not yet created by builder milestone")
    def test_t1_f17_01_setup_doc_exists_and_content(self) -> None:
        """TEST-T1-F17-01: SETUP.md exists and contains required setup and execution sections."""
        setup_file = PROJECT_ROOT / "SETUP.md"
        content = setup_file.read_text(encoding="utf-8")
        self.assertGreater(len(content), 300, "SETUP.md content is too brief")
        for hdr in ("Prerequisites", "Engine", "Python", "Run"):
            self.assertTrue(
                re.search(rf"#+.*{hdr}", content, re.IGNORECASE),
                f"SETUP.md missing required section header matching '{hdr}'"
            )

    @unittest.skipUnless((PROJECT_ROOT / "INTEGRATION.md").is_file(), "INTEGRATION.md not yet created by builder milestone")
    def test_t1_f17_02_integration_doc_architecture(self) -> None:
        """TEST-T1-F17-02: INTEGRATION.md details UDP architecture, port 42425, calibration, and fallback."""
        integ_file = PROJECT_ROOT / "INTEGRATION.md"
        content = integ_file.read_text(encoding="utf-8")
        self.assertIn("42425", content, "INTEGRATION.md missing UDP port 42425 reference")
        self.assertTrue(re.search(r"calibrate|calibration|'C'", content, re.IGNORECASE))
        self.assertTrue(re.search(r"fallback|keyboard|WASD", content, re.IGNORECASE))

    def test_t1_f17_03_python_requirements_contents(self) -> None:
        """TEST-T1-F17-03: tracker/requirements.txt contains core dependencies: opencv-python, mediapipe, numpy."""
        req_file = PROJECT_ROOT / "tracker" / "requirements.txt"
        self.assertTrue(req_file.is_file(), f"requirements.txt missing at {req_file}")
        content = req_file.read_text(encoding="utf-8").lower()
        self.assertIn("opencv-python", content)
        self.assertIn("mediapipe", content)
        self.assertIn("numpy", content)

    @unittest.skipUnless((PROJECT_ROOT / "run_game.bat").is_file(), "run_game.bat not yet created by builder milestone")
    def test_t1_f17_04_launcher_script_syntax(self) -> None:
        """TEST-T1-F17-04: run_game.bat orchestrates tracker and engine startup."""
        bat_file = PROJECT_ROOT / "run_game.bat"
        content = bat_file.read_text(encoding="utf-8", errors="ignore")
        self.assertTrue(re.search(r"python.*head_tracker\.py", content, re.IGNORECASE))
        self.assertTrue(re.search(r"godot", content, re.IGNORECASE))

    def test_t1_f17_05_doc_code_layout_alignment(self) -> None:
        """TEST-T1-F17-05: Workspace conforms to documented directory structure."""
        for d in ("tracker", "scenes", "scripts", "materials", "test"):
            dir_path = PROJECT_ROOT / d
            self.assertTrue(dir_path.is_dir(), f"Expected directory '{d}' missing in project layout")


if __name__ == "__main__":
    unittest.main()
