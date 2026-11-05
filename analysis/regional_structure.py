"""Empirical regional structure of state swings relative to the national swing, 12 presidential transitions 1976->2024.
Input: validated 1976-2024 presidential file (read-only). Also writes 2024 state vote totals for popular-vote weights."""
import csv, sys, json, collections, statistics as st, math, itertools
P = collections.defaultdict(lambda: collections.defaultdict(float)); T = collections.defaultdict(float)
for r in csv.DictReader(open(sys.argv[1], newline='', encoding='utf-8')):
    y = int(r['year']); s = r['state_po']; v = float(r['candidatevotes'] or 0); k = {'DEMOCRAT': 'D', 'REPUBLICAN': 'R'}.get(r['party_simplified'], 'O'); P[(y, s)][k] += v; T[(y, s)] += v
REG = {'M': "IL IN IA KS MI MN MO NE ND OH PA SD WI", 'S': "AL AR FL GA KY LA MS NC OK SC TN TX VA WV", 'W': "AK AZ CA CO HI ID MT NV NM OR UT WA WY", 'N': "CT DE ME MD MA NH NJ NY RI VT"}
REG = {k: v.split() for k, v in REG.items()}; STATES = [s for v in REG.values() for s in v]
def m(y, s): return 100 * (P[(y, s)]['D'] - P[(y, s)]['R']) / T[(y, s)]
def nat(y):
    D = sum(v['D'] for (yy, _), v in P.items() if yy == y); R = sum(v['R'] for (yy, _), v in P.items() if yy == y); Tt = sum(T[k] for k in T if k[0] == y); return 100 * (D - R) / Tt
years = [1976, 1980, 1984, 1988, 1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024]; trans = list(zip(years[:-1], years[1:]))
dev = {}; g = {k: [] for k in REG}
for a, b in trans:
    dn = nat(b) - nat(a)
    for s in STATES: dev[(a, b, s)] = (m(b, s) - m(a, s)) - dn
    for k, ss in REG.items():
        w = [T[(b, s)] for s in ss]; g[k].append(sum(dev[(a, b, s)] * wi for s, wi in zip(ss, w)) / sum(w))
def corr(x, y):
    mx, my = st.mean(x), st.mean(y); return sum((a - mx) * (c - my) for a, c in zip(x, y)) / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((c - my) ** 2 for c in y))
print("Vote-weighted regional mean deviation from the national swing, by transition (pts):")
print("transition  " + "  ".join(f"{k:>6}" for k in REG)); [print(f"{a}-{b}   " + "  ".join(f"{g[k][i]:+6.1f}" for k in REG)) for i, (a, b) in enumerate(trans)]
print("\nSD across 12 transitions of the regional mean:", {k: round(st.stdev(v), 2) for k, v in g.items()})
print("\nCorrelation of regional means across the 12 transitions (SE about 0.29 each):")
ks = list(REG); print("      " + "  ".join(f"{k:>6}" for k in ks)); [print(f"{a:>5} " + "  ".join(f"{corr(g[a], g[b]):+6.2f}" for b in ks)) for a in ks]
# average pairwise correlation of individual state deviations within and between regions
def avgc(A, B, same):
    cs = []
    for s, t in itertools.product(A, B):
        if same and s >= t: continue
        if s == t: continue
        cs.append(corr([dev[(a, b, s)] for a, b in trans], [dev[(a, b, t)] for a, b in trans]))
    return st.mean(cs), len(cs)
print("\nAverage pairwise correlation of STATE deviations (12 transitions):")
for a in ks: print(f"  within {a}: {avgc(REG[a], REG[a], True)[0]:+.2f}")
for a, b in itertools.combinations(ks, 2): print(f"  between {a}-{b}: {avgc(REG[a], REG[b], False)[0]:+.2f}")
bgS = ['AZ', 'GA', 'NV', 'NC']; bgM = ['PA', 'MI', 'WI']
print(f"  battleground Sun Belt four (AZ GA NV NC) within: {avgc(bgS, bgS, True)[0]:+.2f} | blue wall (PA MI WI) within: {avgc(bgM, bgM, True)[0]:+.2f} | blue wall vs Sun Belt: {avgc(bgM, bgS, False)[0]:+.2f}")
print(f"  GA/NC (South) vs AZ/NV (West): {avgc(['GA','NC'], ['AZ','NV'], False)[0]:+.2f} | GA-NC {corr([dev[(a,b,'GA')] for a,b in trans],[dev[(a,b,'NC')] for a,b in trans]):+.2f} | AZ-NV {corr([dev[(a,b,'AZ')] for a,b in trans],[dev[(a,b,'NV')] for a,b in trans]):+.2f}")
# state-level residual SD per transition for battleground states in recent vs older transitions
print("\nIdiosyncratic scale: SD of state deviations after removing the regional mean, by transition:")
for i, (a, b) in enumerate(trans):
    res = [dev[(a, b, s)] - g[k][i] for k, ss in REG.items() for s in ss if T[(b, s)] > 1.5e6]; print(f"  {a}-{b}: {st.stdev(res):.2f}", end=";")
print()
vt = {s: T[(2024, s)] for s in STATES + ['DC']}; tot = sum(vt.values())
json.dump({'votes_2024': vt, 'national_margin_2024': nat(2024), 'weighted_state_margin_2024': 100 * sum(vt[s] * m(2024, s) for s in vt) / tot, 'transitions': trans, 'regional_mean_dev': g}, open(sys.argv[2], 'w'), indent=1)
print("\n2024 national margin", round(nat(2024), 3), "| vote-weighted mean of state margins", round(100 * sum(vt[s] * m(2024, s) for s in vt) / tot, 3), "| total votes", int(tot))
