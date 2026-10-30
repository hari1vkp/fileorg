#!/usr/bin/env python3
"""fileorg desktop - a small Tkinter front end for the fileorg organiser."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import fileorg

APP_VERSION = fileorg.__version__

BG = "#f1f5f9"
CARD = "#ffffff"
BORDER = "#e2e8f0"
TEXT = "#0f172a"
MUTED = "#64748b"
FAINT = "#94a3b8"
ACCENT = "#0284c7"
ACCENT_DARK = "#0369a1"
ACCENT_SOFT = "#e0f2fe"
SUCCESS = "#059669"
WARNING = "#d97706"
DANGER = "#dc2626"

CATEGORY_COLORS = {
    "Images": "#0284c7",
    "Videos": "#7c3aed",
    "Audio": "#059669",
    "Documents": "#d97706",
    "Spreadsheets": "#0d9488",
    "Presentations": "#ea580c",
    "Archives": "#dc2626",
    "Installers": "#4f46e5",
    "Code": "#2563eb",
    "Fonts": "#9333ea",
    "Design": "#db2777",
    "3D": "#0891b2",
    fileorg.UNKNOWN_FOLDER: "#64748b",
}


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def pick_font(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for family in ("Segoe UI Variable", "Segoe UI", "Inter", "DejaVu Sans", "Helvetica"):
        if family in available:
            return family
    return "TkDefaultFont"


def pick_mono(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for family in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"):
        if family in available:
            return family
    return "TkFixedFont"


def pretty_path(path: Path) -> str:
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(path)


def open_in_file_manager(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


def dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
    except Exception:
        pass


@dataclass
class Plan:
    source: Path
    dest: Path
    moves: list[fileorg.Move]
    unknown: list[Path]
    warnings: list[str]


class FileorgApp:
    def __init__(self, root: tk.Tk, initial: Path | None = None) -> None:
        self.root = root
        self.state_dir = fileorg.default_state_dir()
        self.plan: Plan | None = None
        self.busy = False

        self.family = pick_font(root)
        self.mono = pick_mono(root)

        self.source_var = tk.StringVar(value=str(initial) if initial else "~/Downloads")
        self.dest_var = tk.StringVar()
        self.ignore_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.unknown_var = tk.BooleanVar(value=False)
        self.hidden_var = tk.BooleanVar(value=False)

        for var in (
            self.source_var,
            self.dest_var,
            self.ignore_var,
            self.recursive_var,
            self.unknown_var,
            self.hidden_var,
        ):
            var.trace_add("write", self._changed)

        self._configure_window()
        self._configure_styles()
        self._build_ui()
        self._refresh_undo_state()
        initial_path = self._path(self.source_var.get())
        if initial_path is not None and initial_path.is_dir():
            self.root.after(200, self.preview)
        else:
            self._set_status("Choose a folder to get started.")

    # ---------------------------------------------------------------- window

    def _configure_window(self) -> None:
        self.root.title("fileorg")
        self.root.configure(bg=BG)
        self.root.minsize(920, 620)
        width, height = 1020, 700
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        try:
            self.icon = tk.PhotoImage(file=str(resource_path("assets", "icon.png")))
            divisor = max(1, self.icon.width() // 42)
            self.icon_small = self.icon.subsample(divisor, divisor)
            self.root.iconphoto(True, self.icon)
        except tk.TclError:
            self.icon = None
            self.icon_small = None

        self.root.bind("<Control-o>", lambda _event: self.choose_source())
        self.root.bind("<Control-r>", lambda _event: self.preview())
        self.root.bind("<F5>", lambda _event: self.preview())
        self.root.bind("<Control-Return>", lambda _event: self.organise())
        self.root.bind("<Control-z>", lambda _event: self.undo_last())

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=(self.family, 10))
        style.configure(
            "TEntry",
            fieldbackground=CARD,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=TEXT,
            padding=6,
        )
        style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])
        style.configure("TButton", font=(self.family, 10), padding=(12, 7))
        style.configure(
            "Secondary.TButton",
            background=CARD,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            borderwidth=1,
            focusthickness=0,
            padding=(11, 7),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#f8fafc"), ("pressed", "#f1f5f9")],
            bordercolor=[("active", "#cbd5e1")],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            padding=(16, 8),
            font=(self.family, 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", "#bae6fd"), ("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
            foreground=[("disabled", "#f0f9ff")],
        )
        style.configure(
            "Ghost.TButton",
            background=CARD,
            foreground=MUTED,
            borderwidth=0,
            focusthickness=0,
            padding=(10, 8),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#f1f5f9"), ("pressed", "#e2e8f0")],
            foreground=[("disabled", "#cbd5e1"), ("active", TEXT)],
        )
        style.configure(
            "Card.TCheckbutton",
            background=CARD,
            foreground=TEXT,
            font=(self.family, 10),
            focusthickness=0,
        )
        style.map("Card.TCheckbutton", background=[("active", CARD)])
        style.configure("TSeparator", background=BORDER)
        style.configure(
            "Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=TEXT,
            rowheight=27,
            borderwidth=0,
            font=(self.family, 9),
        )
        style.configure(
            "Treeview.Heading",
            background=CARD,
            foreground=MUTED,
            font=(self.family, 8, "bold"),
            relief="flat",
            padding=(8, 7),
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT_SOFT)],
            foreground=[("selected", TEXT)],
        )
        style.map("Treeview.Heading", background=[("active", CARD)])
        style.configure("Vertical.TScrollbar", background="#e2e8f0", troughcolor=CARD, borderwidth=0)

    # ------------------------------------------------------------------- ui

    def _build_ui(self) -> None:
        self._build_header()

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(16, 8))
        body.grid_columnconfigure(0, weight=0, minsize=344)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        settings = self._card(body)
        settings.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self._build_settings(settings)

        preview = self._card(body)
        preview.grid(row=0, column=1, sticky="nsew")
        self._build_preview(preview)

        self._build_footer()

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=CARD, height=88)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = tk.Frame(header, bg=CARD)
        inner.pack(fill="both", expand=True, padx=22, pady=15)

        if self.icon_small is not None:
            logo = tk.Label(inner, image=self.icon_small, bg=CARD, bd=0)
            logo.pack(side="left", padx=(0, 12))

        text = tk.Frame(inner, bg=CARD)
        text.pack(side="left", fill="y", pady=1)
        tk.Label(
            text,
            text="fileorg",
            bg=CARD,
            fg=TEXT,
            font=(self.family, 21, "bold"),
        ).pack(anchor="w")
        tk.Label(
            text,
            text="Sort a folder into tidy category folders. Preview first, undo anytime.",
            bg=CARD,
            fg=MUTED,
            font=(self.family, 10),
        ).pack(anchor="w", pady=(1, 0))

        tk.Label(
            inner,
            text=f"v{APP_VERSION}",
            bg=ACCENT_SOFT,
            fg=ACCENT,
            font=(self.family, 9, "bold"),
            padx=9,
            pady=4,
        ).pack(side="right")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    def _build_settings(self, parent: tk.Frame) -> None:
        wrap = tk.Frame(parent, bg=CARD)
        wrap.pack(fill="both", expand=True, padx=18, pady=18)

        self._section_label(wrap, "FOLDER")
        tk.Label(
            wrap, text="Source", bg=CARD, fg=TEXT, font=(self.family, 9, "bold")
        ).pack(anchor="w", pady=(2, 4))
        source_row = tk.Frame(wrap, bg=CARD)
        source_row.pack(fill="x")
        ttk.Entry(source_row, textvariable=self.source_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            source_row, text="Browse", style="Secondary.TButton", command=self.choose_source
        ).pack(side="left", padx=(6, 0))

        tk.Label(
            wrap,
            text="Destination (optional)",
            bg=CARD,
            fg=TEXT,
            font=(self.family, 9, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        dest_row = tk.Frame(wrap, bg=CARD)
        dest_row.pack(fill="x")
        ttk.Entry(dest_row, textvariable=self.dest_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            dest_row,
            text="Browse",
            style="Secondary.TButton",
            command=self.choose_destination,
        ).pack(side="left", padx=(6, 0))
        tk.Label(
            wrap,
            text="Leave empty to sort in place.",
            bg=CARD,
            fg=FAINT,
            font=(self.family, 8),
        ).pack(anchor="w", pady=(3, 0))

        ttk.Separator(wrap).pack(fill="x", pady=16)

        self._section_label(wrap, "OPTIONS")
        ttk.Checkbutton(
            wrap,
            text="Include subfolders",
            variable=self.recursive_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(
            wrap,
            text="Move unknown files to Other/",
            variable=self.unknown_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(
            wrap,
            text="Include hidden files",
            variable=self.hidden_var,
            style="Card.TCheckbutton",
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(
            wrap,
            text="Ignore patterns",
            bg=CARD,
            fg=TEXT,
            font=(self.family, 9, "bold"),
        ).pack(anchor="w", pady=(14, 4))
        ttk.Entry(wrap, textvariable=self.ignore_var).pack(fill="x")
        tk.Label(
            wrap,
            text="Comma-separated globs, e.g. *.pdf, *.tmp",
            bg=CARD,
            fg=FAINT,
            font=(self.family, 8),
        ).pack(anchor="w", pady=(3, 0))

        ttk.Separator(wrap).pack(fill="x", pady=16)

        tip = tk.Frame(wrap, bg="#f0f9ff", highlightbackground="#bae6fd", highlightthickness=1)
        tip.pack(fill="x", side="bottom")
        tk.Label(
            tip,
            text="Safe by default",
            bg="#f0f9ff",
            fg=ACCENT_DARK,
            font=(self.family, 9, "bold"),
        ).pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(
            tip,
            text="Preview never moves anything. Organise asks first, and every run can be undone.",
            bg="#f0f9ff",
            fg="#075985",
            font=(self.family, 9),
            wraplength=260,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 9))

    def _build_preview(self, parent: tk.Frame) -> None:
        head = tk.Frame(parent, bg=CARD)
        head.pack(fill="x", padx=18, pady=(15, 9))
        tk.Label(
            head, text="Preview", bg=CARD, fg=TEXT, font=(self.family, 13, "bold")
        ).pack(side="left")
        self.summary = tk.Label(
            head,
            text="Choose a folder, then preview.",
            bg=CARD,
            fg=MUTED,
            font=(self.family, 9),
        )
        self.summary.pack(side="right")

        self.detail = tk.Label(
            parent,
            text="",
            bg=CARD,
            fg=MUTED,
            font=(self.family, 9),
            anchor="w",
            justify="left",
        )
        self.detail.pack(fill="x", padx=18, pady=(0, 8))

        tree_wrap = tk.Frame(parent, bg=CARD)
        tree_wrap.pack(fill="both", expand=True, padx=18)

        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("file", "dest"),
            show="headings",
            selectmode="none",
        )
        self.tree.heading("file", text="FILE", anchor="w")
        self.tree.heading("dest", text="DESTINATION", anchor="w")
        self.tree.column("file", width=330, minwidth=220, stretch=True, anchor="w")
        self.tree.column("dest", width=250, minwidth=180, stretch=True, anchor="w")

        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.tag_configure("odd", background=CARD)
        self.tree.tag_configure("even", background="#f8fafc")
        for folder, color in CATEGORY_COLORS.items():
            self.tree.tag_configure(f"cat-{folder}", foreground=color)

        footer = tk.Frame(parent, bg=CARD)
        footer.pack(fill="x", padx=18, pady=(12, 15))

        self.undo_btn = ttk.Button(
            footer, text="Undo last run", style="Ghost.TButton", command=self.undo_last
        )
        self.undo_btn.pack(side="right", padx=(6, 0))

        self.organise_btn = ttk.Button(
            footer, text="Organise", style="Accent.TButton", command=self.organise
        )
        self.organise_btn.pack(side="right", padx=(6, 0))

        self.preview_btn = ttk.Button(
            footer, text="Preview", style="Secondary.TButton", command=self.preview
        )
        self.preview_btn.pack(side="right")

    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=22, pady=(0, 10))

        self.status = tk.Label(
            footer,
            text="Ready",
            bg=BG,
            fg=MUTED,
            font=(self.family, 9),
        )
        self.status.pack(side="left")

        journals = tk.Label(
            footer,
            text="Journals  \u2197",
            bg=BG,
            fg=ACCENT,
            font=(self.family, 9),
            cursor="hand2",
        )
        journals.pack(side="right")
        journals.bind("<Button-1>", lambda _event: open_in_file_manager(self.state_dir))
        tk.Label(
            footer,
            text=f"{pretty_path(self.state_dir)}   \u00b7   ",
            bg=BG,
            fg=FAINT,
            font=(self.family, 9),
        ).pack(side="right")

    # -------------------------------------------------------------- helpers

    def _card(self, parent: tk.Misc) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )

    def _section_label(self, parent: tk.Misc, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            bg=CARD,
            fg=FAINT,
            font=(self.family, 8, "bold"),
        ).pack(anchor="w")

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, fg=color)

    def _parse_ignore(self) -> list[str]:
        return [part.strip() for part in re.split(r"[,;]", self.ignore_var.get()) if part.strip()]

    def _path(self, value: str) -> Path | None:
        value = value.strip()
        return Path(value).expanduser() if value else None

    def _changed(self, *_args: object) -> None:
        if self.busy:
            return
        self._reset_preview("Preview to see what will move.")

    def _reset_preview(self, message: str) -> None:
        self.plan = None
        self.tree.delete(*self.tree.get_children())
        self.summary.configure(text=message)
        self.detail.configure(text="")
        self.organise_btn.state(["disabled"])
        self.organise_btn.configure(text="Organise")

    def _refresh_undo_state(self) -> None:
        journal = fileorg.latest_journal(self.state_dir)
        if journal is None:
            self.undo_btn.state(["disabled"])
        else:
            self.undo_btn.state(["!disabled"])

    # -------------------------------------------------------------- actions

    def choose_source(self) -> None:
        initial = self._path(self.source_var.get()) or Path.home()
        chosen = filedialog.askdirectory(parent=self.root, initialdir=str(initial), title="Choose a folder")
        if chosen:
            self.source_var.set(chosen)

    def choose_destination(self) -> None:
        initial = self._path(self.dest_var.get()) or self._path(self.source_var.get()) or Path.home()
        chosen = filedialog.askdirectory(parent=self.root, initialdir=str(initial), title="Choose a destination")
        if chosen:
            self.dest_var.set(chosen)

    def preview(self) -> None:
        if self.busy:
            return
        self.plan = None
        source = self._path(self.source_var.get())
        if source is None or not source.is_dir():
            messagebox.showerror("Folder not found", f"Choose an existing folder.\n\n{source or '(empty)'}")
            self._reset_preview("Choose an existing folder.")
            self._set_status("Source folder not found.", DANGER)
            return

        dest = self._path(self.dest_var.get()) or source
        if dest.exists() and not dest.is_dir():
            messagebox.showerror("Destination problem", f"Not a folder:\n\n{dest}")
            self._reset_preview("Choose a valid destination.")
            self._set_status("Destination is not a folder.", DANGER)
            return

        try:
            moves, unknown, warnings = fileorg.build_moves(
                source,
                dest,
                recursive=self.recursive_var.get(),
                ignore=self._parse_ignore(),
                include_hidden=self.hidden_var.get(),
                move_unknown=self.unknown_var.get(),
            )
        except OSError as error:
            messagebox.showerror("Could not scan folder", str(error))
            self._reset_preview("Could not scan this folder.")
            self._set_status("Could not scan the folder.", DANGER)
            return

        self.plan = Plan(source=source, dest=dest, moves=moves, unknown=unknown, warnings=warnings)
        self._populate(moves, source)
        self._update_plan_ui()

    def _populate(self, moves: list[fileorg.Move], source: Path) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, move in enumerate(moves):
            try:
                relative = move.src.relative_to(source).as_posix()
            except ValueError:
                relative = str(move.src)
            destination = f"{move.folder}/{move.dst.name}"
            row_tag = "even" if index % 2 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(relative, destination),
                tags=(row_tag, f"cat-{move.folder}"),
            )

    def _update_plan_ui(self) -> None:
        assert self.plan is not None
        moves = self.plan.moves
        folders = len({move.folder for move in moves})

        if not moves:
            self.summary.configure(text="Nothing to move.")
            self.detail.configure(text="This folder is already tidy for the selected options.")
            self.organise_btn.state(["disabled"])
            self.organise_btn.configure(text="Organise")
            self._set_status("Preview complete. Nothing to move.", SUCCESS)
            return

        self.summary.configure(
            text=f"{fileorg.plural(len(moves), 'file')}  \u2192  {fileorg.plural(folders, 'folder')}"
        )
        details = []
        if self.plan.unknown:
            details.append(f"{fileorg.plural(len(self.plan.unknown), 'unknown file')} will stay in place")
        if self.plan.warnings:
            details.append(f"{fileorg.plural(len(self.plan.warnings), 'warning')}")
        if self.plan.dest != self.plan.source:
            details.append(f"destination: {pretty_path(self.plan.dest)}")
        self.detail.configure(text="  \u00b7  ".join(details) if details else "Ready to organise.")
        self.organise_btn.configure(text=f"Organise {fileorg.plural(len(moves), 'file')}")
        self.organise_btn.state(["!disabled"])
        self._set_status("Preview complete. Nothing has been moved yet.", MUTED)

    def organise(self) -> None:
        if self.busy:
            return
        if self.plan is None:
            self.preview()
            if self.plan is None:
                return
        plan = self.plan
        if not plan.moves:
            messagebox.showinfo("Nothing to move", "This folder is already tidy for the selected options.")
            return

        folders = len({move.folder for move in plan.moves})
        confirmed = messagebox.askyesno(
            "Organise files?",
            f"Move {fileorg.plural(len(plan.moves), 'file')} into "
            f"{fileorg.plural(folders, 'folder')} in:\n\n{plan.dest}\n\n"
            "Nothing is overwritten, and this run can be undone.",
            icon="question",
            default="yes",
        )
        if not confirmed:
            return

        try:
            result = self._run_busy(
                lambda: fileorg.apply_moves(
                    plan.moves,
                    self.state_dir,
                    plan.source,
                    plan.dest,
                    verbose=False,
                )
            )
        except OSError as error:
            self._set_status("Could not finish the run.", DANGER)
            messagebox.showerror("Could not organise", str(error))
            return
        self._after_apply(result)

    def _run_busy(self, action):
        self.busy = True
        self.root.configure(cursor="watch")
        for button in (self.preview_btn, self.organise_btn, self.undo_btn):
            button.state(["disabled"])
        self.root.update_idletasks()
        try:
            return action()
        finally:
            self.busy = False
            self.root.configure(cursor="")
            self._refresh_undo_state()

    def _after_apply(self, result) -> None:
        journal, errors = result
        self.preview()
        self._refresh_undo_state()

        moved = 0
        if journal is not None:
            try:
                moved = len(json.loads(journal.read_text(encoding="utf-8")).get("moves", []))
            except (OSError, json.JSONDecodeError):
                moved = 0

        self._set_status(f"Moved {fileorg.plural(moved, 'file')}.", SUCCESS if not errors else WARNING)

        lines = [f"Moved {fileorg.plural(moved, 'file')}."]
        if errors:
            lines.append("")
            lines.append(f"{fileorg.plural(len(errors), 'file')} could not be moved:")
            for path, error in errors[:5]:
                lines.append(f"  {path.name}: {error}")
            if len(errors) > 5:
                lines.append(f"  ...and {len(errors) - 5} more")
            messagebox.showwarning("Finished with errors", "\n".join(lines))
        else:
            if journal is not None:
                lines.append("")
                lines.append(f"Journal: {journal}")
            messagebox.showinfo("Organised", "\n".join(lines))

    def undo_last(self) -> None:
        if self.busy:
            return
        journal = fileorg.latest_journal(self.state_dir)
        if journal is None:
            messagebox.showinfo("Nothing to undo", "No organise run has been recorded yet.")
            return

        try:
            data = json.loads(journal.read_text(encoding="utf-8"))
            entries, missing = fileorg.plan_undo(data)
        except (OSError, json.JSONDecodeError, KeyError) as error:
            messagebox.showerror("Could not read journal", str(error))
            return

        if not entries:
            messagebox.showinfo(
                "Nothing to restore",
                "The files from the last run are no longer where they were moved.",
            )
            return

        confirmed = messagebox.askyesno(
            "Undo the last run?",
            f"Restore {fileorg.plural(len(entries), 'file')} to their original places?\n\n"
            "Emptied category folders will be removed.",
            icon="question",
            default="yes",
        )
        if not confirmed:
            return

        self.busy = True
        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        restored: list[fileorg.Move] = []
        errors: list[tuple[Path, str]] = []
        try:
            for move in entries:
                try:
                    move.dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(move.src), str(move.dst))
                except OSError as error:
                    errors.append((move.src, str(error)))
                    continue
                restored.append(move)

            removed: list[Path] = []
            if restored:
                removed = fileorg.prune_empty_dirs(
                    {move.src.parent for move in restored},
                    Path(data.get("dest", "")),
                )
                try:
                    journal.replace(journal.with_name(journal.name + ".undone"))
                except OSError:
                    pass
        finally:
            self.busy = False
            self.root.configure(cursor="")

        self.preview()
        self._refresh_undo_state()
        self._set_status(f"Restored {fileorg.plural(len(restored), 'file')}.", SUCCESS if not errors else WARNING)

        lines = [f"Restored {fileorg.plural(len(restored), 'file')}."]
        if removed:
            lines.append(f"Removed {fileorg.plural(len(removed), 'empty folder')}.")
        if missing:
            lines.append("")
            lines.append(f"{fileorg.plural(len(missing), 'file')} was no longer in its organised place.")
        if errors:
            lines.append("")
            lines.append(f"{fileorg.plural(len(errors), 'file')} could not be restored:")
            for path, error in errors[:5]:
                lines.append(f"  {path.name}: {error}")
        (messagebox.showwarning if errors else messagebox.showinfo)("Undo complete", "\n".join(lines))


def main() -> int:
    dpi_awareness()
    initial = None
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.is_dir():
            initial = candidate

    root = tk.Tk()
    root.app = FileorgApp(root, initial)

    def report_callback_exception(exc_type, exc_value, _traceback) -> None:
        messagebox.showerror("Unexpected error", f"{exc_type.__name__}: {exc_value}")

    root.report_callback_exception = report_callback_exception
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
