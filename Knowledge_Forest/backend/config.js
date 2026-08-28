// config.js — 后端配置集中管理

export const PORT = process.env.PORT || 8799;
export const LARK_CLI_PATH = process.env.LARK_CLI_PATH || 'lark-cli';
export const LLM_BASE_URL = process.env.LLM_BASE_URL || 'http://localhost:23333/api/openai/v1';
export const LLM_MODEL = process.env.LLM_MODEL || 'gpt-5.4';

export const WIKI_SPACE_ID = process.env.WIKI_SPACE_ID?.trim();
if (!WIKI_SPACE_ID) {
  throw new Error('WIKI_SPACE_ID is required. Set it in the environment before starting the backend.');
}

// 首次启动自动生成并持久化到本地文件，扩展端首次也会拿到同一份、写入
// chrome.storage.local；之后每次请求都要带这个 token，防止同机其他进程
// 或恶意网页伪造请求打到本地后端。
export const SHARED_TOKEN_PATH = process.env.SHARED_TOKEN_PATH
  || new URL('./.shared-token', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');

// 采集日志（来源 URL + 内容哈希）持久化路径，用于幂等去重
export const CAPTURE_LOG_PATH = process.env.CAPTURE_LOG_PATH
  || new URL('./state/capture-log.json', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
