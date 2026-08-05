# 执行计划 0007：多平台接入 + 绿色版零捆绑打包

> 状态：✅ 已完成
> 创建：2026-08-04
> 完成：2026-08-04
> 前置：0001-0006（全链路 + 桌面壳 + 弹性时间轴）
> 目标：把应用改造为**零捆绑可执行程序（绿色版 AppImage）**——ASR/翻译/配音三环节全部用户可选平台，模型全部用户自下载，数据写入用户目录。

## 背景

当前应用依赖开发目录硬编码路径、模型预置在仓库。用户希望：核心包不含任何模型，三环节（识别/翻译/配音）均可自由切换不同平台，语音识别支持 whisper.cpp / faster-whisper / FunASR / 云端听写等主流方案，翻译走 DeepSeek 等主流 AI 提供商并支持专业词库，配音沿用 edge-tts + GPT-SoVITS。打包产出绿色版（Linux AppImage 本地验证，Windows NSIS 经 CI）。

## 决策

| 项 | 决策 |
|----|------|
| 平台 | Linux 绿色版 AppImage（本地验证）+ Windows NSIS（CI 文件就绪） |
| 后端打包 | python-build-standalone + 可重定位 venv（uv 构建） |
| 模型 | 全部零捆绑：whisper / Qwen / GPT-SoVITS 均用户自下载或独立可选包 |
| ASR v1 | whisper.cpp（GGML，pywhispercpp）+ faster-whisper（现有） |
| 翻译 v1 | DeepSeek（现有）；本地 Qwen 为 v2；词库 GUI + CSV |
| 配音 | edge-tts + GPT-SoVITS（独立可选包，检测到自动启动） |
| UI | 先功能后界面：加 provider/模型/词库/设置，界面细节后续迭代 |

## 步骤

### 阶段 A：Provider 抽象层（地基）
1. `scripts/providers/`：三接口 AsrProvider / TranslateProvider / TtsProvider + 注册表 + 配置 schema + 单测
2. 现有实现改造为 provider：faster-whisper / DeepSeek / edge-tts / GPT-SoVITS
3. 新增 whisper.cpp provider（pywhispercpp，GGML 模型下载）
4. 词库模块 `glossary.py`：加载/校验 CSV、prompt 注入 + 后处理校验替换 + 单测

### 阶段 B：模型下载管理器
5. 泛化 download_model：whisper 模型列表 + GGML 格式 + Qwen GGUF（预留），GUI 下载/进度/重试，存用户数据目录
6. 后端 API：/api/models、/api/glossary、provider 配置；SSE 复用

### 阶段 C：运行时重构 + 打包
7. runtime 模块（AIDUBBING_ROOT / AIDUBBING_DATA 环境注入）+ 数据目录分离
8. Tauri 壳：current_exe() 解析资源目录 + 注入环境 + GPT-SoVITS 可选包检测启动
9. 后端捆绑（uv + python-build-standalone + CPU torch）+ scripts/package/build.py（产出 AppImage + 可选包）
10. GitHub Actions workflow 文件（ubuntu AppImage / windows NSIS）

### 阶段 D：前端重构（先功能）
11. 前端加：provider 选择、模型下载管理、词库管理、设置

### 阶段 E：验证
12. dev 回归（pytest + ruff 全绿）
13. 打包产物脱离开发目录全流程验证
14. 文档更新（README + plan 归档 + 债务）

## 验收

- [x] 三环节 GUI 可选不同平台；whisper.cpp 与 faster-whisper 切换正常
- [x] 专业词库生效（术语翻译一致）
- [x] `build.py` 产出零捆绑 AppImage，脱离开发目录全流程 OK
- [x] 数据（含模型）全部写入用户目录（~/.local/share/aidubbing）
- [x] GPT-SoVITS 可选包逻辑就绪（检测 pack.json 自动启动）
- [x] dev 模式回归不破
- [x] CI workflow 文件就绪（Linux + Windows）

## 决策日志补充（执行期）

- **2026-08-04**：edge-tts 捆绑 env 中解析到旧版 6.1.7，Bing 新端点返回 403 → 升级到 7.2.8（pyproject 约束 >=7.0.0）。
- **2026-08-04**：Tauri 自带 AppImage 打包器（appimagetool 下载）卡死 → 手动构建 AppDir + appimagetool（直连下载 5s）产出 AppImage。已验证 AppImage 独立运行、数据写用户目录。
- **2026-08-04**：AppImage 只读挂载问题——Rust data_dir 需以 `pyproject.toml` 存在与否区分 dev/打包模式（资源目录只含 backend/scripts，无 pyproject）。
- **2026-08-04**：stage 命名统一为 `translate`（曾误用 `translation` 导致分组键不一致）。
- **2026-08-04**：打包 env 构建需 `--constraint` 锁定 torch CPU 版（避免 diarize 依赖把 torch 解析成 CUDA 版）。


## 风险

| 风险 | 对策 |
|------|------|
| pywhispercpp 依赖编译/二进制兼容 | 优先用预编译 wheel；失败退 CLI binary 调用 |
| 路径重构影响面广 | 集中 runtime 模块 + 单测覆盖 |
| uv venv 可重定位性 | 实测 python-build-standalone 解释器 |
| 模型下载网络/镜像 | 支持 HF_ENDPOINT（hf-mirror），进度 + 重试 |
| Windows 本地无法验证 | CI 双 runner（需推 GitHub），本地以 Linux 验证 |
| 词库注入影响翻译质量 | prompt 注入 + 后处理校验替换双保险 |
