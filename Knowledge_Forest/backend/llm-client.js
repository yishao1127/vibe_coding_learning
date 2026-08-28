// llm-client.js — 封装调用本地 OpenAI Responses API（非流式）
//
// 知识森林的 pipeline 是离线批处理（分类/合并/目录维护），不需要像
// feishu-ai-writer 那样流式打字机效果，所以这里只做一次性请求-返回，
// 复用同一个本地 LLM 代理（LLM_BASE_URL/LLM_MODEL）。
//
// 本地代理不支持 Structured Outputs（传 text.format=json_schema 会被忽略，
// 仍返回自由文本），因此结构化结果改为：system prompt 里明确要求"只输出
// JSON，不要任何解释文字"，返回后做容错解析（剥离可能的 ```json 代码块包裹）。

import { LLM_BASE_URL, LLM_MODEL } from './config.js';

function extractJson(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = fenced ? fenced[1] : text;
  return JSON.parse(candidate.trim());
}

/**
 * 请求一次 LLM 补全，返回文本（或结构化 JSON 对象，取决于是否传 jsonSchema）。
 * @param {Array<{role: string, content: string}>} messages
 * @param {{ jsonSchema?: { name: string, schema: object } }} [opts]
 * @returns {Promise<string | object>}
 */
export async function complete(messages, opts = {}) {
  let finalMessages = messages;
  if (opts.jsonSchema) {
    const instruction = `\n\n只输出一个 JSON 对象，不要任何解释文字、不要代码块包裹。JSON 必须严格符合以下 schema：\n${JSON.stringify(opts.jsonSchema.schema)}`;
    finalMessages = messages.map((m, i) =>
      i === 0 && m.role === 'system' ? { ...m, content: m.content + instruction } : m,
    );
    if (finalMessages[0]?.role !== 'system') {
      finalMessages = [{ role: 'system', content: instruction.trim() }, ...finalMessages];
    }
  }

  const body = {
    model: LLM_MODEL,
    input: finalMessages,
    stream: false,
  };

  const res = await fetch(`${LLM_BASE_URL}/responses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`本地大模型请求失败: HTTP ${res.status} ${text}`);
  }

  const data = await res.json();
  const message = (data.output || []).find((item) => item.type === 'message');
  const textOutput = message?.content?.find((c) => c.type === 'output_text')?.text;
  if (textOutput === undefined) {
    throw new Error(`本地大模型未返回文本内容: ${JSON.stringify(data)}`);
  }

  if (opts.jsonSchema) {
    try {
      return extractJson(textOutput);
    } catch {
      throw new Error(`本地大模型结构化输出解析失败: ${textOutput}`);
    }
  }
  return textOutput;
}

/**
 * 支持图片输入的补全（多模态 OCR / 图片理解）。
 * @param {string} prompt 文本指令
 * @param {Array<string>} imageUrlsOrDataUrls 图片 URL 或 data URL
 * @returns {Promise<string>}
 */
export async function completeWithImages(prompt, imageUrlsOrDataUrls) {
  const content = [
    { type: 'input_text', text: prompt },
    ...imageUrlsOrDataUrls.map((url) => ({ type: 'input_image', image_url: url })),
  ];
  return complete([{ role: 'user', content }]);
}
