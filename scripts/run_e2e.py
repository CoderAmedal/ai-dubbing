"""端到端入口：视频 → ASR → 翻译 → TTS → 混音 → 成片。

用法:
    uv run python scripts/run_e2e.py --input assets/demo.mp4 --output output/out.mp4

依赖环境变量 DEEPSEEK_API_KEY（步骤2 翻译）。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from common import (
    DEFAULT_MODEL_DIR,
    PROJECT_ROOT,
    dump_json,
    ensure_workdir,
    setup_logging,
)
from step1_asr import extract_audio, to_srt, transcribe
from step2_translate import translate_text
from step3_tts import synth_sync
from step4_mux import build_audio, make_srt, mux

log = logging.getLogger("run_e2e")


def run_pipeline(input_video: Path, out_path: Path, model_dir: Path) -> None:
    work = ensure_workdir(f"e2e/{input_video.stem}")

    # 1. ASR
    log.info("=== 步骤 1/4: ASR 识别 ===")
    audio = work / "audio.wav"
    extract_audio(input_video, audio)
    segments = transcribe(audio, model_dir)
    seg_json = work / "segments.json"
    dump_json(segments, seg_json)
    seg_json.with_suffix(".srt").write_text(to_srt(segments), encoding="utf-8")

    # 2. 翻译
    log.info("=== 步骤 2/4: 翻译 (DeepSeek) ===")
    translated = []
    for seg in segments:
        translated.append(
            {
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "src": seg["text"],
                "tgt": translate_text(seg["text"]),
            }
        )
    trans_json = work / "translations.json"
    dump_json(translated, trans_json)

    # 3. TTS
    log.info("=== 步骤 3/4: TTS (edge-tts) ===")
    tts_dir = work / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    for seg in translated:
        synth_sync(seg, tts_dir / f"seg_{seg['id']:03d}.mp3")

    # 4. 混音 + 字幕
    log.info("=== 步骤 4/4: 混音 + 烧录字幕 ===")
    voiceover = work / "voiceover.wav"
    build_audio(tts_dir, translated, voiceover)
    srt = work / "subs_zh.srt"
    make_srt(translated, srt)
    mux(input_video, voiceover, srt, out_path)

    log.info("=== 完成: %s ===", out_path)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="端到端配音链路")
    parser.add_argument("--input", type=Path, required=True, help="输入视频")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "out.mp4")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    run_pipeline(args.input, args.output, args.model)


if __name__ == "__main__":
    main()
