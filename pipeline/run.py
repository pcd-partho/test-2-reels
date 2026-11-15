"""Run:  python -m pipeline.run        (set DRY_RUN=1 to test without internet or API keys)"""
import datetime
import json
import os
import shutil
import sys
import traceback
import zlib
from pathlib import Path

import yaml

from . import assemble, captions, gates, notify, script_gen, thumb, visuals, voice
from .topics import demo_repo, fetch_hero, pick_repo
from .util import log

WORK, OUT = Path("work"), Path("out")
CURRENT = {"repo": None}


def pick_language(cfg):
    langs = cfg.get("rotate_languages") or ["en"]
    return os.environ.get("LANGUAGE") or langs[datetime.date.today().toordinal() % len(langs)]


def build_once(cfg, used, dry):
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    WORK.mkdir()
    OUT.mkdir()
    lang = pick_language(cfg)

    repo = demo_repo() if dry else pick_repo(used)
    CURRENT["repo"] = repo["full_name"]
    log("repo:", repo["full_name"], "| language:", lang)

    if dry:
        lang, data, sprov = "en", script_gen.template_script(repo), "dry-run template"
    else:
        sprov, lang, data = script_gen.make_script(cfg, repo, lang)
    scenes = data["scenes"]

    seed = zlib.crc32(repo["full_name"].encode()) % 1000
    hero_path = str(WORK / "hero.png")
    if dry:  # offline test: draw a stand-in picture
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (1280, 640), (40, 60, 90))
        ImageDraw.Draw(im).rectangle([40, 40, 1240, 600], outline=(255, 255, 255), width=6)
        im.save(hero_path)
        hero = hero_path
    else:
        hero = fetch_hero(repo, hero_path)
    log("hero picture:", "yes" if hero else "no (using cards only)")
    bgs, wavs, durs, infos, engines, off = [], [], [], [], [], 0.0
    for i, sc in enumerate(scenes):
        eng, wav, dur, words = voice.synthesize(sc["narration"], lang, cfg, str(WORK / f"v{i}"), dry=dry)
        engines.append(eng)
        bg = visuals.make_bg(str(WORK / f"bg{i}.png"), i, len(scenes), repo, seed, hero=hero)
        bgs.append(bg)
        wavs.append(wav)
        durs.append(dur)
        infos.append({"offset": off, "duration": dur, "text": sc["narration"], "on_screen": sc["on_screen"], "words": words})
        off += dur

    ass = captions.build_ass(infos, lang, str(WORK / "captions.ass"))
    final = OUT / "final.mp4"
    assemble.assemble(bgs, wavs, durs, ass, WORK, final)
    problems = gates.check(str(final))
    if problems:
        raise RuntimeError("quality gate failed: " + "; ".join(problems))

    thumb.make_thumb(data["title"], lang, repo, seed, str(OUT / "thumb.jpg"), hero=hero)
    tags = " ".join("#" + t.replace(" ", "") for t in data["tags"])
    caption = f"{data['title']}\n\n{data['description']}\n\n{tags}\nSource: {repo['url']}\n{cfg.get('ai_label_text', '')}".strip()
    (OUT / "caption.txt").write_text(caption, encoding="utf-8")
    meta = {"repo": repo["full_name"], "url": repo["url"], "language": lang, "title": data["title"],
            "script_provider": sprov, "voice_engines": sorted(set(engines)), "duration_s": round(sum(durs), 1)}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return repo, caption, meta


def main():
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    dry = os.environ.get("DRY_RUN") == "1"
    used = json.load(open("topics.json")) if os.path.exists("topics.json") else []
    failed = None
    last_err = None
    for attempt in (1, 2):
        try:
            repo, caption, meta = build_once(cfg, used, dry)
            break
        except Exception as e:
            last_err = e
            log(f"attempt {attempt} failed:", e)
            traceback.print_exc()
            if not dry and CURRENT["repo"]:
                used.append(CURRENT["repo"])  # do not retry the same repo this run
                failed = CURRENT["repo"]
    else:
        notify.message(f"Video pipeline FAILED: {str(last_err)[:900]}")
        sys.exit(1)

    if not dry:
        notify.send_video(str(OUT / "final.mp4"), str(OUT / "thumb.jpg"), caption)
        notify.message(f"Run info: language={meta['language']} | script={meta['script_provider']} | "
                       f"voice={','.join(meta['voice_engines'])} | length={meta['duration_s']}s | repo={meta['repo']}")
        if repo["full_name"] not in used:
            used.append(repo["full_name"])
        json.dump(used[-500:], open("topics.json", "w"), indent=0)
    log("DONE:", meta)


if __name__ == "__main__":
    main()
