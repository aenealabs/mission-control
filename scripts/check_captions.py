"""Check a demo video's captions: no repeats, in order, each up long enough to read, and the
captions ending with the video.

    python check_captions.py ~/mission-control-suite/demo/mission-control-demo.mp4
"""

import re
import subprocess
import sys
from pathlib import Path

READ_BASE, READ_CHARS_PER_SEC = 1.2, 14.0


def seconds(stamp: str) -> float:
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main(video: Path) -> int:
    text = video.with_suffix(".vtt").read_text()
    cues = [(seconds(a), seconds(b), body.strip()) for a, b, body in re.findall(
        r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)\n(.+?)(?:\n\n|\Z)", text, re.S)]
    import imageio_ffmpeg
    probe = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(video)],
                           capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe).groups()
    duration = int(h) * 3600 + int(m) * 60 + float(s)
    problems = []
    seen = set()
    for i, (start, end, body) in enumerate(cues):
        need = READ_BASE + len(body) / READ_CHARS_PER_SEC
        if body in seen:
            problems.append(f"{start:6.1f}s repeats an earlier caption: {body[:50]}")
        seen.add(body)
        if i and start < cues[i - 1][1] - 0.05:
            problems.append(f"{start:6.1f}s starts before the previous caption ends")
        if end - start < need - 0.1:
            problems.append(f"{start:6.1f}s up {end - start:.1f}s, needs {need:.1f}s: {body[:50]}")
        print(f"{int(start // 60)}:{start % 60:05.2f}  {end - start:5.1f}s (needs {need:4.1f})  "
              f"{body[:70]}")
    if cues and abs(cues[-1][1] - duration) > 0.6:
        problems.append(f"captions end at {cues[-1][1]:.1f}s but the video is {duration:.1f}s")
    print(f"\n{len(cues)} captions, video {duration:.1f}s")
    print("\n".join(problems) or "No problems found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).expanduser()))
