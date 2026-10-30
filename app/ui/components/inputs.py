"""Themed labelled inputs and option rows."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from app.ui.components.base import ThemedFrame, ThemedLabel
from app.ui.components.buttons import secondary_button
from app.ui.themes.theme_manager import ThemeManager


class LabeledEntry(ThemedFrame):
    """A bold label, an entry row, and an optional hint."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        label: str,
        variable: tk.StringVar,
        *,
        hint: str | None = None,
        pad_top: int = 0,
    ) -> None:
        super().__init__(master, theme_manager, role="surface")
        self.variable = variable
        self._label = ThemedLabel(
            self,
            theme_manager,
            label,
            role="label",
            bg_role="surface",
            anchor="w",
        )
        self._label.pack(fill="x", pady=(pad_top, 4))

        self.row = ThemedFrame(self, theme_manager, role="surface")
        self.row.pack(fill="x")
        self.row.grid_columnconfigure(0, weight=1)
        self.entry = ttk.Entry(self.row, textvariable=variable, width=10)
        self.entry.grid(row=0, column=0, sticky="ew")

        self._hint: ThemedLabel | None = None
        if hint:
            self._hint = ThemedLabel(
                self,
                theme_manager,
                hint,
                role="faint",
                bg_role="surface",
                anchor="w",
            )
            self._hint.pack(fill="x", pady=(3, 0))

    def set_enabled(self, enabled: bool) -> None:
        self.entry.state(["!disabled"] if enabled else ["disabled"])


class PathInput(LabeledEntry):
    """A path entry with an adjacent browse button."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        label: str,
        variable: tk.StringVar,
        browse_command: Callable[[], None],
        *,
        hint: str | None = None,
        pad_top: int = 0,
    ) -> None:
        super().__init__(
            master,
            theme_manager,
            label,
            variable,
            hint=hint,
            pad_top=pad_top,
        )
        self.button = secondary_button(
            self.row,
            "Browse",
            browse_command,
            padding=(8, 5),
            width=7,
        )
        self.button.grid(row=0, column=1, sticky="e", padx=(6, 0))

    def set_enabled(self, enabled: bool) -> None:
        super().set_enabled(enabled)
        self.button.state(["!disabled"] if enabled else ["disabled"])


class OptionCheck(ttk.Checkbutton):
    """A checkbox using the card surface style."""

    def __init__(
        self,
        master: tk.Misc,
        theme_manager: ThemeManager,
        text: str,
        variable: tk.BooleanVar,
    ) -> None:
        super().__init__(
            master,
            text=text,
            variable=variable,
            style="Card.TCheckbutton",
            takefocus=True,
        )

    def set_enabled(self, enabled: bool) -> None:
        self.state(["!disabled"] if enabled else ["disabled"])
