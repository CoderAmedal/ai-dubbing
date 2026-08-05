# 技术债务跟踪

> 已知债务、不理想模式、待清理项。定期由智能体扫描更新。

| # | 描述 | 影响 | 发现日期 | 状态 |
|---|------|------|---------|------|
| T-001 | 音色克隆（GPT-SoVITS）未接入，TTS 用 edge-tts 占位 | 成片无原说话人音色，不达产品卖点 | 2026-08-04 | ✅ 已解决（0002） |
| T-005 | CPU few-shot 音色相似度有限，GPU 微调可提升 | 音色还原度不完美 | 2026-08-04 | 待办（GPU 里程碑） |
| T-002 | 翻译用 DeepSeek API（联网），本地 Qwen 未验证 | 违反"素材不出本机"主打卖点，需联网 | 2026-08-04 | 待办（14GB 内存偏紧） |
| T-003 | 本机 `all_proxy=socks://` 前缀 httpx 不识别，联网脚本前需 `unset all_proxy ALL_PROXY` | 环境不友好，易踩坑 | 2026-08-04 | 部分解决（0005 后端任务前自动清理 socks 代理；系统级代理配置仍待改） |
| T-004 | `docs/` 曾被 .gitignore 忽略，文档仓库化修复后需确认历史 | 曾导致仓库外知识不可见 | 2026-08-04 | 已修复（本轮） |
| T-006 | `check_architecture.py`（AGENTS.md 提及）尚未创建 | 架构边界无 lint 强制执行 | 2026-08-04 | 待办（编码为 CI 检查） |
| T-007 | diarize/torch 依赖需 CPU 版（torch 走 pytorch CPU index，无法写入 pyproject 普通依赖） | 环境重建需手动装 CPU torch | 2026-08-04 | 部分解决（0007 build.py 用 constraint 锁定 CPU torch；本地安装文档仍待补） |
| T-008 | 桌面应用 Tauri 需系统依赖（webkit2gtk 等），无 sudo 安装文档 | 新机器无法编译 Tauri 壳 | 2026-08-04 | 部分解决（README 有记录；构建机器仍需 sudo） |
| T-009 | Windows NSIS 打包仅 CI 可验证（本仓库无 git remote，workflow 已就绪未跑） | Windows 产物未实测 | 2026-08-04 | 待办（推 GitHub 后触发 CI） |
| T-010 | Tauri 自带 AppImage 打包器在代理环境下卡死，需手动 appimagetool 构建 | 打包流程需人工步骤 | 2026-08-04 | 待办（可脚本化 appimagetool 下载） |
| T-011 | `uv run` 会按 uv.lock 重装 CUDA 版 torch（与 venv 的 CPU torch 冲突），当前须用 `.venv/bin/python` 直接执行 | 文档中的 `uv run pytest` 命令会下载 846MB CUDA torch 或失败 | 2026-08-05 | 待办（uv.lock 与 README CPU-torch 工作流不一致；建议用 constraints 统一或改文档） |
| T-012 | easyocr（设计稿 OCR 用）已用后卸载，`scripts/ocr_design.py` 需重装才能再跑 | 重跑 OCR 需临时 `uv pip install easyocr` + 匹配 torchvision | 2026-08-05 | 已缓解（提取结果已落盘 notes.md，dev 工具勿入打包依赖） |

## 清理原则（黄金原则）

1. 优先共享工具包而非散落的手写辅助函数
2. 不使用"YOLO 式"探测数据——验证边界或依赖类型化 SDK
3. 定期后台任务扫描偏差，发起针对性重构 PR
4. 人类品味一旦捕捉，编码为 lint 或文档，持续应用
