"""Automatic bilingual translation interface for work communication."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..domain.models import LookupResult, ServiceResult
from ..services.learning_service import LearningService
from ..services.speech_service import SpeechResult, SpeechService
from .result_cards import ResultCard
from .workers import Worker


class TranslationInputEdit(QPlainTextEdit):
    """Single-line editor with a controlled hint unaffected by Windows IME rendering."""

    def __init__(self, hint_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hint_text = hint_text
        self.setPlaceholderText("")
        self._set_visible_text_color()
        self.textChanged.connect(self._refresh_viewport)

    def _set_visible_text_color(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor("#1F2937"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        self.setPalette(palette)

    def _refresh_viewport(self) -> None:
        self._set_visible_text_color()
        self.viewport().update()

    def insertFromMimeData(self, source) -> None:
        super().insertFromMimeData(source)
        self._refresh_viewport()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.toPlainText() or self.hasFocus():
            return
        painter = QPainter(self.viewport())
        painter.setPen(QColor("#748196"))
        painter.setFont(self.font())
        painter.drawText(
            self.viewport().rect().adjusted(13, 12, -13, -12),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._hint_text,
        )

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.viewport().update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.viewport().update()


class LookupTab(QWidget):
    INPUT_HINT = "按 Enter 翻译；Shift + Enter 换行"
    GRID_BREAKPOINT = 620

    completed = Signal()
    status_changed = Signal(str, str)

    def __init__(
        self,
        service_factory: Callable[[], LearningService],
        speech_service_factory: Callable[[], SpeechService] = SpeechService,
    ) -> None:
        super().__init__()
        self._service_factory = service_factory
        self._speech_service_factory = speech_service_factory
        self._thread_pool = QThreadPool.globalInstance()
        self._active_worker: Worker | None = None
        self._active_speech_worker: Worker | None = None
        self._pronunciation_buttons: list = []
        self._last_result: LookupResult | None = None
        self._last_result_columns: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 16, 28, 22)
        layout.setSpacing(12)

        input_card = QFrame()
        input_card.setObjectName("inputCard")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(18, 16, 18, 16)
        input_layout.setSpacing(10)
        input_layout.addWidget(self._section_label("输入内容"))
        self.input_edit = TranslationInputEdit(self.INPUT_HINT)
        self.input_edit.setObjectName("translationInput")
        self.input_edit.setFixedHeight(92)
        self.input_edit.installEventFilter(self)
        input_layout.addWidget(self.input_edit)
        layout.addWidget(input_card)

        result_card = QFrame()
        result_card.setObjectName("resultCard")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(18, 16, 18, 18)
        result_layout.setSpacing(10)
        result_layout.addWidget(self._section_label("翻译结果"))
        self.output = QScrollArea()
        self.output.setObjectName("translationResult")
        self.output.setWidgetResizable(True)
        self.output.setFrameShape(QFrame.Shape.NoFrame)
        self.output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.output.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.result_container = QWidget()
        self.result_container.setObjectName("translationResultContainer")
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(2, 2, 2, 2)
        self.result_layout.setSpacing(16)
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.output.setWidget(self.result_container)
        result_layout.addWidget(self.output, 1)
        layout.addWidget(result_card, 1)
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
        self._show_loading()
        worker = Worker(lambda: self._service_factory().translate(input_text))
        self._active_worker = worker
        worker.signals.succeeded.connect(self._show_result)
        worker.signals.failed.connect(self._show_error)
        worker.signals.finished.connect(self._finish_request)
        self._thread_pool.start(worker)

    def _show_empty_state(self) -> None:
        self._clear_result_layout()
        empty_label = QLabel("输入内容后按 Enter，即可查看翻译或词汇学习卡。")
        empty_label.setObjectName("translationEmptyState")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.result_layout.addWidget(empty_label, alignment=Qt.AlignmentFlag.AlignTop)

    def _show_loading(self) -> None:
        self._last_result = None
        self._last_result_columns = None
        self.status_changed.emit("正在翻译…", "loading")
        self._clear_result_layout()
        loading_label = QLabel("正在生成工作场景翻译，请稍候…")
        loading_label.setObjectName("translationEmptyState")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_layout.addWidget(loading_label, alignment=Qt.AlignmentFlag.AlignTop)

    def _finish_request(self) -> None:
        self._active_worker = None

    def _show_result(self, service_result: ServiceResult) -> None:
        result = service_result.value
        assert isinstance(result, LookupResult)
        self._last_result = result
        self._last_result_columns = None
        self._render_last_result()
        if service_result.save_warning:
            self.status_changed.emit(f"翻译完成，但未保存：{service_result.save_warning}", "warning")
        else:
            self.status_changed.emit("翻译完成，已保存学习记录。", "success")
        self.input_edit.clear()
        self.input_edit.setFocus()
        self.completed.emit()

    def _show_error(self, message: str) -> None:
        self._last_result = None
        self._last_result_columns = None
        self.status_changed.emit("翻译失败", "error")
        self._clear_result_layout()
        error_card = ResultCard("无法完成翻译", "standard")
        error_card.setObjectName("translationErrorCard")
        error_card.add_text(message)
        self.result_layout.addWidget(error_card, alignment=Qt.AlignmentFlag.AlignTop)

    def _speak(self, word: str, accent: str) -> None:
        if self._active_speech_worker is not None:
            return
        active_buttons = [button for button in self._pronunciation_buttons if button is not None]
        for button in active_buttons:
            button.setEnabled(False)
        self.status_changed.emit(f"正在朗读{'英式' if accent == 'british' else '美式'}发音…", "loading")
        worker = Worker(lambda: self._speech_service_factory().speak(word, accent))
        self._active_speech_worker = worker
        worker.signals.succeeded.connect(self._show_speech_result)
        worker.signals.failed.connect(self._show_speech_error)
        worker.signals.finished.connect(self._finish_speech)
        self._thread_pool.start(worker)

    def _show_speech_result(self, result: SpeechResult) -> None:
        self.status_changed.emit(result.message, "success")

    def _show_speech_error(self, message: str) -> None:
        self.status_changed.emit(message, "error")

    def _finish_speech(self) -> None:
        self._active_speech_worker = None
        for button in self._pronunciation_buttons:
            if button is not None and button.isVisible():
                button.setEnabled(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_result_layout)

    def _render_last_result(self) -> None:
        if self._last_result is None:
            return
        columns = 1 if self.output.viewport().width() < self.GRID_BREAKPOINT else 2
        if columns != self._last_result_columns:
            self._clear_result_layout()
            primary_cards, secondary_cards = self._build_result_cards(self._last_result)
            for primary_card in primary_cards:
                self.result_layout.addWidget(primary_card)
            if secondary_cards:
                grid_widget = QWidget()
                grid_widget.setObjectName("translationCardGrid")
                grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                grid = QGridLayout(grid_widget)
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setHorizontalSpacing(16)
                grid.setVerticalSpacing(16)
                for index, card in enumerate(secondary_cards):
                    row, column = divmod(index, columns)
                    grid.addWidget(card, row, column)
                for column in range(columns):
                    grid.setColumnStretch(column, 1)
                self.result_layout.addWidget(grid_widget, alignment=Qt.AlignmentFlag.AlignTop)
            self._last_result_columns = columns

    def _refresh_result_layout(self) -> None:
        self._render_last_result()

    def _build_result_cards(self, result: LookupResult) -> tuple[list[ResultCard], list[ResultCard]]:
        if result.word_details:
            details = result.word_details
            primary_card = ResultCard("基本释义", "primary")
            primary_card.add_text(details.english_word, "translationHeadword")
            self._pronunciation_buttons = list(
                primary_card.add_pronunciations(
                    details.british_ipa,
                    details.american_ipa,
                    details.english_word,
                    lambda: self._speak(details.english_word, "british"),
                    lambda: self._speak(details.english_word, "american"),
                )
            )
            primary_card.add_text(" / ".join(details.parts_of_speech), "translationMeta")
            primary_card.add_bullets(details.chinese_meanings)
            cards: list[ResultCard] = []
            if details.verb_forms:
                forms = details.verb_forms
                verb_card = ResultCard("动词变化")
                verb_card.add_key_values(
                    [
                        ("原形", forms.base),
                        ("第三人称单数", forms.third_person_singular),
                        ("过去式", forms.past),
                        ("过去分词", forms.past_participle),
                        ("现在分词", forms.present_participle),
                    ]
                )
                cards.append(verb_card)
            collocation_card = ResultCard("常见搭配")
            collocation_card.add_bullets(details.collocations)
            cards.append(collocation_card)
            example_card = ResultCard("例句")
            if details.examples:
                for example in details.examples:
                    example_card.add_example(example.english, example.chinese)
            else:
                example_card.add_text("暂无例句。", "translationEmptyState")
            cards.append(example_card)
            notes_card = ResultCard("使用提醒")
            notes_card.add_bullets(details.notes)
            cards.append(notes_card)
            return [primary_card], cards

        details = result.translation_details
        assert details is not None
        source_card = ResultCard("原文")
        source_card.setObjectName("translationSourceCard")
        source_card.add_text(result.source_text, "translationSourceText")
        primary_card = ResultCard("推荐工作表达", "primary")
        primary_card.add_text(details.primary_translation, "translationHero")
        rationale_card = ResultCard("为什么这样表达")
        rationale_card.add_bullets(details.translation_rationale)
        alternatives_card = ResultCard("其他可用表达")
        if details.alternatives:
            for alternative in details.alternatives:
                alternatives_card.add_alternative(alternative.expression, alternative.usage_note)
        else:
            alternatives_card.add_text("当前表达已适合直接使用。", "translationEmptyState")
        return [source_card, primary_card], [rationale_card, alternatives_card]

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
