"""模型下载管理器 — 统一的模型下载/进度/状态。

聚合各 provider 的模型清单，支持：
  - 列出可下载模型（含已安装状态）
  - 后台下载（带进度回调，可中断/续传）
  - 本地目录校验

用法：
  from model_manager import list_models, download_model
  models = list_models()
  download_model("faster-whisper", "small", progress=cb)
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import providers
from runtime import resolve_model_dir

log = logging.getLogger("model_manager")

_DOWNLOADS: dict[str, dict] = {}
_lock = threading.Lock()


def list_models() -> list[dict]:
    """聚合所有 requires_model 的 provider 的模型清单，标注本地已装状态。"""
    results = []
    model_dir = resolve_model_dir()
    for info in providers.list_providers():
        if not info.requires_model:
            continue
        for m in info.models:
            installed = _check_installed(info.name, m, model_dir)
            results.append(
                {
                    "provider": info.name,
                    "provider_label": info.label,
                    "model": m["name"],
                    "repo": m["repo"],
                    "size": m.get("size", ""),
                    "description": m.get("description", ""),
                    "filename": m.get("filename"),
                    "installed": installed,
                }
            )
    return results


def _check_installed(provider: str, model: dict, model_dir: Path) -> bool:
    if provider == "faster-whisper":
        return (model_dir / f"faster-whisper-{model['name']}" / "model.bin").exists()
    if provider == "whisper.cpp":
        return (model_dir / "whisper.cpp" / model["filename"]).exists()
    return False


def download_model(provider: str, model_name: str, progress=None) -> dict:
    """下载模型。progress(pct: int, msg: str) 可选。model_name 缺省取 provider 首个模型。"""
    key = f"{provider}:{model_name}"
    with _lock:
        if key in _DOWNLOADS and _DOWNLOADS[key].get("status") == "running":
            return _DOWNLOADS[key]

    state = {"key": key, "status": "running", "progress": 0, "message": "排队中"}
    with _lock:
        _DOWNLOADS[key] = state

    def _report(pct: int, msg: str) -> None:
        state["progress"] = pct
        state["message"] = msg
        if progress:
            progress(pct, msg)

    def _run() -> None:
        try:
            _report(1, "开始下载")
            target = _download_path(provider, model_name)
            if target.exists():
                _report(100, "已存在")
            else:
                _hf_download(provider, model_name, target, _report)
            state["status"] = "done"
            state["progress"] = 100
        except Exception as exc:
            log.exception("模型下载失败 %s", key)
            state["status"] = "failed"
            state["message"] = f"失败: {exc}"
        finally:
            _report(state["progress"], state["message"])

    threading.Thread(target=_run, daemon=True).start()
    return state


def get_download_state(key: str) -> dict | None:
    with _lock:
        return _DOWNLOADS.get(key)


def _download_path(provider: str, model_name: str) -> Path:
    from providers.base import AsrProvider
    from providers.registry import get_provider

    p = get_provider(provider, AsrProvider)
    # 通过 info.models 找到文件目标
    model_dir = resolve_model_dir()
    if provider == "faster-whisper":
        return model_dir / f"faster-whisper-{model_name}" / "model.bin"
    if provider == "whisper.cpp":
        meta = next((m for m in p.info.models if m["name"] == model_name), None)
        if meta is None:
            raise ValueError(f"未知模型: {model_name}")
        return model_dir / "whisper.cpp" / meta["filename"]
    raise ValueError(f"provider {provider} 不支持模型下载")


def _hf_download(provider: str, model_name: str, target: Path, progress) -> None:
    from huggingface_hub import hf_hub_download, snapshot_download
    from providers.base import AsrProvider
    from providers.registry import get_provider

    p = get_provider(provider, AsrProvider)
    meta = next((m for m in p.info.models if m["name"] == model_name), None)
    if meta is None:
        raise ValueError(f"未知模型: {model_name}")

    target.parent.mkdir(parents=True, exist_ok=True)

    if provider == "faster-whisper":
        # 整个仓库快照（多个文件）
        snapshot_download(meta["repo"], local_dir=str(target.parent), max_workers=4)
        progress(90, "模型文件已下载，校验中")
    elif provider == "whisper.cpp":
        # 单个 GGML 文件
        hf_hub_download(
            meta["repo"],
            meta["filename"],
            local_dir=str(target.parent),
            local_dir_use_symlinks=False,
        )
        progress(90, "模型文件已下载，校验中")
    else:
        raise ValueError(f"provider {provider} 不支持模型下载")

    if not target.exists():
        raise RuntimeError(f"下载完成后未找到模型文件: {target}")
