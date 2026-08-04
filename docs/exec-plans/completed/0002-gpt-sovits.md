# 执行计划 0002：接入 GPT-SoVITS 音色克隆

> 状态：✅ 已完成 — 2026-08-04
> 创建：2026-08-04
> 关联债务：T-001（已解决）
> 目标：把 step3 的 edge-tts 占位替换为 **GPT-SoVITS 真实音色克隆**，让成片使用原说话人音色——这是产品核心卖点"用你自己的声音说外语"。

## 背景

0001 已验证完整链路（ASR→翻译→TTS→混音），但 TTS 用的是 edge-tts 固定音色（占位）。产品差异化在于**克隆视频原说话人的音色**。GPT-SoVITS 支持 few-shot 音色克隆（无需微调训练，用参考音频 + 预训练模型即可），本机 CPU 可跑推理（慢但可行），生产环境换 5060Ti GPU。

## 目标与范围

**范围内**：
- GPT-SoVITS few-shot 克隆：从 demo 视频提取说话人参考音频 → 克隆音色 → 中文 TTS
- step3_tts.py 改造为可切换后端（edge-tts / gpt-sovits）
- 端到端验证：成片音色与原始说话人相似

**范围外**（后续里程碑）：
- GPT-SoVITS 微调训练（需更多样本，CPU 不现实）
- 多角色音色（依赖 diarization，另立计划）
- 本地 Qwen 翻译（T-002，另立计划）

## 步骤

| # | 任务 | 产出 | 验收标准 | 结果 |
|---|------|------|---------|------|
| 1 | 调研 GPT-SoVITS 部署方式（源码 / pip / Docker） | 部署方案决策 | 选 CPU 可行的最小方案 | ✅ 采用 **GPT-SoVITS-CPUFast**（CPU 加速版，独立 venv） |
| 2 | 安装 GPT-SoVITS 依赖 + 下载预训练模型 | 可运行的推理环境 | 模型加载成功 | ✅ `venv-sovits/` + `tools/GPT-SoVITS-CPUFast/` |
| 3 | 从 demo.mp4 提取说话人参考音频（5-30s 干净人声） | 参考音频文件 | 取到清晰人声 | ✅ demo 无 BGM，直接提取 |
| 4 | 实现 voice-clone 模块：few-shot 克隆 + 中文 TTS | `scripts/voice_clone.py` | 输入参考音频+文本 → 输出克隆音色语音 | ✅ 通过本地 API (127.0.0.1:9880) 合成 |
| 5 | step3_tts.py 改造为可切换后端 | 后端抽象 | `--tts edge-tts\|gpt-sovits` 可切换 | ✅ `tools/start_sovits_server.sh` 启动服务 |
| 6 | 端到端验证：run_e2e 用 gpt-sovits 后端跑 demo | 成片 | 音色可感知相似；中文可听懂 | ✅ `output/out_sovits.mp4` + 回归 `out_reg.mp4` |

## 决策日志

- **2026-08-04**：优先 few-shot（零样本）模式，不做微调——CPU 上训练不现实，few-shot 即可验证"音色相似"卖点。
- **2026-08-04**：TTS 后端抽象为可切换，避免 GPT-SoVITS 失败时阻塞链路（edge-tts 兜底）。
- **2026-08-04**：部署采用 **GPT-SoVITS-CPUFast** 变体（CPU 推理优化），以独立 venv 隔离 torch 依赖。

## 风险与验证结果

| 风险 | 对策 | 结果 |
|------|------|------|
| GPT-SoVITS CPU 推理过慢 | demo 只有 8s；验收以功能正确为主 | ✅ 功能正确，速度留 GPU 里程碑 |
| 依赖冲突（torch 大包） | 独立 venv（`venv-sovits/`） | ✅ 未污染主 venv |
| 模型下载被墙 | 复用 0001 经验 | ✅ 已解决 |
| few-shot 音色相似度不达预期 | 记录主观评分 | ⚠️ 待 GPU 上微调提升（记入债务） |

## 验收结果

- [x] `run_e2e.py --tts gpt-sovits --input assets/demo.mp4 --output output/out_sovits.mp4` 单命令产出成片
- [x] 成片中文配音音色与原说话人可感知相似
- [x] edge-tts 后端回归通过（`output/out_reg.mp4`）

## 产出文件

- `scripts/voice_clone.py`：GPT-SoVITS few-shot 克隆 TTS 后端（API: 127.0.0.1:9880）
- `tools/GPT-SoVITS-CPUFast/`：CPU 加速版部署
- `tools/start_sovits_server.sh`：启动脚本
- `venv-sovits/`：隔离依赖
- `output/out_sovits.mp4`：验证成片

## 遗留（记入 tech-debt-tracker）

- 音色相似度在 CPU few-shot 下有限，GPU 微调可提升（新债务）
- 多角色音色依赖 diarization（另立计划）
