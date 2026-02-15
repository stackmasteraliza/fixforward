"""Rollback state persistence."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List

STATE_DIR = Path.home() / ".fixforward"
STATE_FILE = STATE_DIR / "state.json"


class RollbackError(Exception):
    pass


@dataclass
class RollbackState:
    project_path: str
    original_branch: str
    fixforward_branch: str
    stash_ref: Optional[str]
    timestamp: str
    files_changed: List[str]


def save_state(state: RollbackState):
    """Save rollback state to disk."""
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))


def load_state() -> Optional[RollbackState]:
    """Load rollback state from disk."""
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text())
        return RollbackState(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def clear_state():
    """Remove rollback state."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def rollback(project_path: str) -> dict:
    """Undo the last fixforward patch."""
    import subprocess

    state = load_state()
    if state is None:
        raise RollbackError(
            "No fixforward state found. Nothing to rollback.\n"
            "State is saved at: ~/.fixforward/state.json"
        )

    path = Path(project_path).resolve()
    state_path = Path(state.project_path).resolve()

    # Verify we're in the right project
    if str(path) != str(state_path):
        raise RollbackError(
            f"State is for project: {state.project_path}\n"
            f"But you're in: {project_path}"
        )

    def _git(args):
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=str(path),
        )
        if result.returncode != 0:
            raise RollbackError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    # Switch back to original branch
    _git(["checkout", state.original_branch])

    # Delete the fixforward branch
    try:
        _git(["branch", "-D", state.fixforward_branch])
    except RollbackError:
        pass  # Branch might already be deleted

    # Restore stash if one was created
    if state.stash_ref:
        try:
            _git(["stash", "pop"])
        except RollbackError:
            pass  # Stash might already be popped

    info = {
        "original_branch": state.original_branch,
        "fixforward_branch": state.fixforward_branch,
    }

    clear_state()
    return info
