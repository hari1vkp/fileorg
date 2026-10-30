"""The left navigation rail."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from app.config import resource_path
from app.core.constants import APP_VERSION
from app.ui.components.base import ThemedFrame, ThemedLabel
from app.ui.components.buttons import sidebar_button
from app.ui.components.navigation import NavButton
from app.ui.themes.theme_manager import Theme, ThemeManager


class Sidebar(ThemedFrame):
    """Brand, primary navigation and the theme switch."""

    def __init__(
        self,
        parent: tk.Misc,
        theme_manager: ThemeManager,
        *,
        on_navigate: Callable[[str], None],
        on_toggle_theme: Callable[[], None],
        on_open_journals: Callable[[], None],
    ) -> None:
        super().__init__(parent, theme_manager, role="sidebar", width=218)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._on_toggle_theme = on_toggle_theme

        self._icon: tk.PhotoImage | None = self._load_icon(theme_manager)
        self._build()
        self.set_theme_name(theme_manager.theme.name)

        self.dashboard_button.set_active(True)

    def _load_icon(self, theme_manager: ThemeManager) -> tk.PhotoImage | None:
        try:
            icon = tk.PhotoImage(file=str(resource_path("assets", "icons", "icon.png")))
        except tk.TclError:
            return None
        factor = max(1, icon.width() // 34)
        self._icon_small = icon.subsample(factor, factor)
        return icon

    def _build(self) -> None:
        brand = ThemedFrame(self, self._theme_manager, role="sidebar")
        brand.pack(fill="x", padx=18, pady=(20, 24))
        if getattr(self, "_icon_small", None) is not None:
            tk.Label(
                brand,
                image=self._icon_small,
                bg=self._theme_manager.palette.sidebar,
                bd=0,
            ).pack(side="left", padx=(0, 10))
        text = ThemedFrame(brand, self._theme_manager, role="sidebar")
        text.pack(side="left", fill="y")
        ThemedLabel(text, self._theme_manager, "fileorg", role="brand", bg_role="sidebar").pack(
            anchor="w"
        )
        ThemedLabel(
            text,
            self._theme_manager,
            f"v{APP_VERSION}",
            role="faint",
            bg_role="sidebar",
        ).pack(anchor="w")

        self.dashboard_button = NavButton(
            self, "Organise", lambda: self._on_navigate("dashboard")
        )
        self.dashboard_button.pack(fill="x", padx=12, pady=(0, 2))
        self.settings_button = NavButton(
            self, "Settings", lambda: self._on_navigate("settings")
        )
        self.settings_button.pack(fill="x", padx=12)

        spacer = ThemedFrame(self, self._theme_manager, role="sidebar")
        spacer.pack(fill="both", expand=True)

        self.theme_button = sidebar_button(self, "Dark mode", self._on_toggle_theme)
        self.theme_button.pack(fill="x", padx=12, pady=(0, 6))

        journals = ThemedFrame(self, self._theme_manager, role="sidebar")
        journals.pack(fill="x", padx=12, pady=(0, 18))
        link = ThemedLabel(
            journals,
            self._theme_manager,
            "Journals  \u2197",
            role="accent",
            bg_role="sidebar",
            cursor="hand2",
        )
        link.pack(anchor="w", padx=2)
        link.bind("<Button-1>", lambda _event: self._on_navigate("settings"))

        border = ThemedFrame(self, self._theme_manager, role="border", width=1)
        border.place(relx=1.0, rely=0, relheight=1.0, x=-1)

    def set_active(self, page: str) -> None:
        self.dashboard_button.set_active(page == "dashboard")
        self.settings_button.set_active(page == "settings")

    def set_theme_name(self, name: str) -> None:
        self.theme_button.configure(text="Light mode" if name == "dark" else "Dark mode")

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)
        self.set_theme_name(theme.name)
