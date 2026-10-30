"""Application service that coordinates planning, moving and undoing.

The GUI, the CLI and the tests all go through this one service, so there is a
single implementation of the organiser's behaviour.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import default_state_dir
from app.core.exceptions import (
    InvalidDestinationError,
    InvalidSourceError,
    JournalNotFoundError,
    OrganiseError,
    ScanError,
)
from app.core.fileops import apply_moves, undo_moves
from app.core.journal import (
    format_created,
    latest_journal,
    mark_undone,
    plan_undo,
    read_journal,
)
from app.core.planner import build_moves
from app.models.organise import (
    Move,
    OrganiseOptions,
    OrganisePlan,
    OrganiseResult,
    UndoPlan,
    UndoResult,
)

MoveCallback = Callable[[Move], None]


class OrganiseService:
    """High-level operations for organising a folder and undoing a run."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()

    def preview(
        self,
        source: str | Path,
        destination: str | Path | None = None,
        options: OrganiseOptions | None = None,
    ) -> OrganisePlan:
        """Validate the inputs and build a plan without touching the disk."""
        options = options or OrganiseOptions()
        source_path = Path(source).expanduser()
        if not source_path.exists():
            raise InvalidSourceError(f"folder not found: {source_path}")
        if not source_path.is_dir():
            raise InvalidSourceError(f"not a folder: {source_path}")

        dest_path = Path(destination).expanduser() if destination else source_path
        if dest_path.exists() and not dest_path.is_dir():
            raise InvalidDestinationError(f"destination is not a folder: {dest_path}")

        source_path = source_path.resolve()
        dest_path = dest_path.resolve()
        try:
            moves, unknown, warnings = build_moves(
                source_path,
                dest_path,
                recursive=options.recursive,
                ignore=options.ignore,
                include_hidden=options.include_hidden,
                move_unknown=options.move_unknown,
            )
        except OSError as error:
            raise ScanError(f"could not scan folder: {error}") from error

        return OrganisePlan(
            source=source_path,
            destination=dest_path,
            options=options,
            moves=moves,
            unknown=unknown,
            warnings=warnings,
        )

    def organise(
        self,
        plan: OrganisePlan,
        on_move: MoveCallback | None = None,
    ) -> OrganiseResult:
        """Apply a plan and journal the files that moved."""
        try:
            journal, errors = apply_moves(
                plan.moves,
                self.state_dir,
                plan.source,
                plan.destination,
                on_move=on_move,
            )
        except OSError as error:
            raise OrganiseError(f"could not finish the run: {error}") from error
        return OrganiseResult(
            journal=journal,
            planned=len(plan.moves),
            errors=errors,
        )

    def has_undo(self) -> bool:
        return latest_journal(self.state_dir) is not None

    def latest_journal(self) -> Path | None:
        return latest_journal(self.state_dir)

    def load_undo(self, journal_path: str | Path | None = None) -> UndoPlan:
        """Read a journal and prepare the moves that restore the files."""
        path = (
            Path(journal_path).expanduser()
            if journal_path is not None
            else latest_journal(self.state_dir)
        )
        if path is None:
            raise JournalNotFoundError(f"no journal found in {self.state_dir}")
        if not path.is_file():
            raise JournalNotFoundError(f"journal not found: {path}")

        data = read_journal(path)
        entries, missing = plan_undo(data)
        destination = _path_or_default(data.get("dest"), Path("."))
        source = _path_or_default(data.get("source"), Path("."))
        return UndoPlan(
            journal=path,
            created=format_created(data.get("created")),
            source=source,
            destination=destination,
            entries=entries,
            missing=missing,
            raw=data,
        )

    def undo(self, undo_plan: UndoPlan) -> UndoResult:
        """Apply an undo plan, clean up empty folders and close the journal."""
        restored, errors, removed = undo_moves(undo_plan.entries, undo_plan.destination)
        if restored:
            mark_undone(undo_plan.journal)
        return UndoResult(
            restored=restored,
            errors=errors,
            removed=removed,
            missing=list(undo_plan.missing),
        )


def _path_or_default(value: object, fallback: Path) -> Path:
    if isinstance(value, str) and value:
        return Path(value)
    return fallback
