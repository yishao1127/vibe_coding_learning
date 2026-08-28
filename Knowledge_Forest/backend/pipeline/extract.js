// extract.js — 内容提取：文本清洗 + 图片理解（OCR/语义描述）
//
// 插件侧已经做了基础 DOM 提取，这里只负责：
//   1. 去除明显噪声（多余空行/重复空白）
//   2. 若带图片，用多模态 LLM 提取图中文字与要点，拼接进正文供分类/合并使用

import { completeWithImages } from '../llm-client.js';

function cleanText(text) {
  return (text || '')
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const IMAGE_PROMPT = '请描述这些图片中的内容：如果是文字/截图，提取其中的文字；如果是图表或场景图，用简洁的中文概括要点。多张图按顺序逐条列出。';

/**
 * @param {{ text: string, images?: string[] }} raw 插件提取的原始内容
 * @returns {Promise<string>} 清洗 + 图片理解后拼接的最终文本
 */
export async function extractContent(raw) {
  const cleaned = cleanText(raw.text);
  if (!raw.images?.length) {
    return cleaned;
  }

  const imageDescription = await completeWithImages(IMAGE_PROMPT, raw.images);
  return `${cleaned}\n\n[图片内容]\n${imageDescription}`.trim();
}
