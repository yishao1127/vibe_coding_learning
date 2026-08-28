// toc.js — 目录维护：飞书 wiki 的页面树本身就是目录导航，这里只维护一个
// "Homepage" 节点的正文，列出所有根级知识体及其一级子节点，作为可读的总览入口。

import { listWikiNodes, fetchNodeContent, overwriteNodeContent } from '../lark/wiki-client.js';

const HOMEPAGE_TITLE = 'Homepage';

async function findHomepageNode() {
  const rootNodes = await listWikiNodes();
  return rootNodes.find((n) => n.title === HOMEPAGE_TITLE) || null;
}

function renderDirectory(rootNodes, trunkNodesByRoot) {
  const lines = ['# 知识森林目录', ''];
  for (const root of rootNodes) {
    if (root.title === HOMEPAGE_TITLE) continue;
    lines.push(`## ${root.title}`);
    const trunks = trunkNodesByRoot.get(root.node_token) || [];
    if (trunks.length === 0) {
      lines.push('（暂无子节点）');
    } else {
      for (const trunk of trunks) {
        lines.push(`- ${trunk.title}`);
      }
    }
    lines.push('');
  }
  return lines.join('\n').trim();
}

/**
 * 刷新 Homepage 节点正文，使其反映当前所有根级知识体和一级子节点。
 * 若 Homepage 节点不存在则跳过（不主动创建，避免覆盖用户已有的自定义首页）。
 */
export async function refreshTableOfContents() {
  const homepage = await findHomepageNode();
  if (!homepage) return;

  const rootNodes = await listWikiNodes();
  const trunkNodesByRoot = new Map();
  for (const root of rootNodes) {
    if (root.title === HOMEPAGE_TITLE || !root.has_child) continue;
    const trunks = await listWikiNodes(root.node_token);
    trunkNodesByRoot.set(root.node_token, trunks);
  }

  const newContent = renderDirectory(rootNodes, trunkNodesByRoot);
  await overwriteNodeContent(homepage.obj_token, newContent);
}
