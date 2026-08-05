"""GPT-SoVITS 配音 provider — 本地 few-shot 音色克隆。

参考音频由说话人分离阶段自动提取（speaker_ref），或用户指定。
"""

from __future__ import annotations

import logging
from pathlib import Path

from providers.base import ProviderInfo, TtsProvider
from providers.registry import register

log = logging.getLogger("providers.tts_gpt_sovits")


@register
class GptSovitsProvider(TtsProvider):
    info = ProviderInfo(
        name="gpt-sovits",
        label="GPT-SoVITS (本地音色克隆)",
        stage="tts",
        kind="local",
        config_fields=[
            {"key": "api_url", "label": "API 地址（默认 127.0.0.1:9880）", "type": "text"},
            {"key": "ref_audio", "label": "参考音频路径", "type": "text"},
            {"key": "prompt_text", "label": "参考音频转写文本", "type": "text"},
            {"key": "prompt_lang", "label": "参考音频语言", "type": "text"},
            {"key": "speed_factor", "label": "语速因子", "type": "number"},
        ],
    )

    def synthesize(self, text: str, out_path: Path, config: dict) -> Path:
        from voice_clone import clone_tts

        ref_audio = config.get("ref_audio")
        if not ref_audio:
            raise RuntimeError("GPT-SoVITS 需要参考音频路径")

        return clone_tts(
            text=text,
            ref_audio_path=str(ref_audio),
            prompt_lang=config.get("prompt_lang", "en"),
            prompt_text=config.get("prompt_text", ""),
            api_url=config.get("api_url", "http://127.0.0.1:9880"),
            out_path=out_path,
            speed_factor=float(config.get("speed_factor", 1.0)),
        )
