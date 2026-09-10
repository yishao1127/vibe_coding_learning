"""Main application window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QTabWidget, QToolButton, QWidget

from ..config import SettingsStore
from ..services.learning_service import LearningService
from ..services.markdown_repository import MarkdownRepository
from ..services.openai_responses_client import OpenAIResponsesClient
from .lookup_tab import LookupTab
from .polish_tab import PolishTab
from .review_tab import ReviewTab
from .settings_dialog import SettingsDialog
from .theme import set_status


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore) -> None:
        super().__init__()
        self._settings_store = settings_store
        self.setWindowTitle("English Learning Partner")
        self.resize(1120, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.lookup_tab = LookupTab(self._service)
        self.polish_tab = PolishTab(self._service)
        self.review_tab = ReviewTab(self._repository)
        self.lookup_tab.completed.connect(self.review_tab.reload)
        self.polish_tab.completed.connect(self.review_tab.reload)
        self.lookup_tab.status_changed.connect(self._set_global_status)
        self.polish_tab.status_changed.connect(self._set_global_status)
        self.review_tab.status_changed.connect(self._set_global_status)
        self.tabs.addTab(self.lookup_tab, "翻译")
        self.tabs.addTab(self.polish_tab, "润色")
        self.tabs.addTab(self.review_tab, "复习")

        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 10, 0)
        corner_layout.setSpacing(6)
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("globalStatusLabel")
        corner_layout.addWidget(self.status_label)
        settings_button = QToolButton()
        settings_button.setObjectName("settingsButton")
        settings_button.setText("⚙")
        settings_button.setToolTip("设置")
        settings_button.setAccessibleName("设置")
        settings_button.clicked.connect(self._open_settings)
        corner_layout.addWidget(settings_button)
        self.tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)
        self.setCentralWidget(self.tabs)

    def _set_global_status(self, message: str, status: str) -> None:
        set_status(self.status_label, message, status)

    def _service(self) -> LearningService:
        settings = self._settings_store.load()
        return LearningService(
            OpenAIResponsesClient(settings.model_base_url, settings.timeout_seconds),
            MarkdownRepository(settings.learning_directory),
            settings.model_name,
        )

    def _repository(self) -> MarkdownRepository:
        return MarkdownRepository(self._settings_store.load().learning_directory)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._settings_store.load(), self)
        if dialog.exec():
            self._settings_store.save(dialog.value())
            self.review_tab.reload()
