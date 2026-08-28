// merge.js — 阶段二：把新内容与既有页面正文合并重写，保持全文可读、连贯、有条理
//
// 不是简单追加，而是让 LLM 看到"旧正文 + 新片段"后，产出一份重新组织过的
// 完整新正文（Markdown），并在末尾维护一个"来源"小节记录溯源信息。

import { complete } from '../llm-client.js';

const MERGE_SCHEMA = {
  name: 'merge_result',
  schema: {
    type: 'object',
    properties: {
      skip: { type: 'boolean', description: '若新内容与已有正文完全重复、无新增信息，设为 true 并跳过改写' },
      newContent: { type: 'string', description: '合并重写后的完整 Markdown 正文；skip 为 true 时可为空字符串' },
      changeSummary: { type: 'string', description: '一句话说明这次做了什么改动' },
    },
    required: ['skip', 'newContent', 'changeSummary'],
    additionalProperties: false,
  },
};

const SYSTEM_PROMPT = `你是"知识森林"知识库的整理助手。你会收到一个知识页面的现有正文，以及一段新采集到的碎片内容
（已判断应归入这个页面）。你的任务：把新内容整合进现有正文，产出一份重新组织过的完整新正文，而不是简单地在末尾追加。

要求：
- 保持全文结构清晰、语言连贯，避免重复表述。
- 如果新内容与已有内容视角不同或有细节补充，融入合适的段落/小标题下。
- 正文末尾维护一个"## 来源"小节，用列表记录每条内容的原始链接和采集时间；合并时保留旧来源，追加新来源。
- 如果新内容和已有正文实质重复（没有任何新信息），设置 skip=true，不要强行改写。
- 直接输出 Markdown 正文本身，不要额外的解释性文字包裹在 newContent 里。`;

/**
 * @param {string} existingContent 页面现有正文（Markdown，可能为空字符串——新建页面场景）
 * @param {{ text: string, sourceUrl?: string, capturedAt?: string }} newContent
 */
export async function mergeContent(existingContent, newContent) {
  const sourceLine = `- ${newContent.sourceUrl || '未知来源'}（采集于 ${newContent.capturedAt || new Date().toISOString()}）`;
  const userPrompt = `现有正文：
${existingContent || '(空 — 这是一个新页面，请基于新内容撰写初始正文)'}

新采集内容：
${newContent.text}

本次采集的来源记录（合并进"## 来源"小节）：
${sourceLine}`;

  return complete(
    [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: userPrompt },
    ],
    { jsonSchema: MERGE_SCHEMA },
  );
}
