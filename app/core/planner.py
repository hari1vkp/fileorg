"""Pure planning logic: work out where files should go without moving them."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterable, Sequence

from app.core.constants import (
    COMPOUND_SUFFIXES,
    UNKNOWN_FOLDER,
    extension_map,
)
from app.models.organise import Move


def split_name(name: str) -> tuple[str, str]:
    """Split a filename into stem and suffix, keeping .tar.gz style suffixes."""
    lowered = name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if lowered.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)], name[-len(suffix) :]
    suffix = Path(name).suffix
    if suffix and name != suffix:
        return name[: -len(suffix)], suffix
    return name, ""


def reserve_path(path: Path, reserved: set[Path]) -> Path:
    """Return a free path, adding " (1)", " (2)", ... instead of overwriting."""
    if not path.exists() and path not in reserved:
        reserved.add(path)
        return path

    stem, suffix = split_name(path.name)
    index = 1
    while True:
        candidate = path.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists() and candidate not in reserved:
            reserved.add(candidate)
            return candidate
        index += 1


def iter_files(
    source: Path,
    dest_root: Path,
    *,
    recursive: bool,
    ignore: Sequence[str],
    include_hidden: bool,
    category_dirs: set[str],
    warnings: list[str],
) -> Iterable[Path]:
    """Yield files that should be considered, in a stable order."""
    dest_resolved = dest_root.resolve()

    def is_ignored(path: Path) -> bool:
        rel = path.relative_to(source).as_posix()
        return any(
            fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(rel, pattern)
            for pattern in ignore
        )

    if not recursive:
        with os.scandir(source) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name.lower())
        for entry in ordered:
            path = Path(entry.path)
            if entry.is_symlink():
                warnings.append(f"skipped symlink: {path}")
                continue
            if entry.is_dir(follow_symlinks=False):
                continue
            if not include_hidden and path.name.startswith("."):
                continue
            if is_ignored(path):
                continue
            yield path
        return

    def on_error(error: OSError) -> None:
        warnings.append(f"could not read folder: {error}")

    for root, dirs, files in os.walk(source, onerror=on_error):
        root_path = Path(root)
        keep: list[str] = []
        for name in sorted(dirs, key=str.lower):
            child = root_path / name
            if child.is_symlink():
                warnings.append(f"skipped symlinked folder: {child}")
                continue
            if not include_hidden and name.startswith("."):
                continue
            if is_ignored(child):
                continue
            if child.resolve() == dest_resolved:
                continue
            # Already-organised folders should not be re-processed.
            if root_path.resolve() == dest_resolved and name in category_dirs:
                continue
            keep.append(name)
        dirs[:] = keep

        for name in sorted(files, key=str.lower):
            path = root_path / name
            if path.is_symlink():
                warnings.append(f"skipped symlink: {path}")
                continue
            if not include_hidden and name.startswith("."):
                continue
            if is_ignored(path):
                continue
            yield path


def build_moves(
    source: Path,
    dest_root: Path,
    *,
    recursive: bool = False,
    ignore: Sequence[str] = (),
    include_hidden: bool = False,
    move_unknown: bool = False,
) -> tuple[list[Move], list[Path], list[str]]:
    """Work out where every file should go without touching the disk."""
    mapping = extension_map()
    category_dirs = set(mapping.values())
    if move_unknown:
        category_dirs.add(UNKNOWN_FOLDER)
    warnings: list[str] = []
    moves: list[Move] = []
    unknown: list[Path] = []
    reserved: set[Path] = set()

    for path in iter_files(
        source,
        dest_root,
        recursive=recursive,
        ignore=ignore,
        include_hidden=include_hidden,
        category_dirs=category_dirs,
        warnings=warnings,
    ):
        ext = path.suffix.lower().lstrip(".")
        folder = mapping.get(ext)
        if folder is None:
            if not move_unknown:
                unknown.append(path)
                continue
            folder = UNKNOWN_FOLDER

        target_dir = dest_root / folder
        if path.parent.resolve() == target_dir.resolve():
            continue

        dst = reserve_path(target_dir / path.name, reserved)
        moves.append(Move(path, dst, folder))

    return moves, unknown, warnings
