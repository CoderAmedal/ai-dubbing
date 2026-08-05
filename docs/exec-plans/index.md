# 执行计划

> 计划是一等工件。复杂工作先写执行计划（带进度和决策日志），提交到仓库。

## 目录结构

```
exec-plans/
├── active/        # 进行中的计划
├── completed/     # 已完成的计划
└── tech-debt-tracker.md   # 已知技术债务
```

## 活跃计划

| 计划 | 状态 | 说明 |
|------|------|------|
| [0010 本地翻译引擎接入](active/0010-local-translation.md) | 📝 起草中 | Qwen GGUF 本地翻译，兑现"零云端依赖"卖点 |

## 已完成计划

| 计划 | 状态 | 说明 |
|------|------|------|
| [MVP 端到端链路验证](completed/0001-mvp-e2e.md) | ✅ 2026-08-04 | 视频→识别→翻译→配音→混音最小闭环跑通 |
| [GPT-SoVITS 音色克隆接入](completed/0002-gpt-sovits.md) | ✅ 2026-08-04 | few-shot 音色克隆替换 edge-tts 占位，核心卖点落地 |
| [多说话人分离接入](completed/0003-diarization.md) | ✅ 2026-08-04 | 识别"谁在说话"，多角色分组 |
| [多角色音色配音](completed/0004-multi-voice.md) | ✅ 2026-08-04 | 每说话人各自克隆音色配音，多角色卖点完整落地 |
| [Tauri 桌面壳](completed/0005-tauri-shell.md) | ✅ 2026-08-04 | Tauri + FastAPI 桌面应用：GUI 导入/进度/成片预览 |
| [弹性时间轴 + 长停顿剪辑](completed/0006-timeline.md) | ✅ 2026-08-04 | 中文语速自然优先：变速±15% + 停顿裁剪 |
| [多平台接入 + 绿色版打包](completed/0007-provider-packaging.md) | ✅ 2026-08-04 | 零捆绑 AppImage，三环节 provider 可选 + 词库 |
| [启动台首页一比一模仿](completed/0008-launcher-home.md) | ✅ 2026-08-04 | 工作台壳：侧栏/搜索/创作卡片/最近任务/环境就绪度 + 字幕流程（原文字幕/双语字幕/SRT 翻译）落地 |
| [按设计稿实现全部功能页](completed/0009-design-pages.md) | ✅ 2026-08-05 | 下载/字幕/校对/配音/引擎/翻译/词库/音色/合成 9 页按 design-pic 落地，占位页清零；多词库 + 音色库 + yt-dlp + 烧录/软封装 + 配音导出 |

## 工作流

1. 复杂任务 → 在 `active/` 创建计划（`NNNN-名称.md`）
2. 计划含：目标、步骤、验收标准、决策日志、进度
3. 完成 → 移到 `completed/`，更新本索引
4. 发现债务 → 记入 tech-debt-tracker.md
