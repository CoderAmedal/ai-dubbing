"""voice_clone.py — GPT-SoVITS few-shot 音色克隆 TTS 后端。

通过本地 GPT-SoVITS API (默认 127.0.0.1:9880) 合成语音，
输入：中文文本 + 参考音频路径 → 输出：克隆音色的 WAV 文件。

用法:
    from voice_clone import clone_tts
    wav_path = clone_tts("你好世界", ref_audio_path="ref.wav")

CLI:
    uv run python scripts/voice_clone.py --text "你好世界" --ref ref.wav --out out.wav
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import requests

log = logging.getLogger("voice_clone")

DEFAULT_API = "http://127.0.0.1:9880"


def clone_tts(
    text: str,
    ref_audio_path: str,
    prompt_lang: str = "en",
    prompt_text: str = "",
    api_url: str = DEFAULT_API,
    out_path: str | Path | None = None,
    speed_factor: float = 1.0,
) -> Path:
    """调用 GPT-SoVITS API 合成语音，返回 WAV 路径。"""
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": str(Path(ref_audio_path).resolve()),
        "prompt_lang": prompt_lang,
        "prompt_text": prompt_text,
        "media_type": "wav",
        "speed_factor": speed_factor,
        "streaming_mode": False,
    }
    log.info("GPT-SoVITS POST %s/tts  text=%s", api_url, text[:40])
    session = requests.Session()
    session.trust_env = False  # 绕过系统代理（GPT-SoVITS 为本地服务）
    resp = session.post(f"{api_url}/tts", json=payload, timeout=300)
    if resp.status_code != 200:
        raise RuntimeError(f"GPT-SoVITS {resp.status_code}: {resp.text[:200]}")
    content_type = resp.headers.get("content-type", "")
    if "json" in content_type:
        raise RuntimeError(f"GPT-SoVITS 返回错误: {resp.text[:200]}")
    if out_path is None:
        out_path = Path("sovits_output.wav")
    else:
        out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    log.info("克隆语音已保存: %s (%.1f KB)", out_path, len(resp.content) / 1024)
    return out_path


def check_server(api_url: str = DEFAULT_API) -> bool:
    try:
        requests.get(f"{api_url}/control", params={"command": "exit"}, timeout=2)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="GPT-SoVITS 音色克隆 TTS")
    parser.add_argument("--text", required=True, help="要合成的中文文本")
    parser.add_argument("--ref", required=True, help="参考音频路径")
    parser.add_argument("--prompt-lang", default="en", help="参考音频语言 (default: en)")
    parser.add_argument("--prompt-text", default="", help="参考音频转写文本（可选，提高准确度）")
    parser.add_argument("--api", default=DEFAULT_API, help="GPT-SoVITS API 地址")
    parser.add_argument("--out", default=None, help="输出 WAV 路径")
    args = parser.parse_args()

    out = clone_tts(
        text=args.text,
        ref_audio_path=args.ref,
        prompt_lang=args.prompt_lang,
        prompt_text=args.prompt_text,
        api_url=args.api,
        out_path=args.out,
    )
    print(out)


if __name__ == "__main__":
    main()
