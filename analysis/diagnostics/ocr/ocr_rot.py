import sys, subprocess, os, glob
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
pdf, pg, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
import shutil; shutil.rmtree('/tmp/rot', ignore_errors=True); os.makedirs('/tmp/rot', exist_ok=True)
subprocess.run(['pdftoppm','-r','200','-gray','-f',str(pg),'-l',str(pg),'-png',pdf,'/tmp/rot/pg'],check=True)
img = Image.open(sorted(glob.glob('/tmp/rot/pg*.png'))[-1]); eng = RapidOCR(); best = None
for ang in ((int(sys.argv[4]),) if len(sys.argv) > 4 else (90, 270)):
    im = img.rotate(ang, expand=True); path = f'/tmp/rot/r{ang}.png'; im.save(path)
    res, _ = eng(path); res = res or []
    score = sum(1 for _, t, c in res if any(w in t.lower() for w in ('democrat','republican','total','state','alabama','california','texas')))
    print(f"angle {ang}: {len(res)} boxes, keyword score {score}")
    if best is None or score > best[0]: best = (score, ang, res, path)
score, ang, res, path = best; print("using angle", ang)
rows = sorted(((sum(p[1] for p in b)/4, b[0][0], t) for b, t, c in res)); lines = []; cur = []; last = None
for y, x, t in rows:
    if last is not None and abs(y-last) > 16: lines.append(cur); cur = []
    cur.append((x, t)); last = y
if cur: lines.append(cur)
open(out,'w').write("\n".join("   ".join(t for _, t in sorted(l)) for l in lines))
import shutil; shutil.copy(path, out.replace('.txt','.png'))
