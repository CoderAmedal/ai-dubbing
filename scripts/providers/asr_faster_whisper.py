"""faster-whisper ASR provider — CTranslate2 加速，CPU int8。"""

from __future__ import annotations

import logging
from pathlib import Path

from runtime import resolve_model_dir

from providers.base import AsrProvider, ProviderInfo, format_models
from providers.registry import register

log = logging.getLogger("providers.asr_faster_whisper")

WHISPER_MODELS = [
    {"name": "tiny", "repo": "Systran/faster-whisper-tiny", "size": "~75M", "description": "最快，准确度较低"},
    {"name": "base", "repo": "Systran/faster-whisper-base", "size": "~145M", "description": "轻量，CPU 友好"},
    {"name": "small", "repo": "Systran/faster-whisper-small", "size": "~464M", "description": "推荐平衡，CPU 可用"},
    {"name": "medium", "repo": "Systran/faster-whisper-medium", "size": "~1.5G", "description": "高准确，CPU 偏慢"},
    {"name": "large-v3", "repo": "Systran/faster-whisper-large-v3", "size": "~3G", "description": "最佳准确度，内存需求高"},
]


@register
class FasterWhisperProvider(AsrProvider):
    info = ProviderInfo(
        name="faster-whisper",
        label="Faster-Whisper (本地)",
        stage="asr",
        kind="local",
        requires_model=True,
        models=format_models(WHISPER_MODELS),
        config_fields=[
            {"key": "model", "label": "模型大小", "type": "select", "options": [m["name"] for m in WHISPER_MODELS]},
            {"key": "language", "label": "语言（如 en/zh，留空自动检测）", "type": "text"},
        ],
    )

    def transcribe(self, audio: Path, config: dict) -> list[dict]:
        from faster_whisper import WhisperModel

        model_name = config.get("model") or "small"
        model_dir = resolve_model_dir() / f"faster-whisper-{model_name}"
        if not (model_dir / "model.bin").exists():
            raise FileNotFoundError(
                f"模型未下载: {model_dir}（请在设置中下载 {model_name} 模型）"
            )

        log.info("faster-whisper 加载 %s (device=cpu, compute_type=int8)", model_dir)
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")
        segments, _info = model.transcribe(
            str(audio),
            vad_filter=True,
            language=config.get("language") or None,
            beam_size=5,
        )
        results = []
        for i, seg in enumerate(segments):
            results.append(
                {"id": i, "start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip()}
            )
        return results
