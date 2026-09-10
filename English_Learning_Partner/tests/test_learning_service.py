from pathlib import Path

import pytest

from english_learning_partner.domain.errors import LocalModelResponseError
from english_learning_partner.domain.models import LookupResult
from english_learning_partner.services.learning_service import LearningService
from english_learning_partner.services.markdown_repository import MarkdownRepository


class FakeModelClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str]] = []

    def generate_json(self, model_name: str, prompt: str) -> dict:
        self.calls.append((model_name, prompt))
        return self.payload


def word_payload() -> dict:
    return {
        "source_language": "zh",
        "target_language": "en",
        "result_kind": "word_card",
        "word_details": {
            "english_word": "align",
            "british_ipa": "/əˈlaɪn/",
            "american_ipa": "/əˈlaɪn/",
            "chinese_meanings": ["对齐", "协调一致"],
            "parts_of_speech": ["动词"],
            "verb_forms": {
                "base": "align",
                "third_person_singular": "aligns",
                "past": "aligned",
                "past_participle": "aligned",
                "present_participle": "aligning",
            },
            "collocations": [
                "align on sth — 就某事达成一致",
                "align with sth — 与某项策略、目标或标准保持一致",
            ],
            "examples": [{"english": "Let's align on priorities.", "chinese": "让我们就优先级达成一致。"}],
            "notes": ["常与 on 搭配。"],
        },
        "translation_details": None,
    }


def work_translation_payload(source_language: str, target_language: str, text: str) -> dict:
    return {
        "source_language": source_language,
        "target_language": target_language,
        "result_kind": "work_translation",
        "word_details": None,
        "translation_details": {
            "primary_translation": text,
            "translation_rationale": ["采用简洁、明确的工作沟通语气。"],
            "alternatives": [{"expression": "Please confirm the priority by Friday.", "usage_note": "适用于需要明确截止时间时。"}],
        },
    }


def polish_payload(input_kind: str, grammar_issues: list[dict] | None = None) -> dict:
    return {
        "input_kind": input_kind,
        "polished_text": "Could you please share the latest status by Friday?",
        "alternatives": [
            {
                "expression": "Please share the latest status by Friday.",
                "usage_note": "更直接，适合 Teams 消息。",
            }
        ],
        "grammar_issues": grammar_issues or [],
    }


def test_chinese_word_creates_complete_word_card_and_saves_it(tmp_path: Path) -> None:
    client = FakeModelClient(word_payload())
    service = LearningService(client, MarkdownRepository(tmp_path), "gpt-5.4")

    response = service.translate("对齐")

    assert isinstance(response.value, LookupResult)
    assert response.value.word_details is not None
    assert response.value.word_details.english_word == "align"
    assert response.value.word_details.verb_forms.past == "aligned"
    assert response.saved_paths[0].exists()
    assert client.calls[0][0] == "gpt-5.4"


def test_chinese_sentence_creates_work_translation(tmp_path: Path) -> None:
    client = FakeModelClient(work_translation_payload("zh", "en", "Please confirm the priority by Friday."))

    response = LearningService(client, MarkdownRepository(tmp_path), "gpt-5.4").translate("请在周五前确认优先级")

    assert response.value.result_kind == "work_translation"
    assert response.value.translation_details.primary_translation == "Please confirm the priority by Friday."


def test_english_sentence_creates_chinese_work_translation(tmp_path: Path) -> None:
    client = FakeModelClient(work_translation_payload("en", "zh", "请分享最新进展。"))

    response = LearningService(client, MarkdownRepository(tmp_path), "gpt-5.4").lookup("Could you share the latest status?")

    assert response.value.source_language == "en"
    assert response.value.target_language == "zh"
    assert response.value.translation_details.primary_translation == "请分享最新进展。"


def test_rejects_conflicting_translation_branches(tmp_path: Path) -> None:
    payload = word_payload()
    payload["translation_details"] = work_translation_payload("zh", "en", "x")["translation_details"]

    with pytest.raises(LocalModelResponseError):
        LearningService(FakeModelClient(payload), MarkdownRepository(tmp_path), "gpt-5.4").translate("对齐")


def test_english_polish_writes_grammar_note_for_obvious_issue(tmp_path: Path) -> None:
    grammar_issues = [
        {
            "category": "prepositions",
            "original": "look forward hear",
            "correction": "look forward to hearing",
            "explanation": "缺少介词 to。",
            "rule": "look forward to 后接动名词。",
        }
    ]
    response = LearningService(
        FakeModelClient(polish_payload("english_polish", grammar_issues)),
        MarkdownRepository(tmp_path),
        "gpt-5.4",
    ).polish("I look forward hear from you.")

    assert response.value.input_kind == "english_polish"
    assert len(response.value.alternatives) == 1
    assert {path.parent.name for path in response.saved_paths} == {"polishes", "grammar-notes"}


def test_chinese_to_english_never_creates_grammar_note(tmp_path: Path) -> None:
    response = LearningService(
        FakeModelClient(polish_payload("translation_to_english")),
        MarkdownRepository(tmp_path),
        "gpt-5.4",
    ).polish("请周五前发最新状态")

    assert response.value.input_kind == "translation_to_english"
    assert len(response.saved_paths) == 1
    assert response.saved_paths[0].parent.name == "polishes"
    assert not (tmp_path / "grammar-notes").exists()


def test_rejects_grammar_issues_for_chinese_to_english(tmp_path: Path) -> None:
    payload = polish_payload("translation_to_english", [{
        "category": "word_choice",
        "original": "x",
        "correction": "y",
        "explanation": "z",
        "rule": "r",
    }])

    with pytest.raises(LocalModelResponseError):
        LearningService(FakeModelClient(payload), MarkdownRepository(tmp_path), "gpt-5.4").polish("请确认")
