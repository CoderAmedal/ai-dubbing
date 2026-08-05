"""共享工具：路径、ffmpeg、结构化日志。"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from runtime import resolve_model_dir, resolve_output_dir, resolve_workdir

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 兼容旧引用：默认值走 runtime 解析（dev=仓库，打包=用户数据目录）
DEFAULT_MODEL_DIR = resolve_model_dir() / "faster-whisper-small"
DEFAULT_WORKDIR = resolve_workdir()
DEFAULT_OUTPUT = resolve_output_dir()


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def get_ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    logging.getLogger("common").info("运行: %s", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def load_json(path: Path) -> list | dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_workdir(name: str) -> Path:
    d = DEFAULT_WORKDIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d
