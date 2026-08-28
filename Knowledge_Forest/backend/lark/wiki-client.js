// wiki-client.js — 封装 lark-cli 的 wiki 节点管理 + docs 内容读写命令
//
// 知识森林把"根/干/枝/叶"四级知识粒度直接映射为飞书 wiki 的节点父子层级：
//   space 根节点 -> 根(root) -> 干(trunk) -> 枝(branch) -> 叶(leaf)
// 节点本身只是"目录条目"（node_token + title + parent），节点对应的正文内容
// 挂在其 obj_token（docx 文档）上，读写正文走 docs +fetch / +update。

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { LARK_CLI_PATH, WIKI_SPACE_ID } from '../config.js';

const execFileAsync = promisify(execFile);

// 飞书 token 只允许字母数字，防止意外内容混进 CLI 参数
const SAFE_TOKEN_RE = /^[A-Za-z0-9]+$/;

function assertSafeToken(token, label = 'token') {
  if (!token || !SAFE_TOKEN_RE.test(token)) {
    throw new Error(`非法的${label}: ${token}`);
  }
}

async function runLarkCli(args) {
  try {
    const { stdout } = await execFileAsync(LARK_CLI_PATH, [...args, '--as', 'user', '--format', 'json'], {
      maxBuffer: 20 * 1024 * 1024, // 文档内容可能较大，放宽缓冲区
    });
    return JSON.parse(stdout);
  } catch (err) {
    // execFile 失败（非零退出码）时 err.stdout 可能仍包含 lark-cli 的 JSON 错误信息
    if (err.stdout) {
      try {
        return JSON.parse(err.stdout);
      } catch {
        /* 落到下面统一抛错 */
      }
    }
    throw new Error(`lark-cli 执行失败: ${err.message}`);
  }
}

/**
 * 列出某个 wiki 空间下、某个父节点下的子节点（不传 parentNodeToken 则列出根级节点）
 * @param {string} [parentNodeToken]
 * @returns {Promise<Array<{node_token, obj_token, obj_type, title, parent_node_token, has_child}>>}
 */
export async function listWikiNodes(parentNodeToken) {
  const args = ['wiki', '+node-list', '--space-id', WIKI_SPACE_ID, '--page-all'];
  if (parentNodeToken) {
    assertSafeToken(parentNodeToken, 'node_token');
    args.push('--parent-node-token', parentNodeToken);
  }
  const result = await runLarkCli(args);
  if (!result.ok) {
    throw new Error(`列出 wiki 节点失败: ${JSON.stringify(result.error)}`);
  }
  return result.data.nodes || [];
}

/**
 * 递归拉取整棵 wiki 树（仅到指定深度，避免上下文过大）。
 * 每个有子节点的节点都要单独 spawn 一次 lark-cli 子进程；调用方应优先使用
 * tree-index.js 里维护在飞书"目录索引"文档中的快照，只有首次初始化或怀疑
 * 索引和远程不一致时才需要直接调这个函数做全量拉取。
 * @param {string} [parentNodeToken]
 * @param {number} maxDepth 最大递归深度（根节点算第 1 层）
 * @returns {Promise<Array>} 每个节点带 children 数组
 */
export async function fetchWikiTree(parentNodeToken, maxDepth = 4) {
  const nodes = await listWikiNodes(parentNodeToken);
  if (maxDepth <= 1) {
    return nodes.map((n) => ({ ...n, children: [] }));
  }
  // 各节点的子树读取互不依赖，并行发起而不是逐个 await，把总耗时从
  // "节点数 * 单次调用耗时"降到"约等于单次调用耗时"
  const childrenLists = await Promise.all(
    nodes.map((node) => (node.has_child ? fetchWikiTree(node.node_token, maxDepth - 1) : Promise.resolve([]))),
  );
  return nodes.map((node, i) => ({ ...node, children: childrenLists[i] }));
}

/**
 * 在指定父节点下创建新的 wiki 节点（docx 类型）
 * @param {string} title 节点标题
 * @param {string} [parentNodeToken] 不传则创建到 space 根级
 * @returns {Promise<{node_token, obj_token, title}>}
 */
export async function createWikiNode(title, parentNodeToken) {
  const args = ['wiki', '+node-create', '--space-id', WIKI_SPACE_ID, '--obj-type', 'docx', '--title', title];
  if (parentNodeToken) {
    assertSafeToken(parentNodeToken, 'node_token');
    args.push('--parent-node-token', parentNodeToken);
  }
  const result = await runLarkCli(args);
  if (!result.ok) {
    throw new Error(`创建 wiki 节点失败: ${JSON.stringify(result.error)}`);
  }
  return result.data.node || result.data;
}

/**
 * 读取节点对应文档的正文（Markdown 格式，便于 LLM 阅读和重写）
 * @param {string} objToken docx 文档 token（wiki 节点的 obj_token）
 */
export async function fetchNodeContent(objToken) {
  assertSafeToken(objToken, 'obj_token');
  const result = await runLarkCli(['docs', '+fetch', '--doc', objToken, '--doc-format', 'markdown']);
  if (!result.ok) {
    throw new Error(`读取节点内容失败: ${JSON.stringify(result.error)}`);
  }
  return result.data.document.content;
}

/**
 * 用新内容整体覆盖节点正文（LLM 合并重写后的完整 Markdown 正文）
 * @param {string} objToken docx 文档 token
 * @param {string} markdownContent 完整的新正文（Markdown）
 */
export async function overwriteNodeContent(objToken, markdownContent) {
  assertSafeToken(objToken, 'obj_token');
  const result = await runLarkCli([
    'docs', '+update',
    '--doc', objToken,
    '--command', 'overwrite',
    '--doc-format', 'markdown',
    '--content', markdownContent,
  ]);
  if (!result.ok || result.data?.result === 'failed') {
    throw new Error(`覆盖节点内容失败: ${JSON.stringify(result.error || result.data?.warnings)}`);
  }
  return result.data;
}

/**
 * 在节点正文末尾追加一段内容（不做整体重写，用于纯追加语义的场景，如变更日志）。
 *
 * 不用 `docs +update --command append`：实测这个命令对同一篇文档第二次调用起
 * 必定失败（`degrade_code=1002, Block ID transform failed: target block not found`），
 * 是 lark-cli/飞书 API 对 `append`（内部等价于 `block_insert_after --block-id -1`）
 * 重复调用时的已知缺陷，与内容格式（XML/Markdown/列表/段落）无关。
 * 绕过方式：先重新 fetch 文档拿到真实的末尾 block id，再用 `block_insert_after`
 * 显式指定该 id 追加——这个组合实测可以稳定连续调用。
 * @param {string} objToken docx 文档 token
 * @param {string} markdownContent 要追加的 Markdown 片段
 */
export async function appendNodeContent(objToken, markdownContent) {
  assertSafeToken(objToken, 'obj_token');
  const fetchResult = await runLarkCli(['docs', '+fetch', '--doc', objToken, '--detail', 'with-ids']);
  if (!fetchResult.ok) {
    throw new Error(`追加节点内容失败（读取文档结构时出错）: ${JSON.stringify(fetchResult.error)}`);
  }
  const content = fetchResult.data.document.content;
  const idMatches = [...content.matchAll(/\sid="([^"]+)"/g)];
  const lastBlockId = idMatches.length ? idMatches[idMatches.length - 1][1] : fetchResult.data.document.document_id;

  const result = await runLarkCli([
    'docs', '+update',
    '--doc', objToken,
    '--command', 'block_insert_after',
    '--block-id', lastBlockId,
    '--doc-format', 'markdown',
    '--content', markdownContent,
  ]);
  if (!result.ok || result.data?.result === 'failed') {
    throw new Error(`追加节点内容失败: ${JSON.stringify(result.error || result.data?.warnings)}`);
  }
  return result.data;
}
