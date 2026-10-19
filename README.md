# Mission Control

Five tools for running IT product ownership in an engineering organization (PLM, CAD data,
engineering change, engineering BOMs and the SAP integration), built on one way of working:

> **Code computes. The AI drafts and explains, and code checks everything it cites. A person
> decides. Everything is audited.**

Each tool takes one problem end to end and sits on top of the systems of record (PLM, Jira,
ServiceNow, SAP) rather than replacing them. Together they follow one problem from what
stakeholders say, through the data that explains it, to the backlog and a cited leadership
update. Built by LaVon Rutledge.

## Watch the demo (4:50)

[![Highlights: ranked problems, why engineering changes come back, renewals at risk, one backlog, and built-in help](media/highlights.webp)](media/mission-control-suite-demo.mp4)

*Highlights (34 seconds).* [**Watch the full demo**](media/mission-control-suite-demo.mp4)
(4:50, captions on screen; [captions file](media/mission-control-suite-demo.vtt)). It runs
entirely offline on fictional data, from recorded AI output.

## The apps

| App | What it does | Repo |
| --- | --- | --- |
| **Leadership Pilot** | Turns listening-tour interviews into a ranked, cited problem list and a 30-60-90 readout; computes product status by rule and drafts the weekly leadership update, checking every sentence before it can be sent. | [leadership-pilot](https://github.com/aenealabs/leadership-pilot) |
| **PLM Insight** | Finds data problems in a PLM export (duplicate parts, missing export classification, BOM errors) and shows where engineering changes wait and why they come back. | [plm-insight](https://github.com/aenealabs/plm-insight) |
| **Support Pilot** | Answers engineers' questions only from the knowledge base, with every step quoted, and turns recurring tickets into problems to fix and articles to write. | [support-pilot](https://github.com/aenealabs/support-pilot) |
| **App Portfolio** | Proposes invest, tolerate, migrate, or eliminate for each engineering app; reads contracts so no renewal notice is missed; counts legacy apps' users from Active Directory, read-only. | [app-portfolio](https://github.com/aenealabs/app-portfolio) |
| **Backlog Pilot** | The hub: turns requests (typed in, or sent from the other apps) into epics and stories traced to the stakeholder's words, WSJF-prioritized and planned onto a capacity-based roadmap. | [backlog-pilot](https://github.com/aenealabs/backlog-pilot) |

The app menu, the Help pages, and the shared look come from one package,
[mission-control-common](https://github.com/aenealabs/mission-control-common).

## A tour

### Leadership Pilot

| | |
| --- | --- |
| ![Ranked problems from the listening tour](docs/screenshots/leadership-synthesis.png) | ![Status computed by rules, with early warnings](docs/screenshots/leadership-status.png) |
| **Ranked problems.** The AI groups interview pain points into themes; code counts who raised what and computes the ranking. | **Status by rule.** Red, amber, and green come from rules over the roadmap, RAID log, and budget, never from the AI; each warning shows its numbered facts. |
| ![Weekly update with every sentence checked](docs/screenshots/leadership-update.png) | |
| **Weekly update.** Every sentence cites facts and uses only numbers found in them; a flagged sentence blocks approval. | |

### PLM Insight

| | |
| --- | --- |
| ![Why engineering changes are sent back](docs/screenshots/plm-ecos.png) | ![A duplicate merge that would change an export classification](docs/screenshots/plm-duplicate.png) |
| **Why ECOs come back.** The AI groups return comments into causes; code checks every cited ECO and quote and does the counting. | **Duplicate parts.** Rules find them; when a merge would change an export classification, only Trade Compliance can approve it. |

### Support Pilot

| | |
| --- | --- |
| ![Recurring problems and knowledge gaps](docs/screenshots/support-problems.png) | ![A problem's likely root cause, every quote checked](docs/screenshots/support-problem.png) |
| **Recurring problems.** About 1,900 tickets grouped into problems without AI, with trends and the gaps no article covers. | **Likely root cause.** Every ticket id and quote the AI cites is checked. |
| ![An answer quoted from the knowledge base](docs/screenshots/support-ask.png) | |
| **Ask.** Answers only from the knowledge base, each step quoted; when the articles do not cover it, no answer rather than a guess. | |

### App Portfolio

| | |
| --- | --- |
| ![Every engineering app on business fit and technical fit](docs/screenshots/portfolio-2x2.png) | ![Renewal notice deadlines from checked contract terms](docs/screenshots/portfolio-licenses.png) |
| **The portfolio.** A TIME proposal for each app by rule; ringed apps duplicate the PLM platform. | **Renewals.** Notice deadlines from contract terms the AI read and code checked, word for word. |
| ![PartFinder: rules propose Eliminate](docs/screenshots/portfolio-app.png) | ![Legacy apps' access groups read over LDAP](docs/screenshots/portfolio-directory.png) |
| **A decision.** The rules propose; an approver decides, and overriding needs a reason. | **Legacy apps.** Access groups read from Active Directory, read-only; only counts are stored. |

### Backlog Pilot

| | |
| --- | --- |
| ![A drafted backlog with stories traced to the stakeholder's words](docs/screenshots/backlog-review.png) | ![The inbox, with work from four apps](docs/screenshots/backlog-inbox.png) |
| **Review.** Stories traced to the stakeholder's words, quality-checked, and scored; nothing reaches the backlog until a person approves. | **One inbox.** Work arrives from the other apps with its evidence and a link back. |
| ![Roadmap computed from WSJF and capacity](docs/screenshots/backlog-roadmap.png) | |
| **Roadmap.** Computed from WSJF and quarterly capacity; every move is logged with its cause. | |

### Across the suite

| | |
| --- | --- |
| ![The Mission Control app menu](docs/screenshots/suite-menu.png) | ![A rules reference generated from the code](docs/screenshots/help-reference.png) |
| **One suite.** The app name opens a menu of every app. | **Built-in help.** Every screen has help, and the rules reference is generated from the code that runs the rules. |
| ![Dark theme](docs/screenshots/dark-portfolio.png) | |
| **Light and dark**, in Brightlayer UI styling, on desktop and phone. | |

## How the apps connect

```mermaid
flowchart LR
    LP[Leadership Pilot] -- problems from interviews, proposed personas --> BP
    PI[PLM Insight] -- data and ECO problems --> BP
    SP[Support Pilot] -- recurring problems --> BP
    AP[App Portfolio] -- retirement work --> BP
    BP[Backlog Pilot<br/>inbox, backlog, roadmap] -- roadmap, read-only --> LP
```

Every hand-off goes to Backlog Pilot's inbox, where a person drafts from it; nothing enters
the backlog directly. Each item keeps a link back to where it came from. The apps are
separate deployments, connected by two settings that are the same everywhere: the list of
apps (`MISSION_CONTROL_APPS`) and a shared suite token.

## The same rules in every app

- **Code computes.** Scores, counts, dates, thresholds, and statuses come from rules that are
  shown next to the result and documented from the code.
- **The AI is checked.** Every quote, cited record, and number it uses is checked by code;
  what fails is flagged and never silently used. When the sources do not cover a question,
  it says so.
- **People decide.** Overriding a proposed score, rating, placement, or fix, rejecting a
  draft, or dropping anything the AI drafted needs a reason. Rewording a draft keeps the AI's
  original beside it.
- **Everything is audited**, including every refused attempt and failed sign-in, with
  full-text search.
- **Starts small.** The apps read exports and APIs and write nothing to systems of record.
  Every app runs offline on fictional data from recorded AI output, and live with the Claude
  API or Claude on Microsoft Foundry, with single sign-on through Microsoft Entra ID.

## Running the suite

Each app runs on its own; see its README. To run them together, start each with the same
`MISSION_CONTROL_APPS` and suite token, for example:

```bash
MISSION_CONTROL_APPS="Backlog Pilot=http://127.0.0.1:8000, Leadership Pilot=http://127.0.0.1:8010, PLM Insight=http://127.0.0.1:8020, Support Pilot=http://127.0.0.1:8030, App Portfolio=http://127.0.0.1:8040"
```

## Screenshots and video

Both are generated from fresh copies of all five apps in offline demo mode, with the
repositories checked out side by side (`~/mission-control-suite/<repo>`):

```bash
~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/capture_screenshots.py          # docs/screenshots
~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/record_mission_control_suite.py # the video
~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/check_captions.py <video.mp4>   # caption timing
~/mission-control-suite/backlog-pilot/.venv/bin/python scripts/make_highlights.py             # README reel
```

`media/highlights.webp` is cut from the full video (see the reel's clip times in `scripts/make_highlights.py`); `media/mission-control-suite-demo-web.mp4` is a smaller copy for embedding.

## Data and branding

All people, apps, parts, contracts, tickets, and numbers are fictional. The apps use the
open-source Brightlayer UI color and theme values (BSD-3-Clause). This is an independent project, not affiliated with or endorsed by Eaton.

## License

Copyright (c) 2026 aenealabs. All rights reserved.
