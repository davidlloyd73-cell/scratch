import sys, csv, collections
p = sys.argv[1]; R = list(csv.DictReader(open(p, newline='', encoding='utf-8')))
print("rows", len(R), "| years", sorted({r['year'] for r in R}), "| states", len({r['state_po'] for r in R}), "| versions", sorted({r['version'] for r in R}))
print("party_simplified values:", collections.Counter(r['party_simplified'] for r in R).most_common())
# integrity: per state-year, sum candidatevotes vs totalvotes; duplicate keys
agg = collections.defaultdict(float); tv = collections.defaultdict(set); keys = collections.Counter(); P = collections.defaultdict(lambda: collections.defaultdict(float))
for r in R:
    k = (int(r['year']), r['state_po']); v = float(r['candidatevotes'] or 0); agg[k] += v; tv[k].add(r['totalvotes'])
    keys[(r['year'], r['state_po'], r['candidate'], r['party_detailed'], r['writein'])] += 1
    P[int(r['year'])][r['party_simplified']] += v
bad = [(k, agg[k], tv[k]) for k in agg if len(tv[k]) > 1 or abs(agg[k] - float(next(iter(tv[k])))) > 0.005 * agg[k]]
print("state-years where sum(candidatevotes) differs from totalvotes by >0.5%:", len(bad), bad[:6])
print("exact duplicate keys:", sum(1 for c in keys.values() if c > 1))
print("\nyear   D%     R%    margin   total votes   (checks vs published: 1976 +2.1, 1980 -9.7, 1984 -18.2, 1988 -7.8, 1992 +5.6, 1996 +8.5, 2000 +0.5, 2004 -2.5, 2008 +7.3, 2012 +3.9, 2016 +2.1, 2020 +4.5, 2024 -1.5)")
for y in sorted(P):
    T = sum(P[y].values()); D = P[y]['DEMOCRAT']; Rr = P[y]['REPUBLICAN']
    print(f"{y}  {100*D/T:5.1f}  {100*Rr/T:5.1f}  {100*(D-Rr)/T:+6.2f}   {T:12,.0f}")
