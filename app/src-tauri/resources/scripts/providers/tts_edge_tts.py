"""edge-tts 配音 provider — 微软在线 TTS（免费）。"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from providers.base import ProviderInfo, TtsProvider
from providers.registry import register

log = logging.getLogger("providers.tts_edge_tts")

DEFAULT_VOICE = "zh-CN-YunxiNeural"


@register
class EdgeTtsProvider(TtsProvider):
    info = ProviderInfo(
        name="edge-tts",
        label="Edge TTS (微软, 免费)",
        stage="tts",
        kind="api",
        config_fields=[
            {"key": "voice", "label": "音色（如 zh-CN-YunxiNeural）", "type": "text"},
            {"key": "rate", "label": "语速（如 +0%）", "type": "text"},
        ],
    )

    def synthesize(self, text: str, out_path: Path, config: dict) -> Path:
        import edge_tts

        voice = config.get("voice") or DEFAULT_VOICE
        rate = config.get("rate") or "+0%"

        async def _synth() -> None:
            tts = edge_tts.Communicate(text, voice, rate=rate)
            await tts.save(str(out_path))

        asyncio.run(_synth())
        return out_path
