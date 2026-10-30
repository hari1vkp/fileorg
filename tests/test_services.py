"""Tests for the organise and settings services."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.config import AppPaths
from app.core.exceptions import (
    InvalidDestinationError,
    InvalidSourceError,
    JournalNotFoundError,
)
from app.models.organise import OrganiseOptions
from app.models.settings import AppSettings
from app.services.organise_service import OrganiseService
from app.services.settings_service import SettingsService


class OrganiseServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "Downloads"
        self.source.mkdir()
        self.state = self.root / "state"
        self.service = OrganiseService(self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def touch(self, relative: str, content: str = "x") -> Path:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_preview_plans_without_moving(self) -> None:
        self.touch("photo.jpg")
        self.touch("mystery.xyz")
        plan = self.service.preview(self.source)
        self.assertEqual(len(plan.moves), 1)
        self.assertEqual(plan.moves[0].folder, "Images")
        self.assertEqual(len(plan.unknown), 1)
        self.assertEqual(plan.source, self.source.resolve())
        self.assertFalse((self.source / "Images").exists())

    def test_preview_honours_options(self) -> None:
        self.touch("photo.jpg")
        self.touch("skip.jpg")
        plan = self.service.preview(
            self.source,
            options=OrganiseOptions(ignore=("skip.jpg",), move_unknown=True),
        )
        self.assertEqual([move.src.name for move in plan.moves], ["photo.jpg"])

    def test_missing_source_raises(self) -> None:
        with self.assertRaises(InvalidSourceError):
            self.service.preview(self.root / "nope")

    def test_destination_file_raises(self) -> None:
        destination = self.root / "file.txt"
        destination.write_text("x", encoding="utf-8")
        with self.assertRaises(InvalidDestinationError):
            self.service.preview(self.source, destination)

    def test_organise_writes_journal_and_moves(self) -> None:
        self.touch("photo.jpg")
        plan = self.service.preview(self.source)
        result = self.service.organise(plan)
        self.assertEqual(result.moved_count, 1)
        self.assertEqual(result.errors, [])
        self.assertIsNotNone(result.journal)
        self.assertTrue((self.source / "Images/photo.jpg").is_file())
        data = json.loads(result.journal.read_text(encoding="utf-8"))
        self.assertEqual(len(data["moves"]), 1)
        self.assertEqual(data["source"], str(self.source.resolve()))

    def test_undo_restores_and_removes_folders(self) -> None:
        self.touch("photo.jpg")
        plan = self.service.preview(self.source)
        self.service.organise(plan)
        undo_plan = self.service.load_undo()
        result = self.service.undo(undo_plan)
        self.assertEqual(result.restored_count, 1)
        self.assertTrue((self.source / "photo.jpg").is_file())
        self.assertFalse((self.source / "Images").exists())
        self.assertEqual(list(self.state.glob("journal-*.json")), [])
        self.assertEqual(len(list(self.state.glob("journal-*.json.undone"))), 1)

    def test_load_undo_without_journal(self) -> None:
        with self.assertRaises(JournalNotFoundError):
            self.service.load_undo()

    def test_has_undo_tracks_journal_state(self) -> None:
        self.assertFalse(self.service.has_undo())
        self.touch("photo.jpg")
        plan = self.service.preview(self.source)
        self.service.organise(plan)
        self.assertTrue(self.service.has_undo())


class SettingsServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.paths = AppPaths.for_home(Path(self._tmp.name))
        self.service = SettingsService(self.paths)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file_returns_defaults(self) -> None:
        self.assertEqual(self.service.load(), AppSettings())

    def test_save_and_load(self) -> None:
        settings = AppSettings(theme="dark", source="/tmp/Downloads", recursive=True)
        self.service.save(settings)
        self.assertEqual(self.service.load(), settings)
        self.assertTrue(self.paths.settings_file.is_file())

    def test_corrupt_file_returns_defaults(self) -> None:
        self.paths.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.paths.settings_file.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.service.load(), AppSettings())

    def test_reset_writes_defaults(self) -> None:
        self.service.save(AppSettings(theme="dark"))
        self.assertEqual(self.service.reset(), AppSettings())
        self.assertEqual(self.service.load(), AppSettings())


if __name__ == "__main__":
    unittest.main()
