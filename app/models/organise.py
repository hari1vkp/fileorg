"""Data models for planning, organising and undoing a run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence


@dataclass
class Move:
    """One planned (or completed) file move."""

    src: Path
    dst: Path
    folder: str

    def relative_source(self, root: Path) -> str:
        """Return the source path relative to ``root``, for display."""
        try:
            return self.src.relative_to(root).as_posix()
        except ValueError:
            return str(self.src)

    def destination_label(self) -> str:
        """Return ``Folder/name`` for display in the preview table."""
        return f"{self.folder}/{self.dst.name}"

    def __iter__(self) -> Iterator[Any]:
        # Keeps old tuple-style unpacking working for external callers.
        yield self.src
        yield self.dst
        yield self.folder


@dataclass(frozen=True)
class OrganiseOptions:
    """Options that control how a folder is scanned."""

    recursive: bool = False
    ignore: tuple[str, ...] = ()
    include_hidden: bool = False
    move_unknown: bool = False

    @classmethod
    def from_values(
        cls,
        *,
        recursive: bool,
        ignore: Sequence[str],
        include_hidden: bool,
        move_unknown: bool,
    ) -> "OrganiseOptions":
        cleaned = tuple(pattern.strip() for pattern in ignore if pattern.strip())
        return cls(
            recursive=recursive,
            ignore=cleaned,
            include_hidden=include_hidden,
            move_unknown=move_unknown,
        )


@dataclass
class OrganisePlan:
    """The result of a dry run: what would move, and where."""

    source: Path
    destination: Path
    options: OrganiseOptions
    moves: list[Move] = field(default_factory=list)
    unknown: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.moves

    @property
    def folder_count(self) -> int:
        return len({move.folder for move in self.moves})

    @property
    def is_in_place(self) -> bool:
        return self.source == self.destination


@dataclass
class MoveError:
    """A file that could not be moved, with the reason."""

    path: Path
    message: str

    @property
    def name(self) -> str:
        return self.path.name

    def __iter__(self) -> Iterator[Any]:
        # Keeps old tuple-style unpacking working for external callers.
        yield self.path
        yield self.message


@dataclass
class OrganiseResult:
    """The outcome of an organise run."""

    journal: Path | None
    planned: int
    errors: list[MoveError] = field(default_factory=list)

    @property
    def moved_count(self) -> int:
        return max(0, self.planned - len(self.errors))


@dataclass
class UndoPlan:
    """An undo that has been read from a journal but not applied yet."""

    journal: Path
    created: str | None
    source: Path
    destination: Path
    entries: list[Move] = field(default_factory=list)
    missing: list[Path] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.entries


@dataclass
class UndoResult:
    """The outcome of an undo run."""

    restored: list[Move] = field(default_factory=list)
    errors: list[MoveError] = field(default_factory=list)
    removed: list[Path] = field(default_factory=list)
    missing: list[Path] = field(default_factory=list)

    @property
    def restored_count(self) -> int:
        return len(self.restored)
