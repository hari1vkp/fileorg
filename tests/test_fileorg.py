"""Tests for fileorg. Run with: python -m unittest discover -s tests -v"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fileorg  # noqa: E402


class FileorgTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.downloads = self.root / "Downloads"
        self.downloads.mkdir()
        self.state = self.root / "state"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def touch(self, relative: str, content: str = "x") -> Path:
        path = self.downloads / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = fileorg.main([str(self.downloads), "--state-dir", str(self.state), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def seed_common(self) -> None:
        for name in (
            "photo.jpg",
            "clip.mp4",
            "song.mp3",
            "notes.pdf",
            "data.csv",
            "slides.pptx",
            "bundle.tar.gz",
            "main.py",
            "font.ttf",
            "mystery.xyz",
        ):
            self.touch(name)

    def test_split_name(self) -> None:
        self.assertEqual(fileorg.split_name("archive.tar.gz"), ("archive", ".tar.gz"))
        self.assertEqual(fileorg.split_name("photo.JPG"), ("photo", ".JPG"))
        self.assertEqual(fileorg.split_name("README"), ("README", ""))
        self.assertEqual(fileorg.split_name(".bashrc"), (".bashrc", ""))

    def test_dry_run_is_the_default(self) -> None:
        self.seed_common()
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertIn("Would move 9 files", out)
        self.assertTrue((self.downloads / "photo.jpg").exists())
        self.assertFalse((self.downloads / "Images").exists())
        self.assertFalse(self.state.exists())

    def test_apply_sorts_files_into_categories(self) -> None:
        self.seed_common()
        code, out, err = self.run_cli("--apply")
        self.assertEqual(code, 0, err)
        self.assertIn("Moved 9 files", out)

        expected = {
            "Images/photo.jpg": "photo.jpg",
            "Videos/clip.mp4": "clip.mp4",
            "Audio/song.mp3": "song.mp3",
            "Documents/notes.pdf": "notes.pdf",
            "Spreadsheets/data.csv": "data.csv",
            "Presentations/slides.pptx": "slides.pptx",
            "Archives/bundle.tar.gz": "bundle.tar.gz",
            "Code/main.py": "main.py",
            "Fonts/font.ttf": "font.ttf",
        }
        for target, source in expected.items():
            self.assertTrue((self.downloads / target).is_file(), target)
            self.assertFalse((self.downloads / source).exists(), source)
        self.assertTrue((self.downloads / "mystery.xyz").exists())

    def test_move_unknown_uses_other_folder(self) -> None:
        self.touch("mystery.xyz")
        self.touch("noextension")
        code, _, err = self.run_cli("--apply", "--move-unknown")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.downloads / "Other/mystery.xyz").is_file())
        self.assertTrue((self.downloads / "Other/noextension").is_file())

    def test_hidden_files_are_skipped_by_default(self) -> None:
        self.touch(".secret.txt")
        self.touch(".hidden/inside.png")
        self.touch("visible.png")
        self.run_cli("--apply", "--recursive")
        self.assertTrue((self.downloads / ".secret.txt").exists())
        self.assertTrue((self.downloads / ".hidden/inside.png").exists())
        self.assertTrue((self.downloads / "Images/visible.png").is_file())

    def test_include_hidden_moves_dotfiles(self) -> None:
        self.touch(".secret.txt")
        self.run_cli("--apply", "--include-hidden")
        self.assertTrue((self.downloads / "Documents/.secret.txt").is_file())

    def test_name_collisions_never_overwrite(self) -> None:
        self.touch("photo.jpg", "first")
        self.touch("nested/photo.jpg", "second")
        code, _, err = self.run_cli("--apply", "--recursive")
        self.assertEqual(code, 0, err)
        images = self.downloads / "Images"
        self.assertTrue((images / "photo.jpg").is_file())
        self.assertTrue((images / "photo (1).jpg").is_file())
        self.assertEqual((images / "photo.jpg").read_text(), "first")
        self.assertEqual((images / "photo (1).jpg").read_text(), "second")

    def test_second_run_is_a_no_op(self) -> None:
        self.seed_common()
        self.run_cli("--apply")
        code, out, _ = self.run_cli("--apply", "--recursive")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to move", out)
        self.assertFalse((self.downloads / "Images/photo (1).jpg").exists())

    def test_undo_restores_files_and_removes_empty_folders(self) -> None:
        self.seed_common()
        self.run_cli("--apply")
        code, out, err = self.run_cli("--undo", "--apply")
        self.assertEqual(code, 0, err)
        self.assertIn("Restored 9 files", out)

        for name in ("photo.jpg", "clip.mp4", "song.mp3", "notes.pdf", "main.py"):
            self.assertTrue((self.downloads / name).is_file(), name)
        for folder in ("Images", "Videos", "Audio", "Documents", "Code"):
            self.assertFalse((self.downloads / folder).exists(), folder)
        self.assertTrue((self.downloads / "mystery.xyz").exists())
        self.assertEqual(list(self.state.glob("journal-*.json")), [])
        self.assertEqual(len(list(self.state.glob("journal-*.json.undone"))), 1)

    def test_undo_dry_run_changes_nothing(self) -> None:
        self.seed_common()
        self.run_cli("--apply")
        code, out, _ = self.run_cli("--undo")
        self.assertEqual(code, 0)
        self.assertIn("Would restore 9 files", out)
        self.assertTrue((self.downloads / "Images/photo.jpg").is_file())
        self.assertEqual(len(list(self.state.glob("journal-*.json"))), 1)

    def test_custom_destination(self) -> None:
        sorted_folder = self.root / "Sorted"
        self.touch("photo.jpg")
        self.touch("mystery.xyz")
        out = io.StringIO()
        with redirect_stdout(out):
            code = fileorg.main(
                [
                    str(self.downloads),
                    "--dest",
                    str(sorted_folder),
                    "--apply",
                    "--state-dir",
                    str(self.state),
                ]
            )
        self.assertEqual(code, 0)
        self.assertTrue((sorted_folder / "Images/photo.jpg").is_file())
        self.assertTrue((self.downloads / "mystery.xyz").exists())

        with redirect_stdout(io.StringIO()):
            fileorg.main(["--undo", "--apply", "--state-dir", str(self.state)])
        self.assertTrue((self.downloads / "photo.jpg").is_file())
        self.assertFalse((sorted_folder / "Images").exists())

    def test_ignore_pattern(self) -> None:
        self.touch("keep.pdf")
        self.touch("skip.pdf")
        self.run_cli("--apply", "--ignore", "skip.pdf")
        self.assertTrue((self.downloads / "skip.pdf").exists())
        self.assertTrue((self.downloads / "Documents/keep.pdf").is_file())

    def test_missing_source_reports_error(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = fileorg.main([str(self.root / "nope"), "--state-dir", str(self.state)])
        self.assertEqual(code, 2)
        self.assertIn("not found", err.getvalue())

    def test_symlinks_are_left_alone(self) -> None:
        target = self.root / "outside.txt"
        target.write_text("outside", encoding="utf-8")
        link = self.downloads / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks need extra privileges here")
        code, _, err = self.run_cli("--apply")
        self.assertEqual(code, 0, err)
        self.assertTrue(link.is_symlink())
        self.assertIn("skipped symlink", err)


if __name__ == "__main__":
    unittest.main()
