# ARCHITECTURE.md — 顶层架构地图

> 本文件提供域和包分层的顶层视图。详细设计见 `docs/design-docs/`。

## 系统总览

本地桌面应用，进程模型：

```
┌─────────────────────────────────────────────┐
│         Tauri 桌面壳 (Rust + Web UI)         │
│   自动模式 / 手动模式 / 音色库 / 任务队列      │
└──────────────────┬──────────────────────────┘
                   │ HTTP (127.0.0.1:port)
┌──────────────────▼──────────────────────────┐
│          Python 后端 (FastAPI)               │
│   任务编排: 状态机 + 进度上报 + 文件管理       │
└─────────────────────────────────────────────┘
```

## 业务域分层（每个域内强制）

```
Types → Config → Repo → Service → Runtime → UI
```

横切关注点（认证、遥测、功能标志、连接器）通过 `Providers` 接口进入，不得直接依赖。

### 域清单

| 域 | 职责 | 关键模块 |
|----|------|---------|
| `video-ingest` | 视频导入/下载/音频提取 | ffmpeg, yt-dlp |
| `voice-separation` | 人声分离（去 BGM） | UVR5/Demucs |
| `asr` | 语音识别 + 时间戳 | faster-whisper |
| `diarization` | 说话人分离/聚类 | pyannote |
| `translation` | 翻译 + 文本优化 | Qwen 本地 / 可选 API |
| `voice-clone` | 音色克隆 + TTS | GPT-SoVITS |
| `timeline` | 弹性时间轴对齐 | 自研 + ffmpeg |
| `mux` | 混音 + 字幕烧录 + 成片 | ffmpeg |
| `app-wiring` | 桌面壳与后端编排 | Tauri, FastAPI |

## 依赖方向

- 每个域内部：`Types → Config → Repo → Service → Runtime → UI`（只允许向前依赖）
- 域之间：通过 `Service` 层接口交互，不直接跨域调用内部实现
- `Utils` 位于域外，只提供纯函数工具，不依赖任何域

## 强制执行

- `scripts/check_architecture.py`：结构测试，检查依赖方向与分层违规
- CI 中运行，违反即失败
- lint 规则集中维护，错误信息注入修复指引（供智能体消费）

## 数据流（一次完整处理）

```
video-ingest → voice-separation → asr → diarization
     → translation → voice-clone → timeline → mux → output/
```

每步产物落盘（`workdir/<task_id>/`），便于断点续跑与调试。

## 关键非功能约束

- 全部本地处理，素材不出本机（对标产品卖点）
- 任务可中断/恢复（状态机持久化）
- 16GB 显存 / CPU 均可运行（自动检测硬件）
- 单视频处理为原子任务，失败不污染其他任务
