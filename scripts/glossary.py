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
GLOSSARIES_DIR = "glossaries"
META_FILE = "_meta.json"


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
    """便捷加载（无词库时返回空 dict）。

    多套词库模式下：合并所有"已启用"词库（从上到下优先，后者覆盖前者）。
    旧版单文件 glossary.json 存在时自动并入（视为默认启用词库）。
    """
    lib = GlossaryLibrary()
    return lib.merged_items()


class GlossaryLibrary:
    """多套词库管理（词库页）：每套词库一个 JSON 文件 + 启用开关 + 顺序。

    存储：数据目录 glossaries/<name>.json（词条）+ glossaries/_meta.json（顺序与启用状态）。
    旧版单文件 glossary.json 自动迁移为"默认词库"。
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (resolve_data_dir() / GLOSSARIES_DIR)
        self._default_root = root is None
        self.root.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.root / META_FILE
        if self._default_root:
            self._migrate_legacy()

    def _migrate_legacy(self) -> None:
        legacy = resolve_data_dir() / GLOSSARY_FILE
        default_file = self.root / "默认词库.json"
        if legacy.exists() and not default_file.exists():
            try:
                items = {k: v for k, v in load_json(legacy).items() if k and v}
            except Exception:  # noqa: BLE001
                items = {}
            if items:
                dump_json(items, default_file)
                meta = self._load_meta()
                if "默认词库" not in meta["order"]:
                    meta["order"].append("默认词库")
                    meta["enabled"]["默认词库"] = True
                    self._save_meta(meta)
                log.info("旧版词库已迁移为「默认词库」: %d 条", len(items))

    def _load_meta(self) -> dict:
        if self.meta_path.exists():
            m = load_json(self.meta_path)
            return {"order": m.get("order", []), "enabled": m.get("enabled", {})}
        return {"order": [], "enabled": {}}

    def _save_meta(self, meta: dict) -> None:
        dump_json(meta, self.meta_path)

    def _glossary_path(self, name: str) -> Path:
        safe = "".join(c for c in name if c not in '/\\:*?"<>|').strip()
        return self.root / f"{safe}.json"

    def list(self) -> list[dict]:
        """全部词库（按顺序），含启用状态与词条数。"""
        meta = self._load_meta()
        result = []
        for name in meta["order"]:
            path = self._glossary_path(name)
            count = len(load_json(path)) if path.exists() else 0
            result.append({"name": name, "enabled": meta["enabled"].get(name, True), "count": count})
        return result

    def create(self, name: str) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("词库名不能为空")
        meta = self._load_meta()
        if name in meta["order"]:
            raise ValueError(f"词库已存在: {name}")
        dump_json({}, self._glossary_path(name))
        meta["order"].append(name)
        meta["enabled"][name] = True
        self._save_meta(meta)
        return {"name": name, "enabled": True, "count": 0}

    def set_enabled(self, name: str, enabled: bool) -> None:
        meta = self._load_meta()
        if name not in meta["order"]:
            raise KeyError(f"词库不存在: {name}")
        meta["enabled"][name] = bool(enabled)
        self._save_meta(meta)

    def delete(self, name: str) -> bool:
        meta = self._load_meta()
        if name not in meta["order"]:
            return False
        meta["order"].remove(name)
        meta["enabled"].pop(name, None)
        self._save_meta(meta)
        self._glossary_path(name).unlink(missing_ok=True)
        return True

    def terms(self, name: str) -> dict[str, str]:
        path = self._glossary_path(name)
        return {k: v for k, v in load_json(path).items() if k and v} if path.exists() else {}

    def set_term(self, name: str, src: str, tgt: str) -> None:
        src, tgt = src.strip(), tgt.strip()
        if not src or not tgt:
            return
        terms = self.terms(name)
        terms[src] = tgt
        dump_json(terms, self._glossary_path(name))

    def delete_term(self, name: str, src: str) -> bool:
        terms = self.terms(name)
        if src not in terms:
            return False
        del terms[src]
        dump_json(terms, self._glossary_path(name))
        return True

    def merged_items(self) -> dict[str, str]:
        """合并所有启用词库（顺序后者覆盖前者 = 上方优先）。"""
        merged: dict[str, str] = {}
        for g in reversed(self.list()):
            if g["enabled"]:
                merged.update(self.terms(g["name"]))
        # 兼容：旧版单文件未被迁移时兜底（仅默认根目录）
        if not merged and self._default_root:
            merged = GlossaryStore().items
        return merged
