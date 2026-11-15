import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .util import find_font
from .visuals import PALETTES, _gradient


def make_thumb(title, lang, repo, seed, out_path, hero=None):
    if hero:
        img = Image.open(hero).convert("RGB").resize((1280, 720))
        img = ImageEnhance.Brightness(img).enhance(0.45)
    else:
        c1, c2 = PALETTES[seed % len(PALETTES)]
        img = _gradient((1280, 720), c1, c2)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(find_font(lang, bold=True) or find_font("en", True), 96)
    small = ImageFont.truetype(find_font("en", bold=True) or find_font("en"), 44)
    words = title.split()[:6]
    text = "\n".join(textwrap.wrap(" ".join(words), 16)[:3])
    d.multiline_text((70, 90), text, font=font, fill=(255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0), spacing=14)
    d.text((70, 610), f"{repo['stars']:,} stars on GitHub", font=small, fill=(255, 215, 0), stroke_width=3, stroke_fill=(0, 0, 0))
    img.save(out_path, quality=88)
    return out_path
