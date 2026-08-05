"""守护方式启动后端服务（双 fork 完全脱离调用方进程组）。

用法: uv run python backend/launch_server.py --port 8756
Tauri 壳与开发调试均通过本脚本拉起后端子进程。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "workdir" / "server.log"


def daemonize() -> None:
    """经典双 fork 守护化：脱离控制终端、会话与进程组。"""
    if os.fork() > 0:
        os._exit(0)  # 父进程退出
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())


def main() -> None:
    parser = argparse.ArgumentParser(description="守护启动后端")
    parser.add_argument("--port", type=int, default=8756)
    args = parser.parse_args()

    daemonize()

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
    import uvicorn
    from server import app

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
