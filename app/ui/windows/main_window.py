"""The main window: shell, page switching and the view protocol."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from app.config import AppPaths, resource_path
from app.core.constants import APP_TAGLINE, DEFAULT_SOURCE_TEXT, TONE_MUTED
from app.models.forms import OrganiseForm
from app.models.organise import OrganisePlan, OrganiseResult, UndoPlan, UndoResult
from app.models.settings import AppSettings
from app.ui.components.dialogs import Dialogs
from app.ui.layouts.main_layout import MainLayout
from app.ui.themes.theme_manager import Theme, ThemeManager
from app.ui.views.dashboard_view import DashboardCallbacks, DashboardView
from app.ui.views.settings_view import SettingsCallbacks, SettingsView
from app.utils.helpers import open_in_file_manager


@dataclass
class WindowCallbacks:
    """Controller entry points used by the window and its screens."""

    on_preview: Callable[[], None]
    on_organise: Callable[[], None]
    on_undo: Callable[[], None]
    on_form_changed: Callable[[], None]
    on_theme_change: Callable[[str], None]
    on_toggle_theme: Callable[[], None]
    on_default_source_change: Callable[[str], None]
    on_reset: Callable[[], None]


class MainWindow:
    """Owns the root layout and exposes methods for the controller."""

    def __init__(
        self,
        root: tk.Tk,
        theme_manager: ThemeManager,
        callbacks: WindowCallbacks,
        settings: AppSettings,
        paths: AppPaths,
    ) -> None:
        self.root = root
        self.theme_manager = theme_manager
        self.callbacks = callbacks
        self.settings = settings
        self.paths = paths
        self.dialogs = Dialogs(root)
        self.controller = None  # set by Application after construction

        form = OrganiseForm.from_settings(settings)
        if not form.source:
            form = form.with_source(DEFAULT_SOURCE_TEXT)
        self._form = form
        self._page = ""
        self._busy = False
        self._undo_available = False
        self._icon: tk.PhotoImage | None = None

        self._configure_window()
        self.layout = MainLayout(
            root,
            theme_manager,
            state_dir=paths.state_dir,
            on_navigate=self.show_page,
            on_toggle_theme=callbacks.on_toggle_theme,
            on_open_journals=self.open_journals,
        )
        self.layout.pack(fill="both", expand=True)
        self._bind_shortcuts()
        self.show_page("dashboard")
        theme_manager.events.subscribe("theme_changed", self._theme_changed)

    # --------------------------------------------------------------- window

    def _configure_window(self) -> None:
        self.root.title("fileorg")
        self.root.configure(bg=self.theme_manager.palette.background)
        self.root.minsize(1000, 660)
        width, height = 1080, 740
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        try:
            self._icon = tk.PhotoImage(
                file=str(resource_path("assets", "icons", "icon.png"))
            )
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            self._icon = None

    def _bind_shortcuts(self) -> None:
        bindings = {
            "<Control-o>": self._browse_source,
            "<Control-r>": self.callbacks.on_preview,
            "<F5>": self.callbacks.on_preview,
            "<Control-Return>": self.callbacks.on_organise,
            "<Control-z>": self.callbacks.on_undo,
            "<Control-d>": self.callbacks.on_toggle_theme,
            "<Control-1>": lambda: self.show_page("dashboard"),
            "<Control-2>": lambda: self.show_page("settings"),
        }
        for sequence, action in bindings.items():
            self.root.bind(sequence, lambda _event, run=action: run())

    def _browse_source(self) -> None:
        if self.dashboard is not None:
            self.dashboard.choose_source()
        else:
            self.show_page("dashboard")
            if self.dashboard is not None:
                self.dashboard.choose_source()

    # ---------------------------------------------------------------- pages

    @property
    def dashboard(self) -> DashboardView | None:
        return self._dashboard

    @property
    def settings_view(self) -> SettingsView | None:
        return self._settings_view

    _dashboard: DashboardView | None = None
    _settings_view: SettingsView | None = None

    def show_page(self, page: str) -> None:
        if page not in ("dashboard", "settings"):
            return
        if page == self._page:
            return
        if self._dashboard is not None:
            self._form = self._dashboard.form_state()
            self._dashboard.destroy()
            self._dashboard = None
        if self._settings_view is not None:
            self._settings_view.destroy()
            self._settings_view = None

        self._page = page
        self.layout.sidebar.set_active(page)

        if page == "dashboard":
            self.layout.set_page("Organise", APP_TAGLINE)
            self._dashboard = DashboardView(
                self.layout.content,
                self.theme_manager,
                DashboardCallbacks(
                    on_preview=self.callbacks.on_preview,
                    on_organise=self.callbacks.on_organise,
                    on_undo=self.callbacks.on_undo,
                    on_form_changed=self._form_changed,
                ),
                self._form,
                self._undo_available,
            )
            self._dashboard.pack(fill="both", expand=True)
            if self.controller is not None and self.controller.plan is not None:
                self._dashboard.show_plan(self.controller.plan)
            elif not self._busy:
                self._dashboard.reset_preview("Preview to see what will move.")
            if self._busy:
                self._dashboard.set_busy(True)
        else:
            self.layout.set_page("Settings", "Tune the app to match how you work.")
            self._settings_view = SettingsView(
                self.layout.content,
                self.theme_manager,
                SettingsCallbacks(
                    on_theme_change=self.callbacks.on_theme_change,
                    on_default_source_change=self.callbacks.on_default_source_change,
                    on_reset=self.callbacks.on_reset,
                    on_open_journals=self.open_journals,
                ),
                self.settings,
                self.paths,
            )
            self._settings_view.pack(fill="both", expand=True)

    def _form_changed(self) -> None:
        if self._dashboard is not None:
            self._form = self._dashboard.form_state()
        self.callbacks.on_form_changed()

    def open_journals(self) -> None:
        open_in_file_manager(self.paths.state_dir)

    # ------------------------------------------------------- view protocol

    def form_state(self) -> OrganiseForm:
        if self._dashboard is not None:
            self._form = self._dashboard.form_state()
        return self._form

    def set_form(self, form: OrganiseForm, settings: AppSettings | None = None) -> None:
        self._form = form
        if settings is not None:
            self.settings = settings
        if self._dashboard is not None:
            self._dashboard.set_form(form)

    def refresh_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.layout.sidebar.set_theme_name(settings.theme)
        if self._settings_view is not None:
            self._settings_view.refresh(settings)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        if self._dashboard is not None:
            self._dashboard.set_busy(busy)

    def set_status(self, text: str, tone: str = TONE_MUTED) -> None:
        self.layout.set_status(text, tone)

    def show_plan(self, plan: OrganisePlan) -> None:
        self._form = self.form_state()
        if self._dashboard is not None:
            self._dashboard.show_plan(plan)

    def reset_preview(self, message: str) -> None:
        if self._dashboard is not None:
            self._dashboard.reset_preview(message)

    def set_undo_available(self, available: bool) -> None:
        self._undo_available = available
        if self._dashboard is not None:
            self._dashboard.set_undo_available(available)

    def confirm_organise(self, plan: OrganisePlan) -> bool:
        return self.dialogs.confirm_organise(plan)

    def confirm_undo(self, plan: UndoPlan) -> bool:
        return self.dialogs.confirm_undo(plan)

    def nothing_to_move(self) -> None:
        self.dialogs.nothing_to_move()

    def nothing_to_undo(self) -> None:
        self.dialogs.nothing_to_undo()

    def nothing_to_restore(self) -> None:
        self.dialogs.nothing_to_restore()

    def show_info(self, title: str, message: str) -> None:
        self.dialogs.info(title, message)

    def show_warning(self, title: str, message: str) -> None:
        self.dialogs.warning(title, message)

    def show_error(self, title: str, message: str) -> None:
        self.dialogs.error(title, message)

    def organise_done(self, result: OrganiseResult) -> None:
        self.dialogs.organise_done(result)

    def undo_done(self, result: UndoResult) -> None:
        self.dialogs.undo_done(result)

    # --------------------------------------------------------------- theme

    def _theme_changed(self, theme: Theme) -> None:
        self.layout.sidebar.set_theme_name(theme.name)
        self.root.configure(bg=theme.palette.background)
        if self._settings_view is not None:
            self._settings_view.refresh(self.settings)

    def report_exception(self, exc_type, exc_value, _traceback) -> None:
        self.dialogs.error("Unexpected error", f"{exc_type.__name__}: {exc_value}")

    def close(self) -> None:
        self.root.destroy()
