"""Parse cargo test output into TestResult."""

import re
from fixforward.detector import TestResult, TestFailure

# Patterns
SUMMARY_RE = re.compile(
    r"test result:\s+(ok|FAILED)\.\s+(\d+)\s+passed;\s+(\d+)\s+failed;\s+"
    r"(\d+)\s+ignored;"
)
PANICKED_RE = re.compile(
    r"thread\s+'(.+?)'\s+panicked\s+at\s+'?(.+?)'?,?\s+(.+?):(\d+)"
)
# Alternative panicked format (newer Rust)
PANICKED_ALT_RE = re.compile(
    r"thread\s+'(.+?)'\s+panicked\s+at\s+(.+?):(\d+):\d+:\s*\n\s*(.+)"
)
TEST_FAIL_RE = re.compile(r"^test\s+(\S+)\s+\.\.\.\s+FAILED$", re.MULTILINE)
STDOUT_SECTION_RE = re.compile(r"---- (\S+) stdout ----")
ASSERTION_RE = re.compile(
    r"assertion.*failed.*\n\s+left:\s*`(.+?)`\s*\n\s+right:\s*`(.+?)`",
    re.MULTILINE,
)


def parse(raw_output: str) -> TestResult:
    """Parse cargo test output."""

    # Extract summary
    summary = SUMMARY_RE.search(raw_output)
    if summary:
        passed_count = int(summary.group(2))
        failed_count = int(summary.group(3))
        ignored = int(summary.group(4))
        total = passed_count + failed_count + ignored
    else:
        # Count individual test lines
        passed_count = raw_output.count("... ok")
        failed_count = raw_output.count("... FAILED")
        total = passed_count + failed_count

    failures = []

    # Find panicked tests
    for m in PANICKED_RE.finditer(raw_output):
        test_name = m.group(1)
        error_msg = m.group(2)
        file_path = m.group(3)
        line_number = int(m.group(4))

        # Get stdout section
        full_output = _extract_stdout(raw_output, test_name)

        # Check for assertion details
        assertion = ASSERTION_RE.search(full_output)
        if assertion:
            error_msg = f"left: {assertion.group(1)}, right: {assertion.group(2)}"

        failures.append(TestFailure(
            test_name=test_name,
            file_path=file_path,
            line_number=line_number,
            error_message=error_msg,
            full_output=full_output,
        ))

    # Try alternative panic format
    if not failures:
        for m in PANICKED_ALT_RE.finditer(raw_output):
            test_name = m.group(1)
            file_path = m.group(2)
            line_number = int(m.group(3))
            error_msg = m.group(4).strip()

            full_output = _extract_stdout(raw_output, test_name)
            failures.append(TestFailure(
                test_name=test_name,
                file_path=file_path,
                line_number=line_number,
                error_message=error_msg,
                full_output=full_output,
            ))

    # Fallback: just find FAILED test names
    if not failures and failed_count > 0:
        for m in TEST_FAIL_RE.finditer(raw_output):
            test_name = m.group(1)
            failures.append(TestFailure(
                test_name=test_name,
                file_path="",
                line_number=None,
                error_message="Test failed (see raw output)",
                full_output=_extract_stdout(raw_output, test_name),
            ))

    return TestResult(
        passed=failed_count == 0,
        exit_code=0,
        raw_output=raw_output,
        total_tests=total,
        passed_count=passed_count,
        failed_count=failed_count,
        failures=failures,
    )


def _extract_stdout(raw_output: str, test_name: str) -> str:
    """Extract the stdout section for a specific test."""
    # Look for ---- test_name stdout ----
    # The test name in stdout sections uses the short name
    short_name = test_name.split("::")[-1] if "::" in test_name else test_name
    lines = raw_output.splitlines()
    result = []
    capturing = False
    for line in lines:
        if f"---- {test_name} stdout ----" in line or f"---- {short_name} stdout ----" in line:
            capturing = True
            continue
        if capturing:
            if line.startswith("----") or line.startswith("note:"):
                break
            result.append(line)
    return "\n".join(result)
