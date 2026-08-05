"""运行时路径解析 — dev 与打包双模式。

打包模式下 Tauri 壳注入环境变量：
  AIDUBBING_ROOT  → 后端/脚本/静态资源根（应用安装位置）
  AIDUBBING_DATA  → 用户数据目录（workdir/output/settings/models）
dev 模式下无环境变量，回退到仓库根。

所有模块必须通过本模块解析路径，禁止硬编码。
"""

from __future__ import annotations

import os
from pathlib import Path

# 仓库根（dev 模式）：scripts/runtime.py 的父目录的父目录
_REPO_ROOT = Path(__file__).resolve().parent.parent

# 打包模式：运行时可能不再存在仓库结构，root 由环境变量注入
_ROOT_ENV = "AIDUBBING_ROOT"
_DATA_ENV = "AIDUBBING_DATA"


def resolve_root() -> Path:
    """应用资源根：打包=exe 旁 resources，dev=仓库根。"""
    root = os.environ.get(_ROOT_ENV)
    return Path(root) if root else _REPO_ROOT


def resolve_data_dir() -> Path:
    """用户数据目录：打包=OS app-data，dev=仓库 workdir。"""
    data = os.environ.get(_DATA_ENV)
    if data:
        return Path(data)
    return _REPO_ROOT / "workdir"


def resolve_workdir() -> Path:
    """处理中间产物目录（每个任务一个子目录）。"""
    return resolve_data_dir() / "tasks"


def resolve_output_dir() -> Path:
    """成片输出目录。"""
    return resolve_data_dir() / "output"


def resolve_model_dir() -> Path:
    """本地模型目录（用户下载的模型存这里）。"""
    return resolve_data_dir() / "models"


def resolve_settings_file() -> Path:
    """设置文件路径。"""
    return resolve_data_dir() / "settings.json"


def ensure_data_dirs() -> None:
    """确保数据目录存在（打包后用户目录可能不存在）。"""
    for d in (resolve_data_dir(), resolve_workdir(), resolve_output_dir(), resolve_model_dir()):
        d.mkdir(parents=True, exist_ok=True)
