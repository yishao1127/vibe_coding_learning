"""Typed data exchanged between services and the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Example:
    english: str
    chinese: str


@dataclass(frozen=True)
class VerbForms:
    base: str
    third_person_singular: str
    past: str
    past_participle: str
    present_participle: str


@dataclass(frozen=True)
class WordDetails:
    english_word: str
    british_ipa: str
    american_ipa: str
    chinese_meanings: list[str]
    parts_of_speech: list[str]
    verb_forms: VerbForms | None
    collocations: list[str]
    examples: list[Example]
    notes: list[str]


@dataclass(frozen=True)
class TranslationAlternative:
    expression: str
    usage_note: str


@dataclass(frozen=True)
class WorkTranslation:
    primary_translation: str
    translation_rationale: list[str]
    alternatives: list[TranslationAlternative]


@dataclass(frozen=True)
class LookupResult:
    source_text: str
    source_language: str
    target_language: str
    result_kind: str
    word_details: WordDetails | None = None
    translation_details: WorkTranslation | None = None


@dataclass(frozen=True)
class GrammarIssue:
    category: str
    original: str
    correction: str
    explanation: str
    rule: str
    record_key: str | None = None


@dataclass(frozen=True)
class PolishResult:
    original_text: str
    polished_text: str
    input_kind: str
    alternatives: list[TranslationAlternative] = field(default_factory=list)
    grammar_issues: list[GrammarIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ServiceResult:
    value: LookupResult | PolishResult
    saved_paths: list[Path] = field(default_factory=list)
    save_warning: str | None = None


@dataclass(frozen=True)
class ReviewItem:
    record_type: str
    title: str
    created_at: datetime
    path: Path
    categories: list[str] = field(default_factory=list)
    record_key: str | None = None


@dataclass(frozen=True)
class ReviewLoadResult:
    items: list[ReviewItem]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewSection:
    title: str
    lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GrammarReviewSection:
    created_at: datetime
    record_key: str
    issues: list[GrammarIssue] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewDetail:
    title: str
    sections: list[ReviewSection] = field(default_factory=list)
    grammar_sections: list[GrammarReviewSection] = field(default_factory=list)
