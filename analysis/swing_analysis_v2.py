"""Swing persistence, MEDSL 2025-09-10 schema (house-results.csv, 1976-2024) + 1976-2024 presidential file.
Reads inputs READ-ONLY. Usage: python3 -I swing_analysis_v2.py HOUSE PRES CLERK_TOTALS_CSV OUT_JSON
Decisions D1-D16 in data/CLEANING_LOG.md. Redraw exclusions (REDRAWN) are analyst decisions from memory, NOT verified from data."""
import sys, csv, json, collections, statistics as st
H_PATH, P_PATH, CLERK, OUT = sys.argv[1:5]
REDRAWN = {1994: {'GA','TX','LA','FL','NC','VA'}, 2006: {'TX'}, 2014: {'VA','FL','NC'}, 2018: {'PA','NC'}}
NO_PANEL3 = {2010: '2012 maps changed (2yr panel only)', 2022: '2022 maps changed in most states'}
def read(p):
    with open(p, newline='', encoding='utf-8') as f: yield from csv.DictReader(f)
def isD(pt): return pt.startswith('democrat')
def isR(pt): return pt in ('republican', 'independent-republican')
def num(x):
    try: return float(x)
    except: return None
# ---------- House ----------
rows = collections.defaultdict(dict)   # (y,s,d) -> race_row -> row   (race_row keeps distinct write-in rows)  D15
for r in read(H_PATH):
    if r['stage'].lower() != 'gen' or r['special'].lower() == 'true': continue          # D2, D3
    rows[(int(r['year']), r['state_po'], r['district'])][(r['race_row'], r['candidate'], r['party'])] = r
D = {}; consist = collections.defaultdict(lambda: [0.0, 0.0])
for key, rs in rows.items():
    cands = collections.defaultdict(list); other = 0.0
    for r in rs.values():
        name = (r['candidate'] or '').strip().upper()
        if name in ('', 'WRITEIN', 'WRITE-IN') or name.startswith('BLANK VOTE') or r['writein'].lower() == 'true': other += num(r['candidatevotes']) or 0.0
        else: cands[name].append(r)
    d = rr = 0.0; hasD = hasR = False; ctot = 0.0
    for name, lines in cands.items():
        parties = [(l['party'] or '').lower() for l in lines]
        s_lines = sum(num(l['candidatevotes']) or 0.0 for l in lines)
        cv = [num(l['candidate_total_votes']) for l in lines if num(l['candidate_total_votes']) is not None]
        votes = max([s_lines] + cv) if any(l['fusion_ticket'].lower() == 'true' for l in lines) else s_lines   # D6/D16 fusion: use candidate_total_votes
        ctot += votes
        if any(isD(p) for p in parties): d += votes; hasD = True
        elif any(isR(p) for p in parties): rr += votes; hasR = True
    tot = ctot + other
    tv = num(next(iter(rs.values()))['totalvotes'])
    consist[key[0]][0] += tot; consist[key[0]][1] += tv or 0.0
    status = 'contested' if (hasD and hasR) else ('uncontested' if (hasD or hasR) else 'none')
    D[key] = dict(d=d, r=rr, tot=tot, status=status, placeholder=(status == 'uncontested' and tot <= 1), winner=('D' if hasD and not hasR else 'R' if hasR and not hasD else None))
# ---------- President (MIT 1976-2024) + Clerk official totals ----------
PS = collections.defaultdict(lambda: collections.defaultdict(float)); PT = collections.defaultdict(float)
for r in read(P_PATH):
    y = int(r['year']); s = r['state_po']; v = num(r['candidatevotes']) or 0.0
    k = 'D' if r['party_simplified'] == 'DEMOCRAT' else 'R' if r['party_simplified'] == 'REPUBLICAN' else 'O'
    PS[(y, s)][k] += v; PT[(y, s)] += v
def pres_margin(y, s=None):
    if s: return 100 * (PS[(y, s)]['D'] - PS[(y, s)]['R']) / PT[(y, s)]
    Dv = sum(v['D'] for (yy, _), v in PS.items() if yy == y); Rv = sum(v['R'] for (yy, _), v in PS.items() if yy == y); Tv = sum(PT[k] for k in PT if k[0] == y)
    return 100 * (Dv - Rv) / Tv
CL = {}
for r in read(CLERK): CL[(int(r['year']), r['office'].split(' (')[0])] = float(r['margin_pp'])
# ---------- treatments ----------
_mt = {}
def med_tot(y, s):
    ts = [v['tot'] for (yy, ss, _), v in D.items() if yy == y and ss == s and v['status'] == 'contested'] or [v['tot'] for (yy, _, _), v in D.items() if yy == y and v['status'] == 'contested']
    return st.median(ts)
def contrib(y, s, dist, t):
    v = D.get((y, s, dist))
    if v is None or v['status'] == 'none': return (0.0, 0.0)
    if t == 'as_recorded': return (v['d'] - v['r'], v['tot'])
    if t == 'contested_only': return (v['d'] - v['r'], v['tot']) if v['status'] == 'contested' else (0.0, 0.0)
    if t.startswith('impute'):
        sh = float(t.split('_')[1]) / 100
        if v['status'] == 'contested': return (v['d'] - v['r'], v['tot'])
        T = _mt.setdefault((y, s), med_tot(y, s)); return ((2 * sh - 1) * T * (1 if v['winner'] == 'D' else -1), T)
    raise ValueError(t)
def margin_all(y, t):
    m = tt = 0.0
    for (yy, s, dist) in D:
        if yy == y: a, b = contrib(y, s, dist, t); m += a; tt += b
    return 100 * m / tt
def margin_state(y, s, t):
    m = tt = 0.0
    for (yy, ss, dist) in D:
        if yy == y and ss == s: a, b = contrib(y, s, dist, t); m += a; tt += b
    return (100 * m / tt) if tt > 0 else None
def matched(y0, y1, y2, red, three=True):
    ys = [y0, y1] + ([y2] if three else []); sw1 = sw2 = w = 0.0; n = 0
    for (yy, s, d) in [k for k in D if k[0] == y0 and k[1] not in red]:
        vs = [D.get((y, s, d)) for y in ys]
        if any(v is None or v['status'] != 'contested' or v['tot'] < 1000 for v in vs): continue
        mg = [(v['d'] - v['r']) / v['tot'] * 100 for v in vs]; wt = sum(v['tot'] for v in vs) / len(vs)
        sw1 += wt * (mg[1] - mg[0]); sw2 += wt * (mg[2] - mg[0]) if three else 0; w += wt; n += 1
    return sw1 / w, (sw2 / w if three else None), n
def ols(x, y):
    n = len(x); mx = sum(x)/n; my = sum(y)/n; sxx = sum((a-mx)**2 for a in x); b = sum((a-mx)*(c-my) for a, c in zip(x, y)) / sxx
    return b, my - b*mx, (sum((c-(my+b*(a-mx)))**2 for a, c in zip(x, y))/(n-2))**.5
TREAT = ['as_recorded', 'contested_only', 'impute_65', 'impute_70', 'impute_80']
out = {'national_margin_by_year': {}, 'consistency_candidate_sum_vs_totalvotes': {}, 'cycles': {}}
years = sorted({k[0] for k in D})
for y in years:
    out['national_margin_by_year'][y] = {t: margin_all(y, t) for t in TREAT}
    out['consistency_candidate_sum_vs_totalvotes'][y] = consist[y][0] / consist[y][1] if consist[y][1] else None
print("national House margin (as_recorded) by year, new file:")
print("  " + "  ".join(f"{y}:{out['national_margin_by_year'][y]['as_recorded']:+.2f}" for y in years))
print("candidate-vote sum / reported totalvotes by year (1.00 = consistent):", {y: round(v, 3) for y, v in out['consistency_candidate_sum_vs_totalvotes'].items() if v and abs(v-1) > 0.01})
for y in (1992,):
    print(f"1992 check vs official Clerk total: file {out['national_margin_by_year'][1992]['as_recorded']:+.2f} vs official {CL[(1992,'US House')]:+.2f}")
def report(y, P0, P2, rows):
    print(f"\n=== cycle {y}: presidential {P0:+.2f} -> {P2:+.2f} (dP {P2-P0:+.2f}) ===")
    print(f"{'definition':26} {'S':>8} {'beta_P':>8} {'beta_H':>8}")
    for k, v in rows.items():
        if 'slope' in v: print(f"{k:26} slope {v['slope']:+.2f} intercept {v['intercept']:+.1f} resid SD {v['resid_sd']:.1f} (n={v['n_states']})")
        else: print(f"{k:26} {v['S']:+8.2f} {v['beta_P']:+8.2f} {('%+.2f' % v['beta_H']) if v.get('beta_H') is not None else '   n/a':>8}" + (f"  [{v['n_seats']} seats]" if 'n_seats' in v else ''))
for y in (1994, 2006, 2010, 2014, 2018, 2022):
    P0, P2 = pres_margin(y - 2), pres_margin(y + 2); rows_ = {}
    for t in TREAT:
        S = margin_all(y, t) - margin_all(y - 2, t); Hn = margin_all(y + 2, t) - margin_all(y - 2, t); rows_[t] = dict(S=S, beta_P=(P2 - P0) / S, beta_H=Hn / S)
    if y in NO_PANEL3:
        if y == 2010: m1, _, n = matched(y - 2, y, None, set(), three=False); rows_['matched_panel_2yr_only'] = dict(S=m1, beta_P=(P2-P0)/m1, beta_H=None, n_seats=n, note=NO_PANEL3[y])
        else: rows_['matched_panel'] = dict(note='n/a: ' + NO_PANEL3[y], S=float('nan'), beta_P=float('nan'), beta_H=None)
    else:
        m1, m2, n = matched(y - 2, y, y + 2, REDRAWN.get(y, set())); rows_['matched_panel'] = dict(S=m1, beta_P=(P2-P0)/m1, beta_H=m2/m1, n_seats=n, excluded=sorted(REDRAWN.get(y, set())))
    sts = sorted({s for (yy, s, _) in D if yy == y}); XY = {'state_xsec_as_recorded': [], 'state_xsec_impute_70': []}
    for s in sts:
        if (y - 2, s) not in PT or (y + 2, s) not in PT: continue
        for nm, t in (('state_xsec_as_recorded', 'as_recorded'), ('state_xsec_impute_70', 'impute_70')):
            a, b = margin_state(y, s, t), margin_state(y - 2, s, t)
            if a is not None and b is not None: XY[nm].append((a - b, pres_margin(y + 2, s) - pres_margin(y - 2, s)))
    for nm, arr in XY.items():
        b, a, sd = ols([p[0] for p in arr], [p[1] for p in arr]); rows_[nm] = dict(slope=b, intercept=a, resid_sd=sd, n_states=len(arr))
    out['cycles'][y] = dict(P_prev=P0, P_next=P2, measures=rows_); report(y, P0, P2, rows_)
# 1974 cycle: only national, official Clerk totals for 1972/1974; 1976 from the file; no seat data before 1976
H72, H74, P72 = CL[(1972, 'US House')], CL[(1974, 'US House')], CL[(1972, 'US President')]
H76, P76 = out['national_margin_by_year'][1976]['as_recorded'], pres_margin(1976); S = H74 - H72
out['cycles'][1974] = dict(H72=H72, H74=H74, H76=H76, P72=P72, P76=P76, S=S, beta_P=(P76 - P72) / S, beta_H=(H76 - H72) / S, H78=out['national_margin_by_year'][1978]['as_recorded'], H80=out['national_margin_by_year'][1980]['as_recorded'])
print(f"\n=== cycle 1974 (national only; Clerk official 1972/1974): S {S:+.2f}  beta_P {(P76-P72)/S:+.2f} (1972 landslide baseline artefact)  beta_H {(H76-H72)/S:+.2f}")
print(f"    lag persistence of the 1974 swing: 1976 {(H76-H72)/S:.2f}, 1978 {(out['cycles'][1974]['H78']-H72)/S:.2f}, 1980 {(out['cycles'][1974]['H80']-H72)/S:+.2f}")
out['pres_margin'] = {y: pres_margin(y) for y in sorted({k[0] for k in PT})}
json.dump(out, open(OUT, 'w'), indent=1, default=str)
