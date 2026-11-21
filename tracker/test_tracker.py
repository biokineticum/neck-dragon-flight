"""
test_tracker.py - Master Test Runner for Milestone 1 Head Tracker Subsystem

Executes all unit and integration test suites:
- Suite 1: Packet schema compliance (test_packet_schema.py)
- Suite 2: 1-Euro filter verification (test_one_euro_filter.py)
- Suite 3: Deadzone & power curve scaling (test_deadzone_curve.py)
- Suite 4: 3D solvePnP & Euler recovery (test_euler_solvepnp.py)
- Suite 5: Local UDP loopback & socket resilience (test_udp_loopback.py)

Usage:
    python tracker/test_tracker.py
    pytest tracker/test_tracker.py
    pytest tracker/tests/
"""

import sys
import os
import unittest


def run_all_tests() -> bool:
    """Discovers and runs all unit and integration tests under tracker/tests/."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(current_dir, "tests")

    # Ensure parent directory of tracker is in sys.path
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=tests_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
