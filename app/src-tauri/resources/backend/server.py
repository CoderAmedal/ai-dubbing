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
from downloader import download_urls, extract_urls, probe_engine
from glossary import GlossaryLibrary, GlossaryStore
from model_manager import download_model, list_models
from mux_service import burn_subtitles, embed_soft_subtitles, replace_audio
from providers.registry import list_providers
from run_e2e import run_pipeline, translate_srt_file
from runtime import ensure_data_dirs, resolve_data_dir, resolve_output_dir
from settings import ensure_env, sanitize_proxy
from settings import load as load_settings
from settings import save as save_settings
from step1_asr import parse_srt, to_srt
from task_manager import manager
from tts_service import build_track, synth_line, synth_segments
from voice_library import VoiceLibrary

ensure_data_dirs()

log = logging.getLogger("server")

APP_VERSION = "0.8.0"

app = FastAPI(title="AI 配音工作台后端", version=APP_VERSION)

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
    return {"status": "ok", "project": PROJECT_ROOT.name, "version": APP_VERSION}


# ---------- 环境就绪度（启动台右面板） ----------

_ENV_CACHE: dict = {"at": 0.0, "data": None}
_ENV_TTL = 30.0


def _probe_gpu() -> dict:
    """GPU 加速探测：torch.cuda 可用即就绪。"""
    try:
        import torch

        if torch.cuda.is_available():
            return {"ready": True, "label": "已就绪", "detail": torch.cuda.get_device_name(0)}
        return {"ready": False, "label": "待检测", "detail": "未检测到可用 CUDA 设备"}
    except Exception:  # noqa: BLE001 — torch 未装等情况
        return {"ready": False, "label": "待检测", "detail": "torch 不可用"}


def _probe_asr(settings: dict) -> dict:
    """语音模型：当前 ASR provider 的模型是否已安装。"""
    provider = (settings.get("asr") or {}).get("provider", "faster-whisper")
    models = [m for m in list_models() if m["provider"] == provider]
    if not models:
        return {"ready": True, "label": "已就绪", "detail": "无需下载模型"}
    installed = [m for m in models if m["installed"]]
    if installed:
        return {"ready": True, "label": "已就绪", "detail": installed[0]["model"]}
    return {"ready": False, "label": "未下载", "detail": f"{provider} 模型未安装"}


def _probe_translate(settings: dict) -> dict:
    """翻译服务：provider 是否已配置凭据。"""
    cfg = settings.get("translate") or {}
    provider = cfg.get("provider", "deepseek")
    if provider == "deepseek":
        if settings.get("deepseek_api_key"):
            return {"ready": True, "label": "已配置", "detail": "DeepSeek"}
        return {"ready": False, "label": "未配置", "detail": "缺少 API Key"}
    return {"ready": True, "label": "已配置", "detail": provider}


def _probe_tts(settings: dict) -> dict:
    """配音服务：edge-tts 恒就绪；gpt-sovits 探测本地 9880。"""
    cfg = settings.get("tts") or {}
    provider = cfg.get("provider", "edge-tts")
    if provider == "gpt-sovits":
        import socket

        api = cfg.get("sovits_api", "http://127.0.0.1:9880")
        host, _, port = api.rpartition("//")[2].partition(":")
        try:
            with socket.create_connection((host or "127.0.0.1", int(port or 9880)), timeout=1):
                return {"ready": True, "label": "已就绪", "detail": "GPT-SoVITS 运行中"}
        except OSError:
            return {"ready": False, "label": "未配置", "detail": "GPT-SoVITS 未启动"}
    return {"ready": True, "label": "已就绪", "detail": "edge-tts"}


@app.get("/api/env/status")
def env_status() -> dict:
    """启动台"环境就绪度"：语音模型 / GPU / 翻译 / 配音四项探测（30s 缓存）。"""
    now = time.time()
    if _ENV_CACHE["data"] and now - _ENV_CACHE["at"] < _ENV_TTL:
        return _ENV_CACHE["data"]

    settings = load_settings()
    rows = {
        "asr": _probe_asr(settings),
        "gpu": _probe_gpu(),
        "translate": _probe_translate(settings),
        "tts": _probe_tts(settings),
    }
    # GPU 不阻塞开工：其余三项就绪即可
    workable = all(r["ready"] for k, r in rows.items() if k != "gpu")
    data = {"workable": workable, "rows": rows, "memory_gb": _total_mem_gb()}
    _ENV_CACHE.update(at=now, data=data)
    return data


def _total_mem_gb() -> float:
    """本机总内存（GB），引擎页模型推荐依据。"""
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3), 1)
    except (ValueError, OSError, AttributeError):
        return 0.0


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


# ---------- 多套词库（词库页：列表/启停/词条） ----------


@app.get("/api/glossaries")
def list_glossaries() -> dict:
    """词库列表（名称/启用/词条数），按顺序。"""
    return {"items": GlossaryLibrary().list()}


@app.post("/api/glossaries")
def manage_glossary(payload: dict) -> dict:
    """词库操作。action: create{name} | toggle{name,enabled} | delete{name}"""
    lib = GlossaryLibrary()
    action = payload.get("action")
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "缺少 name")
    try:
        if action == "create":
            return lib.create(name)
        if action == "toggle":
            lib.set_enabled(name, bool(payload.get("enabled", True)))
            return {"toggled": True}
        if action == "delete":
            if not lib.delete(name):
                raise HTTPException(404, f"词库不存在: {name}")
            return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    raise HTTPException(400, f"未知 action: {action}")


@app.get("/api/glossaries/{name}/terms")
def glossary_terms(name: str) -> dict:
    """指定词库的词条。"""
    return {"name": name, "items": GlossaryLibrary().terms(name)}


@app.post("/api/glossaries/{name}/terms")
def manage_glossary_terms(name: str, payload: dict) -> dict:
    """词条操作。{items:{源:译}} 或 {action:delete, src}。"""
    lib = GlossaryLibrary()
    if payload.get("action") == "delete":
        lib.delete_term(name, payload["src"])
    else:
        for src, tgt in payload.get("items", {}).items():
            lib.set_term(name, src, tgt)
    return {"count": len(lib.terms(name))}


@app.post("/api/glossaries/{name}/import")
async def glossary_import_named(name: str, file: UploadFile):
    """导入 CSV 到指定词库。"""
    import csv
    import io

    content = await file.read()
    lib = GlossaryLibrary()
    added = 0
    text = content.decode("utf-8-sig", errors="replace")
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2:
            continue
        src, tgt = row[0].strip(), row[1].strip()
        if not src or not tgt or src == "源语" or src.lower() == "source":
            continue
        lib.set_term(name, src, tgt)
        added += 1
    return {"added": added, "count": len(lib.terms(name))}


_OUTPUT_SUFFIX = {
    "video": ("_dubbed.mp4", "video"),
    "src-srt": ("_src.srt", "src-srt"),
    "bilingual-srt": ("_zh.srt", "bilingual-srt"),
}


# ---------- 下载页（yt-dlp） ----------


@app.get("/api/download/engine")
def download_engine() -> dict:
    """yt-dlp 引擎探测（下载页顶部引擎卡片）。"""
    info = probe_engine()
    return {
        "name": "yt-dlp",
        "sites": "YouTube · Bilibili · 抖音/小红书 等 1800+ 站点",
        **info,
    }


@app.post("/api/downloads")
def create_download(payload: dict) -> dict:
    """创建下载任务。payload: {text(混杂文本) 或 urls[], dir, quality, subs, cookie_file}"""
    text = payload.get("text", "")
    urls = payload.get("urls") or extract_urls(text)
    if not urls:
        raise HTTPException(400, "未识别到视频链接")

    out_dir = Path(payload.get("dir") or (resolve_data_dir() / "downloads"))
    opts = {
        "quality": payload.get("quality", "最佳"),
        "subs": bool(payload.get("subs", False)),
        "cookie_file": payload.get("cookie_file") or None,
    }

    task = manager.create({"video_path": "", "urls": urls, "kind": "download"})

    def runner(task_obj) -> str:
        sanitize_proxy()
        produced = download_urls(
            urls,
            out_dir,
            opts,
            progress=lambda pct, msg: task_obj.set("running", progress=pct, message=msg),
        )
        return produced[0] if produced else str(out_dir)

    manager.run(task, runner)
    return {"task_id": task.id, "count": len(urls), "urls": urls}


@app.post("/api/downloads/parse")
def parse_download_links(payload: dict) -> dict:
    """解析链接按钮：从混杂文本提取 URL 列表（不下载）。"""
    return {"urls": extract_urls(payload.get("text", ""))}


# ---------- 字幕 / 校对页（SRT 解析与保存） ----------


def _list_srt_files() -> list[dict]:
    """列出产物目录中的字幕文件。"""
    files = []
    for f in sorted(OUTPUT_DIR.glob("*.srt"), key=lambda p: p.stat().st_mtime, reverse=True):
        files.append(
            {"name": f.name, "path": str(f), "size": f.stat().st_size, "mtime": f.stat().st_mtime}
        )
    return files


@app.get("/api/subtitles")
def list_subtitles() -> dict:
    """字幕文件列表（产物目录）。"""
    return {"items": _list_srt_files()}


@app.get("/api/subtitles/rows")
def subtitle_rows(path: str) -> dict:
    """解析 SRT 为行（校对页编辑）。"""
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"字幕不存在: {path}")
    try:
        rows = parse_srt(p)
    except Exception as exc:
        raise HTTPException(400, f"SRT 解析失败: {exc}") from exc
    return {"path": str(p), "name": p.name, "rows": rows, "count": len(rows)}


@app.post("/api/subtitles/save")
def save_subtitles(payload: dict) -> dict:
    """保存校对后的字幕行。payload: {path, rows: [{id,start,end,text}]}"""
    path = payload.get("path")
    rows = payload.get("rows")
    if not path or rows is None:
        raise HTTPException(400, "缺少 path 或 rows")
    # 边界解析：校验每行字段齐全且时间为数
    parsed = []
    for i, r in enumerate(rows):
        try:
            parsed.append(
                {
                    "id": i,
                    "start": float(r["start"]),
                    "end": float(r["end"]),
                    "text": str(r["text"]),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(400, f"第 {i + 1} 行数据非法: {exc}") from exc
    Path(path).write_text(to_srt(parsed), encoding="utf-8")
    return {"saved": True, "count": len(parsed), "path": path}


# ---------- 配音页（单条合成试听） ----------


@app.post("/api/tts/synth")
def tts_synth(payload: dict) -> dict:
    """合成单行文本为音频（配音页试听）。payload: {text, voice_id?, ...overrides}"""
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "缺少 text")
    overrides = {k: v for k, v in payload.items() if k not in ("text",)}
    try:
        wav = synth_line(text, load_settings(), overrides)
    except Exception as exc:
        raise HTTPException(500, f"合成失败: {exc}") from exc
    return {"url": f"/api/preview/{wav.name}", "name": wav.name}


@app.get("/api/preview/{filename}")
def get_preview(filename: str):
    """试听产物（配音页音频预览）。"""
    fpath = resolve_data_dir() / "tts_preview" / filename
    if not fpath.exists():
        raise HTTPException(404, f"文件不存在: {filename}")
    media = "audio/mpeg" if fpath.suffix == ".mp3" else "audio/wav"
    return FileResponse(fpath, media_type=media, filename=filename)


# ---------- 音色页（我的音色库） ----------


@app.get("/api/voices")
def list_voices() -> dict:
    """我的音色列表。"""
    return {"items": VoiceLibrary().items}


@app.post("/api/voices")
async def add_voice(file: UploadFile, name: str = "", prompt_text: str = "", prompt_lang: str = "zh"):
    """上传参考音频，添加音色。"""
    import tempfile

    content = await file.read()
    if not content:
        raise HTTPException(400, "空文件")
    suffix = Path(file.filename or "ref.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        tmp = Path(f.name)
    try:
        item = VoiceLibrary().add(
            name or Path(file.filename or "音色").stem,
            tmp,
            prompt_text=prompt_text,
            prompt_lang=prompt_lang,
        )
    finally:
        tmp.unlink(missing_ok=True)
    return item


@app.delete("/api/voices/{voice_id}")
def delete_voice(voice_id: str) -> dict:
    """删除音色。"""
    if not VoiceLibrary().delete(voice_id):
        raise HTTPException(404, f"音色不存在: {voice_id}")
    return {"deleted": True}


@app.post("/api/voices/from_path")
def add_voice_from_path(payload: dict) -> dict:
    """从本机路径添加音色（Tauri 壳文件对话框返回真实路径，后端本地读取）。"""
    path = Path(payload.get("path") or "")
    if not path.exists():
        raise HTTPException(400, f"文件不存在: {path}")
    return VoiceLibrary().add(
        payload.get("name") or path.stem,
        path,
        prompt_text=payload.get("prompt_text", ""),
        prompt_lang=payload.get("prompt_lang", "zh"),
    )


# ---------- 配音页（批量合成 + 导出成品） ----------


@app.post("/api/dub/export")
def dub_export(payload: dict) -> dict:
    """配音导出任务：整段字幕批量 TTS → 合并配音轨 →（可选）替换视频音轨。

    payload: {srt_path, video_path?, ...tts overrides(voice/rate/voice_id...)}
    """
    srt_path = Path(payload.get("srt_path") or "")
    if not srt_path.exists():
        raise HTTPException(400, f"字幕不存在: {srt_path}")
    video = Path(payload["video_path"]) if payload.get("video_path") else None
    if video and not video.exists():
        raise HTTPException(400, f"视频不存在: {video}")
    overrides = {k: v for k, v in payload.items() if k not in ("srt_path", "video_path")}

    task = manager.create({"video_path": str(video) if video else "", "kind": "dub"})

    def runner(task_obj) -> str:
        ensure_env()
        sanitize_proxy()
        rows = parse_srt(srt_path)
        if not rows:
            raise ValueError("字幕为空")
        segments = [
            {"id": r["id"], "start": r["start"], "end": r["end"], "tgt": r["text"]} for r in rows
        ]
        settings = load_settings()
        paths = synth_segments(
            segments,
            settings,
            overrides,
            progress=lambda pct, msg: task_obj.set("running", progress=min(pct, 80), message=msg),
        )
        task_obj.set("running", progress=85, message="合并配音轨")
        out_wav = OUTPUT_DIR / f"{srt_path.stem}_dub.wav"
        build_track(segments, paths, out_wav)
        if video:
            task_obj.set("running", progress=95, message="替换视频音轨")
            out_video = OUTPUT_DIR / f"{video.stem}_dubbed.mp4"
            replace_audio(video, out_wav, out_video)
            return str(out_video)
        return str(out_wav)

    manager.run(task, runner)
    return {"task_id": task.id}


# ---------- 合成页（烧录 / 软封装） ----------
@app.post("/api/mux")
def create_mux_task(payload: dict) -> dict:
    """字幕合成任务。payload: {video, srt, audio?, style?, mode: burn|soft, out?}"""
    video = Path(payload.get("video") or "")
    srt = Path(payload.get("srt") or "")
    if not video.exists():
        raise HTTPException(400, f"视频不存在: {video}")
    if not srt.exists():
        raise HTTPException(400, f"字幕不存在: {srt}")
    audio = Path(payload["audio"]) if payload.get("audio") else None
    if audio and not audio.exists():
        raise HTTPException(400, f"音轨不存在: {audio}")
    mode = payload.get("mode", "burn")
    style = payload.get("style")
    out = Path(payload.get("out") or (OUTPUT_DIR / f"{video.stem}_subtitled.{'mp4' if mode == 'burn' else 'mkv'}"))

    task = manager.create({"video_path": str(video), "kind": "mux"})

    def runner(task_obj) -> str:
        task_obj.set("running", progress=20, message="合成中（烧录硬字幕较慢）" if mode == "burn" else "封装中")
        if mode == "soft":
            embed_soft_subtitles(video, srt, out, audio=audio)
        else:
            burn_subtitles(video, srt, out, style=style, audio=audio)
        return str(out)

    manager.run(task, runner)
    return {"task_id": task.id}


def _default_output(input_name: str, output_mode: str = "video") -> Path:
    suffix, _ = _OUTPUT_SUFFIX.get(output_mode, _OUTPUT_SUFFIX["video"])
    return OUTPUT_DIR / f"{Path(input_name).stem}{suffix}"


@app.post("/api/tasks")
def create_task(payload: dict) -> dict:
    """提交任务。

    视频任务必需: video_path；可选: output_mode(video/src-srt/bilingual-srt),
      tts_backend, multi_speaker, num_speakers, speed, elastic_timeline 等。
    字幕翻译必需: srt_path（翻译已有 SRT → 译文字幕）。
    """
    srt = payload.get("srt_path")
    video = payload.get("video_path")
    if not srt and not video:
        raise HTTPException(400, "缺少 video_path 或 srt_path")

    if srt:
        srt_path = Path(srt)
        if not srt_path.exists():
            raise HTTPException(400, f"字幕不存在: {srt}")
        task = manager.create(payload)

        def srt_runner(task_obj) -> str:
            ensure_env()
            sanitize_proxy()
            out = payload.get("out_path") or OUTPUT_DIR / f"{srt_path.stem}_zh.srt"
            translate_srt_file(
                srt_path,
                Path(out),
                settings=load_settings(),
                progress=lambda pct, msg: task_obj.set("running", progress=pct, message=msg),
            )
            return str(out)

        manager.run(task, srt_runner)
        return {"task_id": task.id}

    video_path = Path(video)
    if not video_path.exists():
        raise HTTPException(400, f"视频不存在: {video}")

    output_mode = payload.get("output_mode", "video")
    if output_mode not in _OUTPUT_SUFFIX:
        raise HTTPException(400, f"未知 output_mode: {output_mode}")

    task = manager.create(payload)

    def runner(task_obj) -> str:
        ensure_env()  # 从设置注入 DEEPSEEK_API_KEY
        sanitize_proxy()  # 清理 socks:// 代理（T-003）
        out = payload.get("out_path") or _default_output(video_path.stem, output_mode)
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
            output_mode=output_mode,
        )
        return str(out)

    manager.run(task, runner)
    return {"task_id": task.id}


@app.get("/api/tasks")
def list_tasks() -> dict:
    """任务列表（启动台"最近任务"），按创建时间倒序。"""
    return {"items": [t.to_dict() for t in manager.list()]}


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
    """下载/预览产物（成片 mp4 / 字幕 srt）。"""
    fpath = OUTPUT_DIR / filename
    if not fpath.exists():
        raise HTTPException(404, f"文件不存在: {filename}")
    media_type = "text/plain; charset=utf-8" if fpath.suffix == ".srt" else "video/mp4"
    return FileResponse(fpath, media_type=media_type, filename=filename)


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
