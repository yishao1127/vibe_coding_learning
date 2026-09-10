"""Configuration dialog for the local Responses API and learning folder."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..config import AppSettings
from ..services.openai_responses_client import OpenAIResponsesClient
from .workers import Worker


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self._initial_settings = settings
        self._thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("设置")
        self.setMinimumWidth(620)
        self._build_ui(settings)

    def _build_ui(self, settings: AppSettings) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("本工具调用与 Knowledge Forest 相同的本地 OpenAI Responses API 兼容服务。"))
        form = QFormLayout()

        self.url_edit = QLineEdit(settings.model_base_url)
        self.url_edit.setPlaceholderText("http://localhost:23333/api/openai/v1")
        form.addRow("服务地址：", self.url_edit)

        self.model_edit = QLineEdit(settings.model_name)
        self.model_edit.setPlaceholderText("gpt-5.4")
        form.addRow("模型名称：", self.model_edit)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setValue(settings.timeout_seconds)
        self.timeout_spin.setSuffix(" 秒")
        form.addRow("请求超时：", self.timeout_spin)

        folder_row = QHBoxLayout()
        self.directory_edit = QLineEdit(str(settings.learning_directory))
        self.browse_button = QPushButton("选择 OneDrive 文件夹…")
        self.browse_button.clicked.connect(self._choose_directory)
        folder_row.addWidget(self.directory_edit, 1)
        folder_row.addWidget(self.browse_button)
        form.addRow("学习资料目录：", folder_row)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self._test_connection)
        actions.addWidget(self.test_button)
        self.test_status = QLabel()
        actions.addWidget(self.test_status, 1)
        layout.addLayout(actions)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_if_valid)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def value(self) -> AppSettings:
        return AppSettings(
            model_base_url=self.url_edit.text().strip().rstrip("/"),
            model_name=self.model_edit.text().strip(),
            timeout_seconds=self.timeout_spin.value(),
            learning_directory=Path(self.directory_edit.text().strip()).expanduser(),
        )

    def _choose_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择 OneDrive 同步资料目录", self.directory_edit.text())
        if selected:
            self.directory_edit.setText(selected)

    def _test_connection(self) -> None:
        settings = self.value()
        if not settings.model_base_url or not settings.model_name:
            self.test_status.setText("请先填写服务地址和模型名称。")
            return
        self.test_button.setEnabled(False)
        self.test_status.setText("正在测试…")
        worker = Worker(lambda: OpenAIResponsesClient(settings.model_base_url, settings.timeout_seconds).generate_json(
            settings.model_name, '请只返回 JSON：{"status":"ok"}'
        ))
        worker.signals.succeeded.connect(lambda _: self.test_status.setText("连接成功。"))
        worker.signals.failed.connect(lambda message: self.test_status.setText(f"连接失败：{message}"))
        worker.signals.finished.connect(lambda: self.test_button.setEnabled(True))
        self._thread_pool.start(worker)

    def _accept_if_valid(self) -> None:
        settings = self.value()
        if not settings.model_base_url or not settings.model_name:
            QMessageBox.warning(self, "设置不完整", "请填写本地服务地址和模型名称。")
            return
        if not str(settings.learning_directory):
            QMessageBox.warning(self, "设置不完整", "请选择学习资料目录。")
            return
        self.accept()
