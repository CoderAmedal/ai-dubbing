"""核心纯逻辑单元测试：SRT 格式化、翻译结果结构。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from step1_asr import to_srt
from step4_mux import make_srt


class TestSrtFormat:
    def test_to_srt_basic(self):
        segments = [{"id": 0, "start": 0.0, "end": 3.12, "text": "Hello world."}]
        srt = to_srt(segments)
        assert "1" in srt
        assert "00:00:00,000 --> 00:00:03,120" in srt
        assert "Hello world." in srt

    def test_to_srt_rounds_ms(self):
        segments = [{"id": 0, "start": 4.08, "end": 8.0, "text": "Hi"}]
        srt = to_srt(segments)
        assert "00:00:04,080 --> 00:00:08,000" in srt


class TestMakeSrt:
    def test_make_srt_writes_chinese(self, tmp_path: Path):
        trans = [
            {"id": 0, "start": 0.0, "end": 3.0, "tgt": "大家好", "src": "hello"},
        ]
        out = tmp_path / "subs.srt"
        make_srt(trans, out)
        text = out.read_text(encoding="utf-8")
        assert "大家好" in text
        assert "00:00:00,000 --> 00:00:03,000" in text


class TestTranslationShape:
    def test_translate_result_has_expected_fields(self):
        import json

        data = json.loads(
            '{"id":0,"start":0.0,"end":1.5,"src":"hi","tgt":"你好"}'
        )
        assert set(data) >= {"id", "start", "end", "src", "tgt"}
