"""User settings persisted between launches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.constants import THEME_DARK, THEME_LIGHT, THEMES

DEFAULT_SOURCE = ""
DEFAULT_IGNORE = ""


@dataclass
class AppSettings:
    """Everything the app remembers about the user's preferences."""

    theme: str = THEME_LIGHT
    source: str = DEFAULT_SOURCE
    destination: str = ""
    recursive: bool = False
    move_unknown: bool = False
    include_hidden: bool = False
    ignore: str = DEFAULT_IGNORE

    def normalised(self) -> "AppSettings":
        """Return a copy with invalid values replaced by defaults."""
        return AppSettings(
            theme=self.theme if self.theme in THEMES else THEME_LIGHT,
            source=str(self.source or ""),
            destination=str(self.destination or ""),
            recursive=bool(self.recursive),
            move_unknown=bool(self.move_unknown),
            include_hidden=bool(self.include_hidden),
            ignore=str(self.ignore or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "source": self.source,
            "destination": self.destination,
            "recursive": self.recursive,
            "move_unknown": self.move_unknown,
            "include_hidden": self.include_hidden,
            "ignore": self.ignore,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AppSettings":
        """Build settings from untrusted JSON, falling back per field."""
        defaults = cls()
        theme = data.get("theme")
        return cls(
            theme=theme if theme in THEMES else defaults.theme,
            source=_text(data.get("source"), defaults.source),
            destination=_text(data.get("destination"), defaults.destination),
            recursive=_flag(data.get("recursive"), defaults.recursive),
            move_unknown=_flag(data.get("move_unknown"), defaults.move_unknown),
            include_hidden=_flag(data.get("include_hidden"), defaults.include_hidden),
            ignore=_text(data.get("ignore"), defaults.ignore),
        )


def _text(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) else fallback


def _flag(value: Any, fallback: bool) -> bool:
    return value if isinstance(value, bool) else fallback


__all__ = ["AppSettings", "DEFAULT_SOURCE", "DEFAULT_IGNORE", "THEME_DARK", "THEME_LIGHT"]
