"""Small, UI-agnostic helpers used by the CLI and the desktop app."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def plural(count: int, word: str) -> str:
    """Return ``"1 file"`` or ``"3 files"``."""
    return f"{count} {word}" + ("" if count == 1 else "s")


def pretty_path(path: Path) -> str:
    """Replace the user's home folder with ``~`` for display."""
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(path)


def open_in_file_manager(path: Path) -> None:
    """Open ``path`` in the platform file manager, ignoring failures."""
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


def enable_dpi_awareness() -> None:
    """Ask Windows for crisp text on high-DPI displays."""
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


def error_lines(errors: list[tuple[str, str]], limit: int = 5) -> list[str]:
    """Format up to ``limit`` ``(name, message)`` errors for a dialog."""
    lines = [f"  {name}: {message}" for name, message in errors[:limit]]
    if len(errors) > limit:
        lines.append(f"  ...and {len(errors) - limit} more")
    return lines


def shorten(text: str, limit: int = 72) -> str:
    """Shorten a path or message for a compact status line."""
    return text if len(text) <= limit else "..." + text[-(limit - 3) :]
