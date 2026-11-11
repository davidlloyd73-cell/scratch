"""Swing persistence under alternative definitions. Reads MEDSL constituency returns READ-ONLY (never writes to them).
Usage: python3 -I swing_analysis.py HOUSE_FILE PRES_FILE OUT_JSON [cycles,comma,separated]
Loader auto-detects delimiter (csv/tab) and column names (party | party_detailed | party_simplified), keeps mode=='TOTAL' if a mode column has several values.
Cleaning decisions are documented in data/CLEANING_LOG.md (D1-D9)."""
import sys, csv, json, collections, statistics as st
H_PATH, P_PATH, OUT = sys.argv[1:4]
CYCLES = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else [1994, 2006, 2010, 2014]
REDRAWN = {1994: {'GA','TX','LA','FL','NC','VA'}, 2006: {'TX'}, 2014: {'VA','FL','NC'}}   # D8: analyst decision from memory of 1996/2006/2016 redraws; NOT verified from data
def read(path):
    with open(path, newline='', encoding='latin-1') as f:
        head = f.readline(); f.seek(0)
        delim = '\t' if head.count('\t') > head.count(',') else ','
        for r in csv.DictReader(f, delimiter=delim):
            yield {k.strip('"'): v for k, v in r.items()}
def party_of(r):
    for c in ('party_detailed', 'party', 'party_simplified'):
        if r.get(c) not in (None, '', 'NA'): return r[c].lower()
    return 'na'
def isD(pt): return pt.startswith('democrat')
def isR(pt): return pt in ('republican', 'independent-republican')   # D10: MN 1992 label 'independent-republican' (bug found 2026-11-05: previously matched 'republican' only)
# ---------- House: district frame ----------
raw = collections.defaultdict(list)
modes = set()
for r in read(H_PATH):
    if r.get('stage') == 'pri' or r.get('special') in ('TRUE', 'True', 'true'): continue   # D2, D3
    raw[(int(r['year']), r['state_po'], r['district'])].append(r)
    modes.add(r.get('mode'))
keep_total = ('TOTAL' in {m.upper() for m in modes if m}) and len({m for m in modes if m}) > 1
def votes(r):
    try: return float(r['candidatevotes'])
    except: return 0.0
D = {}   # (year,state,district) -> dict(d,r,tot,status,winner)
for key, rs in raw.items():
    if keep_total: rs = [r for r in rs if (r.get('mode') or '').upper() == 'TOTAL']
    best = {}
    for r in rs:   # D4 de-duplicate versions: keep latest version of an identical candidate/party row
        k = (r.get('candidate'), r.get('party') or r.get('party_detailed'), r.get('writein'))
        if k not in best or (r.get('version') or '') > (best[k].get('version') or ''): best[k] = r
    cands = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in best.values():
        name = r['candidate'] if r.get('candidate') not in (None, '', 'NA') else '__other__' + party_of(r)
        cands[name][party_of(r)] += votes(r)
    d = rr = tot = 0.0; hasD = hasR = False
    for c in cands.values():
        ct = sum(c.values()); tot += ct
        if any(isD(q) for q in c): d += ct; hasD = True      # D5 fusion tickets credited to the candidate's major party
        elif any(isR(q) for q in c): rr += ct; hasR = True
    status = 'contested' if (hasD and hasR) else ('uncontested' if (hasD or hasR) else 'none')
    placeholder = status == 'uncontested' and tot <= 1       # D6 placeholder votes (candidatevotes=totalvotes=1 or 0)
    D[key] = dict(d=d, r=rr, tot=tot, status=status, placeholder=placeholder, winner=('D' if hasD and not hasR else 'R' if hasR and not hasD else None))
# ---------- Presidential state margins ----------
PS = collections.defaultdict(lambda: collections.defaultdict(float)); PT = collections.defaultdict(float)
for r in read(P_PATH):
    y = int(r['year']); s = r['state_po']; pt = party_of(r); v = votes(r)
    PT[(y, s)] += v; PS[(y, s)]['D' if isD(pt) else 'R' if isR(pt) else 'O'] += v
def pres_margin(y, s=None):
    if s: return 100 * (PS[(y, s)]['D'] - PS[(y, s)]['R']) / PT[(y, s)]
    D_ = sum(v['D'] for (yy, _), v in PS.items() if yy == y); R_ = sum(v['R'] for (yy, _), v in PS.items() if yy == y); T_ = sum(PT[(yy, s_)] for (yy, s_) in PT if yy == y)
    return 100 * (D_ - R_) / T_
# ---------- treatments: map a district record -> (margin_votes, total_votes) ----------
def med_tot(y, s):
    ts = [v['tot'] for (yy, ss, _), v in D.items() if yy == y and ss == s and v['status'] == 'contested']
    if not ts: ts = [v['tot'] for (yy, _, _), v in D.items() if yy == y and v['status'] == 'contested']
    return st.median(ts)
_mt = {}
def contrib(y, s, dist, treatment):
    v = D.get((y, s, dist))
    if v is None or v['status'] == 'none': return (0.0, 0.0)
    if treatment == 'as_recorded': return (v['d'] - v['r'], v['tot'])
    if treatment == 'contested_only': return (v['d'] - v['r'], v['tot']) if v['status'] == 'contested' else (0.0, 0.0)
    if treatment.startswith('impute'):
        sh = float(treatment.split('_')[1]) / 100
        if v['status'] == 'contested': return (v['d'] - v['r'], v['tot'])
        k = (y, s); _mt.setdefault(k, med_tot(y, s)); T = _mt[k]
        return ((2 * sh - 1) * T * (1 if v['winner'] == 'D' else -1), T)
    raise ValueError(treatment)
def margin_all(y, treatment, states=None):
    m = t = 0.0
    for (yy, s, dist) in D:
        if yy != y or (states is not None and s not in states): continue
        a, b = contrib(y, s, dist, treatment); m += a; t += b
    return 100 * m / t
def margin_state(y, s, treatment):
    m = t = 0.0
    for (yy, ss, dist) in D:
        if yy == y and ss == s: a, b = contrib(y, s, dist, treatment); m += a; t += b
    return (100 * m / t) if t > 0 else None
def matched(y0, y1, y2, redrawn, require3=True):
    """Seats contested (both parties, votes recorded) in every listed year, excluding redrawn states. Returns vote-weighted swing y0->y1 and y0->y2."""
    ys = [y0, y1] + ([y2] if require3 else [])
    seats = [(s, d) for (yy, s, d), v in D.items() if yy == y0 and s not in redrawn]
    sw1 = sw2 = w = 0.0; n = 0
    for s, d in seats:
        vs = [D.get((y, s, d)) for y in ys]
        if any(v is None or v['status'] != 'contested' or v['tot'] < 1000 for v in vs): continue
        mg = [(v['d'] - v['r']) / v['tot'] * 100 for v in vs]; wt = sum(v['tot'] for v in vs) / len(vs)
        sw1 += wt * (mg[1] - mg[0]); sw2 += wt * (mg[2] - mg[0]) if require3 else 0; w += wt; n += 1
    return sw1 / w, (sw2 / w if require3 else None), n
def ols(x, y):
    n = len(x); mx = sum(x)/n; my = sum(y)/n; sxx = sum((a-mx)**2 for a in x); b = sum((a-mx)*(c-my) for a, c in zip(x, y)) / sxx
    res = [c - (my + b*(a-mx)) for a, c in zip(x, y)]; return b, my - b*mx, (sum(e*e for e in res)/(n-2))**.5
TREAT = ['as_recorded', 'contested_only', 'impute_65', 'impute_70', 'impute_80']
out = {}
print(f"keep_total_mode_only={keep_total}; districts loaded={len(D)}")
for y in CYCLES:
    P0, P2 = pres_margin(y - 2), pres_margin(y + 2); dP = P2 - P0; rows = {}
    for t in TREAT:
        S = margin_all(y, t) - margin_all(y - 2, t); Hn = margin_all(y + 2, t) - margin_all(y - 2, t)
        rows[t] = dict(S=S, beta_P=dP / S, beta_H=Hn / S)
    red = REDRAWN.get(y, set())
    if y in REDRAWN and y != 2010:
        m1, m2, n = matched(y - 2, y, y + 2, red); rows['matched_panel'] = dict(S=m1, beta_P=dP / m1, beta_H=m2 / m1, n_seats=n, excluded=sorted(red))
    else:
        m1, _, n = matched(y - 2, y, None, set(), require3=False); rows['matched_panel_2yr_only'] = dict(S=m1, beta_P=dP / m1, beta_H=None, n_seats=n, note='map changed in y+2; House persistence not computable by seat')
    # state-level cross-section: does a state's House swing predict its presidential change?
    sts = sorted({s for (yy, s, _) in D if yy == y}); X = []; Y = []; Xr = []
    for s in sts:
        if (y - 2, s) not in PT or (y + 2, s) not in PT: continue
        for t, store in (('as_recorded', X), ('impute_70', Xr)):
            a, b = margin_state(y, s, t), margin_state(y - 2, s, t)
            if a is None or b is None: break
            store.append((a - b, pres_margin(y + 2, s) - pres_margin(y - 2, s)))
    for nm, arr in (('state_xsec_as_recorded', X), ('state_xsec_impute_70', Xr)):
        b, a, sd = ols([p[0] for p in arr], [p[1] for p in arr]); rows[nm] = dict(slope=b, intercept=a, resid_sd=sd, n_states=len(arr))
    out[y] = dict(P_prev=P0, P_next=P2, dP=dP, measures=rows)
    print(f"\n=== cycle {y}: presidential {P0:+.1f} -> {P2:+.1f} (dP {dP:+.1f}) ===")
    print(f"{'definition':26} {'S(midterm swing)':>17} {'beta_P=dP/S':>12} {'beta_H':>8}")
    for k, v in rows.items():
        if 'slope' in v: print(f"{k:26} slope {v['slope']:+.2f} intercept {v['intercept']:+.1f}  resid SD {v['resid_sd']:.1f}  (n={v['n_states']} states)")
        else: print(f"{k:26} {v['S']:+17.2f} {v['beta_P']:+12.2f} {('%+.2f' % v['beta_H']) if v.get('beta_H') is not None else '   n/a':>8}" + (f"   [{v['n_seats']} seats]" if 'n_seats' in v else ''))
json.dump(out, open(OUT, 'w'), indent=1)
