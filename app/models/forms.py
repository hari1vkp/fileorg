"""Form state passed between the dashboard view and the controller."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Sequence

from app.models.organise import OrganiseOptions
from app.models.settings import AppSettings


@dataclass
class OrganiseForm:
    """The raw values typed into the dashboard."""

    source: str = ""
    destination: str = ""
    ignore: str = ""
    recursive: bool = False
    move_unknown: bool = False
    include_hidden: bool = False

    @property
    def ignore_patterns(self) -> tuple[str, ...]:
        return tuple(
            part.strip() for part in re.split(r"[,;]", self.ignore) if part.strip()
        )

    def to_options(self) -> OrganiseOptions:
        return OrganiseOptions.from_values(
            recursive=self.recursive,
            ignore=self.ignore_patterns,
            include_hidden=self.include_hidden,
            move_unknown=self.move_unknown,
        )

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "OrganiseForm":
        return cls(
            source=settings.source,
            destination=settings.destination,
            ignore=settings.ignore,
            recursive=settings.recursive,
            move_unknown=settings.move_unknown,
            include_hidden=settings.include_hidden,
        )

    def apply_to(self, settings: AppSettings) -> AppSettings:
        return replace(
            settings,
            source=self.source,
            destination=self.destination,
            ignore=self.ignore,
            recursive=self.recursive,
            move_unknown=self.move_unknown,
            include_hidden=self.include_hidden,
        )

    def with_source(self, source: str) -> "OrganiseForm":
        return replace(self, source=source)


def parse_patterns(values: Sequence[str]) -> tuple[str, ...]:
    """Normalise repeated ``--ignore`` values from the CLI."""
    return tuple(value.strip() for value in values if value.strip())
