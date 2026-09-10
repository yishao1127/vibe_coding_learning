"""Application entry point."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from .app import create_application
from .ui.theme import APP_STYLESHEET


FONT_FAMILY = "Source Han Sans CN"
APP_USER_MODEL_ID = "YiShao.EnglishLearningPartner"


def set_windows_app_id() -> None:
    """Keep the development window separate from the Python taskbar group."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass


def app_icon_path() -> Path:
    """Locate the packaged icon in both source and PyInstaller environments."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root) / "resources" / "app_icon.png"
    return Path(__file__).resolve().parents[2] / "resources" / "app_icon.png"


def main() -> int:
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("English Learning Partner")
    app.setOrganizationName("Yi Shao")
    app.setWindowIcon(QIcon(str(app_icon_path())))
    app.setFont(QFont(FONT_FAMILY, 13))
    app.setStyleSheet(APP_STYLESHEET)
    window = create_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
