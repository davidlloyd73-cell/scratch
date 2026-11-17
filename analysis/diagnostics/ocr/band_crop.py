import sys, re
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
png, out = sys.argv[1], sys.argv[2]; res, _ = RapidOCR()(png); im = Image.open(png)
cands = [(sum(p[1] for p in b)/4, b[0][0], t) for b, t, c in res if re.match(r'^\s*Total', t, re.I)]
print("Total-labelled boxes (y, x, text):", [(int(y), int(x), t[:12]) for y, x, t in cands])
if cands:
    y = max(cands)[0]; im.crop((0, int(y) - 40, im.width, int(y) + 60)).save(out); print("saved band at y", int(y))
