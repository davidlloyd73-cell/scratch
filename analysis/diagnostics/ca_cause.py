import sys, csv, collections
p = sys.argv[1]
rows = [r for r in csv.DictReader(open(p, newline='', encoding='latin-1')) if r['year']=='2018' and r['state_po']=='CA' and r['district']=='1']
print("RAW rows for 2018 CA-1 (no aggregation code, no filtering besides year/state/district):")
for r in rows: print("  ", {k: r[k] for k in ('candidate','party','candidatevotes','totalvotes','stage','special','unofficial','version')})
cv = sum(int(r['candidatevotes']) for r in rows); tv_vals = {r['totalvotes'] for r in rows}
print(f"\nsum(candidatevotes) over the {len(rows)} candidate rows = {cv:,}")
print(f"distinct totalvotes values in those rows = {sorted(tv_vals)}  (one value, repeated on each row)")
print(f"if totalvotes were summed across rows: {sum(int(r['totalvotes']) for r in rows):,}")
cert = 291594
print(f"certified total supplied by user = {cert:,}; sum(candidatevotes)/certified = {cv/cert:.6f}")
for r in rows: print(f"   {r['candidate']}: raw {int(r['candidatevotes']):,} -> halved {int(r['candidatevotes'])/2:,.1f}")
# parity test: are ALL 2018 CA candidatevotes even? compare other states and other years
par = collections.defaultdict(lambda: [0, 0])
for r in csv.DictReader(open(p, newline='', encoding='latin-1')):
    if r['stage'] == 'pri' or r['candidatevotes'] in ('', 'NA'): continue
    k = (r['year'], r['state_po']); v = int(float(r['candidatevotes'])); par[k][0] += 1; par[k][1] += (v % 2 == 0)
print("\nParity test: state-years where EVERY candidatevotes value is even (expected ~50% even by chance; 8+ rows):")
flag = [(k, n) for k, (n, e) in sorted(par.items()) if n >= 8 and e == n]
print("  ", flag if flag else "none")
ca = par[('2018', 'CA')]; print(f"  CA 2018: {ca[1]}/{ca[0]} even;  CA 2016: {par[('2016','CA')][1]}/{par[('2016','CA')][0]} even;  NY 2018: {par[('2018','NY')][1]}/{par[('2018','NY')][0]} even")
