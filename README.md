# AI 配音工作台

**本地 AI 视频翻译配音桌面应用**：上传外语视频 → 自动识别说话人 → 翻译 → 用原说话人音色配音 → 输出中文成片。对标海风声影 Studio。

> 产品愿景：让每个创作者都能**用自己的声音说任何语言**——一键产出"听起来像本人说中文"的成片。

## 核心能力（已实现 ✅）

| 能力 | 说明 |
|------|------|
| 🎙️ 音色克隆 | GPT-SoVITS few-shot 克隆原说话人音色（独立可选包） |
| 👥 多说话人分离 | diarize 库自动区分视频中每个人，各角色各音色 |
| 🧩 多平台引擎 | 识别（faster-whisper / whisper.cpp / 云端）、翻译（DeepSeek 等）、配音均用户自选 |
| 📚 多套专业词库 | 按剧集/领域建多套词库，启用开关 + 优先级，翻译术语一致 |
| 🎤 我的音色库 | 上传参考音频保存常用音色，配音页随取随用 |
| ⏱️ 弹性时间轴 | 中文语速自然优先：变速 ±15% + 长停顿裁剪 |
| 📝 字幕工作台 | 字幕页（转写/翻译配置条）+ 校对页（逐行编辑自动保存） |
| 🎬 配音工作台 | 逐行合成试听、修正、一键导出成品（合并配音轨/替换视频音轨） |
| 🖼️ 合成器 | 字幕样式预设/自定义 + 烧录硬字幕 + 封装软字幕（MKV） |
| ⬇️ 视频下载 | yt-dlp 集成：粘贴链接/聊天记录解析、清晰度、官方字幕 |
| 🖥️ 桌面应用 | Tauri + FastAPI，图形界面导入/进度/成片预览 |
| 📦 绿色版 | AppImage 零捆绑，模型全部用户自下载，数据写用户目录 |
| 🔒 素材不出本机 | 处理全部本地，仅翻译可选手动联网 |

## 快速开始

### 桌面应用（推荐）

```bash
# 1. 安装系统依赖（Linux，Tauri 需要；macOS/Windows 跳过）
sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev

# 2. 安装 Python 环境
uv venv
uv pip install -e ".[dev]"
uv pip install torch --index-url https://download.pytorch.org/whl/cpu   # 仅 CPU
uv pip install torchaudio torchcodec --index-url https://download.pytorch.org/whl/cpu

# 3. 启动 GPT-SoVITS 音色克隆服务（可选，音色克隆模式需要）
cd tools/GPT-SoVITS-CPUFast && python api_v2.py   # 监听 127.0.0.1:9880

# 4. 启动桌面应用（首次需编译 Rust）
cd app && npm install && npm run tauri dev
```

首次使用在应用内配置 **DeepSeek API Key**（设置页，仅存本机 `workdir/settings.json`）。

### 命令行（快速验证）

```bash
# 单说话人 + edge-tts（最快）
export DEEPSEEK_API_KEY=sk-xxx && unset all_proxy ALL_PROXY
python scripts/run_e2e.py --input assets/demo.mp4 --output output/out.mp4

# 音色克隆（需 GPT-SoVITS 服务）
python scripts/run_e2e.py --input assets/demo.mp4 --output output/out.mp4 \
  --tts gpt-sovits --multi-speaker

# 弹性时间轴（中文语速自然优先）
python scripts/run_e2e.py --input assets/demo.mp4 --output output/out.mp4 \
  --elastic-timeline
```

> 💡 本机 `all_proxy=socks://...` 会导致 httpx 报错（T-003），联网前先 `unset all_proxy ALL_PROXY`；桌面后端已自动处理。

## 架构

```
┌──────────────────────────────────────────────┐
│  Tauri 桌面壳 (Rust + Web UI)                 │
│  拉起居端 → 随机端口 → 健康轮询 → 退出清理     │
└───────────────────┬──────────────────────────┘
                    │ HTTP + SSE (127.0.0.1:port)
┌───────────────────▼──────────────────────────┐
│  Python 后端 (FastAPI)                        │
│  任务队列 + SSE 进度 + 设置持久化 + 静态前端    │
└───────────────────────────────────────────────┘

处理链路:
  video → ASR(faster-whisper) → diarization(diarize)
       → 翻译(DeepSeek) → TTS(GPT-SoVITS) → timeline(弹性)
       → mux(ffmpeg 混音+烧字幕) → output/
```

- **前端**：Vanilla HTML/CSS/JS（`backend/static/`），后端直接托管，浏览器可测
- **后端**：`backend/` — server.py / task_manager.py / settings.py
- **脚本**：`scripts/` — 可独立运行的 pipeline 步骤
- **架构规范**：见 [ARCHITECTURE.md](ARCHITECTURE.md)

## 项目结构

```
├── app/                    # Tauri 桌面壳 (Rust)
│   └── src-tauri/          #   主进程：后端子进程管理
├── backend/                # FastAPI 后端
│   ├── server.py           #   API + SSE + 静态托管
│   ├── task_manager.py     #   任务队列
│   ├── settings.py         #   API Key 持久化 + 代理清理
│   └── static/             #   Web 前端（壳 + 分页视图）
├── scripts/                # Pipeline 脚本
│   ├── run_e2e.py          #   端到端入口
│   ├── step1_asr.py        #   ASR + 说话人标签
│   ├── step2_translate.py  #   翻译
│   ├── step3_tts.py        #   TTS（edge-tts / gpt-sovits）
│   ├── step4_mux.py        #   混音 + 烧字幕
│   ├── speaker_diarize.py  #   说话人分离
│   ├── speaker_ref.py      #   各角色参考音频提取
│   ├── timeline.py         #   弹性时间轴 + 停顿裁剪
│   ├── voice_clone.py      #   GPT-SoVITS API 客户端
│   ├── downloader.py       #   yt-dlp 视频下载
│   ├── tts_service.py      #   单条/批量 TTS + 配音轨合并
│   ├── mux_service.py      #   烧录/软封装/音轨替换
│   ├── subtitle_style.py   #   字幕样式 → ASS force_style
│   ├── voice_library.py    #   我的音色库
│   └── glossary.py         #   多套专业词库
├── docs/                   # 仓库内知识（计划/设计/规格）
├── models/                 # 模型文件（gitignore）
├── workdir/                # 处理中间产物（gitignore）
└── assets/                 # 测试素材（gitignore）
```

## 技术栈

| 环节 | 选型 |
|------|------|
| 桌面壳 | Tauri v2 (Rust) |
| 后端 | Python FastAPI + uvicorn + SSE |
| 语音识别 | faster-whisper (CPU int8) |
| 说话人分离 | diarize + WeSpeaker embeddings |
| 翻译 | DeepSeek API（本地 Qwen 待办） |
| 音色克隆 | GPT-SoVITS（few-shot） |
| 视频处理 | ffmpeg（imageio-ffmpeg） |
| 包管理 | uv (Python) / cargo (Rust) |

详细选型理由见 [docs/design-docs/tech-stack.md](docs/design-docs/tech-stack.md)。

## 开发

```bash
uv run pytest                    # 测试（49 个用例）
uv run ruff check scripts/ backend/ tests/   # Lint
python scripts/run_e2e.py --help  # 全部 CLI 选项
```

## 执行计划

| 计划 | 状态 | 说明 |
|------|------|------|
| 0001 MVP 端到端 | ✅ | 视频→识别→翻译→配音→混音闭环 |
| 0002 音色克隆 | ✅ | GPT-SoVITS 接入 |
| 0003 说话人分离 | ✅ | diarize 接入 |
| 0004 多角色配音 | ✅ | 各说话人各音色 |
| 0005 Tauri 桌面壳 | ✅ | 桌面应用 |
| 0006 弹性时间轴 | ✅ | 中文语速自然优先 |
| 0007 多平台 + 绿色版 | ✅ | 零捆绑 AppImage + Provider 抽象 + 词库 |
| 0008 启动台首页 | ✅ | 工作台壳 + 字幕流程 |
| 0009 按设计稿全部功能页 | ✅ | 下载/字幕/校对/配音/引擎/翻译/词库/音色/合成 |

见 [docs/exec-plans/index.md](docs/exec-plans/index.md)。

## 打包（绿色版 AppImage）

```bash
# 构建捆绑 Python 环境（CPU torch）+ 资源 + AppImage
python scripts/package/build.py
# 产物：app/src-tauri/target/release/bundle/appimage/*.AppImage
# 数据目录：Linux ~/.local/share/aidubbing
```

## 已知限制与路线

- 翻译默认 DeepSeek API（联网）——本地 Qwen 待接入（T-002）
- CPU 音色克隆速度较慢（每段 4-6s）——GPU 里程碑（T-005）
- Windows NSIS 打包待 CI 验证（T-009）
- 口型同步 / 批量队列为后续里程碑

技术债务详见 [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md)。
