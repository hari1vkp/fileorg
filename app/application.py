"""Composition root: wire settings, services, theme, window and controller."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from typing import Sequence

from app.config import AppPaths
from app.controllers.main_controller import MainController
from app.core.events import EventBus
from app.services.organise_service import OrganiseService
from app.services.settings_service import SettingsService
from app.ui.themes.theme_manager import ThemeManager
from app.ui.windows.main_window import MainWindow, WindowCallbacks
from app.utils.helpers import enable_dpi_awareness
from app.utils.tasks import ThreadedTaskRunner


class Application:
    """Owns the Tk root and every collaborator for one app instance."""

    def __init__(self, initial: Path | None = None) -> None:
        enable_dpi_awareness()
        self.root = tk.Tk()

        self.paths = AppPaths.default()
        self.settings_service = SettingsService(self.paths)
        self.settings = self.settings_service.load()
        if initial is not None:
            self.settings.source = str(initial)

        self.events = EventBus()
        self.theme_manager = ThemeManager(self.root, self.settings.theme, self.events)
        self.service = OrganiseService(self.paths.state_dir)
        self.runner = ThreadedTaskRunner(self.root)

        self.window = MainWindow(
            self.root,
            self.theme_manager,
            WindowCallbacks(
                on_preview=lambda: self.controller.preview(),
                on_organise=lambda: self.controller.organise(),
                on_undo=lambda: self.controller.undo_last(),
                on_form_changed=lambda: self.controller.form_changed(),
                on_theme_change=lambda name: self.controller.set_theme(name),
                on_toggle_theme=lambda: self.controller.toggle_theme(),
                on_default_source_change=lambda value: self.controller.set_default_source(
                    value
                ),
                on_reset=lambda: self.controller.reset_settings(),
            ),
            self.settings,
            self.paths,
        )
        self.controller = MainController(
            self.window,
            self.service,
            self.settings_service,
            self.settings,
            self.theme_manager,
            self.runner,
        )
        self.window.controller = self.controller
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.report_callback_exception = self.window.report_exception
        self.root.after(250, self.controller.start)

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def shutdown(self) -> None:
        try:
            self.controller.shutdown()
        finally:
            self.window.close()


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    initial = None
    if args:
        candidate = Path(args[0]).expanduser()
        if candidate.is_dir():
            initial = candidate
    return Application(initial).run()


if __name__ == "__main__":
    raise SystemExit(main())
