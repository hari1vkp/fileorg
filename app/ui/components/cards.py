"""Card and banner components."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from app.ui.components.base import ThemedFrame, ThemedLabel
from app.ui.themes.theme_manager import Theme, ThemeManager


class Card(tk.Canvas):
    """A rounded surface with a padded content frame at ``.body``."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        *,
        padding: int | None = None,
        radius: int | None = None,
        role: str = "surface",
        bg_role: str = "background",
        **kwargs: Any,
    ) -> None:
        theme = theme_manager.theme
        self._theme_manager = theme_manager
        self._padding = padding if padding is not None else theme.spacing.lg
        self._radius = radius if radius is not None else theme.radii.md
        self._role = role
        self._bg_role = bg_role
        super().__init__(
            master,
            bg=self._colour(theme, bg_role),
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.body = tk.Frame(self, bg=self._colour(theme, role), bd=0)
        self._window = self.create_window(
            self._padding,
            self._padding,
            anchor="nw",
            window=self.body,
        )
        self.bind("<Configure>", self._on_configure)
        theme_manager.register(self)

    def _colour(self, theme: Theme, role: str) -> str:
        return getattr(theme.palette, role)

    def _on_configure(self, event: tk.Event) -> None:
        width = max(1, event.width)
        height = max(1, event.height)
        self.itemconfigure(
            self._window,
            width=max(1, width - 2 * self._padding),
            height=max(1, height - 2 * self._padding),
        )
        self._redraw(width, height)

    def _redraw(self, width: int, height: int) -> None:
        self.delete("card")
        if width < 2 or height < 2:
            return
        radius = min(self._radius, width // 2, height // 2)
        theme = self._theme_manager.theme
        self._rounded(
            0,
            0,
            width - 1,
            height - 1,
            radius,
            fill=self._colour(theme, self._role),
            outline=theme.palette.border,
        )
        self.tag_lower("card")

    def _rounded(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        *,
        fill: str,
        outline: str,
    ) -> None:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        self.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            tags="card",
        )

    def apply_theme(self, theme: Theme) -> None:
        self.configure(bg=self._colour(theme, self._bg_role))
        self.body.configure(bg=self._colour(theme, self._role))
        self._redraw(self.winfo_width(), self.winfo_height())


class SectionLabel(ThemedLabel):
    """A small uppercase-style section heading."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        text: str,
        *,
        bg_role: str = "surface",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            theme_manager,
            text.upper(),
            role="section",
            bg_role=bg_role,
            anchor="w",
            **kwargs,
        )


class InfoBanner(ThemedFrame):
    """A soft callout with a title and body text."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        title: str,
        text: str,
        *,
        role: str = "tip_bg",
        border_role: str = "tip_border",
        wrap: int = 260,
    ) -> None:
        self._border_role = border_role
        super().__init__(
            master,
            theme_manager,
            role=role,
            highlightthickness=1,
            highlightbackground=getattr(theme_manager.theme.palette, border_role),
        )
        self._title = ThemedLabel(
            self,
            theme_manager,
            title,
            role="tip_title",
            bg_role=role,
        )
        self._title.pack(anchor="w", padx=11, pady=(7, 0))
        self._text = ThemedLabel(
            self,
            theme_manager,
            text,
            role="tip_body",
            bg_role=role,
            wraplength=wrap,
            justify="left",
            anchor="w",
        )
        self._text.pack(anchor="w", padx=11, pady=(2, 7))

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)
        self.configure(highlightbackground=getattr(theme.palette, self._border_role))
