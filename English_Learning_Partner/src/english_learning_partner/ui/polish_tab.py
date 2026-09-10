"""Fast English work-expression generator and English polishing interface."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..domain.models import PolishResult, ServiceResult
from ..services.learning_service import LearningService
from .result_cards import ResultCard
from .workers import Worker


class PolishTab(QWidget):
    INPUT_HINT = "按 Enter 生成英文；Shift + Enter 换行"
    completed = Signal()
    status_changed = Signal(str, str)

    def __init__(self, service_factory: Callable[[], LearningService]) -> None:
        super().__init__()
        self._service_factory = service_factory
        self._thread_pool = QThreadPool.globalInstance()
        self._active_worker: Worker | None = None
        self._last_result: PolishResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 16, 28, 22)
        layout.setSpacing(12)

        splitter = QSplitter()
        splitter.setObjectName("polishSplitter")
        splitter.setHandleWidth(16)
        splitter.setChildrenCollapsible(False)

        input_card = QFrame()
        input_card.setObjectName("inputCard")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(18, 16, 18, 18)
        input_layout.setSpacing(10)
        input_layout.addWidget(self._section_label("输入内容"))
        self.input_edit = QPlainTextEdit()
        self.input_edit.setObjectName("polishInput")
        self.input_edit.setPlaceholderText(self.INPUT_HINT)
        self.input_edit.installEventFilter(self)
        input_layout.addWidget(self.input_edit, 1)
        splitter.addWidget(input_card)

        result_card = QFrame()
        result_card.setObjectName("resultCard")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(18, 16, 18, 18)
        result_layout.setSpacing(10)
        result_layout.addWidget(self._section_label("英文表达"))
        self.output = QScrollArea()
        self.output.setObjectName("polishResult")
        self.output.setWidgetResizable(True)
        self.output.setFrameShape(QFrame.Shape.NoFrame)
        self.output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_container = QWidget()
        self.result_container.setObjectName("polishResultContainer")
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(2, 2, 2, 2)
        self.result_layout.setSpacing(16)
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.output.setWidget(self.result_container)
        result_layout.addWidget(self.output, 1)
        splitter.addWidget(result_card)
        splitter.setSizes([380, 800])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        layout.addWidget(splitter, 1)
        self._show_empty_state()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.input_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers():
                self._submit()
                return True
        return super().eventFilter(watched, event)

    def _submit(self) -> None:
        if self._active_worker is not None:
            return
        input_text = self.input_edit.toPlainText()
        self.input_edit.setReadOnly(True)
        self._last_result = None
        self.status_changed.emit("正在生成英文表达…", "loading")
        self._show_message("正在整理英文工作表达，请稍候…")
        worker = Worker(lambda: self._service_factory().polish(input_text))
        self._active_worker = worker
        worker.signals.succeeded.connect(self._show_result)
        worker.signals.failed.connect(self._show_error)
        worker.signals.finished.connect(self._finish_request)
        self._thread_pool.start(worker)

    def _finish_request(self) -> None:
        self._active_worker = None
        self.input_edit.setReadOnly(False)

    def _show_empty_state(self) -> None:
        self._show_message("输入内容后按 Enter，即可生成适合邮件或 Teams 的英文表达。")

    def _show_message(self, message: str) -> None:
        self._clear_result_layout()
        label = QLabel(message)
        label.setObjectName("translationEmptyState")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.result_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignTop)

    def _show_result(self, service_result: ServiceResult) -> None:
        result = service_result.value
        assert isinstance(result, PolishResult)
        self._last_result = result
        self._render_last_result()
        if service_result.save_warning:
            self.status_changed.emit(f"生成完成，但未保存：{service_result.save_warning}", "warning")
        elif result.input_kind == "english_polish" and result.grammar_issues:
            self.status_changed.emit("生成完成，已保存记录并新增语法复习项。", "success")
        else:
            self.status_changed.emit("生成完成，已保存学习记录。", "success")
        self.input_edit.clear()
        self.input_edit.setFocus()
        self.completed.emit()

    def _show_error(self, message: str) -> None:
        self._last_result = None
        self.status_changed.emit("生成失败", "error")
        self._clear_result_layout()
        error_card = ResultCard("无法生成英文表达")
        error_card.setObjectName("translationErrorCard")
        error_card.add_text(message)
        self.result_layout.addWidget(error_card, alignment=Qt.AlignmentFlag.AlignTop)

    def _render_last_result(self) -> None:
        if self._last_result is None:
            return
        self._clear_result_layout()
        primary_card, secondary_cards = self._build_result_cards(self._last_result)
        self.result_layout.addWidget(primary_card, alignment=Qt.AlignmentFlag.AlignTop)
        for card in secondary_cards:
            self.result_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignTop)

    @staticmethod
    def _build_result_cards(result: PolishResult) -> tuple[ResultCard, list[ResultCard]]:
        primary_card = ResultCard("英文表达", "primary")
        primary_card.add_text(result.polished_text, "translationHero")

        alternatives_card = ResultCard("其他翻译候选")
        if result.alternatives:
            for alternative in result.alternatives:
                alternatives_card.add_alternative(alternative.expression, alternative.usage_note)
        else:
            alternatives_card.add_text("暂无其他候选表达。", "translationEmptyState")
        cards = [alternatives_card]

        if result.input_kind == "english_polish" and result.grammar_issues:
            issues_card = ResultCard("可复习的问题")
            for issue in result.grammar_issues:
                issues_card.add_issue(
                    issue.category,
                    issue.original,
                    issue.correction,
                    issue.explanation,
                    issue.rule,
                )
            cards.append(issues_card)
        return primary_card, cards

    def _clear_result_layout(self) -> None:
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _section_label(title: str) -> QLabel:
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        return label
