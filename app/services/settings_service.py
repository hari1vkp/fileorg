"""Persistence for user settings."""

from __future__ import annotations

import json

from app.config import AppPaths
from app.models.settings import AppSettings


class SettingsService:
    """Load and save :class:`AppSettings` as a small JSON file."""

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def load(self) -> AppSettings:
        """Read settings, falling back to defaults for missing or bad data."""
        path = self.paths.settings_file
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return AppSettings()
        if not isinstance(data, dict):
            return AppSettings()
        return AppSettings.from_dict(data).normalised()

    def save(self, settings: AppSettings) -> None:
        """Write settings atomically; failures are reported to the caller."""
        path = self.paths.settings_file
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(settings.normalised().to_dict(), indent=2) + "\n"
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(payload, encoding="utf-8")
        temp.replace(path)

    def reset(self) -> AppSettings:
        """Return defaults and persist them."""
        settings = AppSettings()
        self.save(settings)
        return settings
