"""模型下载脚本：确保 faster-whisper 模型就位。

用法: uv run python scripts/download_model.py
下载源按环境变量 HF_ENDPOINT 指定（默认 huggingface.co，可设 https://hf-mirror.com）。
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from common import PROJECT_ROOT, setup_logging


def main() -> None:
    setup_logging()
    log = logging.getLogger("download_model")
    parser = argparse.ArgumentParser(description="下载 faster-whisper 模型")
    parser.add_argument("--repo", default="Systran/faster-whisper-small")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "models")
    args = parser.parse_args()

    local_dir = args.out / Path(args.repo).name
    if (local_dir / "model.bin").exists():
        log.info("模型已存在: %s，跳过下载", local_dir)
        return

    from huggingface_hub import snapshot_download

    log.info("下载模型 %s -> %s (HF_ENDPOINT=%s)", args.repo, local_dir, os.environ.get("HF_ENDPOINT", "huggingface.co"))
    snapshot_download(args.repo, local_dir=str(local_dir), max_workers=4)
    log.info("完成: %s", local_dir)


if __name__ == "__main__":
    main()
