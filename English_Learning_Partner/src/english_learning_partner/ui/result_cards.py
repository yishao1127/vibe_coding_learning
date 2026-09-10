"""Native Qt cards used by the translation result view."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ResultCard(QFrame):
    """A titled card that renders model text as literal, selectable Qt text."""

    def __init__(self, title: str, variant: str = "standard", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(
            "translationPrimaryCard" if variant == "primary" else "translationSectionCard"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(16, 14, 16, 15)
        self.content_layout.setSpacing(9)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("translationCardTitle")
        self.content_layout.addWidget(self.title_label)

    @staticmethod
    def _breakable_text(value: str) -> str:
        """Keep model text literal; Qt wraps at URL punctuation when space is constrained."""
        return value

    def add_text(self, value: str, style: str = "translationCardText") -> QLabel:
        label = QLabel(self._breakable_text(value))
        label.setObjectName(style)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.content_layout.addWidget(label)
        return label

    def add_pronunciations(
        self,
        british_ipa: str,
        american_ipa: str,
        word: str,
        on_speak_british: Callable[[], None],
        on_speak_american: Callable[[], None],
    ) -> tuple[QToolButton, QToolButton]:
        """Add British and American IPA controls on one compact row."""
        row = QWidget()
        row.setObjectName("pronunciationRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        british_label = self._pronunciation_label("英式", british_ipa)
        british_button = self._pronunciation_button("英式", word, on_speak_british)
        american_label = self._pronunciation_label("美式", american_ipa)
        american_button = self._pronunciation_button("美式", word, on_speak_american)
        row_layout.addWidget(british_label)
        row_layout.addWidget(british_button)
        row_layout.addSpacing(12)
        row_layout.addWidget(american_label)
        row_layout.addWidget(american_button)
        row_layout.addStretch()
        self.content_layout.addWidget(row)
        return british_button, american_button

    @staticmethod
    def _pronunciation_label(accent_label: str, ipa: str) -> QLabel:
        label = QLabel(f"{accent_label} {ipa}")
        label.setObjectName("translationMeta")
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _pronunciation_button(
        self,
        accent_label: str,
        word: str,
        on_speak: Callable[[], None],
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName("pronunciationButton")
        button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        button.setToolTip(f"朗读{accent_label}发音")
        button.setAccessibleName(f"朗读{accent_label}发音：{word}")
        button.setAutoRaise(True)
        button.clicked.connect(on_speak)
        return button

    def add_bullets(self, values: Iterable[str], empty_message: str = "暂无补充内容。") -> None:
        non_empty_values = [value for value in values if value.strip()]
        if not non_empty_values:
            self.add_text(empty_message, "translationEmptyState")
            return
        for value in non_empty_values:
            row = QLabel(f"• {value}")
            row.setObjectName("translationBullet")
            row.setTextFormat(Qt.TextFormat.PlainText)
            row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.setWordWrap(True)
            self.content_layout.addWidget(row)

    def add_key_values(self, values: Iterable[tuple[str, str]]) -> None:
        for key, value in values:
            row = QWidget()
            row.setObjectName("translationKeyValueRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 3, 0, 3)
            row_layout.setSpacing(10)
            key_label = QLabel(key)
            key_label.setObjectName("translationKey")
            value_label = QLabel(value)
            value_label.setObjectName("translationValue")
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_label.setWordWrap(True)
            row_layout.addWidget(key_label, 0)
            row_layout.addWidget(value_label, 1)
            self.content_layout.addWidget(row)

    def add_example(self, english: str, chinese: str) -> None:
        example = QFrame()
        example.setObjectName("translationMicroCard")
        example_layout = QVBoxLayout(example)
        example_layout.setContentsMargins(11, 9, 11, 9)
        example_layout.setSpacing(3)
        english_label = QLabel(english)
        english_label.setObjectName("translationExampleEnglish")
        english_label.setTextFormat(Qt.TextFormat.PlainText)
        english_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        english_label.setWordWrap(True)
        chinese_label = QLabel(chinese)
        chinese_label.setObjectName("translationExampleChinese")
        chinese_label.setTextFormat(Qt.TextFormat.PlainText)
        chinese_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        chinese_label.setWordWrap(True)
        example_layout.addWidget(english_label)
        example_layout.addWidget(chinese_label)
        self.content_layout.addWidget(example)

    def add_alternative(self, expression: str, usage_note: str) -> None:
        alternative = QFrame()
        alternative.setObjectName("translationMicroCard")
        alternative_layout = QVBoxLayout(alternative)
        alternative_layout.setContentsMargins(11, 9, 11, 9)
        alternative_layout.setSpacing(3)
        expression_label = QLabel(self._breakable_text(expression))
        expression_label.setObjectName("translationAlternativeExpression")
        expression_label.setTextFormat(Qt.TextFormat.PlainText)
        expression_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        expression_label.setWordWrap(True)
        expression_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        note_label = QLabel(self._breakable_text(usage_note))
        note_label.setObjectName("translationAlternativeNote")
        note_label.setTextFormat(Qt.TextFormat.PlainText)
        note_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        note_label.setWordWrap(True)
        note_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        alternative_layout.addWidget(expression_label)
        alternative_layout.addWidget(note_label)
        self.content_layout.addWidget(alternative)

    def add_issue(
        self,
        category: str,
        original: str,
        correction: str,
        explanation: str,
        rule: str,
        on_delete: Callable[[], None] | None = None,
    ) -> None:
        """Add one clearly separated grammar or expression issue."""
        issue = QFrame()
        issue.setObjectName("translationIssueCard")
        issue_layout = QVBoxLayout(issue)
        issue_layout.setContentsMargins(12, 10, 12, 11)
        issue_layout.setSpacing(5)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        badge = QLabel(category.replace("_", " ").title())
        badge.setObjectName("translationIssueBadge")
        header.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
        header.addStretch()
        if on_delete is not None:
            menu_button = QToolButton()
            menu_button.setObjectName("issueMenuButton")
            menu_button.setText("⋯")
            menu_button.setToolTip("更多操作")
            menu_button.setAccessibleName("此问题的更多操作")
            menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QMenu(menu_button)
            delete_action = menu.addAction("删除")
            delete_action.triggered.connect(on_delete)
            menu_button.setMenu(menu)
            header.addWidget(menu_button)
        issue_layout.addLayout(header)
        for label, value, style in (
            ("原句片段", original, "translationIssueText"),
            ("建议改为", correction, "translationIssueCorrection"),
            ("说明", explanation, "translationIssueText"),
            ("通用规则", rule, "translationIssueText"),
        ):
            caption = QLabel(label)
            caption.setObjectName("translationIssueCaption")
            content = QLabel(value)
            content.setObjectName(style)
            content.setTextFormat(Qt.TextFormat.PlainText)
            content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content.setWordWrap(True)
            issue_layout.addWidget(caption)
            issue_layout.addWidget(content)
        self.content_layout.addWidget(issue)
