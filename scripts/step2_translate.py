"""步骤 2：翻译验证 — DeepSeek API 英文→中文。

用法: uv run python scripts/step2_translate.py --input workdir/asr/segments.json --out workdir/trans/translations.json
依赖环境变量 DEEPSEEK_API_KEY。
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from common import dump_json, load_json, setup_logging

log = logging.getLogger("step2_translate")

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

SYSTEM_PROMPT = (
    "你是专业的视频字幕翻译。把给定的英文字幕翻译成自然、口语化的简体中文，"
    "保留说话人语气。只输出译文本身，不要任何解释、引号或编号。"
)


def translate_text(text: str) -> str:
    from openai import OpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("缺少 DEEPSEEK_API_KEY 环境变量")

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="DeepSeek 翻译")
    parser.add_argument("--input", type=Path, required=True, help="segments.json")
    parser.add_argument("--out", type=Path, default=None, help="translations.json")
    args = parser.parse_args()

    segments = load_json(args.input)
    translated = []
    for seg in segments:
        zh = translate_text(seg["text"])
        translated.append(
            {
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "src": seg["text"],
                "tgt": zh,
            }
        )
        log.info("  [%s] %s -> %s", seg["id"], seg["text"], zh)

    out = args.out or args.input.parent.parent / "trans" / "translations.json"
    dump_json(translated, out)
    log.info("翻译完成: %d 段 -> %s", len(translated), out)


if __name__ == "__main__":
    main()
