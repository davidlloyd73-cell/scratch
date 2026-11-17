import sys, re
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
png, out = sys.argv[1], sys.argv[2]; targets = sys.argv[3:]
res, _ = RapidOCR()(png); im = Image.open(png)
hits = []
for b, t, c in res:
    s = re.sub(r'[ ,.:;]', '', t)
    for tg in targets:
        if tg in s: hits.append((tg, [(int(p[0]), int(p[1])) for p in b], t))
for h in hits: print(h)
if hits:
    xs = [p[0] for h in hits for p in h[1]]; ys = [p[1] for h in hits for p in h[1]]
    pad = 60; box = (max(0, min(xs)-pad-400), max(0, min(ys)-pad-90), min(im.width, max(xs)+pad+400), min(im.height, max(ys)+pad+90))
    print("crop", box); im.crop(box).save(out)
