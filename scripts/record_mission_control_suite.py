"""Record the Mission Control suite video: the "so what" story across all five apps.

The same approach as record_mission_control.py (whose video stays as it is): private copies of
every app in offline demo mode with fresh databases, connected with a demo token; the demo
state prepared off camera; then one problem followed across the suite, with readable captions,
smooth fades, and a visible pointer. This version adds App Portfolio (renewals and retiring
an app) and the built-in Help.

    ~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/record_mission_control_suite.py
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright  # noqa: E402
from record_demo_video import HEIGHT, OVERLAY_JS, WIDTH, Demo, free_port, write_captions  # noqa: E402
from record_mission_control import SMOOTH_JS, SmoothDemo, post  # noqa: E402

TOKEN = "mission-control-demo"

APPS = {  # name: (repo, factory, env prefix, user cookie, demo user)
    "Backlog Pilot": ("backlog-pilot", "backlog_pilot.app:create_app", "BP", "bp_user", "po"),
    "Leadership Pilot": ("leadership-pilot", "leadership_pilot.app:create_app", "LP", "lp_user",
                         "po"),
    "PLM Insight": ("plm-insight", "plm_insight.app:create_app", "PI", "pi_user", "steward"),
    "Support Pilot": ("support-pilot", "support_pilot.app:create_app", "SP", "sp_user", "lead"),
    "App Portfolio": ("app-portfolio", "app_portfolio.app:create_app", "AP", "ap_user", "po"),
}
CONTRACTS = ["ardent", "calder", "helix", "keystone-plm", "northbridge", "voltaic"]


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
        env.pop("AP_LDAP_URL", None)  # always the fictional demo directory
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


def prepare(url: dict[str, str]) -> None:
    """Off camera: the state a leader would have after a few weeks of use."""
    lp, pi, sp, ap = (url["Leadership Pilot"], url["PLM Insight"], url["Support Pilot"],
                      url["App Portfolio"])
    for path in ["/interviews/extract-all", "/interviews/accept-all", "/synthesis/run",
                 "/updates/draft", "/updates/1/approve"]:
        post(lp + path, "lp_user=po")
    post(lp + "/synthesis/1/problems/0/send", "lp_user=po")
    post(pi + "/ecos/why", "pi_user=steward")
    post(pi + "/issues/2/ai", "pi_user=steward")
    post(sp + "/problems/PRB-3/review", "sp_user=lead")
    post(sp + "/problems/PRB-3/draft", "sp_user=lead")
    post(sp + "/problems/PRB-1/send", "sp_user=lead")
    for c in CONTRACTS:  # the AI reads every contract (recorded readings), checked by code
        post(f"{ap}/contracts/{c}.md/read", "ap_user=po")
    post(ap + "/directory/sync", "ap_user=po")  # legacy apps' AD groups, read-only


def run_flow(d: Demo, url: dict[str, str]) -> None:
    page = d.page
    lp, pi, sp, bp, ap = (url["Leadership Pilot"], url["PLM Insight"], url["Support Pilot"],
                          url["Backlog Pilot"], url["App Portfolio"])

    def goto(full: str) -> None:
        d.leave()
        page.goto(full)
        d.arrive()

    # Title card, solid from the first frame on a page in the card's blue; the first app page
    # then fades in over the same blue.
    page.route(lp + "/__title", lambda route: route.fulfill(
        content_type="text/html",
        body="<html style='background:#005eb8'><head></head>"
             "<body style='margin:0;background:#005eb8;animation:none'></body></html>"))
    page.goto(lp + "/__title")
    page.evaluate("() => window.__demoCard('', [])")
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
    d.caption("Rules find duplicate parts. The AI caught what my rules missed: these two have "
              "different export classifications.", 0.5)
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
    d.show(page.locator("#draft"), 5.5)
    goto(sp + "/")
    d.click(page.locator("[data-question]").nth(5), 0.4)
    d.follow(page.locator(".ask-box button[type=submit]"), 0.5)
    d.caption("Asked something no article covers, it says so and writes the ticket, instead "
              "of guessing.", 0.5)
    d.show(page.locator(".answer-card"), 4.5)

    # 5. The money: what we pay for, and what we can retire
    goto(ap + "/licenses")
    d.caption("App Portfolio covers what we pay for. The AI reads each contract; code checks "
              "every quoted term, then works out the notice deadlines.", 0.5)
    d.show(page.locator("tr.notice-passed").first, 3)
    d.caption("One renewal's notice window already closed; three more are due this month.", 2)
    goto(ap + "/apps/APP-04")
    d.caption("PartFinder: the PLM platform already does all of it, and 118 of 880 licensed "
              "people use it. Rules propose Eliminate.", 0.5)
    d.show(page.locator(".card", has_text="Rules propose").first, 3)
    d.caption("Its licensed users come from Active Directory, read-only.", 2)
    d.caption("I decide; overriding the rules would need a reason. The retirement work goes to "
              "the same backlog.", 0.3)
    d.follow(page.locator("form.decide button[type=submit]"), 0.5)
    d.follow(page.locator("form[action$='/send'] button"), 1)

    # 6. One backlog
    goto(bp + "/")
    d.caption("Everything lands in one backlog: from interviews, ECO data, the help desk, and "
              "the portfolio, each with its evidence and a link back.", 0.5)
    d.show(page.locator(".inbox-card"), 5)

    # 7. Leadership
    goto(lp + "/status")
    d.caption("Status is computed by rules, and early warnings show the numbers behind them.",
              0.5)
    d.show(page.locator(".warnings-card"), 4)
    goto(lp + "/updates/1")
    d.caption("The weekly update says only what the data says: every number is checked "
              "against its source, and nothing is sent until I approve it.", 0.5)
    d.show(page.locator("#preview"), 5)

    # 8. It explains itself
    d.caption("Every screen explains itself, and the rules reference is generated from the code "
              "that runs the rules, so it can't drift.", 0.3)
    d.follow(page.locator("a[aria-label='Help for this page']"), 0.8)
    d.follow(page.locator(".help-nav a", has_text="Rules and settings reference"), 0.3)
    d.show(page.locator("#status-rules"), 3)

    d.clear_caption()  # the closing cards fade in over the page
    d.list_card("What does Mission Control do that I can't already do with existing tools?", [
        ("Connects the dots.", "One problem, from what people said to a cited update."),
        ("Shows its work.", "Code checks every AI claim before it is used."),
        ("Keeps people deciding.", "Overrides need a reason; every decision is recorded."),
        ("Explains itself.", "Built-in help, documented from the code."),
        ("Starts small.", "Reads exports and APIs; writes nothing to systems of record."),
    ], 8)
    # the video ends on this card
    d.swap_card("Mission Control", ["Backlog Pilot · Leadership Pilot · PLM Insight · "
                                    "Support Pilot · App Portfolio",
                                    "Built by LaVon Rutledge · Aenea Labs"], 4)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(SUITE / "demo/mission-control-suite-demo.mp4"))
    parser.add_argument("--pace", type=float, default=1.7,
                        help="<1 faster, >1 slower; 1.7 leaves room for narration")
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    work = Path(tempfile.mkdtemp(prefix="mc-suite-demo-"))
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
