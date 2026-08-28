// background.js — 知识森林采集入口：点击工具栏图标=整页采集；右键菜单=划词采集
//
// 两种入口都统一走 CAPTURE_PAGE / CAPTURE_SNIPPET 消息 -> 注入 content-script
// 提取内容 -> POST 到本地后端 /capture -> 在页面内弹一个悬浮提示条展示结果。
//
// 注意：完整流水线（LLM 分类 + LLM 合并 + 多次 lark-cli 子进程调用）实测耗时
// 20~30 秒，是正常现象，不是卡死；"正在采集..."提示条必须等到请求真正返回
// （或报错）才消失，不能按固定秒数自动隐藏，否则会让用户误以为没有反应。

const BACKEND_URL = 'http://127.0.0.1:8799';

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'kf-capture-snippet',
    title: '加入知识森林',
    contexts: ['selection', 'image'],
  });
});

async function ensureSharedToken() {
  const stored = await chrome.storage.local.get('sharedToken');
  if (stored.sharedToken) return stored.sharedToken;
  const res = await fetch(`${BACKEND_URL}/token`);
  const data = await res.json();
  await chrome.storage.local.set({ sharedToken: data.token });
  return data.token;
}

// 在页面里维护一个常驻提示条：pending=true 时展示为处理中样式且不会自动消失；
// pending=false 时展示最终结果样式，几秒后自动消失。
function renderToast(tabId, message, { pending, isError } = {}) {
  chrome.scripting.executeScript({
    target: { tabId },
    func: (msg, isPending, isErr) => {
      const ID = '__kf-toast__';
      let el = document.getElementById(ID);
      if (!el) {
        el = document.createElement('div');
        el.id = ID;
        Object.assign(el.style, {
          position: 'fixed',
          top: '16px',
          right: '16px',
          zIndex: 2147483647,
          padding: '10px 16px',
          borderRadius: '8px',
          color: '#fff',
          fontSize: '13px',
          fontFamily: 'sans-serif',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          maxWidth: '360px',
          lineHeight: '1.4',
        });
        document.body.appendChild(el);
      }
      el.textContent = msg;
      el.style.background = isPending ? '#2980b9' : (isErr ? '#c0392b' : '#2ecc71');
      if (!isPending) {
        setTimeout(() => el.remove(), 8000);
      }
    },
    args: [message, Boolean(pending), Boolean(isError)],
  });
}

async function sendCapture(tabId, payload) {
  const token = await ensureSharedToken();
  renderToast(tabId, '知识森林：正在采集并整理，通常需要 20~30 秒，请耐心等待...', { pending: true });
  try {
    const res = await fetch(`${BACKEND_URL}/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Extension-Token': token },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      renderToast(tabId, `采集失败: ${data.error || res.status}`, { isError: true });
      return;
    }
    if (data.skipped) {
      renderToast(tabId, `已跳过：${data.reason}`);
    } else {
      renderToast(tabId, `已归入「${data.classification?.knowledgeDomain || '知识库'}」：${data.changeSummary || '更新完成'}`);
    }
  } catch (err) {
    renderToast(tabId, `无法连接本地服务: ${err.message}`, { isError: true });
  }
}

// 点击工具栏图标 = 整页采集
chrome.action.onClicked.addListener(async (tab) => {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: extractFullPage,
  });
  await sendCapture(tab.id, { mode: 'full-page', sourceUrl: tab.url, sourceTitle: tab.title, ...result });
});

// 右键菜单 = 划词/图片采集
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== 'kf-capture-snippet') return;
  const payload = {
    mode: 'snippet',
    sourceUrl: tab.url,
    sourceTitle: tab.title,
    text: info.selectionText || '',
    images: info.srcUrl ? [info.srcUrl] : [],
    capturedAt: new Date().toISOString(),
  };
  await sendCapture(tab.id, payload);
});

// 注入到页面执行的提取函数：拿正文文本 + 图片 URL 列表
// （必须是纯函数，chrome.scripting.executeScript 会把它序列化后在页面上下文执行）
//
// 小红书笔记页 document.body.innerText 会把推荐流、侧边栏、平台备案信息全部
// 读进来，导致后端合并时把这些噪音也写进知识库。优先定位笔记详情容器，只有
// 找不到时才兜底用整个 body。
function extractFullPage() {
  const NOTE_DETAIL_SELECTORS = [
    '#noteContainer',
    '.note-container',
    '.note-scroller .note-content',
    '.interaction-container',
  ];
  let scope = document.body;
  if (location.hostname.includes('xiaohongshu.com')) {
    for (const sel of NOTE_DETAIL_SELECTORS) {
      const el = document.querySelector(sel);
      if (el) { scope = el; break; }
    }
  }
  const text = scope.innerText || '';
  const images = Array.from(scope.querySelectorAll('img'))
    .map((img) => img.src)
    .filter((src) => src && src.startsWith('http'))
    .slice(0, 10); // 控制单次采集的图片数量
  return { text, images, capturedAt: new Date().toISOString() };
}
