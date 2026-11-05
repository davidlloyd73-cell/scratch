"""Leave-one-out backtest of midterm-swing persistence under alternative definitions. Reads swing_v2_all.json produced by swing_analysis_v2.py."""
import json, sys, statistics as st, math
R = json.load(open(sys.argv[1])); C = R['cycles']
INCLUDE_1974 = (len(sys.argv) > 3 and sys.argv[3] == 'with1974')
cyc = ([1974] if INCLUDE_1974 else []) + [1994, 2006, 2010, 2014, 2018, 2022]
def series(defn):
    out = {}
    for y in cyc:
        if y == 1974:
            c = C['1974']; out[y] = dict(S=c['S'], Pp=c['P72'], Pn=c['P76'], beta=c['beta_H'], note='beta_H used (1972 landslide baseline makes beta_P uninformative)')
            continue
        c = C[str(y)]; m = c['measures'].get(defn)
        if not m or m.get('beta_P') is None or m['beta_P'] != m['beta_P']: continue
        out[y] = dict(S=m['S'], Pp=c['P_prev'], Pn=c['P_next'], beta=m['beta_P'])
    return out
T80, T90 = {5: (1.476, 2.015), 4: (1.533, 2.132), 6: (1.440, 1.943)}, None
tq = {3:(1.638,2.353),4:(1.533,2.132),5:(1.476,2.015),6:(1.440,1.943)}   # t(0.90),t(0.95) one-sided -> 80%/90% two-sided
def loo(S, rule, excl1974=False):
    ys = [y for y in S if not (excl1974 and y == 1974)]; ae = []; cov80 = cov90 = 0
    for y in ys:
        o = [S[z]['beta'] for z in ys if z != y]; n = len(o)
        m = {'zero': 0.0, 'one': 1.0}.get(rule, sum(o)/n); sd = st.stdev(o) * math.sqrt(1 + 1/n)
        pred = S[y]['Pp'] + m * S[y]['S']; err = S[y]['Pn'] - pred; ae.append(err)
        q80, q90 = tq[min(max(n-1, 3), 6)]
        cov80 += abs(err) <= q80 * sd * abs(S[y]['S']); cov90 += abs(err) <= q90 * sd * abs(S[y]['S'])
    return dict(n=len(ys), MAE=sum(abs(e) for e in ae)/len(ae), RMSE=math.sqrt(sum(e*e for e in ae)/len(ae)), cov80=f"{cov80}/{len(ys)}", cov90=f"{cov90}/{len(ys)}")
print(f"{'definition':24} {'n':>2} | {'mean beta':>9} {'sd':>5} {'median':>6} | LOO MAE: persistence  no-change  full(1.0) | cov80  cov90 | ex-1974 MAE: persist  no-change")
res = {}
for d in ('as_recorded', 'matched_panel', 'impute_70', 'impute_65', 'impute_80', 'contested_only'):
    S = series(d)
    if len(S) < 5: print(f"{d:24} only {len(S)} cycles available"); continue
    b = [v['beta'] for v in S.values()]; p, z, one = loo(S, 'pool'), loo(S, 'zero'), loo(S, 'one'); p2, z2 = loo(S, 'pool', True), loo(S, 'zero', True)
    res[d] = dict(n=len(S), mean=st.mean(b), sd=st.stdev(b), median=st.median(b), betas={y: v['beta'] for y, v in S.items()}, loo_persist=p, loo_nochange=z, loo_full=one, loo_persist_ex1974=p2, loo_nochange_ex1974=z2)
    print(f"{d:24} {len(S):>2} | {st.mean(b):9.2f} {st.stdev(b):5.2f} {st.median(b):6.2f} |          {p['MAE']:7.2f}     {z['MAE']:7.2f}   {one['MAE']:7.2f} | {p['cov80']:>5} {p['cov90']:>5} |          {p2['MAE']:7.2f}   {z2['MAE']:7.2f}")
S = series('as_recorded')
ys_=list(S); print('\nLOO detail (as_recorded):')
for y in ys_:
    o=[S[z]['beta'] for z in ys_ if z!=y]; n=len(o); m=st.mean(o); sd_=st.stdev(o)*math.sqrt(1+1/n); q80,q90=tq[min(max(n-1,3),6)]; pred=S[y]['Pp']+m*S[y]['S']; err=S[y]['Pn']-pred
    print(f"  {y}: predicted {pred:+.1f} actual {S[y]['Pn']:+.1f} error {err:+.1f} | 80% half-width {q80*sd_*abs(S[y]['S']):.1f} 90% {q90*sd_*abs(S[y]['S']):.1f} | beta_others mean {m:.2f} sd {st.stdev(o):.2f}")
print("\nas_recorded beta by cycle:", {y: round(v['beta'], 2) for y, v in S.items()})
op = [S[y]['beta'] for y in (2006, 2014, 2022)]; inc = [S[y]['beta'] for y in ((1974,) if INCLUDE_1974 else ()) + (1994, 2010, 2018)]
print(f"open-seat cycles (2006, 2014, 2022): mean {st.mean(op):.2f} sd {st.stdev(op):.2f} | president-running ({'1974, ' if INCLUDE_1974 else ''}1994, 2010, 2018): mean {st.mean(inc):.2f} sd {st.stdev(inc):.2f}")
d = st.mean(op) - st.mean(inc); se = math.sqrt(st.variance(op)/len(op) + st.variance(inc)/len(inc)); print(f"difference {d:+.2f}, SE {se:.2f}, t = {d/se:.2f} (Welch, ~df 3-4: not significant)")
# projection inputs
H24 = R['national_margin_by_year']['2024']['as_recorded']; P24 = R['pres_margin']['2024']
print(f"\n2024 baselines: House as_recorded {H24:+.2f}, presidential {P24:+.2f}")
for H26 in (12.0, 13.5, 15.0):
    S26 = H26 - H24; b = [v['beta'] for v in S.values()]
    print(f"  H26 {H26:+.1f}: S26 {S26:.1f}  -> implied 2028 presidential margin  beta=0: {P24:+.1f} | median beta {st.median(b):.2f}: {P24+st.median(b)*S26:+.1f} | mean {st.mean(b):.2f}: {P24+st.mean(b)*S26:+.1f} | open-seat mean {st.mean(op):.2f}: {P24+st.mean(op)*S26:+.1f} | president-running mean {st.mean(inc):.2f}: {P24+st.mean(inc)*S26:+.1f}")
json.dump(res, open(sys.argv[2], 'w'), indent=1)
