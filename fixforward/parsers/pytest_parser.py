"""Parse pytest verbose output into TestResult."""

import re
from fixforward.detector import TestResult, TestFailure

# Patterns
# Match summary lines like "1 failed, 4 passed in 0.02s" or "5 passed in 0.01s"
SUMMARY_RE = re.compile(r"=+\s*(.+?)\s+in\s+([\d.]+)s\s*=+")
FAILED_COUNT_RE = re.compile(r"(\d+)\s+failed")
PASSED_COUNT_RE = re.compile(r"(\d+)\s+passed")
ERROR_COUNT_RE = re.compile(r"(\d+)\s+error")
SHORT_SUMMARY_RE = re.compile(r"=+\s*short test summary info\s*=+")
FAILED_LINE_RE = re.compile(r"FAILED\s+(.+?)::(.+?)(?:\s*-\s*(.*))?$")
ERROR_LINE_RE = re.compile(r"ERROR\s+(.+?)::(.+?)(?:\s*-\s*(.*))?$")
# Collection errors: "ERROR collecting <file>" or just "ERROR <file>"
ERROR_COLLECT_RE = re.compile(r"ERROR\s+(?:collecting\s+)?(\S+\.py)\s*$")
PASSED_LINE_RE = re.compile(r"(\S+\.py)::(\S+)\s+PASSED")
SECTION_SEP_RE = re.compile(r"_{5,}\s+(.+?)\s+_{5,}")
TRACEBACK_FILE_RE = re.compile(r"(\S+\.py):(\d+):")
# Collection error block header
COLLECT_ERROR_RE = re.compile(r"_{5,}\s+ERROR collecting\s+(\S+\.py)\s+_{5,}")


def parse(raw_output: str) -> TestResult:
    """Parse pytest -v --tb=long output."""
    lines = raw_output.splitlines()

    failures = []
    passed_count = 0
    failed_count = 0
    error_count = 0
    duration = 0.0

    # Try to extract from summary line
    for line in reversed(lines):
        m = SUMMARY_RE.search(line)
        if m:
            summary_text = m.group(1)
            duration = float(m.group(2))
            fm = FAILED_COUNT_RE.search(summary_text)
            if fm:
                failed_count = int(fm.group(1))
            pm = PASSED_COUNT_RE.search(summary_text)
            if pm:
                passed_count = int(pm.group(1))
            em = ERROR_COUNT_RE.search(summary_text)
            if em:
                error_count = int(em.group(1))
            break

    # Extract individual failure details
    # Look for FAILED lines in the short summary section
    in_summary = False
    for line in lines:
        if SHORT_SUMMARY_RE.search(line):
            in_summary = True
            continue
        if in_summary:
            m = FAILED_LINE_RE.search(line)
            if m:
                file_path = m.group(1)
                test_name = m.group(2)
                error_msg = m.group(3) or ""
                # Try to find line number from traceback
                line_num = _find_line_number(lines, file_path, test_name)
                # Get full traceback for this test
                full_output = _extract_traceback(lines, test_name)
                failures.append(TestFailure(
                    test_name=test_name,
                    file_path=file_path,
                    line_number=line_num,
                    error_message=error_msg.strip(),
                    full_output=full_output,
                ))
            m = ERROR_LINE_RE.search(line)
            if m:
                file_path = m.group(1)
                test_name = m.group(2)
                error_msg = m.group(3) or ""
                failures.append(TestFailure(
                    test_name=test_name,
                    file_path=file_path,
                    line_number=None,
                    error_message=error_msg.strip(),
                    full_output="",
                ))

    # If no FAILED lines found in summary, try scanning for FAILED in body
    if not failures and failed_count > 0:
        for line in lines:
            m = FAILED_LINE_RE.search(line)
            if m:
                file_path = m.group(1)
                test_name = m.group(2)
                error_msg = m.group(3) or ""
                line_num = _find_line_number(lines, file_path, test_name)
                full_output = _extract_traceback(lines, test_name)
                failures.append(TestFailure(
                    test_name=test_name,
                    file_path=file_path,
                    line_number=line_num,
                    error_message=error_msg.strip(),
                    full_output=full_output,
                ))

    # Handle collection errors (e.g. "ERROR collecting foo_test.py")
    if not failures and error_count > 0:
        seen_files = set()
        for line in lines:
            m = ERROR_COLLECT_RE.search(line)
            if m and m.group(1) not in seen_files:
                file_path = m.group(1)
                seen_files.add(file_path)
                # Extract the error from the collection error block
                error_msg, full_output = _extract_collection_error(
                    lines, file_path
                )
                failures.append(TestFailure(
                    test_name=f"collect: {file_path}",
                    file_path=file_path,
                    line_number=None,
                    error_message=error_msg,
                    full_output=full_output,
                ))
                if len(failures) >= 5:  # Limit — they're often all the same error
                    break

    # Fallback: count from individual test lines
    if passed_count == 0 and failed_count == 0:
        for line in lines:
            if "PASSED" in line:
                passed_count += 1
            elif "FAILED" in line:
                failed_count += 1
            elif "ERROR" in line and "::" in line:
                error_count += 1

    total = passed_count + failed_count + error_count
    failed_count = failed_count + error_count  # Treat errors as failures

    return TestResult(
        passed=failed_count == 0,
        exit_code=0,
        raw_output=raw_output,
        total_tests=total,
        passed_count=passed_count,
        failed_count=failed_count,
        failures=failures,
        duration_seconds=duration,
    )


def _find_line_number(lines, file_path, test_name):
    """Try to find the line number where the failure occurred."""
    in_traceback = False
    last_line_num = None
    for line in lines:
        if test_name in line and ("FAILED" in line or "____" in line):
            in_traceback = True
            continue
        if in_traceback:
            m = TRACEBACK_FILE_RE.search(line)
            if m:
                last_line_num = int(m.group(2))
            if line.startswith("=") or (line.startswith("_") and len(line) > 10):
                break
    return last_line_num


def _extract_collection_error(lines, file_path):
    """Extract error message from a collection error block."""
    capturing = False
    result = []
    error_msg = ""
    for line in lines:
        if f"ERROR collecting {file_path}" in line and "___" in line:
            capturing = True
            continue
        if capturing:
            if line.startswith("=") and len(line) > 10:
                break
            if line.startswith("_") and "ERROR collecting" in line:
                break
            result.append(line)
            # Capture the E line (actual error)
            stripped = line.strip()
            if stripped.startswith("E   ") or stripped.startswith("E\t"):
                error_msg = stripped[1:].strip()
    return error_msg or "(collection error)", "\n".join(result[-20:])


def _extract_traceback(lines, test_name):
    """Extract the full traceback block for a specific test."""
    result = []
    capturing = False
    for line in lines:
        if f"__ {test_name} __" in line or f"__{test_name}__" in line.replace(" ", ""):
            capturing = True
            continue
        if capturing:
            if line.startswith("=") and len(line) > 10:
                break
            if line.startswith("_") and len(line.strip("_ ")) > 0 and test_name not in line:
                break
            result.append(line)
    return "\n".join(result)
