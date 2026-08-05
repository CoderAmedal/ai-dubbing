"""音色库模块 — 管理"我的音色"（克隆参考音频）（音色页后端）。

音色 = {id, name, ref_audio(路径), prompt_text, prompt_lang, created_at}。
存储：数据目录 voices/ 下，voices.json 为索引，音频文件同目录。
来源：用户上传参考音频；或从说话人分离产物（workdir/refs/）导入。

用法：
  from voice_library import VoiceLibrary
  lib = VoiceLibrary()
  lib.add("角色A", Path("ref.wav"), prompt_text="...", prompt_lang="zh")
  lib.items  # [{id, name, ...}]
"""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from pathlib import Path

from common import dump_json, load_json
from runtime import resolve_data_dir

log = logging.getLogger("voice_library")

VOICES_DIR = "voices"
INDEX_FILE = "voices.json"


class VoiceLibrary:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (resolve_data_dir() / VOICES_DIR)
        self.index_path = self.root / INDEX_FILE
        self.root.mkdir(parents=True, exist_ok=True)
        self._items: list[dict] = []
        self.reload()

    @property
    def items(self) -> list[dict]:
        return [dict(i) for i in self._items]

    def reload(self) -> None:
        if self.index_path.exists():
            self._items = [i for i in load_json(self.index_path) if i.get("id")]
        else:
            self._items = []

    def save(self) -> None:
        dump_json(self._items, self.index_path)
        log.info("音色库已保存: %d 条 -> %s", len(self._items), self.index_path)

    def get(self, voice_id: str) -> dict | None:
        return next((i for i in self._items if i["id"] == voice_id), None)

    def add(
        self,
        name: str,
        ref_audio: Path,
        prompt_text: str = "",
        prompt_lang: str = "zh",
    ) -> dict:
        """添加音色：复制参考音频到音色库目录。"""
        name = name.strip() or f"音色 {len(self._items) + 1}"
        voice_id = uuid.uuid4().hex[:8]
        ext = ref_audio.suffix or ".wav"
        dest = self.root / f"{voice_id}{ext}"
        shutil.copy2(ref_audio, dest)
        item = {
            "id": voice_id,
            "name": name,
            "ref_audio": str(dest),
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "created_at": time.time(),
        }
        self._items.append(item)
        self.save()
        return item

    def delete(self, voice_id: str) -> bool:
        item = self.get(voice_id)
        if not item:
            return False
        audio = Path(item["ref_audio"])
        if audio.exists() and audio.parent == self.root:
            audio.unlink()
        self._items = [i for i in self._items if i["id"] != voice_id]
        self.save()
        return True

    def rename(self, voice_id: str, name: str) -> bool:
        item = self.get(voice_id)
        if not item or not name.strip():
            return False
        item["name"] = name.strip()
        self.save()
        return True
