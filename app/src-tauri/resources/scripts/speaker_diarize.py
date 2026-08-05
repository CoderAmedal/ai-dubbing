"""说话人分离模块 — 用 diarize 库判断“谁在什么时候说话”。

用法: uv run python scripts/diarize.py --input assets/demo_multi.mp4 --out workdir/diarize/segments.json
输出: [{start, end, speaker}, ...]，speaker 形如 SPEAKER_00。

也可作为库调用:
    from diarize import run_diarization
    segments = run_diarization(audio_path)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from common import (
    PROJECT_ROOT,
    dump_json,
    ensure_workdir,
    get_ffmpeg,
    run,
    setup_logging,
)

log = logging.getLogger("diarize")


def extract_audio(video: Path, out_audio: Path) -> None:
    """提取音频为 16kHz mono WAV（供 diarize 使用）。"""
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


def run_diarization(
    audio_path: Path,
    num_speakers: int | None = None,
) -> list[dict]:
    """执行说话人分离，返回带时间戳的分段列表。

    Args:
        audio_path: WAV 音频路径（16kHz mono）
        num_speakers: 预期说话人数量（None = 自动检测）

    Returns:
        [{"start": float, "end": float, "speaker": str}, ...]
    """
    from diarize import diarize as _diarize

    log.info("执行说话人分离: %s", audio_path)
    result = _diarize(str(audio_path), num_speakers=num_speakers)

    segments = []
    for seg in result:
        segments.append(
            {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "speaker": seg.speaker,
            }
        )

    log.info("分离完成: %d 个说话人段落", len(segments))
    for s in segments:
        log.info("  [%6.2f -> %6.2f] %s", s["start"], s["end"], s["speaker"])

    return segments


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="说话人分离")
    parser.add_argument("--input", type=Path, required=True, help="视频或音频文件")
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="预期说话人数量（默认自动检测）",
    )
    parser.add_argument("--work", type=Path, default=PROJECT_ROOT / "workdir" / "diarize")
    parser.add_argument("--out", type=Path, default=None, help="分段 JSON 输出路径")
    args = parser.parse_args()

    work = ensure_workdir(args.work.name)
    audio = work / "audio.wav"
    extract_audio(args.input, audio)

    segments = run_diarization(audio, num_speakers=args.num_speakers)

    out_json = args.out or work / "segments.json"
    dump_json(segments, out_json)
    log.info("说话人分离完成: %d 段 -> %s", len(segments), out_json)


if __name__ == "__main__":
    main()
