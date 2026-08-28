// changelog.js — 维护一个"变更日志"节点，记录每次采集处理的结果
// （时间、来源、判定归入的章节、做了什么改动/是否跳过），方便回溯"这次到底改到哪了"。
//
// 用 append 而不是 LLM 合并重写：日志是纯追加语义，不需要模型重新组织，
// 直接拼接一行 Markdown 列表项即可，省一次 LLM 调用。

import { listWikiNodes, createWikiNode, appendNodeContent } from '../lark/wiki-client.js';

const CHANGELOG_TITLE = '变更日志';
const LEVEL_LABEL = { root: '根', trunk: '干', branch: '枝', leaf: '叶' };
const ACTION_LABEL = {
  merged: '已合并写入',
  'skip-duplicate-content': '跳过（内容重复）',
  'skip-no-change': '跳过（无新增信息）',
};

let cachedNode = null;

async function findOrCreateChangelogNode() {
  if (cachedNode) return cachedNode;
  const rootNodes = await listWikiNodes();
  const existing = rootNodes.find((n) => n.title === CHANGELOG_TITLE);
  if (existing) {
    cachedNode = existing;
    return existing;
  }
  const created = await createWikiNode(CHANGELOG_TITLE);
  cachedNode = { node_token: created.node_token, obj_token: created.obj_token, title: CHANGELOG_TITLE };
  return cachedNode;
}

function formatEntry({ capturedAt, sourceUrl, sourceTitle, domain, level, targetTitle, action, summary }) {
  const time = capturedAt || new Date().toISOString();
  const levelLabel = LEVEL_LABEL[level] || level || '-';
  const actionLabel = ACTION_LABEL[action] || action;
  return `- **${time}** | 来源：[${sourceTitle || sourceUrl}](${sourceUrl}) | 归入：${targetTitle || '-'}（${domain || '-'} / ${levelLabel}）| ${actionLabel}：${summary || ''}`;
}

/**
 * 追加一条日志（不做 LLM 合并，直接在文档末尾 append 一行）
 * @param {{capturedAt?, sourceUrl, sourceTitle?, domain?, level?, targetTitle?, action, summary?}} entry
 */
export async function appendChangelogEntry(entry) {
  try {
    const node = await findOrCreateChangelogNode();
    await appendNodeContent(node.obj_token, formatEntry(entry));
  } catch (err) {
    // 日志写入失败不应阻断主流程，只打印警告
    console.error('[changelog] 追加日志失败:', err.message);
  }
}
