"""0009 新增模块单元测试：下载链接解析、字幕样式、音色库、配音服务配置解析。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from downloader import extract_urls
from glossary import GlossaryLibrary
from subtitle_style import PRESETS, to_force_style
from voice_library import VoiceLibrary


class TestExtractUrls:
    def test_plain_lines(self):
        text = "https://youtu.be/abc123\nhttps://www.bilibili.com/video/BV1xx"
        assert extract_urls(text) == [
            "https://youtu.be/abc123",
            "https://www.bilibili.com/video/BV1xx",
        ]

    def test_mixed_chat_text(self):
        text = "看这个视频 https://youtu.be/abc123 很不错，还有https://a.com/v?x=1。"
        urls = extract_urls(text)
        assert "https://youtu.be/abc123" in urls
        assert "https://a.com/v?x=1" in urls

    def test_dedup_and_strip_trailing_punct(self):
        text = "https://a.com/v, https://a.com/v,"
        assert extract_urls(text) == ["https://a.com/v"]

    def test_empty(self):
        assert extract_urls("没有链接") == []


class TestSubtitleStyle:
    def test_default_outline_mode(self):
        fs = to_force_style({})
        assert "BorderStyle=1" in fs
        assert "PrimaryColour=&H00FFFFFF" in fs
        assert "Outline=2" in fs

    def test_box_mode(self):
        fs = to_force_style({"back_mode": "box", "box_color": "#000000", "box_opacity": 100})
        assert "BorderStyle=3" in fs
        assert "BackColour=&H00000000" in fs
        assert "Shadow=0" in fs

    def test_color_conversion_bgr(self):
        # #FF0000（红）→ ASS &H000000FF（BBGGRR）
        fs = to_force_style({"color": "#FF0000"})
        assert "PrimaryColour=&H000000FF" in fs

    def test_all_presets_valid(self):
        for name, preset in PRESETS.items():
            fs = to_force_style(preset)
            assert "FontName=" in fs, name
            assert "FontSize=" in fs, name

    def test_bold_flag(self):
        fs = to_force_style({"bold": True})
        assert "Bold=1" in fs


class TestVoiceLibrary:
    def test_add_get_delete(self, tmp_path: Path):
        ref = tmp_path / "ref.wav"
        ref.write_bytes(b"RIFFfake")
        lib = VoiceLibrary(root=tmp_path / "voices")
        item = lib.add("角色A", ref, prompt_text="hello", prompt_lang="en")
        assert item["name"] == "角色A"
        assert Path(item["ref_audio"]).exists()

        lib2 = VoiceLibrary(root=tmp_path / "voices")  # 重新加载持久化
        assert len(lib2.items) == 1
        assert lib2.get(item["id"])["prompt_text"] == "hello"

        assert lib2.delete(item["id"]) is True
        assert lib2.items == []
        assert not Path(item["ref_audio"]).exists()

    def test_add_default_name(self, tmp_path: Path):
        ref = tmp_path / "a.mp3"
        ref.write_bytes(b"x")
        lib = VoiceLibrary(root=tmp_path / "voices")
        item = lib.add("", ref)
        assert item["name"].startswith("音色")

    def test_delete_missing(self, tmp_path: Path):
        lib = VoiceLibrary(root=tmp_path / "voices")
        assert lib.delete("nonexistent") is False


class TestGlossaryLibrary:
    def test_create_list_toggle(self, tmp_path: Path):
        lib = GlossaryLibrary(root=tmp_path / "g")
        lib.create("剧集A")
        lib.create("剧集B")
        items = lib.list()
        assert [g["name"] for g in items] == ["剧集A", "剧集B"]
        assert all(g["enabled"] for g in items)

        lib.set_enabled("剧集A", False)
        items = lib.list()
        assert items[0]["enabled"] is False

    def test_terms_and_merge_priority(self, tmp_path: Path):
        lib = GlossaryLibrary(root=tmp_path / "g")
        lib.create("顶部")
        lib.create("底部")
        lib.set_term("底部", "RAG", "检索增强")
        lib.set_term("底部", "LLM", "大模型")
        lib.set_term("顶部", "RAG", "检索增强生成")  # 列表首位=最上方=优先
        merged = lib.merged_items()
        assert merged["RAG"] == "检索增强生成"
        assert merged["LLM"] == "大模型"

    def test_disabled_excluded_from_merge(self, tmp_path: Path):
        lib = GlossaryLibrary(root=tmp_path / "g")
        lib.create("A")
        lib.set_term("A", "x", "y")
        lib.set_enabled("A", False)
        assert lib.merged_items() == {}

    def test_delete_term_and_glossary(self, tmp_path: Path):
        lib = GlossaryLibrary(root=tmp_path / "g")
        lib.create("A")
        lib.set_term("A", "x", "y")
        assert lib.delete_term("A", "x") is True
        assert lib.terms("A") == {}
        assert lib.delete("A") is True
        assert lib.list() == []

    def test_create_duplicate_rejected(self, tmp_path: Path):
        import pytest

        lib = GlossaryLibrary(root=tmp_path / "g")
        lib.create("A")
        with pytest.raises(ValueError):
            lib.create("A")


class TestTtsConfigResolve:
    def test_voice_id_injects_sovits(self, tmp_path: Path, monkeypatch):
        ref = tmp_path / "ref.wav"
        ref.write_bytes(b"RIFF")
        lib = VoiceLibrary(root=tmp_path / "voices")
        item = lib.add("测试", ref, prompt_text="示例文本", prompt_lang="zh")

        import voice_library
        monkeypatch.setattr(voice_library, "VoiceLibrary", lambda: lib)
        import tts_service
        monkeypatch.setattr(tts_service, "VoiceLibrary", lambda: lib, raising=False)

        from tts_service import _resolve_tts_config

        provider, cfg = _resolve_tts_config({"tts": {"provider": "edge-tts"}}, {"voice_id": item["id"]})
        assert provider == "gpt-sovits"
        assert cfg["ref_audio"] == item["ref_audio"]
        assert cfg["prompt_text"] == "示例文本"

    def test_default_edge_tts(self):
        from tts_service import _resolve_tts_config

        provider, _cfg = _resolve_tts_config({"tts": {"provider": "edge-tts", "voice": "v"}}, None)
        assert provider == "edge-tts"
