#!/usr/bin/env python3
"""Unified Master CLI Runner for E2E Test Suite.

Features:
- Pure Python standard library implementation (unittest-based, zero third-party runner dependencies).
- Selective test execution via --tier, --feature, --pattern / -k, --failfast, --godot-bin.
- Custom TieredTextTestResult & TieredTextTestRunner for per-tier statistics and timings.
- Structured ASCII summary presentation table.
- JSON report export (--json-report).
- Standard exit code semantics: 0 on all tests passing, non-zero on any failure/error.
"""

import argparse
import json
import os
import re
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from e2e_tests.framework.config import E2E_ROOT, FRAMEWORK_ROOT


class TierStats:
    """Statistics accumulator for a single test tier."""

    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label
        self.total: int = 0
        self.passed: int = 0
        self.failed: int = 0
        self.errors: int = 0
        self.skipped: int = 0
        self.start_time: Optional[float] = None
        self.duration_sec: float = 0.0

    def record_start(self) -> None:
        if self.start_time is None:
            self.start_time = time.perf_counter()

    def record_stop(self) -> None:
        if self.start_time is not None:
            self.duration_sec += time.perf_counter() - self.start_time
            self.start_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "duration_sec": round(self.duration_sec, 2),
        }


class TieredTextTestResult(unittest.TextTestResult):
    """Custom TestResult categorizing test executions by tier and measuring timings."""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.suite_start_time = time.perf_counter()
        self.suite_end_time: Optional[float] = None

        self.tiers: Dict[str, TierStats] = {
            "tier1": TierStats("tier1", "Tier 1: Feature Coverage (F1-F18)"),
            "tier2": TierStats("tier2", "Tier 2: Boundary & Corner Cases (BVA)"),
            "tier3": TierStats("tier3", "Tier 3: Pairwise Combinations"),
            "tier4": TierStats("tier4", "Tier 4: Real-World Flight Scenarios"),
            "tier5": TierStats("tier5", "Tier 5: Adversarial Coverage Hardening"),
            "framework": TierStats("framework", "Framework Harness Self-Tests"),
            "other": TierStats("other", "Uncategorized Tests"),
        }
        self.test_start_time: float = 0.0
        self.current_tier_key: str = "other"
        self.failure_details: List[Dict[str, Any]] = []

    def _classify_test_tier(self, test: unittest.TestCase) -> str:
        mod = getattr(test, "__module__", "") or ""
        cls_name = test.__class__.__name__

        if "tier1" in mod or "t1" in mod.lower() or "Tier1" in cls_name:
            return "tier1"
        elif "tier2" in mod or "t2" in mod.lower() or "Tier2" in cls_name:
            return "tier2"
        elif "tier3" in mod or "t3" in mod.lower() or "Tier3" in cls_name:
            return "tier3"
        elif "tier4" in mod or "t4" in mod.lower() or "Tier4" in cls_name:
            return "tier4"
        elif "tier5" in mod or "t5" in mod.lower() or "Tier5" in cls_name:
            return "tier5"
        elif "framework" in mod or "Framework" in cls_name:
            return "framework"
        return "other"

    def startTest(self, test: unittest.TestCase) -> None:
        self.current_tier_key = self._classify_test_tier(test)
        tier = self.tiers[self.current_tier_key]
        tier.record_start()
        tier.total += 1
        self.test_start_time = time.perf_counter()
        super().startTest(test)

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        tier = self.tiers[self.current_tier_key]
        tier.passed += 1
        tier.record_stop()

    def addFailure(self, test: unittest.TestCase, err) -> None:
        super().addFailure(test, err)
        tier = self.tiers[self.current_tier_key]
        tier.failed += 1
        tier.record_stop()
        self.failure_details.append({
            "test": str(test),
            "tier": self.current_tier_key,
            "type": "failure",
            "error": self._exc_info_to_string(err, test),
        })

    def addError(self, test: unittest.TestCase, err) -> None:
        super().addError(test, err)
        tier = self.tiers[self.current_tier_key]
        tier.errors += 1
        tier.record_stop()
        self.failure_details.append({
            "test": str(test),
            "tier": self.current_tier_key,
            "type": "error",
            "error": self._exc_info_to_string(err, test),
        })

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        tier = self.tiers[self.current_tier_key]
        tier.skipped += 1
        tier.record_stop()

    def stopSuite(self) -> None:
        self.suite_end_time = time.perf_counter()


class TieredTextTestRunner(unittest.TextTestRunner):
    """Custom TestRunner using TieredTextTestResult and rendering structured ASCII summaries."""

    resultclass = TieredTextTestResult

    def run(self, test: unittest.TestSuite) -> TieredTextTestResult:
        result = super().run(test)
        result.stopSuite()
        self.print_summary_table(result)
        return result

    def print_summary_table(self, result: TieredTextTestResult) -> None:
        total_duration = (
            result.suite_end_time - result.suite_start_time
            if result.suite_end_time
            else 0.0
        )

        total_tests = sum(t.total for t in result.tiers.values())
        total_passed = sum(t.passed for t in result.tiers.values())
        total_failed = sum(t.failed for t in result.tiers.values())
        total_errors = sum(t.errors for t in result.tiers.values())
        total_skipped = sum(t.skipped for t in result.tiers.values())

        pass_rate = (total_passed / total_tests * 100.0) if total_tests > 0 else 100.0

        out = self.stream
        out.writeln("\n" + "=" * 80)
        out.writeln("                    E2E TEST EXECUTION SUMMARY (OPAQUE-BOX)")
        out.writeln("=" * 80)
        out.writeln(f" {'Tier':<8} {'Description':<35} {'Total':>7} {'Passed':>7} {'Failed':>7} {'Errors':>7} {'Time':>8}")
        out.writeln("-" * 80)

        order = ["tier1", "tier2", "tier3", "tier4", "tier5", "framework", "other"]
        tier_names = {
            "tier1": "Tier 1",
            "tier2": "Tier 2",
            "tier3": "Tier 3",
            "tier4": "Tier 4",
            "tier5": "Tier 5",
            "framework": "Fwk",
            "other": "Other",
        }

        for key in order:
            t = result.tiers[key]
            if t.total > 0:
                short_name = tier_names.get(key, key)
                time_str = f"{t.duration_sec:.2f}s"
                out.writeln(
                    f" {short_name:<8} {t.label:<35} {t.total:>7} {t.passed:>7} {t.failed:>7} {t.errors:>7} {time_str:>8}"
                )

        out.writeln("-" * 80)
        total_time_str = f"{total_duration:.2f}s"
        out.writeln(
            f" {'TOTAL':<44} {total_tests:>7} {total_passed:>7} {total_failed:>7} {total_errors:>7} {total_time_str:>8}"
        )
        out.writeln("=" * 80)

        if total_failed == 0 and total_errors == 0:
            status = f"ALL TESTS PASSED [PASS RATE: {pass_rate:.1f}%]"
        else:
            status = f"TESTS FAILED (Failed: {total_failed}, Errors: {total_errors}) [PASS RATE: {pass_rate:.1f}%]"

        out.writeln(f" OVERALL STATUS: {status}")
        out.writeln("=" * 80 + "\n")


def build_filtered_suite(
    tier_choice: str = "all",
    feature_id: Optional[int] = None,
    pattern: Optional[str] = None,
) -> unittest.TestSuite:
    """Discovers and filters tests across e2e_tests subdirectories."""
    loader = unittest.TestLoader()
    combined_suite = unittest.TestSuite()

    # Determine which directories to scan
    dirs_to_scan: List[Tuple[str, Path]] = []

    tier_map = {
        "1": [("tier1", E2E_ROOT / "tier1")],
        "tier1": [("tier1", E2E_ROOT / "tier1")],
        "2": [("tier2", E2E_ROOT / "tier2")],
        "tier2": [("tier2", E2E_ROOT / "tier2")],
        "3": [("tier3", E2E_ROOT / "tier3")],
        "tier3": [("tier3", E2E_ROOT / "tier3")],
        "4": [("tier4", E2E_ROOT / "tier4")],
        "tier4": [("tier4", E2E_ROOT / "tier4")],
        "5": [("tier5", E2E_ROOT / "tier5")],
        "tier5": [("tier5", E2E_ROOT / "tier5")],
        "framework": [("framework", FRAMEWORK_ROOT)],
        "fwk": [("framework", FRAMEWORK_ROOT)],
    }

    if tier_choice in tier_map:
        dirs_to_scan = tier_map[tier_choice]
    else:
        # All tiers + framework self tests
        dirs_to_scan = [
            ("tier1", E2E_ROOT / "tier1"),
            ("tier2", E2E_ROOT / "tier2"),
            ("tier3", E2E_ROOT / "tier3"),
            ("tier4", E2E_ROOT / "tier4"),
            ("tier5", E2E_ROOT / "tier5"),
            ("framework", FRAMEWORK_ROOT),
        ]

    # Feature string formatting (e.g. feature 1 -> "f01" or "feature_01")
    feature_patterns: List[str] = []
    if feature_id is not None:
        feature_patterns = [
            f"f{feature_id:02d}",
            f"f_{feature_id:02d}",
            f"feature_{feature_id:02d}",
            f"feature{feature_id:02d}",
            f"f{feature_id}",
        ]

    regex_pattern = None
    use_substring_fallback = False
    pattern_lower = ""
    pattern_stripped = ""
    if pattern:
        try:
            regex_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error:
            use_substring_fallback = True
            pattern_lower = pattern.lower()
            pattern_stripped = pattern.strip("*").lower()

    # Discover and filter test cases
    for _, target_dir in dirs_to_scan:
        if not target_dir.exists():
            continue

        discovered = loader.discover(
            start_dir=str(target_dir),
            pattern="test_*.py",
            top_level_dir=str(PROJECT_ROOT),
        )

        for test_item in _flatten_suite(discovered):
            test_id = test_item.id()
            test_name = test_item._testMethodName if hasattr(test_item, "_testMethodName") else str(test_item)
            cls_name = test_item.__class__.__name__

            # Filter by feature ID
            if feature_patterns:
                matched_feature = any(
                    fp in test_id.lower() or fp in cls_name.lower() or fp in test_name.lower()
                    for fp in feature_patterns
                )
                if not matched_feature:
                    continue

            # Filter by regex pattern or fallback substring matching
            if regex_pattern:
                if not (
                    regex_pattern.search(test_id)
                    or regex_pattern.search(test_name)
                    or regex_pattern.search(cls_name)
                ):
                    continue
            elif use_substring_fallback:
                matched_sub = (
                    pattern_lower in test_id.lower()
                    or pattern_lower in test_name.lower()
                    or pattern_lower in cls_name.lower()
                    or (pattern_stripped and (
                        pattern_stripped in test_id.lower()
                        or pattern_stripped in test_name.lower()
                        or pattern_stripped in cls_name.lower()
                    ))
                )
                if not matched_sub:
                    continue

            combined_suite.addTest(test_item)

    return combined_suite


def _flatten_suite(suite_or_test) -> List[unittest.TestCase]:
    """Recursively extracts individual TestCase instances from TestSuite objects."""
    tests = []
    if isinstance(suite_or_test, unittest.TestSuite):
        for sub_item in suite_or_test:
            tests.extend(_flatten_suite(sub_item))
    elif isinstance(suite_or_test, unittest.TestCase):
        tests.append(suite_or_test)
    return tests


def save_json_report(report_path: str, result: TieredTextTestResult) -> None:
    """Exports structured JSON report of the execution results."""
    total_tests = sum(t.total for t in result.tiers.values())
    total_passed = sum(t.passed for t in result.tiers.values())
    total_failed = sum(t.failed for t in result.tiers.values())
    total_errors = sum(t.errors for t in result.tiers.values())
    total_skipped = sum(t.skipped for t in result.tiers.values())

    total_duration = (
        result.suite_end_time - result.suite_start_time
        if result.suite_end_time
        else 0.0
    )

    data = {
        "summary": {
            "total": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "skipped": total_skipped,
            "duration_sec": round(total_duration, 2),
            "success": (total_failed == 0 and total_errors == 0),
        },
        "tiers": {
            key: t.to_dict()
            for key, t in result.tiers.items()
            if t.total > 0
        },
        "failures": result.failure_details,
    }

    out_file = Path(report_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="E2E Test Runner for First-Person Dragon Flying Game"
    )
    parser.add_argument(
        "--tier",
        type=str,
        default="all",
        choices=["all", "1", "2", "3", "4", "5", "tier1", "tier2", "tier3", "tier4", "tier5", "framework", "fwk"],
        help="Execute only tests belonging to the designated tier (default: all)",
    )
    parser.add_argument(
        "--feature",
        type=int,
        choices=range(1, 19),
        default=None,
        help="Filter tests by architectural feature number (1 through 18)",
    )
    parser.add_argument(
        "-k",
        "--pattern",
        type=str,
        default=None,
        help="Regex or substring filter matched against test names or classes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose test execution logging",
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Abort test run immediately upon the first failure",
    )
    parser.add_argument(
        "--godot-bin",
        type=str,
        default=None,
        help="Path to override Godot console executable binary",
    )
    parser.add_argument(
        "--json-report",
        type=str,
        default=None,
        help="Output path for structured JSON results report",
    )

    args = parser.parse_args()

    if args.godot_bin:
        os.environ["GODOT_BIN"] = str(Path(args.godot_bin).resolve())

    suite = build_filtered_suite(
        tier_choice=args.tier,
        feature_id=args.feature,
        pattern=args.pattern,
    )

    runner = TieredTextTestRunner(
        verbosity=2 if args.verbose else 1,
        failfast=args.failfast,
    )

    result = runner.run(suite)

    if args.json_report:
        save_json_report(args.json_report, result)

    # Return 0 if successful, 1 if failures/errors occurred
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
