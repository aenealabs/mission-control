"""Cut a square (1080x1080) social clip from the suite video, for LinkedIn and similar feeds.

Each shot sits between a headline band (readable on a phone, where the app's own captions are
small) and a band with the repository link; shots crossfade. Writes
~/mission-control-suite/demo/mission-control-social.mp4.

    ~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/make_social_clip.py
"""

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "media" / "mission-control-suite-demo.mp4"
OUT = Path.home() / "mission-control-suite" / "demo" / "mission-control-social.mp4"
SIZE, VIDEO_H = 1080, 675  # the 1440x900 video scaled to the clip's width
TOP = (SIZE - VIDEO_H) // 2
FADE = 0.5
LINK = "github.com/aenealabs/mission-control"

# (start in the suite video, seconds, headline)
SHOTS = [
    (15.6, 6.5, "Listen, then rank"),
    (56.6, 7.0, "Find the cause, not just the count"),
    (138.9, 7.0, "Catch renewals before the notice window closes"),
    (190.4, 7.0, "One backlog, evidence attached"),
    (279.6, 4.5, "Code computes. The AI is checked. People decide."),
]

BAND_HTML = """<!doctype html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600&display=swap"
      rel="stylesheet">
<style>
  html, body {{ margin: 0; width: {size}px; height: {size}px; background: #005eb8;
               font-family: 'Open Sans', sans-serif; color: #fff; }}
  .top {{ height: {top}px; display: flex; flex-direction: column; justify-content: center;
          padding: 0 56px; box-sizing: border-box; }}
  .over {{ font-size: 22px; letter-spacing: 4px; font-weight: 600; opacity: .8; }}
  .head {{ font-size: {head_px}px; font-weight: 600; line-height: 1.15; margin-top: 10px; }}
  .bottom {{ position: absolute; top: {bottom_top}px; left: 0; right: 0; bottom: 0;
             display: flex; align-items: center; justify-content: center; font-size: 30px; }}
</style></head><body>
  <div class="top"><div class="over">MISSION CONTROL</div><div class="head">{head}</div></div>
  <div class="bottom">{link}</div>
</body></html>"""


def bands(work: Path) -> list[Path]:
    paths = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": SIZE, "height": SIZE})
        for i, (_, _, head) in enumerate(SHOTS):
            page.set_content(BAND_HTML.format(
                size=SIZE, top=TOP, bottom_top=TOP + VIDEO_H, link=LINK, head=head,
                head_px=46 if len(head) < 34 else 38))
            page.wait_for_load_state("networkidle")
            path = work / f"band{i}.png"
            page.screenshot(path=path)
            paths.append(path)
        browser.close()
    return paths


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="mc-social-"))
    images = bands(work)
    inputs, graph = ["-i", str(VIDEO)], []
    for i, img in enumerate(images):
        inputs += ["-loop", "1", "-i", str(img)]
    for i, (start, length, _) in enumerate(SHOTS):
        graph.append(f"[0:v]trim=start={start}:duration={length},setpts=PTS-STARTPTS,fps=30,"
                     f"scale={SIZE}:{VIDEO_H}:flags=lanczos[v{i}]")
        graph.append(f"[{i + 1}:v]trim=duration={length},setpts=PTS-STARTPTS,fps=30[b{i}]")
        graph.append(f"[b{i}][v{i}]overlay=0:{TOP},format=yuv420p[s{i}]")
    last, offset = "s0", SHOTS[0][1]
    for i in range(1, len(SHOTS)):
        offset -= FADE
        graph.append(f"[{last}][s{i}]xfade=transition=fade:duration={FADE}:offset={offset:.2f}"
                     f"[x{i}]")
        last, offset = f"x{i}", offset + SHOTS[i][1]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", *inputs,
                    "-filter_complex", ";".join(graph), "-map", f"[{last}]",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-r", "30", "-movflags", "+faststart", str(OUT)], check=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB, about {offset:.0f} s)")


if __name__ == "__main__":
    main()
