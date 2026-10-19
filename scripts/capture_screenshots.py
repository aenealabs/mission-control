"""Capture the README screenshots from a fresh copy of the whole suite.

Starts all five apps in offline demo mode with the same demo state the video uses (see
record_mission_control_suite.py), then saves one screenshot per view to docs/screenshots/.
Re-run after any UI change:

    ~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/capture_screenshots.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright  # noqa: E402
from record_mission_control_suite import APPS, HEIGHT, WIDTH, prepare, start  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"

# file name: (app, path, element to bring into view or "" for the top, action before the shot)
SHOTS = {
    "leadership-synthesis": ("Leadership Pilot", "/synthesis", "#ranking", None),
    "leadership-status": ("Leadership Pilot", "/status", "", None),
    "leadership-update": ("Leadership Pilot", "/updates/1", "", None),
    "plm-ecos": ("PLM Insight", "/ecos", "#why", None),
    "plm-duplicate": ("PLM Insight", "/issues/2", "", None),
    "support-problems": ("Support Pilot", "/problems", "", None),
    "support-problem": ("Support Pilot", "/problems/PRB-3", "", None),
    "support-ask": ("Support Pilot", "/", "", "ask"),
    "portfolio-2x2": ("App Portfolio", "/", "", None),
    "portfolio-licenses": ("App Portfolio", "/licenses", "", None),
    "portfolio-app": ("App Portfolio", "/apps/APP-04", "", None),
    "portfolio-directory": ("App Portfolio", "/directory", "", None),
    "backlog-review": ("Backlog Pilot", "/", "", "draft"),
    "backlog-inbox": ("Backlog Pilot", "/", "", None),
    "backlog-roadmap": ("Backlog Pilot", "/roadmap?product=plm-sap", "", None),
    "suite-menu": ("Backlog Pilot", "/backlog", "", "menu"),
    "help-reference": ("App Portfolio", "/help/reference", "", None),
    "dark-portfolio": ("App Portfolio", "/", "", "dark"),
}


def act(page, action: str | None) -> None:
    if action == "ask":  # a question the knowledge base answers, with its checked quotes
        page.locator("[data-question]").first.click()
        page.locator(".ask-box button[type=submit]").click()
        page.wait_for_load_state("networkidle")
        page.locator(".answer-card").scroll_into_view_if_needed()
    elif action == "draft":  # a request drafted into epics, features, and traced stories
        page.locator("[data-scenario]").first.click()
        page.locator("form[hx-post='/decompose'] button[type=submit]").click()
        page.wait_for_selector(".wsjf-editor", timeout=60_000)
        page.evaluate("() => { document.querySelector('#result').scrollIntoView({block: 'start'});"
                      " scrollBy(0, -16); }")
    elif action == "menu":
        page.locator("details.suite-menu summary").click()
    elif action == "dark":
        page.locator("#theme-toggle").click()
    page.wait_for_timeout(400)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="mc-shots-"))
    url, procs = start(work)
    try:
        prepare(url)
        post_send = url["App Portfolio"] + "/apps/APP-04"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
            context.add_cookies([{"name": c, "value": u, "url": url[n]}
                                 for n, (_, _, _, c, u) in APPS.items()])
            page = context.new_page()
            # as in the video: PartFinder decided and sent, so the inbox has all four apps
            page.goto(post_send)
            page.locator("form.decide button[type=submit]").click()
            page.locator("form[action$='/send'] button").click()
            page.wait_for_load_state("networkidle")
            for name, (app, path, target, action) in SHOTS.items():
                page.goto(url[app] + path)
                page.wait_for_load_state("networkidle")
                page.add_style_tag(content="*{transition:none!important;animation:none!important;"
                                           "caret-color:transparent!important}")
                if target:
                    page.evaluate("s => document.querySelector(s).scrollIntoView({block: 'start'})"
                                  "|| scrollBy(0, -16)", target)
                act(page, action)
                page.screenshot(path=OUT / f"{name}.png")
                if action == "dark":
                    page.locator("#theme-toggle").click()  # back to light for the next shots
                print("saved", name)
            browser.close()
        return 0
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=10)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
