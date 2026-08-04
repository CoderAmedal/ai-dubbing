"""步骤 3：TTS 中文配音 — 支持 edge-tts / gpt-sovits 后端切换。

用法:
  edge-tts（默认）:
    uv run python scripts/step3_tts.py --input workdir/trans/translations.json --out workdir/tts/
  gpt-sovits（音色克隆）:
    uv run python scripts/step3_tts.py --input workdir/trans/translations.json --tts gpt-sovits \
      --ref-audio workdir/sovits/ref_audio.wav --prompt-lang en \
      --prompt-text "Hello everyone, welcome to the AI dubbing studio."
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from common import load_json, setup_logging

log = logging.getLogger("step3_tts")

DEFAULT_VOICE = "zh-CN-YunxiNeural"


def synth_edge_tts(seg: dict, out: Path, voice: str = DEFAULT_VOICE) -> None:
    import edge_tts

    async def _synth() -> None:
        tts = edge_tts.Communicate(seg["tgt"], voice, rate="+0%")
        await tts.save(str(out))

    asyncio.run(_synth())
    log.info("  [%s] (edge-tts) %s -> %s", seg["id"], seg["tgt"], out.name)


def synth_sovits(
    seg: dict,
    out: Path,
    ref_audio: str,
    prompt_lang: str = "en",
    prompt_text: str = "",
    api_url: str = "http://127.0.0.1:9880",
    speed_factor: float = 1.0,
) -> None:
    from voice_clone import clone_tts

    wav_path = clone_tts(
        text=seg["tgt"],
        ref_audio_path=ref_audio,
        prompt_lang=prompt_lang,
        prompt_text=prompt_text,
        api_url=api_url,
        out_path=out,
        speed_factor=speed_factor,
    )
    log.info("  [%s] (gpt-sovits) %s -> %s", seg["id"], seg["tgt"], wav_path.name)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="TTS 中文配音")
    parser.add_argument("--input", type=Path, required=True, help="translations.json")
    parser.add_argument("--out", type=Path, default=None, help="输出目录")
    parser.add_argument("--tts", choices=["edge-tts", "gpt-sovits"], default="edge-tts", help="TTS 后端")
    parser.add_argument("--ref-audio", type=Path, default=None, help="参考音频路径（gpt-sovits 必填）")
    parser.add_argument("--prompt-lang", default="en", help="参考音频语言")
    parser.add_argument("--prompt-text", default="", help="参考音频转写文本")
    parser.add_argument("--sovits-api", default="http://127.0.0.1:9880", help="GPT-SoVITS API 地址")
    parser.add_argument("--speed", type=float, default=1.0, help="语速因子 (gpt-sovits)")
    args = parser.parse_args()

    if args.tts == "gpt-sovits" and args.ref_audio is None:
        parser.error("--tts gpt-sovits 需要 --ref-audio")

    segments = load_json(args.input)
    out_dir = args.out or (args.input.parent.parent / "tts")
    out_dir.mkdir(parents=True, exist_ok=True)

    for seg in segments:
        out_path = out_dir / f"seg_{seg['id']:03d}.wav"
        if args.tts == "edge-tts":
            mp3_out = out_dir / f"seg_{seg['id']:03d}.mp3"
            synth_edge_tts(seg, mp3_out)
        else:
            synth_sovits(
                seg,
                out_path,
                ref_audio=str(args.ref_audio),
                prompt_lang=args.prompt_lang,
                prompt_text=args.prompt_text,
                api_url=args.sovits_api,
                speed_factor=args.speed,
            )

    log.info("TTS 完成 (%s): %d 段 -> %s", args.tts, len(segments), out_dir)


if __name__ == "__main__":
    main()
