"""A tiny synchronous event bus used to decouple the UI from theme changes.

Events are emitted on the Tkinter main thread. Background work never emits
directly; the controller marshals results back to the main thread first.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict

THEME_CHANGED = "theme_changed"
SETTINGS_CHANGED = "settings_changed"
STATUS_CHANGED = "status_changed"
BUSY_CHANGED = "busy_changed"
PLAN_CHANGED = "plan_changed"
UNDO_AVAILABILITY_CHANGED = "undo_availability_changed"

Listener = Callable[[Any], None]


class EventBus:
    """A minimal subscribe/emit bus with string event names."""

    def __init__(self) -> None:
        self._listeners: DefaultDict[str, list[Listener]] = defaultdict(list)

    def subscribe(self, event: str, listener: Listener) -> Callable[[], None]:
        """Register ``listener`` and return a function that unsubscribes it."""
        self._listeners[event].append(listener)

        def unsubscribe() -> None:
            self.unsubscribe(event, listener)

        return unsubscribe

    def unsubscribe(self, event: str, listener: Listener) -> None:
        """Remove a previously registered listener, if present."""
        listeners = self._listeners.get(event, [])
        if listener in listeners:
            listeners.remove(listener)

    def emit(self, event: str, payload: Any = None) -> None:
        """Call every listener for ``event`` with ``payload``."""
        for listener in tuple(self._listeners.get(event, ())):
            listener(payload)
