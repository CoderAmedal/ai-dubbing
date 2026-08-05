"""一次性工具：OCR 提取设计稿文字与坐标（dev 用途，不进打包依赖）。

用法: uv run python scripts/ocr_design.py
输出: docs/design-docs/design-pic/notes.md
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.getLogger("easyocr").setLevel(logging.ERROR)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIC_DIR = PROJECT_ROOT / "docs" / "design-docs" / "design-pic"
OUT = PIC_DIR / "notes.md"

PAGES = ["index", "下载", "字幕", "校对", "配音", "引擎", "翻译", "词库", "音色", "合成"]


def main() -> None:
    import easyocr

    reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)

    lines = [
        "# 设计稿 OCR 提取笔记",
        "",
        "> 由 scripts/ocr_design.py 生成。坐标基于原图（约 3836×1987，2x）。",
        "> 布局还原规则：按 (x, y) 聚类为侧栏/顶栏/主区/右栏。",
        "",
    ]

    for name in PAGES:
        img = PIC_DIR / f"{name}.png"
        if not img.exists():
            continue
        results = reader.readtext(str(img))
        # 按 y 排序，再按 x 排序，模拟阅读顺序
        results.sort(key=lambda r: (round(r[0][0][1] / 20), r[0][0][0]))
        lines.append(f"\n## {name}.png\n")
        lines.append("| y | x | 文本 | 置信度 |")
        lines.append("|---|---|------|--------|")
        for box, text, conf in results:
            x, y = int(box[0][0]), int(box[0][1])
            if conf < 0.3:
                continue
            lines.append(f"| {y} | {x} | {text} | {conf:.2f} |")
        lines.append("")
        print(f"OK {name}: {len(results)} 条")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"写入 {OUT}")


if __name__ == "__main__":
    main()
