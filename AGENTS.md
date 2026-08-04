# AGENTS.md — AI 配音工作台

> 本文件是**地图**，不是百科全书。先读这里，再按链接去 `docs/` 找深层信息。
> 本仓库遵循 Harness Engineering 模式：人类掌舵，智能体执行。代码由智能体编写。

## 项目是什么

本地 AI 视频翻译配音桌面应用：上传外语视频 → 自动识别说话人 → 翻译 → 用原说话人音色配音 → 输出中文成片。对标海风声影 Studio。

## 快速导航

| 想了解 | 去哪里 |
|--------|--------|
| 产品定位与功能 | [docs/product-specs/](docs/product-specs/) |
| 技术架构与选型 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 设计决策与验证状态 | [docs/design-docs/index.md](docs/design-docs/index.md) |
| 当前执行计划 | [docs/exec-plans/active/](docs/exec-plans/active/) |
| 已知技术债务 | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 核心信念（不可违背）

1. **智能体优先**：所有代码、测试、CI、文档由智能体编写。人类不手动写代码。
2. **仓库即记录系统**：仓库里看不到的知识 = 不存在。任何关键决策必须落地为仓库内文档。
3. **地图而非说明书**：AGENTS.md 保持精简（~100行），深层知识放 docs/，靠链接渐进披露。
4. **强制执行不变量**：用 lint/测试强制架构边界，不靠口头约定。
5. **计划是一等工件**：复杂工作先写执行计划，再写代码，计划随进度更新并提交。

## 技术栈

- 桌面壳：Tauri（Rust + Web 前端）
- 后端：Python FastAPI（本地服务，127.0.0.1）
- AI 组件：faster-whisper / pyannote / GPT-SoVITS / Qwen 本地翻译 / UVR5
- 视频处理：ffmpeg / yt-dlp
- 包管理：uv（Python）、cargo（Rust）

> 详细选型理由见 [docs/design-docs/tech-stack.md](docs/design-docs/tech-stack.md)

## 架构约束（lint 强制执行）

每个业务域内，依赖只允许"向前"流动：

```
Types → Config → Repo → Service → Runtime → UI
```

横切关注点（认证、遥测、功能标志）只能通过 `Providers` 接口进入。违反此规则 = CI 失败。

> 详见 [ARCHITECTURE.md](ARCHITECTURE.md)

## 工作流程

1. **新任务**：先看 `docs/exec-plans/active/` 是否有相关计划；复杂任务先创建执行计划。
2. **实施**：按计划写代码 + 测试，遵守架构约束。
3. **验证**：跑测试 + lint + 结构检查；能启动应用就实际验证。
4. **提交**：小步提交，信息清晰，一个 PR 一个主题。
5. **完成**：更新计划状态（active → completed），更新相关文档。

## 质量标准

- 测试：核心逻辑必须有测试（pytest / cargo test）
- 边界解析数据（parse, don't validate）
- 日志：结构化日志，字段一致
- 文件大小：单个源文件尽量 < 500 行
- 文档：改动行为必须同步更新 docs/

## 常用命令

```bash
# Python 后端
uv venv && uv pip install -e ".[dev]"
uv run pytest

# 前端/桌面壳
cd app && cargo build

# 结构检查
uv run python scripts/check_architecture.py
```

## 给智能体的提示

- 遇到模糊需求：在仓库内创建/更新 design-doc 记录决策，而不是问人类
- 发现文档过时：直接修文档（doc-gardening）
- 发现不良模式：记录到 tech-debt-tracker.md，并考虑编码为 lint
- 多智能体协作时：通过 PR + 评论交互，用 `gh` 等标准工具
