from __future__ import annotations

from abc import ABC, abstractmethod

from app.application.dto.edit_progress import EditProgress


class EditProgressTracker(ABC):
    """Where an in-flight edit publishes its progress so a separate request
    can read it. Keyed by a caller-chosen progress_id rather than the
    edit's id, because the caller needs to poll *while* the request that
    creates the edit is still running — before it knows that id."""

    @abstractmethod
    def report(self, progress_id: str, progress: EditProgress) -> None: ...

    @abstractmethod
    def get(self, progress_id: str) -> EditProgress | None: ...
