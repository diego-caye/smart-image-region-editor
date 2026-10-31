"""Edit progress kept in process memory. Enough for this app's single
backend process: progress is only interesting while an edit runs, and
losing it on restart costs nothing. Several uvicorn workers would each see
only their own edits — that would need a shared store instead (e.g. Redis)
behind the same EditProgressTracker port."""

from __future__ import annotations

import threading
from collections import OrderedDict

from app.application.dto.edit_progress import EditProgress
from app.application.ports.edit_progress_tracker import EditProgressTracker


class InMemoryEditProgressTracker(EditProgressTracker):
    def __init__(self, max_entries: int = 256) -> None:
        # Written by the request running the edit, read by polling requests
        # on other threads.
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, EditProgress] = OrderedDict()
        self._max_entries = max_entries

    def report(self, progress_id: str, progress: EditProgress) -> None:
        with self._lock:
            self._entries[progress_id] = progress
            self._entries.move_to_end(progress_id)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def get(self, progress_id: str) -> EditProgress | None:
        with self._lock:
            return self._entries.get(progress_id)
