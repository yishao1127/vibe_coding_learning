// tree-index.js — 目录索引：把 wiki 树结构快照维护成飞书知识库里的一篇专门文档，
// 而不是散落在本地磁盘。
//
// 之前的问题：每次采集都要递归调用 `lark-cli wiki +node-list` 拉取整棵树（根节点越多、
// 每个根节点都要多起一次 lark-cli 子进程，实测 3~9 秒）。
// 现在的方案：维护一个标题为"目录索引"的 wiki 节点，正文里存一份 JSON 格式的树快照。
// 平时读取只需要 fetchNodeContent 读一次这篇文档（1 次调用，而不是 N 次），
// 只有真正新建节点时才去更新它（本身也只是覆盖这一篇文档的正文，同样是 1 次调用）。
// 这样"目录索引总能反映当前树结构"这件事本身也维护在飞书文档里，而不是本地文件。

import { listWikiNodes, createWikiNode, fetchNodeContent, overwriteNodeContent, fetchWikiTree } from './wiki-client.js';

const INDEX_TITLE = '目录索引';

let cachedIndexNode = null;

async function findOrCreateIndexNode() {
  if (cachedIndexNode) return cachedIndexNode;
  const rootNodes = await listWikiNodes();
  const existing = rootNodes.find((n) => n.title === INDEX_TITLE);
  if (existing) {
    cachedIndexNode = existing;
    return existing;
  }
  const created = await createWikiNode(INDEX_TITLE);
  cachedIndexNode = { node_token: created.node_token, obj_token: created.obj_token, title: INDEX_TITLE };
  return cachedIndexNode;
}

function extractJson(markdown) {
  const fenced = markdown.match(/```(?:json)?\s*([\s\S]*?)```/);
  return JSON.parse((fenced ? fenced[1] : markdown).trim());
}

function renderIndexDoc(tree) {
  return `# 目录索引\n\n此文档由知识森林后端自动维护，记录当前 wiki 目录树的完整结构快照，请勿手动编辑。\n\n\`\`\`json\n${JSON.stringify(tree, null, 2)}\n\`\`\``;
}

/**
 * 强制从飞书重新全量拉取，重写目录索引文档（用于首次初始化，或怀疑索引与
 * 远程不一致时手动修复）。
 */
export async function rebuildTreeIndex() {
  const tree = await fetchWikiTree(undefined, 4);
  const indexNode = await findOrCreateIndexNode();
  await overwriteNodeContent(indexNode.obj_token, renderIndexDoc(tree));
  return tree;
}

/**
 * 获取当前目录树快照：优先读目录索引文档（1 次调用）；索引文档为空或解析失败
 * （比如刚创建、还没写过内容）时，退化为全量重建一次。
 */
export async function getTreeIndex() {
  const indexNode = await findOrCreateIndexNode();
  const content = await fetchNodeContent(indexNode.obj_token);
  try {
    return extractJson(content);
  } catch {
    return rebuildTreeIndex();
  }
}

/**
 * 在目录索引文档里插入一个新建的节点，只需要覆盖这一篇文档（1 次调用），
 * 不需要为了这一次新增而重新拉取整棵树。
 * @param {{node_token, obj_token, title}} newNode
 * @param {string} [parentNodeToken] 不传则插入为根级节点
 */
export async function addNodeToIndex(newNode, parentNodeToken) {
  const tree = await getTreeIndex();
  const entry = { ...newNode, obj_type: 'docx', parent_node_token: parentNodeToken || '', has_child: false, children: [] };

  if (!parentNodeToken) {
    tree.push(entry);
  } else {
    const findNode = (nodes) => {
      for (const node of nodes) {
        if (node.node_token === parentNodeToken) return node;
        const found = findNode(node.children || []);
        if (found) return found;
      }
      return null;
    };
    const parent = findNode(tree);
    if (!parent) {
      // 索引里找不到父节点，说明索引已经和远程不一致，重建一次后重试
      await rebuildTreeIndex();
      return addNodeToIndex(newNode, parentNodeToken);
    }
    parent.has_child = true;
    parent.children = parent.children || [];
    parent.children.push(entry);
  }

  const indexNode = await findOrCreateIndexNode();
  await overwriteNodeContent(indexNode.obj_token, renderIndexDoc(tree));
}
