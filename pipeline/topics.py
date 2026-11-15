import datetime
import os
import re

import requests

API = "https://api.github.com"


def _headers(raw=False):
    h = {"Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
         "User-Agent": "auto-video-pipeline"}
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _readme_excerpt(full_name, limit=2500):
    try:
        r = requests.get(f"{API}/repos/{full_name}/readme", headers=_headers(raw=True), timeout=30)
        if r.status_code != 200:
            return ""
        txt = r.text
        txt = re.sub(r"<[^>]+>", " ", txt)                 # html tags
        txt = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", txt)   # images
        txt = re.sub(r"\s+", " ", txt)
        return txt[:limit]
    except Exception:
        return ""


def pick_repo(used, days=14, min_stars=100):
    """Newest fast-growing repos first. GitHub has no official trending API, so we use search."""
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    q = f"created:>{since} stars:>{min_stars}"
    r = requests.get(f"{API}/search/repositories",
                     params={"q": q, "sort": "stars", "order": "desc", "per_page": 30},
                     headers=_headers(), timeout=30)
    r.raise_for_status()
    for it in r.json().get("items", []):
        if it["full_name"] in used or it.get("fork") or it.get("archived"):
            continue
        return {
            "full_name": it["full_name"],
            "url": it["html_url"],
            "stars": it["stargazers_count"],
            "language": it.get("language") or "",
            "description": it.get("description") or "",
            "forks": it.get("forks_count", 0),
            "issues": it.get("open_issues_count", 0),
            "topics": (it.get("topics") or [])[:5],
            "license": ((it.get("license") or {}).get("spdx_id") or ""),
            "created": (it.get("created_at") or "")[:10],
            "readme": _readme_excerpt(it["full_name"]),
        }
    if days < 90:
        return pick_repo(used, days * 3, max(20, min_stars // 2))
    raise RuntimeError("no unused trending repo found")


def fetch_hero(repo, out_path):
    """GitHub's own social preview picture for the repo. Returns the path, or None if unavailable."""
    try:
        r = requests.get(f"https://opengraph.githubassets.com/1/{repo['full_name']}", timeout=30)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 5000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
    except Exception:
        pass
    return None


def demo_repo():
    return {"full_name": "demo-user/awesome-demo", "url": "https://github.com/demo-user/awesome-demo",
            "stars": 12345, "language": "Python", "forks": 987, "issues": 42,
            "topics": ["ai", "automation", "tools"], "license": "MIT", "created": "2026-11-01",
            "description": "A demo repository used for offline testing.",
            "readme": "Demo repo. Does useful things for developers."}
