"""Sidebar navigation components."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class NavButton(ttk.Button):
    """A sidebar destination that can show the active state."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            text=text,
            command=command,
            style="Sidebar.TButton",
            takefocus=True,
        )
        self._active = False

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        self.configure(style="SidebarActive.TButton" if active else "Sidebar.TButton")
