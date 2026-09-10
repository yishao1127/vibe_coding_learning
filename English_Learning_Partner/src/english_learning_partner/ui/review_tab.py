"""Separate word and grammar review boards with native card details."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QMenu,
    QScrollArea,
    QSplitter,
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..domain.models import ReviewDetail, ReviewItem, ReviewLoadResult, ReviewSection
from ..services.markdown_repository import MarkdownRepository
from ..services.speech_service import SpeechResult, SpeechService
from .result_cards import ResultCard
from .workers import Worker


class ReviewBoard(QWidget):
    """Searchable review board that keeps storage metadata out of the reading view."""

    status_changed = Signal(str, str)

    def __init__(
        self,
        repository_factory: Callable[[], MarkdownRepository],
        loader: Callable[[], ReviewLoadResult],
        placeholder: str,
        empty_message: str,
        allow_delete: bool = False,
        speech_service_factory: Callable[[], SpeechService] = SpeechService,
    ) -> None:
        super().__init__()
        self._repository_factory = repository_factory
        self._loader = loader
        self._speech_service_factory = speech_service_factory
        self._thread_pool = QThreadPool.globalInstance()
        self._active_speech_worker: Worker | None = None
        self._pronunciation_buttons: list = []
        self._items: list[ReviewItem] = []
        self._empty_message = empty_message
        self._allow_delete = allow_delete
        self._build_ui(placeholder)

    def _build_ui(self, placeholder: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        filter_card = QFrame()
        filter_card.setObjectName("reviewCard")
        controls = QHBoxLayout(filter_card)
        controls.setContentsMargins(14, 10, 14, 10)
        controls.setSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(placeholder)
        self.search_edit.textChanged.connect(self._render_items)
        controls.addWidget(self.search_edit, 1)
        self.reload_button = QPushButton("刷新")
        self.reload_button.clicked.connect(self.reload)
        controls.addWidget(self.reload_button)
        layout.addWidget(filter_card)

        content_card = QFrame()
        content_card.setObjectName("reviewCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter()
        self.item_list = QListWidget()
        self.item_list.setObjectName("reviewList")
        self.item_list.currentItemChanged.connect(self._show_current_item)
        splitter.addWidget(self.item_list)

        self.detail_view = QScrollArea()
        self.detail_view.setObjectName("reviewDetail")
        self.detail_view.setWidgetResizable(True)
        self.detail_view.setFrameShape(QFrame.Shape.NoFrame)
        self.detail_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_container = QWidget()
        self.detail_container.setObjectName("reviewDetailContainer")
        self.detail_layout = QVBoxLayout(self.detail_container)
        self.detail_layout.setContentsMargins(2, 2, 2, 2)
        self.detail_layout.setSpacing(16)
        self.detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.detail_view.setWidget(self.detail_container)
        splitter.addWidget(self.detail_view)
        splitter.setSizes([350, 750])
        content_layout.addWidget(splitter, 1)
        layout.addWidget(content_card, 1)

        self.status_label = QLabel()
        self.status_label.setObjectName("hintLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self._show_empty_detail()

    def reload(self) -> None:
        loaded = self._loader()
        self._items = loaded.items
        message = f"共 {len(self._items)} 条记录。"
        if loaded.warnings:
            message += " " + "；".join(loaded.warnings)
        self.status_label.setText(message)
        self._render_items()

    def _render_items(self) -> None:
        current_path = self._selected_path()
        query = self.search_edit.text().strip().lower()
        self.item_list.clear()
        for item in self._items:
            searchable = " ".join([item.title, *item.categories]).lower()
            if query and query not in searchable:
                continue
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, str(item.path))
            list_item.setData(Qt.ItemDataRole.UserRole + 1, item.record_type)
            list_item.setData(Qt.ItemDataRole.UserRole + 2, item.title)
            list_item.setData(Qt.ItemDataRole.UserRole + 3, item.record_key)
            row_widget = self._create_list_row(item)
            list_item.setSizeHint(row_widget.sizeHint())
            self.item_list.addItem(list_item)
            self.item_list.setItemWidget(list_item, row_widget)
            if item.path == current_path:
                self.item_list.setCurrentItem(list_item)
        if self.item_list.count() and not self.item_list.currentItem():
            self.item_list.setCurrentRow(0)
        if not self.item_list.count():
            self._show_empty_detail()

    def _create_list_row(self, item: ReviewItem) -> QWidget:
        row = QWidget()
        row.setObjectName("reviewListRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 10, 8, 10)
        layout.setSpacing(8)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        title = QLabel(item.title)
        title.setObjectName("reviewListTitle")
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        timestamp = item.created_at.strftime("%Y-%m-%d %H:%M")
        if item.record_type == "语法笔记":
            timestamp = f"最近学习：{timestamp}"
        elif item.record_type != "词汇":
            timestamp = f"{item.record_type} · {timestamp}"
        metadata = QLabel(timestamp)
        metadata.setObjectName("reviewListMetadata")
        metadata.setTextFormat(Qt.TextFormat.PlainText)
        text_layout.addWidget(title)
        text_layout.addWidget(metadata)
        layout.addLayout(text_layout, 1)
        if self._allow_delete and item.record_type == "词汇":
            menu_button = self._create_delete_menu_button(
                item.path,
                item.record_type,
                item.record_key,
                item.title,
            )
            menu_button.setObjectName("reviewItemMenuButton")
            layout.addWidget(menu_button, alignment=Qt.AlignmentFlag.AlignTop)
        return row

    def _create_delete_menu_button(
        self,
        path: Path,
        record_type: str,
        record_key: str | None,
        title: str,
    ) -> QToolButton:
        button = QToolButton()
        button.setText("⋯")
        button.setToolTip("更多操作")
        button.setAccessibleName(f"{title} 的更多操作")
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        action = menu.addAction("删除")
        action.triggered.connect(
            lambda _checked=False, path=path, record_type=record_type, record_key=record_key, title=title: self._delete_record(
                path, record_type, record_key, title
            )
        )
        button.setMenu(menu)
        return button

    def _selected_path(self) -> Path | None:
        item = self.item_list.currentItem()
        return Path(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _show_current_item(self, item: QListWidgetItem | None) -> None:
        if item is None:
            self._show_empty_detail()
            return
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        record_type = str(item.data(Qt.ItemDataRole.UserRole + 1))
        record_key = item.data(Qt.ItemDataRole.UserRole + 3)
        try:
            detail = self._repository_factory().read_review_detail(path, record_type, record_key)
            self._render_detail(detail, path)
        except (OSError, ValueError) as error:
            self._show_message(f"无法读取记录：\n{error}")

    def _render_detail(self, detail: ReviewDetail, source_path: Path) -> None:
        self._clear_detail_layout()
        if detail.grammar_sections:
            self._render_grammar_detail(detail, source_path)
        else:
            self._render_standard_detail(detail)
        self.detail_layout.addStretch()

    def _render_standard_detail(self, detail: ReviewDetail) -> None:
        sections = detail.sections
        if not sections:
            self._show_message(self._empty_message)
            return

        if not detail.title:
            self._render_word_detail(sections)
            return

        primary_card = ResultCard(detail.title, "primary")
        for line in sections[0].lines:
            primary_card.add_text(self._strip_markdown(line), "translationHero")
        self.detail_layout.addWidget(primary_card)
        for section in sections[1:]:
            card = ResultCard(section.title)
            self._add_section_content(card, section)
            self.detail_layout.addWidget(card)

    def _render_word_detail(self, sections: list[ReviewSection]) -> None:
        summary_titles = {"音标", "中文意思", "词性"}
        summary_sections = [section for section in sections if section.title in summary_titles]
        remaining_sections = [section for section in sections if section.title not in summary_titles]
        self._pronunciation_buttons = []
        if summary_sections:
            summary_card = ResultCard("基本释义", "primary")
            pronunciation = next((section for section in summary_sections if section.title == "音标"), None)
            british_ipa, american_ipa = self._pronunciation_values(pronunciation)
            word = self._current_word_title()
            if british_ipa and american_ipa and word:
                self._pronunciation_buttons = list(
                    summary_card.add_pronunciations(
                        british_ipa,
                        american_ipa,
                        word,
                        lambda: self._speak(word, "british"),
                        lambda: self._speak(word, "american"),
                    )
                )
            elif pronunciation:
                summary_card.add_bullets(
                    [self._strip_markdown(line) for line in pronunciation.lines]
                )
            for section in summary_sections:
                if section.title != "音标":
                    summary_card.add_bullets([self._strip_markdown(line) for line in section.lines])
            self.detail_layout.addWidget(summary_card)
        for section in remaining_sections:
            card = ResultCard(section.title)
            self._add_section_content(card, section)
            self.detail_layout.addWidget(card)

    @staticmethod
    def _pronunciation_values(section: ReviewSection | None) -> tuple[str | None, str | None]:
        if section is None:
            return None, None
        values: dict[str, str] = {}
        for line in section.lines:
            clean_line = ReviewBoard._strip_markdown(line)
            for label in ("英式：", "美式："):
                if clean_line.startswith(label):
                    values[label] = clean_line.removeprefix(label).strip()
        return values.get("英式："), values.get("美式：")

    def _current_word_title(self) -> str | None:
        item = self.item_list.currentItem()
        if item is None or item.data(Qt.ItemDataRole.UserRole + 1) != "词汇":
            return None
        return str(item.data(Qt.ItemDataRole.UserRole + 2))

    def _speak(self, word: str, accent: str) -> None:
        if self._active_speech_worker is not None:
            return
        for button in self._pronunciation_buttons:
            button.setEnabled(False)
        accent_label = "英式" if accent == "british" else "美式"
        self.status_changed.emit(f"正在朗读{accent_label}发音…", "loading")
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
            if button.isVisible():
                button.setEnabled(True)

    def _render_grammar_detail(self, detail: ReviewDetail, source_path: Path) -> None:
        for group in detail.grammar_sections:
            date_card = ResultCard(group.created_at.strftime("%Y-%m-%d %H:%M"), "primary")
            for issue in group.issues:
                date_card.add_issue(
                    issue.category,
                    issue.original,
                    issue.correction,
                    issue.explanation,
                    issue.rule,
                    lambda _checked=False, key=issue.record_key, title=detail.title, path=source_path: self._delete_grammar_record(
                        path, key, title
                    ),
                )
            self.detail_layout.addWidget(date_card)

    def _delete_grammar_record(self, path: Path, record_key: str | None, title: str) -> None:
        if not record_key:
            return
        self._delete_record(path, "语法笔记", record_key, title)

    def _delete_record(
        self,
        path: Path,
        record_type: str,
        record_key: str | None,
        title: str,
    ) -> None:
        try:
            self._repository_factory().delete_review_item(path, record_type, record_key)
        except Exception as error:
            QMessageBox.warning(self, "删除失败", str(error) or "无法删除所选记录。")
            return
        self.reload()

    @staticmethod
    def _add_section_content(card: ResultCard, section: ReviewSection) -> None:
        if section.title not in {"英文表达", "中文意思", "音标", "词性"}:
            card.title_label.setText(section.title)
        elif card.title_label.text() != "基本释义":
            card.title_label.setText(section.title)
        lines = [ReviewBoard._strip_markdown(line) for line in section.lines]
        if section.title in {"音标", "中文意思", "词性"}:
            card.add_bullets(lines)
        else:
            card.add_bullets(lines)

    @staticmethod
    def _strip_markdown(line: str) -> str:
        clean = line.removeprefix("- ").replace("**", "")
        return clean.replace("\\", "").strip()

    def _show_empty_detail(self) -> None:
        self._show_message(self._empty_message)

    def _show_message(self, message: str) -> None:
        self._clear_detail_layout()
        label = QLabel(message)
        label.setObjectName("translationEmptyState")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.detail_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignTop)

    def _clear_detail_layout(self) -> None:
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()



class ReviewTab(QWidget):
    """Review the user's vocabulary cards and recurrent writing mistakes separately."""

    status_changed = Signal(str, str)

    def __init__(self, repository_factory: Callable[[], MarkdownRepository]) -> None:
        super().__init__()
        self._repository_factory = repository_factory
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 16, 28, 22)
        layout.setSpacing(8)

        self.boards = QTabWidget()
        self.boards.setObjectName("reviewTabs")
        self.word_board = ReviewBoard(
            self._repository_factory,
            lambda: self._repository_factory().list_word_review_items(),
            "按英文单词、中文义或词性筛选…",
            "还没有词汇卡。请先在“翻译”中查询中文或英文单词。",
            allow_delete=True,
        )
        self.grammar_board = ReviewBoard(
            self._repository_factory,
            lambda: self._repository_factory().list_grammar_review_items(),
            "按语法类别筛选，例如 tense 或 prepositions…",
            "还没有语法笔记。润色发现明显问题后会自动汇总到这里。",
        )
        self.history_board = ReviewBoard(
            self._repository_factory,
            lambda: self._repository_factory().list_review_items(),
            "按内容、类别或记录类型筛选…",
            "还没有学习记录。",
        )
        self.word_board.status_changed.connect(self.status_changed)
        self.history_board.status_changed.connect(self.status_changed)
        self.boards.addTab(self.word_board, "单词复习")
        self.boards.addTab(self.grammar_board, "语法复习")
        self.boards.addTab(self.history_board, "全部记录")
        layout.addWidget(self.boards, 1)

    def reload(self) -> None:
        self.word_board.reload()
        self.grammar_board.reload()
        self.history_board.reload()
