import re

from .util import font_family


def _t(sec):
    sec = max(0.0, sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(s):
    return re.sub(r"[{}]", "", s).replace("\n", " ").strip()


def _chunks(text, words, dur, per=5):
    """Return [(start, end, text)] relative to scene start."""
    toks = text.split()
    spoken = max(0.5, dur - 0.35)
    if words and len(words) >= max(2, len(toks) // 2):
        out = []
        for i in range(0, len(words), per):
            grp = words[i:i + per]
            out.append((grp[0]["start"], grp[-1]["start"] + grp[-1]["dur"] + 0.05, " ".join(w["text"] for w in grp)))
        return out
    weights = [len(t) + 2 for t in toks] or [1]
    total = float(sum(weights))
    t0, out, i = 0.0, [], 0
    while i < len(toks):
        grp = toks[i:i + per]
        w = sum(weights[i:i + per])
        d = spoken * w / total
        out.append((t0, t0 + d, " ".join(grp)))
        t0 += d
        i += per
    return out


def build_ass(scenes_info, lang, out_path):
    fam = font_family(lang)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{fam},72,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,2,70,70,420,1
Style: Title,{fam},60,&H0000D7FF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,5,2,8,70,70,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for sc in scenes_info:
        off, dur = sc["offset"], sc["duration"]
        if sc.get("on_screen"):
            lines.append(f"Dialogue: 0,{_t(off + 0.1)},{_t(off + min(3.0, dur - 0.2))},Title,,0,0,0,,{_clean(sc['on_screen'])}")
        for a, b, txt in _chunks(sc["text"], sc.get("words"), dur):
            lines.append(f"Dialogue: 0,{_t(off + a)},{_t(off + b)},Cap,,0,0,0,,{_clean(txt)}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")
    return out_path
