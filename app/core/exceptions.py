"""Domain exceptions raised by the fileorg core and services.

The GUI and CLI both translate these into friendly messages, so the
exceptions carry user-facing text as their message.
"""

from __future__ import annotations


class FileorgError(Exception):
    """Base class for expected, user-facing fileorg errors."""


class InvalidSourceError(FileorgError):
    """The source folder is missing or is not a folder."""


class InvalidDestinationError(FileorgError):
    """The destination exists but is not a folder."""


class ScanError(FileorgError):
    """The folder could not be scanned."""


class JournalNotFoundError(FileorgError):
    """No journal matched the requested undo."""


class JournalReadError(FileorgError):
    """A journal exists but could not be parsed."""


class OrganiseError(FileorgError):
    """A run could not be started or completed."""


class UndoError(FileorgError):
    """An undo run could not be prepared."""
