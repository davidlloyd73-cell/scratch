import sys, subprocess, os, glob, time
from rapidocr_onnxruntime import RapidOCR
pdf, year, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(outdir, exist_ok=True); tmp = f"/tmp/ocr_{year}"; os.makedirs(tmp, exist_ok=True)
n = int([l for l in subprocess.check_output(['pdfinfo', pdf]).decode().splitlines() if l.startswith('Pages')][0].split()[1])
eng = RapidOCR(); t0 = time.time()
for pg in range(1, n + 1):
    out = f"{outdir}/{year}_p{pg:03d}.txt"
    if os.path.exists(out): continue
    subprocess.run(['pdftoppm', '-r', '200', '-gray', '-f', str(pg), '-l', str(pg), '-png', pdf, f"{tmp}/pg"], check=True)
    img = sorted(glob.glob(f"{tmp}/pg*.png"))[-1]
    res, _ = eng(img)
    rows = []
    for box, txt, conf in (res or []):
        y = sum(p[1] for p in box) / 4; x = box[0][0]; rows.append((y, x, txt, conf))
    rows.sort(); lines = []; cur = []; last = None
    for y, x, txt, c in rows:
        if last is not None and abs(y - last) > 18: lines.append(cur); cur = []
        cur.append((x, txt)); last = y
    if cur: lines.append(cur)
    open(out, 'w').write("\n".join("   ".join(t for _, t in sorted(l)) for l in lines))
    for f in glob.glob(f"{tmp}/pg*.png"): os.remove(f)
    print(year, pg, n, f"{time.time()-t0:.0f}s", flush=True)
