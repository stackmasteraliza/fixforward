"""CLI entry point for FixForward."""

import argparse
import sys
import json

from fixforward import __version__
from fixforward.display import Display
from fixforward.detector import detect, run_tests, Ecosystem
from fixforward.classifier import classify
from fixforward.copilot import generate_patch, explain_failure, CopilotError
from fixforward.patcher import apply_patch, PatchError
from fixforward.verifier import verify
from fixforward.reporter import generate_report
from fixforward.state import rollback, RollbackError


def _cmd_run(args):
    """Full autopilot: detect -> classify -> patch -> verify -> report."""
    display = Display(animate=not args.no_animate)
    display.show_banner()

    # Step 1: Detect ecosystem
    display.step(1, "Detecting project ecosystem...")
    try:
        ecosystem = detect(args.path)
    except Exception as e:
        display.error(f"Detection failed: {e}")
        sys.exit(1)
    display.ecosystem_found(ecosystem)

    # Step 2: Run tests
    display.step(2, "Running tests to capture failures...")
    result = run_tests(args.path, ecosystem)

    if result.passed:
        display.all_tests_pass(result)
        return

    display.failures_found(result)

    # Step 3: Classify failures
    display.step(3, "Classifying failures...")
    classifications = classify(result.failures, ecosystem)
    display.show_classifications(classifications)

    if args.dry_run:
        display.dry_run_summary(classifications)
        return

    # Step 4: Generate patch via Copilot CLI
    display.step(4, "Asking GitHub Copilot for a fix...")
    try:
        patch = generate_patch(
            failures=classifications,
            project_path=args.path,
            ecosystem=ecosystem,
            verbose=args.verbose,
        )
    except CopilotError as e:
        display.error(f"Copilot failed: {e}")
        sys.exit(1)

    display.show_patch_preview(patch)

    # Confirm
    if not args.no_confirm:
        if not display.confirm_apply():
            display.aborted()
            return

    # Step 5: Apply patch
    display.step(5, "Applying patch on a safe branch...")
    try:
        branch_info = apply_patch(patch, args.path)
    except PatchError as e:
        display.error(f"Patch failed: {e}")
        sys.exit(1)
    display.patch_applied(branch_info)

    # Step 6: Verify
    display.step(6, "Re-running tests to verify fix...")
    verify_result = verify(args.path, ecosystem, result)
    display.show_verification(verify_result)

    # Generate report
    pr_info = generate_report(
        classifications=classifications,
        patch=patch,
        verify_result=verify_result,
        ecosystem=ecosystem,
    )
    display.show_pr_report(pr_info)
    display.done()


def _cmd_diagnose(args):
    """Detect and classify failures without fixing."""
    display = Display(animate=not getattr(args, "no_animate", False))
    display.show_banner()

    display.step(1, "Detecting project ecosystem...")
    try:
        ecosystem = detect(args.path)
    except Exception as e:
        display.error(f"Detection failed: {e}")
        sys.exit(1)
    display.ecosystem_found(ecosystem)

    display.step(2, "Running tests to capture failures...")
    result = run_tests(args.path, ecosystem)

    if result.passed:
        display.all_tests_pass(result)
        return

    display.failures_found(result)

    display.step(3, "Classifying failures...")
    classifications = classify(result.failures, ecosystem)

    if getattr(args, "json_output", False):
        data = [
            {
                "test": c.failure.test_name,
                "file": c.failure.file_path,
                "line": c.failure.line_number,
                "category": c.category.value,
                "confidence": c.confidence,
                "summary": c.summary,
                "error": c.failure.error_message,
            }
            for c in classifications
        ]
        print(json.dumps(data, indent=2))
    else:
        display.show_classifications(classifications)

        # Ask Copilot to explain each failure
        display.step(4, "Asking Copilot to explain failures...")
        for c in classifications:
            try:
                explanation = explain_failure(c, args.path)
                display.show_explanation(c, explanation)
            except CopilotError:
                display.show_explanation(c, "(Copilot CLI unavailable)")

    display.diagnose_done()


def _cmd_rollback(args):
    """Undo the last fixforward patch."""
    display = Display(animate=False)
    display.show_banner()

    try:
        info = rollback(args.path)
        display.rollback_success(info)
    except RollbackError as e:
        display.error(f"Rollback failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="fixforward",
        description="Incident-to-PR autopilot powered by GitHub Copilot CLI.",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"fixforward {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Full autopilot: detect, fix, verify, report")
    run_parser.add_argument("--path", "-p", default=".", help="Path to the project (default: .)")
    run_parser.add_argument("--dry-run", "-n", action="store_true", help="Show plan without executing")
    run_parser.add_argument("--no-confirm", action="store_true", help="Skip patch confirmation prompt")
    run_parser.add_argument("--no-animate", action="store_true", help="Disable animations")
    run_parser.add_argument("--verbose", action="store_true", help="Show raw Copilot output")

    # diagnose command
    diag_parser = subparsers.add_parser("diagnose", help="Detect and classify failures only")
    diag_parser.add_argument("--path", "-p", default=".", help="Path to the project (default: .)")
    diag_parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    diag_parser.add_argument("--no-animate", action="store_true", help="Disable animations")

    # rollback command
    rb_parser = subparsers.add_parser("rollback", help="Undo the last fixforward patch")
    rb_parser.add_argument("--path", "-p", default=".", help="Path to the project (default: .)")

    args = parser.parse_args()

    if args.command is None:
        # Default to run
        args.command = "run"
        args.path = "."
        args.dry_run = False
        args.no_confirm = False
        args.no_animate = False
        args.verbose = False

    commands = {
        "run": _cmd_run,
        "diagnose": _cmd_diagnose,
        "rollback": _cmd_rollback,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
    except Exception as e:
        from rich.console import Console
        Console(stderr=True).print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
