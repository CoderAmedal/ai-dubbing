"""Provider 接口定义 — ASR / 翻译 / 配音。

每个 provider 实现一个接口，注册到 registry。
配置 schema 描述 provider 需要的配置字段（GUI 据此渲染表单）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProviderInfo:
    """Provider 静态元信息，供注册表与 GUI 使用。"""

    name: str  # 唯一标识，如 "faster-whisper"
    label: str  # 展示名，如 "Faster-Whisper (本地)"
    stage: str  # "asr" | "translate" | "tts"
    kind: str = "local"  # "local" | "api"
    requires_model: bool = False  # 是否需要下载模型
    config_fields: list[dict] = field(default_factory=list)  # GUI 表单字段
    models: list[dict] = field(default_factory=list)  # 可选模型（requires_model 时）


class AsrProvider(ABC):
    info: ProviderInfo

    @abstractmethod
    def transcribe(self, audio: Path, config: dict) -> list[dict]:
        """识别音频，返回 [{id, start, end, text}]。"""


class TranslateProvider(ABC):
    info: ProviderInfo

    @abstractmethod
    def translate(self, text: str, config: dict, glossary: dict | None = None) -> str:
        """翻译文本，glossary 为 {源语: 译语} 专业词库。"""


class TtsProvider(ABC):
    info: ProviderInfo

    @abstractmethod
    def synthesize(self, text: str, out_path: Path, config: dict) -> Path:
        """合成语音到 out_path，返回音频路径。"""


def format_models(models: list[dict]) -> list[dict]:
    """规范化模型列表（缺省字段补全）。"""
    return [
        {
            "name": m.get("name", m["repo"]),
            "repo": m["repo"],
            "size": m.get("size", ""),
            "description": m.get("description", ""),
            "filename": m.get("filename"),
        }
        for m in models
    ]
