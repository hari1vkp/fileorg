"""Button factories with consistent styles and accessible defaults."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable


def _button(
    parent: tk.Misc,
    text: str,
    command: Callable[[], None],
    style: str,
    **kwargs: Any,
) -> ttk.Button:
    return ttk.Button(
        parent,
        text=text,
        command=command,
        style=style,
        takefocus=True,
        **kwargs,
    )


def primary_button(
    parent: tk.Misc, text: str, command: Callable[[], None], **kwargs: Any
) -> ttk.Button:
    return _button(parent, text, command, "Primary.TButton", **kwargs)


def secondary_button(
    parent: tk.Misc, text: str, command: Callable[[], None], **kwargs: Any
) -> ttk.Button:
    return _button(parent, text, command, "Secondary.TButton", **kwargs)


def ghost_button(
    parent: tk.Misc, text: str, command: Callable[[], None], **kwargs: Any
) -> ttk.Button:
    return _button(parent, text, command, "Ghost.TButton", **kwargs)


def sidebar_button(
    parent: tk.Misc, text: str, command: Callable[[], None], **kwargs: Any
) -> ttk.Button:
    return _button(parent, text, command, "Sidebar.TButton", **kwargs)


def text_link(
    parent: tk.Misc,
    text: str,
    command: Callable[[], None],
    *,
    style: str = "Link.TLabel",
    **kwargs: Any,
) -> ttk.Label:
    """A clickable text link, styled from the active theme."""
    label = ttk.Label(
        parent,
        text=text,
        style=style,
        cursor="hand2",
        takefocus=True,
        **kwargs,
    )
    label.bind("<Button-1>", lambda _event: command())
    label.bind("<Return>", lambda _event: command())
    label.bind("<space>", lambda _event: command())
    return label
