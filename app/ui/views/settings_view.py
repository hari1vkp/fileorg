"""Settings screen: theme, default folder, journals and about information."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable

from app.config import AppPaths
from app.core.constants import APP_NAME, APP_VERSION, THEME_DARK, THEME_LIGHT
from app.models.settings import AppSettings
from app.ui.components.base import ThemedFrame, ThemedLabel
from app.ui.components.buttons import secondary_button, text_link
from app.ui.components.cards import Card, SectionLabel
from app.ui.components.inputs import PathInput
from app.ui.themes.theme_manager import Theme, ThemeManager
from app.utils.helpers import pretty_path

REPOSITORY_URL = "https://github.com/hari1vkp/fileorg"


@dataclass
class SettingsCallbacks:
    on_theme_change: Callable[[str], None]
    on_default_source_change: Callable[[str], None]
    on_reset: Callable[[], None]
    on_open_journals: Callable[[], None]


class SettingsView(ThemedFrame):
    """Appearance, defaults and information, all live-applied."""

    def __init__(
        self,
        parent: tk.Misc,
        theme_manager: ThemeManager,
        callbacks: SettingsCallbacks,
        settings: AppSettings,
        paths: AppPaths,
    ) -> None:
        super().__init__(parent, theme_manager, role="background")
        self._theme_manager = theme_manager
        self._callbacks = callbacks
        self._paths = paths
        self._suspend = True

        self.theme_var = tk.StringVar(value=settings.theme)
        self.source_var = tk.StringVar(value=settings.source)

        self._build()
        self.theme_var.trace_add("write", self._theme_changed)
        self.source_var.trace_add("write", self._source_changed)
        self._suspend = False
        self.apply_theme(theme_manager.theme)

    # ----------------------------------------------------------------- build

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1, uniform="settings")
        self.grid_columnconfigure(1, weight=1, uniform="settings")
        self.grid_rowconfigure(2, weight=1)

        appearance = self._card(row=0, column=0, height=160)
        SectionLabel(appearance.body, self._theme_manager, "Appearance").pack(fill="x")
        ThemedLabel(
            appearance.body,
            self._theme_manager,
            "Choose how fileorg looks. The change applies immediately.",
            role="muted",
            bg_role="surface",
            wraplength=300,
            justify="left",
        ).pack(fill="x", pady=(2, 10))
        self._radio(
            appearance.body, "Light", "Bright surfaces and dark text.", THEME_LIGHT
        ).pack(anchor="w", pady=(0, 4))
        self._radio(
            appearance.body, "Dark", "Dim surfaces for low-light rooms.", THEME_DARK
        ).pack(anchor="w")

        defaults = self._card(row=1, column=0, height=150)
        SectionLabel(defaults.body, self._theme_manager, "Default folder").pack(fill="x")
        self.default_input = PathInput(
            defaults.body,
            self._theme_manager,
            "Source at launch",
            self.source_var,
            self._choose_default_source,
            hint="Leave empty for ~/Downloads.",
            pad_top=6,
        )
        self.default_input.pack(fill="x", pady=(2, 0))

        reset = self._card(row=2, column=0, height=130)
        SectionLabel(reset.body, self._theme_manager, "Reset").pack(fill="x")
        ThemedLabel(
            reset.body,
            self._theme_manager,
            "Restore every option and the light theme.",
            role="muted",
            bg_role="surface",
        ).pack(fill="x", pady=(2, 8))
        secondary_button(reset.body, "Restore defaults", self._callbacks.on_reset).pack(
            anchor="w"
        )

        journals = self._card(row=0, column=1, height=140)
        SectionLabel(journals.body, self._theme_manager, "Journals").pack(fill="x")
        ThemedLabel(
            journals.body,
            self._theme_manager,
            "Each run is recorded here so it can be undone.",
            role="muted",
            bg_role="surface",
            wraplength=300,
            justify="left",
        ).pack(fill="x", pady=(2, 8))
        ThemedLabel(
            journals.body,
            self._theme_manager,
            pretty_path(self._paths.state_dir),
            role="mono",
            bg_role="surface",
            wraplength=300,
            justify="left",
        ).pack(fill="x")
        secondary_button(
            journals.body, "Open folder", self._callbacks.on_open_journals
        ).pack(anchor="w", pady=(10, 0))

        about = self._card(row=1, column=1, height=130)
        SectionLabel(about.body, self._theme_manager, "About").pack(fill="x")
        ThemedLabel(
            about.body,
            self._theme_manager,
            f"{APP_NAME} {APP_VERSION}",
            role="body",
            bg_role="surface",
        ).pack(fill="x", pady=(2, 2))
        ThemedLabel(
            about.body,
            self._theme_manager,
            "MIT licensed. Built with Python and Tkinter.",
            role="muted",
            bg_role="surface",
        ).pack(fill="x")
        text_link(
            about.body,
            "View the source on GitHub",
            lambda: webbrowser.open(REPOSITORY_URL),
        ).pack(anchor="w", pady=(8, 0))

        shortcuts = self._card(row=2, column=1, height=170)
        SectionLabel(shortcuts.body, self._theme_manager, "Shortcuts").pack(fill="x")
        for keys, action in (
            ("Ctrl+O", "Choose a folder"),
            ("Ctrl+R / F5", "Preview"),
            ("Ctrl+Enter", "Organise"),
            ("Ctrl+Z", "Undo the last run"),
            ("Ctrl+D", "Toggle light and dark"),
            ("Ctrl+1 / Ctrl+2", "Switch screens"),
        ):
            row = ThemedFrame(shortcuts.body, self._theme_manager, role="surface")
            row.pack(fill="x", pady=1)
            ThemedLabel(
                row,
                self._theme_manager,
                keys,
                role="mono",
                bg_role="surface",
                width=17,
                anchor="w",
            ).pack(side="left")
            ThemedLabel(
                row,
                self._theme_manager,
                action,
                role="muted",
                bg_role="surface",
                anchor="w",
            ).pack(side="left")

    def _card(self, *, row: int, column: int, height: int = 152) -> Card:
        card = Card(self, self._theme_manager, padding=16, height=height)
        card.grid(
            row=row,
            column=column,
            sticky="new",
            padx=(0, 12) if column == 0 else (0, 0),
            pady=(0, 12),
        )
        return card

    def _radio(self, parent: tk.Misc, text: str, hint: str, value: str) -> ttk.Radiobutton:
        holder = ThemedFrame(parent, self._theme_manager, role="surface")
        row = ttk.Radiobutton(
            holder,
            text=text,
            value=value,
            variable=self.theme_var,
            style="Card.TRadiobutton",
            takefocus=True,
        )
        row.pack(anchor="w")
        ThemedLabel(
            holder,
            self._theme_manager,
            hint,
            role="faint",
            bg_role="surface",
        ).pack(anchor="w", padx=(21, 0))
        return holder

    # -------------------------------------------------------------- public

    def refresh(self, settings: AppSettings) -> None:
        self._suspend = True
        try:
            self.theme_var.set(settings.theme)
            self.source_var.set(settings.source)
        finally:
            self._suspend = False

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)

    # ------------------------------------------------------------- actions

    def _theme_changed(self, *_args: object) -> None:
        if self._suspend:
            return
        self._callbacks.on_theme_change(self.theme_var.get())

    def _source_changed(self, *_args: object) -> None:
        if self._suspend:
            return
        self._callbacks.on_default_source_change(self.source_var.get())

    def _choose_default_source(self) -> None:
        initial = self.source_var.get().strip() or str(Path.home())
        chosen = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=str(Path(initial).expanduser()),
            title="Choose the default folder",
        )
        if chosen:
            self.source_var.set(chosen)


__all__ = ["SettingsCallbacks", "SettingsView"]
