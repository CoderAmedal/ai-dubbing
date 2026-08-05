"""弹性时间轴 + 长停顿剪辑 — 让中文配音语速自然。

问题：硬对齐（adelay+amix 按原时间轴放置）会压缩/重叠译文。
本模块：
  1. 变速补偿：译文与原时长差 >±15% 时用 rubberband/atempo 变速到限幅
  2. 漂移放置：段按序放置，累积漂移吸收时长差（单段 ≤500ms，全局 ≤2s）
  3. 停顿裁剪：段间空隙 >1.5s 裁剪到 0.8s
  4. 输出：新时间轴 + 合成轨 + 字幕时间

用法:
  uv run python scripts/timeline.py --trans workdir/e2e/demo/translations.json \
      --tts workdir/e2e/demo/tts/ --work workdir/e2e/demo/timeline \
      --video-duration 8.0
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from common import dump_json, get_ffmpeg, load_json, run, setup_logging

log = logging.getLogger("timeline")

SPEED_MAX = 1.15  # 变速上限（加速）
SPEED_MIN = 0.85  # 变速下限（减速）
DRIFT_PER_SEG = 0.5  # 单段偏移上限（秒）
DRIFT_GLOBAL = 2.0  # 全局漂移上限（秒）
PAUSE_CLIP_THRESHOLD = 1.5  # 长停顿阈值（秒）
PAUSE_TARGET = 0.8  # 裁剪后停顿目标（秒）


def audio_duration(path: Path) -> float:
    import soundfile as sf

    return sf.info(str(path)).duration


def pick_speed(zh_dur: float, orig_dur: float) -> float:
    """根据译文/原时长比决定变速倍率（限幅 ±15%）。"""
    if orig_dur <= 0:
        return 1.0
    ratio = zh_dur / orig_dur
    if ratio > SPEED_MAX:
        return SPEED_MAX
    if ratio < SPEED_MIN:
        return SPEED_MIN
    return 1.0


def tempo_change(src: Path, speed: float, out: Path) -> None:
    """变速（优先 rubberband，失败退 atempo）。"""
    if abs(speed - 1.0) < 1e-6:
        return
    ffmpeg = get_ffmpeg()
    for af in (f"rubberband=tempo={speed}", f"atempo={speed}"):
        try:
            run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(src),
                    "-af",
                    af,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(out),
                ]
            )
            return
        except Exception as exc:  # noqa: BLE001 — 尝试下一种变速滤镜
            log.info("变速 %s 失败，尝试下一种: %s", af, exc)
            continue
    raise RuntimeError(f"变速失败: {src} ({af})")


def compute_placements(
    segments: list[dict],
    video_duration: float,
) -> list[dict]:
    """计算每段的变速倍率、变速后时长与新时间轴位置。

    输入 segments 需含: id, start, end, tgt_audio(路径)
    输出在原 dict 上补充: orig_dur, zh_dur, speed, ndur, new_start, new_end
    """
    n = len(segments)
    # 按原时间轴排序
    segments.sort(key=lambda s: s["start"])

    for s in segments:
        s["orig_dur"] = s["end"] - s["start"]
        if "zh_dur" not in s:
            s["zh_dur"] = audio_duration(Path(s["tgt_audio"]))
        s["speed"] = pick_speed(s["zh_dur"], s["orig_dur"])
        s["ndur"] = s["zh_dur"] / s["speed"]

    drift = 0.0
    prev_out_end = 0.0
    for i, s in enumerate(segments):
        ideal = s["start"] + drift
        # 单段偏移约束
        ideal = max(s["start"] - DRIFT_PER_SEG, min(s["start"] + DRIFT_PER_SEG, ideal))

        start = max(prev_out_end, ideal)  # 不重叠（顺序音频下优先于漂移约束）
        gap = start - prev_out_end
        if gap > PAUSE_CLIP_THRESHOLD:
            start = prev_out_end + PAUSE_TARGET  # 长停顿裁剪
        elif gap < 0:
            start = prev_out_end

        s["new_start"] = start
        s["new_end"] = start + s["ndur"]
        prev_out_end = s["new_end"]

        # 漂移更新：本段相对原窗口的溢出
        overrun = s["new_end"] - s["end"]
        drift += overrun
        if i + 1 < n:
            gap = segments[i + 1]["start"] - s["new_end"]
            if gap > 0:
                drift = max(0.0, drift - gap)  # 段间空隙吸收漂移
        drift = min(drift, DRIFT_GLOBAL)

    return segments


def prepare_speed_files(segments: list[dict], work_dir: Path) -> list[dict]:
    """为需要变速的段生成变速音频，更新 tgt_audio 指向变速文件。"""
    prepared = []
    for s in segments:
        src = Path(s["tgt_audio"])
        if abs(s["speed"] - 1.0) < 1e-6:
            prepared.append(s)
            continue
        out = work_dir / f"seg_{s['id']:03d}_t{s['speed']:.2f}.wav"
        tempo_change(src, s["speed"], out)
        s["tgt_audio"] = str(out)
        s["zh_dur"] = audio_duration(out)
        s["ndur"] = s["zh_dur"]
        prepared.append(s)
    return prepared


def build_track(segments: list[dict], work_dir: Path, out_wav: Path) -> None:
    """用 adelay+amix 按新时间轴合成音轨（段间无重叠）。"""
    ffmpeg = get_ffmpeg()
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    inputs: list[str] = []
    delays: list[str] = []
    for i, s in enumerate(segments):
        audio_file = s["tgt_audio"]
        inputs += ["-i", audio_file]
        ms = int(s["new_start"] * 1000)
        delays.append(f"[{i}:0]adelay={ms}|{ms}[d{i}]")

    mix_in = "".join(f"[d{i}]" for i in range(len(segments)))
    filter_complex = ";".join(delays) + f";{mix_in}amix=inputs={len(segments)}:normalize=0[aout]"
    run(
        [
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
    )


def build_timeline(
    trans: list[dict],
    tts_dir: Path,
    work_dir: Path,
    video_duration: float,
) -> tuple[list[dict], Path]:
    """完整弹性时间轴流程，返回（新时间轴, 合成轨路径）。

    trans 每项需含 id/start/end；tgt_audio 指向译文音频。
    """
    for t in trans:
        t["tgt_audio"] = str(tts_dir / f"seg_{t['id']:03d}.mp3")
        if not Path(t["tgt_audio"]).exists():
            t["tgt_audio"] = str(tts_dir / f"seg_{t['id']:03d}.wav")

    work_dir.mkdir(parents=True, exist_ok=True)
    segments = compute_placements(trans, video_duration)
    prepare_speed_files(segments, work_dir)

    voiceover = work_dir / "voiceover.wav"
    build_track(segments, work_dir, voiceover)

    timeline = [
        {
            "id": s["id"],
            "start": round(s["new_start"], 3),
            "end": round(s["new_end"], 3),
            "speed": s["speed"],
            "src": s.get("src", ""),
            "tgt": s.get("tgt", ""),
        }
        for s in segments
    ]
    dump_json(timeline, work_dir / "timeline.json")
    return timeline, voiceover


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="弹性时间轴")
    parser.add_argument("--trans", type=Path, required=True, help="translations.json")
    parser.add_argument("--tts", type=Path, required=True, help="TTS 段目录")
    parser.add_argument("--work", type=Path, default=None, help="输出目录")
    parser.add_argument("--video-duration", type=float, default=10.0, help="视频时长(秒)")
    args = parser.parse_args()

    trans = load_json(args.trans)
    work = args.work or args.trans.parent / "timeline"
    work.mkdir(parents=True, exist_ok=True)

    timeline, voiceover = build_timeline(trans, args.tts, work, args.video_duration)
    log.info("弹性时间轴完成: %s / %s", voiceover, work / "timeline.json")
    for s in timeline:
        log.info(
            "  [%6.2f -> %6.2f] speed=%.2f %s",
            s["start"],
            s["end"],
            s["speed"],
            s["tgt"],
        )


if __name__ == "__main__":
    main()
