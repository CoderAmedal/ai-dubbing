"""speaker_ref.py — 为每个说话人提取参考音频 + prompt 文本。

从 diarization 分段中，为每个唯一说话人选取最长的分段，
提取为参考音频（GPT-SoVITS 音色克隆用），并用 faster-whisper
转写该片段作为 prompt_text（提高克隆准确度）。

用法:
  uv run python scripts/speaker_ref.py \
    --audio workdir/asr/audio.wav \
    --diarize workdir/diarize/segments.json \
    --work workdir/refs

产出:
  workdir/refs/SPEAKER_XX.wav   (每说话人参考音频)
  workdir/refs/refs.json        ({speaker: {audio, prompt_text, prompt_lang}})
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from common import (
    DEFAULT_MODEL_DIR,
    dump_json,
    get_ffmpeg,
    load_json,
    run,
    setup_logging,
)
from step1_asr import transcribe

log = logging.getLogger("speaker_ref")

MARGIN = 0.1  # 参考音频前后边距（秒）
MIN_REF_DURATION = 3.0  # GPT-SoVITS 要求参考音频 3~10 秒
MAX_REF_DURATION = 10.0  # GPT-SoVITS 参考音频上限

OTHER_SPEAKER_MAX_OVERLAP = 0.2  # 扩展窗口时允许与其它说话人重叠的秒数


def audio_duration(audio: Path) -> float:
    import soundfile as sf

    return sf.info(str(audio)).duration


def select_reference_segment(
    speaker_segments: list[dict],
    all_segments: list[dict],
    duration: float,
) -> dict | None:
    """选取说话人最长的分离分段作为参考（含 0.1s 边距，clamp 到音频范围内）。

    若最长分段不足 MIN_REF_DURATION，向两侧对称扩展窗口到最小时长，
    扩展时尽量避免覆盖其它说话人的语音（超过 OTHER_SPEAKER_MAX_OVERLAP 则停）。
    """
    best: dict | None = None
    for seg in speaker_segments:
        start = max(0.0, seg["start"] - MARGIN)
        end = min(duration, seg["end"] + MARGIN)
        if best is None or (end - start) > (best["end"] - best["start"]):
            best = {"start": start, "end": end}

    if best is None:
        return None

    other_ranges = [
        (max(0.0, s["start"]), min(duration, s["end"]))
        for s in all_segments
        if s.get("speaker") and s["speaker"] != speaker_segments[0].get("speaker")
    ]
    window = _expand_window(best, duration, other_ranges)
    return _trim_to_max(window, duration)


def _trim_to_max(window: dict, duration: float) -> dict:
    """参考音频超长时裁剪到 MAX_REF_DURATION（取窗口中间段，避开开头/结尾静音）。"""
    if (window["end"] - window["start"]) <= MAX_REF_DURATION:
        return window
    mid = (window["start"] + window["end"]) / 2
    half = MAX_REF_DURATION / 2
    start = max(0.0, mid - half)
    end = min(duration, mid + half)
    # 若在边界导致不足 MAX，向另一侧补足
    if end - start < MAX_REF_DURATION:
        if start == 0.0:
            end = min(duration, start + MAX_REF_DURATION)
        elif end == duration:
            start = max(0.0, end - MAX_REF_DURATION)
    return {"start": start, "end": end}


def _expand_window(
    window: dict, duration: float, other_ranges: list[tuple[float, float]]
) -> dict:
    """把窗口对称扩展到 MIN_REF_DURATION，同时避开其它说话人语音。"""
    start, end = window["start"], window["end"]
    while (end - start) < MIN_REF_DURATION:
        grow_left = start - 0.05 >= 0.0
        grow_right = end + 0.05 <= duration
        if not grow_left and not grow_right:
            break

        candidates = []
        if grow_left:
            new_start = start - 0.05
            if _other_overlap(new_start, start, other_ranges) <= OTHER_SPEAKER_MAX_OVERLAP:
                candidates.append(("left", new_start, start))
        if grow_right:
            new_end = end + 0.05
            if _other_overlap(end, new_end, other_ranges) <= OTHER_SPEAKER_MAX_OVERLAP:
                candidates.append(("right", end, new_end))

        if not candidates:
            break

        # 优先扩展与其它说话人重叠少的一侧
        side, a, b = min(candidates, key=lambda c: _other_overlap(c[1], c[2], other_ranges))
        if side == "left":
            start = a
        else:
            end = b

    return {"start": start, "end": end}


def _other_overlap(
    a: float, b: float, other_ranges: list[tuple[float, float]]
) -> float:
    """计算窗口 [a,b] 与其它说话人分段时间的重叠总量。"""
    total = 0.0
    for s, e in other_ranges:
        total += max(0.0, min(b, e) - max(a, s))
    return total


def extract_clip(audio: Path, start: float, end: float, out: Path) -> None:
    ffmpeg = get_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(audio),
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(out),
        ]
    )
    log.info("参考音频提取: %s (%.2fs)", out, end - start)


def extract_references(
    audio: Path,
    diarize_segments: list[dict],
    work_dir: Path,
    model_dir: Path,
) -> dict:
    """为每个说话人生成参考音频 + prompt 文本，返回 refs 配置。"""
    duration = audio_duration(audio)
    log.info("音频时长 %.2fs", duration)

    by_speaker: dict[str, list[dict]] = {}
    for seg in diarize_segments:
        by_speaker.setdefault(seg["speaker"], []).append(seg)

    refs: dict[str, dict] = {}
    for speaker, segs in sorted(by_speaker.items()):
        best = select_reference_segment(segs, diarize_segments, duration)
        if best is None:
            log.warning("说话人 %s 无可用分段，跳过", speaker)
            continue

        clip = work_dir / f"{speaker}.wav"
        extract_clip(audio, best["start"], best["end"], clip)

        segs_text = transcribe(clip, model_dir)
        prompt_text = " ".join(s["text"] for s in segs_text).strip()
        log.info("说话人 %s prompt_text: %s", speaker, prompt_text)

        refs[speaker] = {
            "audio": str(clip.resolve()),
            "prompt_text": prompt_text,
            "prompt_lang": "en",
        }

    refs_json = work_dir / "refs.json"
    dump_json(refs, refs_json)
    log.info("参考音频配置 -> %s (%d 个说话人)", refs_json, len(refs))
    return refs


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="说话人参考音频提取")
    parser.add_argument("--audio", type=Path, required=True, help="音频 WAV (16kHz)")
    parser.add_argument("--diarize", type=Path, required=True, help="diarize segments.json")
    parser.add_argument("--work", type=Path, default=Path("workdir/refs"))
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    diarize_segments = load_json(args.diarize)
    extract_references(args.audio, diarize_segments, args.work, args.model)


if __name__ == "__main__":
    main()
