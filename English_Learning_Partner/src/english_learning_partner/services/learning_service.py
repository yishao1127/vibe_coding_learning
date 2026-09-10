"""Business workflows for translation, polishing, and automatic learning records."""

from __future__ import annotations

from collections.abc import Mapping

from ..domain.errors import LocalModelResponseError, RecordSaveError
from ..domain.models import (
    Example,
    GrammarIssue,
    LookupResult,
    PolishResult,
    ServiceResult,
    TranslationAlternative,
    VerbForms,
    WordDetails,
    WorkTranslation,
)
from .markdown_repository import MarkdownRepository
from .openai_responses_client import OpenAIResponsesClient
from .prompts import polish_prompt, translate_prompt


class LearningService:
    def __init__(
        self,
        model_client: OpenAIResponsesClient,
        repository: MarkdownRepository,
        model_name: str,
    ) -> None:
        self.model_client = model_client
        self.repository = repository
        self.model_name = model_name

    def translate(self, text: str) -> ServiceResult:
        clean_text = self._validate_text(text, "请输入要翻译的中文、英文或中英混合内容。", 12_000)
        result = self._parse_translation(clean_text, self._generate_with_retry(translate_prompt(clean_text)))
        try:
            saved_path = self.repository.save_lookup(result, self.model_name)
        except RecordSaveError as error:
            return ServiceResult(result, save_warning=str(error))
        return ServiceResult(result, saved_paths=[saved_path])

    def lookup(self, text: str) -> ServiceResult:
        """Backward-compatible alias for the former English-only lookup action."""
        return self.translate(text)

    def polish(self, text: str, tone: str | None = None) -> ServiceResult:
        """Create a concise English work expression; ``tone`` is ignored for compatibility."""
        clean_text = self._validate_text(text, "请输入需要整理为英文工作表达的内容。", 12_000)
        result = self._parse_polish(clean_text, self._generate_with_retry(polish_prompt(clean_text)))
        try:
            polish_path = self.repository.save_polish(result, self.model_name)
            grammar_paths = (
                self.repository.save_grammar_notes(result, polish_path)
                if result.input_kind == "english_polish"
                else []
            )
        except RecordSaveError as error:
            return ServiceResult(result, save_warning=str(error))
        return ServiceResult(result, saved_paths=[polish_path, *grammar_paths])

    def _generate_with_retry(self, prompt: str) -> dict:
        try:
            return self.model_client.generate_json(self.model_name, prompt)
        except LocalModelResponseError as first_error:
            try:
                return self.model_client.generate_json(
                    self.model_name,
                    f"{prompt}\n\n上一次输出格式无效。请务必只返回完整、合法的 JSON 对象。",
                )
            except LocalModelResponseError:
                raise first_error

    @staticmethod
    def _validate_text(text: str, empty_message: str, limit: int) -> str:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError(empty_message)
        if len(clean_text) > limit:
            raise ValueError(f"输入内容不能超过 {limit:,} 个字符。")
        return clean_text

    @classmethod
    def _parse_translation(cls, source_text: str, payload: Mapping[str, object]) -> LookupResult:
        source_language = cls._enum(payload, "source_language", {"zh", "en", "mixed"})
        target_language = cls._enum(payload, "target_language", {"zh", "en"})
        result_kind = cls._enum(payload, "result_kind", {"word_card", "work_translation"})
        word_value = payload.get("word_details")
        translation_value = payload.get("translation_details")
        if result_kind == "word_card":
            if not isinstance(word_value, Mapping) or translation_value is not None:
                raise LocalModelResponseError("本地模型返回的词汇卡结构不正确。")
            return LookupResult(
                source_text=source_text,
                source_language=source_language,
                target_language=target_language,
                result_kind=result_kind,
                word_details=cls._word_details(word_value),
            )
        if not isinstance(translation_value, Mapping) or word_value is not None:
            raise LocalModelResponseError("本地模型返回的工作翻译结构不正确。")
        return LookupResult(
            source_text=source_text,
            source_language=source_language,
            target_language=target_language,
            result_kind=result_kind,
            translation_details=cls._work_translation(translation_value),
        )

    @classmethod
    def _word_details(cls, value: Mapping[str, object]) -> WordDetails:
        parts_of_speech = cls._string_list(value.get("parts_of_speech"), "parts_of_speech")
        verb_value = value.get("verb_forms")
        is_verb = any("verb" in part.lower() or "动词" in part for part in parts_of_speech)
        if is_verb and not isinstance(verb_value, Mapping):
            raise LocalModelResponseError("动词词汇卡必须包含完整词形变化。")
        if verb_value is not None and not isinstance(verb_value, Mapping):
            raise LocalModelResponseError("本地模型字段格式不正确：verb_forms。")
        return WordDetails(
            english_word=cls._required_text(value, "english_word"),
            british_ipa=cls._required_text(value, "british_ipa"),
            american_ipa=cls._required_text(value, "american_ipa"),
            chinese_meanings=cls._string_list(value.get("chinese_meanings"), "chinese_meanings"),
            parts_of_speech=parts_of_speech,
            verb_forms=cls._verb_forms(verb_value) if isinstance(verb_value, Mapping) else None,
            collocations=cls._string_list(value.get("collocations"), "collocations"),
            examples=cls._examples(value.get("examples")),
            notes=cls._string_list(value.get("notes"), "notes"),
        )

    @classmethod
    def _verb_forms(cls, value: Mapping[str, object]) -> VerbForms:
        return VerbForms(
            base=cls._required_text(value, "base"),
            third_person_singular=cls._required_text(value, "third_person_singular"),
            past=cls._required_text(value, "past"),
            past_participle=cls._required_text(value, "past_participle"),
            present_participle=cls._required_text(value, "present_participle"),
        )

    @classmethod
    def _work_translation(cls, value: Mapping[str, object]) -> WorkTranslation:
        rationales = cls._string_list(value.get("translation_rationale"), "translation_rationale")
        if not rationales:
            raise LocalModelResponseError("工作翻译至少需要一条翻译理由。")
        return WorkTranslation(
            primary_translation=cls._required_text(value, "primary_translation"),
            translation_rationale=rationales,
            alternatives=cls._alternatives(value.get("alternatives")),
        )

    @classmethod
    def _alternatives(cls, value: object) -> list[TranslationAlternative]:
        if not isinstance(value, list):
            raise LocalModelResponseError("本地模型字段格式不正确：alternatives。")
        alternatives = []
        for item in value:
            if not isinstance(item, Mapping):
                raise LocalModelResponseError("本地模型字段格式不正确：alternatives。")
            alternatives.append(
                TranslationAlternative(
                    expression=cls._required_text(item, "expression"),
                    usage_note=cls._required_text(item, "usage_note"),
                )
            )
        return alternatives

    @classmethod
    def _parse_polish(cls, original_text: str, payload: Mapping[str, object]) -> PolishResult:
        input_kind = cls._enum(payload, "input_kind", {"translation_to_english", "english_polish"})
        alternatives = cls._alternatives(payload.get("alternatives"))
        grammar_issues = cls._grammar_issues(payload.get("grammar_issues"))
        if input_kind == "translation_to_english" and grammar_issues:
            raise LocalModelResponseError("中文转英文结果不应包含语法复习问题。")
        return PolishResult(
            original_text=original_text,
            polished_text=cls._required_text(payload, "polished_text"),
            input_kind=input_kind,
            alternatives=alternatives,
            grammar_issues=grammar_issues,
        )

    @staticmethod
    def _required_text(payload: Mapping[str, object], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LocalModelResponseError(f"本地模型缺少必填字段：{key}。")
        return value.strip()

    @staticmethod
    def _enum(payload: Mapping[str, object], key: str, values: set[str]) -> str:
        value = payload.get(key)
        if value not in values:
            raise LocalModelResponseError(f"本地模型字段值不正确：{key}。")
        return str(value)

    @staticmethod
    def _string_list(value: object, field_name: str) -> list[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise LocalModelResponseError(f"本地模型字段格式不正确：{field_name}。")
        return [item.strip() for item in value if item.strip()]

    @classmethod
    def _examples(cls, value: object) -> list[Example]:
        if not isinstance(value, list):
            raise LocalModelResponseError("本地模型字段格式不正确：examples。")
        examples = []
        for item in value:
            if not isinstance(item, Mapping):
                raise LocalModelResponseError("本地模型字段格式不正确：examples。")
            examples.append(Example(cls._required_text(item, "english"), cls._required_text(item, "chinese")))
        return examples

    @staticmethod
    def _normalize_grammar_category(category: str) -> str:
        normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "冠词": "articles",
            "时态": "tense",
            "介词": "prepositions",
            "主谓一致": "subject_verb_agreement",
            "可数性": "countability",
            "词汇选择": "word_choice",
            "商务写作": "business_writing",
            "其他": "other",
        }
        return aliases.get(normalized, normalized or "other")

    @classmethod
    def _grammar_issues(cls, value: object) -> list[GrammarIssue]:
        if not isinstance(value, list):
            raise LocalModelResponseError("本地模型字段格式不正确：grammar_issues。")
        issues = []
        for item in value:
            if not isinstance(item, Mapping):
                raise LocalModelResponseError("本地模型字段格式不正确：grammar_issues。")
            issues.append(
                GrammarIssue(
                    category=cls._normalize_grammar_category(cls._required_text(item, "category")),
                    original=cls._required_text(item, "original"),
                    correction=cls._required_text(item, "correction"),
                    explanation=cls._required_text(item, "explanation"),
                    rule=cls._required_text(item, "rule"),
                )
            )
        return issues
