# 知识森林（Knowledge Forest）

把碎片化阅读自动整理进飞书知识库的浏览器插件 + 本地服务。技术方案见 [docs/design.md](docs/design.md)。

## 目录结构

```
Knowledge_Forest/
  docs/design.md          # 技术方案设计文档
  backend/                 # 本地 Node 服务：分类/合并/写回飞书 wiki
  extension/                # MV3 浏览器插件：整页采集 + 划词/图片右键采集
```

## 快速开始

1. 安装后端依赖：
   ```bash
   cd backend
   npm install
   ```
2. 设置目标飞书知识库的空间 ID。Windows 可将配置持久保存为用户环境变量：
   ```powershell
   [Environment]::SetEnvironmentVariable("WIKI_SPACE_ID", "your-space-id", "User")
   ```
   设置后需要完全关闭并重新打开 VS Code，使新终端和后端进程继承该变量。也可以只为当前终端临时设置：
   ```powershell
   $env:WIKI_SPACE_ID = "your-space-id"
   npm start   # 监听 http://127.0.0.1:8799
   ```
   Bash：
   ```bash
   WIKI_SPACE_ID="your-space-id" npm start
   ```
   `LARK_CLI_PATH` 为可选环境变量；未设置时会从 `PATH` 中查找 `lark-cli`。不要把真实空间 ID 或本机路径写入源码、README 或其他可提交文件。
3. Chrome/Edge 打开 `chrome://extensions`，开启开发者模式，"加载已解压的扩展程序"选择 `extension/` 目录。
4. 打开任意网页：
   - 点击工具栏图标 → 整页采集当前页面正文 + 图片。
   - 选中一段文字（或右键图片）→ 右键菜单"加入知识森林" → 只采集选中片段。
5. 采集结果会自动分类归入 `WIKI_SPACE_ID` 指定的飞书知识库，并与已有页面正文合并重写。每次处理结果（无论合并写入还是跳过）都会追加一条记录到知识库根目录下的"变更日志"节点，可以直接去那里查最近几次到底改到了哪个章节。
6. **整个流程实测耗时 20~30 秒**（LLM 分类 + LLM 合并 + 多次 lark-cli 子进程调用累加），页面右上角的提示条会一直停留在"正在采集并整理..."直到真正拿到结果才会变化，属于正常现象，请耐心等待，不要在提示条消失前反复点击。

## 目录索引：为什么不用每次都重新拉取整棵 wiki 树

飞书开放 API 没有"一次性拉取整棵知识库树"的接口，只能一层一层地列子节点；早期实现是每次采集都递归调用 `lark-cli wiki +node-list`，节点越多越慢（实测 3~9 秒）。

现在改为在知识库根目录下维护一篇专门的**"目录索引"**文档（`backend/lark/tree-index.js`），正文里存一份 JSON 格式的树结构快照：
- 平时采集只需要读这一篇文档（1 次调用，通常几百毫秒），不再需要对每个根节点分别发起调用。
- 只有真正新建节点时，才会把新节点追加进这篇文档的快照里再覆盖写回（同样只是 1 次调用）。
- 如果怀疑索引和飞书实际结构不一致（比如手动在飞书里挪动过节点），可以直接去飞书把"目录索引"这篇文档删掉，下次采集会自动全量重建一份新的。

## 排查："点了没反应"

1. 先看提示条：现在会一直显示"正在采集并整理"直到有结果，不会中途消失（旧版本 4 秒后会自动消失，容易误以为没反应，已修复）。
2. 确认后端在跑：浏览器打开 `http://127.0.0.1:8799/health`，能看到 `{"status":"ok",...}` 才说明后端活着；采集前建议先看一眼这个。
3. 查看后端终端输出的 `[pipeline] xxx done: +xxxxms` 日志，能看出卡在哪一步（拉取知识库目录树 / LLM 分类 / LLM 合并 / 写回飞书）。

## 依赖前提

- 本机已配置好 `lark-cli`（`lark-cli whoami` 能正常返回身份信息）。
- 本机 `LLM_BASE_URL`（默认 `http://localhost:23333/api/openai/v1`）有可用的 OpenAI Responses API 兼容服务。

## 已知限制（MVP 阶段）

- 结构化输出依赖提示词约束 + 容错解析（本地 LLM 代理不支持 `json_schema` 强制模式），个别情况下模型可能返回非纯 JSON，会直接报错而非重试。
- 图片提取依赖插件能拿到可访问的图片 URL；有防盗链/登录墙的图片可能无法被后端下载理解。
- 目录维护仅刷新名为 `Homepage` 的现有根节点，不会主动创建它。
- `lark-cli docs +update --command append` 对同一篇文档第二次调用起必定失败（`degrade_code=1002, Block ID transform failed`），是该命令本身的缺陷，与内容格式无关；`backend/lark/wiki-client.js` 的 `appendNodeContent` 已改为"先 fetch 拿真实末尾 block id，再用 `block_insert_after` 显式指定"来绕过，"变更日志"节点依赖这个函数，若发现日志又停止更新，先怀疑这个绕过逻辑是否还生效。
