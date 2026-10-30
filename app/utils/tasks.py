"""Background task runners that keep Tk's event loop free.

Worker threads never touch widgets. Results are queued and drained by a
callback scheduled with ``after()`` on the Tk main thread.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Callable, Protocol, TypeVar

T = TypeVar("T")


class TaskRunner(Protocol):
    """Run blocking work off the UI thread."""

    def run(
        self,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
    ) -> None: ...


class ThreadedTaskRunner:
    """A :class:`TaskRunner` backed by daemon threads and a result queue."""

    def __init__(self, root: tk.Misc, poll_ms: int = 30) -> None:
        self._root = root
        self._poll_ms = poll_ms
        self._queue: "queue.Queue[tuple[Callable, object]]" = queue.Queue()
        self._pending = 0
        self._polling = False

    def run(
        self,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self._pending += 1

        def worker() -> None:
            try:
                result = work()
            except Exception as error:  # delivered to the UI thread
                self._queue.put((on_error, error))
            else:
                self._queue.put((on_success, result))

        threading.Thread(target=worker, daemon=True).start()
        if not self._polling:
            self._polling = True
            self._root.after(self._poll_ms, self._poll)

    def _poll(self) -> None:
        while True:
            try:
                callback, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            self._pending -= 1
            callback(payload)
        if self._pending > 0:
            self._root.after(self._poll_ms, self._poll)
        else:
            self._polling = False


class ImmediateTaskRunner:
    """Runs work inline; useful in tests and before the main loop starts."""

    def run(
        self,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        try:
            result = work()
        except Exception as error:
            on_error(error)
        else:
            on_success(result)
