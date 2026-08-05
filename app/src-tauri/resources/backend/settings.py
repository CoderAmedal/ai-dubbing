"""应用设置持久化 — 存到用户数据目录 settings.json（已 gitignore）。

支持 provider 配置：
{
  "deepseek_api_key": "...",
  "asr":   {"provider": "faster-whisper", "model": "small", ...},
  "translate": {"provider": "deepseek", "api_key": "...", ...},
  "tts":   {"provider": "edge-tts", "voice": "zh-CN-YunxiNeural", ...}
}
桌面应用 GUI 中配置，后端进程在跑任务前读取。
"""

from __future__ import annotations

import json
import os
import threading

from runtime import resolve_settings_file

SETTINGS_FILE = resolve_settings_file()

_lock = threading.RLock()  # save() 内部调用 load()，需可重入锁

DEFAULTS: dict = {
    "deepseek_api_key": "",
    "asr": {},
    "translate": {},
    "tts": {},
}


def load() -> dict:
    with _lock:
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                return _deep_merge(dict(DEFAULTS), data)
            except json.JSONDecodeError:
                return dict(DEFAULTS)
        return dict(DEFAULTS)


def save(settings: dict) -> dict:
    with _lock:
        current = load()
        for key, value in settings.items():
            if isinstance(value, dict):
                # provider 配置段：合并而非整体覆盖（保留其它字段）
                current.setdefault(key, {})
                for k, v in value.items():
                    if v not in (None, ""):
                        current[key][k] = v
            elif value not in (None, ""):
                current[key] = value
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(
            json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return current


def ensure_env() -> None:
    """若环境变量缺失，用已保存的设置补齐 DEEPSEEK_API_KEY。"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        saved = load().get("deepseek_api_key")
        if saved:
            os.environ["DEEPSEEK_API_KEY"] = saved


def sanitize_proxy() -> None:
    """清理 httpx 不识别的 socks:// 代理（T-003）。

    本机 all_proxy=socks://127.0.0.1:7897，httpx 仅支持 socks5://。
    DeepSeek API 可直连，故移除 all_proxy/ALL_PROXY 让 httpx 走直连；
    http_proxy/https_proxy（http:// 前缀）保留不动。
    """
    for var in ("all_proxy", "ALL_PROXY"):
        value = os.environ.get(var, "")
        if value.startswith("socks://"):
            os.environ.pop(var, None)


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
