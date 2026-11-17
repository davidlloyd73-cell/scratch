import sys, csv, collections
p = sys.argv[1]
D = collections.defaultdict(list)
for r in csv.DictReader(open(p, newline='', encoding='latin-1')):
    if r['stage']=='pri' or r['special']=='TRUE': continue
    D[(int(r['year']), r['state_po'], r['district'])].append(r)
def major(r): 
    pt=(r['party'] or '').lower(); return 'D' if pt.startswith('democrat') else ('R' if pt=='republican' else None)
stats = collections.defaultdict(lambda: collections.Counter())
examples = {}
for (y,s,d), rs in D.items():
    maj = {major(r) for r in rs} - {None}
    if len(maj) == 2: stats[y]['contested'] += 1; continue
    kind = 'uncontested_' + (next(iter(maj)) if maj else 'none')
    votes = [r['candidatevotes'] for r in rs]; tv = {r['totalvotes'] for r in rs}
    recorded = any(v not in ('','NA','0') and float(v) > 1 for v in votes)
    stats[y][kind + ('_votes_recorded' if recorded else '_votes_MISSING')] += 1
    if (y, kind, recorded) not in examples: examples[(y, kind, recorded)] = [(r['state_po'], r['district'], r['candidate'], r['party'], r['candidatevotes'], r['totalvotes']) for r in rs][:3]
for y in (1976, 1994, 2006, 2010, 2014, 2018):
    print(y, dict(stats[y]))
print("\nexamples of uncontested rows with MISSING votes:")
for k, v in list(examples.items()):
    if not k[2]: print("  ", k[:2], v)
    if k[0] == 2014 and k[2]: print("   recorded example", k[:2], v)
