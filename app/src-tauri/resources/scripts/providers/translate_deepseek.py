"""DeepSeek 翻译 provider — 支持专业词库注入。"""

from __future__ import annotations

import logging
import os

from providers.base import ProviderInfo, TranslateProvider
from providers.registry import register

log = logging.getLogger("providers.translate_deepseek")

SYSTEM_PROMPT = (
    "你是专业的视频字幕翻译。把给定的外文文本翻译成自然、口语化的简体中文，"
    "保留说话人语气。只输出译文本身，不要任何解释、引号或编号。"
)


def _build_system_prompt(glossary: dict | None) -> str:
    prompt = SYSTEM_PROMPT
    if glossary:
        terms = "\n".join(f"- {src} → {tgt}" for src, tgt in glossary.items())
        prompt += (
            "\n\n【专业术语表，必须严格遵守】\n"
            f"{terms}\n"
            "翻译时遇到上述术语，必须使用给出的译法，保持术语一致。"
        )
    return prompt


@register
class DeepSeekTranslateProvider(TranslateProvider):
    info = ProviderInfo(
        name="deepseek",
        label="DeepSeek (API)",
        stage="translate",
        kind="api",
        config_fields=[
            {"key": "api_key", "label": "API Key", "type": "password"},
            {"key": "base_url", "label": "Base URL（可选）", "type": "text"},
            {"key": "model", "label": "模型（可选）", "type": "text"},
        ],
    )

    def translate(self, text: str, config: dict, glossary: dict | None = None) -> str:
        from openai import OpenAI

        api_key = config.get("api_key") or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("缺少 DeepSeek API Key（请在设置中配置）")

        base_url = config.get("base_url") or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = config.get("model") or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _build_system_prompt(glossary)},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
