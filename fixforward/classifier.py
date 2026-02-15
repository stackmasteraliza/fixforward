"""Failure classification engine using regex heuristics."""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List

from fixforward.detector import TestFailure, Ecosystem


class FailureCategory(Enum):
    SYNTAX_ERROR = "syntax_error"
    DEPENDENCY = "dependency"
    ENV_MISMATCH = "env_mismatch"
    API_CHANGE = "api_change"
    LINT = "lint"
    FLAKY_TEST = "flaky_test"
    ASSERTION = "assertion"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedFailure:
    failure: TestFailure
    category: FailureCategory
    confidence: float
    summary: str


# Classification rules in priority order (first match wins).
# Each rule: (category, confidence, [(pattern, summary_template)])
RULES = [
    (FailureCategory.SYNTAX_ERROR, 0.95, [
        (r"SyntaxError:\s*(.+)", "Syntax error: {0}"),
        (r"IndentationError:\s*(.+)", "Indentation error: {0}"),
        (r"Unexpected token\s*(.+)", "Unexpected token: {0}"),
        (r"parse error", "Parse error"),
        (r"expected\s+.+,\s+found\s+(.+)", "Expected/found mismatch: {0}"),
    ]),
    (FailureCategory.DEPENDENCY, 0.90, [
        (r"ModuleNotFoundError:\s*No module named '(\S+)'", "Missing module: {0}"),
        (r"ImportError:\s*(.+)", "Import error: {0}"),
        (r"Cannot find module '(\S+)'", "Missing Node module: {0}"),
        (r"No module named '?(\S+?)'?", "Missing module: {0}"),
        (r"unresolved import `(\S+)`", "Unresolved import: {0}"),
        (r"package `(\S+)`.+not found", "Missing Rust crate: {0}"),
        (r"Could not find a version that satisfies", "Dependency version conflict"),
    ]),
    (FailureCategory.ENV_MISMATCH, 0.80, [
        (r"version mismatch", "Version mismatch"),
        (r"requires Python\s*([\d.]+)", "Requires Python {0}"),
        (r"engine .+ is incompatible", "Engine incompatible"),
        (r"ENOENT.+?'(\S+)'", "Command not found: {0}"),
        (r"command not found:\s*(\S+)", "Command not found: {0}"),
        (r"minimum supported rust version", "Rust version too old"),
    ]),
    (FailureCategory.API_CHANGE, 0.85, [
        (r"AttributeError:\s*'?(\w+)'?\s+object has no attribute '(\w+)'",
         "{0} has no attribute '{1}'"),
        (r"TypeError:\s*(\w+)\(\) (?:got an unexpected|missing \d+ required|takes \d+)",
         "Wrong arguments for {0}()"),
        (r"missing \d+ required (?:positional )?argument", "Missing required argument"),
        (r"has no member named `(\w+)`", "No member: {0}"),
        (r"no method named `(\w+)`", "No method: {0}"),
        (r"is not a function", "Not a function"),
        (r"is not defined", "Not defined"),
    ]),
    (FailureCategory.LINT, 0.75, [
        (r"flake8", "Flake8 lint error"),
        (r"eslint", "ESLint error"),
        (r"clippy", "Clippy warning"),
        (r"warning\[(\w+)\]", "Compiler warning: {0}"),
        (r"formatting.+differ", "Formatting difference"),
    ]),
    (FailureCategory.FLAKY_TEST, 0.60, [
        (r"timeout|timed?\s*out", "Test timed out"),
        (r"flaky", "Flaky test"),
        (r"intermittent", "Intermittent failure"),
        (r"connection refused", "Connection refused"),
        (r"ECONNRESET", "Connection reset"),
        (r"Resource temporarily unavailable", "Resource unavailable"),
    ]),
    (FailureCategory.ASSERTION, 0.85, [
        (r"AssertionError:\s*assert\s+(.+)", "Assertion failed: {0}"),
        (r"AssertionError:\s*(.+)", "Assertion: {0}"),
        (r"assert\s+[\d.]+\s*==\s*[\d.]+", "Assertion: value mismatch"),
        (r"assert\s+(.+?)\s*==\s*(.+)", "Assertion: {0} != {1}"),
        (r"assert_eq!.+left:\s*`(.+?)`,\s*right:\s*`(.+?)`",
         "assert_eq! left={0}, right={1}"),
        (r"expect\(.+\)\.to(?:Equal|Be)\((.+?)\)", "Expected {0}"),
        (r"Expected\s+(.+?)\s+to (?:equal|be)\s+(.+)", "Expected {1}, got {0}"),
        (r"expected:\s*(.+?)\s+but was:\s*(.+)", "Expected {0}, got {1}"),
        (r"!=\s", "Value mismatch"),
        (r"AssertionError", "Assertion error"),
    ]),
]


def classify(
    failures: List[TestFailure],
    ecosystem: Ecosystem,
) -> List[ClassifiedFailure]:
    """Classify each test failure by category."""
    return [_classify_one(f) for f in failures]


def _classify_one(failure: TestFailure) -> ClassifiedFailure:
    """Classify a single failure."""
    text = f"{failure.error_message}\n{failure.full_output}"

    for category, base_confidence, patterns in RULES:
        for pattern, summary_template in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    summary = summary_template.format(*m.groups())
                except (IndexError, KeyError):
                    summary = summary_template
                return ClassifiedFailure(
                    failure=failure,
                    category=category,
                    confidence=base_confidence,
                    summary=summary,
                )

    # No match
    error_preview = failure.error_message[:80] if failure.error_message else "Unknown error"
    return ClassifiedFailure(
        failure=failure,
        category=FailureCategory.UNKNOWN,
        confidence=0.3,
        summary=error_preview,
    )
