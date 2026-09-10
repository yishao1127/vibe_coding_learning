"""Prompts and strict JSON contracts for the personal work-English assistant."""

from __future__ import annotations

import json

TRANSLATE_SCHEMA = {
    "source_language": "zh|en|mixed",
    "target_language": "zh|en",
    "result_kind": "word_card|work_translation",
    "word_details": {
        "english_word": "英文单词",
        "british_ipa": "/英式 IPA 音标/",
        "american_ipa": "/美式 IPA 音标/",
        "chinese_meanings": ["中文义"],
        "parts_of_speech": ["词性"],
        "verb_forms": {
            "base": "原形",
            "third_person_singular": "第三人称单数",
            "past": "过去式",
            "past_participle": "过去分词",
            "present_participle": "现在分词",
        },
        "collocations": ["英文搭配、介词搭配或句型 — 中文说明"],
        "examples": [{"english": "英文例句", "chinese": "中文翻译"}],
        "notes": ["用词提醒或易混点"],
    },
    "translation_details": {
        "primary_translation": "目标语言的推荐工作表达",
        "translation_rationale": ["采用这一表达的理由"],
        "alternatives": [{"expression": "替代译法", "usage_note": "适用场景或语气差异"}],
    },
}

POLISH_SCHEMA = {
    "input_kind": "translation_to_english|english_polish",
    "polished_text": "可直接发送的英文工作表达",
    "alternatives": [{"expression": "其他英文候选", "usage_note": "适用场景或细微差异"}],
    "grammar_issues": [
        {
            "category": "articles|tense|prepositions|subject_verb_agreement|countability|word_choice|business_writing|other",
            "original": "原始有问题的英文片段",
            "correction": "建议英文改法",
            "explanation": "本次明显问题的中文解释",
            "rule": "可复习的通用中文规则",
        }
    ],
}

WORK_CONTEXT = """用户是微软公司的产品经理。所有表达都服务于真实工作沟通，常见场景包括跨团队协作、优先级讨论、路线图、干系人同步、客户反馈、评审会议和行动项。不得编造项目事实、数据、承诺、组织名称或人员信息。"""


def translate_prompt(text: str) -> str:
    return f"""你是面向微软产品经理的中英工作沟通与学习助手。
{WORK_CONTEXT}

自动判断以下输入是中文、英文还是中英混合，并只返回一个合法 JSON 对象；不要 Markdown、代码围栏或额外文字。必须严格符合此结构，所有字段必须出现：
{json.dumps(TRANSLATE_SCHEMA, ensure_ascii=False)}

分流规则：
1. 输入是单个英文单词，或少于 5 个英文单词且可作为整体学习的固定词组/短语（例如 follow up on、align with、in line with）时，result_kind 必须为 word_card，word_details 必须是对象，translation_details 必须为 null。中文输入若自然且明确地对应一个单个英文词法单元或这类固定短语，也使用 word_card。只有完整句子、较长短语或不适合作为词块复习的表达才使用 work_translation。
2. 单词卡必须同时提供 british_ipa 与 american_ipa，均使用标准 IPA（如英式 /əˈlaɪn/、美式 /əˈlaɪn/）；两者相同时也必须分别填写。chinese_meanings 和 parts_of_speech 必须非空。parts_of_speech 只写词性标签（如“名词”“动词”），不要在该字段重复释义；所有中文释义按词性合并写入 chinese_meanings，避免同一含义重复。仅当词性包含动词时，verb_forms 填写原形、第三人称单数、过去式、过去分词和现在分词；非动词时 verb_forms 为 null。
3. collocations 必须是非空数组，每项严格写为“英文搭配或句型 — 中文说明”。对动词提供 3–5 条真实、自然且适合工作沟通的高价值搭配，优先覆盖动词+宾语、双宾语或替代表达、动词+介词、动词+非谓语、动词+从句。用 sb、sth、to do、doing、that + clause 表示句型，并说明宾语、介词或结构限制。若同一词存在多种支配结构，必须并列比较，例如“provide sb sth / provide sth to sb / provide sb with sth — 均表示向某人提供某物；with 结构强调提供所需内容”。不要为凑数量编造不自然或不成立的结构；非动词保留常见搭配，但不强制这些句型。examples 要贴合产品管理工作语境。
4. 输入为中文短语或句子时，优先给出自然、专业的英文工作表达；输入为英文短语或句子时，给出准确自然的中文工作表达。此时 result_kind 必须为 work_translation，translation_details 必须是对象，word_details 必须为 null。
5. 翻译卡必须含主译文、至少一条翻译理由，以及可为空的替代表达列表；替代表达应解释适用语气或场景。
6. 对中英混合输入，保留产品名、团队名和专业术语，并按用户主要意图选择目标语言。

用户输入：
{text}"""


def polish_prompt(text: str) -> str:
    return f"""你是面向微软产品经理的英文工作沟通助手。
{WORK_CONTEXT}

将下方中文、英文或中英混合内容整理为简洁、自然、适合邮件和 Teams 消息直接发送的英文表达。只返回合法 JSON，不要 Markdown、代码围栏或额外文字。所有说明使用简体中文，严格使用以下结构且每个字段必须存在：
{json.dumps(POLISH_SCHEMA, ensure_ascii=False)}

规则：
- polished_text 必须是完整、可直接发送的英文工作表达，保留原始意图且不新增事实。
- 中文或以中文为主的输入：input_kind 必须为 translation_to_english，grammar_issues 必须为 []；不要把翻译取舍记作语法问题。
- 以英文为主的输入：input_kind 必须为 english_polish。仅当存在明显语法错误、固定搭配错误、明显影响理解或不合适的工作沟通表达时，才在 grammar_issues 中记录；单纯风格偏好不要记录。
- alternatives 提供 0–3 个有实际差异、可直接使用的英文候选；usage_note 解释其适用场景或细微差异。

原文：
{text}"""
