"""Background workers that keep model calls off the Qt event loop."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self.task = task
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.succeeded.emit(self.task())
        except Exception as error:  # Error text is presented by the calling tab.
            self.signals.failed.emit(str(error) or "操作失败，请重试。")
        finally:
            self.signals.finished.emit()
