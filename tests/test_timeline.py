"""弹性时间轴核心逻辑单测：变速决策、漂移约束、停顿裁剪。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from timeline import PAUSE_TARGET, compute_placements, pick_speed


class TestPickSpeed:
    def test_long_zh_speeds_up(self):
        assert pick_speed(zh_dur=4.0, orig_dur=3.0) == 1.15  # ratio 1.33 > 1.15

    def test_short_zh_slows_down(self):
        assert pick_speed(zh_dur=2.0, orig_dur=3.0) == 0.85  # ratio 0.67 < 0.85

    def test_balanced_no_change(self):
        assert pick_speed(zh_dur=3.0, orig_dur=3.0) == 1.0

    def test_slight_diff_no_change(self):
        assert pick_speed(zh_dur=3.1, orig_dur=3.0) == 1.0  # ratio 1.03


class TestComputePlacements:
    def _segs(self, spec):
        """spec: [(start, end, zh_dur), ...]"""
        return [
            {
                "id": i,
                "start": s,
                "end": e,
                "zh_dur": d,
                "tgt_audio": f"seg_{i:03d}.wav",
            }
            for i, (s, e, d) in enumerate(spec)
        ]

    def test_contiguous_zh_flows_naturally(self):
        segs = self._segs([(0.0, 3.0, 4.0), (3.0, 6.0, 4.0)])
        compute_placements(segs, video_duration=10.0)
        # 第一段超长 → 变速 1.15，ndur=4/1.15=3.48
        assert abs(segs[0]["ndur"] - 3.478) < 0.01
        # 第二段紧随（无空隙）
        assert abs(segs[1]["new_start"] - segs[0]["new_end"]) < 0.001

    def test_no_overlap_between_segments(self):
        segs = self._segs([(0.0, 2.0, 5.0), (2.0, 4.0, 5.0)])
        compute_placements(segs, video_duration=10.0)
        assert segs[1]["new_start"] >= segs[0]["new_end"] - 1e-6

    def test_long_pause_clipped(self):
        # 原始空隙 4.0s（两段间隔），应裁剪到 PAUSE_TARGET
        segs = self._segs([(0.0, 2.0, 2.0), (6.0, 8.0, 2.0)])
        compute_placements(segs, video_duration=10.0)
        gap = segs[1]["new_start"] - segs[0]["new_end"]
        assert gap <= PAUSE_TARGET + 1e-6

    def test_short_pause_kept(self):
        segs = self._segs([(0.0, 2.0, 2.0), (2.5, 4.5, 2.0)])
        compute_placements(segs, video_duration=10.0)
        gap = segs[1]["new_start"] - segs[0]["new_end"]
        assert 0.4 <= gap <= 0.6  # 原空隙 ~0.5s 保留

    def test_drift_bounded_realistic(self):
        # 8 段连续语音，每段译文比原时长长 30%（变速 1.15 后残差小）
        segs = self._segs([(i * 2.0, i * 2.0 + 1.0, 1.3) for i in range(8)])
        compute_placements(segs, video_duration=20.0)
        for s in segs:
            assert s["new_start"] - s["start"] <= 2.0 + 1e-6

    def test_extreme_no_overlap_monotonic(self):
        # 极端超长：段无重叠、时间单调递增（顺序音频下漂移自然增长）
        segs = self._segs([(i * 2.0, i * 2.0 + 1.0, 3.0) for i in range(8)])
        compute_placements(segs, video_duration=20.0)
        for i in range(1, len(segs)):
            assert segs[i]["new_start"] >= segs[i - 1]["new_end"] - 1e-6
            assert segs[i]["new_end"] > segs[i]["new_start"]
