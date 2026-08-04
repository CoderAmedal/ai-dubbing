# 技术选型（已验证）

> 状态：✅ 已验证 — 2026-08-04
> 决策：所有组件选开源、可商用、支持 CPU 回退的方案。

## 选型表

| 环节 | 首选 | 备选 | 理由 |
|------|------|------|------|
| 桌面壳 | Tauri (Rust) | Electron | 体积小(~10MB)、解压即用、跨平台 |
| 后端 | Python FastAPI | — | AI 生态全在 Python |
| 视频处理 | ffmpeg | — | 提取/混音/烧字幕 |
| 视频下载 | yt-dlp | — | 网络视频 |
| 人声分离 | UVR5 / Demucs | — | 分离人声与 BGM |
| 语音识别 | faster-whisper | FunASR | 外语识别+时间戳，CPU 可跑 |
| 说话人分离 | pyannote.audio | WhisperX | 多角色分组 |
| 翻译 | Qwen2.5-7B (GGUF 本地) | DeepSeek API | 全本地主打；API 作高级选项 |
| 音色克隆+TTS | GPT-SoVITS | F5-TTS / CosyVoice | 中文配音质量天花板 |
| 包管理 | uv (Python) / cargo (Rust) | — | 快、可复现 |

## 决策记录

### D1: 为什么 Tauri 而不是 Electron
- 最终产物要"解压即用"（对标海风声影），Tauri 安装包 ~10MB vs Electron ~100MB+
- Rust 壳 + Web UI，前端生态不受影响
- 跨平台（Win/macOS/Linux），海风声影仅 Windows，这是我们的差异化

### D2: 为什么翻译走本地 Qwen
- 产品卖点是"零云端 API 依赖、素材不出本机"
- Qwen2.5-7B GGUF Q4 ~4.5GB，16GB 显存或 32GB 内存可跑
- 翻译质量对短字幕足够；可选 DeepSeek API 作为"高级模式"兜底

### D3: 为什么 faster-whisper 而非原生 whisper
- CTranslate2 加速，CPU 上快 4 倍，int8 量化内存减半
- 自带 VAD 过滤静音，时间戳质量好

### D4: 为什么音色克隆默认 GPT-SoVITS
- few-shot：1 分钟样本即可，适合"从视频里提取说话人声音"场景
- 中文配音效果目前开源最佳
- 备选 F5-TTS（零样本更强）、CosyVoice（阿里开源）做自动择优

## 未决问题

- 弹性时间轴对齐的变速上限（±15%？）与听感关系，需原型验证
- GPT-SoVITS 模型训练时长在 CPU 上的可接受范围
- 多说话人相似音色聚类的阈值
