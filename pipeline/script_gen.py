import json
import os
import re

import requests

from .util import first_working, log

LANG_NAME = {"bn": "Bangla (Bengali script)", "hi": "Hindi (Devanagari script)", "en": "English"}


def build_prompt(repo, lang, scenes, seconds):
    return f"""You write short animated story-style videos (about {seconds} seconds) that introduce a trending GitHub repository.
Write ALL spoken text in {LANG_NAME[lang]}. Keep the repository name and tool names in English letters.
Use exactly {scenes} scenes. Scene 1 must be a strong hook. The last scene invites viewers to follow for more.
Each narration is 1-2 short sentences (12-20 words). Use only facts given below. Do not invent features, numbers or benchmarks.
Return ONLY valid JSON with this shape and nothing else:
{{"title": "max 70 chars", "hook": "first line", "scenes": [{{"narration": "...", "on_screen": "max 5 words", "keywords": ["a", "b"]}}],
"description": "max 300 chars plus 4 hashtags", "tags": ["five", "short", "tags", "no", "hash"]}}

FACTS
Repository: {repo['full_name']}
Link: {repo['url']}
Stars: {repo['stars']}
Main language: {repo['language']}
Description: {repo['description']}
README excerpt: {repo['readme']}
"""


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("no JSON in reply")
    return json.loads(text[a:b + 1])


def validate(data, scenes):
    sc = data.get("scenes")
    if not isinstance(sc, list) or len(sc) < 3:
        raise ValueError("too few scenes")
    clean = []
    for s in sc[:scenes]:
        n = str(s.get("narration", "")).strip()
        if not n:
            raise ValueError("empty narration")
        clean.append({"narration": n, "on_screen": str(s.get("on_screen", "")).strip()[:40],
                      "keywords": s.get("keywords", [])})
    data["scenes"] = clean
    data["title"] = str(data.get("title", "")).strip()[:90] or "New GitHub repo"
    data["description"] = str(data.get("description", "")).strip()[:400]
    data["tags"] = [str(t).strip("# ") for t in data.get("tags", [])][:8]
    return data


def _chat(prov, prompt, scenes):
    key = os.environ.get(prov["key_env"], "")
    if not key:
        raise RuntimeError(f"no {prov['key_env']} set")
    last = None
    for _ in range(2):  # retry once on bad JSON
        r = requests.post(f"{prov['base']}/chat/completions",
                          headers={"Authorization": f"Bearer {key}"},
                          json={"model": prov["model"], "temperature": 0.8,
                                "messages": [{"role": "user", "content": prompt}]},
                          timeout=120)
        r.raise_for_status()
        try:
            return validate(parse_json(r.json()["choices"][0]["message"]["content"]), scenes)
        except Exception as e:
            last = e
    raise RuntimeError(f"bad JSON twice: {last}")


def template_script(repo):
    """Last-resort script with no AI. English only."""
    name = repo["full_name"].split("/")[-1]
    desc = repo["description"] or "a new open source project"
    sc = [
        ("Have you seen this new GitHub repo yet?", "New on GitHub"),
        (f"It is called {name}, and it already has {repo['stars']:,} stars.", f"{repo['stars']:,} stars"),
        (f"In short: {desc[:140]}", "What it does"),
        (f"It is mostly written in {repo['language'] or 'several languages'}.", "Built with"),
        ("Follow for more trending repos every week.", "Follow for more"),
    ]
    return {"title": f"{name}: new GitHub repo", "hook": sc[0][0],
            "scenes": [{"narration": a, "on_screen": b, "keywords": []} for a, b in sc],
            "description": f"{desc[:200]} #github #opensource #coding #tech",
            "tags": ["github", "opensource", "coding", "tech", "programming"]}


def make_script(cfg, repo, lang):
    prompt = build_prompt(repo, lang, cfg["scenes"], cfg["seconds_target"])
    providers = [(n, (lambda p=cfg["llm"][n]: _chat(p, prompt, cfg["scenes"]))) for n in cfg["llm"]]
    try:
        name, data = first_working("script", providers)
        return name, lang, data
    except RuntimeError as e:
        log("all AI providers failed, using template script (English)", e)
        return "template", "en", template_script(repo)
