"""Keeps a model loaded while it's in use and releases it after a quiet
period. Loading is the expensive part of an edit (measured ~40s for Qwen
and ~20s for SAM2 when reloaded each time), but holding GPU memory forever
would starve whatever else shares the GPU — this is the middle ground:
fast back-to-back edits, memory handed back once the user stops editing."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class IdleReleaser:
    """Runs `release` once `idle_seconds` pass without a touch(). An
    idle_seconds of 0 or less releases right away on every touch — i.e.
    load per use, never keep."""

    def __init__(self, idle_seconds: float, release: Callable[[], None], *, name: str) -> None:
        self._idle_seconds = idle_seconds
        self._release = release
        self._name = name
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def touch(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if self._idle_seconds > 0:
                self._timer = threading.Timer(self._idle_seconds, self._fire)
                self._timer.daemon = True
                self._timer.start()
        if self._idle_seconds <= 0:
            self._fire()

    def _fire(self) -> None:
        try:
            self._release()
            logger.info("Released %s after %ss idle", self._name, self._idle_seconds)
        except Exception:
            logger.warning("Could not release %s", self._name, exc_info=True)
