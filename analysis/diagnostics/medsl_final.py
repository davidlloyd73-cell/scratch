import sys, csv, collections, json
p, out = sys.argv[1], sys.argv[2]
best = {}; dup = collections.Counter(); seen = collections.Counter()
with open(p, newline='', encoding='latin-1') as f:
    for r in csv.DictReader(f):
        if r['stage'] == 'pri': continue
        k = (r['year'], r['state_po'], r['district'], r['stage'], r['special'], r['runoff'], r['candidate'], r['party'], r['writein'], r['mode'])
        seen[r['year']] += 1
        if k in best:
            dup[r['year']] += 1
            if r['version'] > best[k]['version']: best[k] = r
        else: best[k] = r
print("rows kept", len(best), "| duplicate (superseded) rows by year:", dict(sorted(dup.items())))
def isD(pt): return pt.startswith('democrat')
# organise: year -> district -> candidate -> {party: votes}
Y = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(float))))
S = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(float))))
for k, r in best.items():
    try: v = float(r['candidatevotes'])
    except: continue
    y = int(r['year']); d = (r['state_po'], r['district']); cand = r['candidate'] if r['candidate'] not in ('', 'NA') else '__other__' + (r['party'] or 'na')
    pt = (r['party'] or 'na').lower()
    (S if r['special'] == 'TRUE' else Y)[y][d][cand][pt] += v
res = {}
print("\nyear |  party-line-only: D%    R%   margin | fusion-aggregated: D%    R%   margin | districts | unc(noD/noR)")
for y in sorted(Y):
    keys = set(Y[y]) | set(S[y])
    D1 = R1 = T = D2 = R2 = 0.0; noD = noR = 0
    for d in keys:
        cands = Y[y][d] if d in Y[y] else S[y][d]
        tot = sum(sum(c.values()) for c in cands.values()); T += tot
        dl = sum(v for c in cands.values() for q, v in c.items() if isD(q)); rl = sum(v for c in cands.values() for q, v in c.items() if q == 'republican')
        D1 += dl; R1 += rl
        d2 = r2 = 0.0
        for c in cands.values():
            ct = sum(c.values())
            if any(isD(q) for q in c): d2 += ct
            elif 'republican' in c: r2 += ct
        D2 += d2; R2 += r2
        if d2 == 0: noD += 1
        if r2 == 0: noR += 1
    res[y] = dict(m_party=100*(D1-R1)/T, m_fusion=100*(D2-R2)/T, D=100*D2/T, R=100*R2/T, D_votes=D2, R_votes=R2, total=T, districts=len(keys), noD=noD, noR=noR)
    print(f"{y} |  {100*D1/T:5.1f} {100*R1/T:5.1f} {100*(D1-R1)/T:+6.2f}          |   {100*D2/T:5.1f} {100*R2/T:5.1f} {100*(D2-R2)/T:+6.2f}            |   {len(keys):3d}      |  {noD:3d}/{noR:3d}")
json.dump(res, open(out, 'w'), indent=1)
