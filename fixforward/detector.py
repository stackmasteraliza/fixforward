"""Ecosystem detection and test runner."""

import subprocess
import time
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class Ecosystem(Enum):
    PYTHON = "python"
    NODE = "node"
    RUST = "rust"


class DetectionError(Exception):
    pass


@dataclass
class TestFailure:
    test_name: str
    file_path: str
    line_number: Optional[int]
    error_message: str
    full_output: str


@dataclass
class TestResult:
    passed: bool
    exit_code: int
    raw_output: str
    total_tests: int
    passed_count: int
    failed_count: int
    failures: List[TestFailure] = field(default_factory=list)
    duration_seconds: float = 0.0


# Test commands for each ecosystem
TEST_COMMANDS = {
    Ecosystem.PYTHON: ["python3", "-m", "pytest", "--tb=long", "-v"],
    Ecosystem.NODE: ["npm", "test", "--"],
    Ecosystem.RUST: ["cargo", "test"],
}


def detect(project_path: str) -> Ecosystem:
    """Detect which ecosystem a project uses."""
    path = Path(project_path).resolve()

    if not path.exists():
        raise DetectionError(f"Path does not exist: {path}")

    if not path.is_dir():
        raise DetectionError(f"Not a directory: {path}")

    # Check Python indicators
    if (path / "pytest.ini").exists():
        return Ecosystem.PYTHON
    if (path / "pyproject.toml").exists():
        content = (path / "pyproject.toml").read_text()
        if "[tool.pytest" in content or "pytest" in content:
            return Ecosystem.PYTHON
    if (path / "setup.cfg").exists():
        content = (path / "setup.cfg").read_text()
        if "[tool:pytest]" in content:
            return Ecosystem.PYTHON
    # Fallback: any test_*.py files
    if list(path.rglob("test_*.py")) or list(path.rglob("*_test.py")):
        return Ecosystem.PYTHON

    # Check Node indicators
    if (path / "package.json").exists():
        return Ecosystem.NODE

    # Check Rust indicators
    if (path / "Cargo.toml").exists():
        return Ecosystem.RUST

    raise DetectionError(
        "Could not detect project ecosystem. "
        "Looked for: pytest.ini, pyproject.toml, test_*.py, package.json, Cargo.toml"
    )


def run_tests(project_path: str, ecosystem: Ecosystem) -> TestResult:
    """Run the test suite and parse results."""
    from fixforward.parsers import parse_pytest, parse_npm, parse_cargo

    path = Path(project_path).resolve()
    cmd = TEST_COMMANDS[ecosystem]

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(path),
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            passed=False,
            exit_code=-1,
            raw_output="Test execution timed out after 120 seconds.",
            total_tests=0,
            passed_count=0,
            failed_count=0,
            failures=[
                TestFailure(
                    test_name="<timeout>",
                    file_path="",
                    line_number=None,
                    error_message="Test execution timed out after 120 seconds",
                    full_output="",
                )
            ],
            duration_seconds=120.0,
        )
    except FileNotFoundError:
        raise DetectionError(
            f"Test command not found: {cmd[0]}. "
            f"Make sure {cmd[0]} is installed and in your PATH."
        )

    elapsed = time.time() - start
    raw_output = proc.stdout + proc.stderr

    # Parse with the appropriate parser
    parsers = {
        Ecosystem.PYTHON: parse_pytest,
        Ecosystem.NODE: parse_npm,
        Ecosystem.RUST: parse_cargo,
    }

    result = parsers[ecosystem](raw_output)
    result.exit_code = proc.returncode
    result.raw_output = raw_output
    result.duration_seconds = elapsed
    result.passed = proc.returncode == 0 and result.failed_count == 0

    return result
