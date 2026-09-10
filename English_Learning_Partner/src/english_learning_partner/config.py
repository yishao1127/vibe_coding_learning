"""Local application settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings


@dataclass(frozen=True)
class AppSettings:
    model_base_url: str
    model_name: str
    timeout_seconds: int
    learning_directory: Path


class SettingsStore:
    DEFAULT_URL = "http://localhost:23333/api/openai/v1"
    DEFAULT_MODEL = "gpt-5.4"
    DEFAULT_TIMEOUT = 90

    def __init__(self) -> None:
        self._settings = QSettings()

    @staticmethod
    def default_learning_directory() -> Path:
        return Path.home() / "OneDrive - Microsoft" / "EnglishLearningPartner"

    def load(self) -> AppSettings:
        directory = self._settings.value("learningDirectory", str(self.default_learning_directory()))
        timeout = self._settings.value("timeoutSeconds", self.DEFAULT_TIMEOUT)
        return AppSettings(
            model_base_url=str(self._settings.value("modelBaseUrl", self.DEFAULT_URL)).rstrip("/"),
            model_name=str(self._settings.value("modelName", self.DEFAULT_MODEL)).strip(),
            timeout_seconds=max(5, int(timeout)),
            learning_directory=Path(str(directory)).expanduser(),
        )

    def save(self, value: AppSettings) -> None:
        self._settings.setValue("modelBaseUrl", value.model_base_url.rstrip("/"))
        self._settings.setValue("modelName", value.model_name.strip())
        self._settings.setValue("timeoutSeconds", value.timeout_seconds)
        self._settings.setValue("learningDirectory", str(value.learning_directory))
        self._settings.sync()
