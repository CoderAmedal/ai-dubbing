"""whisper.cpp ASR provider — 轻量 CPU (ggml)，经 pywhispercpp。

模型为 GGML .bin 格式，从 HF 下载（ggml-org/whisper.cpp 仓库）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from runtime import resolve_model_dir

from providers.base import AsrProvider, ProviderInfo, format_models
from providers.registry import register

log = logging.getLogger("providers.asr_whisper_cpp")

WHISPER_CPP_MODELS = [
    {"name": "tiny", "repo": "ggml-org/whisper.cpp", "filename": "ggml-tiny.bin", "size": "~75M", "description": "最快"},
    {"name": "base", "repo": "ggml-org/whisper.cpp", "filename": "ggml-base.bin", "size": "~145M", "description": "轻量"},
    {"name": "small", "repo": "ggml-org/whisper.cpp", "filename": "ggml-small.bin", "size": "~466M", "description": "推荐"},
    {"name": "medium", "repo": "ggml-org/whisper.cpp", "filename": "ggml-medium.bin", "size": "~1.5G", "description": "高准确"},
    {"name": "large-v3", "repo": "ggml-org/whisper.cpp", "filename": "ggml-large-v3.bin", "size": "~3G", "description": "最佳"},
]


@register
class WhisperCppProvider(AsrProvider):
    info = ProviderInfo(
        name="whisper.cpp",
        label="Whisper.cpp (本地, GGML)",
        stage="asr",
        kind="local",
        requires_model=True,
        models=format_models(WHISPER_CPP_MODELS),
        config_fields=[
            {"key": "model", "label": "模型大小", "type": "select", "options": [m["name"] for m in WHISPER_CPP_MODELS]},
            {"key": "language", "label": "语言（如 en/zh，留空自动检测）", "type": "text"},
        ],
    )

    def _model_path(self, config: dict) -> Path:
        model_name = config.get("model") or "small"
        meta = next((m for m in WHISPER_CPP_MODELS if m["name"] == model_name), None)
        if meta is None:
            raise ValueError(f"未知模型: {model_name}")
        return resolve_model_dir() / "whisper.cpp" / meta["filename"]

    def transcribe(self, audio: Path, config: dict) -> list[dict]:
        from pywhispercpp.model import Model

        model_path = self._model_path(config)
        if not model_path.exists():
            raise FileNotFoundError(f"模型未下载: {model_path}（请在设置中下载 {model_path.stem}）")

        log.info("whisper.cpp 加载 %s (n_threads=8)", model_path)
        model = Model(
            model=model_path,
            n_threads=8,
            language=config.get("language") or "auto",
        )
        segments = model.transcribe(str(audio))
        results = []
        for i, seg in enumerate(segments):
            results.append(
                {"id": i, "start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip()}
            )
        return results
