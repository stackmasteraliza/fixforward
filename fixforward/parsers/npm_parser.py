"""Parse npm test / Jest / Mocha output into TestResult."""

import re
from fixforward.detector import TestResult, TestFailure

# Jest patterns
JEST_SUMMARY_RE = re.compile(
    r"Tests:\s+(?:(\d+)\s+failed\s*,?\s*)?(?:(\d+)\s+passed\s*,?\s*)?(\d+)\s+total"
)
JEST_FAIL_FILE_RE = re.compile(r"FAIL\s+(.+?)$", re.MULTILINE)
JEST_TEST_FAIL_RE = re.compile(r"\s+[✕×✗]\s+(.+?)(?:\s+\((\d+)\s*ms\))?$", re.MULTILINE)
JEST_EXPECT_RE = re.compile(r"Expected:?\s*(.+?)$", re.MULTILINE)
JEST_RECEIVED_RE = re.compile(r"Received:?\s*(.+?)$", re.MULTILINE)
JEST_AT_RE = re.compile(r"at\s+.*?\((.+?):(\d+):\d+\)")
JEST_TIME_RE = re.compile(r"Time:\s+([\d.]+)\s*s")

# Mocha patterns
MOCHA_PASSING_RE = re.compile(r"(\d+)\s+passing")
MOCHA_FAILING_RE = re.compile(r"(\d+)\s+failing")
MOCHA_FAIL_TITLE_RE = re.compile(r"^\s+\d+\)\s+(.+)$", re.MULTILINE)
MOCHA_ERROR_RE = re.compile(r"^\s+(AssertionError|Error|TypeError|ReferenceError).+$", re.MULTILINE)


def parse(raw_output: str) -> TestResult:
    """Parse npm test / Jest / Mocha output."""

    # Try Jest format first
    jest_match = JEST_SUMMARY_RE.search(raw_output)
    if jest_match:
        return _parse_jest(raw_output, jest_match)

    # Try Mocha format
    mocha_pass = MOCHA_PASSING_RE.search(raw_output)
    mocha_fail = MOCHA_FAILING_RE.search(raw_output)
    if mocha_pass or mocha_fail:
        return _parse_mocha(raw_output, mocha_pass, mocha_fail)

    # Fallback: check exit code indicators
    failed = "FAIL" in raw_output or "ERR!" in raw_output or "Error" in raw_output
    return TestResult(
        passed=not failed,
        exit_code=1 if failed else 0,
        raw_output=raw_output,
        total_tests=0,
        passed_count=0,
        failed_count=1 if failed else 0,
        failures=[
            TestFailure(
                test_name="<unknown>",
                file_path="",
                line_number=None,
                error_message=raw_output[:500],
                full_output=raw_output,
            )
        ] if failed else [],
    )


def _parse_jest(raw_output: str, summary_match):
    """Parse Jest-style output."""
    failed_count = int(summary_match.group(1) or 0)
    passed_count = int(summary_match.group(2) or 0)
    total = int(summary_match.group(3) or 0)

    time_match = JEST_TIME_RE.search(raw_output)
    duration = float(time_match.group(1)) if time_match else 0.0

    failures = []

    # Find FAIL files
    current_file = ""
    for m in JEST_FAIL_FILE_RE.finditer(raw_output):
        current_file = m.group(1).strip()

    # Find individual failing tests
    for m in JEST_TEST_FAIL_RE.finditer(raw_output):
        test_name = m.group(1).strip()
        # Try to find file and line from stack trace
        file_path = current_file
        line_number = None

        # Look for "at" lines after this test
        pos = m.end()
        chunk = raw_output[pos:pos + 1000]
        at_match = JEST_AT_RE.search(chunk)
        if at_match:
            file_path = at_match.group(1)
            line_number = int(at_match.group(2))

        # Get error message
        error_msg = ""
        expect_match = JEST_EXPECT_RE.search(chunk)
        received_match = JEST_RECEIVED_RE.search(chunk)
        if expect_match and received_match:
            error_msg = f"Expected {expect_match.group(1)}, received {received_match.group(1)}"
        elif expect_match:
            error_msg = f"Expected {expect_match.group(1)}"

        failures.append(TestFailure(
            test_name=test_name,
            file_path=file_path,
            line_number=line_number,
            error_message=error_msg,
            full_output=chunk[:500],
        ))

    return TestResult(
        passed=failed_count == 0,
        exit_code=1 if failed_count > 0 else 0,
        raw_output=raw_output,
        total_tests=total,
        passed_count=passed_count,
        failed_count=failed_count,
        failures=failures,
        duration_seconds=duration,
    )


def _parse_mocha(raw_output: str, pass_match, fail_match):
    """Parse Mocha-style output."""
    passed_count = int(pass_match.group(1)) if pass_match else 0
    failed_count = int(fail_match.group(1)) if fail_match else 0
    total = passed_count + failed_count

    failures = []
    for m in MOCHA_FAIL_TITLE_RE.finditer(raw_output):
        test_name = m.group(1).strip()
        # Get error after this line
        pos = m.end()
        chunk = raw_output[pos:pos + 1000]
        error_match = MOCHA_ERROR_RE.search(chunk)
        error_msg = error_match.group(0).strip() if error_match else ""

        at_match = JEST_AT_RE.search(chunk)
        file_path = at_match.group(1) if at_match else ""
        line_number = int(at_match.group(2)) if at_match else None

        failures.append(TestFailure(
            test_name=test_name,
            file_path=file_path,
            line_number=line_number,
            error_message=error_msg,
            full_output=chunk[:500],
        ))

    return TestResult(
        passed=failed_count == 0,
        exit_code=1 if failed_count > 0 else 0,
        raw_output=raw_output,
        total_tests=total,
        passed_count=passed_count,
        failed_count=failed_count,
        failures=failures,
    )
