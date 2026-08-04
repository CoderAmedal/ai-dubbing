"""步骤 3：TTS 验证 — edge-tts 中文配音（占位，后续接 GPT-SoVITS 音色克隆）。

用法: uv run python scripts/step3_tts.py --input workdir/trans/translations.json --out workdir/tts/
产出: 每段一句中文语音（tts/seg_<id>.mp3）。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from common import load_json, setup_logging

log = logging.getLogger("step3_tts")

VOICE = "zh-CN-YunxiNeural"


async def synth(seg: dict, out: Path) -> None:
    import edge_tts

    tts = edge_tts.Communicate(seg["tgt"], VOICE, rate="+0%")
    await tts.save(str(out))
    log.info("  [%s] %s -> %s", seg["id"], seg["tgt"], out.name)


def synth_sync(seg: dict, out: Path) -> None:
    asyncio.run(synth(seg, out))


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="edge-tts 中文配音")
    parser.add_argument("--input", type=Path, required=True, help="translations.json")
    parser.add_argument("--out", type=Path, default=None, help="输出目录")
    args = parser.parse_args()

    segments = load_json(args.input)
    out_dir = args.out or (args.input.parent.parent / "tts")
    out_dir.mkdir(parents=True, exist_ok=True)

    async def run_all() -> None:
        tasks = [synth(seg, out_dir / f"seg_{seg['id']:03d}.mp3") for seg in segments]
        await asyncio.gather(*tasks)

    asyncio.run(run_all())
    log.info("TTS 完成: %d 段 -> %s", len(segments), out_dir)


if __name__ == "__main__":
    main()
