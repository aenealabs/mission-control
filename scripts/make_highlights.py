"""Cut the README's animated highlight reel (media/highlights.webp) from the full video.

Re-run after re-recording the video; adjust CLIPS if the caption times change
(they are in media/mission-control-suite-demo.vtt).

    ~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/make_highlights.py
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg

MEDIA = Path(__file__).resolve().parent.parent / "media"
# (start seconds, length): ranked problems, why ECOs come back, renewals, one inbox, help
CLIPS = [(15.6, 7), (56.6, 7), (138.9, 7), (190.4, 7.5), (223.4, 6)]


def main() -> None:
    parts = [f"[0:v]trim=start={s}:duration={d},setpts=PTS-STARTPTS,fps=8,"
             f"scale=960:-1:flags=lanczos[c{i}]" for i, (s, d) in enumerate(CLIPS)]
    graph = (";".join(parts) + ";" + "".join(f"[c{i}]" for i in range(len(CLIPS)))
             + f"concat=n={len(CLIPS)}:v=1:a=0[out]")
    out = MEDIA / "highlights.webp"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y",
                    "-i", str(MEDIA / "mission-control-suite-demo.mp4"),
                    "-filter_complex", graph, "-map", "[out]", "-c:v", "libwebp_anim",
                    "-quality", "60", "-compression_level", "6", "-loop", "0", str(out)],
                   check=True)
    print(f"Wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
