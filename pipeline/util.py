import os
import subprocess


def log(*a):
    print("[pipeline]", *a, flush=True)


def first_working(label, providers, *args, **kw):
    """Try each (name, function) in order; return (name, result) of the first that works."""
    errors = []
    for name, fn in providers:
        try:
            log(f"{label}: trying {name}")
            res = fn(*args, **kw)
            log(f"{label}: {name} OK")
            return name, res
        except Exception as e:  # network, rate limit, bad output
            errors.append(f"{name}: {e}")
            log(f"{label}: {name} failed -> {e}")
    raise RuntimeError(f"{label}: all providers failed -> " + " | ".join(errors))


def run(cmd, cwd=None):
    cmd = [str(c) for c in cmd]
    if cmd[0] == "ffmpeg":
        cmd.insert(1, "-hide_banner")
    log("$", " ".join(cmd)[:260])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(cmd)[:200]}\n{r.stderr[-1500:]}")
    return r


def probe_duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path])
    return float(r.stdout.strip())


def find_font(lang, bold=False):
    fam = {"bn": "Noto Sans Bengali", "hi": "Noto Sans Devanagari"}.get(lang, "Noto Sans")
    pat = f"{fam}:bold" if bold else fam
    try:
        r = subprocess.run(["fc-match", "-f", "%{file}", pat], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except FileNotFoundError:
        pass
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return p if os.path.exists(p) else None


def font_family(lang):
    return {"bn": "Noto Sans Bengali", "hi": "Noto Sans Devanagari"}.get(lang, "Noto Sans")
