"""Rich-based terminal UI for FixForward."""

import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.columns import Columns
from rich.markdown import Markdown
from rich import box

ACCENT = "bright_cyan"
WARN = "bright_yellow"
ERROR = "bright_red"
SUCCESS = "bright_green"
DIM = "dim"

BANNER = r"""
  _____ _      _____                            _
 |  ___(_)_  _|  ___|__  _ ____      ____ _ _ __| |
 | |_  | \ \/ / |_ / _ \| '__\ \ /\ / / _` | '__| |/ _` |
 |  _| | |>  <|  _| (_) | |   \ V  V / (_| | |  | | (_| |
 |_|   |_/_/\_\_|  \___/|_|    \_/\_/ \__,_|_|  |_|\__,_|
"""

CATEGORY_ICONS = {
    "dependency": "[bright_magenta]PKG[/]",
    "syntax_error": "[bright_red]SYN[/]",
    "assertion": "[bright_yellow]AST[/]",
    "api_change": "[bright_cyan]API[/]",
    "env_mismatch": "[bright_blue]ENV[/]",
    "lint": "[bright_white]LNT[/]",
    "flaky_test": "[dim]FLK[/]",
    "unknown": "[dim]???[/]",
}

ECOSYSTEM_ICONS = {
    "python": "Python / pytest",
    "node": "Node.js / npm test",
    "rust": "Rust / cargo test",
}


class Display:
    def __init__(self, animate=True):
        self.console = Console()
        self.animate = animate
        self._step_count = 0

    def _pause(self, seconds=0.5):
        if self.animate:
            time.sleep(seconds)

    def show_banner(self):
        self.console.print(
            Panel(
                Text(BANNER, style=f"bold {ACCENT}"),
                subtitle="[dim]incident-to-PR autopilot powered by GitHub Copilot CLI[/]",
                border_style=ACCENT,
                box=box.DOUBLE_EDGE,
                padding=(0, 2),
            )
        )
        self._pause(0.3)

    def step(self, num, message):
        self._step_count = num
        self.console.print()
        if self.animate:
            with Progress(
                SpinnerColumn(style=ACCENT),
                TextColumn(f"[bold bright_white]\\[{num}/6] {message}[/]"),
                transient=True,
                console=self.console,
            ) as progress:
                progress.add_task("step", total=None)
                time.sleep(0.8)
        self.console.print(f"  [bold {ACCENT}][{num}/6][/] [bold]{message}[/]")

    def ecosystem_found(self, ecosystem):
        name = ECOSYSTEM_ICONS.get(ecosystem.value, ecosystem.value)
        self.console.print(
            Panel(
                f"[bold {SUCCESS}]Detected:[/] {name}",
                border_style=SUCCESS,
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def all_tests_pass(self, result):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {SUCCESS}]All {result.total_tests} tests pass![/]\n"
                f"[dim]Nothing to fix. Your project is healthy.[/]",
                title="[bold green]ALL CLEAR[/]",
                border_style=SUCCESS,
                box=box.DOUBLE_EDGE,
                padding=(1, 2),
            )
        )

    def failures_found(self, result):
        self.console.print(
            Panel(
                f"[bold {ERROR}]{result.failed_count} failed[/] / "
                f"[{SUCCESS}]{result.passed_count} passed[/] / "
                f"[dim]{result.total_tests} total[/]  "
                f"[dim]({result.duration_seconds:.1f}s)[/]",
                title="[bold red]TEST FAILURES DETECTED[/]",
                border_style=ERROR,
                box=box.HEAVY,
                padding=(0, 2),
            )
        )

    def show_classifications(self, classifications):
        table = Table(
            title="[bold]Failure Classification[/]",
            box=box.SIMPLE_HEAVY,
            show_lines=True,
            title_style="bold bright_white",
            border_style="bright_blue",
        )
        table.add_column("", width=3, justify="center")
        table.add_column("Test", style="bold bright_white", max_width=35)
        table.add_column("File", style="dim", max_width=30)
        table.add_column("Category", justify="center")
        table.add_column("Confidence", justify="center", max_width=10)
        table.add_column("Summary", max_width=45)

        for c in classifications:
            icon = CATEGORY_ICONS.get(c.category.value, "[dim]?[/]")
            conf_color = SUCCESS if c.confidence >= 0.7 else (WARN if c.confidence >= 0.4 else ERROR)
            conf_bar = _confidence_bar(c.confidence, conf_color)
            loc = c.failure.file_path
            if c.failure.line_number:
                loc += f":{c.failure.line_number}"
            table.add_row(
                icon,
                c.failure.test_name,
                loc,
                f"[bold]{c.category.value}[/]",
                conf_bar,
                c.summary,
            )

        self.console.print()
        self.console.print(table)

    def show_patch_preview(self, patch):
        self.console.print()
        for change in patch.changes:
            self.console.print(
                Panel(
                    Syntax(change.diff, "diff", theme="monokai", line_numbers=False),
                    title=f"[bold bright_white]{change.file_path}[/]",
                    border_style="bright_cyan",
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )

        if patch.explanation:
            self.console.print(
                Panel(
                    patch.explanation,
                    title="[bold]Copilot's Explanation[/]",
                    border_style="bright_magenta",
                    box=box.ROUNDED,
                    padding=(0, 2),
                )
            )

    def confirm_apply(self):
        self.console.print()
        return Confirm.ask(
            f"  [{ACCENT}]Apply this patch?[/]",
            default=True,
            console=self.console,
        )

    def patch_applied(self, branch_info):
        self.console.print(
            Panel(
                f"[bold {SUCCESS}]Branch:[/] {branch_info.name}\n"
                f"[dim]Files changed: {', '.join(branch_info.files_changed)}[/]",
                title="[bold green]PATCH APPLIED[/]",
                border_style=SUCCESS,
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def show_verification(self, verify_result):
        self.console.print()

        # Before / After comparison
        before_text = (
            f"[bold {ERROR}]{verify_result.original.failed_count} failed[/] / "
            f"[{SUCCESS}]{verify_result.original.passed_count} passed[/]\n"
            f"[dim]{verify_result.original.total_tests} total[/]"
        )
        after_text = (
            f"[bold {ERROR if verify_result.after_fix.failed_count > 0 else SUCCESS}]"
            f"{verify_result.after_fix.failed_count} failed[/] / "
            f"[{SUCCESS}]{verify_result.after_fix.passed_count} passed[/]\n"
            f"[dim]{verify_result.after_fix.total_tests} total[/]"
        )

        before_panel = Panel(
            before_text,
            title="[bold red]BEFORE[/]",
            border_style="red",
            box=box.ROUNDED,
            width=35,
            padding=(0, 2),
        )
        after_panel = Panel(
            after_text,
            title=f"[bold green]AFTER[/]",
            border_style="green",
            box=box.ROUNDED,
            width=35,
            padding=(0, 2),
        )

        self.console.print(Columns([before_panel, after_panel], padding=2))

        # Confidence score
        conf = verify_result.confidence
        conf_color = SUCCESS if conf >= 0.7 else (WARN if conf >= 0.4 else ERROR)
        bar = _confidence_bar_large(conf, conf_color)
        self.console.print(
            Panel(
                f"  {bar}  [{conf_color}]{conf:.0%}[/]",
                title="[bold]Confidence Score[/]",
                border_style=conf_color,
                box=box.HEAVY,
                padding=(0, 2),
            )
        )

        if verify_result.all_passing:
            self.console.print(
                f"\n  [bold {SUCCESS}]All tests passing after fix![/]"
            )
        elif verify_result.fixed_count > 0:
            self.console.print(
                f"\n  [{WARN}]Fixed {verify_result.fixed_count} of "
                f"{verify_result.original.failed_count} failures[/]"
            )

    def show_pr_report(self, pr_info):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold bright_white]{pr_info.title}[/]",
                title="[bold]PR Title[/]",
                border_style=ACCENT,
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )
        self.console.print(
            Panel(
                Markdown(pr_info.body),
                title="[bold]PR Body[/]",
                border_style=ACCENT,
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def dry_run_summary(self, classifications):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {WARN}]DRY RUN[/] — would attempt to fix "
                f"{len(classifications)} classified failure(s).\n"
                f"[dim]Run without --dry-run to apply fixes.[/]",
                border_style=WARN,
                box=box.DOUBLE_EDGE,
                padding=(0, 2),
            )
        )

    def show_explanation(self, classification, explanation):
        self.console.print(
            Panel(
                explanation,
                title=f"[bold]{classification.failure.test_name}[/]",
                subtitle=f"[dim]{classification.category.value}[/]",
                border_style="bright_magenta",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def diagnose_done(self):
        self.console.print()
        self.console.print(
            f"  [dim]Run [bold]fixforward run[/bold] to auto-fix these failures.[/]"
        )

    def rollback_success(self, info):
        self.console.print(
            Panel(
                f"[bold {SUCCESS}]Restored to branch:[/] {info['original_branch']}\n"
                f"[dim]Deleted branch: {info['fixforward_branch']}[/]",
                title="[bold green]ROLLBACK COMPLETE[/]",
                border_style=SUCCESS,
                box=box.DOUBLE_EDGE,
                padding=(0, 2),
            )
        )

    def aborted(self):
        self.console.print(f"\n  [{WARN}]Aborted. No changes made.[/]")

    def info(self, message):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]{message}[/]",
                title="[bold cyan]INFO[/]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

    def error(self, message):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {ERROR}]{message}[/]",
                title="[bold red]ERROR[/]",
                border_style=ERROR,
                box=box.HEAVY,
                padding=(0, 2),
            )
        )

    def done(self):
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {SUCCESS}]FixForward complete![/]\n"
                f"[dim]Review the branch, then push and open a PR.[/]",
                border_style=SUCCESS,
                box=box.DOUBLE_EDGE,
                padding=(0, 2),
            )
        )


def _confidence_bar(conf, color):
    filled = int(conf * 5)
    empty = 5 - filled
    return f"[{color}]{'█' * filled}{'░' * empty}[/] [{color}]{conf:.0%}[/]"


def _confidence_bar_large(conf, color):
    filled = int(conf * 20)
    empty = 20 - filled
    return f"[{color}]{'█' * filled}{'░' * empty}[/]"
