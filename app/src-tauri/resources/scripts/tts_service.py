"""配音合成服务 — 单条/整段字幕 TTS 合成（配音页后端）。

设计稿：design-pic/配音.png（选字幕 → 左侧挑引擎音色 → 逐行试听修正 → 导出）。
支持：edge-tts（在线，voice 参数）、gpt-sovits（本地克隆，ref_audio 参数）。
合成产物缓存到数据目录 tts_preview/，同名文本+配置复用。

用法：
  from tts_service import synth_line, synth_segments
  wav = synth_line("你好世界", settings, voice_id=None)
  paths = synth_segments(segs, settings, progress=cb)
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from runtime import resolve_data_dir

log = logging.getLogger("tts_service")

PREVIEW_DIR = "tts_preview"


def _preview_dir() -> Path:
    d = resolve_data_dir() / PREVIEW_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve_tts_config(settings: dict, overrides: dict | None) -> tuple[str, dict]:
    """从 settings 取 TTS provider 与配置，应用 overrides（voice_id 等）。"""
    from providers.registry import resolve_provider_config

    cfg = resolve_provider_config(settings or {}, "tts")
    provider = cfg.pop("provider", "edge-tts")
    overrides = dict(overrides or {})

    # 允许显式指定引擎（配音页引擎切换）
    if overrides.get("provider"):
        provider = overrides.pop("provider")

    # voice_id → 查音色库注入 ref_audio
    voice_id = overrides.pop("voice_id", None)
    if voice_id:
        from voice_library import VoiceLibrary

        voice = VoiceLibrary().get(voice_id)
        if voice:
            provider = "gpt-sovits"
            cfg.update(
                {
                    "ref_audio": voice["ref_audio"],
                    "prompt_text": voice.get("prompt_text", ""),
                    "prompt_lang": voice.get("prompt_lang", "zh"),
                }
            )
    cfg.update({k: v for k, v in overrides.items() if v not in (None, "")})
    return provider, cfg


def synth_line(
    text: str,
    settings: dict,
    overrides: dict | None = None,
    use_cache: bool = True,
) -> Path:
    """合成单行文本为音频，返回路径（缓存命中直接返回）。"""
    from providers.registry import get_provider

    provider_name, cfg = _resolve_tts_config(settings, overrides)
    key = hashlib.md5(
        f"{provider_name}|{cfg.get('voice', '')}|{cfg.get('ref_audio', '')}|{text}".encode()
    ).hexdigest()[:16]
    # edge-tts 产出 MP3 内容，gpt-sovits 产出 WAV；扩展名须匹配真实格式
    ext = ".mp3" if provider_name == "edge-tts" else ".wav"
    out = _preview_dir() / f"{key}{ext}"
    if use_cache and out.exists():
        log.info("命中缓存: %s", out.name)
        return out

    provider = get_provider(provider_name)
    provider.synthesize(text, out, cfg)
    log.info("合成完成 (%s): %s -> %s", provider_name, text[:20], out.name)
    return out


def synth_segments(
    segments: list[dict],
    settings: dict,
    overrides: dict | None = None,
    progress=None,
) -> list[Path]:
    """批量合成字幕段（每段 {id, text/tgt}），progress(pct, msg)。"""
    total = len(segments)
    paths: list[Path] = []
    for i, seg in enumerate(segments):
        text = seg.get("tgt") or seg.get("text") or ""
        if progress:
            progress(i * 100 // total, f"[{i + 1}/{total}] {text[:20]}")
        paths.append(synth_line(text, settings, overrides))
    if progress:
        progress(100, f"合成完成 {total} 段")
    return paths


def build_track(segments: list[dict], audio_paths: list[Path], out_wav: Path) -> Path:
    """把逐段音频按时间轴（adelay+amix）合并为一条配音轨。"""
    from common import get_ffmpeg, run

    if len(segments) != len(audio_paths):
        raise ValueError("segments 与 audio_paths 数量不一致")
    if not segments:
        raise ValueError("无字幕段")
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = get_ffmpeg()
    inputs: list[str] = []
    delays: list[str] = []
    for i, (seg, path) in enumerate(zip(segments, audio_paths, strict=True)):
        inputs += ["-i", str(path)]
        ms = int(seg["start"] * 1000)
        delays.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]")
    mix_in = "".join(f"[d{i}]" for i in range(len(segments)))
    filter_complex = ";".join(delays) + f";{mix_in}amix=inputs={len(segments)}:normalize=0[aout]"
    run(
        [
            ffmpeg, "-y", *inputs,
            "-filter_complex", filter_complex,
            "-map", "[aout]", "-ar", "44100", "-ac", "2",
            str(out_wav),
        ]
    )
    log.info("配音轨合并完成: %s (%d 段)", out_wav, len(segments))
    return out_wav
