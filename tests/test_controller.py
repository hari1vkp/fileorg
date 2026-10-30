"""Tests for the MainController using a fake view and inline runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import AppPaths
from app.controllers.main_controller import MainController
from app.models.forms import OrganiseForm
from app.models.settings import AppSettings
from app.services.organise_service import OrganiseService
from app.services.settings_service import SettingsService
from app.utils.tasks import ImmediateTaskRunner


class FakeThemeManager:
    def __init__(self) -> None:
        self.name = "light"
        self.calls: list[str] = []

    def set_theme(self, name: str) -> None:
        self.name = name
        self.calls.append(name)


class FakeView:
    def __init__(self, form: OrganiseForm) -> None:
        self.form = form
        self.busy = False
        self.status: tuple[str, str] | None = None
        self.plan = None
        self.reset_message = ""
        self.undo_available = False
        self.errors: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []
        self.organised = []
        self.undone = []
        self.answer = True
        self.settings: AppSettings | None = None

    def form_state(self) -> OrganiseForm:
        return self.form

    def set_form(self, form: OrganiseForm, settings: AppSettings | None = None) -> None:
        self.form = form
        self.settings = settings

    def refresh_settings(self, settings: AppSettings) -> None:
        self.settings = settings

    def set_busy(self, busy: bool) -> None:
        self.busy = busy

    def set_status(self, text: str, tone: str = "muted") -> None:
        self.status = (text, tone)

    def show_plan(self, plan) -> None:
        self.plan = plan

    def reset_preview(self, message: str) -> None:
        self.reset_message = message

    def set_undo_available(self, available: bool) -> None:
        self.undo_available = available

    def confirm_organise(self, plan) -> bool:
        return self.answer

    def confirm_undo(self, plan) -> bool:
        return self.answer

    def nothing_to_move(self) -> None:
        self.infos.append(("Nothing to move", ""))

    def nothing_to_undo(self) -> None:
        self.infos.append(("Nothing to undo", ""))

    def nothing_to_restore(self) -> None:
        self.infos.append(("Nothing to restore", ""))

    def show_info(self, title: str, message: str) -> None:
        self.infos.append((title, message))

    def show_warning(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def organise_done(self, result) -> None:
        self.organised.append(result)

    def undo_done(self, result) -> None:
        self.undone.append(result)


class ControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "Downloads"
        self.source.mkdir()
        (self.source / "photo.jpg").write_text("x", encoding="utf-8")
        (self.source / "main.py").write_text("x", encoding="utf-8")

        self.paths = AppPaths.for_home(self.root / "home")
        self.settings_service = SettingsService(self.paths)
        self.settings = AppSettings(source=str(self.source))
        self.service = OrganiseService(self.paths.state_dir)
        self.view = FakeView(OrganiseForm(source=str(self.source)))
        self.theme = FakeThemeManager()
        self.controller = MainController(
            self.view,
            self.service,
            self.settings_service,
            self.settings,
            self.theme,  # type: ignore[arg-type]
            ImmediateTaskRunner(),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_preview_populates_the_view(self) -> None:
        self.controller.preview()
        self.assertIsNotNone(self.controller.plan)
        self.assertEqual(len(self.controller.plan.moves), 2)
        self.assertEqual(self.view.plan, self.controller.plan)
        self.assertEqual(self.view.status, ("Preview complete. Nothing has been moved yet.", "muted"))
        self.assertFalse(self.view.busy)

    def test_organise_moves_and_reports(self) -> None:
        self.controller.preview()
        self.controller.organise()
        self.assertTrue((self.source / "Images/photo.jpg").is_file())
        self.assertTrue((self.source / "Code/main.py").is_file())
        self.assertEqual(len(self.view.organised), 1)
        self.assertTrue(self.view.undo_available)

    def test_undo_restores_files(self) -> None:
        self.controller.preview()
        self.controller.organise()
        self.controller.undo_last()
        self.assertTrue((self.source / "photo.jpg").is_file())
        self.assertTrue((self.source / "main.py").is_file())
        self.assertEqual(len(self.view.undone), 1)
        self.assertEqual(self.view.status, ("Restored 2 files.", "success"))

    def test_declining_confirmation_does_nothing(self) -> None:
        self.controller.preview()
        self.view.answer = False
        self.controller.organise()
        self.assertTrue((self.source / "photo.jpg").is_file())
        self.assertEqual(self.view.organised, [])

    def test_missing_source_reports_an_error(self) -> None:
        self.view.form = OrganiseForm(source=str(self.root / "nope"))
        self.controller.preview()
        self.assertEqual(self.view.errors[0][0], "Folder not found")
        self.assertEqual(self.view.status, ("Preview failed.", "danger"))

    def test_form_change_clears_the_plan(self) -> None:
        self.controller.preview()
        self.controller.form_changed()
        self.assertIsNone(self.controller.plan)
        self.assertEqual(self.view.reset_message, "Preview to see what will move.")

    def test_theme_is_applied_and_saved(self) -> None:
        self.controller.set_theme("dark")
        self.assertEqual(self.theme.name, "dark")
        self.assertEqual(self.settings_service.load().theme, "dark")

    def test_reset_restores_defaults(self) -> None:
        self.controller.set_theme("dark")
        self.controller.reset_settings()
        self.assertEqual(self.theme.name, "light")
        self.assertEqual(self.view.form.source, "")
        self.assertEqual(self.view.status, ("Settings restored to defaults.", "success"))

    def test_undo_without_journal(self) -> None:
        self.controller.undo_last()
        self.assertEqual(self.view.infos[0][0], "Nothing to undo")


if __name__ == "__main__":
    unittest.main()
