// server.js — 知识森林后端：接收插件采集的内容，跑完 extract -> classify -> merge -> toc 流水线，
// 写回飞书 wiki 知识库

import express from 'express';
import cors from 'cors';
import crypto from 'node:crypto';
import fs from 'node:fs';
import { PORT, SHARED_TOKEN_PATH } from './config.js';
import { createWikiNode, fetchNodeContent, overwriteNodeContent } from './lark/wiki-client.js';
import { getTreeIndex, addNodeToIndex } from './lark/tree-index.js';
import { extractContent } from './pipeline/extract.js';
import { classifyContent } from './pipeline/classify.js';
import { mergeContent } from './pipeline/merge.js';
import { refreshTableOfContents } from './pipeline/toc.js';
import { appendChangelogEntry } from './pipeline/changelog.js';
import { findExisting, recordCapture } from './state/capture-log.js';

function loadOrCreateSharedToken() {
  if (fs.existsSync(SHARED_TOKEN_PATH)) {
    return fs.readFileSync(SHARED_TOKEN_PATH, 'utf8').trim();
  }
  const token = crypto.randomBytes(24).toString('hex');
  fs.writeFileSync(SHARED_TOKEN_PATH, token, { mode: 0o600 });
  return token;
}

const SHARED_TOKEN = loadOrCreateSharedToken();

const app = express();
app.use(cors());
app.use(express.json({ limit: '20mb' })); // 整页内容 + 多张图片 base64 可能较大

app.get('/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// 插件启动时调用一次，拿到共享 token 存进 chrome.storage.local
app.get('/token', (req, res) => {
  res.json({ token: SHARED_TOKEN });
});

function requireToken(req, res, next) {
  const provided = req.get('X-Extension-Token');
  if (provided !== SHARED_TOKEN) {
    return res.status(401).json({ ok: false, error: '缺少或错误的鉴权 token' });
  }
  next();
}

/**
 * 核心流水线：extract -> classify -> (创建节点/取已有正文) -> merge -> 写回 -> toc
 */
async function runPipeline({ mode, sourceUrl, sourceTitle, text, images, capturedAt }) {
  const t0 = Date.now();
  const step = (label) => console.log(`[pipeline] ${label}: +${Date.now() - t0}ms`);

  const cleanedText = await extractContent({ text, images });
  step('extract done');

  const existing = findExisting(sourceUrl, cleanedText);
  if (existing) {
    await appendChangelogEntry({
      capturedAt, sourceUrl, sourceTitle,
      action: 'skip-duplicate-content',
      summary: '相同内容已采集过',
    });
    return { ok: true, skipped: true, reason: '相同内容已采集过，跳过', existing };
  }

  const wikiTree = await getTreeIndex();
  step('getTreeIndex done');
  const classification = await classifyContent({ text: cleanedText, sourceUrl }, wikiTree);
  step('classify done');

  let targetNodeToken = classification.targetNodeToken;
  let targetObjToken;
  let targetTitle;

  if (targetNodeToken === 'new') {
    const parent = classification.parentNodeTokenForNew || undefined;
    const created = await createWikiNode(classification.newNodeTitle, parent);
    step('createWikiNode done');
    targetNodeToken = created.node_token;
    targetObjToken = created.obj_token;
    targetTitle = classification.newNodeTitle;
    await addNodeToIndex(created, parent);
    step('addNodeToIndex done');
  } else {
    // 在树快照里找到该 node_token 对应的 obj_token
    const findInTree = (nodes) => {
      for (const node of nodes) {
        if (node.node_token === targetNodeToken) return node;
        if (node.children?.length) {
          const found = findInTree(node.children);
          if (found) return found;
        }
      }
      return null;
    };
    const targetNode = findInTree(wikiTree);
    if (!targetNode) {
      throw new Error(`分类结果指向的 node_token 在当前树中不存在: ${targetNodeToken}`);
    }
    targetObjToken = targetNode.obj_token;
    targetTitle = targetNode.title;
  }

  const existingContent = classification.targetNodeToken === 'new' ? '' : await fetchNodeContent(targetObjToken);
  step('fetchNodeContent done');
  const merged = await mergeContent(existingContent, { text: cleanedText, sourceUrl, capturedAt });
  step('merge done');

  if (merged.skip) {
    recordCapture({ sourceUrl, text: cleanedText, targetNodeToken, action: 'skip-no-change' });
    await appendChangelogEntry({
      capturedAt, sourceUrl, sourceTitle,
      domain: classification.knowledgeDomain, level: classification.level, targetTitle,
      action: 'skip-no-change', summary: merged.changeSummary,
    });
    return { ok: true, skipped: true, reason: merged.changeSummary, classification };
  }

  await overwriteNodeContent(targetObjToken, merged.newContent);
  step('overwriteNodeContent done');
  await refreshTableOfContents();
  step('refreshTableOfContents done');

  recordCapture({ sourceUrl, text: cleanedText, targetNodeToken, action: 'merged' });
  await appendChangelogEntry({
    capturedAt, sourceUrl, sourceTitle,
    domain: classification.knowledgeDomain, level: classification.level, targetTitle,
    action: 'merged', summary: merged.changeSummary,
  });
  step('appendChangelogEntry done');

  return {
    ok: true,
    skipped: false,
    classification,
    changeSummary: merged.changeSummary,
    targetNodeToken,
    targetTitle,
  };
}

app.post('/capture', requireToken, async (req, res) => {
  const { mode, sourceUrl, sourceTitle, text, images, capturedAt } = req.body || {};
  if (!text || !sourceUrl) {
    return res.status(400).json({ ok: false, error: '缺少 text 或 sourceUrl' });
  }

  try {
    const result = await runPipeline({ mode, sourceUrl, sourceTitle, text, images, capturedAt });
    res.json(result);
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.listen(PORT, '127.0.0.1', () => {
  console.log(`[knowledge-forest backend] listening on http://127.0.0.1:${PORT}`);
});
