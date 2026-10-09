# Courtside — NBA fantasy dashboard

ESPN league **618015977**, team **BAJ (2)**, **2026–27** season (`2027` in ESPN's API). Static, responsive GitHub Pages dashboard with a standard-library Python collector and scheduled GitHub Actions publication.

## Features

- Current roster, ESPN injury flags and league scoring-weighted projections.
- Draft history, full-league picks and value compared with current ESPN ADP.
- Searchable available-player pool and position filters.
- Actual matchup scores and published opponent schedule.
- Relative roster grades and two transparent models: ESPN projection and 75% projection / 25% prior-season total.
- Last-updated age in hours, manual refresh and explicit refresh failure states.

## Run locally

```sh
python3 scripts/sync.py
python3 -m http.server 8080 --directory site
```

Open http://localhost:8080. No build step or third-party Python packages required.

## GitHub Pages

Create a repository and push these files to `main`. Under Settings → Pages choose **GitHub Actions**. Run **Sync ESPN and publish dashboard** in Actions. The workflow refreshes once daily at 14:07 UTC (7:07 AM Pacific daylight time / 6:07 AM Pacific standard time). GitHub scheduling and Pages deployment may be delayed; this is snapshot monitoring, not a low-latency draft feed. Clicking Refresh snapshot only reads the latest deployed data. Use Run workflow for an immediate import request.

The ESPN endpoint returned this league without cookies during setup. If authenticated access becomes required, add **ESPN_S2** and **ESPN_SWID** under Settings → Secrets and variables → Actions. Never paste cookies in code, workflow YAML, issues or browser storage. The collector reads secrets from environment variables; it never publishes raw ESPN responses, owner IDs, member profiles or cookies. The public site exposes team names, rosters, draft picks, matchup scores and projections. Snapshot JSON is ignored by Git and published only through the Pages artifact.

Optional Actions variables: `ESPN_LEAGUE_ID` (618015977), `ESPN_TEAM_ID` (2), `ESPN_SEASON` (2027). Change the season when moving to a new NBA season; ESPN uses the season-ending year. An ESPN fetch/schema failure fails the workflow and leaves the last successful deployment unchanged. Monitor Actions failures. Public repository schedules may disable after 60 days without repository activity; re-enable the workflow if needed.

## Models and limits

Only H2H points leagues with global scoring weights are supported; category leagues and position-specific overrides fail explicitly. Source-1, full-season ESPN projected stat totals are scored using the league weights. Source-0 prior-season full-season actuals provide the blend baseline. Missing projections remain null. Missing prior season falls back to projection. Team strength sums all non-IR players, including bench; it is **not** a forecast of counted team points. No daily lineup optimization, future waiver moves, probability calibration or explicit schedule/lineup-limit modeling. ESPN projected games embed ESPN availability assumptions. Relative grades: ranks 1–2 A, 3–4 B, 5–7 C, remaining D. More rostered players can inflate totals. ADP is current, not archived draft-day ADP. Read model notes in the app.

ESPN's fantasy read API is undocumented and can change. Implementation reference: https://github.com/cwendt94/espn-api. GitHub schedule documentation: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

## Validation

```sh
python3 -m unittest discover -s tests
node --check site/app.js
```
