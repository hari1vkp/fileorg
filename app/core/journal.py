"""Reading and writing undo journals."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.core.constants import (
    APP_VERSION,
    JOURNAL_PREFIX,
    JOURNAL_SUFFIX,
    JOURNAL_VERSION,
)
from app.core.exceptions import JournalReadError
from app.core.planner import reserve_path
from app.models.organise import Move


def write_journal(
    state_dir: Path,
    source: Path,
    dest_root: Path,
    moves: Sequence[Move],
) -> Path:
    """Persist what was moved so the run can be undone."""
    state_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = state_dir / f"{JOURNAL_PREFIX}{stamp}{JOURNAL_SUFFIX}"
    payload = {
        "version": JOURNAL_VERSION,
        "tool": f"fileorg {APP_VERSION}",
        "created": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "dest": str(dest_root),
        "moves": [{"src": str(m.src), "dst": str(m.dst)} for m in moves],
    }
    _atomic_write_json(path, payload)
    return path


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def latest_journal(state_dir: Path) -> Path | None:
    """Return the most recent journal that has not been undone yet."""
    if not state_dir.is_dir():
        return None
    journals = sorted(state_dir.glob(f"{JOURNAL_PREFIX}*{JOURNAL_SUFFIX}"))
    return journals[-1] if journals else None


def read_journal(path: Path) -> dict[str, Any]:
    """Read a journal, raising a friendly error if it is unusable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise JournalReadError(f"could not read journal: {error}") from error
    except json.JSONDecodeError as error:
        raise JournalReadError(f"journal is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise JournalReadError("journal has an unexpected format")
    return data


def plan_undo(data: dict[str, Any]) -> tuple[list[Move], list[Path]]:
    """Turn a journal into moves that put everything back."""
    entries: list[Move] = []
    missing: list[Path] = []
    reserved: set[Path] = set()
    raw_moves = data.get("moves", [])
    if not isinstance(raw_moves, list):
        raise JournalReadError("journal is missing its move list")
    for item in reversed(raw_moves):
        try:
            current = Path(item["dst"])
            original = Path(item["src"])
        except (KeyError, TypeError) as error:
            raise JournalReadError("journal contains an invalid move") from error
        if not current.exists():
            missing.append(current)
            continue
        if original.exists():
            original = reserve_path(original, reserved)
        else:
            reserved.add(original)
        entries.append(Move(current, original, original.parent.name))
    return entries, missing


def mark_undone(path: Path) -> Path:
    """Rename a journal so the next undo targets the run before it."""
    target = path.with_name(path.name + ".undone")
    try:
        path.replace(target)
    except OSError:
        return path
    return target


def format_created(value: Any) -> str | None:
    """Format a journal timestamp for display."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value
