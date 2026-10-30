"""Reusable, theme-aware primitives used by every screen."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from app.ui.themes.theme_manager import Theme, ThemeManager

_TEXT_ROLES: dict[str, tuple[str, str]] = {
    "display": ("text", "display"),
    "brand": ("text", "brand"),
    "title": ("text", "title"),
    "subtitle": ("muted", "subtitle"),
    "body": ("text", "body"),
    "label": ("text", "small_bold"),
    "muted": ("muted", "small"),
    "mono": ("muted", "mono_small"),
    "faint": ("faint", "tiny"),
    "section": ("faint", "tiny_bold"),
    "accent": ("accent", "small"),
    "success": ("success", "small"),
    "warning": ("warning", "small"),
    "danger": ("danger", "small"),
    "tip_title": ("tip_text", "small_bold"),
    "tip_body": ("tip_text", "small"),
}


class ThemedFrame(tk.Frame):
    """A frame whose background is a palette role."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        *,
        role: str = "background",
        **kwargs: Any,
    ) -> None:
        self._theme_manager = theme_manager
        self._role = role
        kwargs.setdefault("bg", self._colour(theme_manager.theme))
        super().__init__(master, **kwargs)
        theme_manager.register(self)

    def _colour(self, theme: Theme) -> str:
        return getattr(theme.palette, self._role)

    def apply_theme(self, theme: Theme) -> None:
        self.configure(bg=self._colour(theme))


class ThemedLabel(tk.Label):
    """A label with a typographic role and a background role."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        text: str = "",
        *,
        role: str = "body",
        bg_role: str = "surface",
        tone: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._theme_manager = theme_manager
        self._role = role
        self._bg_role = bg_role
        self._tone = tone
        theme = theme_manager.theme
        kwargs.setdefault("bg", getattr(theme.palette, bg_role))
        kwargs.setdefault("fg", self._foreground(theme))
        kwargs.setdefault("font", self._font(theme))
        kwargs.setdefault("anchor", "w")
        super().__init__(master, text=text, **kwargs)
        theme_manager.register(self)

    def _font(self, theme: Theme) -> tuple[str, int, str]:
        method = getattr(theme.fonts, _TEXT_ROLES[self._role][1])
        return method()

    def _foreground(self, theme: Theme) -> str:
        target = self._tone or _TEXT_ROLES[self._role][0]
        return getattr(theme.palette, target)

    def set_text(self, text: str) -> None:
        self.configure(text=text)

    def set_tone(self, tone: str | None) -> None:
        """Change only the colour, keeping the role's font."""
        self._tone = tone
        self.configure(fg=self._foreground(self._theme_manager.theme))

    def apply_theme(self, theme: Theme) -> None:
        self.configure(
            bg=getattr(theme.palette, self._bg_role),
            fg=self._foreground(theme),
            font=self._font(theme),
        )


class Divider(ThemedFrame):
    """A one pixel horizontal rule."""

    def __init__(self, master: tk.Misc, theme_manager: ThemeManager) -> None:
        super().__init__(master, theme_manager, role="border", height=1)
        self.pack_propagate(False)
