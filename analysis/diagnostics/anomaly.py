import sys, csv, collections
hp, pp = sys.argv[1], sys.argv[2]
H = collections.defaultdict(float); best = {}
with open(hp, newline='', encoding='latin-1') as f:
    for r in csv.DictReader(f):
        if r['stage'] == 'pri': continue
        k = (r['year'], r['state_po'], r['district'], r['special'], r['runoff'], r['candidate'], r['party'], r['writein'])
        if k not in best or r['version'] > best[k]['version']: best[k] = r
for k, r in best.items():
    if r['special'] == 'TRUE': continue
    try: H[(int(r['year']), r['state_po'])] += float(r['candidatevotes'])
    except: pass
Pt = {}
with open(pp, newline='', encoding='latin-1') as f:
    for r in csv.DictReader(f): Pt[(int(r['year']), r['state_po'])] = float(r['totalvotes'])
print("House total / presidential total by state, presidential years; flagged if <0.55 or >1.12")
flag = []
for (y, s), pv in sorted(Pt.items()):
    h = H.get((y, s))
    if h is None: flag.append((y, s, 'no House data', None)); continue
    ratio = h / pv
    if ratio < 0.55 or ratio > 1.12: flag.append((y, s, round(ratio, 2), int(h)))
for x in flag: print(" ", x)
print("n flagged:", len(flag), "of", len(Pt))
# non-presidential years: year-over-year state total ratio vs previous midterm (2y... use 4y gap)
print("\nMidterm-to-midterm (4-year gap) state totals, flag ratio >1.8 or <0.55:")
for (y, s), h in sorted(H.items()):
    if y % 4 == 2 and (y - 4, s) in H and H[(y - 4, s)] > 0:
        r = h / H[(y - 4, s)]
        if r > 1.8 or r < 0.55: print(" ", y, s, round(r, 2))
print("\nAdjacent-cycle check for 2018 vs 2016 (ratio of state totals), top outliers:")
rs = sorted(((H[(2018, s)] / H[(2016, s)], s) for (y, s) in H if y == 2018 and (2016, s) in H), reverse=True)
print(" ", [(s, round(r, 2)) for r, s in rs[:5]], "...", [(s, round(r, 2)) for r, s in rs[-3:]])
