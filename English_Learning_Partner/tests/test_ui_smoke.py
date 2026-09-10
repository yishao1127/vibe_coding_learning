from PySide6.QtWidgets import QGridLayout, QLabel, QMessageBox, QScrollArea, QToolButton

from english_learning_partner.domain.models import (
    Example,
    GrammarIssue,
    LookupResult,
    PolishResult,
    TranslationAlternative,
    VerbForms,
    WordDetails,
    WorkTranslation,
)
from english_learning_partner.services.markdown_repository import MarkdownRepository
from english_learning_partner.ui.lookup_tab import LookupTab
from english_learning_partner.ui.polish_tab import PolishTab
from english_learning_partner.ui.result_cards import ResultCard
from english_learning_partner.ui.review_tab import ReviewTab


def work_translation() -> LookupResult:
    return LookupResult(
        source_text="请在周五前确认优先级",
        source_language="zh",
        target_language="en",
        result_kind="work_translation",
        translation_details=WorkTranslation(
            primary_translation="Please confirm the priority by Friday.",
            translation_rationale=["明确行动和截止时间。"],
            alternatives=[
                TranslationAlternative(
                    "Could you confirm the priority by Friday?", "语气更协作。"
                )
            ],
        ),
    )


def word_card() -> LookupResult:
    return LookupResult(
        source_text="分类",
        source_language="zh",
        target_language="en",
        result_kind="word_card",
        word_details=WordDetails(
            english_word="triage",
            british_ipa="/ˈtriːɑːʒ/",
            american_ipa="/ˈtriːɑːʒ/",
            chinese_meanings=["分类处理", "初步评估"],
            parts_of_speech=["动词"],
            verb_forms=VerbForms("triage", "triages", "triaged", "triaged", "triaging"),
            collocations=["triage incoming feedback — 分类处理收到的反馈"],
            examples=[Example("Let's triage the incoming feedback.", "让我们先分类处理收到的反馈。")],
            notes=["常用于产品问题和客户反馈的初步处理。"],
        ),
    )


def polish_translation() -> PolishResult:
    return PolishResult(
        original_text="请确认最新状态",
        polished_text="Please confirm the latest status.",
        input_kind="translation_to_english",
        alternatives=[TranslationAlternative("Could you confirm the latest status?", "语气更协作。")],
    )


def english_polish() -> PolishResult:
    return PolishResult(
        original_text="I look forward hear from you.",
        polished_text="I look forward to hearing from you.",
        input_kind="english_polish",
        alternatives=[],
        grammar_issues=[
            GrammarIssue(
                category="prepositions",
                original="look forward hear",
                correction="look forward to hearing",
                explanation="缺少介词 to。",
                rule="look forward to 后接动名词。",
            )
        ],
    )


def test_learning_tabs_start_with_separate_review_boards(qtbot, tmp_path) -> None:
    lookup = LookupTab(lambda: object())
    polish = PolishTab(lambda: object())
    review = ReviewTab(lambda: MarkdownRepository(tmp_path))

    for widget in (lookup, polish, review):
        qtbot.addWidget(widget)
        widget.show()
        assert widget.isVisible()

    assert isinstance(lookup.output, QScrollArea)
    assert lookup.output.objectName() == "translationResult"
    assert not hasattr(polish, "polish_button")
    assert not hasattr(polish, "tone_combo")
    assert isinstance(polish.output, QScrollArea)
    assert polish.output.objectName() == "polishResult"
    assert [review.boards.tabText(index) for index in range(review.boards.count())] == [
        "单词复习",
        "语法复习",
        "全部记录",
    ]
    assert not hasattr(review.word_board, "delete_button")
    assert not hasattr(review.grammar_board, "delete_button")
    assert not hasattr(review.history_board, "delete_button")


def test_work_translation_is_rendered_as_native_cards(qtbot) -> None:
    lookup = LookupTab(lambda: object())
    qtbot.addWidget(lookup)
    lookup.resize(1000, 700)
    lookup.show()
    lookup._last_result = work_translation()
    lookup._render_last_result()

    cards = lookup.result_container.findChildren(ResultCard)
    titles = [card.title_label.text() for card in cards]

    assert titles == ["原文", "推荐工作表达", "为什么这样表达", "其他可用表达"]
    assert cards[0].findChildren(QLabel)[1].text() == "请在周五前确认优先级"
    grid = lookup.result_container.findChildren(QGridLayout)[0]
    assert grid.columnCount() == 2
    assert grid.count() == 2


def test_word_modules_use_native_two_column_grid(qtbot) -> None:
    lookup = LookupTab(lambda: object())
    qtbot.addWidget(lookup)
    lookup.resize(1100, 760)
    lookup.show()
    lookup._last_result = word_card()
    lookup._render_last_result()

    cards = lookup.result_container.findChildren(ResultCard)
    titles = [card.title_label.text() for card in cards]
    grid = lookup.result_container.findChildren(QGridLayout)[0]

    assert titles == ["基本释义", "动词变化", "常见搭配", "例句", "使用提醒"]
    assert grid.columnCount() == 2
    assert grid.count() == 4
    buttons = cards[0].findChildren(QToolButton, "pronunciationButton")
    assert [button.toolTip() for button in buttons] == ["朗读英式发音", "朗读美式发音"]
    assert buttons[0].accessibleName() == "朗读英式发音：triage"


def test_word_modules_reflow_to_one_column_when_narrow(qtbot) -> None:
    lookup = LookupTab(lambda: object())
    qtbot.addWidget(lookup)
    lookup.resize(500, 700)
    lookup.show()
    lookup._last_result = word_card()
    lookup._render_last_result()

    grid = lookup.result_container.findChildren(QGridLayout)[0]

    assert grid.columnCount() == 1
    assert grid.count() == 4


def test_custom_input_hint_is_not_a_system_placeholder(qtbot) -> None:
    lookup = LookupTab(lambda: object())
    qtbot.addWidget(lookup)

    assert lookup.input_edit.placeholderText() == ""
    assert lookup.input_edit._hint_text == lookup.INPUT_HINT


def test_polish_translation_uses_native_cards_without_grammar_section(qtbot) -> None:
    polish = PolishTab(lambda: object())
    qtbot.addWidget(polish)
    polish.resize(1000, 700)
    polish.show()
    polish._last_result = polish_translation()
    polish._render_last_result()

    cards = polish.result_container.findChildren(ResultCard)

    assert [card.title_label.text() for card in cards] == ["英文表达", "其他翻译候选"]
    assert not polish.result_container.findChildren(QGridLayout)
    assert "Please confirm the latest status." in [label.text() for label in cards[0].findChildren(QLabel)]


def test_english_polish_uses_native_grammar_issue_card(qtbot) -> None:
    polish = PolishTab(lambda: object())
    qtbot.addWidget(polish)
    polish.resize(1000, 700)
    polish.show()
    polish._last_result = english_polish()
    polish._render_last_result()

    cards = polish.result_container.findChildren(ResultCard)

    assert [card.title_label.text() for card in cards] == ["英文表达", "其他翻译候选", "可复习的问题"]
    assert "look forward to hearing" in [label.text() for label in cards[-1].findChildren(QLabel)]


def test_review_detail_hides_metadata_and_word_source_input(qtbot, tmp_path) -> None:
    repository = MarkdownRepository(tmp_path)
    repository.save_lookup(word_card(), "gpt-5.4")
    review = ReviewTab(lambda: repository)
    qtbot.addWidget(review)
    review.show()

    cards = review.word_board.detail_container.findChildren(ResultCard)
    card_titles = [card.title_label.text() for card in cards]
    detail_text = "\n".join(label.text() for label in review.word_board.detail_container.findChildren(QLabel))

    assert "基本释义" in card_titles
    assert "原始输入" not in card_titles
    assert "id:" not in detail_text
    pronunciation_buttons = review.word_board.detail_container.findChildren(QToolButton, "pronunciationButton")
    assert [button.toolTip() for button in pronunciation_buttons] == ["朗读英式发音", "朗读美式发音"]
    row = review.word_board.item_list.itemWidget(review.word_board.item_list.currentItem())
    assert row.findChild(QLabel, "reviewListTitle").text() == "triage"
    assert row.findChild(QLabel, "reviewListMetadata").text().startswith("20")


def test_word_row_menu_deletes_its_own_record_not_current_selection(qtbot, tmp_path, monkeypatch) -> None:
    repository = MarkdownRepository(tmp_path)
    first_path = repository.save_lookup(word_card(), "gpt-5.4")
    second = word_card()
    second = LookupResult(
        source_text="follow up",
        source_language=second.source_language,
        target_language=second.target_language,
        result_kind=second.result_kind,
        word_details=WordDetails(
            "follow up",
            second.word_details.british_ipa,
            second.word_details.american_ipa,
            second.word_details.chinese_meanings,
            second.word_details.parts_of_speech,
            second.word_details.verb_forms,
            second.word_details.collocations,
            second.word_details.examples,
            second.word_details.notes,
        ),
    )
    second_path = repository.save_lookup(second, "gpt-5.4")
    review = ReviewTab(lambda: repository)
    qtbot.addWidget(review)
    review.show()
    review.word_board.item_list.setCurrentRow(0)
    second_row = next(
        review.word_board.item_list.itemWidget(review.word_board.item_list.item(index))
        for index in range(review.word_board.item_list.count())
        if review.word_board.item_list.itemWidget(review.word_board.item_list.item(index))
        .findChild(QLabel, "reviewListTitle")
        .text()
        == "follow up"
    )
    button = second_row.findChild(QToolButton, "reviewItemMenuButton")
    monkeypatch.setattr(
        "english_learning_partner.ui.review_tab.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    button.menu().actions()[0].trigger()

    assert first_path.exists()
    assert not second_path.exists()


def test_grammar_issue_menu_deletes_bound_issue(qtbot, tmp_path, monkeypatch) -> None:
    repository = MarkdownRepository(tmp_path)
    issues = [
        GrammarIssue("tense", "She go", "She goes", "第三人称单数错误。", "第三人称单数动词加 -s。"),
        GrammarIssue("tense", "They goes", "They go", "复数主语错误。", "复数主语使用动词原形。"),
    ]
    result = PolishResult("Bad text", "Correct text", "english_polish", grammar_issues=issues)
    polish_path = repository.save_polish(result, "gpt-5.4")
    note_path = repository.save_grammar_notes(result, polish_path)[0]
    review = ReviewTab(lambda: repository)
    qtbot.addWidget(review)
    review.show()
    review.boards.setCurrentWidget(review.grammar_board)
    issue_buttons = review.grammar_board.detail_container.findChildren(QToolButton, "issueMenuButton")
    assert len(issue_buttons) == 2
    assert all(button.menu().actions()[0].text() == "删除" for button in issue_buttons)
    monkeypatch.setattr(
        "english_learning_partner.ui.review_tab.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    issue_buttons[1].menu().actions()[0].trigger()

    detail = repository.read_review_detail(note_path, "语法笔记")
    remaining_issues = [issue for group in detail.grammar_sections for issue in group.issues]
    assert len(remaining_issues) == 1


def test_model_text_is_displayed_as_literal_plain_text() -> None:
    card = ResultCard("测试")
    label = card.add_text("a < b & c")

    assert label.text() == "a < b & c"
