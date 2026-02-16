---
title: "FixForward: One Command to Go from Broken Build to Ready-to-Merge PR"
published: false
tags: devchallenge, githubchallenge, cli, githubcopilot
---

# FixForward: Incident-to-PR Autopilot Powered by GitHub Copilot CLI

#devchallenge #githubchallenge #cli #githubcopilot

**GitHub Copilot CLI Challenge Submission**

*This is my submission for the [GitHub Copilot CLI Challenge](https://dev.to/challenges/github).*

## What I Built

Every developer knows the pain: your build breaks, your tests fail, and suddenly you're down a rabbit hole of stack traces, file-hopping, and manual patching. I've been there one too many times, so I built **FixForward** — a CLI autopilot that takes you from broken tests to a verified, ready-to-merge PR in a single command.

```bash
pip install fixforward
fixforward run
```

That's it. One command.

FixForward detects your test framework, runs the suite, parses the failures, classifies each one, asks **GitHub Copilot CLI** to generate a minimal fix, applies it on a safe branch, re-runs your tests to verify the fix actually works, and generates a PR description with a confidence score. The entire pipeline is automated, and the entire tool is powered by Copilot CLI under the hood.

![FixForward Cover](https://raw.githubusercontent.com/stackmasteraliza/fixforward/main/assets/cover.png)

## Demo

Here is FixForward running against a real broken Python project. It detects the failing test, classifies the bug as an assertion failure, generates a one-line fix via Copilot CLI, patches the file, re-runs the tests, and reports 95% confidence — all without leaving the terminal:

![FixForward Demo](https://raw.githubusercontent.com/stackmasteraliza/fixforward/main/assets/demo.gif)

## The Pipeline: How It Works

FixForward is not a wrapper around a single Copilot prompt. It's a **full incident response pipeline** with 8 distinct stages:

```
tests fail → parse output → classify failure → Copilot generates fix
     → apply on safe branch → re-run tests → confidence score → PR report
```

**1. Detect** — Scans for `pytest.ini`, `package.json`, or `Cargo.toml` to identify your ecosystem automatically. No config files, no setup.

**2. Run Tests** — Executes your test suite (`pytest`, `npm test`, or `cargo test`) and captures full raw output.

**3. Parse** — Custom parsers extract individual failures with file paths, line numbers, error messages, and tracebacks. This isn't regex on the whole blob — there are dedicated parsers for pytest, Jest/Mocha, and cargo test that understand each format's quirks.

**4. Classify** — Categorizes every failure using heuristic pattern matching:

| Category | Examples | Confidence |
|----------|----------|------------|
| `syntax_error` | `SyntaxError`, `IndentationError`, `Unexpected token` | 95% |
| `dependency` | `ModuleNotFoundError`, `Cannot find module` | 90% |
| `api_change` | `AttributeError`, `TypeError` (wrong args) | 85% |
| `assertion` | `AssertionError`, `assert_eq!`, `expect().toEqual()` | 85% |
| `env_mismatch` | Version conflicts, missing commands | 80% |
| `lint` | Flake8, ESLint, Clippy warnings | 75% |
| `flaky_test` | Timeouts, connection refused, intermittent | 60% |

**5. Generate Patch** — Sends structured failure context + relevant source files to GitHub Copilot CLI (`gh copilot -p`) for a minimal fix. Copilot reads the actual code, understands the bug, and generates the smallest possible change.

**6. Apply** — Creates a `fixforward/auto-*` branch, writes the patched files, and commits. Your working branch is **never touched**.

**7. Verify** — Re-runs the entire test suite on the fix branch and computes a before/after confidence score.

**8. Report** — Generates a Markdown PR title and body with what changed, why, and the verification results.

## Screenshots

### Full Autopilot Run
The complete pipeline from broken tests to verified fix:

![Full run](https://raw.githubusercontent.com/stackmasteraliza/fixforward/main/assets/screenshot_run.png)

### Diagnose Mode
Use `fixforward diagnose` to inspect failures without applying any changes:

![Diagnose](https://raw.githubusercontent.com/stackmasteraliza/fixforward/main/assets/screenshot_diagnose.png)

### Dependency Detection
FixForward recognizes when the fix isn't a code change but a missing package:

![Dependency](https://raw.githubusercontent.com/stackmasteraliza/fixforward/main/assets/screenshot_dependency.png)

### Multi-Ecosystem: Node.js Support
Same pipeline, different ecosystem. Jest failures parsed and classified automatically:

![Node.js](https://raw.githubusercontent.com/stackmasteraliza/fixforward/main/assets/screenshot_nodejs.png)

## Three Ecosystems, One Interface

| Ecosystem | Test Command | What Gets Parsed |
|-----------|-------------|------------------|
| **Python** | `pytest --tb=long -v` | Failures, tracebacks, assertion details, collection errors |
| **Node.js** | `npm test` | Jest and Mocha output, suite-level failures, missing modules |
| **Rust** | `cargo test` | Panics, `assert_eq!` failures, test summaries |

I didn't just support one language and call it a day. Each ecosystem has its own parser that understands the specific output format — pytest tracebacks look nothing like Jest failures, and cargo test panics are their own thing entirely. FixForward handles all of them.

## Safety First

I spent a lot of time thinking about what could go wrong. When you're auto-applying code patches, you better not destroy someone's working tree. FixForward has several layers of protection:

- **Never touches your working branch** — all fixes go on `fixforward/auto-*` branches
- **Stashes dirty state** — uncommitted changes are saved and restored on rollback
- **Patch preview** — see the exact diff before confirming
- **Dry-run mode** — `fixforward run --dry-run` diagnoses without touching anything
- **One-command rollback** — `fixforward rollback` undoes everything cleanly
- **State persistence** — rollback info stored at `~/.fixforward/state.json`

I wanted this to be a tool you could trust running in your repo without hesitation.

## My Experience with GitHub Copilot CLI

Copilot CLI is not just a helper in this project — it **is** the engine. FixForward uses `gh copilot -p` at its core to generate the actual code fixes. Here's what that looks like internally:

```bash
gh copilot -- -p "I have a python project with failing tests.
  The test test_divide in test_app.py fails with AssertionError:
  assert 3.333 == 3. Generate a minimal fix..." \
  --allow-all-tools --add-dir ./project --silent
```

Copilot reads the source files through `--add-dir`, understands the test context, and generates the smallest code change. FixForward then parses Copilot's response (which can come in several formats — code blocks, file headers, inline diffs), extracts the patched files, and applies them.

Building the Copilot response parser was one of the trickier parts. Copilot doesn't always respond in the same format, so I built multiple parsing strategies:

1. **Fenced code blocks** with `FILE:` markers
2. **Filename headers** (### file.js, **file.js**, backtick file.js) followed by code blocks
3. **Language-tagged blocks** matched to project files
4. **Fuzzy file matching** against the project tree (skipping node_modules)

If one strategy fails, the next one kicks in. This makes FixForward resilient to Copilot's varying output formats.

I also used Copilot CLI extensively during development — for scaffolding parsers, debugging edge cases in Jest output handling, and figuring out the right subprocess patterns for capturing test output across platforms.

## Try It Yourself

The repo includes ready-made broken demo projects:

```bash
git clone https://github.com/stackmasteraliza/fixforward.git
cd fixforward

# Python: division bug (a / b should be a // b)
fixforward run --path demo/broken_python

# Node.js: truncation bug ("..." becomes "..")
fixforward diagnose --path demo/broken_node

# Rust: off-by-one in clamp()
fixforward diagnose --path demo/broken_rust

# Safe mode: see the diagnosis without changing anything
fixforward run --path demo/broken_python --dry-run
```

Install from PyPI:

```bash
pip install fixforward
```

## Architecture

```
fixforward/
├── cli.py          # argparse CLI: run, diagnose, rollback
├── detector.py     # Ecosystem detection + test runner
├── classifier.py   # Regex heuristic failure classification
├── copilot.py      # GitHub Copilot CLI integration
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

**Only one dependency:** [`rich`](https://github.com/Textualize/rich). Everything else is Python standard library.

## Links

- **PyPI:** [fixforward on PyPI](https://pypi.org/project/fixforward/)
- **Repo:** [stackmasteraliza/fixforward on GitHub](https://github.com/stackmasteraliza/fixforward)

---

Thanks for reading! I'd love to hear your feedback — especially if you try it on your own broken tests.
