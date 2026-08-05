"""端到端入口：视频 → ASR → 翻译 → TTS → 混音 → 成片。

用法:
  edge-tts（默认）:
    uv run python scripts/run_e2e.py --input assets/demo.mp4 --output output/out.mp4
  gpt-sovits（音色克隆）:
    uv run python scripts/run_e2e.py --input assets/demo.mp4 --output output/out.mp4 \
      --tts gpt-sovits --ref-audio workdir/sovits/ref_audio.wav \
      --prompt-text "Hello everyone, welcome to the AI dubbing studio."
  gpt-sovits（多角色，各说话人自动克隆音色）:
    uv run python scripts/run_e2e.py --input assets/demo_multi.mp4 --output output/out_multi.mp4 \
      --tts gpt-sovits --multi-speaker --diarize
  弹性时间轴（中文语速自然优先）:
    uv run python scripts/run_e2e.py --input assets/demo.mp4 --output output/out_elastic.mp4 \
      --elastic-timeline

依赖环境变量 DEEPSEEK_API_KEY（步骤2 翻译）。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from pathlib import Path

from common import (
    DEFAULT_MODEL_DIR,
    PROJECT_ROOT,
    dump_json,
    ensure_workdir,
    setup_logging,
)
from speaker_diarize import run_diarization
from speaker_ref import extract_references
from step1_asr import extract_audio, to_srt, transcribe
from step2_translate import translate_text
from step3_tts import synth_edge_tts, synth_sovits
from step4_mux import build_audio, make_srt, mux, mux_elastic
from timeline import build_timeline

log = logging.getLogger("run_e2e")


def _apply_glossary_post(text: str, glossary: dict) -> str:
    """词库后处理校验替换：译文残留源语术语时替换为译语。"""
    for src, tgt in glossary.items():
        if src and src in text:
            text = text.replace(src, tgt)
    return text


def run_pipeline(
    input_video: Path,
    out_path: Path,
    model_dir: Path | None = None,
    tts_backend: str = "edge-tts",
    ref_audio: str | None = None,
    prompt_lang: str = "en",
    prompt_text: str = "",
    sovits_api: str = "http://127.0.0.1:9880",
    speed: float = 1.0,
    multi_speaker: bool = False,
    num_speakers: int | None = None,
    elastic_timeline: bool = False,
    settings: dict | None = None,
    progress: Callable[[int, str], None] | None = None,
) -> None:
    """执行完整配音链路。

    settings: 可选，provider 配置 {"asr": {...}, "translate": {...}, "tts": {...}}。
    提供后三环节走 provider；缺省回退到旧参数（model_dir/tts_backend 等），保持 CLI 兼容。
    progress: 可选回调，签名 progress(percent: int, message: str)。
    """

    def emit(pct: int, msg: str) -> None:
        if progress:
            progress(pct, msg)
        log.info("[%3d%%] %s", pct, msg)

    # 解析 provider（可选）
    asr_provider = tr_provider = tts_provider = None
    asr_cfg = tr_cfg = tts_cfg = {}
    glossary: dict = {}
    if settings:
        from glossary import load_glossary
        from providers.base import AsrProvider, TranslateProvider, TtsProvider
        from providers.registry import get_provider, resolve_provider_config

        asr_cfg = resolve_provider_config(settings, "asr")
        tr_cfg = resolve_provider_config(settings, "translate")
        tts_cfg = resolve_provider_config(settings, "tts")
        if asr_cfg.get("provider"):
            asr_provider = get_provider(asr_cfg["provider"], AsrProvider)
        if tr_cfg.get("provider"):
            tr_provider = get_provider(tr_cfg["provider"], TranslateProvider)
        if tts_cfg.get("provider"):
            tts_provider = get_provider(tts_cfg["provider"], TtsProvider)
        glossary = load_glossary()

    work = ensure_workdir(f"e2e/{input_video.stem}")

    # 1. ASR（多角色模式额外做说话人分离）
    if multi_speaker:
        emit(5, "步骤 1/5: ASR + 说话人分离")
    else:
        emit(5, "步骤 1/4: ASR 识别")
    audio = work / "audio.wav"
    extract_audio(input_video, audio)
    if asr_provider is not None:
        segments = asr_provider.transcribe(audio, asr_cfg)
    else:
        if model_dir is None:
            raise ValueError("未配置 ASR provider 且未提供 model_dir")
        segments = transcribe(audio, model_dir)
    if multi_speaker:
        diarize_segs = run_diarization(audio, num_speakers=num_speakers)
        from step1_asr import merge_speakers

        segments = merge_speakers(segments, diarize_segs)
    seg_json = work / "segments.json"
    dump_json(segments, seg_json)
    seg_json.with_suffix(".srt").write_text(to_srt(segments), encoding="utf-8")

    # 2. 多角色模式：提取各说话人参考音频（gpt-sovits）
    ref_map: dict | None = None
    sovits_mode = tts_backend == "gpt-sovits" or tts_cfg.get("provider") == "gpt-sovits"
    if multi_speaker and sovits_mode:
        emit(25, "步骤 2/5: 提取各说话人参考音频")
        ref_map = extract_references(audio, diarize_segs, work / "refs", model_dir)

    # 3. 翻译
    if multi_speaker:
        emit(30, "步骤 3/5: 翻译")
    else:
        emit(25, "步骤 2/4: 翻译")
    translated = []
    n = len(segments)
    for i, seg in enumerate(segments):
        if tr_provider is not None:
            tgt = tr_provider.translate(seg["text"], tr_cfg, glossary)
            tgt = _apply_glossary_post(tgt, glossary)
        else:
            tgt = translate_text(seg["text"])
        item = {
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "src": seg["text"],
            "tgt": tgt,
        }
        if multi_speaker:
            item["speaker"] = seg.get("speaker", "UNKNOWN")
        translated.append(item)
        if multi_speaker:
            emit(30 + int(10 * (i + 1) / n), f"翻译 {i + 1}/{n}")
        else:
            emit(25 + int(15 * (i + 1) / n), f"翻译 {i + 1}/{n}")
    trans_json = work / "translations.json"
    dump_json(translated, trans_json)

    # 4. TTS
    tts_dir = work / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    n = len(translated)
    if tts_provider is not None:
        emit(40, f"步骤 4/5: TTS ({tts_cfg.get('provider')})")
        for i, seg in enumerate(translated):
            seg_cfg = dict(tts_cfg)
            if ref_map is not None:
                speaker = seg.get("speaker", "UNKNOWN")
                rc = ref_map[speaker]
                seg_cfg["ref_audio"] = rc["audio"]
                seg_cfg["prompt_text"] = rc.get("prompt_text", seg_cfg.get("prompt_text", ""))
                seg_cfg["prompt_lang"] = rc.get("prompt_lang", seg_cfg.get("prompt_lang", "en"))
            tts_provider.synthesize(
                seg["tgt"], tts_dir / f"seg_{seg['id']:03d}.wav", seg_cfg
            )
            emit(40 + int(50 * (i + 1) / n), f"TTS 合成 {i + 1}/{n}")
    elif sovits_mode:
        emit(40, "步骤 4/5: TTS (gpt-sovits 音色克隆)")
        for i, seg in enumerate(translated):
            if ref_map is not None:
                speaker = seg.get("speaker", "UNKNOWN")
                cfg = ref_map[speaker]
                seg_ref_audio = cfg["audio"]
                seg_prompt_lang = cfg.get("prompt_lang", prompt_lang)
                seg_prompt_text = cfg.get("prompt_text", prompt_text)
            else:
                seg_ref_audio = ref_audio
                seg_prompt_lang = prompt_lang
                seg_prompt_text = prompt_text
            synth_sovits(
                seg,
                tts_dir / f"seg_{seg['id']:03d}.wav",
                ref_audio=seg_ref_audio,
                prompt_lang=seg_prompt_lang,
                prompt_text=seg_prompt_text,
                api_url=sovits_api,
                speed_factor=speed,
            )
            emit(40 + int(50 * (i + 1) / n), f"TTS 合成 {i + 1}/{n}")
    else:
        emit(40, "步骤 4/5: TTS (edge-tts)")
        for i, seg in enumerate(translated):
            synth_edge_tts(seg, tts_dir / f"seg_{seg['id']:03d}.mp3")
            emit(40 + int(50 * (i + 1) / n), f"TTS 合成 {i + 1}/{n}")

    # 5. 混音 + 字幕
    if elastic_timeline:
        emit(90, "步骤 5/5: 弹性时间轴 + 混音 + 烧录字幕")
        from step4_mux import video_duration

        video_dur = video_duration(input_video)
        timeline, voiceover = build_timeline(
            translated, tts_dir, work / "timeline", video_dur
        )
        srt = work / "subs_zh_elastic.srt"
        make_srt(timeline, srt)
        mux_elastic(input_video, voiceover, srt, out_path)
    else:
        emit(90, "步骤 5/5: 混音 + 烧录字幕")
        voiceover = work / "voiceover.wav"
        build_audio(tts_dir, translated, voiceover)
        srt = work / "subs_zh.srt"
        make_srt(translated, srt)
        mux(input_video, voiceover, srt, out_path)

    emit(100, "完成")
    log.info("=== 完成: %s ===", out_path)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="端到端配音链路")
    parser.add_argument("--input", type=Path, required=True, help="输入视频")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "out.mp4")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--tts", choices=["edge-tts", "gpt-sovits"], default="edge-tts", help="TTS 后端")
    parser.add_argument("--ref-audio", type=Path, default=None, help="参考音频 (gpt-sovits)")
    parser.add_argument("--prompt-lang", default="en", help="参考音频语言 (gpt-sovits)")
    parser.add_argument("--prompt-text", default="", help="参考音频转写文本 (gpt-sovits)")
    parser.add_argument("--sovits-api", default="http://127.0.0.1:9880", help="GPT-SoVITS API 地址")
    parser.add_argument("--speed", type=float, default=1.0, help="语速因子 (gpt-sovits)")
    parser.add_argument(
        "--multi-speaker",
        action="store_true",
        help="多角色模式：自动分离说话人并为每个角色提取/克隆音色",
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="预期说话人数量（配合 --multi-speaker，默认自动检测）",
    )
    parser.add_argument(
        "--elastic-timeline",
        action="store_true",
        help="弹性时间轴：中文语速自然优先（变速±15% + 长停顿裁剪）",
    )
    args = parser.parse_args()

    if args.tts == "gpt-sovits" and args.ref_audio is None and not args.multi_speaker:
        parser.error("--tts gpt-sovits 需要 --ref-audio 或 --multi-speaker")

    run_pipeline(
        args.input,
        args.output,
        args.model,
        tts_backend=args.tts,
        ref_audio=str(args.ref_audio) if args.ref_audio else None,
        prompt_lang=args.prompt_lang,
        prompt_text=args.prompt_text,
        sovits_api=args.sovits_api,
        speed=args.speed,
        multi_speaker=args.multi_speaker,
        num_speakers=args.num_speakers,
        elastic_timeline=args.elastic_timeline,
    )


if __name__ == "__main__":
    main()
