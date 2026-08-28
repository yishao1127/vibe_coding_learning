// capture-log.js — 记录每次采集的溯源信息（来源 URL + 内容哈希），用于幂等去重
//
// 落盘为单个 JSON 文件（内容量级不大，不需要引入数据库）。

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { CAPTURE_LOG_PATH } from '../config.js';

function loadLog() {
  if (!fs.existsSync(CAPTURE_LOG_PATH)) return [];
  try {
    return JSON.parse(fs.readFileSync(CAPTURE_LOG_PATH, 'utf8'));
  } catch {
    return [];
  }
}

function saveLog(entries) {
  fs.mkdirSync(path.dirname(CAPTURE_LOG_PATH), { recursive: true });
  fs.writeFileSync(CAPTURE_LOG_PATH, JSON.stringify(entries, null, 2));
}

export function contentHash(sourceUrl, text) {
  return crypto.createHash('sha256').update(`${sourceUrl}\n${text}`).digest('hex');
}

/**
 * 查找是否已处理过相同内容（同一来源 URL + 相同正文哈希）
 */
export function findExisting(sourceUrl, text) {
  const hash = contentHash(sourceUrl, text);
  const entries = loadLog();
  return entries.find((e) => e.hash === hash) || null;
}

/**
 * 记录一次采集处理结果
 */
export function recordCapture({ sourceUrl, text, targetNodeToken, action }) {
  const entries = loadLog();
  entries.push({
    hash: contentHash(sourceUrl, text),
    sourceUrl,
    targetNodeToken,
    action,
    capturedAt: new Date().toISOString(),
  });
  saveLog(entries);
}
