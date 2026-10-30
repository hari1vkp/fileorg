"""The fileorg command line interface."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Sequence

from app.core.constants import APP_VERSION, UNKNOWN_FOLDER
from app.core.exceptions import FileorgError, JournalNotFoundError
from app.models.organise import Move, OrganiseOptions
from app.services.organise_service import OrganiseService
from app.utils.helpers import plural


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fileorg",
        description=(
            "Organise a folder into category subfolders "
            "(Images, Videos, Documents, ...). Dry run unless --apply is given."
        ),
        epilog=(
            "examples:\n"
            "  fileorg                       preview ~/Downloads\n"
            "  fileorg ~/Downloads --apply   move the files\n"
            "  fileorg --undo --apply        undo the last run\n"
            "  fileorg ~/Downloads --dest ~/Sorted --apply --recursive\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        nargs="?",
        default="~/Downloads",
        help="folder to organise (default: ~/Downloads)",
    )
    parser.add_argument(
        "-d",
        "--dest",
        help="where the category folders live (default: the source folder)",
    )
    parser.add_argument(
        "-n",
        "--apply",
        action="store_true",
        help="actually move files (without this it is a dry run)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="also organise files inside subfolders",
    )
    parser.add_argument(
        "-u",
        "--move-unknown",
        action="store_true",
        help=f'move unrecognised files into an "{UNKNOWN_FOLDER}" folder',
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="include dotfiles and hidden folders",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATTERN",
        help="skip names matching this glob (repeatable)",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="reverse the most recent run (combine with --apply)",
    )
    parser.add_argument("--journal", help="undo a specific journal file")
    parser.add_argument(
        "--state-dir",
        help="folder for journals (default: platform state folder)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print every file as it is handled",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    return parser


def print_counts(moves: Sequence[Move]) -> None:
    counts = Counter(move.folder for move in moves)
    width = max((len(folder) for folder in counts), default=0) + 1
    for folder in sorted(counts):
        print(f"  {folder + '/':<{width}}  {plural(counts[folder], 'file')}")


def undo_hint() -> str:
    script = Path(sys.argv[0]).name
    if script.endswith(".py"):
        return f"python3 {script} --undo --apply"
    return f"{script} --undo --apply"


def run_organise(args: argparse.Namespace, service: OrganiseService) -> int:
    options = OrganiseOptions(
        recursive=args.recursive,
        ignore=tuple(args.ignore),
        include_hidden=args.include_hidden,
        move_unknown=args.move_unknown,
    )
    try:
        plan = service.preview(args.source, args.dest, options)
    except FileorgError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for warning in plan.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    mode = "" if args.apply else " (dry run)"
    print(f"fileorg {APP_VERSION} - {plan.source}{mode}")
    print()

    if not plan.moves:
        if plan.unknown:
            print(
                f"Nothing to move. {plural(len(plan.unknown), 'unrecognised file')} "
                "left in place."
            )
        else:
            print("Nothing to organise - this folder is already tidy.")
        return 0

    print_counts(plan.moves)
    if plan.unknown:
        print(
            f"\n  {plural(len(plan.unknown), 'unrecognised file')} left in place "
            "(use --move-unknown)."
        )

    if args.verbose:
        print()
        for move in plan.moves:
            print(f"  {move.relative_source(plan.source)} -> {move.destination_label()}")

    if not args.apply:
        print(f"\nWould move {plural(len(plan.moves), 'file')}. Re-run with --apply to do it.")
        return 0

    def on_move(move: Move) -> None:
        print(f"  {move.src.name} -> {move.folder}/{move.dst.name}")

    try:
        result = service.organise(plan, on_move=on_move if args.verbose else None)
    except FileorgError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        f"\nMoved {plural(result.moved_count, 'file')} into "
        f"{plural(plan.folder_count, 'folder')}."
    )
    for error in result.errors:
        print(f"error: could not move {error.path}: {error.message}", file=sys.stderr)
    if result.journal is not None:
        print(f"Journal: {result.journal}")
        print(f"Undo with: {undo_hint()}")
    return 1 if result.errors else 0


def run_undo(args: argparse.Namespace, service: OrganiseService) -> int:
    try:
        undo_plan = service.load_undo(args.journal)
    except JournalNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except FileorgError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(
        f"fileorg {APP_VERSION} - undo of run from "
        f"{undo_plan.created or 'unknown time'}"
    )
    print(f"Journal: {undo_plan.journal}\n")

    for path in undo_plan.missing:
        print(f"warning: missing, skipped: {path}", file=sys.stderr)
    if not undo_plan.entries:
        print("Nothing to restore.")
        return 1 if undo_plan.missing else 0

    counts = Counter(
        move.dst.parent.name or str(move.dst.parent) for move in undo_plan.entries
    )
    width = max(len(name) for name in counts) + 1
    for name in sorted(counts):
        print(f"  {name + '/':<{width}}  {plural(counts[name], 'file')}")
    if args.verbose:
        print()
        for move in undo_plan.entries:
            print(f"  {move.src} -> {move.dst}")

    if not args.apply:
        print(
            f"\nWould restore {plural(len(undo_plan.entries), 'file')}. "
            "Re-run with --apply to do it."
        )
        return 0

    result = service.undo(undo_plan)
    if result.restored:
        print(f"\nRestored {plural(len(result.restored), 'file')}.")
        if result.removed:
            print(f"Removed {plural(len(result.removed), 'empty folder')}.")
    for error in result.errors:
        print(f"error: could not restore {error.path}: {error.message}", file=sys.stderr)
    return 1 if result.errors or result.missing else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.journal and not args.undo:
        parser.error("--journal can only be used together with --undo")

    state_dir = Path(args.state_dir).expanduser() if args.state_dir else None
    service = OrganiseService(state_dir)
    try:
        if args.undo:
            return run_undo(args, service)
        return run_organise(args, service)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
