"""Provider 抽象层 + 词库单测。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import providers  # noqa: F401 — 触发注册
from glossary import GlossaryStore
from providers.base import AsrProvider, TranslateProvider
from providers.registry import get_provider, list_providers


class TestRegistry:
    def test_all_stages_registered(self):
        names = [i.name for i in list_providers()]
        assert "faster-whisper" in names
        assert "whisper.cpp" in names
        assert "deepseek" in names
        assert "edge-tts" in names
        assert "gpt-sovits" in names

    def test_stage_filter(self):
        asr = [i.name for i in list_providers("asr")]
        assert asr == ["faster-whisper", "whisper.cpp"]

    def test_get_provider_typecheck(self):
        p = get_provider("faster-whisper", AsrProvider)
        assert isinstance(p, AsrProvider)
        # 跨环节实例化应报错
        try:
            get_provider("faster-whisper", TranslateProvider)
            assert False, "应抛 TypeError"
        except TypeError:
            pass

    def test_unknown_provider(self):
        try:
            get_provider("nope")
            assert False, "应抛 KeyError"
        except KeyError:
            pass

    def test_provider_metadata_for_gui(self):
        asr = next(i for i in list_providers("asr") if i.name == "whisper.cpp")
        assert asr.requires_model
        assert any(m["name"] == "small" for m in asr.models)


class TestGlossaryStore:
    def test_set_and_reload(self, tmp_path: Path):
        store = GlossaryStore(tmp_path / "glossary.json")
        store.set("GPT", "生成式预训练模型")
        store.set("LLM", "大语言模型")
        assert store.items["GPT"] == "生成式预训练模型"

        store2 = GlossaryStore(tmp_path / "glossary.json")
        assert store2.items["LLM"] == "大语言模型"

    def test_import_csv(self, tmp_path: Path):
        csv_path = tmp_path / "terms.csv"
        csv_path.write_text("源语,译语\nRAG,检索增强生成\nReAct,推理-行动\n", encoding="utf-8")
        store = GlossaryStore(tmp_path / "glossary.json")
        n = store.import_csv(csv_path)
        assert n == 2
        assert store.items["RAG"] == "检索增强生成"

    def test_export_roundtrip(self, tmp_path: Path):
        store = GlossaryStore(tmp_path / "glossary.json")
        store.set("A", "甲")
        out = tmp_path / "out.csv"
        store.export_csv(out)
        store2 = GlossaryStore(tmp_path / "glossary2.json")
        store2.import_csv(out)
        assert store2.items == {"A": "甲"}

    def test_apply_post(self, tmp_path: Path):
        store = GlossaryStore(tmp_path / "glossary.json")
        store.set("RAG", "检索增强生成")
        assert store.apply_post("关于 RAG 的原理") == "关于 检索增强生成 的原理"

    def test_delete(self, tmp_path: Path):
        store = GlossaryStore(tmp_path / "glossary.json")
        store.set("X", "Y")
        assert store.delete("X") is True
        assert store.delete("X") is False
        assert store.items == {}
