"""合成服务 — 字幕烧录 / 软封装 / 音轨混合（合成页后端）。

设计稿：design-pic/合成.png（选视频+字幕+可选配音音轨 → 样式 → 烧录硬字幕/封装软字幕）。
复用 step4_mux 的 ffmpeg 封装；样式经 subtitle_style.to_force_style 注入。

用法：
  from mux_service import burn_subtitles, embed_soft_subtitles
  burn_subtitles(video, srt, out, style={...}, audio=None)
  embed_soft_subtitles(video, srt, out_mkv)
"""

from __future__ import annotations

import logging
from pathlib import Path

from common import get_ffmpeg, run
from subtitle_style import to_force_style

log = logging.getLogger("mux_service")


def burn_subtitles(
    video: Path,
    srt: Path,
    out: Path,
    style: dict | None = None,
    audio: Path | None = None,
) -> None:
    """烧录硬字幕（可混合配音音轨替换原声）。

    video + srt（必需）；audio 可选（提供则替换原声轨）。
    style 见 subtitle_style（None=经典白字黑边）。
    """
    ffmpeg = get_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = f"subtitles={srt.as_posix()}:force_style='{to_force_style(style)}'"

    cmd = [ffmpeg, "-y", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    if audio:
        cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    else:
        cmd += ["-c:a", "copy"]
    cmd += [str(out)]
    run(cmd)
    log.info("硬字幕烧录完成: %s", out)


def embed_soft_subtitles(
    video: Path,
    srt: Path,
    out: Path,
    audio: Path | None = None,
) -> None:
    """封装软字幕（MKV 容器，流拷贝不重编码，秒出）。"""
    ffmpeg = get_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() != ".mkv":
        out = out.with_suffix(".mkv")

    cmd = [ffmpeg, "-y", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-i", str(srt)]
    cmd += ["-map", "0:v"]
    if audio:
        cmd += ["-map", "1:a"]
    else:
        cmd += ["-map", "0:a?"]
    cmd += ["-map", "2:s" if audio else "1:s"]
    cmd += ["-c", "copy", "-c:s", "srt", str(out)]
    run(cmd)
    log.info("软字幕封装完成: %s", out)


def replace_audio(video: Path, audio: Path, out: Path) -> None:
    """替换视频音轨（配音页"导出成品"：视频流拷贝，仅换音频，不重编码）。"""
    ffmpeg = get_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg, "-y",
            "-i", str(video), "-i", str(audio),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", str(out),
        ]
    )
    log.info("音轨替换完成: %s", out)
