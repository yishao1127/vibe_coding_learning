"""Client for the local OpenAI-compatible Responses API used by Knowledge Forest."""

from __future__ import annotations

import json
from collections.abc import Mapping

import requests

from ..domain.errors import LocalModelConnectionError, LocalModelResponseError


class OpenAIResponsesClient:
    """Non-streaming local model client for ``{base_url}/responses``."""

    def __init__(self, base_url: str, timeout_seconds: int = 90) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def generate_json(self, model_name: str, prompt: str) -> dict:
        """Request one non-streaming completion through the shared local API."""
        data = self._post(
            "/responses",
            {
                "model": model_name,
                "input": [
                    {
                        "role": "system",
                        "content": "只输出一个合法 JSON 对象，不要解释文字，也不要使用 Markdown 代码围栏。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        text = self._extract_output_text(data)
        try:
            parsed = json.loads(self._strip_code_fence(text))
        except json.JSONDecodeError as error:
            raise LocalModelResponseError("本地大模型返回的内容不是有效 JSON。") from error
        if not isinstance(parsed, dict):
            raise LocalModelResponseError("本地大模型返回的 JSON 格式不正确。")
        return parsed

    def check_connection(self) -> None:
        """Verify that the configured local service accepts a minimal request."""
        self._post(
            "/responses",
            {
                "model": "",
                "input": [{"role": "user", "content": "ping"}],
                "stream": False,
                "max_output_tokens": 1,
            },
        )

    def _post(self, path: str, payload: dict) -> dict:
        try:
            response = self._session.post(
                f"{self.base_url}{path}", json=payload, timeout=self.timeout_seconds
            )
        except requests.Timeout as error:
            raise LocalModelConnectionError("本地大模型请求超时，请稍后重试或增加超时时间。") from error
        except requests.RequestException as error:
            raise LocalModelConnectionError(
                "无法连接本地大模型服务。请确认服务已启动，且地址设置正确。"
            ) from error
        return self._read_response(response)

    @staticmethod
    def _read_response(response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError as error:
            raise LocalModelResponseError("本地大模型返回了无法识别的响应。") from error
        if not response.ok:
            message = data.get("error") if isinstance(data, Mapping) else None
            if isinstance(message, Mapping):
                message = message.get("message")
            raise LocalModelResponseError(
                str(message or f"本地大模型请求失败（HTTP {response.status_code}）。")
            )
        if not isinstance(data, dict):
            raise LocalModelResponseError("本地大模型返回的响应格式不正确。")
        return data

    @staticmethod
    def _extract_output_text(data: Mapping[str, object]) -> str:
        output = data.get("output")
        if not isinstance(output, list):
            raise LocalModelResponseError("本地大模型未返回文本内容。")
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, Mapping) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
        raise LocalModelResponseError("本地大模型未返回文本内容。")

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            return "\n".join(lines[1:-1]).strip()
        return stripped
