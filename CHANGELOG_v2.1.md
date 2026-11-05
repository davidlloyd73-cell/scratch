# Road to 2028 Version 2.1 (5 Nov 2026)

Status: scenario analysis, not a validated forecast.

1. **Popular-vote margin** now uses actual 2024 votes cast by state as weights (was electoral votes). Affects every popular-vote figure and the National Popular Vote Compact. Checks: weighted 2024 margins -1.477 vs actual -1.47; uniform 16-pt shift gives 14.51 vs 14.51 expected; compact at 100% equals the share of simulations with a positive popular-vote margin. Effect about -0.3 pt on the median margin.
2. **Calibration** uses the six comparable presidential-margin cycles (1994, 2006, 2010, 2014, 2018, 2022): mean 0.40, SD 0.47. The Watergate House-to-House coefficient (0.78) is a separate labelled stress test and a "six cycles plus Watergate" sensitivity option. Generic Democrat v generic Republican: 73% to 68%, median D+5.6 to D+3.8 (72% with Watergate added back).
3. **Backtest** without the inconsistent observation: persistence model 4.54 pts vs 4.34 for "nothing changes" (slightly worse); 80% interval 4 of 6, 90% 6 of 6. Previously, with Watergate: 7.01 vs 7.32, 5 of 7 and 6 of 7. The apparent edge came from one 20.7-pt baseline artefact.
4. **Regional correlations**: shared South/West shock removed. Twelve presidential transitions (1976-2024) give regional-mean correlations Rust Belt-South -0.68, West-Northeast -0.59, South-West -0.31 (each SE about 0.29). Four regions with these correlations halved, new dial (0 independent, 1 full estimate). Simulated correlations match targets.

Unchanged: interface, defaults for regional size (2.5) and state noise (1.75), hypothetical effects off by default, candidate and running-mate treatment, 2026 inputs.

Evidence: `analysis/regional_structure.py`, `analysis/backtest.py`, `analysis/results/`.
