#!/usr/bin/env python3
"""fileorg - tidy up a folder by moving files into category subfolders.

Examples:
    python3 fileorg.py ~/Downloads          # dry run (the default)
    python3 fileorg.py ~/Downloads --apply  # actually move files
    python3 fileorg.py --undo               # preview undoing the last run
    python3 fileorg.py --undo --apply       # actually undo it
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

__version__ = "1.0.0"

UNKNOWN_FOLDER = "Other"

# Folder name -> space separated extensions (lower case, no leading dot).
CATEGORIES: dict[str, str] = {
    "Images": (
        "jpg jpeg png gif bmp svg webp tiff tif heic heif avif ico "
        "raw cr2 cr3 nef arw dng orf rw2"
    ),
    "Videos": "mp4 mkv mov avi wmv flv webm m4v mpg mpeg mts m2ts 3gp ogv",
    "Audio": "mp3 wav flac aac ogg oga m4a wma opus aiff alac mid midi",
    "Documents": "pdf doc docx txt rtf odt md markdown pages epub mobi azw3 djvu tex",
    "Spreadsheets": "xls xlsx xlsm csv tsv ods numbers",
    "Presentations": "ppt pptx pps ppsx odp key",
    "Archives": "zip rar 7z tar gz bz2 xz zst tgz tbz2 txz iso dmg",
    "Installers": "exe msi deb rpm apk pkg appimage flatpak snap",
    "Code": (
        "py js mjs cjs ts tsx jsx html htm css scss sass less json xml yml yaml "
        "toml ini cfg sh bash zsh fish ps1 bat cmd c h cpp hpp cc java kt go rs "
        "rb php lua pl sql ipynb"
    ),
    "Fonts": "ttf otf woff woff2 eot",
    "Design": "psd ai xcf fig sketch afdesign afphoto",
    "3D": "obj fbx stl glb gltf blend usdz",
}

COMPOUND_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst")


@dataclass
class Move:
    """One planned (or completed) file move."""

    src: Path
    dst: Path
    folder: str


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def default_state_dir() -> Path:
    """Return the platform-appropriate folder for journals."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "fileorg"


def extension_map() -> dict[str, str]:
    """Build a lower-case extension -> folder mapping."""
    mapping: dict[str, str] = {}
    for folder, extensions in CATEGORIES.items():
        for ext in extensions.split():
            mapping[ext] = folder
    return mapping


def split_name(name: str) -> tuple[str, str]:
    """Split a filename into stem and suffix, keeping .tar.gz style suffixes intact."""
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


def write_journal(
    state_dir: Path,
    source: Path,
    dest_root: Path,
    moves: Sequence[Move],
) -> Path:
    """Persist what was moved so the run can be undone."""
    state_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = state_dir / f"journal-{stamp}.json"
    payload = {
        "version": 1,
        "tool": f"fileorg {__version__}",
        "created": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "dest": str(dest_root),
        "moves": [{"src": str(m.src), "dst": str(m.dst)} for m in moves],
    }
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def apply_moves(
    moves: Sequence[Move],
    state_dir: Path,
    source: Path,
    dest_root: Path,
    *,
    verbose: bool = False,
) -> tuple[Path | None, list[tuple[Path, str]]]:
    """Move the files, journalling whatever succeeded."""
    done: list[Move] = []
    errors: list[tuple[Path, str]] = []
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
                errors.append((move.src, str(error)))
                continue
            done.append(move)
            if verbose:
                print(f"  {move.src.name} -> {move.folder}/{move.dst.name}")
    finally:
        if done:
            journal_path = write_journal(state_dir, source, dest_root, done)
    return journal_path, errors


def latest_journal(state_dir: Path) -> Path | None:
    if not state_dir.is_dir():
        return None
    journals = sorted(state_dir.glob("journal-*.json"))
    return journals[-1] if journals else None


def plan_undo(data: dict) -> tuple[list[Move], list[Path]]:
    """Turn a journal into moves that put everything back."""
    entries: list[Move] = []
    missing: list[Path] = []
    reserved: set[Path] = set()
    for item in reversed(data.get("moves", [])):
        current = Path(item["dst"])
        original = Path(item["src"])
        if not current.exists():
            missing.append(current)
            continue
        if original.exists():
            original = reserve_path(original, reserved)
        else:
            reserved.add(original)
        entries.append(Move(current, original, original.parent.name))
    return entries, missing


def prune_empty_dirs(dirs: Iterable[Path], stop: Path) -> list[Path]:
    """Remove empty folders left behind, never removing `stop` itself."""
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


def run_organise(args: argparse.Namespace, state_dir: Path) -> int:
    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"error: folder not found: {source}", file=sys.stderr)
        return 2
    if not source.is_dir():
        print(f"error: not a folder: {source}", file=sys.stderr)
        return 2
    source = source.resolve()

    dest_root = Path(args.dest).expanduser() if args.dest else source
    if dest_root.exists() and not dest_root.is_dir():
        print(f"error: destination is not a folder: {dest_root}", file=sys.stderr)
        return 2
    dest_root = dest_root.resolve()

    moves, unknown, warnings = build_moves(
        source,
        dest_root,
        recursive=args.recursive,
        ignore=args.ignore,
        include_hidden=args.include_hidden,
        move_unknown=args.move_unknown,
    )

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if not args.apply:
        print(f"fileorg {__version__} - {source} (dry run)")
    else:
        print(f"fileorg {__version__} - {source}")
    print()

    if not moves:
        if unknown:
            print(f"Nothing to move. {plural(len(unknown), 'unrecognised file')} left in place.")
        else:
            print("Nothing to organise - this folder is already tidy.")
        return 0

    print_counts(moves)
    if unknown:
        print(f"\n  {plural(len(unknown), 'unrecognised file')} left in place (use --move-unknown).")

    if args.verbose:
        print()
        for move in moves:
            try:
                shown = move.dst.relative_to(dest_root).as_posix()
            except ValueError:
                shown = str(move.dst)
            print(f"  {move.src.name} -> {shown}")

    if not args.apply:
        print(f"\nWould move {plural(len(moves), 'file')}. Re-run with --apply to do it.")
        return 0

    journal_path, errors = apply_moves(
        moves,
        state_dir,
        source,
        dest_root,
        verbose=args.verbose,
    )

    moved = len(moves) - len(errors)
    print(f"\nMoved {plural(moved, 'file')} into {plural(len({m.folder for m in moves}), 'folder')}.")
    for failed, message in errors:
        print(f"error: could not move {failed}: {message}", file=sys.stderr)
    if journal_path is not None:
        print(f"Journal: {journal_path}")
        print(f"Undo with: {undo_hint()}")
    return 1 if errors else 0


def run_undo(args: argparse.Namespace, state_dir: Path) -> int:
    journal_path = Path(args.journal).expanduser() if args.journal else latest_journal(state_dir)
    if journal_path is None:
        print(f"error: no journal found in {state_dir}", file=sys.stderr)
        return 2
    if not journal_path.is_file():
        print(f"error: journal not found: {journal_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: could not read journal: {error}", file=sys.stderr)
        return 2

    entries, missing = plan_undo(data)
    created = data.get("created")
    if isinstance(created, str):
        try:
            created = datetime.fromisoformat(created).astimezone().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    print(f"fileorg {__version__} - undo of run from {created or 'unknown time'}")
    print(f"Journal: {journal_path}\n")

    for path in missing:
        print(f"warning: missing, skipped: {path}", file=sys.stderr)
    if not entries:
        print("Nothing to restore.")
        return 1 if missing else 0

    counts = Counter(move.dst.parent.name or str(move.dst.parent) for move in entries)
    width = max(len(name) for name in counts) + 1
    for name in sorted(counts):
        print(f"  {name + '/':<{width}}  {plural(counts[name], 'file')}")
    if args.verbose:
        print()
        for move in entries:
            print(f"  {move.src} -> {move.dst}")

    if not args.apply:
        print(f"\nWould restore {plural(len(entries), 'file')}. Re-run with --apply to do it.")
        return 0

    errors: list[tuple[Path, str]] = []
    restored: list[Move] = []
    for move in entries:
        try:
            move.dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(move.src), str(move.dst))
        except OSError as error:
            errors.append((move.src, str(error)))
            continue
        restored.append(move)

    if restored:
        removed = prune_empty_dirs(
            {move.src.parent for move in restored},
            Path(data.get("dest", "")),
        )
        print(f"\nRestored {plural(len(restored), 'file')}.")
        if removed:
            print(f"Removed {plural(len(removed), 'empty folder')}.")
        try:
            journal_path.replace(journal_path.with_name(journal_path.name + ".undone"))
        except OSError:
            pass
    for failed, message in errors:
        print(f"error: could not restore {failed}: {message}", file=sys.stderr)
    return 1 if errors or missing else 0


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
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.journal and not args.undo:
        parser.error("--journal can only be used together with --undo")

    state_dir = Path(args.state_dir).expanduser() if args.state_dir else default_state_dir()
    try:
        if args.undo:
            return run_undo(args, state_dir)
        return run_organise(args, state_dir)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
