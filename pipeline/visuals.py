import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .util import find_font

PALETTES = [((15, 32, 39), (44, 83, 100)), ((35, 37, 38), (65, 67, 69)), ((30, 60, 114), (42, 82, 152)),
            ((66, 39, 90), (115, 75, 109)), ((19, 78, 94), (113, 178, 128)), ((58, 28, 113), (215, 109, 119))]
GOLD, WHITE, SOFT = (255, 215, 0, 255), (255, 255, 255, 255), (220, 230, 240, 255)


def _gradient(size, c1, c2):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(c1)[None, None, :]
    b = np.array(c2)[None, None, :]
    arr = (a * (1 - t) + b * t).astype("uint8")
    return Image.fromarray(np.repeat(arr, w, axis=1), "RGB")


def _fonts():
    fp, fb = find_font("en"), find_font("en", bold=True)
    return (ImageFont.truetype(fb or fp, 66), ImageFont.truetype(fp, 44),
            ImageFont.truetype(fb or fp, 150), ImageFont.truetype(fb or fp, 56))


def _card(d, box):
    d.rounded_rectangle(box, radius=40, fill=(255, 255, 255, 38), outline=(255, 255, 255, 90), width=3)


def _dots(d, idx, total, w, h):
    gap, r = 46, 11
    x0 = w // 2 - (total - 1) * gap // 2
    for i in range(total):
        col = GOLD if i == idx else (255, 255, 255, 110)
        d.ellipse([x0 + i * gap - r, h - 150 - r, x0 + i * gap + r, h - 150 + r], fill=col)


def _short(name, n=24):
    return name if len(name) <= n else name[:n - 1] + "..."


def make_bg(path, idx, total, repo, seed, hero=None, size=(1080, 1920)):
    """Scene picture. Layout depends on the scene number so the video does not look repeated."""
    w, h = size
    c1, c2 = PALETTES[seed % len(PALETTES)]
    img = _gradient(size, c1, c2)
    d = ImageDraw.Draw(img, "RGBA")
    f_big, f_mid, f_huge, f_num = _fonts()
    top = [430, 560, 690][(seed + idx) % 3]
    last = idx == total - 1

    if idx == 0 and hero:
        # opening shot: GitHub's own picture of the repo
        pic = Image.open(hero).convert("RGB").resize((940, 470))
        mask = Image.new("L", pic.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pic.size[0], pic.size[1]], radius=36, fill=255)
        img.paste(pic, (70, top), mask)
        d.text((70, top + 520), _short(repo["full_name"], 22), font=f_big, fill=WHITE)
        d.text((70, top + 610), f"{repo['stars']:,} stars", font=f_mid, fill=GOLD)
    elif idx == 1:
        # numbers card
        _card(d, [70, top, w - 70, top + 620])
        rows = [(f"{repo['stars']:,}", "stars"), (f"{repo.get('forks', 0):,}", "forks"), (f"{repo.get('issues', 0):,}", "open issues")]
        for i, (num, lab) in enumerate(rows):
            y = top + 40 + i * 190
            d.text((120, y), num, font=f_num, fill=GOLD if i == 0 else WHITE)
            d.text((120 + int(d.textlength(num, font=f_num)) + 30, y + 24), lab, font=f_mid, fill=SOFT)
    elif idx == 2 and (repo.get("topics") or repo.get("language")):
        # built-with card with topic chips
        _card(d, [70, top, w - 70, top + 620])
        d.text((120, top + 50), "Built with", font=f_mid, fill=SOFT)
        d.text((120, top + 120), repo.get("language") or "Open source", font=f_big, fill=WHITE)
        x, y = 120, top + 270
        for t in (repo.get("topics") or [])[:5]:
            tw = int(d.textlength(t, font=f_mid)) + 50
            if x + tw > w - 100:
                x, y = 120, y + 100
            d.rounded_rectangle([x, y, x + tw, y + 76], radius=38, fill=(255, 215, 0, 60), outline=GOLD, width=2)
            d.text((x + 25, y + 12), t, font=f_mid, fill=WHITE)
            x += tw + 20
    elif last:
        # follow card
        _card(d, [70, top, w - 70, top + 520])
        d.text((120, top + 70), "Follow for more", font=f_big, fill=GOLD)
        d.text((120, top + 190), "trending GitHub repos", font=f_mid, fill=WHITE)
        d.text((120, top + 270), "every week", font=f_mid, fill=WHITE)
        d.text((120, top + 390), _short(repo["full_name"], 30), font=f_mid, fill=SOFT)
    else:
        # default repo card
        _card(d, [70, top, w - 70, top + 380])
        d.text((110, top + 50), _short(repo["full_name"], 21), font=f_big, fill=WHITE)
        d.text((110, top + 170), f"{repo['stars']:,} stars", font=f_mid, fill=GOLD)
        if repo.get("language"):
            d.text((110, top + 245), repo["language"], font=f_mid, fill=SOFT)
    _dots(d, idx, total, w, h)
    img.save(path)
    return path
