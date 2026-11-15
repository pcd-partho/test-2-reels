import asyncio
import os
from pathlib import Path

from .util import first_working, log, probe_duration, run


async def _edge_async(text, voice, out_mp3, rate, pitch):
    import edge_tts
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    words = []
    with open(out_mp3, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"text": ch["text"], "start": ch["offset"] / 1e7, "dur": ch["duration"] / 1e7})
    if os.path.getsize(out_mp3) < 1000:
        raise RuntimeError("edge-tts returned no audio")
    return words


def _edge(text, lang, cfg, out_base):
    out = f"{out_base}.mp3"
    rate = cfg.get("voice_rate", {}).get(lang, "+0%")
    words = asyncio.run(_edge_async(text, cfg["voices"][lang], out, rate, cfg.get("voice_pitch", "+0Hz")))
    return out, words


def _gtts(text, lang, cfg, out_base):
    from gtts import gTTS
    out = f"{out_base}.mp3"
    gTTS(text=text, lang=cfg["gtts_lang"][lang]).save(out)
    return out, []


def _espeak(text, lang, cfg, out_base):
    out = f"{out_base}.wav"
    run(["espeak-ng", "-v", cfg["espeak_lang"][lang], "-s", "150", "-w", out, text])
    return out, []


def _dry(text, lang, cfg, out_base):
    out = f"{out_base}.wav"
    d = max(2.0, len(text.split()) * 0.38)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=44100", "-t", f"{d:.2f}",
         "-af", "volume=0.25", out])
    return out, []


def synthesize(text, lang, cfg, out_base, dry=False):
    """Returns (engine, wav_path, duration_seconds, words)."""
    providers = [("dry-run tone", _dry)] if dry else [("edge-tts", _edge), ("gTTS", _gtts), ("espeak-ng", _espeak)]
    name, (raw, words) = first_working("voice", [(n, (lambda f=f: f(text, lang, cfg, out_base))) for n, f in providers])
    wav = f"{out_base}_n.wav"
    # slow engines (gTTS, espeak-ng) are sped up; their word timings do not exist, so captions are estimated
    speed = cfg.get("fallback_speedup", 1.12) if name in ("gTTS", "espeak-ng") else 1.0
    af = (f"atempo={speed}," if speed != 1.0 else "") + "apad=pad_dur=0.35"
    # mono 44.1k, plus 0.35 s of silence so scenes breathe
    run(["ffmpeg", "-y", "-i", raw, "-ar", "44100", "-ac", "1", "-af", af, wav])
    return name, wav, probe_duration(wav), words
