# Road to 2028 Version 2.1: baseline record

- Baseline commit: `d9964474173296cd843ff19d5b7a7305235158e3` (branch `claude/dreamy-curie-4f7epy`). The page itself is unchanged since commit `0941369`.
- Page: `road-to-2028-v2.1.html`, sha256 `32b9337a0e110e9413d36520e7a97922e21548b79f2b4ca561de1743c1e934a6`
- Model `RTW2028-v2.1.0`, default seed 20281103, 4,000 simulations per matchup.
- Status: scenario analysis, not a validated forecast.
- Backtest, six comparable cycles: persistence 4.5 pts vs 4.3 for "nothing changes"; 80% interval 4 of 6, 90% 6 of 6.
- Default headline (generic Democrat v generic Republican): about 68%, median national margin D+3.8, 90% range R+7.4 to D+17.9.
- Data: MIT House release 2025-09-10 (user-supplied), MIT presidential 1976-2024, Clerk of the House totals for 1972, 1974, 1992. Checksums in `data/raw/*/SHA256SUMS.txt`.
- Intended git tag: `v2.1-baseline` at the commit above. The session could not push tags (HTTP 403), so the tag has not been published. To create it from a machine with push access:

```bash
git fetch origin claude/dreamy-curie-4f7epy
git tag -a v2.1-baseline d9964474173296cd843ff19d5b7a7305235158e3 -m "Road to 2028 Version 2.1 baseline"
git push origin v2.1-baseline
```

Later evidence updates (certified 2026 returns, polling, state-level results) are to be compared against this baseline and logged with date and source.
