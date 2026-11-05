# Evidence update log

Purpose: record every change to the evidence behind Road to 2028, so any later result can be compared with the Version 2.1 baseline and the reason for each change is on file.

## Rules
1. **Never edit the baseline.** Version 2.1 (`v2.1-baseline`, page sha256 `32b9337a...34a6`) stays as it is. An update is a new file and a new release, with the old one kept.
2. **One entry per update**, added at the top of the log below, using the template. Date and source for every figure.
3. **Label the status of each figure**: certified, reported (incomplete), poll, estimate, or assumed. Never blend them without saying so.
4. **Raw data is preserved untouched** with a checksum (`data/raw/...`) and every cleaning decision goes in `data/CLEANING_LOG.md`.
5. **Run the checks** before publishing (checklist below) and record the result.
6. **Say whether the method changed.** An evidence update changes inputs only. If the method changes, it needs its own review and a new minor version.
7. **The status line stays** unless the evidence warrants removing it: *scenario analysis, not a validated forecast*.

## Version naming
- Inputs only (new count, new poll, new state returns): `2.1.1`, `2.1.2`, ...
- Method change (new component, new calibration, new correlation structure): `2.2`, with a changelog like `CHANGELOG_v2.1.md`.
- Release title: `Road to 2028 v2.1.N: <what changed>` (for example "certified 2026 House results").

## What to look for, and where it enters the model
| New evidence | Where it enters | Notes |
|---|---|---|
| Certified 2026 House result | `h26` dial and its spread (`h26sd`) | Replace the reported D+13.5 and narrow the spread. Recompute the 2026 swing S against the same 2024 definition. |
| District-level 2026 House returns | Persistence measure | Lets the 2026 swing be measured by the matched-seat and imputed definitions as well, not just as recorded. |
| State-level 2026 returns (PA, MI, WI, AZ, GA, NV, NC) | State module | Currently 2024 margins plus modelled noise. Record whether used as evidence or only as a check. |
| Post-midterm 2028 polls | Candidate effects | Replace the single August Emerson poll. Keep sampling error in the shrinkage. |
| Presidential approval and economy | Hypothetical overlays | Only move an overlay from hypothetical to evidence-based with a documented basis. |
| Any new historical cycle | Persistence calibration and backtest | 2028 itself becomes the seventh comparable cycle after the election. |

## Checks before publishing
- [ ] New data files saved read-only, checksums recorded, cleaning decisions logged.
- [ ] Electoral votes total 538. With persistence, candidates, overlays and all noise off, the page reproduces 2024 exactly (226 Democratic electoral votes, popular margin -1.47).
- [ ] Same seed gives identical output twice.
- [ ] Vote-weighted 2024 state margins equal the national margin (within 0.01).
- [ ] With the compact at 100%, win probability equals the share of simulations with a positive popular-vote margin.
- [ ] Backtest re-run if any historical figure or cycle changed; intervals and mean errors recorded below.
- [ ] Snapshot taken: `node analysis/headline_snapshot.js NEW_PAGE.html analysis/results/headline_snapshot_vX.json` and compared with the baseline in the table below.
- [ ] Phone-width view checked; no horizontal scrolling.
- [ ] Release created on GitHub with the page checksum in the description.

## Entry template (copy to the top of the log)

```
### YYYY-MM-DD: <short title>   (version X.Y.Z)
**Changed:** <inputs only | method too (say what)>
**Evidence added**
| Item | Value | Source and date | Status (certified / reported / poll / estimate / assumed) |
|---|---|---|---|
| | | | |
**Not changed:** <what stayed the same and why>
**Effect on the standard headlines (default settings, seed 20281103, 4,000 simulations)**
| | Baseline v2.1 | This update |
|---|---|---|
| Generic Democrat v generic Republican, win | 68% | |
| Median national margin | D+3.8 | |
| Buttigieg v Vance, win | 74% | |
| Ocasio-Cortez v Vance, win | 68% | |
| Persistence mean and spread (six cycles) | 0.40, 0.47 | |
| Backtest error, model vs no change | 4.5 vs 4.3 | |
**Interpretation:** <one or two sentences, including what the update does NOT show>
**Checks:** <passed / exceptions>
**Files:** <page, snapshot, data checksums, release link>
```

## Standard headline numbers, Version 2.1 baseline
Default settings, seed 20281103, 4,000 simulations per matchup (from `analysis/results/headline_snapshot_v2.1.json`). Win probability in the page is shown rounded to 5%; these are unrounded.

| Matchup | Pooled (default) | Plus Watergate | Open-seat | President-running | No persistence |
|---|---|---|---|---|---|
| Generic D v generic R, win | 68.2% | 73.6% | 89.9% | 47.3% | 22.9% |
| Generic D v generic R, median margin | D+3.8 | D+5.6 | D+11.3 | R+0.1 | R+1.5 |
| Buttigieg v Vance, win | 73.6% | 78.0% | 92.3% | 55.3% | 41.0% |
| Ocasio-Cortez v Vance, win | 68.3% | 73.7% | 89.8% | 47.1% | 27.3% |
| Ossoff v Rubio, win | 67.0% | 72.5% | 88.9% | 45.3% | 23.7% |

## Log (newest first)

### 2026-11-05: Baseline established (version 2.1.0)
**Changed:** first baseline; no prior entry.
**Evidence:** House results 1976-2024 (MIT Election Lab release 2025-09-10, supplied by the project owner, content checked against official totals); MIT presidential returns 1976-2024; Clerk of the House official national totals for 1972, 1974 and 1992 (read from scans); 2026 House margin D+13 to 14 as reported 3 to 5 Nov 2026 (incomplete count, status: reported); Emerson College 2028 poll 16-17 Aug 2026, n=1,000 (poll); other inputs as listed in the page's audit table.
**Method:** persistence from six comparable presidential-margin cycles; vote-weighted popular vote; four correlated regions; hypothetical effects off by default.
**Validation:** six-cycle backtest, persistence model 4.5 pts vs 4.3 for "nothing changes"; 80% interval 4 of 6, 90% 6 of 6. Not validated at state or candidate level.
**Files:** `road-to-2028-v2.1.html`, `BASELINE_v2.1.md`, `CHANGELOG_v2.1.md`, release `v2.1-baseline`.
