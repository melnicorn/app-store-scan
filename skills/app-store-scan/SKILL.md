---
name: app-store-scan
description: Scan an iOS, iPadOS, macOS, tvOS, watchOS or visionOS project for App Store Review Guideline and upload-requirement problems before submission, and produce an HTML report with history. Use when the user asks whether an app is ready for the App Store, wants a pre-submission or App Review check, got a rejection and wants to find related problems, or asks to rescan one area (privacy, payments, accounts, metadata, Mac sandboxing, ...) after fixing something. Works on native Xcode, SwiftPM, React Native, Expo, Flutter, Capacitor, Electron and Tauri projects.
argument-hint: "[project-path] [area ...] [--full] [--platform ios|macos|...]"
license: MIT
compatibility: Needs python3 (standard library only). git, sips and xcodebuild are used when present.
metadata:
  version: "1.0.0"
  apple-guidelines-last-updated: "2026-10-16"
  apple-docs-checked: "2026-11-19"
---

# App Store scan

Find what App Review or App Store Connect upload validation would object to in a project, record it, and render a report.

Built against Apple's App Review Guidelines last updated **October 16, 2026**, and upload requirements checked on **2026-11-19**. The exact pages and per-section fingerprints are in `SKILL/apple-sources.json`. The scan is split into areas so that only the guidance that applies is ever loaded, and so one area can be rescanned on its own.

`SKILL` below means the directory holding this file. `STATE` means `<project>/.app-store-scan/`, a self-ignoring directory (it contains its own `.gitignore` with `*`), so nothing in it reaches source control and the project's `.gitignore` is not touched.

## Token rules

These are the point of the design. Follow them.

- Never read `STATE/profile.json`. It is large. Ask `detect.py --area` for the slice you need.
- Read an area file from `SKILL/areas/` only when you are about to scan that area. Never read them all up front.
- Signals from `detect.py` come with file and line. Open only those locations, plus what you need to confirm or dismiss a lead. Do not read the whole codebase.
- On a rescan, start from the previous findings and the changed-file list, not from zero.

## Step 1: preflight

```
python3 SKILL/scripts/detect.py <project>
```

The project path defaults to the current directory. In a monorepo, scan the repo root and pass `--exclude a,b` for directories that do not ship in the app (a web front end, a desktop helper, server code); excludes are remembered in `STATE/config.json`. `--platform` overrides detection and is also remembered.

The output lists platforms, git state, each area with `yes | maybe | no`, hint counts, when each area was last scanned and which files changed since.

## Step 2: choose areas

| Request | Areas to scan |
|---|---|
| First scan, or `--full` | every `yes` area; each `maybe` area after a quick look at its signals (Step 3 command) to decide whether it is real |
| Named areas ("rescan payments") | just those |
| "Rescan" / "check again" with no area named | areas that have a previous fail or risk, plus areas whose changed-file list is not empty |
| An area marked UNCHANGED with no previous fail, risk or manual item | skip it and say so, unless `--full` |

Area ids: `completeness`, `technical`, `permissions`, `privacy`, `metadata`, `design`, `content` (always apply); `accounts`, `payments`, `ugc`, `kids`, `health`, `regulated`, `extensions`, `macos`, `tv-watch-vision` (conditional). If the user describes something the detector cannot see ("it's a kids app", "we sell subscriptions on our site"), include the matching area regardless of the detector.

Platform handling: checks inside area files carry a tag. `[all]` always applies; `[ios]` covers iOS and iPadOS; `[mac]` applies only when macOS is a platform. Skip checks tagged for platforms the project does not target. Mac-only rules (sandbox, updaters, licensing) live in `areas/macos.md` and are never loaded for an iOS-only project.

## Step 3: scan each area

For each chosen area, one at a time:

1. `python3 SKILL/scripts/detect.py <project> --area <id>` for hints, facts and grep evidence.
2. Read `SKILL/areas/<id>.md`.
3. If `STATE/findings/<id>.json` exists, read it. It is your memory of the last scan. Re-verify each earlier `fail` and `warn` first; keep any check whose `note` records a user decision or confirmation exactly as it is unless the code contradicts it.
4. Work through the checks. Open the cited locations. A hint or signal is a lead: confirm it in the code before reporting it, and drop it when it is a false positive (a test, a comment, a desktop helper that does not ship).
5. Write `STATE/findings/<id>.json` (schema below), replacing the previous file. Finish and write one area before starting the next.

With four or more areas to scan and a subagent tool available, give each area to its own subagent in parallel. Each subagent gets: the project path, the area id, the absolute paths of `detect.py` and the area file, the findings schema section of this file, and the instruction to write the findings file and reply with one line of counts. Do not paste area guidance into the prompt, and do not have subagents return findings in their reply. This keeps the main context small.

### Judging

- `fail`: the code shows a violation, or an upload-validation error is certain. You would bet on a rejection. Severity `blocker` (upload rejected or near-certain rejection) or `high` (commonly rejected).
- `warn`: a real risk that turns on reviewer judgment or on facts not in the repo (rights held, licences, how the listing is worded). Severity `high` when rejections for it are common, otherwise `medium` or `low`.
- `manual`: cannot be decided from the project at all (App Store Connect fields, review notes, demo accounts, legal entitlements). Say exactly what to confirm and where. Use sparingly: only for items that genuinely matter for this app.
- `pass`: checked and fine. One short line; no evidence needed.
- `na`: the check does not apply to this app. Leave out checks for other platforms entirely.

If a `maybe` area turns out not to apply (the signals were incidental wording), still write its findings file with a single check `<PREFIX>-00`, status `na`, explaining why. That records the decision so later scans do not repeat the work.

Report every check in the area file as one of these, so the report shows what was covered, except where an area file tells you to fold items into one check. When a check has a part the code decides and a part only the listing decides, the code part sets the status and the listing part goes in `fix` or `note`. When a check cites several guidelines, put the one that matches the finding in `guideline`. Add extra findings the area file did not anticipate with ids like `PAY-X1`. Quote file paths relative to the project root. Never put secret values in findings.

### Findings schema

```json
{
  "area": "payments",
  "summary": "One or two sentences on the state of this area.",
  "checks": [
    {
      "id": "PAY-03",
      "guideline": "3.1.1",
      "title": "No way to restore purchases",
      "status": "fail",
      "severity": "high",
      "detail": "What is wrong and why App Review cares, in plain words.",
      "evidence": [{"file": "App/Store/Paywall.swift", "line": 88, "note": "purchase button, no restore action"}],
      "fix": "Concrete change to make.",
      "note": "Optional: user decisions, context to carry into later scans."
    }
  ]
}
```

`status` and `title` are always required. `severity` and `fix` are required for `fail` and `warn`; for `manual`, put the confirmation steps in `fix` and add `severity` only when the item could itself cause rejection. `detail` and `evidence` are allowed on any status; keep `pass` and `na` to one line. When project files are generated (XcodeGen `project.yml`, Expo `app.json`, Tuist), cite the source file, not the generated one. `guideline` is the guideline number (`5.1.1(v)`) or an upload error code (`ITMS-91053`). Backticks in text fields render as code. Do not add `scanned_at` or `git`; `report.py` stamps them.

## Step 4: record and report

```
python3 SKILL/scripts/report.py <project> --open
```

This validates the findings (fix what it rejects and rerun), stamps each rescanned area with the time and git state (commit, branch, uncommitted paths), snapshots file fingerprints for change detection, works out what was resolved, new or regressed since the previous run, appends the run to `STATE/history.json`, and renders `STATE/report.html` covering all areas, including ones not rescanned this time.

Then tell the user, briefly: the verdict, the failing items worst first with `file:line`, what changed since the last run, what must be checked by hand, and the report path. Do not paste the whole report into the chat.

## Iterating

- The user fixed something: rescan only the affected area(s). Prior results for other areas stay in the report.
- The user confirms a `manual` item ("demo account is in the review notes"): set that check to `pass` and record the confirmation with its date in `note`. Preserve it on later scans.
- The user accepts a risk or disputes a finding: keep the status honest, record their reasoning in `note`, and do not re-argue it on later scans unless the code changed.
- "What changed since the last scan?": answer from the `detect.py` overview and `STATE/history.json` (small; fine to read).

## Keeping current

`SKILL/scripts/requirements.json` holds everything time-sensitive: minimum Xcode and SDK, minimum deployment targets, metadata limits, required-reason API codes, Apple's listed-SDK list, and the dates above (`guidelines_last_updated`, `as_of`). `SKILL/apple-sources.json` records each Apple page the skill was built from, with a fingerprint per guideline section. The report footer prints both dates.

If `as_of` is more than about four months old, tell the user the guidance may have moved. The skill's repository has `tools/check-apple-sources.py`, which compares the live pages with that baseline and lists the changed guideline sections and the area files that cite them.

## Limits to state plainly

This is a static review. It cannot see App Store Connect, cannot run the app, and App Review exercises judgment. A clean scan lowers the odds of rejection; it does not guarantee approval.
