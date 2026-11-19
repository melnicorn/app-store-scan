# app-store-scan

A Claude Code skill that checks an Apple-platform project against the App Review Guidelines and App Store Connect upload requirements before you submit, and keeps an HTML report with history.

## Built against

| Apple source | Version used |
|---|---|
| [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) | Last Updated October 16, 2026 |
| [Upcoming Requirements](https://developer.apple.com/news/upcoming-requirements/) | as published 2026-11-19 |
| [Submitting apps](https://developer.apple.com/app-store/submitting/) (SDK and deployment minimums) | as published 2026-11-19 |
| [Third-party SDK requirements](https://developer.apple.com/support/third-party-SDK-requirements/) | as published 2026-11-19 |
| [Required-reason API](https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api) | as published 2026-11-19 |
| [Offering account deletion](https://developer.apple.com/support/offering-account-deletion-in-your-app/) | as published 2026-11-19 |

The machine-readable record is `skills/app-store-scan/apple-sources.json`: each page's URL and content fingerprint, the guidelines' "Last Updated" date, and a fingerprint for each of the 132 numbered guideline sections. The same dates appear in `SKILL.md` and in every report footer.

## Install

The repository follows the layout the [`skills` CLI](https://github.com/vercel-labs/skills) expects (`skills/<name>/SKILL.md`):

```bash
npx skills add melnicorn/app-store-scan
```

From a local checkout:

```bash
npx skills add . --skill app-store-scan
```

Or symlink it by hand:

```bash
ln -s "$(pwd)/skills/app-store-scan" ~/.claude/skills/app-store-scan
```

The scripts need `python3` only (standard library). Fan-out to subagents is used where the agent supports it and skipped elsewhere.

## Use

```
/app-store-scan                      full scan of the current project
/app-store-scan payments accounts    rescan just those areas
/app-store-scan --full               rescan everything, even unchanged areas
```

or just ask: "is this ready for the App Store?", "rescan privacy".

## How it keeps token use down

- `scripts/detect.py` does discovery without the model: platforms, Info.plist, entitlements, privacy manifest, dependencies, about 110 grep signals with `file:line`, deterministic hints, and which areas apply.
- Guidance is split into 16 area files under `areas/`. Seven always apply; nine are loaded only when the project calls for them (accounts, payments, user-generated/AI content, kids, health, regulated, extensions, macOS, tvOS/watchOS/visionOS). Mac App Store rules are never loaded for an iOS-only app.
- Rescans load only the areas asked for. Areas whose files have not changed since their last scan are skipped.
- Full scans can fan out one subagent per area, so the main conversation only sees one-line summaries.

## What it writes

Everything goes in `<project>/.app-store-scan/`, which contains its own `.gitignore` (`*`), so it never reaches source control and your `.gitignore` is not modified.

| File | Purpose |
|---|---|
| `report.html` | The readable report: verdict, findings by area, what changed, run history |
| `findings/<area>.json` | Latest result per area, stamped with time and git state |
| `history.json` | Every run: commit, branch, uncommitted paths, areas, totals, resolved and new findings |
| `state.json`, `snapshots/` | Per-check status memory and per-area file fingerprints for change detection |
| `profile.json`, `config.json` | Latest preflight output; remembered excludes and platform override |

## Updating to a newer version of Apple's documentation

```bash
python3 tools/check-apple-sources.py
```

This fetches the live pages and compares them with the baseline. When something moved it lists which pages changed, the old and new "Last Updated" date, each guideline section that was added, removed or edited, and the area files that cite that section. It exits non-zero on drift, so it can run in CI or on a schedule.

Then:

1. Edit the cited `skills/app-store-scan/areas/*.md` checks to match the new guideline text.
2. Edit `skills/app-store-scan/scripts/requirements.json` if minimums, limits, reason codes or the listed-SDK list moved.
3. Run `python3 tools/check-apple-sources.py --update` to record the new baseline. It also syncs the dates in `requirements.json`.
4. Update the dates in the table above and in the `SKILL.md` front matter and intro, and bump `metadata.version`.

This is a static review. It cannot see App Store Connect or run the app, and it does not guarantee approval.

## License

MIT. See [LICENSE](LICENSE).
