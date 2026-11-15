import glob
import os
import random
from pathlib import Path

from .util import run

W, H, FPS = 1080, 1920, 30


def make_segment(bg, dur, out, idx):
    frames = max(1, int(dur * FPS))
    zoom = f"1+0.12*on/{frames}" if idx % 2 == 0 else f"1.12-0.12*on/{frames}"
    vf = (f"scale=1296:2304,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
          f"fade=t=in:st=0:d=0.25,format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", FPS, "-t", f"{dur:.3f}", "-i", bg, "-vf", vf,
         "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", out])


def _concat(files, out, workdir):
    lst = Path(workdir) / (Path(out).stem + "_list.txt")
    lst.write_text("".join(f"file '{Path(f).resolve()}'\n" for f in files))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])


def assemble(bgs, wavs, durs, ass_path, workdir, out_path, music_dir="assets/music"):
    workdir = Path(workdir)
    segs = []
    for i, (bg, d) in enumerate(zip(bgs, durs)):
        s = workdir / f"seg{i}.mp4"
        make_segment(bg, d, s, i)
        segs.append(s)
    video = workdir / "video.mp4"
    voice = workdir / "voice.wav"
    _concat(segs, video, workdir)
    _concat(wavs, voice, workdir)
    total = sum(durs)

    tracks = glob.glob(os.path.join(music_dir, "*.mp3")) + glob.glob(os.path.join(music_dir, "*.wav"))
    cmd = ["ffmpeg", "-y", "-i", video.resolve(), "-i", voice.resolve()]
    if tracks:
        cmd += ["-stream_loop", "-1", "-i", random.choice(tracks)]
        fc = ("[0:v]ass=captions.ass[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[vo];"
              "[2:a]volume=0.10,afade=t=in:d=1[m];[vo][m]amix=inputs=2:duration=first:dropout_transition=0[a]")
    else:
        fc = "[0:v]ass=captions.ass[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", Path(out_path).resolve()]
    # run inside workdir so the ass filter finds a simple relative file name
    run(cmd, cwd=workdir)
    return out_path
