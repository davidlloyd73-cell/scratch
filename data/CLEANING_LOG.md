# Data preservation and cleaning log

## Preservation
- Original files are in `data/raw/medsl-constituency-returns-fe67c05/`, byte-identical copies, read-only, with `SHA256SUMS.txt`.
- Source: https://github.com/MEDSL/constituency-returns, commit `fe67c056502fc09ddb1ace2ff8f87c53233a744e` (2026-02-12), retrieved 2026-11-05 by read-only `git clone`.
- Nothing is edited in place. Every cleaning step below happens in memory inside `analysis/swing_analysis.py`.
- Coverage: House 1976-2018, presidential (state level) 1976-2016. It does NOT cover 1972, 1974, 2020, 2022, 2024.

## Decisions
| ID | Decision | Effect |
|----|----------|--------|
| D1 | House CSV is not UTF-8. Read as Latin-1 (lossless). | Only candidate-name accents. |
| D2 | Primary rows (`stage == pri`) excluded. | 60 rows. |
| D3 | Special elections (`special == TRUE`) excluded. | 1996: 60 rows, so 425 districts. 2006: 30 Texas rows, so 431. Filling these in moves the 2006 margin by +0.07. |
| D4 | Rows identical on year/state/district/stage/special/runoff/candidate/party/writein/mode de-duplicated, keeping the latest `version`. | Superseded rows: 2002 7, 2006 7, 2008 22, 2010 15, 2012 16, 2014 13, 2016 17. |
| D5 | Votes summed by candidate name within a district and credited to the candidate's major party (fusion tickets). | Margin changes 0.1 to 0.3 pts. |
| D6 | Placeholder uncontested seats (`candidatevotes = totalvotes = 1` or 0, mainly FL, AR, LA, OK) are kept as uncontested with unknown votes. | `as_recorded` gives them about zero weight. `impute_*` treatments replace them. |
| D7 | Margin = (D minus R) / all candidate votes, in points. | Two-party margin differs by 0.5 pt or less. |
| D8 | Matched-seat panel keys seats by (state, district number). Excluded states for mid-decade redraws are from my memory, NOT verified from the data: 1994 cycle GA,TX,LA,FL,NC,VA; 2006 TX; 2014 VA,FL,NC. 2010 cycle: 2012 maps changed, so only 2008-2010 is matched. | Panel sizes 264 to 358 seats. |
| D9 | **2018 California is NOT amended.** Raw `candidatevotes` are exactly 2x the certified totals (CA-1: 263,096 + 320,092 = 583,188 vs certified 291,594, supplied by the user). All 106 CA-2018 values are even (CA 2016: 54 of 106). Summing `totalvotes` is ruled out: it would give 1,166,376. Published margin D+10.94; halving California gives D+8.55, shown for reference only. | 2018 excluded from calibration until the V15 file is checked. |

## Added 2026-11-05 (second upload)
| ID | Decision / finding | Effect |
|----|--------------------|--------|
| D10 | **My bug, fixed:** Minnesota 1992 Republicans are labelled `independent-republican` in the MIT file; my classifier matched `republican` only. Now both match (`swing_analysis.py`, `diagnostics/medsl_final.py`). The MIT data were not defective here. | 1992 House margin +6.84 to +5.88; 1994 cycle S -12.95 to -11.99, beta_P -0.22 to -0.23, beta_H 0.49 to 0.44. 1992 R votes now within 50K (0.1%) of the official total. |
| D11 | Upload `road_to_2028_sources_PARTIAL.zip` preserved read-only in `data/raw/user-upload-2026-11-05/` with SHA256SUMS. Contents match the user's manifest hashes. | - |
| D12 | The three Clerk PDFs are 1998 bilevel scans with no text layer. OCR (RapidOCR, isolated venv) is used ONLY to locate tables. Every figure used is read visually from a cropped image of the printed totals row (`data/derived/evidence_crops/`). OCR digits are NOT trusted: it confuses 3 and 8 (e.g. Louisiana R 398,679 read as 898,679). | Official totals in `data/derived/clerk_official_national_totals.csv`. |
| D13 | Tooling bug, found and fixed: `ocr_rot.py` reused stale page images from earlier runs. It affected only discarded outputs (1972 pages 50, 51, 55 and 56 first runs, which showed a seat-count table). No retained figure depended on it. | - |
| D14 | `1976-2024-president.csv` validated: 4,822 rows, 51 jurisdictions, 13 elections, no duplicate keys, national margins match published results (2020 +4.45, 2024 -1.47). One state-year mismatch of 0.8% (2024 DC: candidate votes 328,404 vs total 325,869). | Presidential margins for all cycles to 2024 now from one file. |

## Unresolved discrepancies between sources
- 1992 House D votes: MIT 49,168,549 (fusion) or 48,921,919 (party-line only) vs official 48,550,096. Margin gap +0.68 pt after the D10 fix. Cause not identified; needs a state-by-state reconciliation.
- 1976, 1994, 1996, 2006: MIT-derived margins differ from Wikipedia-derived Clerk figures by 0.1 to 1.0 pt. Cannot be resolved without the Clerk PDFs for those years.
- 1972 presidential: party-line (-22.98) vs candidate-level (about -23.2, recalled, unverified).

## Known measurement biases (not corrected)
- Uncontested seats: recorded with unrepresentative turnout in most states and as placeholders in FL, AR, LA, OK.
- Secondary-source House margins (Wikipedia-derived) differ from MEDSL-derived margins by up to about 1 point in some years (1976: 13.6 vs 14.6; 1994: 6.8 vs 6.1; 1996: 0.07 vs 0.55).

## Pending data (uploads requested)
Harvard Dataverse V15 `1976-2024-house.tab` (user's download returned HTTP 400). Clerk PDFs for 1976, 1978, 1980, 1994, 1996 first, then 2004 to 2018, to reconcile MIT-derived margins with official totals.
