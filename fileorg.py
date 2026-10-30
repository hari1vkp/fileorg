#!/usr/bin/env python3
"""fileorg - tidy up a folder by moving files into category subfolders.

Examples:
    python3 fileorg.py ~/Downloads          # dry run (the default)
    python3 fileorg.py ~/Downloads --apply  # actually move files
    python3 fileorg.py --undo               # preview undoing the last run
    python3 fileorg.py --undo --apply       # actually undo it

This module is a thin command line entry point. The implementation lives in
:mod:`app.cli`, and the shared core lives in :mod:`app.core`.
"""

from __future__ import annotations

from app import __version__
from app.cli import build_parser, main
from app.core.constants import UNKNOWN_FOLDER
from app.core.fileops import apply_moves, prune_empty_dirs, undo_moves
from app.core.journal import latest_journal, plan_undo, read_journal, write_journal
from app.core.planner import (
    build_moves,
    extension_map,
    iter_files,
    reserve_path,
    split_name,
)
from app.models.organise import Move

__all__ = [
    "__version__",
    "Move",
    "UNKNOWN_FOLDER",
    "apply_moves",
    "build_moves",
    "build_parser",
    "extension_map",
    "iter_files",
    "latest_journal",
    "main",
    "plan_undo",
    "prune_empty_dirs",
    "read_journal",
    "reserve_path",
    "split_name",
    "undo_moves",
    "write_journal",
]

if __name__ == "__main__":
    raise SystemExit(main())
