"""Provider 抽象层 — ASR / 翻译 / 配音三环节可插拔。

每个环节一个接口 + 注册表，用户配置选择 provider，模型全部自下载。
导入本包即注册全部内置 provider。
"""

from . import (
    asr_faster_whisper,  # noqa: F401
    asr_whisper_cpp,  # noqa: F401
    translate_deepseek,  # noqa: F401
    tts_edge_tts,  # noqa: F401
    tts_gpt_sovits,  # noqa: F401
)
from .registry import get_provider, list_providers, resolve_provider_config  # noqa: F401
