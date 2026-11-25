"""
Shared Ethernet adapter cache.

The window reads the last result immediately. A scan starts only when the
cache is empty, older than the TTL, or the user presses Refresh. The scan
runs on a QThread and does not block page changes.
"""

import time

from PySide6.QtCore import QObject, QThread, Signal

from app.adapter_detection import get_physical_ethernet_adapters

CACHE_TTL_SECONDS = 8.0


def is_cache_fresh(fetched_at: float, now: float, ttl: float = CACHE_TTL_SECONDS) -> bool:
    """True when a stored result is still inside the short reuse window."""
    if fetched_at <= 0:
        return False
    return (now - fetched_at) < ttl


class AdapterScanThread(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            self.succeeded.emit(get_physical_ethernet_adapters())
        except Exception as exc:
            self.failed.emit(str(exc))


class AdapterDirectory(QObject):
    updated = Signal(object)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adapters = None
        self._fetched_at = 0.0
        self._thread = None
        self._rerun = False

    def current(self):
        return self._adapters

    def is_fresh(self) -> bool:
        return is_cache_fresh(self._fetched_at, time.monotonic())

    def invalidate(self):
        """Mark the cache stale without forgetting the last list."""
        self._fetched_at = 0.0

    def revalidate(self, force: bool = False):
        """Start a scan when needed. Returns immediately."""
        if self._thread is not None and self._thread.isRunning():
            if force:
                self._rerun = True
            return
        if self.is_fresh() and not force:
            return
        self._start()

    def _start(self):
        thread = AdapterScanThread(self)
        thread.succeeded.connect(self._on_success)
        thread.failed.connect(self._on_fail)
        self._thread = thread
        thread.start()

    def _on_success(self, adapters):
        self._adapters = list(adapters)
        self._fetched_at = time.monotonic()
        self.updated.emit(self._adapters)
        self._maybe_rerun()

    def _on_fail(self, message: str):
        self.failed.emit(str(message))
        self._maybe_rerun()

    def _maybe_rerun(self):
        if not self._rerun:
            return
        self._rerun = False
        if self._thread is not None and self._thread.isRunning():
            return
        self._start()
