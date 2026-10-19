"""Record the Mission Control "so what" video: one problem, followed across the suite.

Starts private copies of all four apps (offline demo mode, fresh databases, connected with a
demo token), prepares the demo state off camera, then films the story with captions and a
visible pointer. Reuses the Backlog Pilot recorder's overlay and helpers.

    ~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/record_mission_control.py
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SUITE = Path.home() / "mission-control-suite"  # the repos, side by side
sys.path.insert(0, str(SUITE / "backlog-pilot" / "scripts"))
from playwright.sync_api import sync_playwright  # noqa: E402
from record_demo_video import (  # noqa: E402
    HEIGHT,
    OVERLAY_JS,
    WIDTH,
    Demo,
    free_port,
    write_captions,
)

TOKEN = "mission-control-demo"

SMOOTH_JS = """
(() => {
  const css = `html { background: #f7f8f8; }
    body { animation: mc-in .45s ease-out both; }
    #demo-card { animation: mc-in .45s ease-out both; }
    #demo-card.mc-out { animation: mc-out .45s ease-in both; }
    @keyframes mc-in { from { opacity: 0; } to { opacity: 1; } }
    body.mc-out { animation: mc-out .4s ease-in both; }
    @keyframes mc-out { from { opacity: 1; } to { opacity: 0; } }
    #demo-card.instant { animation: none; }
    #demo-card > * { transition: opacity .45s ease; }
    #demo-card.swapping > * { opacity: 0; }
    #demo-card ul { text-align: left; font-size: 24px; line-height: 1.5; margin: 22px 0 0;
      padding-left: 28px; max-width: 1340px; }
    #demo-card li { margin: 8px 0; white-space: nowrap; }
    #demo-card li b { font-weight: 600; }
    #demo-card h1.question { font-size: 42px; max-width: 1200px; line-height: 1.25; }`;
  // inject before the first paint, or the page shows once at full opacity and then flickers
  const inject = () => {
    const s = document.createElement('style');
    s.textContent = css;
    (document.head || document.documentElement).appendChild(s);
    // arriving from the title card: fade the page in over the card's blue, not over grey
    try {
      const bg = sessionStorage.getItem('mc-bg');
      if (bg) { document.documentElement.style.background = bg;
                sessionStorage.removeItem('mc-bg'); }
    } catch (e) { /* storage unavailable */ }
  };
  if (document.documentElement) inject();
  else new MutationObserver((_, obs) => {
    if (document.documentElement) { obs.disconnect(); inject(); }
  }).observe(document, {childList: true});
  window.__demoList = (title, items) => {
    window.__demoCard(title, []);
    const card = document.getElementById('demo-card');
    card.querySelector('h1').classList.add('question');
    const ul = document.createElement('ul');
    for (const [lead, rest] of items) {
      const li = document.createElement('li');
      const b = document.createElement('b'); b.textContent = lead;
      li.append(b, document.createTextNode(' ' + rest));
      ul.appendChild(li);
    }
    card.appendChild(ul);
  };
})();
"""


READ_BASE, READ_CHARS_PER_SEC = 1.2, 14.0  # time to read a caption: 1.2 s + 14 chars/s


def read_time(text: str) -> float:
    return READ_BASE + len(text) / READ_CHARS_PER_SEC


class SmoothDemo(Demo):
    """Fades between pages, scrolls once and smoothly, and never changes a caption, a card,
    or the page before what is on screen has been up long enough to read."""

    def __init__(self, page, base: str, pace: float):
        super().__init__(page, base, pace)
        self.shown: tuple[str, float] | None = None  # (text on screen, when it appeared)

    def settle(self) -> None:
        """Wait until the caption or card on screen has been readable for long enough."""
        if self.shown:
            text, at = self.shown
            left = read_time(text) - (time.monotonic() - at)
            if left > 0:
                self.page.wait_for_timeout(left * 1000)

    def caption(self, text: str, hold: float = 3.5) -> None:
        self.settle()
        self.shown = (text, time.monotonic()) if text else None
        super().caption(text, hold)

    def show(self, target, hold: float = 0.6) -> None:
        target.wait_for(state="visible")
        distance = self.page.evaluate(
            "el => { const top = el.getBoundingClientRect().top + scrollY - innerHeight * 0.28;"
            " const d = Math.abs(top - scrollY); scrollTo({top, behavior: 'smooth'}); return d; }",
            target.element_handle())
        self.page.wait_for_timeout(min(1400, 350 + distance * 0.6))
        box = target.bounding_box()
        if box:
            self.page.evaluate("([x, y]) => window.__demoCursor(x, y)",
                               [box["x"] + min(box["width"] / 2, 60), box["y"] + box["height"] / 2])
        self.wait(hold)

    def leave(self) -> None:
        """Before any page change: let the caption be read, clear it, then fade out."""
        self.settle()
        if self.shown is not None or (self.cues and self.cues[-1][1]):
            self.page.evaluate("() => window.__demoCaption('')")
            self.mark("")
        self.shown = None
        self.page.evaluate("() => document.body.classList.add('mc-out')")
        self.page.wait_for_timeout(420)

    def clear_caption(self) -> None:
        self.settle()
        self.page.evaluate("() => window.__demoCaption('')")
        self.mark("")
        self.shown = None

    def arrive(self) -> None:
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)  # the fade-in
        self.page.evaluate("() => { document.documentElement.style.background = ''; }")

    def follow(self, target, hold: float = 0.8) -> None:
        """Click something that loads a new page: point at it, fade out, then click."""
        self.show(target, 0.5)
        box = target.bounding_box()
        if box:
            self.page.evaluate("([x, y]) => window.__demoCursor(x, y, true)",
                               [box["x"] + min(box["width"] / 2, 60),
                                box["y"] + box["height"] / 2])
        self.wait(0.3)
        self.leave()
        target.click()
        self.arrive()
        self.wait(hold)

    def card(self, title: str, lines: list[str], hold: float = 4.5,
             instant: bool = False) -> None:
        """Show a card and leave it up (the next page change or card replaces it)."""
        self.settle()
        self.page.evaluate("([t, l]) => window.__demoCard(t, l)", [title, lines])
        if instant:
            self.page.evaluate(
                "() => document.getElementById('demo-card').classList.add('instant')")
        text = " · ".join([title, *lines])
        self.mark(text)
        self.shown = (text, time.monotonic())
        self.wait(hold)

    def list_card(self, title: str, items: list[tuple[str, str]], hold: float) -> None:
        self.settle()
        self.page.evaluate("([t, i]) => window.__demoList(t, i)", [title, items])
        text = " · ".join([title, *[f"{a} {b}" for a, b in items]])
        self.mark(text)
        self.shown = (text, time.monotonic())
        self.wait(hold)

    def swap_card(self, title: str, lines: list[str], hold: float) -> None:
        """Replace the card's content in place (no page shows in between)."""
        self.settle()
        self.page.evaluate("() => document.getElementById('demo-card').classList.add('swapping')")
        self.page.wait_for_timeout(470)
        self.page.evaluate("([t, l]) => window.__demoCard(t, l)", [title, lines])
        self.page.wait_for_timeout(30)
        self.page.evaluate(
            "() => document.getElementById('demo-card').classList.remove('swapping')")
        text = " · ".join([title, *lines])
        self.mark(text)
        self.shown = (text, time.monotonic())
        self.wait(hold)
        self.settle()


APPS = {  # name: (repo, factory, env prefix, user cookie, demo user)
    "Backlog Pilot": ("backlog-pilot", "backlog_pilot.app:create_app", "BP", "bp_user", "po"),
    "Leadership Pilot": ("leadership-pilot", "leadership_pilot.app:create_app", "LP", "lp_user",
                         "po"),
    "PLM Insight": ("plm-insight", "plm_insight.app:create_app", "PI", "pi_user", "steward"),
    "Support Pilot": ("support-pilot", "support_pilot.app:create_app", "SP", "sp_user", "lead"),
}


def start(work: Path) -> tuple[dict[str, str], list[subprocess.Popen]]:
    ports = {name: free_port() for name in APPS}
    url = {name: f"http://127.0.0.1:{p}" for name, p in ports.items()}
    suite = ", ".join(f"{n}={u}" for n, u in url.items())
    procs = []
    for name, (repo, factory, pre, _, _) in APPS.items():
        env = os.environ | {
            f"{pre}_LLM_PROVIDER": "replay", f"{pre}_DB_PATH": str(work / f"{pre}.db"),
            f"{pre}_AUTH": "demo", f"{pre}_RECORD": "false", f"{pre}_SUITE_TOKEN": TOKEN,
            f"{pre}_PUBLIC_URL": url[name], "MISSION_CONTROL_APPS": suite,
            "BP_TRACKER": "mock", "BP_LEADERSHIP_URL": url["Leadership Pilot"],
            f"{pre}_BACKLOG_URL": url["Backlog Pilot"],
            f"{pre}_LEADERSHIP_URL": url["Leadership Pilot"], "LP_DELIVERY_MODE": "simulate"}
        python = SUITE / repo / ".venv" / "bin" / "python"
        procs.append(subprocess.Popen(
            [str(python), "-m", "uvicorn", factory, "--factory", "--host", "127.0.0.1",
             "--port", str(ports[name]), "--log-level", "warning"], cwd=SUITE / repo, env=env))
    for name in APPS:
        for _ in range(120):
            try:
                urllib.request.urlopen(url[name] + "/static/css/app.css", timeout=1)
                break
            except urllib.error.HTTPError:
                break  # the server answered
            except OSError:
                time.sleep(0.5)
    return url, procs


def post(url: str, cookie: str, data: str = "") -> None:
    req = urllib.request.Request(url, data=data.encode(), method="POST",
                                 headers={"Cookie": cookie,
                                          "Content-Type": "application/x-www-form-urlencoded"})
    try:
        urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:  # redirects to GET pages are fine
        if e.code >= 400:
            raise


def prepare(url: dict[str, str]) -> None:
    """Off camera: the state a leader would have after a few weeks of use."""
    lp, pi, sp = url["Leadership Pilot"], url["PLM Insight"], url["Support Pilot"]
    for path in ["/interviews/extract-all", "/interviews/accept-all", "/synthesis/run",
                 "/updates/draft", "/updates/1/approve"]:
        post(lp + path, "lp_user=po")
    post(lp + "/synthesis/1/problems/0/send", "lp_user=po")
    post(pi + "/ecos/why", "pi_user=steward")
    post(pi + "/issues/2/ai", "pi_user=steward")
    post(sp + "/problems/PRB-3/review", "sp_user=lead")
    post(sp + "/problems/PRB-3/draft", "sp_user=lead")
    post(sp + "/problems/PRB-1/send", "sp_user=lead")


def run_flow(d: Demo, url: dict[str, str]) -> None:
    page = d.page
    lp, pi, sp, bp = (url["Leadership Pilot"], url["PLM Insight"], url["Support Pilot"],
                      url["Backlog Pilot"])

    def goto(full: str) -> None:
        d.leave()
        page.goto(full)
        d.arrive()

    # Open on the title card, solid from the first frame, on a blank page in the card's blue
    # (the browser's start-up frames before it are trimmed). The first app page then fades in
    # over the same blue.
    page.route(lp + "/__title", lambda route: route.fulfill(
        content_type="text/html",
        body="<html style='background:#005eb8'><head></head>"
             "<body style='margin:0;background:#005eb8;animation:none'></body></html>"))
    page.goto(lp + "/__title")
    page.evaluate("() => window.__demoCard('', [])")  # build the card hidden, then fill it
    page.evaluate("() => document.getElementById('demo-card').classList.add('instant')")
    d.started = time.monotonic()
    d.cues.clear()
    d.card("Mission Control", ["The decision layer for IT product ownership in engineering",
                               "Your enterprise already has the systems of record.",
                               "This is what sits on top of them."], 6, instant=True)
    page.evaluate("() => sessionStorage.setItem('mc-bg', '#005eb8')")
    goto(lp + "/synthesis")

    # 1. The problem, from the people
    d.caption("Day 30: eight leadership interviews, synthesized. Code ranks the problems; "
              "every point traces to what people said.", 1)
    d.show(page.locator("#ranking table.problems tbody tr").first, 4)
    d.caption("It also shows where leaders disagree, so I resolve that before building.", 0.5)
    d.show(page.locator(".contradiction").first, 3.5)

    # 2. Evidence: why engineering change is slow
    d.caption("The top complaint: engineering change is slow. Switch apps, same suite.", 2.0)
    d.click(page.locator("details.suite-menu summary"), 1.2)
    d.follow(page.locator(".suite-app", has_text="PLM Insight"), 0.6)
    d.follow(page.locator(".nav-item", has_text="ECO analytics"), 0.2)
    d.caption("PLM Insight measures it: median 18.7 days, and 3 in 10 ECOs are sent back.", 3)
    d.caption("The AI reads 148 return comments and finds the causes. Code checks every cited "
              "ECO and quote, and does the counting.", 0.5)
    d.show(page.locator("#why .theme").first, 5)
    d.caption("The fix is a control in the process, not a reminder email. One click sends it "
              "to the backlog.", 0.3)
    d.follow(page.locator("#why .theme").first.locator(".prevent form button"), 1.5)

    # 3. Data and compliance
    goto(pi + "/issues/2")
    d.caption("Rules find duplicate parts. The AI explains, and it caught what my rules missed: "
              "these two have different export classifications.", 0.5)
    d.show(page.locator(".banner.warning").first, 4.5)
    d.caption("So merging them is now Trade Compliance's call, not the data steward's.", 3)

    # 4. Support: the same problems, from the help desk
    goto(sp + "/problems")
    d.caption("Support Pilot groups 1,900 tickets into 14 recurring problems, without AI, and "
              "shows which have no article.", 0.5)
    d.show(page.locator(".gap-card"), 4.8)
    goto(sp + "/problems/PRB-3")
    d.caption("For a gap, the AI drafts the article from how agents actually resolved it, and "
              "lists what it doesn't know.", 0.5)
    d.show(page.locator("#draft"), 8.5)
    goto(sp + "/")
    d.click(page.locator("[data-question]").nth(5), 0.4)
    d.follow(page.locator(".ask-box button[type=submit]"), 0.5)
    d.caption("Asked something no article covers, it says so and writes the ticket, instead "
              "of guessing.", 0.5)
    d.show(page.locator(".answer-card"), 4.9)

    # 5. One backlog
    goto(bp + "/")
    d.caption("Everything lands in one backlog: from the listening tour, the ECO data, and "
              "the help desk, each with its evidence and a link back.", 0.5)
    d.show(page.locator(".inbox-card"), 5)

    # 6. Leadership
    goto(lp + "/status")
    d.caption("Status is computed by rules, and early warnings show the numbers behind them.",
              0.5)
    d.show(page.locator(".warnings-card"), 4)
    goto(lp + "/updates/1")
    d.caption("The weekly update says only what the data says: every number is checked "
              "against its source, and nothing is sent until I approve it.", 0.5)
    d.show(page.locator("#preview"), 5)

    d.clear_caption()  # the closing cards fade in over the page
    d.list_card("What does Mission Control do that I can't already do with existing tools?", [
        ("Connects the dots.", "One problem, from a stakeholder's words to a cited leadership "
                               "update."),
        ("Shows its work.", "Every AI claim is checked by code, and it says \"I don't know\"."),
        ("Keeps people deciding.", "Approvals, an audit trail, export control respected."),
        ("Starts small.", "Reads exports and APIs; writes nothing to systems of record."),
    ], 9)
    # the video ends on this card
    d.swap_card("Mission Control", ["Backlog Pilot · Leadership Pilot · PLM Insight · "
                                    "Support Pilot", "Built by LaVon Rutledge · Aenea Labs"], 4)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(SUITE / "demo/mission-control-demo.mp4"))
    parser.add_argument("--pace", type=float, default=1.7,
                        help="<1 faster, >1 slower; 1.7 gives about 3 minutes for narration")
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    work = Path(tempfile.mkdtemp(prefix="mc-demo-"))
    url, procs = start(work)
    try:
        prepare(url)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                record_video_dir=str(work / "video"),
                record_video_size={"width": WIDTH, "height": HEIGHT})
            context.add_init_script(OVERLAY_JS)
            context.add_init_script(SMOOTH_JS)
            context.add_cookies([{"name": c, "value": u, "url": url[n]}
                                 for n, (_, _, _, c, u) in APPS.items()])
            page = context.new_page()
            opened = time.monotonic()  # the video starts when the page opens
            demo = SmoothDemo(page, url["Leadership Pilot"], args.pace)
            run_flow(demo, url)
            lead_in = demo.started - opened  # blank frames before the title card
            ended = time.monotonic() - demo.started
            video = page.video.path()
            context.close()
            browser.close()
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", f"{lead_in + 0.15:.3f}",
                        "-i", str(video), "-c:v", "libx264",
                        "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(out)], check=True)
        write_captions(demo.cues, ended, out.with_suffix(".vtt"))
        print(f"Wrote {out} ({ended:.0f}s) and {out.with_suffix('.vtt')}")
        return 0
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=10)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
