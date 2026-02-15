<div align="center">

# FixForward

### Incident-to-PR autopilot powered by GitHub Copilot CLI.

[![PyPI version](https://img.shields.io/pypi/v/fixforward?color=brightgreen&label=PyPI)](https://pypi.org/project/fixforward/)
[![Python](https://img.shields.io/pypi/pyversions/fixforward?color=blue)](https://pypi.org/project/fixforward/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**One command to go from broken build to ready-to-merge PR.**

```
pip install fixforward
```

</div>

---

When builds or tests fail, most devs lose time figuring out root cause and writing the fix. FixForward turns one command into a full recovery workflow:

```
fixforward run
```

It detects failures, classifies the issue, asks GitHub Copilot CLI to generate a minimal patch, applies it on a safe branch, re-runs tests to verify, and generates a PR description — all in your terminal.

## Demo

<!-- Replace with actual demo GIF -->
<!-- ![fixforward demo](screenshots/demo.gif) -->

```
$ fixforward run --path ./my-broken-project

  [1/6] Detecting project ecosystem...       → Python / pytest
  [2/6] Running tests to capture failures... → 1 failed / 4 passed
  [3/6] Classifying failures...              → assertion (85% confidence)
  [4/6] Asking GitHub Copilot for a fix...   → Patch generated
  [5/6] Applying patch on a safe branch...   → fixforward/auto-20260215-130944
  [6/6] Re-running tests to verify fix...    → 0 failed / 5 passed ✓

  Confidence: ███████████████████░ 95%
  All tests passing after fix!
```

## How It Works

```
tests fail → parse output → classify failure → Copilot generates fix → apply on branch → verify → PR report
     │            │               │                    │                     │           │         │
   pytest     extract          regex             gh copilot -p          git branch    re-run   markdown
   npm test   failures       heuristics        "fix this bug..."      safe commit    tests    PR body
   cargo test                                                                        diff
```

1. **Detect** — finds `pytest.ini`, `package.json`, or `Cargo.toml` to identify your ecosystem
2. **Run tests** — executes the test suite and captures the raw output
3. **Parse** — extracts individual test failures with file paths, line numbers, and error messages
4. **Classify** — categorizes failures (dependency, syntax, assertion, API change, env mismatch, lint, flaky)
5. **Generate patch** — sends failure context to GitHub Copilot CLI (`gh copilot -p`) for a minimal fix
6. **Apply** — creates a `fixforward/auto-*` branch, writes the fix, commits
7. **Verify** — re-runs the test suite, shows before/after comparison with confidence score
8. **Report** — generates PR title and body with what changed and why

## Supported Ecosystems

| Ecosystem | Test Command | Parser |
|-----------|-------------|--------|
| **Python** | `pytest --tb=long -v` | Extracts failures, tracebacks, assertion details |
| **Node.js** | `npm test` | Supports Jest and Mocha output formats |
| **Rust** | `cargo test` | Parses panics, `assert_eq!` failures, test summaries |

## Features

| Feature | Description |
|---------|-------------|
| **Auto-detect** | Identifies Python, Node, or Rust projects automatically |
| **Smart classification** | Categorizes failures: dependency, syntax, assertion, API change, env, lint, flaky |
| **Copilot-powered fixes** | Uses `gh copilot -p` to generate minimal patches |
| **Safe branches** | Always applies fixes on a `fixforward/auto-*` branch, never touches your working branch |
| **Before/after verification** | Re-runs tests and shows what changed |
| **Confidence scoring** | 0-100% score based on how many failures were fixed |
| **PR report generation** | Ready-to-use PR title and body in Markdown |
| **Dry-run mode** | Preview the diagnosis without applying any changes |
| **Rollback** | One command to undo everything: `fixforward rollback` |
| **Patch preview** | See the exact diff before confirming |

## Quick Start

```bash
pip install fixforward
```

Or install from source:

```bash
git clone https://github.com/stackmasteraliza/fixforward.git
cd fixforward
pip install -e .
```

### Prerequisites

- Python 3.9+
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- [GitHub Copilot CLI](https://gh.io/copilot-cli) — `gh copilot` must be available
- Git installed and in PATH

## Usage

```bash
# Full autopilot: detect, fix, verify, report
fixforward run

# Specify a project path
fixforward run --path ~/projects/my-broken-app

# Dry run: see diagnosis without applying fixes
fixforward run --dry-run

# Skip confirmation prompt
fixforward run --no-confirm

# Diagnose only: detect and classify failures
fixforward diagnose

# Diagnose with JSON output
fixforward diagnose --json

# Undo the last fix
fixforward rollback
```

You can also run it as a Python module:

```bash
python -m fixforward run --path ./my-project
```

## CLI Options

### `fixforward run`

| Flag | Description |
|------|-------------|
| `--path`, `-p` | Path to the project (default: `.`) |
| `--dry-run`, `-n` | Show diagnosis without applying fixes |
| `--no-confirm` | Skip the patch confirmation prompt |
| `--no-animate` | Disable loading animations |
| `--verbose` | Show raw Copilot CLI output |

### `fixforward diagnose`

| Flag | Description |
|------|-------------|
| `--path`, `-p` | Path to the project (default: `.`) |
| `--json` | Output classification as JSON |
| `--no-animate` | Disable loading animations |

### `fixforward rollback`

| Flag | Description |
|------|-------------|
| `--path`, `-p` | Path to the project (default: `.`) |

## Failure Categories

FixForward classifies failures using regex heuristics for instant, deterministic results:

| Category | Examples | Confidence |
|----------|----------|------------|
| **syntax_error** | `SyntaxError`, `IndentationError`, `Unexpected token` | 95% |
| **dependency** | `ModuleNotFoundError`, `Cannot find module`, `ImportError` | 90% |
| **api_change** | `AttributeError`, `TypeError` (wrong args), `has no member` | 85% |
| **assertion** | `AssertionError`, `assert_eq!`, `expect().toEqual()` | 85% |
| **env_mismatch** | Version conflicts, missing commands, engine incompatible | 80% |
| **lint** | Flake8, ESLint, Clippy warnings | 75% |
| **flaky_test** | Timeouts, connection refused, intermittent | 60% |

## Safety

FixForward is designed to be safe by default:

- **Never modifies your working branch** — all fixes go on `fixforward/auto-*` branches
- **Stashes dirty state** — if you have uncommitted changes, they're stashed and restored on rollback
- **Patch preview** — see the exact diff before confirming
- **Dry-run mode** — diagnose without touching anything
- **One-command rollback** — `fixforward rollback` restores everything
- **State persistence** — rollback info stored at `~/.fixforward/state.json`

## Built With GitHub Copilot CLI

This project was built using [GitHub Copilot CLI](https://gh.io/copilot-cli) as part of the GitHub Copilot CLI Challenge on DEV. Copilot CLI is central to the tool — it powers the actual fix generation via `gh copilot -p`:

```bash
# How FixForward uses Copilot CLI internally:
gh copilot -- -p "I have a python project with failing tests.
  The test test_divide in test_app.py fails with AssertionError:
  assert 3.333 == 3. Generate a minimal fix..." \
  --allow-all-tools --add-dir ./project --silent
```

Copilot CLI reads the source files, understands the context, and generates the smallest possible code change. FixForward then applies it, verifies it, and reports the result.

## Architecture

```
fixforward/
├── cli.py          # argparse CLI with run/diagnose/rollback commands
├── detector.py     # Ecosystem detection + test runner (subprocess)
├── classifier.py   # Regex heuristic failure classification
├── copilot.py      # GitHub Copilot CLI integration (gh copilot -p)
├── patcher.py      # Safe branch creation + file patching
├── verifier.py     # Test re-run + confidence scoring
├── reporter.py     # PR title/body generation
├── display.py      # Rich-based terminal UI
├── state.py        # Rollback state persistence
└── parsers/
    ├── pytest_parser.py   # pytest output parser
    ├── npm_parser.py      # Jest/Mocha output parser
    └── cargo_parser.py    # cargo test output parser
```

**Only dependency:** [`rich`](https://github.com/Textualize/rich) — everything else is Python stdlib.

## Requirements

- Python 3.9+
- Git installed and in PATH
- GitHub CLI (`gh`) with Copilot access
- Terminal with color support

---

<div align="center">

MIT License — see [LICENSE](LICENSE) for details.

**If you like this project, give it a star!**

</div>
