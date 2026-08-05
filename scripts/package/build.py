"""绿色版打包脚本 — 零捆绑核心包 + GPT-SoVITS 可选包。

流程：
  1. 创建可重定位 Python 环境（uv + python-build-standalone）
  2. 安装依赖（CPU torch 走 pytorch index）
  3. 拷贝 backend/ scripts/ static/ env → app/src-tauri/resources/
  4. tauri build 产出 AppImage（Linux）等

用法:
  uv run python scripts/package/build.py [--skip-env] [--skip-tauri]
  --skip-env   复用已构建的 resources/env（改代码后快速重打包）
  --skip-tauri 只准备资源，不跑 cargo/tauri build
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESOURCES = PROJECT_ROOT / "app" / "src-tauri" / "resources"
ENV_DIR = RESOURCES / "env"

log = logging.getLogger("build")

PY_VERSION = "3.11"


def env_python() -> Path:
    if sys.platform == "win32":
        return ENV_DIR / "Scripts" / "python.exe"
    return ENV_DIR / "bin" / "python"


def env_site_packages() -> Path:
    py = env_python()
    if sys.platform == "win32":
        return ENV_DIR / "Lib" / "site-packages"
    return py.parent.parent / "lib" / "python3.11" / "site-packages"

# 依赖：从 pyproject + CPU torch + pywhispercpp
BASE_DEPS = [
    "faster-whisper",
    "edge-tts",
    "imageio-ffmpeg",
    "openai",
    "requests",
    "diarize",
    "silero-vad",
    "wespeakerruntime",
    "scikit-learn",
    "soundfile",
    "fastapi",
    "uvicorn",
    "sse-starlette",
    "python-multipart",
    "pywhispercpp",
]
TORCH_DEPS = ["torch", "torchaudio", "torchcodec"]


def run(cmd: list[str], **kwargs) -> None:
    log.info("运行: %s", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def build_env() -> None:
    python = env_python()
    if ENV_DIR.exists() and python.exists():
        log.info("env 已存在，跳过构建: %s", ENV_DIR)
        return
    ENV_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 用 uv 建可重定位 venv（python-build-standalone）
    run(["uv", "venv", "--python", PY_VERSION, str(ENV_DIR)])

    # 2. 约束文件：锁定 torch 系列为 CPU 版（避免默认源解析到 CUDA）
    constraints = PROJECT_ROOT / "workdir" / "torch-cpu-constraints.txt"
    constraints.parent.mkdir(parents=True, exist_ok=True)
    constraints.write_text(
        "torch==2.13.0+cpu\ntorchaudio==2.11.0+cpu\ntorchcodec==0.15.0+cpu\n",
        encoding="utf-8",
    )

    # 3. 安装全部依赖（extra-index 提供 CPU torch，constraint 强制 CPU 版）
    run(
        [
            "uv", "pip", "install", "--python", str(python),
            "--index-url", "https://pypi.org/simple",
            "--extra-index-url", "https://download.pytorch.org/whl/cpu",
            "--constraint", str(constraints),
            *TORCH_DEPS, *BASE_DEPS,
        ]
    )

    # 4. 减小体积：清理缓存
    site = env_site_packages()
    shutil.rmtree(site / "pip", ignore_errors=True)
    for cache in site.glob("**/__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def copy_resources() -> None:
    """拷贝 backend/ scripts/ static/ 到 resources/。"""
    for name in ("backend", "scripts"):
        src = PROJECT_ROOT / name
        dst = RESOURCES / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    log.info("资源已拷贝: %s", RESOURCES)

    # 移除静态前端外的临时产物
    for p in (RESOURCES / "backend").rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)


def build_tauri() -> None:
    # 确保 cargo/rust 在 PATH（daemon 化后可能丢失 ~/.cargo）
    cargo_bin = Path.home() / ".cargo" / "bin"
    if cargo_bin.exists():
        os.environ["PATH"] = f"{cargo_bin}:{os.environ.get('PATH', '')}"
    os.environ.setdefault("DISPLAY", ":0")
    run(
        ["npm", "run", "tauri", "build"],
        cwd=PROJECT_ROOT / "app",
    )
    log.info("Tauri 构建完成")


def daemonize() -> None:
    """经典双 fork 守护化：脱离控制终端/会话/进程组，避免被调用方杀掉。"""
    import os as _os

    if _os.fork() > 0:
        _os._exit(0)
    _os.setsid()
    if _os.fork() > 0:
        _os._exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    log_file = PROJECT_ROOT / "workdir" / "build.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        _os.dup2(f.fileno(), sys.stdout.fileno())
        _os.dup2(f.fileno(), sys.stderr.fileno())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="绿色版打包")
    parser.add_argument("--skip-env", action="store_true", help="跳过 env 构建")
    parser.add_argument("--skip-tauri", action="store_true", help="只准备资源不构建")
    parser.add_argument("--daemon", action="store_true", help="双 fork 后台运行")
    args = parser.parse_args()

    if args.daemon:
        daemonize()

    copy_resources()
    if not args.skip_env:
        build_env()
    else:
        log.info("跳过 env 构建（--skip-env）")
    if not args.skip_tauri:
        build_tauri()


if __name__ == "__main__":
    main()
