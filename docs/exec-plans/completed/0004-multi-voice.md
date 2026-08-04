# 执行计划 0004：多角色音色配音

> 状态：✅ 已完成
> 创建：2026-08-04
> 完成：2026-08-04
> 前置：0001（链路）、0002（音色克隆）、0003（说话人分离）
> 目标：把"说话人分离"与"音色克隆"组合——**每个说话人自动克隆自己的音色，各角色用各自音色配音**。这是对标海风声影"多角色不同音色"卖点的完整落地。

## 背景

- 0002：单说话人音色克隆可用（GPT-SoVITS few-shot，`voice_clone.py`）
- 0003：说话人分离可用（`speaker_diarize.py`，输出 `{start, end, speaker}`）
- 现在：分离结果**没有接到音色克隆上**——多人视频仍然全程用一个音色

本计划打通：`diarize 分组 → 每角色提取参考音频 → 每角色克隆音色 → 按段用对应音色 TTS → 混音`。

## 目标与范围

**范围内**：
- 从每个说话人的语音段中自动提取干净参考音频（5-30s）
- 为每个说话人建立音色（few-shot 克隆，复用 GPT-SoVITS）
- step3 升级：按段选择对应角色的音色合成
- 端到端验证：多人 demo 成片**每个角色音色不同且对应原说话人**

**范围外**（后续里程碑）：
- 说话人跨视频声纹复用（音色库持久化）
- 相似音色自动合并（embedding 聚类）
- GPU 微调提升音色相似度（T-005）

## 步骤

| # | 任务 | 产出 | 验收标准 |
|---|------|------|---------|
| 1 | 从 diarize 分段中为每角色提取参考音频（选最长段、不足 3s 时扩展窗口） | `scripts/speaker_ref.py` + refs.json | 每角色 ≥1 段 ≥3s 参考音频 + prompt_text |
| 2 | 音色注册：每角色 → GPT-SoVITS 克隆（复用 voice_clone 能力） | refs.json（含 audio/prompt） | 每角色可独立合成 |
| 3 | step3 改造：支持 `--ref-map` 按 speaker 选音色 | 升级版 step3 | 各段使用对应角色音色 |
| 4 | 多角色端到端：run_e2e `--multi-speaker` | 升级版 run_e2e | `demo_multi.mp4` 产出多音色成片 |
| 5 | 验证：音色对应关系 + 回归 | 验证报告 | 角色A段=角色A音色；单人 demo 回归不破 |

## 决策日志

- **2026-08-04**：参考音频提取策略——优先取该角色**最长的分离分段**（含 0.1s 边距），避免含笑声/重叠语音。实现为 `speaker_ref.py`（草稿命名为 extract_refs.py，实际以 speaker_ref.py 落地）。
- **2026-08-04**：GPT-SoVITS 要求参考音频 3~10 秒。最长分段不足 3s 时窗口向两侧对称扩展（优先扩到无其它说话人一侧，与其它说话人重叠 ≤0.2s 停止）。
- **2026-08-04**：音色按任务内缓存（`workdir/e2e/<name>/refs/`），跨视频复用留到音色库里程碑。
- **2026-08-04**：多角色入口为 `run_e2e.py --multi-speaker`（自动 ASR+分离+参考音频+各角色克隆+混音），单说话人 `--tts gpt-sovits --ref-audio` 保持兼容。
- **2026-08-04**：测试素材 demo_multi.mp4 需 ≥18s（demo.mp4 仅 8s，`-shortest` 截断多说话人音频导致只检出 1 说话人）。改为 ffmpeg color 源 + 18s 双说话人音频。
- **2026-08-04**：真实内容测试（test/ 下 10 分钟 YouTube 视频）发现**参考音频超长 bug**——长视频单说话人 diarize 分段可达整段时长，提取整段作为参考被 GPT-SoVITS 拒绝（要求 3~10s）。修复：`speaker_ref.py` 增加 `MAX_REF_DURATION=10`，超长时裁剪取窗口中间 10s。已在 60s 真实片段上验证通过（`output/out_real.mp4`，11 段克隆配音）。

## 风险

| 风险 | 对策 |
|------|------|
| 说话人分段过短/碎片化，参考音频不足 | 合并同角色相邻段；不足 5s 则用该角色所有段拼接 |
| 多角色克隆在 CPU 上耗时成倍 | demo 素材控制在 2 角色 × 短时长；GPU 里程碑解决速度 |
| GPT-SoVITS API 并发/串行限制 | 逐角色串行克隆，任务内排队 |
| 角色音色混淆（相似声音） | 记录主观评分；聚类合并留 0005+ |

## 验收

- [x] `scripts/speaker_ref.py --audio ... --diarize segments.json` 输出每角色参考音频（demo_multi 提取出 4.4s + 5.8s，各带 prompt_text）
- [x] `run_e2e.py --input assets/demo_multi.mp4 --tts gpt-sovits --multi-speaker` 产出成片 `output/out_multi.mp4`，**角色A段与角色B段音色可感知不同**（F0 150Hz vs 179Hz）
- [x] 角色A/B 音色分别对应原说话人 GuyNeural/JennyNeural
- [x] 单人 demo（demo.mp4，edge-tts + gpt-sovits 两种模式）回归不破
