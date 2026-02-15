"""GitHub Copilot CLI integration layer."""

import subprocess
import re
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from fixforward.detector import Ecosystem
from fixforward.classifier import ClassifiedFailure


class CopilotError(Exception):
    pass


@dataclass
class FileChange:
    file_path: str
    original_content: str
    modified_content: str
    diff: str


@dataclass
class PatchResult:
    changes: List[FileChange]
    explanation: str
    raw_copilot_output: str


def generate_patch(
    failures: List[ClassifiedFailure],
    project_path: str,
    ecosystem: Ecosystem,
    verbose: bool = False,
) -> PatchResult:
    """Ask Copilot CLI to generate a fix for classified failures."""
    prompt = _build_fix_prompt(failures, project_path, ecosystem)

    raw_output = _run_copilot(prompt, project_path)

    if verbose:
        from rich.console import Console
        Console(stderr=True).print(f"[dim]Copilot raw output:\n{raw_output}[/]")

    # Parse response into file changes
    changes = _parse_response(raw_output, project_path)
    explanation = _extract_explanation(raw_output)

    if not changes:
        raise CopilotError(
            "Copilot did not produce any file changes. "
            "Try running again or fixing manually."
        )

    return PatchResult(
        changes=changes,
        explanation=explanation,
        raw_copilot_output=raw_output,
    )


def explain_failure(
    classification: ClassifiedFailure,
    project_path: str,
) -> str:
    """Ask Copilot CLI to explain a failure."""
    prompt = (
        f"Explain this test failure concisely:\n"
        f"Test: {classification.failure.test_name}\n"
        f"File: {classification.failure.file_path}\n"
        f"Error: {classification.failure.error_message}\n"
        f"Category: {classification.category.value}\n\n"
        f"What is the likely root cause and how should it be fixed?"
    )

    try:
        return _run_copilot(prompt, project_path)
    except CopilotError:
        return f"({classification.category.value}) {classification.summary}"


def _run_copilot(prompt: str, project_path: str, allow_write: bool = False) -> str:
    """Execute gh copilot in non-interactive mode with -p flag."""
    # Check if gh is available
    try:
        check = subprocess.run(
            ["gh", "copilot", "--", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise CopilotError(
            "GitHub CLI (gh) is not installed. "
            "Install it from: https://cli.github.com/"
        )

    # Build the command using non-interactive prompt mode
    # gh copilot -- -p "prompt" --allow-all-tools --add-dir <path> --quiet
    cmd = [
        "gh", "copilot", "--",
        "-p", prompt,
        "--allow-all-tools",
        "--add-dir", str(Path(project_path).resolve()),
        "--silent",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(project_path).resolve()),
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        raise CopilotError("Copilot CLI timed out after 180 seconds.")

    output = result.stdout + result.stderr
    if not output.strip():
        raise CopilotError("Copilot returned empty response.")

    return output.strip()


def _build_fix_prompt(
    failures: List[ClassifiedFailure],
    project_path: str,
    ecosystem: Ecosystem,
) -> str:
    """Build a prompt for Copilot to generate a fix."""
    failure_descriptions = []
    source_context = []

    for f in failures[:3]:  # Limit to top 3 failures
        desc = (
            f"- [{f.category.value}] {f.failure.test_name}\n"
            f"  File: {f.failure.file_path}"
        )
        if f.failure.line_number:
            desc += f":{f.failure.line_number}"
        desc += f"\n  Error: {f.failure.error_message}"
        failure_descriptions.append(desc)

        # Read source file for context
        src_path = Path(project_path) / f.failure.file_path
        if src_path.exists():
            try:
                content = src_path.read_text()
                source_context.append(
                    f"--- {f.failure.file_path} ---\n{content}"
                )
            except Exception:
                pass

    failures_text = "\n".join(failure_descriptions)
    sources_text = "\n\n".join(source_context) if source_context else "(no source files read)"

    return (
        f"I have a {ecosystem.value} project with failing tests. "
        f"Generate a minimal fix.\n\n"
        f"FAILURES:\n{failures_text}\n\n"
        f"SOURCE FILES:\n{sources_text}\n\n"
        f"Generate the smallest possible code change to fix these failures. "
        f"Show the complete corrected file content for each file that needs changes. "
        f"Format each fix as:\n"
        f"FILE: <filepath>\n"
        f"```\n<complete corrected file content>\n```\n\n"
        f"Then explain what you changed and why."
    )


def _parse_response(raw_output: str, project_path: str) -> List[FileChange]:
    """Parse Copilot's response to extract file changes."""
    changes = []

    # Strategy 1: Look for FILE: <path> followed by code blocks
    # Handle markdown bold: **FILE: app.py** or FILE: app.py
    file_pattern = re.compile(
        r"\*{0,2}FILE:\s*(.+?)\*{0,2}\s*\n\s*```\w*\n(.+?)```",
        re.DOTALL,
    )
    for m in file_pattern.finditer(raw_output):
        file_path = m.group(1).strip().strip("*")
        new_content = m.group(2)

        original_path = Path(project_path) / file_path
        original_content = ""
        if original_path.exists():
            original_content = original_path.read_text()

        if new_content.strip() != original_content.strip():
            diff = _make_diff(file_path, original_content, new_content)
            changes.append(FileChange(
                file_path=file_path,
                original_content=original_content,
                modified_content=new_content,
                diff=diff,
            ))

    # Strategy 2: Look for diff blocks
    if not changes:
        diff_pattern = re.compile(r"```diff\n(.+?)```", re.DOTALL)
        for m in diff_pattern.finditer(raw_output):
            diff_text = m.group(1)
            # Try to extract filename from diff header
            file_match = re.search(r"[+-]{3}\s+[ab]/(.+)", diff_text)
            if file_match:
                file_path = file_match.group(1).strip()
                changes.append(FileChange(
                    file_path=file_path,
                    original_content="",
                    modified_content="",
                    diff=diff_text,
                ))

    # Strategy 3: Look for any code blocks with identifiable file content
    if not changes:
        code_pattern = re.compile(r"```(\w+)\n(.+?)```", re.DOTALL)
        for m in code_pattern.finditer(raw_output):
            lang = m.group(1)
            content = m.group(2)

            # Try to match against existing project files
            ext_map = {"python": ".py", "javascript": ".js", "rust": ".rs",
                       "py": ".py", "js": ".js", "rs": ".rs"}
            ext = ext_map.get(lang, "")
            if ext:
                project = Path(project_path)
                for src_file in project.rglob(f"*{ext}"):
                    if src_file.is_file():
                        original = src_file.read_text()
                        # Check if this looks like a modified version
                        similarity = difflib.SequenceMatcher(
                            None, original, content
                        ).ratio()
                        if 0.5 < similarity < 1.0:
                            rel_path = str(src_file.relative_to(project))
                            diff = _make_diff(rel_path, original, content)
                            changes.append(FileChange(
                                file_path=rel_path,
                                original_content=original,
                                modified_content=content,
                                diff=diff,
                            ))
                            break

    return changes


def _extract_explanation(raw_output: str) -> str:
    """Extract the explanation section from Copilot's response."""
    # Look for common markers
    markers = [
        r"(?:explanation|what changed|changes made|summary):?\s*\n(.+)",
        r"(?:I changed|I fixed|The fix|This fixes|The issue).+",
    ]
    for pattern in markers:
        m = re.search(pattern, raw_output, re.IGNORECASE | re.DOTALL)
        if m:
            text = m.group(0) if m.lastindex is None else m.group(1)
            # Trim to reasonable length
            lines = text.strip().splitlines()
            return "\n".join(lines[:10])

    # Fallback: last paragraph
    paragraphs = raw_output.strip().split("\n\n")
    if paragraphs:
        return paragraphs[-1][:500]
    return ""


def _make_diff(file_path: str, original: str, modified: str) -> str:
    """Generate a unified diff string."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "".join(diff)
