"""字幕样式模块 — 预设样式 + 样式 dict → ASS force_style 串（合成页核心）。

设计稿：design-pic/合成.png（左列样式编辑器：预设/基础设置/样式效果/高级设置）。
样式 dict 字段：
  font(字体) size(字号) color(字体颜色 #RRGGBB)
  back_mode: "outline"(描边+阴影) | "box"(底色色块)
  outline_color / outline_width / shadow_color / shadow_opacity(0-100) / box_color
预设：经典白字黑边 / 电影字幕 / YouTube风格 / 黑底白字 / 清新简约 / 醒目加粗。
"""

from __future__ import annotations


# ASS 颜色格式 &HAABBGGRR（AA 透明度，00 不透明）
def _ass_color(hex_color: str, opacity: int = 100) -> str:
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    aa = f"{255 - round(opacity * 255 / 100):02X}"
    return f"&H{aa}{b}{g}{r}".upper()


PRESETS: dict[str, dict] = {
    "经典白字黑边": {
        "font": "Noto Sans CJK SC", "size": 24, "color": "#FFFFFF",
        "back_mode": "outline", "outline_color": "#000000", "outline_width": 2,
        "shadow_color": "#000000", "shadow_opacity": 50,
    },
    "电影字幕": {
        "font": "Noto Serif CJK SC", "size": 22, "color": "#FFFFFF",
        "back_mode": "outline", "outline_color": "#101010", "outline_width": 2,
        "shadow_color": "#000000", "shadow_opacity": 60,
    },
    "YouTube风格": {
        "font": "Noto Sans CJK SC", "size": 24, "color": "#FFFFFF",
        "back_mode": "box", "box_color": "#000000", "box_opacity": 70,
        "outline_width": 0, "shadow_opacity": 0,
    },
    "黑底白字": {
        "font": "Noto Sans CJK SC", "size": 24, "color": "#FFFFFF",
        "back_mode": "box", "box_color": "#000000", "box_opacity": 100,
        "outline_width": 0, "shadow_opacity": 0,
    },
    "清新简约": {
        "font": "Noto Sans CJK SC", "size": 22, "color": "#F5F5F5",
        "back_mode": "outline", "outline_color": "#333333", "outline_width": 1,
        "shadow_color": "#000000", "shadow_opacity": 30,
    },
    "醒目加粗": {
        "font": "Noto Sans CJK SC", "size": 30, "color": "#FFE04B",
        "back_mode": "outline", "outline_color": "#000000", "outline_width": 3,
        "shadow_color": "#000000", "shadow_opacity": 60, "bold": True,
    },
}

# 默认样式 = 经典白字黑边
DEFAULT_STYLE = PRESETS["经典白字黑边"]


def to_force_style(style: dict) -> str:
    """样式 dict → ffmpeg subtitles force_style 字符串。"""
    s = {**DEFAULT_STYLE, **(style or {})}
    parts = [
        f"FontName={s['font']}",
        f"FontSize={s['size']}",
        f"PrimaryColour={_ass_color(s['color'])}",
        f"Bold={1 if s.get('bold') else 0}",
        "Alignment=2",  # 底部居中
        "MarginV=24",
    ]
    if s.get("back_mode") == "box":
        # BorderStyle=3：底色色块（BackColour 作为底色）
        parts.append("BorderStyle=3")
        parts.append(f"BackColour={_ass_color(s.get('box_color', '#000000'), s.get('box_opacity', 70))}")
        parts.append(f"Outline={s.get('outline_width', 0) or 1}")  # box 模式下 outline=色块边距
        parts.append("Shadow=0")
    else:
        parts.append("BorderStyle=1")
        parts.append(f"OutlineColour={_ass_color(s.get('outline_color', '#000000'))}")
        parts.append(f"Outline={s.get('outline_width', 2)}")
        shadow_opacity = s.get("shadow_opacity", 0)
        parts.append(f"BackColour={_ass_color(s.get('shadow_color', '#000000'), shadow_opacity)}")
        parts.append(f"Shadow={1 if shadow_opacity else 0}")
    return ",".join(parts)
