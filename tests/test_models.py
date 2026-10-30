"""Tests for the data models and form helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.core.constants import THEME_DARK, THEME_LIGHT
from app.models.forms import OrganiseForm
from app.models.organise import Move, OrganiseOptions, OrganisePlan
from app.models.settings import AppSettings


class MoveTest(unittest.TestCase):
    def test_relative_source_falls_back_outside_root(self) -> None:
        move = Move(Path("/tmp/a/photo.jpg"), Path("/tmp/Images/photo.jpg"), "Images")
        self.assertEqual(move.relative_source(Path("/tmp/a")), "photo.jpg")
        self.assertEqual(move.relative_source(Path("/elsewhere")), "/tmp/a/photo.jpg")

    def test_destination_label(self) -> None:
        move = Move(Path("/tmp/photo.jpg"), Path("/tmp/Images/photo (1).jpg"), "Images")
        self.assertEqual(move.destination_label(), "Images/photo (1).jpg")

    def test_move_keeps_tuple_unpacking(self) -> None:
        source, destination, folder = Move(Path("a"), Path("b"), "Code")
        self.assertEqual(folder, "Code")
        self.assertEqual(source, Path("a"))


class OptionsAndPlanTest(unittest.TestCase):
    def test_options_clean_ignore_values(self) -> None:
        options = OrganiseOptions.from_values(
            recursive=True,
            ignore=[" *.pdf ", "", "*.tmp"],
            include_hidden=True,
            move_unknown=True,
        )
        self.assertEqual(options.ignore, ("*.pdf", "*.tmp"))
        self.assertTrue(options.recursive)
        self.assertTrue(options.include_hidden)

    def test_plan_properties(self) -> None:
        plan = OrganisePlan(
            source=Path("/tmp/a"),
            destination=Path("/tmp/a"),
            options=OrganiseOptions(),
            moves=[
                Move(Path("/tmp/a/x.jpg"), Path("/tmp/a/Images/x.jpg"), "Images"),
                Move(Path("/tmp/a/y.jpg"), Path("/tmp/a/Images/y.jpg"), "Images"),
                Move(Path("/tmp/a/z.py"), Path("/tmp/a/Code/z.py"), "Code"),
            ],
        )
        self.assertFalse(plan.is_empty)
        self.assertTrue(plan.is_in_place)
        self.assertEqual(plan.folder_count, 2)

    def test_empty_plan(self) -> None:
        plan = OrganisePlan(
            source=Path("/tmp/a"),
            destination=Path("/tmp/b"),
            options=OrganiseOptions(),
        )
        self.assertTrue(plan.is_empty)
        self.assertFalse(plan.is_in_place)


class SettingsTest(unittest.TestCase):
    def test_defaults_are_light(self) -> None:
        settings = AppSettings()
        self.assertEqual(settings.theme, THEME_LIGHT)
        self.assertEqual(settings.source, "")

    def test_invalid_values_normalise(self) -> None:
        settings = AppSettings.from_dict(
            {
                "theme": "solarized",
                "source": 42,
                "recursive": "yes",
                "move_unknown": True,
                "ignore": None,
            }
        )
        self.assertEqual(settings.theme, THEME_LIGHT)
        self.assertEqual(settings.source, "")
        self.assertFalse(settings.recursive)
        self.assertTrue(settings.move_unknown)
        self.assertEqual(settings.ignore, "")

    def test_round_trip(self) -> None:
        settings = AppSettings(
            theme=THEME_DARK, source="/tmp/Downloads", recursive=True, ignore="*.tmp"
        )
        self.assertEqual(AppSettings.from_dict(settings.to_dict()), settings)

    def test_normalise_keeps_valid_theme(self) -> None:
        self.assertEqual(AppSettings(theme=THEME_DARK).normalised().theme, THEME_DARK)


class FormTest(unittest.TestCase):
    def test_patterns_split_on_comma_and_semicolon(self) -> None:
        form = OrganiseForm(ignore=" *.pdf,*.tmp; *.log ,")
        self.assertEqual(form.ignore_patterns, ("*.pdf", "*.tmp", "*.log"))

    def test_form_round_trips_through_settings(self) -> None:
        form = OrganiseForm(
            source="/tmp/Downloads",
            destination="/tmp/Sorted",
            ignore="*.tmp",
            recursive=True,
            move_unknown=True,
            include_hidden=True,
        )
        settings = form.apply_to(AppSettings(theme=THEME_DARK))
        self.assertEqual(settings.theme, THEME_DARK)
        self.assertEqual(OrganiseForm.from_settings(settings), form)


if __name__ == "__main__":
    unittest.main()
