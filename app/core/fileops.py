"""Filesystem operations: moving files and cleaning up emptied folders."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Iterable, Sequence

from app.core.journal import write_journal
from app.core.planner import reserve_path
from app.models.organise import Move, MoveError

MoveCallback = Callable[[Move], None]


def apply_moves(
    moves: Sequence[Move],
    state_dir: Path,
    source: Path,
    dest_root: Path,
    *,
    verbose: bool = False,
    on_move: MoveCallback | None = None,
) -> tuple[Path | None, list[MoveError]]:
    """Move the files, journalling whatever succeeded."""
    done: list[Move] = []
    errors: list[MoveError] = []
    journal_path: Path | None = None
    try:
        for move in moves:
            try:
                # Re-check: something may have appeared since planning.
                if move.dst.exists():
                    move.dst = reserve_path(move.dst, set())
                move.dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(move.src), str(move.dst))
            except OSError as error:
                errors.append(MoveError(move.src, str(error)))
                continue
            done.append(move)
            if verbose:
                print(f"  {move.src.name} -> {move.folder}/{move.dst.name}")
            if on_move is not None:
                on_move(move)
    finally:
        if done:
            journal_path = write_journal(state_dir, source, dest_root, done)
    return journal_path, errors


def undo_moves(
    entries: Sequence[Move],
    destination: Path,
) -> tuple[list[Move], list[MoveError], list[Path]]:
    """Put files back and remove the category folders that were emptied."""
    restored: list[Move] = []
    errors: list[MoveError] = []
    for move in entries:
        try:
            move.dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(move.src), str(move.dst))
        except OSError as error:
            errors.append(MoveError(move.src, str(error)))
            continue
        restored.append(move)

    removed: list[Path] = []
    if restored:
        removed = prune_empty_dirs(
            {move.src.parent for move in restored},
            destination,
        )
    return restored, errors, removed


def prune_empty_dirs(dirs: Iterable[Path], stop: Path) -> list[Path]:
    """Remove empty folders left behind, never removing ``stop`` itself."""
    removed: list[Path] = []
    stop_resolved = stop.resolve()
    candidates = sorted(set(dirs), key=lambda path: len(path.parts), reverse=True)
    for directory in candidates:
        current = directory
        while True:
            try:
                resolved = current.resolve()
            except OSError:
                break
            if resolved == stop_resolved or stop_resolved not in resolved.parents:
                break
            try:
                if not current.is_dir() or any(current.iterdir()):
                    break
                current.rmdir()
            except OSError:
                break
            removed.append(current)
            current = current.parent
    return removed
