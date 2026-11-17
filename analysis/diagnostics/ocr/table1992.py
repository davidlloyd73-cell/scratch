import re, csv, collections, sys, json
from rapidocr_onnxruntime import RapidOCR
eng = RapidOCR()
names = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
clerk = {}
for png in ('pdf_text/1992_rot_p86.png', 'pdf_text/1992_rot_p87.png'):
    res, _ = eng(png)
    boxes = [(sum(p[0] for p in b)/4, sum(p[1] for p in b)/4, t.strip()) for b, t, c in res]
    rows = []
    for x, y, t in boxes:
        clean = re.sub(r'[\s.\-_:]+$', '', t)
        for n in names:
            if clean == n or clean.startswith(n) and len(clean) <= len(n) + 3: rows.append((n, x, y))
    nums = [(x, y, int(re.sub(r'[ ,.]', '', t))) for x, y, t in boxes if re.fullmatch(r'\d{1,3}(?:[,.]\s?\d{3})+', t)]
    for n, nx, ny in rows:
        mine = sorted([(x, v) for x, y, v in nums if abs(y - ny) < 9 and x > nx + 40])
        if len(mine) >= 2 and n not in clerk: clerk[n] = (mine[0][1], mine[1][1], mine[-1][1])
print("Clerk rows reconstructed:", len(clerk), "| missing:", [n for n in names if n not in clerk])
ab = dict(AL="Alabama",AK="Alaska",AZ="Arizona",AR="Arkansas",CA="California",CO="Colorado",CT="Connecticut",DE="Delaware",FL="Florida",GA="Georgia",HI="Hawaii",ID="Idaho",IL="Illinois",IN="Indiana",IA="Iowa",KS="Kansas",KY="Kentucky",LA="Louisiana",ME="Maine",MD="Maryland",MA="Massachusetts",MI="Michigan",MN="Minnesota",MS="Mississippi",MO="Missouri",MT="Montana",NE="Nebraska",NV="Nevada",NH="New Hampshire",NJ="New Jersey",NM="New Mexico",NY="New York",NC="North Carolina",ND="North Dakota",OH="Ohio",OK="Oklahoma",OR="Oregon",PA="Pennsylvania",RI="Rhode Island",SC="South Carolina",SD="South Dakota",TN="Tennessee",TX="Texas",UT="Utah",VT="Vermont",VA="Virginia",WA="Washington",WV="West Virginia",WI="Wisconsin",WY="Wyoming")
M = collections.defaultdict(lambda: [0.0, 0.0])
for r in csv.DictReader(open(sys.argv[1], newline='', encoding='latin-1')):
    if r['year'] != '1992' or r['stage'] == 'pri': continue
    pt = (r['party'] or '').lower(); v = float(r['candidatevotes'] or 0)
    if pt.startswith('democrat'): M[ab[r['state_po']]][0] += v
    elif pt == 'republican': M[ab[r['state_po']]][1] += v
sD = sum(v[0] for v in clerk.values()); sR = sum(v[1] for v in clerk.values())
print(f"reconstructed Clerk sums: D {sD:,} R {sR:,}  (printed national: D 48,550,096 R 43,498,015)")
print(f"{'state':15} {'Clerk D':>11} {'MEDSL D':>11} {'dD':>10} | {'Clerk R':>11} {'MEDSL R':>11} {'dR':>10}")
for n in names:
    if n not in clerk: continue
    cD, cR, _ = clerk[n]; mD, mR = M[n]
    if abs(mD - cD) > 15000 or abs(mR - cR) > 15000: print(f"{n:15} {cD:11,} {mD:11,.0f} {mD-cD:+10,.0f} | {cR:11,} {mR:11,.0f} {mR-cR:+10,.0f}  <--")
json.dump({n: v[:2] for n, v in clerk.items()}, open('clerk1992_states.json', 'w'))
