"""Theme selection, style application and theme-aware widget registration."""

from __future__ import annotations

import tkinter as tk
import weakref
from dataclasses import dataclass
from tkinter import ttk
from typing import Protocol

from app.core.constants import RADII, SPACE, THEME_DARK, THEMES, Radii, Spacing
from app.core.events import THEME_CHANGED, EventBus
from app.ui.themes.colors import Palette, palette_for
from app.ui.themes.styles import StyleBuilder
from app.ui.themes.typography import FontBook


class ThemeAware(Protocol):
    """A widget that can recolour itself when the theme changes."""

    def apply_theme(self, theme: "Theme") -> None: ...


@dataclass(frozen=True)
class Theme:
    """The complete visual configuration for one theme."""

    name: str
    palette: Palette
    fonts: FontBook
    spacing: Spacing
    radii: Radii


def build_theme(name: str, fonts: FontBook) -> Theme:
    return Theme(
        name=name if name in THEMES else "light",
        palette=palette_for(name),
        fonts=fonts,
        spacing=SPACE,
        radii=RADII,
    )


class ThemeManager:
    """Owns the active theme and repaints registered widgets on change."""

    def __init__(self, root: tk.Misc, name: str, events: EventBus | None = None) -> None:
        self.root = root
        self.events = events or EventBus()
        self._fonts = FontBook.detect(root)
        self._theme = build_theme(name, self._fonts)
        self._style = ttk.Style(root)
        self._widgets: "weakref.WeakSet[ThemeAware]" = weakref.WeakSet()
        self.apply()

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def name(self) -> str:
        return self._theme.name

    @property
    def palette(self) -> Palette:
        return self._theme.palette

    def register(self, widget: ThemeAware) -> None:
        """Track a widget so it is repainted when the theme changes."""
        self._widgets.add(widget)

    def set_theme(self, name: str) -> None:
        """Switch to ``name`` and repaint everything."""
        if name not in THEMES or name == self._theme.name:
            return
        self._theme = build_theme(name, self._fonts)
        self.apply()

    def toggle(self) -> None:
        self.set_theme(THEME_DARK if self.name != THEME_DARK else "light")

    def apply(self) -> None:
        """Rebuild ttk styles and tell every themed widget to recolour."""
        StyleBuilder(self._style, self._theme).build()
        for widget in list(self._widgets):
            try:
                widget.apply_theme(self._theme)
            except tk.TclError:
                self._widgets.discard(widget)
        self.events.emit(THEME_CHANGED, self._theme)
