"""Application paths and platform defaults."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.constants import APP_NAME

SETTINGS_FILENAME = "settings.json"


def default_state_dir() -> Path:
    """Return the platform-appropriate folder for journals."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / APP_NAME


def default_config_dir() -> Path:
    """Return the platform-appropriate folder for user settings."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / APP_NAME


@dataclass(frozen=True)
class AppPaths:
    """Filesystem locations used by the application."""

    config_dir: Path
    settings_file: Path
    state_dir: Path

    @classmethod
    def default(cls) -> "AppPaths":
        config_dir = default_config_dir()
        return cls(
            config_dir=config_dir,
            settings_file=config_dir / SETTINGS_FILENAME,
            state_dir=default_state_dir(),
        )

    @classmethod
    def for_home(cls, home: Path) -> "AppPaths":
        """Build paths under an explicit home folder (used by tests)."""
        return cls(
            config_dir=home / ".config" / APP_NAME,
            settings_file=home / ".config" / APP_NAME / SETTINGS_FILENAME,
            state_dir=home / ".local" / "state" / APP_NAME,
        )


def resource_path(*parts: str) -> Path:
    """Resolve a bundled asset both in development and inside PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "app"  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)
