"""ttk style builder driven entirely by the active theme."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tkinter import ttk

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.ui.themes.theme_manager import Theme


class StyleBuilder:
    """Configure ttk widgets from a :class:`Theme`."""

    def __init__(self, style: ttk.Style, theme: "Theme") -> None:
        self.style = style
        self.theme = theme
        self.p = theme.palette
        self.f = theme.fonts

    def build(self) -> None:
        self.style.theme_use("clam")
        self._base()
        self._buttons()
        self._inputs()
        self._checks()
        self._tree()
        self._scrollbar()
        self._labels()

    def _base(self) -> None:
        p, f = self.p, self.f
        self.style.configure(
            ".",
            background=p.background,
            foreground=p.text,
            font=f.body(),
            borderwidth=0,
            focusthickness=0,
        )
        self.style.configure("TFrame", background=p.background)
        self.style.configure("Surface.TFrame", background=p.surface)
        self.style.configure("Sidebar.TFrame", background=p.sidebar)
        self.style.configure("TSeparator", background=p.border)
        self.style.configure("TLabel", background=p.surface, foreground=p.text)

    def _buttons(self) -> None:
        p, f = self.p, self.f
        self.style.configure(
            "TButton",
            font=f.body_bold(),
            padding=(13, 8),
            borderwidth=0,
            focusthickness=0,
            relief="flat",
        )
        self.style.configure(
            "Primary.TButton",
            background=p.accent,
            foreground=p.on_accent,
            borderwidth=0,
            padding=(16, 9),
            font=f.body_bold(),
        )
        self.style.map(
            "Primary.TButton",
            background=[
                ("disabled", p.disabled_bg),
                ("pressed", p.accent_hover),
                ("active", p.accent_hover),
            ],
            foreground=[("disabled", p.disabled_text)],
        )
        self.style.configure(
            "Secondary.TButton",
            background=p.surface,
            foreground=p.text,
            bordercolor=p.border,
            lightcolor=p.border,
            darkcolor=p.border,
            borderwidth=1,
            padding=(12, 8),
            font=f.body(),
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", p.surface_alt), ("pressed", p.surface_alt)],
            bordercolor=[("active", p.border_strong)],
            foreground=[("disabled", p.faint)],
        )
        self.style.configure(
            "Ghost.TButton",
            background=p.surface,
            foreground=p.muted,
            borderwidth=0,
            padding=(11, 8),
            font=f.body(),
        )
        self.style.map(
            "Ghost.TButton",
            background=[("active", p.surface_alt), ("pressed", p.surface_alt)],
            foreground=[("disabled", p.faint), ("active", p.text)],
        )
        self.style.configure(
            "Sidebar.TButton",
            background=p.sidebar,
            foreground=p.muted,
            borderwidth=0,
            anchor="w",
            padding=(14, 9),
            font=f.body(),
        )
        self.style.map(
            "Sidebar.TButton",
            background=[("active", p.surface_alt), ("pressed", p.surface_alt)],
            foreground=[("active", p.text)],
        )
        self.style.configure(
            "SidebarActive.TButton",
            background=p.nav_active_bg,
            foreground=p.nav_active_fg,
            borderwidth=0,
            anchor="w",
            padding=(14, 9),
            font=f.body_bold(),
        )
        self.style.map(
            "SidebarActive.TButton",
            background=[("active", p.nav_active_bg), ("pressed", p.nav_active_bg)],
            foreground=[("active", p.nav_active_fg)],
        )

    def _inputs(self) -> None:
        p, f = self.p, self.f
        self.style.configure(
            "TEntry",
            fieldbackground=p.surface,
            foreground=p.text,
            bordercolor=p.border,
            lightcolor=p.border,
            darkcolor=p.border,
            insertcolor=p.text,
            padding=7,
            font=f.body(),
        )
        self.style.map(
            "TEntry",
            bordercolor=[("focus", p.accent)],
            lightcolor=[("focus", p.accent)],
            darkcolor=[("focus", p.accent)],
            fieldbackground=[("disabled", p.surface_alt)],
            foreground=[("disabled", p.faint)],
        )

    def _checks(self) -> None:
        p, f = self.p, self.f
        for name in ("Card.TCheckbutton", "Card.TRadiobutton"):
            self.style.configure(
                name,
                background=p.surface,
                foreground=p.text,
                font=f.body(),
                focusthickness=0,
                padding=(0, 2),
            )
            self.style.map(
                name,
                background=[("active", p.surface)],
                foreground=[("disabled", p.faint)],
            )

    def _tree(self) -> None:
        p, f = self.p, self.f
        self.style.configure(
            "Treeview",
            background=p.surface,
            fieldbackground=p.surface,
            foreground=p.text,
            rowheight=29,
            borderwidth=0,
            font=f.small(),
        )
        self.style.configure(
            "Treeview.Heading",
            background=p.surface,
            foreground=p.muted,
            font=f.tiny_bold(),
            relief="flat",
            padding=(9, 8),
        )
        self.style.map(
            "Treeview",
            background=[("selected", p.selection)],
            foreground=[("selected", p.text)],
        )
        self.style.map("Treeview.Heading", background=[("active", p.surface)])

    def _scrollbar(self) -> None:
        p = self.p
        self.style.configure(
            "Vertical.TScrollbar",
            background=p.scrollbar,
            troughcolor=p.surface,
            bordercolor=p.surface,
            lightcolor=p.scrollbar,
            darkcolor=p.scrollbar,
            borderwidth=0,
            arrowsize=12,
            width=11,
        )
        self.style.map(
            "Vertical.TScrollbar",
            background=[("active", p.border_strong)],
        )

    def _labels(self) -> None:
        p, f = self.p, self.f
        self.style.configure(
            "Link.TLabel",
            background=p.surface,
            foreground=p.accent,
            font=f.small(),
        )
        self.style.configure(
            "SidebarLink.TLabel",
            background=p.sidebar,
            foreground=p.accent,
            font=f.small(),
        )
