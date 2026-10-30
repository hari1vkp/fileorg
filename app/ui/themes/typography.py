"""Font discovery and a small, consistent type scale."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Iterable


def _first_available(root: tk.Misc, candidates: Iterable[str], fallback: str) -> str:
    try:
        available = set(tkfont.families(root))
    except tk.TclError:
        return fallback
    for family in candidates:
        if family in available:
            return family
    return fallback


@dataclass(frozen=True)
class FontBook:
    """The resolved font family and type scale for the current system."""

    family: str
    mono: str

    @classmethod
    def detect(cls, root: tk.Misc) -> "FontBook":
        family = _first_available(
            root,
            ("Segoe UI Variable", "Segoe UI", "Inter", "DejaVu Sans", "Helvetica"),
            "TkDefaultFont",
        )
        mono = _first_available(
            root,
            ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"),
            "TkFixedFont",
        )
        return cls(family=family, mono=mono)

    def font(self, size: int, weight: str = "normal") -> tuple[str, int, str]:
        return (self.family, size, weight)

    def display(self) -> tuple[str, int, str]:
        return self.font(22, "bold")

    def brand(self) -> tuple[str, int, str]:
        return self.font(17, "bold")

    def title(self) -> tuple[str, int, str]:
        return self.font(14, "bold")

    def subtitle(self) -> tuple[str, int, str]:
        return self.font(10)

    def body(self) -> tuple[str, int, str]:
        return self.font(10)

    def body_bold(self) -> tuple[str, int, str]:
        return self.font(10, "bold")

    def small(self) -> tuple[str, int, str]:
        return self.font(9)

    def small_bold(self) -> tuple[str, int, str]:
        return self.font(9, "bold")

    def tiny(self) -> tuple[str, int, str]:
        return self.font(8)

    def tiny_bold(self) -> tuple[str, int, str]:
        return self.font(8, "bold")

    def mono_small(self) -> tuple[str, int, str]:
        return (self.mono, 9, "normal")

    def heading(self) -> tuple[str, int, str]:
        return self.font(12, "bold")
