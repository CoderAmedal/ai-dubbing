"""视频下载模块 — yt-dlp 封装（下载页后端）。

支持：多链接队列、混杂文本解析链接、清晰度选择、官方字幕、进度回调。
设计稿：design-pic/下载.png（引擎卡片 + 链接框 + 选项行 + 解析/下载按钮）。

用法：
  from downloader import probe_engine, start_downloads, extract_urls
  info = probe_engine()  # yt-dlp 版本
  urls = extract_urls(mixed_text)
  start_downloads(urls, opts, task)  # 经 TaskManager 跑进度
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger("downloader")

# 从混杂文本中提取 http(s) 链接
_URL_RE = re.compile(r"https?://[^\s，。；\"'<>）)】]+")

# 清晰度 → yt-dlp format 表达式
QUALITY_FORMATS = {
    "最佳": "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p": "bv*[height<=720]+ba/b[height<=720]",
    "480p": "bv*[height<=480]+ba/b[height<=480]",
    "仅音频": "ba/b",
}


def probe_engine() -> dict:
    """探测 yt-dlp 引擎：版本、可用性。"""
    try:
        import yt_dlp

        return {"installed": True, "version": yt_dlp.version.__version__}
    except ImportError:
        return {"installed": False, "version": None}


def extract_urls(text: str) -> list[str]:
    """从混杂文本（聊天记录等）中提取视频链接，去重保序。"""
    seen: dict[str, None] = {}
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;!?)")
        seen[url] = None
    return list(seen)


def _ydl_opts(out_dir: Path, opts: dict, progress) -> dict:
    quality = opts.get("quality", "最佳")
    ydl_opts: dict = {
        "format": QUALITY_FORMATS.get(quality, QUALITY_FORMATS["最佳"]),
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "progress_hooks": [progress],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if opts.get("subs"):
        ydl_opts["writesubtitles"] = True
        ydl_opts["subtitlesformat"] = "srt"
    cookie_file = opts.get("cookie_file")
    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file
    return ydl_opts


def download_urls(urls: list[str], out_dir: Path, opts: dict, progress) -> list[str]:
    """顺序下载多个链接，progress(pct, msg) 汇报总进度。返回产物路径。"""
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    produced: list[str] = []
    total = len(urls)

    for idx, url in enumerate(urls):
        base = idx * 100 // total

        def hook(d: dict, _base: int = base, _idx: int = idx) -> None:
            if d.get("status") == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                frac = downloaded / total_bytes if total_bytes else 0
                pct = _base + int(frac * (100 // total or 1))
                name = Path(d.get("filename", "")).name
                progress(min(pct, 99), f"[{_idx + 1}/{total}] {name}")
            elif d.get("status") == "finished":
                produced.append(d.get("filename", ""))

        progress(base, f"[{idx + 1}/{total}] 解析 {url}")
        with yt_dlp.YoutubeDL(_ydl_opts(out_dir, opts, hook)) as ydl:
            ydl.download([url])

    progress(100, f"完成 {total} 个下载")
    return produced
