"""基线测量 — 量化译文 vs 原时长差异与停顿分布。

用法:
  uv run python scripts/measure_baseline.py --trans workdir/e2e/demo/translations.json --tts workdir/e2e/demo/tts/

输出:
  - 每段原时长 vs 中文 TTS 时长、时长差与百分比
  - 段间空隙分布（原时间轴 vs 合成后）
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from common import load_json, setup_logging

log = logging.getLogger("measure_baseline")


def audio_duration(path: Path) -> float:
    import soundfile as sf

    return sf.info(str(path)).duration


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="基线测量")
    parser.add_argument("--trans", type=Path, required=True, help="translations.json")
    parser.add_argument("--tts", type=Path, required=True, help="TTS 段目录")
    args = parser.parse_args()

    segments = load_json(args.trans)
    print(f"{'id':>3} {'orig':>6} {'zh':>6} {'delta':>7} {'pct%':>7}  gap_orig  gap_zh")
    total_orig_gap = 0.0
    total_zh_gap = 0.0
    for i, seg in enumerate(segments):
        orig_dur = seg["end"] - seg["start"]
        zh_file = args.tts / f"seg_{seg['id']:03d}.mp3"
        if not zh_file.exists():
            zh_file = args.tts / f"seg_{seg['id']:03d}.wav"
        zh_dur = audio_duration(zh_file)
        delta = zh_dur - orig_dur
        pct = delta / orig_dur * 100

        # 与前一段的空隙
        gap_orig = 0.0
        gap_zh = 0.0
        if i > 0:
            prev = segments[i - 1]
            gap_orig = seg["start"] - prev["end"]
            # 合成轨上 zh 段的间隔
            prev_zh = args.tts / f"seg_{prev['id']:03d}.mp3"
            if not prev_zh.exists():
                prev_zh = args.tts / f"seg_{prev['id']:03d}.wav"
            prev_zh_dur = audio_duration(prev_zh)
            gap_zh = seg["start"] - (prev["start"] + prev_zh_dur)
            total_orig_gap += gap_orig
            total_zh_gap += gap_zh

        print(
            f"{seg['id']:>3} {orig_dur:>6.2f} {zh_dur:>6.2f} {delta:>+7.2f} {pct:>+6.1f}%"
            f"  {gap_orig:>7.2f}  {gap_zh:>7.2f}"
        )

    print(f"\n总空隙: 原时间轴 {total_orig_gap:.2f}s, 合成轨 {total_zh_gap:.2f}s")
    print("(gap_zh > 1.5 表示硬对齐后出现突兀停顿)")


if __name__ == "__main__":
    main()
