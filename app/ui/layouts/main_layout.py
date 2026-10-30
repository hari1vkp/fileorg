"""The application shell: sidebar, page header, content and status bar."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.ui.components.base import ThemedFrame, ThemedLabel
from app.ui.components.buttons import text_link
from app.ui.layouts.sidebar import Sidebar
from app.ui.themes.theme_manager import Theme, ThemeManager
from app.utils.helpers import pretty_path


class MainLayout(ThemedFrame):
    """Builds the two-column shell and exposes the content slot."""

    def __init__(
        self,
        parent: tk.Misc,
        theme_manager: ThemeManager,
        *,
        state_dir,
        on_navigate: Callable[[str], None],
        on_toggle_theme: Callable[[], None],
        on_open_journals: Callable[[], None],
    ) -> None:
        super().__init__(parent, theme_manager, role="background")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(
            self,
            theme_manager,
            on_navigate=on_navigate,
            on_toggle_theme=on_toggle_theme,
            on_open_journals=on_open_journals,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns")

        main = ThemedFrame(self, theme_manager, role="background")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self.header = ThemedFrame(main, theme_manager, role="background")
        self.header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 14))
        self.title = ThemedLabel(
            self.header, theme_manager, "", role="display", bg_role="background"
        )
        self.title.pack(anchor="w")
        self.subtitle = ThemedLabel(
            self.header, theme_manager, "", role="subtitle", bg_role="background"
        )
        self.subtitle.pack(anchor="w", pady=(2, 0))

        self.content = ThemedFrame(main, theme_manager, role="background")
        self.content.grid(row=1, column=0, sticky="nsew", padx=28)

        status = ThemedFrame(main, theme_manager, role="background")
        status.grid(row=2, column=0, sticky="ew")
        rule = ThemedFrame(status, theme_manager, role="border", height=1)
        rule.pack(fill="x")
        inner = ThemedFrame(status, theme_manager, role="background")
        inner.pack(fill="x", padx=28, pady=8)

        self.status_label = ThemedLabel(
            inner, theme_manager, "Ready", role="muted", bg_role="background"
        )
        self.status_label.pack(side="left")

        text_link(
            inner,
            "Journals  \u2197",
            on_open_journals,
        ).pack(side="right")
        ThemedLabel(
            inner,
            theme_manager,
            f"{pretty_path(state_dir)}   \u00b7   ",
            role="faint",
            bg_role="background",
        ).pack(side="right")

    def set_page(self, title: str, subtitle: str) -> None:
        self.title.set_text(title)
        self.subtitle.set_text(subtitle)

    def set_status(self, text: str, tone: str = "muted") -> None:
        self.status_label.set_text(text)
        self.status_label.set_tone(tone)

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)
