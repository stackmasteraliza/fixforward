"""Test re-run and confidence scoring after patch application."""

from dataclasses import dataclass
from typing import List

from fixforward.detector import TestResult, Ecosystem, run_tests


@dataclass
class VerifyResult:
    original: TestResult
    after_fix: TestResult
    all_passing: bool
    fixed_count: int
    new_failure_count: int
    confidence: float
    diff: str


def verify(
    project_path: str,
    ecosystem: Ecosystem,
    original_result: TestResult,
) -> VerifyResult:
    """Re-run tests and compare to original results."""
    new_result = run_tests(project_path, ecosystem)

    # Calculate what changed
    fixed_count = max(0, original_result.failed_count - new_result.failed_count)
    new_failures = max(0, new_result.failed_count - 0)  # Any remaining failures

    confidence = _calculate_confidence(original_result, new_result)

    # Generate summary diff
    diff = _summary_diff(original_result, new_result)

    return VerifyResult(
        original=original_result,
        after_fix=new_result,
        all_passing=new_result.passed,
        fixed_count=fixed_count,
        new_failure_count=new_result.failed_count,
        confidence=confidence,
        diff=diff,
    )


def _calculate_confidence(original: TestResult, fixed: TestResult) -> float:
    """Calculate a confidence score for the fix."""
    score = 0.0

    if fixed.passed:
        # All tests pass — high confidence
        score = 0.90
    elif fixed.failed_count < original.failed_count:
        # Some tests fixed
        if original.failed_count > 0:
            fix_ratio = (original.failed_count - fixed.failed_count) / original.failed_count
            score = 0.30 + (fix_ratio * 0.50)
        else:
            score = 0.30
    else:
        # No improvement or worse
        score = 0.10

    # Penalty for new failures that didn't exist before
    if fixed.failed_count > original.failed_count:
        new_count = fixed.failed_count - original.failed_count
        score -= 0.20 * new_count
        score = max(0.0, score)

    # Bonus if total test count is maintained (no tests removed)
    if fixed.total_tests >= original.total_tests:
        score = min(1.0, score + 0.05)

    return round(score, 2)


def _summary_diff(original: TestResult, fixed: TestResult) -> str:
    """Generate a text summary of what changed."""
    lines = []
    lines.append(f"Before: {original.failed_count} failed / {original.passed_count} passed / {original.total_tests} total")
    lines.append(f"After:  {fixed.failed_count} failed / {fixed.passed_count} passed / {fixed.total_tests} total")

    delta_failed = original.failed_count - fixed.failed_count
    if delta_failed > 0:
        lines.append(f"Fixed:  {delta_failed} test(s)")
    elif delta_failed < 0:
        lines.append(f"New failures: {abs(delta_failed)} test(s)")
    else:
        lines.append("No change in failure count.")

    return "\n".join(lines)
