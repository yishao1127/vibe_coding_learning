// classify.js — 阶段一：判断新内容属于"根/干/枝/叶"哪一级、归属哪个知识体
//
// 只把 wiki 树的"结构快照"（标题 + 层级 + token）喂给 LLM，不带正文全文，
// 控制上下文体积；分类结果里带 targetNodeToken（已有节点）或 "new"（需新建）。

import { complete } from '../llm-client.js';

const LEVELS = ['root', 'trunk', 'branch', 'leaf'];
const LEVEL_LABEL = { root: '根', trunk: '干', branch: '枝', leaf: '叶' };

function renderTreeSnapshot(nodes, depth = 0) {
  let lines = [];
  for (const node of nodes) {
    const indent = '  '.repeat(depth);
    const levelLabel = LEVEL_LABEL[LEVELS[Math.min(depth, LEVELS.length - 1)]];
    lines.push(`${indent}- [${levelLabel}] ${node.title} (node_token=${node.node_token})`);
    if (node.children?.length) {
      lines = lines.concat(renderTreeSnapshot(node.children, depth + 1));
    }
  }
  return lines;
}

const CLASSIFY_SCHEMA = {
  name: 'classify_result',
  schema: {
    type: 'object',
    properties: {
      level: { type: 'string', enum: LEVELS },
      knowledgeDomain: { type: 'string', description: '所属知识体名称，例如"心理学"、"投资"' },
      targetNodeToken: { type: 'string', description: '归入的已有节点 node_token；若需新建节点则填 "new"' },
      parentNodeTokenForNew: { type: 'string', description: '仅当 targetNodeToken 为 "new" 时：新节点应挂在哪个父节点下的 node_token；若是全新知识体的根节点则填空字符串' },
      newNodeTitle: { type: 'string', description: '仅当 targetNodeToken 为 "new" 时：新节点的标题' },
      reasoning: { type: 'string', description: '简要说明判断依据' },
    },
    required: ['level', 'knowledgeDomain', 'targetNodeToken', 'parentNodeTokenForNew', 'newNodeTitle', 'reasoning'],
    additionalProperties: false,
  },
};

const SYSTEM_PROMPT = `你是"知识森林"知识库的分类助手。知识体系按"根/干/枝/叶"四级粒度组织：
- 根：某个领域最基础、最抽象的理论或核心原则
- 干：该领域的核心框架、主要分支
- 枝：具体的方法、模型、应用场景
- 叶：具体的案例、细节、只言片语的经验

给定一段新采集到的碎片内容，以及当前知识库的完整目录结构（树形快照，每行标注层级和 node_token），
判断这段新内容应该归入哪个层级、哪个已有节点，或者是否需要新建节点（新知识体或树中缺失的层级）。

判断原则：
- 优先归入已有节点，除非确实找不到合适的归属。
- 新建节点时，parentNodeTokenForNew 必须是树中已存在的 node_token（新建"根"级知识体时留空字符串）。
- 不确定时倾向于归入更具体的层级（叶优于枝，枝优于干）。`;

/**
 * @param {{ text: string, sourceUrl?: string }} content 新采集内容
 * @param {Array} wikiTree getTreeIndex() 得到的目录树快照
 */
export async function classifyContent(content, wikiTree) {
  const snapshot = renderTreeSnapshot(wikiTree).join('\n') || '(知识库当前为空)';
  const userPrompt = `当前知识库目录结构：
${snapshot}

新采集内容（来源：${content.sourceUrl || '未知'}）：
${content.text}`;

  return complete(
    [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: userPrompt },
    ],
    { jsonSchema: CLASSIFY_SCHEMA },
  );
}
