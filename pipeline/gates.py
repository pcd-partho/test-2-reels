import json
import re

from .util import run


def check(path, lo=15, hi=90):
    """Return a list of problems. Empty list means the video passed."""
    problems = []
    info = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration,size",
                           "-of", "json", path]).stdout)
    streams = info.get("streams", [])
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    if not (lo <= dur <= hi):
        problems.append(f"duration {dur:.0f}s outside {lo}-{hi}s")
    if not any(s.get("codec_type") == "audio" for s in streams):
        problems.append("no audio track")
    vids = [s for s in streams if s.get("codec_type") == "video"]
    if not vids or (vids[0].get("width"), vids[0].get("height")) != (1080, 1920):
        problems.append("wrong resolution")
    if size_mb > 45:
        problems.append(f"file too big for Telegram ({size_mb:.0f} MB)")
    vol = run(["ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"]).stderr
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", vol)
    if not m or float(m.group(1)) < -40:
        problems.append("audio too quiet or silent")
    blk = run(["ffmpeg", "-i", path, "-vf", "blackdetect=d=1:pix_th=0.10", "-an", "-f", "null", "-"]).stderr
    if "black_start" in blk:
        problems.append("black frames longer than 1s")
    return problems
