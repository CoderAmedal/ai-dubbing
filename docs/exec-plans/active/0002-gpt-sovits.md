# 执行计划 0002：接入 GPT-SoVITS 音色克隆

> 状态：📝 起草中
> 创建：2026-08-04
> 关联债务：T-001（音色克隆未接入，TTS 用 edge-tts 占位）
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

| # | 任务 | 产出 | 验收标准 |
|---|------|------|---------|
| 1 | 调研 GPT-SoVITS 部署方式（源码 / pip / Docker） | 部署方案决策 | 选 CPU 可行的最小方案 |
| 2 | 安装 GPT-SoVITS 依赖 + 下载预训练模型（小模型优先） | 可运行的推理环境 | 模型加载成功 |
| 3 | 从 demo.mp4 提取说话人参考音频（5-30s 干净人声） | 参考音频文件 | 无人声分离也能取到清晰人声（demo 无 BGM） |
| 4 | 实现 voice-clone 模块：few-shot 克隆 + 中文 TTS | `scripts/voice_clone.py` | 输入参考音频+文本 → 输出克隆音色语音 |
| 5 | step3_tts.py 改造为可切换后端 | 后端抽象 | `--tts edge-tts\|gpt-sovits` 可切换 |
| 6 | 端到端验证：run_e2e 用 gpt-sovits 后端跑 demo | 成片 | 成片音色与原说话人可感知相似；中文可听懂 |

## 决策日志

- **2026-08-04**：优先 few-shot（零样本）模式，不做微调——CPU 上训练不现实，few-shot 即可验证"音色相似"卖点。
- **2026-08-04**：TTS 后端抽象为可切换，避免 GPT-SoVITS 失败时阻塞链路（edge-tts 兜底）。

## 风险

| 风险 | 对策 |
|------|------|
| GPT-SoVITS CPU 推理过慢（分钟级/句） | demo 只有 8s；验收以功能正确为主，速度留给 GPU 里程碑 |
| 依赖冲突（torch 等大包） | 独立 venv（`venv-sovits/`），不污染主 venv |
| 模型下载被墙 | 复用 0001 经验：huggingface.co 直连经代理，或 hf-mirror 直连 |
| few-shot 音色相似度不达预期 | 记录主观评分，作为 GPT-SoVITS 微调/换 F5-TTS 的决策依据 |

## 验收

- [ ] `run_e2e.py --tts gpt-sovits --input assets/demo.mp4 --output output/out_sovits.mp4` 单命令产出成片
- [ ] 成片中文配音音色与 demo 原说话人（edge-tts 生成的英文女声 Jenny）**可感知相似**
- [ ] 反向 ASR 验证成片为中文
- [ ] edge-tts 后端仍可用（回归不破）
