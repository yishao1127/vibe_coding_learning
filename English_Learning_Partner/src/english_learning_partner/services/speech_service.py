"""Offline English pronunciation through Windows Speech API (SAPI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..domain.errors import LocalSpeechError

BRITISH_LCID = "809"
AMERICAN_LCID = "409"


@dataclass(frozen=True)
class SpeechResult:
    requested_accent: str
    actual_accent: str

    @property
    def message(self) -> str:
        labels = {"british": "英式", "american": "美式", "english": "英语"}
        requested = labels[self.requested_accent]
        actual = labels[self.actual_accent]
        return f"正在朗读{actual}发音。" if requested == actual else f"未找到{requested}语音，已使用{actual}英语朗读。"


class SpeechService:
    """Speak an English word using a locally installed Windows SAPI voice."""

    def __init__(self, dispatch: Callable[[str], Any] | None = None) -> None:
        self._dispatch = dispatch

    def speak(self, word: str, accent: str) -> SpeechResult:
        if accent not in {"british", "american"}:
            raise LocalSpeechError("不支持的发音类型。")
        if not word.strip():
            raise LocalSpeechError("没有可朗读的英文单词。")
        try:
            import pythoncom
            import win32com.client
        except ImportError as error:
            raise LocalSpeechError("无法使用 Windows 本地语音服务。") from error

        pythoncom.CoInitialize()
        try:
            voice = (self._dispatch or win32com.client.Dispatch)("SAPI.SpVoice")
            token, actual_accent = self._select_voice(voice.GetVoices(), accent)
            if token is None:
                raise LocalSpeechError("未找到英语语音。请在 Windows 设置中安装英语（美国）或英语（英国）语音包。")
            voice.Voice = token
            voice.Speak(word.strip())
            return SpeechResult(accent, actual_accent)
        except LocalSpeechError:
            raise
        except Exception as error:
            raise LocalSpeechError("无法朗读。请确认 Windows 英语语音和音频设备可用。") from error
        finally:
            pythoncom.CoUninitialize()

    @classmethod
    def _select_voice(cls, voices: Any, accent: str) -> tuple[Any | None, str]:
        candidates = list(voices)
        preferred = BRITISH_LCID if accent == "british" else AMERICAN_LCID
        alternate = AMERICAN_LCID if accent == "british" else BRITISH_LCID
        for language, actual_accent in ((preferred, accent), (alternate, "american" if accent == "british" else "british")):
            for token in candidates:
                if cls._has_language(token, language):
                    return token, actual_accent
        for token in candidates:
            if cls._has_english_language(token):
                return token, "english"
        return None, "english"

    @staticmethod
    def _has_language(token: Any, lcid: str) -> bool:
        languages = str(token.GetAttribute("Language")).lower().split(";")
        return any(value.lstrip("0") == lcid.lstrip("0") for value in languages)

    @staticmethod
    def _has_english_language(token: Any) -> bool:
        languages = str(token.GetAttribute("Language")).lower().split(";")
        return any(value.lstrip("0").endswith("09") for value in languages)
