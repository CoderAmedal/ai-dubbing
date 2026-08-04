"""步骤 1：ASR 验证 — 语音识别 + 时间戳。

用法: uv run python scripts/step1_asr.py --input assets/demo.mp4 --out workdir/asr/segments.json
产出: 带时间戳的分段 JSON（同时生成 SRT 字幕）。
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
    get_ffmpeg,
    run,
    setup_logging,
)

log = logging.getLogger("step1_asr")


def extract_audio(video: Path, out_audio: Path) -> None:
    if out_audio.exists():
        log.info("音频已存在，跳过提取: %s", out_audio)
        return
    ffmpeg = get_ffmpeg()
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(out_audio),
        ]
    )
    log.info("音频提取完成: %s", out_audio)


def transcribe(audio: Path, model_dir: Path) -> list[dict]:
    from faster_whisper import WhisperModel

    log.info("加载模型 %s (device=cpu, compute_type=int8)", model_dir)
    model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        str(audio),
        vad_filter=True,
        language="en",
        beam_size=5,
    )
    log.info("检测语言 %s, 时长 %.1fs", info.language, info.duration)

    results = []
    for i, seg in enumerate(segments):
        results.append(
            {
                "id": i,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
            }
        )
    return results


def to_srt(segments: list[dict]) -> str:
    def fmt(sec: float) -> str:
        ms = round(sec * 1000)
        h, rem = divmod(ms, 3600_000)
        m, rem = divmod(rem, 60_000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = []
    for seg in segments:
        blocks.append(
            f"{seg['id'] + 1}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text']}\n"
        )
    return "\n".join(blocks)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="ASR 识别")
    parser.add_argument("--input", type=Path, required=True, help="视频或音频文件")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--work", type=Path, default=PROJECT_ROOT / "workdir" / "asr")
    parser.add_argument("--out", type=Path, default=None, help="分段 JSON 输出路径")
    args = parser.parse_args()

    work = ensure_workdir(args.work.name)
    audio = work / "audio.wav"
    extract_audio(args.input, audio)
    segments = transcribe(audio, args.model)

    out_json = args.out or work / "segments.json"
    dump_json(segments, out_json)
    srt_path = out_json.with_suffix(".srt")
    srt_path.write_text(to_srt(segments), encoding="utf-8")
    log.info("ASR 完成: %d 段 -> %s / %s", len(segments), out_json, srt_path)

    for seg in segments:
        log.info("  [%6.2f -> %6.2f] %s", seg["start"], seg["end"], seg["text"])


if __name__ == "__main__":
    main()
