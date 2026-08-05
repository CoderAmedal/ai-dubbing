"""步骤 4：混音验证 — ffmpeg 合成配音 + 原视频 + 烧录字幕。

用法: uv run python scripts/step4_mux.py \
    --video assets/demo.mp4 \
    --tts workdir/tts/ \
    --trans workdir/trans/translations.json \
    --out output/out.mp4

逻辑：TTS 段按原时间轴平移到音轨，替换原声，烧录中文 SRT 字幕。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from common import (
    PROJECT_ROOT,
    ensure_workdir,
    get_ffmpeg,
    load_json,
    run,
    setup_logging,
)

log = logging.getLogger("step4_mux")


def build_audio(tts_dir: Path, trans: list[dict], out_wav: Path) -> None:
    ffmpeg = get_ffmpeg()
    # 拼接 ffmpeg 命令：把每个 TTS 段用 adelay 移到目标时间，再 amix
    inputs: list[str] = []
    delays: list[str] = []
    for i, seg in enumerate(trans):
        audio_file = tts_dir / f"seg_{seg['id']:03d}.mp3"
        if not audio_file.exists():
            audio_file = tts_dir / f"seg_{seg['id']:03d}.wav"
        if not audio_file.exists():
            raise FileNotFoundError(f"缺少 TTS 段: seg_{seg['id']:03d} (.mp3/.wav)")
        inputs += ["-i", str(audio_file)]
        ms = int(seg["start"] * 1000)
        delays.append(f"[{i}:0]adelay={ms}|{ms}[d{i}]")
    mix_in = "".join(f"[d{i}]" for i in range(len(trans)))
    filter_complex = ";".join(delays) + f";{mix_in}amix=inputs={len(trans)}:normalize=0[aout]"

    cmd = [
        ffmpeg,
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-ar",
        "44100",
        "-ac",
        "2",
        str(out_wav),
    ]
    run(cmd)


def make_srt(trans: list[dict], path: Path) -> None:
    def fmt(sec: float) -> str:
        ms = round(sec * 1000)
        h, rem = divmod(ms, 3600_000)
        m, rem = divmod(rem, 60_000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = []
    for seg in trans:
        blocks.append(
            f"{seg['id'] + 1}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['tgt']}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


def mux(video: Path, audio: Path, srt: Path, out: Path) -> None:
    ffmpeg = get_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        "subtitles=" + srt.as_posix()
        + ":force_style='FontName=Noto Serif CJK SC,FontSize=18,"
        + "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=2'"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-shortest",
            str(out),
        ]
    )
    log.info("成片输出（含烧录字幕）: %s", out)


def mux_elastic(video: Path, audio: Path, srt: Path, out: Path) -> None:
    """弹性时间轴模式：配音长于视频时冻结末帧延长视频，避免截断结尾语音。"""
    ffmpeg = get_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)

    audio_dur = audio_duration(audio)
    video_dur = video_duration(video)

    vf = (
        "subtitles=" + srt.as_posix()
        + ":force_style='FontName=Noto Serif CJK SC,FontSize=18,"
        + "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BorderStyle=1,Outline=2'"
    )
    if audio_dur > video_dur + 0.05:
        # 冻结末帧延长到配音长度
        vf = f"tpad=stop_mode=clone:stop_duration={audio_dur - video_dur:.3f},{vf}"
        log.info("视频延长 %.2fs 以容纳配音", audio_dur - video_dur)

    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-shortest",
            str(out),
        ]
    )
    log.info("成片输出（弹性时间轴+烧录字幕）: %s", out)


def audio_duration(path: Path) -> float:
    import soundfile as sf

    return sf.info(str(path)).duration


def video_duration(path: Path) -> float:
    """用 ffmpeg probe 视频时长（只读头部，不解码全片）。"""
    import subprocess

    ffmpeg = get_ffmpeg()
    result = subprocess.run(
        [ffmpeg, "-i", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    import re

    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise RuntimeError(f"无法读取视频时长: {path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="混音合成")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--tts", type=Path, required=True, help="TTS 段目录")
    parser.add_argument("--trans", type=Path, required=True, help="translations.json")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    trans = load_json(args.trans)
    work = ensure_workdir("mux")
    audio = work / "voiceover.wav"
    srt = work / "subs_zh.srt"

    build_audio(args.tts, trans, audio)
    make_srt(trans, srt)

    out = args.out or (PROJECT_ROOT / "output" / f"{args.video.stem}_dubbed.mp4")
    mux(args.video, audio, srt, out)


if __name__ == "__main__":
    main()
