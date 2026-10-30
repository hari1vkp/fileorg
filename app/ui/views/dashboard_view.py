"""The organise screen: folder inputs, options and a live preview table."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable

from app.core.constants import CATEGORY_FOLDERS, UNKNOWN_FOLDER
from app.models.forms import OrganiseForm
from app.models.organise import OrganisePlan
from app.ui.components.base import ThemedFrame, ThemedLabel
from app.ui.components.buttons import ghost_button, primary_button, secondary_button
from app.ui.components.cards import Card, InfoBanner, SectionLabel
from app.ui.components.inputs import LabeledEntry, OptionCheck, PathInput
from app.ui.themes.theme_manager import Theme, ThemeManager
from app.utils.helpers import plural, pretty_path


@dataclass
class DashboardCallbacks:
    on_preview: Callable[[], None]
    on_organise: Callable[[], None]
    on_undo: Callable[[], None]
    on_form_changed: Callable[[], None]


class DashboardView(ThemedFrame):
    """Folder selection, scan options and the planned move table."""

    def __init__(
        self,
        parent: tk.Misc,
        theme_manager: ThemeManager,
        callbacks: DashboardCallbacks,
        form: OrganiseForm,
        undo_available: bool = False,
    ) -> None:
        super().__init__(parent, theme_manager, role="background")
        self._theme_manager = theme_manager
        self._callbacks = callbacks
        self._busy = False
        self._has_plan = False
        self._empty_plan = True
        self._undo_available = undo_available
        self._suspend = False

        self.source_var = tk.StringVar(value=form.source)
        self.dest_var = tk.StringVar(value=form.destination)
        self.ignore_var = tk.StringVar(value=form.ignore)
        self.recursive_var = tk.BooleanVar(value=form.recursive)
        self.unknown_var = tk.BooleanVar(value=form.move_unknown)
        self.hidden_var = tk.BooleanVar(value=form.include_hidden)

        for variable in (
            self.source_var,
            self.dest_var,
            self.ignore_var,
            self.recursive_var,
            self.unknown_var,
            self.hidden_var,
        ):
            variable.trace_add("write", self._changed)

        self._build(fonts=theme_manager.theme.fonts)
        self.apply_theme(theme_manager.theme)
        self.set_undo_available(undo_available)

    # ----------------------------------------------------------------- build

    def _build(self, fonts) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1, minsize=380)
        self.grid_rowconfigure(0, weight=1)

        settings_card = Card(self, self._theme_manager, padding=18, width=300)
        settings_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self._build_settings(settings_card.body, fonts)

        preview_card = Card(self, self._theme_manager, padding=18)
        preview_card.grid(row=0, column=1, sticky="nsew")
        self._build_preview(preview_card.body, fonts)

    def _build_settings(self, parent: tk.Misc, fonts) -> None:
        SectionLabel(parent, self._theme_manager, "Folder").pack(fill="x")

        self.source_input = PathInput(
            parent,
            self._theme_manager,
            "Source",
            self.source_var,
            self.choose_source,
            pad_top=6,
        )
        self.source_input.pack(fill="x")

        self.dest_input = PathInput(
            parent,
            self._theme_manager,
            "Destination (optional)",
            self.dest_var,
            self.choose_destination,
            hint="Leave empty to sort in place.",
            pad_top=12,
        )
        self.dest_input.pack(fill="x")

        ThemedFrame(parent, self._theme_manager, role="border", height=1).pack(
            fill="x", pady=10
        )

        SectionLabel(parent, self._theme_manager, "Options").pack(fill="x")
        self.recursive_check = OptionCheck(
            parent, self._theme_manager, "Include subfolders", self.recursive_var
        )
        self.recursive_check.pack(anchor="w", pady=(6, 0))
        self.unknown_check = OptionCheck(
            parent, self._theme_manager, "Move unknown files to Other/", self.unknown_var
        )
        self.unknown_check.pack(anchor="w", pady=(4, 0))
        self.hidden_check = OptionCheck(
            parent, self._theme_manager, "Include hidden files", self.hidden_var
        )
        self.hidden_check.pack(anchor="w", pady=(4, 0))

        self.ignore_input = LabeledEntry(
            parent,
            self._theme_manager,
            "Ignore patterns",
            self.ignore_var,
            hint="Comma-separated globs, e.g. *.pdf, *.tmp",
            pad_top=10,
        )
        self.ignore_input.pack(fill="x")

        self._banner = InfoBanner(
            parent,
            self._theme_manager,
            "Safe by default",
            "Preview never moves. Organise asks first. Undo any run.",
            wrap=236,
        )
        self._banner.pack(side="bottom", fill="x", pady=(10, 0))

    def _build_preview(self, parent: tk.Misc, fonts) -> None:
        head = ThemedFrame(parent, self._theme_manager, role="surface")
        head.pack(fill="x")
        ThemedLabel(
            head,
            self._theme_manager,
            "Preview",
            role="title",
            bg_role="surface",
        ).pack(side="left")
        self.summary = ThemedLabel(
            head,
            self._theme_manager,
            "No preview yet.",
            role="muted",
            bg_role="surface",
            anchor="e",
        )
        self.summary.pack(side="left", fill="x", expand=True)

        self.detail = ThemedLabel(
            parent,
            self._theme_manager,
            "",
            role="muted",
            bg_role="surface",
            anchor="w",
            justify="left",
        )
        self.detail.pack(fill="x", pady=(2, 10))

        self.table_holder = ThemedFrame(parent, self._theme_manager, role="surface")
        self.table_holder.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            self.table_holder,
            columns=("file", "dest"),
            show="headings",
            selectmode="none",
        )
        self.tree.heading("file", text="FILE", anchor="w")
        self.tree.heading("dest", text="DESTINATION", anchor="w")
        self.tree.column("file", width=170, minwidth=110, stretch=True, anchor="w")
        self.tree.column("dest", width=160, minwidth=110, stretch=True, anchor="w")
        scroll = ttk.Scrollbar(
            self.table_holder, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.empty = ThemedFrame(self.table_holder, self._theme_manager, role="surface")
        self._empty_title = ThemedLabel(
            self.empty,
            self._theme_manager,
            "Nothing to preview yet",
            role="title",
            bg_role="surface",
            anchor="center",
        )
        self._empty_title.pack(pady=(0, 4))
        self._empty_text = ThemedLabel(
            self.empty,
            self._theme_manager,
            "Choose a folder and press Preview.",
            role="muted",
            bg_role="surface",
            anchor="center",
        )
        self._empty_text.pack()
        self.empty.place(relx=0.5, rely=0.42, anchor="center")

        footer = ThemedFrame(parent, self._theme_manager, role="surface")
        footer.pack(fill="x", pady=(14, 0))

        self.undo_btn = ghost_button(footer, "Undo", self._callbacks.on_undo)
        self.undo_btn.pack(side="right", padx=(6, 0))
        self.organise_btn = primary_button(footer, "Organise", self._callbacks.on_organise)
        self.organise_btn.pack(side="right", padx=(6, 0))
        self.preview_btn = secondary_button(footer, "Preview", self._callbacks.on_preview)
        self.preview_btn.pack(side="right")

    # -------------------------------------------------------------- public

    def form_state(self) -> OrganiseForm:
        return OrganiseForm(
            source=self.source_var.get(),
            destination=self.dest_var.get(),
            ignore=self.ignore_var.get(),
            recursive=self.recursive_var.get(),
            move_unknown=self.unknown_var.get(),
            include_hidden=self.hidden_var.get(),
        )

    def set_form(self, form: OrganiseForm) -> None:
        self._suspend = True
        try:
            self.source_var.set(form.source)
            self.dest_var.set(form.destination)
            self.ignore_var.set(form.ignore)
            self.recursive_var.set(form.recursive)
            self.unknown_var.set(form.move_unknown)
            self.hidden_var.set(form.include_hidden)
        finally:
            self._suspend = False

    def reset_preview(self, message: str = "Preview to see what will move.") -> None:
        self._has_plan = False
        self._empty_plan = True
        self.tree.delete(*self.tree.get_children())
        self.summary.set_text(message)
        self.detail.set_text("")
        self._empty_title.set_text("Nothing to preview yet")
        self._empty_text.set_text("Choose a folder and press Preview.")
        self.empty.place(relx=0.5, rely=0.42, anchor="center")
        self.organise_btn.configure(text="Organise")
        self._sync_buttons()

    def show_plan(self, plan: OrganisePlan) -> None:
        self._has_plan = True
        self._empty_plan = plan.is_empty
        self.tree.delete(*self.tree.get_children())
        for index, move in enumerate(plan.moves):
            row_tag = "even" if index % 2 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(move.relative_source(plan.source), move.destination_label()),
                tags=(row_tag, f"cat-{move.folder}"),
            )

        if plan.is_empty:
            self.empty.place(relx=0.5, rely=0.42, anchor="center")
            self.summary.set_text("Nothing to move.")
            self.detail.set_text("This folder is already tidy for the selected options.")
            self.organise_btn.configure(text="Organise")
            self._sync_buttons()
            return

        self.empty.place_forget()
        self.summary.set_text(
            f"{plural(len(plan.moves), 'file')}  \u00b7  {plural(plan.folder_count, 'folder')}"
        )
        details = []
        if plan.unknown:
            details.append(f"{plural(len(plan.unknown), 'unknown file')} will stay in place")
        if plan.warnings:
            details.append(plural(len(plan.warnings), "warning"))
        if not plan.is_in_place:
            details.append(f"destination: {pretty_path(plan.destination)}")
        self.detail.set_text("  \u00b7  ".join(details) if details else "Ready to organise.")
        self.organise_btn.configure(text="Organise")
        self._sync_buttons()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        enabled = not busy
        for widget in (
            self.source_input,
            self.dest_input,
            self.ignore_input,
        ):
            widget.set_enabled(enabled)
        for widget in (self.recursive_check, self.unknown_check, self.hidden_check):
            widget.set_enabled(enabled)
        self.winfo_toplevel().configure(cursor="watch" if busy else "")
        self._sync_buttons()

    def set_undo_available(self, available: bool) -> None:
        self._undo_available = available
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        preview_ok = not self._busy
        organise_ok = preview_ok and self._has_plan and not self._empty_plan
        undo_ok = preview_ok and self._undo_available
        _state(self.preview_btn, preview_ok)
        _state(self.organise_btn, organise_ok)
        _state(self.undo_btn, undo_ok)

    # ------------------------------------------------------------- actions

    def choose_source(self) -> None:
        initial = _expand(self.source_var.get()) or Path.home()
        chosen = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=str(initial),
            title="Choose a folder",
        )
        if chosen:
            self.source_var.set(chosen)

    def choose_destination(self) -> None:
        initial = _expand(self.dest_var.get()) or _expand(self.source_var.get()) or Path.home()
        chosen = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=str(initial),
            title="Choose a destination",
        )
        if chosen:
            self.dest_var.set(chosen)

    def _changed(self, *_args: object) -> None:
        if self._suspend:
            return
        self._callbacks.on_form_changed()

    # --------------------------------------------------------------- theme

    def apply_theme(self, theme: Theme) -> None:
        super().apply_theme(theme)
        palette = theme.palette
        self.tree.tag_configure("odd", background=palette.surface)
        self.tree.tag_configure("even", background=palette.stripe)
        for folder in (*CATEGORY_FOLDERS, UNKNOWN_FOLDER):
            colour = palette.categories.get(folder)
            if colour:
                self.tree.tag_configure(f"cat-{folder}", foreground=colour)


def _state(button: ttk.Button, enabled: bool) -> None:
    button.state(["!disabled"] if enabled else ["disabled"])


def _expand(value: str) -> Path | None:
    text = value.strip()
    return Path(text).expanduser() if text else None
