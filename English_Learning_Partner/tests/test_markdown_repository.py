from pathlib import Path

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


def word_card(source_text: str = "对齐") -> LookupResult:
    return LookupResult(
        source_text=source_text,
        source_language="zh",
        target_language="en",
        result_kind="word_card",
        word_details=WordDetails(
            english_word="align",
            british_ipa="/əˈlaɪn/",
            american_ipa="/əˈlaɪn/",
            chinese_meanings=["对齐", "协调一致"],
            parts_of_speech=["动词"],
            verb_forms=VerbForms("align", "aligns", "aligned", "aligned", "aligning"),
            collocations=["align on priorities — 就优先级达成一致"],
            examples=[Example("Let's align on priorities.", "让我们就优先级达成一致。")],
            notes=["常与 on 搭配。"],
        ),
    )


def polish_result(input_kind: str, grammar_issues: list[GrammarIssue] | None = None) -> PolishResult:
    return PolishResult(
        original_text="请在周五前分享最新状态",
        polished_text="Could you please share the latest status by Friday?",
        input_kind=input_kind,
        alternatives=[
            TranslationAlternative(
                "Please share the latest status by Friday.", "更直接，适合 Teams 消息。"
            )
        ],
        grammar_issues=grammar_issues or [],
    )


def test_word_card_is_saved_and_appears_only_in_word_review(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)

    path = repository.save_lookup(word_card(), "gpt-5.4")

    content = path.read_text(encoding="utf-8")
    assert "schema_version: 2" in content
    assert "review_board: words" in content
    assert "## 音标" in content
    assert "## 动词变化" in content
    assert "## 常见搭配" in content
    assert "## 工作场景常用方法" not in content
    assert repository.list_word_review_items().items[0].title == "align"
    assert repository.list_review_items().items[0].record_type == "词汇"


def test_short_english_phrase_is_in_word_review(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)
    result = LookupResult(
        source_text="follow up on",
        source_language="en",
        target_language="zh",
        result_kind="work_translation",
        translation_details=WorkTranslation(
            primary_translation="跟进某件事。",
            translation_rationale=["短语作为整体学习。"],
            alternatives=[],
        ),
    )

    path = repository.save_lookup(result, "gpt-5.4")

    assert "review_board: words" in path.read_text(encoding="utf-8")
    assert repository.list_word_review_items().items[0].title == "follow up on"


def test_work_translation_is_in_history_but_not_word_review(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)
    result = LookupResult(
        source_text="请在周五前确认优先级",
        source_language="zh",
        target_language="en",
        result_kind="work_translation",
        translation_details=WorkTranslation(
            primary_translation="Please confirm the priority by Friday.",
            translation_rationale=["明确行动和截止时间。"],
            alternatives=[],
        ),
    )

    path = repository.save_lookup(result, "gpt-5.4")

    assert "## 推荐表达" in path.read_text(encoding="utf-8")
    assert not repository.list_word_review_items().items
    assert repository.list_review_items().items[0].record_type == "翻译记录"


def test_legacy_lookup_is_compatible_with_word_review(tmp_path: Path) -> None:
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "legacy.md").write_text(
        "---\nid: old\ntype: lookup\ncreated_at: 2026-01-01T09:00:00+08:00\nterm: follow up\n---\n\n# follow up\n",
        encoding="utf-8",
    )

    items = MarkdownRepository(tmp_path).list_word_review_items().items

    assert len(items) == 1
    assert items[0].title == "follow up"


def test_translation_to_english_record_has_candidates_without_grammar_section(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)

    path = repository.save_polish(polish_result("translation_to_english"), "gpt-5.4")
    content = path.read_text(encoding="utf-8")

    assert "schema_version: 3" in content
    assert "input_kind: translation_to_english" in content
    assert "## 英文表达" in content
    assert "## 其他翻译候选" in content
    assert "## 推荐英文工作表达" not in content
    assert "## 润色理由" not in content
    assert "## 可复习的语法与表达问题" not in content
    assert "id:" not in repository.read_record_body(path)


def test_english_polish_grammar_note_is_available_and_can_be_deleted(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)
    issue = GrammarIssue(
        category="prepositions",
        original="look forward hear",
        correction="look forward to hearing",
        explanation="look forward to 后接名词或动名词。",
        rule="固定搭配中的 to 是介词。",
    )
    result = polish_result("english_polish", [issue])

    polish_path = repository.save_polish(result, "gpt-5.4")
    note_paths = repository.save_grammar_notes(result, polish_path)

    assert [path.name for path in note_paths] == ["prepositions.md"]
    grammar_item = repository.list_grammar_review_items().items[0]
    assert grammar_item.record_type == "语法笔记"
    detail = repository.read_review_detail(note_paths[0], "语法笔记")
    issue_key = detail.grammar_sections[0].issues[0].record_key
    assert issue_key
    repository.delete_review_item(note_paths[0], "语法笔记", issue_key)
    assert not note_paths[0].exists()


def test_deleting_one_grammar_record_keeps_other_records(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)
    first_issue = GrammarIssue("tense", "She go", "She goes", "第三人称单数错误。", "主语为第三人称单数时动词加 -s。")
    second_issue = GrammarIssue("tense", "They goes", "They go", "复数主语错误。", "复数主语使用动词原形。")
    first_path = repository.save_polish(polish_result("english_polish", [first_issue]), "gpt-5.4")
    repository.save_grammar_notes(polish_result("english_polish", [first_issue]), first_path)
    second_path = repository.save_polish(polish_result("english_polish", [second_issue]), "gpt-5.4")
    repository.save_grammar_notes(polish_result("english_polish", [second_issue]), second_path)

    items = repository.list_grammar_review_items().items
    assert len(items) == 1
    detail = repository.read_review_detail(items[0].path, "语法笔记")
    assert len(detail.grammar_sections) == 2
    deleted_issue_key = detail.grammar_sections[0].issues[0].record_key
    repository.delete_review_item(items[0].path, "语法笔记", deleted_issue_key)

    remaining_detail = repository.read_review_detail(items[0].path, "语法笔记")
    assert len(remaining_detail.grammar_sections) == 1
    assert remaining_detail.grammar_sections[0].issues[0].record_key != deleted_issue_key


def test_word_record_can_be_deleted(tmp_path: Path) -> None:
    repository = MarkdownRepository(tmp_path)
    path = repository.save_lookup(word_card(), "gpt-5.4")

    repository.delete_review_item(path, "词汇")

    assert not path.exists()
    assert not repository.list_word_review_items().items


def test_damaged_record_is_skipped(tmp_path: Path) -> None:
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "broken.md").write_text("not front matter", encoding="utf-8")

    review = MarkdownRepository(tmp_path).list_review_items()

    assert not review.items
    assert review.warnings
