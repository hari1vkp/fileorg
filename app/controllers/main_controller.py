"""Coordinates the dashboard view, the organise service and settings.

The controller owns application state, validates input, runs slow work through
a :class:`TaskRunner`, and only calls the view from the Tk main thread.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.constants import (
    DEFAULT_SOURCE_TEXT,
    TONE_ACCENT,
    TONE_DANGER,
    TONE_MUTED,
    TONE_SUCCESS,
    TONE_WARNING,
    THEME_DARK,
)
from app.core.exceptions import (
    FileorgError,
    InvalidDestinationError,
    InvalidSourceError,
    JournalNotFoundError,
)
from app.models.forms import OrganiseForm
from app.models.organise import OrganisePlan, OrganiseResult, UndoPlan, UndoResult
from app.models.settings import AppSettings
from app.services.organise_service import OrganiseService
from app.services.settings_service import SettingsService
from app.ui.themes.theme_manager import ThemeManager
from app.utils.tasks import TaskRunner


class MainView(Protocol):
    """Everything the controller needs from the window."""

    def form_state(self) -> OrganiseForm: ...

    def set_form(self, form: OrganiseForm, settings: AppSettings) -> None: ...

    def refresh_settings(self, settings: AppSettings) -> None: ...

    def set_busy(self, busy: bool) -> None: ...

    def set_status(self, text: str, tone: str = TONE_MUTED) -> None: ...

    def show_plan(self, plan: OrganisePlan) -> None: ...

    def reset_preview(self, message: str) -> None: ...

    def set_undo_available(self, available: bool) -> None: ...

    def confirm_organise(self, plan: OrganisePlan) -> bool: ...

    def confirm_undo(self, plan: UndoPlan) -> bool: ...

    def nothing_to_move(self) -> None: ...

    def nothing_to_undo(self) -> None: ...

    def nothing_to_restore(self) -> None: ...

    def show_info(self, title: str, message: str) -> None: ...

    def show_warning(self, title: str, message: str) -> None: ...

    def show_error(self, title: str, message: str) -> None: ...

    def organise_done(self, result: OrganiseResult) -> None: ...

    def undo_done(self, result: UndoResult) -> None: ...


class MainController:
    """Application logic for the organise screen and shared settings."""

    def __init__(
        self,
        view: MainView,
        service: OrganiseService,
        settings_service: SettingsService,
        settings: AppSettings,
        theme_manager: ThemeManager,
        runner: TaskRunner,
    ) -> None:
        self.view = view
        self.service = service
        self.settings_service = settings_service
        self.settings = settings
        self.theme_manager = theme_manager
        self.runner = runner
        self.plan: OrganisePlan | None = None
        self._busy = False
        self._preview_token = 0
        self._outcome: tuple[str, str] | None = None

    # ------------------------------------------------------------ lifecycle

    def start(self) -> None:
        """Auto-preview when the remembered folder exists."""
        self.refresh_undo()
        form = self.view.form_state()
        self._sync_settings(form)
        if _is_dir(form.source):
            self.preview()
        else:
            self.view.set_status("Choose a folder to get started.")

    def shutdown(self) -> None:
        """Persist the current form before the window closes."""
        self._sync_settings(self.view.form_state())
        self._save()

    # ---------------------------------------------------------- form state

    def form_changed(self) -> None:
        if self._busy:
            return
        self._sync_settings(self.view.form_state())
        self.plan = None
        self._outcome = None
        self.view.reset_preview("Preview to see what will move.")
        self.view.set_status("Preview to see what will move.", TONE_MUTED)

    # ------------------------------------------------------------- actions

    def preview(self) -> None:
        if self._busy:
            return
        form = self.view.form_state()
        self._sync_settings(form)
        if not form.source.strip() and not _is_dir(DEFAULT_SOURCE_TEXT):
            self.plan = None
            self.view.reset_preview("Choose a folder, then preview.")
            self.view.set_status("Choose a folder to get started.", TONE_MUTED)
            return

        self._preview_token += 1
        token = self._preview_token
        outcome = self._outcome
        self._outcome = None

        source = form.source.strip() or DEFAULT_SOURCE_TEXT
        destination = form.destination.strip() or None
        options = form.to_options()

        self._set_busy(True)
        self.view.set_status("Scanning folder...", TONE_ACCENT)
        self.plan = None
        self.view.reset_preview("Scanning...")

        self.runner.run(
            lambda: self.service.preview(source, destination, options),
            lambda plan: self._preview_done(token, plan, outcome),
            lambda error: self._preview_failed(token, error),
        )

    def _preview_done(
        self, token: int, plan: OrganisePlan, outcome: tuple[str, str] | None
    ) -> None:
        if token != self._preview_token:
            return
        self._set_busy(False)
        self.plan = plan
        self.view.show_plan(plan)
        self.view.set_undo_available(self.service.has_undo())
        self._save()
        if outcome is not None:
            self.view.set_status(*outcome)
        elif plan.is_empty:
            self.view.set_status("Preview complete. Nothing to move.", TONE_SUCCESS)
        else:
            self.view.set_status(
                "Preview complete. Nothing has been moved yet.", TONE_MUTED
            )

    def _preview_failed(self, token: int, error: Exception) -> None:
        if token != self._preview_token:
            return
        self._set_busy(False)
        self.plan = None
        if isinstance(error, InvalidSourceError):
            title = "Folder not found"
            self.view.reset_preview("Choose an existing folder.")
        elif isinstance(error, InvalidDestinationError):
            title = "Destination problem"
            self.view.reset_preview("Choose a valid destination.")
        else:
            title = "Could not scan folder"
            self.view.reset_preview("Could not scan this folder.")
        self.view.show_error(title, str(error))
        self.view.set_status("Preview failed.", TONE_DANGER)

    def organise(self) -> None:
        if self._busy:
            return
        if self.plan is None:
            self.preview()
            return
        plan = self.plan
        if plan.is_empty:
            self.view.nothing_to_move()
            return
        if not self.view.confirm_organise(plan):
            return

        self._set_busy(True)
        self.view.set_status("Moving files...", TONE_ACCENT)
        self.runner.run(
            lambda: self.service.organise(plan),
            self._organised,
            self._organise_failed,
        )

    def _organised(self, result: OrganiseResult) -> None:
        self._set_busy(False)
        self.plan = None
        self.refresh_undo()
        self._outcome = (
            f"Moved {_files(result.moved_count)}.",
            TONE_WARNING if result.errors else TONE_SUCCESS,
        )
        self.view.organise_done(result)
        self.preview()

    def _organise_failed(self, error: Exception) -> None:
        self._set_busy(False)
        self.view.set_status("Could not finish the run.", TONE_DANGER)
        self.view.show_error("Could not organise", str(error))

    def undo_last(self) -> None:
        if self._busy:
            return
        try:
            undo_plan = self.service.load_undo()
        except JournalNotFoundError:
            self.refresh_undo()
            self.view.nothing_to_undo()
            return
        except FileorgError as error:
            self.view.show_error("Could not read journal", str(error))
            return

        if undo_plan.is_empty:
            self.view.nothing_to_restore()
            return
        if not self.view.confirm_undo(undo_plan):
            return

        self._set_busy(True)
        self.view.set_status("Restoring files...", TONE_ACCENT)
        self.runner.run(
            lambda: self.service.undo(undo_plan),
            self._undone,
            self._undo_failed,
        )

    def _undone(self, result: UndoResult) -> None:
        self._set_busy(False)
        self.refresh_undo()
        self._outcome = (
            f"Restored {_files(result.restored_count)}.",
            TONE_WARNING if result.errors else TONE_SUCCESS,
        )
        self.view.undo_done(result)
        self.preview()

    def _undo_failed(self, error: Exception) -> None:
        self._set_busy(False)
        self.view.set_status("Could not finish the undo.", TONE_DANGER)
        self.view.show_error("Could not undo", str(error))

    # ------------------------------------------------------------ settings

    def set_theme(self, name: str) -> None:
        self.settings.theme = name
        self.theme_manager.set_theme(name)
        self.view.refresh_settings(self.settings)
        self._save()

    def toggle_theme(self) -> None:
        target = "light" if self.settings.theme == THEME_DARK else "dark"
        self.set_theme(target)

    def set_default_source(self, source: str) -> None:
        self.settings.source = source
        self._save()

    def reset_settings(self) -> None:
        self.settings = self.settings_service.reset()
        self.theme_manager.set_theme(self.settings.theme)
        form = OrganiseForm.from_settings(self.settings)
        self.plan = None
        self.view.set_form(form, self.settings)
        self.view.refresh_settings(self.settings)
        self.view.reset_preview("Preview to see what will move.")
        self.view.set_status("Settings restored to defaults.", TONE_SUCCESS)
        if _is_dir(self.settings.source or DEFAULT_SOURCE_TEXT):
            self.preview()

    # ------------------------------------------------------------- helpers

    def refresh_undo(self) -> None:
        self.view.set_undo_available(self.service.has_undo())

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.view.set_busy(busy)

    def _sync_settings(self, form: OrganiseForm) -> None:
        self.settings = form.apply_to(self.settings)

    def _save(self) -> None:
        try:
            self.settings_service.save(self.settings)
        except OSError:
            pass


def _files(count: int) -> str:
    return f"{count} file" + ("" if count == 1 else "s")


def _is_dir(value: str) -> bool:
    text = value.strip() or DEFAULT_SOURCE_TEXT
    return Path(text).expanduser().is_dir()
