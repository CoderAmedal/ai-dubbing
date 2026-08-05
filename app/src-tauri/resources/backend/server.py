"""FastAPI 后端 — 任务队列 + SSE 进度上报。

由 Tauri 壳作为子进程拉起，监听 127.0.0.1:<port>。
前端通过 HTTP API 提交任务、订阅 SSE 进度。

用法:
  uv run python backend/server.py --port 8756
  （也可直接 uvicorn backend.server:app --port 8756）
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common import setup_logging

setup_logging()

import providers  # noqa: F401 — 注册 provider
from glossary import GlossaryStore
from model_manager import download_model, list_models
from providers.registry import list_providers
from run_e2e import run_pipeline
from runtime import ensure_data_dirs, resolve_output_dir
from settings import ensure_env, sanitize_proxy
from settings import load as load_settings
from settings import save as save_settings
from task_manager import manager

ensure_data_dirs()

log = logging.getLogger("server")

app = FastAPI(title="AI 配音工作台后端", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = resolve_output_dir()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "project": PROJECT_ROOT.name}


@app.get("/api/settings")
def get_settings() -> dict:
    s = load_settings()
    return {
        "deepseek_api_key": bool(s.get("deepseek_api_key")),
        "providers": {
            "asr": s.get("asr", {}),
            "translate": s.get("translate", {}),
            "tts": s.get("tts", {}),
        },
        "data_dir": str(resolve_output_dir().parent),
    }


@app.post("/api/settings")
def post_settings(payload: dict) -> dict:
    save_settings({k: v for k, v in payload.items() if v})
    ensure_env()
    return {"saved": True}


@app.get("/api/providers")
def get_providers() -> dict:
    """按环节列出 provider 元信息（GUI 表单渲染用）。"""
    from collections import defaultdict

    by_stage: dict[str, list] = defaultdict(list)
    for info in list_providers():
        by_stage[info.stage].append(
            {
                "name": info.name,
                "label": info.label,
                "kind": info.kind,
                "requires_model": info.requires_model,
                "config_fields": info.config_fields,
                "models": info.models,
            }
        )
    return dict(by_stage)


@app.get("/api/models")
def get_models() -> list:
    return list_models()


@app.post("/api/models")
def post_model(payload: dict) -> dict:
    provider = payload.get("provider")
    model = payload.get("model")
    if not provider:
        raise HTTPException(400, "缺少 provider")
    state = download_model(provider, model)
    return {"key": state["key"]}


@app.get("/api/models/state/{key}")
def get_model_state(key: str) -> dict:
    from model_manager import get_download_state

    state = get_download_state(key)
    if not state:
        raise HTTPException(404, f"无此下载: {key}")
    return state


@app.get("/api/glossary")
def get_glossary() -> dict:
    store = GlossaryStore()
    return {"items": store.items, "count": len(store.items)}


@app.post("/api/glossary")
def post_glossary(payload: dict) -> dict:
    """payload: {"items": {"源": "译"}} 或 {"action": "delete", "src": "..."}"""
    store = GlossaryStore()
    if payload.get("action") == "delete":
        store.delete(payload["src"])
    else:
        for src, tgt in payload.get("items", {}).items():
            store.set(src, tgt)
    return {"count": len(store.items)}


@app.post("/api/glossary/import")
async def glossary_import(file: UploadFile):
    """导入 CSV 词库。"""
    import tempfile

    content = await file.read()
    store = GlossaryStore()
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(content)
        tmp = Path(f.name)
    try:
        added = store.import_csv(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    return {"added": added, "count": len(store.items)}


def _default_output(input_name: str) -> Path:
    return OUTPUT_DIR / f"{Path(input_name).stem}_dubbed.mp4"


@app.post("/api/tasks")
def create_task(payload: dict) -> dict:
    """提交配音任务。

    必需: video_path
    可选: tts_backend(edge-tts/gpt-sovits), multi_speaker(bool),
          ref_audio, prompt_text, num_speakers, speed, sovits_api, out_path
    """
    video = payload.get("video_path")
    if not video:
        raise HTTPException(400, "缺少 video_path")

    video_path = Path(video)
    if not video_path.exists():
        raise HTTPException(400, f"视频不存在: {video}")

    task = manager.create(payload)

    def runner(task_obj) -> str:
        ensure_env()  # 从设置注入 DEEPSEEK_API_KEY
        sanitize_proxy()  # 清理 socks:// 代理（T-003）
        out = payload.get("out_path") or _default_output(video_path.stem)
        settings = load_settings()
        run_pipeline(
            input_video=video_path,
            out_path=Path(out),
            settings=settings,
            tts_backend=payload.get("tts_backend", "edge-tts"),
            ref_audio=payload.get("ref_audio"),
            prompt_lang=payload.get("prompt_lang", "en"),
            prompt_text=payload.get("prompt_text", ""),
            sovits_api=payload.get("sovits_api", "http://127.0.0.1:9880"),
            speed=float(payload.get("speed", 1.0)),
            multi_speaker=bool(payload.get("multi_speaker", False)),
            num_speakers=payload.get("num_speakers"),
            elastic_timeline=bool(payload.get("elastic_timeline", False)),
            progress=lambda pct, msg: task_obj.set("running", progress=pct, message=msg),
        )
        return str(out)

    manager.run(task, runner)
    return {"task_id": task.id}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = manager.get(task_id)
    if not task:
        raise HTTPException(404, f"任务不存在: {task_id}")
    return task.to_dict()


@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str):
    """SSE 进度流，直到任务结束。"""
    task = manager.get(task_id)
    if not task:
        raise HTTPException(404, f"任务不存在: {task_id}")

    async def gen():
        while True:
            try:
                event = task._events.get(timeout=15)
                yield {"event": event["type"], "data": __import__("json").dumps(event)}
                if event["type"] == "end":
                    break
            except Exception:  # noqa: BLE001 — SSE 心跳保活
                yield {"comment": "ping"}

    return EventSourceResponse(gen())


@app.get("/api/output/{filename}")
def get_output(filename: str):
    """下载/预览成片。"""
    fpath = OUTPUT_DIR / filename
    if not fpath.exists():
        raise HTTPException(404, f"文件不存在: {filename}")
    return FileResponse(fpath, media_type="video/mp4", filename=filename)


def _parent_watchdog(parent_pid: int) -> None:
    """父进程死亡则自杀（配合 Tauri 壳，避免僵尸后端）。"""
    def _watch() -> None:
        while True:
            time.sleep(2)
            try:
                os.kill(parent_pid, 0)
            except (ProcessLookupError, PermissionError):
                log.info("父进程 %d 已退出，后端自动关闭", parent_pid)
                os._exit(0)

    threading.Thread(target=_watch, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 配音工作台后端")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8756)
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=None,
        help="Tauri 壳传入的父进程 PID，父进程退出后本服务自动关闭",
    )
    args = parser.parse_args()

    if args.parent_pid:
        _parent_watchdog(args.parent_pid)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
