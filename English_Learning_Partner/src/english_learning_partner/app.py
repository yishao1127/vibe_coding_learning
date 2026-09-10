"""Application composition root."""

from __future__ import annotations

from .config import SettingsStore
from .ui.main_window import MainWindow


def create_application() -> MainWindow:
    return MainWindow(SettingsStore())
