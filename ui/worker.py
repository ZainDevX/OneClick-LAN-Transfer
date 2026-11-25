"""Background jobs and GUI-thread bridges for OneClick LAN views."""

import logging

from PySide6.QtCore import QObject, QThread, Signal

from app.error_handler import AppError

logger = logging.getLogger("OneClickLAN.Worker")


class FunctionThread(QThread):
    """Run one callable off the GUI thread and return its result as a signal."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.succeeded.emit(self._fn())
        except AppError as exc:
            self.failed.emit(exc.detail.format_user_message())
        except Exception as exc:
            logger.exception("Background job failed")
            self.failed.emit(str(exc))


class HostBridge(QObject):
    """Queues host-service callbacks onto the GUI thread."""

    client_connected = Signal(str)
    client_disconnected = Signal()
    progress = Signal(object)
    status = Signal(str)
    error = Signal(str)


class ClientBridge(QObject):
    """Queues client-service callbacks onto the GUI thread."""

    progress = Signal(object)
    status = Signal(str)
    error = Signal(str)
    transfer_complete = Signal()
    disconnected = Signal()
