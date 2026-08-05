"""专业词库模块 — 术语表管理。

词库 = {源语: 译语} 映射。来源：GUI 编辑或 CSV 导入。
CSV 格式：两列 `源语,译语`（首行可含表头，自动跳过）。

用法：
  from glossary import GlossaryStore, load_csv
  store = GlossaryStore()
  store.import_csv(Path("terms.csv"))
  store.items  # {源语: 译语}
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from common import dump_json, load_json
from runtime import resolve_data_dir

log = logging.getLogger("glossary")

GLOSSARY_FILE = "glossary.json"


class GlossaryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (resolve_data_dir() / GLOSSARY_FILE)
        self._items: dict[str, str] = {}
        self.reload()

    @property
    def items(self) -> dict[str, str]:
        return dict(self._items)

    def reload(self) -> None:
        if self.path.exists():
            self._items = {k: v for k, v in load_json(self.path).items() if k and v}
        else:
            self._items = {}

    def save(self) -> None:
        dump_json(self._items, self.path)
        log.info("词库已保存: %d 条 -> %s", len(self._items), self.path)

    def set(self, src: str, tgt: str) -> None:
        src, tgt = src.strip(), tgt.strip()
        if not src or not tgt:
            return
        self._items[src] = tgt
        self.save()

    def delete(self, src: str) -> bool:
        if src in self._items:
            del self._items[src]
            self.save()
            return True
        return False

    def import_csv(self, path: Path) -> int:
        """导入 CSV（源语,译语），返回新增条数。"""
        added = 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                src, tgt = row[0].strip(), row[1].strip()
                if not src or not tgt:
                    continue
                if src == "源语" or src.lower() == "source":
                    continue  # 表头
                if self._items.get(src) != tgt:
                    self._items[src] = tgt
                    added += 1
        self.save()
        return added

    def export_csv(self, path: Path) -> int:
        """导出 CSV，返回条数。"""
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["源语", "译语"])
            for src, tgt in self._items.items():
                writer.writerow([src, tgt])
        return len(self._items)

    def apply_post(self, text: str) -> str:
        """后处理校验替换：译文出现源语术语时替换为译语。"""
        for src, tgt in self._items.items():
            if src and src in text:
                text = text.replace(src, tgt)
        return text


def load_glossary() -> dict[str, str]:
    """便捷加载（无词库时返回空 dict）。"""
    return GlossaryStore().items
