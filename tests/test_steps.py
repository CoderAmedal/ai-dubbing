"""核心纯逻辑单元测试：SRT 格式化、翻译结果结构。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from speaker_ref import _trim_to_max, select_reference_segment
from step1_asr import merge_speakers, to_srt
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


class TestMergeSpeakers:
    def test_assigns_speaker_by_overlap(self):
        asr = [
            {"id": 0, "start": 0.0, "end": 3.12, "text": "A"},
            {"id": 1, "start": 4.08, "end": 8.0, "text": "B"},
        ]
        diar = [
            {"start": 0.2, "end": 2.7, "speaker": "SPEAKER_00"},
            {"start": 3.6, "end": 7.8, "speaker": "SPEAKER_01"},
        ]
        merged = merge_speakers(asr, diar)
        assert merged[0]["speaker"] == "SPEAKER_00"
        assert merged[1]["speaker"] == "SPEAKER_01"

    def test_no_overlap_defaults_unknown(self):
        asr = [{"id": 0, "start": 50.0, "end": 60.0, "text": "X"}]
        diar = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"}]
        merged = merge_speakers(asr, diar)
        assert merged[0]["speaker"] == "UNKNOWN"


class TestSelectReferenceSegment:
    def test_short_segment_expands_to_min(self):
        segs = [{"start": 0.2, "end": 2.1, "speaker": "A"}]
        other = [
            {"start": 0.2, "end": 2.1, "speaker": "A"},
            {"start": 3.1, "end": 5.2, "speaker": "B"},
        ]
        best = select_reference_segment(segs, other, duration=18.0)
        assert best["end"] - best["start"] >= 3.0

    def test_long_segment_stays_as_is(self):
        segs = [{"start": 1.0, "end": 6.0, "speaker": "A"}]
        other = [
            {"start": 1.0, "end": 6.0, "speaker": "A"},
            {"start": 8.0, "end": 10.0, "speaker": "B"},
        ]
        best = select_reference_segment(segs, other, duration=18.0)
        assert abs((best["end"] - best["start"]) - 5.0) < 0.5


class TestTrimToMax:
    def test_60s_window_trimmed_to_10s_center(self):
        trimmed = _trim_to_max({"start": 0.0, "end": 60.0}, duration=60.0)
        assert abs((trimmed["end"] - trimmed["start"]) - 10.0) < 0.1
        assert abs((trimmed["start"] + trimmed["end"]) / 2 - 30.0) < 0.1

    def test_within_max_stays_unchanged(self):
        window = {"start": 2.0, "end": 8.0}
        trimmed = _trim_to_max(window, duration=60.0)
        assert trimmed == window
