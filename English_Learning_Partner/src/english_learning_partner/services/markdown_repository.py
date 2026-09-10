"""Human-readable Markdown storage for learning history."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import yaml

from ..domain.errors import RecordSaveError
from ..domain.models import (
    GrammarIssue,
    GrammarReviewSection,
    LookupResult,
    PolishResult,
    ReviewDetail,
    ReviewItem,
    ReviewLoadResult,
    ReviewSection,
)


class MarkdownRepository:
    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory

    def save_lookup(self, result: LookupResult, model_name: str) -> Path:
        metadata = self._base_metadata("translation", model_name)
        metadata.update(
            {
                "schema_version": 2,
                "source_text": result.source_text,
                "source_language": result.source_language,
                "target_language": result.target_language,
                "result_kind": result.result_kind,
                "review_board": "words" if self._is_word_review_item(result) else "history",
            }
        )
        if result.word_details:
            details = result.word_details
            metadata.update(
                {
                    "headword": details.english_word,
                    "chinese_meanings": details.chinese_meanings,
                    "parts_of_speech": details.parts_of_speech,
                }
            )
            lines = self._word_card_lines(result)
            title = details.english_word
        else:
            lines = self._work_translation_lines(result)
            title = result.source_text
        return self._save_record("queries", title, metadata, lines)

    def save_polish(self, result: PolishResult, model_name: str) -> Path:
        metadata = self._base_metadata("polish", model_name)
        metadata.update(
            {
                "schema_version": 3,
                "input_kind": result.input_kind,
                "style_profile": "concise-natural-email-teams",
                "grammar_categories": sorted({issue.category for issue in result.grammar_issues}),
            }
        )
        lines = [
            "# 英文工作表达",
            "",
            "## 原始内容",
            result.original_text,
            "",
            "## 英文表达",
            result.polished_text,
            "",
            "## 其他翻译候选",
            *(
                [f"- **{item.expression}**：{item.usage_note}" for item in result.alternatives]
                or ["- 无"]
            ),
        ]
        if result.input_kind == "english_polish" and result.grammar_issues:
            lines.extend(
                [
                    "",
                    "## 可复习的语法与表达问题",
                    *self._grammar_issue_lines(result),
                ]
            )
        return self._save_record("polishes", "polish", metadata, lines)

    def save_grammar_notes(self, result: PolishResult, source_path: Path) -> list[Path]:
        if not result.grammar_issues:
            return []
        grouped: dict[str, list] = {}
        for issue in result.grammar_issues:
            grouped.setdefault(self._safe_slug(issue.category) or "other", []).append(issue)
        saved_paths = []
        for category, issues in grouped.items():
            target = self._ensure_directory("grammar-notes") / f"{category}.md"
            content = target.read_text(encoding="utf-8") if target.exists() else self._grammar_note_title(category)
            timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
            record_key = uuid4().hex[:8]
            section = [
                f"## {timestamp} · {record_key}",
                f"来源：[{source_path.name}](../polishes/{source_path.name})",
                "",
            ]
            for issue in issues:
                issue_key = uuid4().hex[:8]
                section.extend(
                    [
                        f"### {issue_key}",
                        f"- **错误**：{issue.original}",
                        f"- **改正**：{issue.correction}",
                        f"- **说明**：{issue.explanation}",
                        f"- **规则**：{issue.rule}",
                        "",
                    ]
                )
            self._atomic_write(target, content.rstrip() + "\n\n" + "\n".join(section).rstrip() + "\n")
            saved_paths.append(target)
        return saved_paths

    def list_review_items(self) -> ReviewLoadResult:
        items: list[ReviewItem] = []
        warnings: list[str] = []
        self._load_query_items(items, warnings)
        self._load_polish_items(items, warnings)
        self._load_grammar_items(items, warnings)
        return ReviewLoadResult(sorted(items, key=lambda item: item.created_at, reverse=True), warnings)

    def list_word_review_items(self) -> ReviewLoadResult:
        loaded = self.list_review_items()
        return ReviewLoadResult([item for item in loaded.items if item.record_type == "词汇"], loaded.warnings)

    def list_grammar_review_items(self) -> ReviewLoadResult:
        """List one item per grammar category; individual entries are managed in its detail view."""
        loaded = self.list_review_items()
        return ReviewLoadResult(
            [item for item in loaded.items if item.record_type == "语法笔记"],
            loaded.warnings,
        )

    def list_grammar_notes(self) -> list[Path]:
        directory = self.root_directory / "grammar-notes"
        return sorted(directory.glob("*.md")) if directory.exists() else []

    @staticmethod
    def read_markdown(path: Path) -> str:
        """Read the original Markdown record, including its metadata."""
        return path.read_text(encoding="utf-8")

    def read_record_body(self, path: Path) -> str:
        """Read the user-facing Markdown body without YAML front matter."""
        content = self.read_markdown(path)
        if not content.startswith("---\n"):
            return content
        parts = content.split("---", 2)
        if len(parts) != 3:
            raise ValueError("记录的 front matter 格式不正确。")
        return parts[2].lstrip("\r\n")

    def read_review_detail(
        self,
        path: Path,
        record_type: str,
        record_key: str | None = None,
    ) -> ReviewDetail:
        """Parse an application record into user-facing sections without metadata."""
        body = self.read_record_body(path).replace("\r\n", "\n")
        if record_type == "语法笔记":
            detail = self._parse_grammar_detail(body, path.stem)
            if record_key:
                detail = ReviewDetail(
                    detail.title,
                    grammar_sections=[
                        section for section in detail.grammar_sections if section.record_key == record_key
                    ],
                )
            return detail
        return self._parse_standard_detail(body, record_type)

    def _parse_standard_detail(self, body: str, record_type: str) -> ReviewDetail:
        lines = body.splitlines()
        title = "学习记录"
        sections: list[ReviewSection] = []
        current_title: str | None = None
        current_lines: list[str] = []
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip() or title
            elif line.startswith("## "):
                if current_title is not None:
                    sections.append(ReviewSection(current_title, self._clean_section_lines(current_lines)))
                current_title = line[3:].strip()
                current_lines = []
            elif current_title is not None:
                current_lines.append(line)
        if current_title is not None:
            sections.append(ReviewSection(current_title, self._clean_section_lines(current_lines)))
        if record_type == "词汇":
            sections = [section for section in sections if section.title != "原始输入"]
            title = ""
        return ReviewDetail(title=title, sections=sections)

    def _parse_grammar_detail(self, body: str, category: str) -> ReviewDetail:
        title = category.replace("_", " ").title()
        groups: list[GrammarReviewSection] = []
        current_time: datetime | None = None
        current_record_key = ""
        current_issue_key = ""
        current_issues: list[GrammarIssue] = []
        current_values: dict[str, str] = {}

        def finish_issue() -> None:
            nonlocal current_values, current_issue_key
            fields = {key: current_values.get(key, "").strip() for key in ("错误", "改正", "说明", "规则")}
            if fields["错误"] and fields["改正"]:
                issue_key = current_issue_key or f"legacy:{current_record_key}:{len(current_issues)}"
                current_issues.append(
                    GrammarIssue(
                        category,
                        fields["错误"],
                        fields["改正"],
                        fields["说明"],
                        fields["规则"],
                        issue_key,
                    )
                )
            current_values = {}
            current_issue_key = ""

        def finish_group() -> None:
            nonlocal current_time, current_record_key, current_issue_key, current_issues
            finish_issue()
            if current_time is not None and current_issues:
                groups.append(GrammarReviewSection(current_time, current_record_key, current_issues))
            current_time = None
            current_record_key = ""
            current_issue_key = ""
            current_issues = []

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if line.startswith("# "):
                title = line[2:].strip() or title
                continue
            if line.startswith("## "):
                finish_group()
                heading = line[3:].strip()
                timestamp_text, separator, current_record_key = heading.partition(" · ")
                try:
                    current_time = datetime.fromisoformat(timestamp_text)
                except ValueError:
                    current_time = None
                    current_record_key = ""
                if not separator:
                    current_record_key = timestamp_text
                continue
            if line.startswith("### "):
                finish_issue()
                current_issue_key = line[4:].strip()
                continue
            if line.startswith("来源：") or line == "---" or not line:
                continue
            for key in ("错误", "改正", "说明", "规则"):
                marker = f"- **{key}**："
                if line.startswith(marker):
                    if key == "错误" and current_values:
                        finish_issue()
                    current_values[key] = line[len(marker):].strip()
                    break
        finish_group()
        return ReviewDetail(title=title, grammar_sections=sorted(groups, key=lambda group: group.created_at, reverse=True))

    @staticmethod
    def _clean_section_lines(lines: list[str]) -> list[str]:
        return [line.strip() for line in lines if line.strip()]

    def delete_review_item(
        self,
        path: Path,
        record_type: str,
        record_key: str | None = None,
    ) -> None:
        """Delete a word card or one dated grammar-note record safely."""
        folders = {"词汇": "queries", "语法笔记": "grammar-notes"}
        folder = folders.get(record_type)
        if folder is None:
            raise RecordSaveError("当前记录类型不支持删除。")
        try:
            root = self.root_directory.resolve()
            target = path.resolve()
            expected_directory = (root / folder).resolve()
            if target.parent != expected_directory or target.suffix.lower() != ".md":
                raise RecordSaveError("只能删除学习资料目录中选定的 Markdown 记录。")
            if record_type == "语法笔记":
                if not record_key:
                    raise RecordSaveError("未找到需要删除的语法问题。")
                self._delete_grammar_issue(target, record_key)
            else:
                target.unlink()
        except RecordSaveError:
            raise
        except OSError as error:
            raise RecordSaveError(f"无法删除学习记录：{path.name}") from error

    def _delete_grammar_issue(self, path: Path, issue_key: str) -> None:
        content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if issue_key.startswith("legacy:"):
            updated = self._delete_legacy_grammar_issue(content, issue_key)
        else:
            match = re.search(rf"(?m)^### {re.escape(issue_key)}$", content)
            if match is None:
                raise RecordSaveError("未找到需要删除的语法问题。")
            next_heading = re.search(r"(?m)^(?:### |## )", content[match.end():])
            end = match.end() + next_heading.start() if next_heading else len(content)
            updated = content[:match.start()] + content[end:]
        updated = re.sub(r"\n{3,}", "\n\n", updated).rstrip() + "\n"
        remaining = self._parse_grammar_detail(updated, path.stem).grammar_sections
        if remaining:
            self._atomic_write(path, updated)
        else:
            path.unlink()

    @staticmethod
    def _delete_legacy_grammar_issue(content: str, issue_key: str) -> str:
        try:
            _, section_key, index_text = issue_key.split(":", 2)
            index = int(index_text)
        except ValueError as error:
            raise RecordSaveError("未找到需要删除的语法问题。") from error
        sections = list(re.finditer(r"(?m)^## ([^\n]+)$", content))
        section_match = next((match for match in sections if match.group(1).strip() == section_key), None)
        if section_match is None:
            raise RecordSaveError("未找到需要删除的语法问题。")
        next_section = next((match for match in sections if match.start() > section_match.start()), None)
        section_end = next_section.start() if next_section else len(content)
        section_content = content[section_match.end():section_end]
        errors = list(re.finditer(r"(?m)^- \*\*错误\*\*：", section_content))
        if index >= len(errors):
            raise RecordSaveError("未找到需要删除的语法问题。")
        start = section_match.end() + errors[index].start()
        end = section_match.end() + (errors[index + 1].start() if index + 1 < len(errors) else len(section_content))
        return content[:start] + content[end:]

    @staticmethod
    def _is_word_review_item(result: LookupResult) -> bool:
        if result.result_kind == "word_card":
            return True
        english_words = re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)?", result.source_text)
        return result.source_language == "en" and 1 < len(english_words) < 5

    def _load_query_items(self, items: list[ReviewItem], warnings: list[str]) -> None:
        directory = self.root_directory / "queries"
        if not directory.exists():
            return
        for path in directory.glob("*.md"):
            try:
                metadata = self._read_front_matter(path)
                created_at = self._metadata_time(metadata)
                is_new_record = metadata.get("schema_version") == 2
                result_kind = metadata.get("result_kind")
                is_word_item = metadata.get("review_board") == "words" or not (
                    is_new_record and result_kind == "work_translation"
                )
                if not is_word_item:
                    title = str(metadata.get("source_text") or "工作场景翻译")
                    record_type = "翻译记录"
                    categories = [str(metadata.get("source_language", "")), str(metadata.get("target_language", ""))]
                else:
                    title = str(metadata.get("headword") or metadata.get("term") or metadata.get("source_text") or "词汇")
                    record_type = "词汇"
                    categories = self._metadata_list(metadata, "chinese_meanings") + self._metadata_list(metadata, "parts_of_speech")
                items.append(ReviewItem(record_type, title, created_at, path, categories))
            except (OSError, ValueError, yaml.YAMLError, TypeError) as error:
                warnings.append(f"已跳过损坏的记录：{path.name}（{error}）")

    def _load_polish_items(self, items: list[ReviewItem], warnings: list[str]) -> None:
        directory = self.root_directory / "polishes"
        if not directory.exists():
            return
        for path in directory.glob("*.md"):
            try:
                metadata = self._read_front_matter(path)
                items.append(
                    ReviewItem(
                        "润色记录",
                        "英文工作表达润色",
                        self._metadata_time(metadata),
                        path,
                        self._metadata_list(metadata, "grammar_categories"),
                    )
                )
            except (OSError, ValueError, yaml.YAMLError, TypeError) as error:
                warnings.append(f"已跳过损坏的记录：{path.name}（{error}）")

    def _load_grammar_items(self, items: list[ReviewItem], warnings: list[str]) -> None:
        directory = self.root_directory / "grammar-notes"
        if not directory.exists():
            return
        for path in directory.glob("*.md"):
            try:
                category = path.stem
                items.append(
                    ReviewItem(
                        "语法笔记",
                        category.replace("_", " ").title(),
                        datetime.fromtimestamp(path.stat().st_mtime).astimezone(),
                        path,
                        [category],
                    )
                )
            except OSError as error:
                warnings.append(f"已跳过无法读取的语法笔记：{path.name}（{error}）")

    def _word_card_lines(self, result: LookupResult) -> list[str]:
        details = result.word_details
        assert details is not None
        lines = [
            f"# {details.english_word}",
            "",
            "## 原始输入",
            result.source_text,
            "",
            "## 音标",
            f"- 英式：{details.british_ipa}",
            f"- 美式：{details.american_ipa}",
            "",
            "## 中文意思",
            *self._bullets(details.chinese_meanings),
            "",
            "## 词性",
            *self._bullets(details.parts_of_speech),
        ]
        if details.verb_forms:
            forms = details.verb_forms
            lines.extend(
                [
                    "",
                    "## 动词变化",
                    f"- 原形：{forms.base}",
                    f"- 第三人称单数：{forms.third_person_singular}",
                    f"- 过去式：{forms.past}",
                    f"- 过去分词：{forms.past_participle}",
                    f"- 现在分词：{forms.present_participle}",
                ]
            )
        lines.extend(
            [
                "",
                "## 常见搭配",
                *self._bullets(details.collocations),
                "",
                "## 例句",
                *self._examples(details.examples),
                "",
                "## 使用提醒",
                *self._bullets(details.notes),
            ]
        )
        return lines

    def _work_translation_lines(self, result: LookupResult) -> list[str]:
        details = result.translation_details
        assert details is not None
        return [
            "# 工作场景翻译",
            "",
            "## 原始输入",
            result.source_text,
            "",
            "## 推荐表达",
            details.primary_translation,
            "",
            "## 翻译理由",
            *self._bullets(details.translation_rationale),
            "",
            "## 其他可用表达",
            *([f"- **{item.expression}**：{item.usage_note}" for item in details.alternatives] or ["- 无"]),
        ]

    def _save_record(self, folder: str, title: str, metadata: dict, lines: list[str]) -> Path:
        identifier = metadata["id"]
        filename = f"{identifier}-{self._safe_slug(title) or folder}.md"
        target = self._ensure_directory(folder) / filename
        front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
        self._atomic_write(target, f"---\n{front_matter}\n---\n\n" + "\n".join(lines).rstrip() + "\n")
        return target

    def _base_metadata(self, record_type: str, model_name: str) -> dict:
        now = datetime.now().astimezone()
        return {
            "id": f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}",
            "type": record_type,
            "created_at": now.isoformat(timespec="seconds"),
            "model": model_name,
            "app_version": "0.2.0",
        }

    def _ensure_directory(self, folder: str) -> Path:
        target = self.root_directory / folder
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise RecordSaveError(f"无法创建学习资料目录：{target}") from error
        return target

    @staticmethod
    def _safe_slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug[:48]

    @staticmethod
    def _bullets(values: list[str]) -> list[str]:
        return [f"- {value}" for value in values] or ["- 无"]

    @staticmethod
    def _examples(examples: list) -> list[str]:
        return [f"- **{item.english}**  \\n  {item.chinese}" for item in examples] or ["- 无"]

    @staticmethod
    def _grammar_issue_lines(result: PolishResult) -> list[str]:
        if not result.grammar_issues:
            return ["- 未发现需要记录的明显语法或工作表达问题。"]
        lines = []
        for issue in result.grammar_issues:
            lines.extend(
                [
                    f"### {issue.category}",
                    f"- **原句片段**：{issue.original}",
                    f"- **建议改为**：{issue.correction}",
                    f"- **说明**：{issue.explanation}",
                    f"- **通用规则**：{issue.rule}",
                    "",
                ]
            )
        return lines

    @staticmethod
    def _grammar_note_title(category: str) -> str:
        return f"# {category.replace('_', ' ').title()}\n"

    @staticmethod
    def _metadata_time(metadata: dict) -> datetime:
        raw_time = metadata.get("created_at")
        return raw_time if isinstance(raw_time, datetime) else datetime.fromisoformat(str(raw_time))

    @staticmethod
    def _metadata_list(metadata: dict, key: str) -> list[str]:
        value = metadata.get(key, [])
        return [str(item) for item in value] if isinstance(value, list) else []

    @staticmethod
    def _read_front_matter(path: Path) -> dict:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            raise ValueError("缺少 front matter")
        _, raw, _ = content.split("---", 2)
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError("front matter 不是对象")
        return data

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=target.parent, delete=False, newline="\n"
            ) as temp:
                temp.write(content)
                temp_path = Path(temp.name)
            os.replace(temp_path, target)
        except OSError as error:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise RecordSaveError(f"无法保存学习记录：{target.name}") from error
