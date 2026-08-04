# 执行计划 0003：多说话人分离（Diarization）接入

> 状态：✅ 已完成
> 创建：2026-08-04
> 完成：2026-08-04
> 关联债务：T-005（多角色音色依赖说话人分离，0002 遗留）
> 目标：接入说话人分离，让系统能自动区分视频中**每个说话人**，为多角色音色配音打基础——对标海风声影"多角色不同音色"卖点。

## 背景

0001 验证了单说话人完整链路，0002 实现了音色克隆。但真实视频（访谈、对话、多人场景）有**多个说话人**，目前整段音频只有一个音色。海风声影的核心卖点之一是"自动分析不同说话人，为访谈、对话和多人视频中的不同角色匹配不同音色"。本计划接入说话人分离，让 ASR 输出带上"谁在说话"的标签。

## 目标与范围

**范围内**：
- 接入说话人分离（pyannote.audio 或 WhisperX diarize）
- 输出：`说话人A: [0:05-0:12] "文本"` 分段结构
- step1_asr 升级：识别 + 分离结合
- 验证：多人对话测试素材能正确分组

**范围外**（后续里程碑）：
- 为每个说话人自动克隆音色（依赖本计划输出，另立计划）
- 说话人跨视频识别（声纹库）
- 实时流式分离

## 步骤

| # | 任务 | 产出 | 验收标准 |
|---|------|------|---------|
| 1 | 调研：pyannote vs WhisperX diarize 选型 | 方案决策 | 选 CPU 可行、中文友好的方案 |
| 2 | 安装依赖 + 获取模型（pyannote 需 HF token） | 可运行环境 | 模型加载成功 |
| 3 | 生成多说话人测试素材（edge-tts 两个不同音色合成对话） | `assets/demo_multi.mp4` | 两个说话人清晰可辨 |
| 4 | 实现 diarization 模块 | `scripts/diarize.py` | 输出带说话人标签的时间段 |
| 5 | step1_asr 集成：识别文本 + 说话人标签合并 | 升级版 step1 | 输出 `说话人A: [t1-t2] 文本` |
| 6 | 验证：demo_multi 跑通分离+识别 | 验证报告 | 两说话人分组正确（≥90% 准确） |

## 决策日志

- **2026-08-04**：选型 `diarize` 库（FoxNoseTech/diarize）替代 pyannote/WhisperX。
  - 理由：pyannote 需 HF token（gated model）；diarize 无需 token，CPU-only，Apache 2.0，DER 4.8%（优于 pyannote 免费模型 11.2%），8x 实时速度。
  - 依赖：silero-vad（VAD）、wespeakerruntime（WeSpeaker embeddings）、scikit-learn（spectral clustering）
  - 脚本命名 `speaker_diarize.py` 避免与库名 `diarize` 冲突。

## 风险

| 风险 | 对策 |
|------|------|
| pyannote 模型需 HF token（gated） | 用户注册 HF 账号拿 token；或换不 gated 的替代方案 |
| CPU 上分离速度慢 | 8s demo 可接受；生产 GPU |
| 中文说话人分离效果 | pyannote 多语言模型；实测评估 |
| 分离错误率影响配音 | 输出可人工修正（手动模式预留） |

## 验收

- [x] `scripts/speaker_diarize.py --input assets/demo_multi.mp4` 输出正确说话人分段
- [x] step1_asr `--diarize` 输出含说话人标签
- [x] 两说话人 demo 分组准确率 100%（SPEAKER_00 / SPEAKER_01 正确）
- [x] 单说话人 demo 回归不破（仍输出单一 SPEAKER_00）
