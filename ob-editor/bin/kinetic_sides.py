#!/usr/bin/env python3
"""Where the subject stands in each footage piece, so kinetic reel words go on the free side (kinetic_cards.pick_layout).
For every hf/assets/broll/*.jpg, Apple Vision (bin/vision_boxes): people's full-body boxes (confidence 0.3+), else faces widened to
a body, else attention-saliency objects. The subject's horizontal extent x0-x1 and centre cx, as fractions of the width,
and every face's x0-x1 (kinetic_cards keeps the words 0.05 clear of a face: people move inside a piece).
  python3 -I kinetic_sides.py WORK        -> WORK/story/kinetic_sides.json {key: {x0, x1, cx, src}}  (cached by file mtime)"""
import json, os, subprocess, sys

W_ = sys.argv[1]; D = f"{W_}/hf/assets/broll"; OUT = f"{W_}/story/kinetic_sides.json"; VB = os.path.expanduser("~/ob-editor/bin/vision_boxes")
db = json.load(open(OUT)) if os.path.exists(OUT) else {}
keys = sorted(f[:-4] for f in os.listdir(D) if f.endswith(".jpg") and not f.startswith("._"))
todo = [k for k in keys if not (k in db and db[k].get("mtime") == os.path.getmtime(f"{D}/{k}.jpg") and db[k].get("v") == 3)]
for i in range(0, len(todo), 40):
    batch = todo[i:i + 40]
    r = subprocess.run([VB] + [f"{D}/{k}.jpg" for k in batch], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        o = json.loads(line); k = os.path.basename(o["path"])[:-4]
        boxes = [b for b in o.get("humans", []) if b[4] >= 0.3]; src = "people"
        if not boxes:
            boxes = [[max(0, f[0] - (f[1] - f[0])), min(1, f[1] + (f[1] - f[0])), 0, 1, f[4]] for f in o.get("faces", []) if f[4] >= 0.4]; src = "faces"
        if not boxes:
            boxes = [b for b in o.get("salient", []) if b[4] >= 0.3]; src = "salient"
        if boxes:
            x0 = min(b[0] for b in boxes); x1 = max(b[1] for b in boxes)
            wts = [(b[1] - b[0]) * (b[3] - b[2]) for b in boxes]
            cx = sum(w * (b[0] + b[1]) / 2 for w, b in zip(wts, boxes)) / max(sum(wts), 1e-9)
            rec = dict(x0=round(max(0, x0), 3), x1=round(min(1, x1), 3), cx=round(cx, 3), src=src)
        else:
            rec = dict(x0=None, x1=None, cx=0.5, src="none")
        rec["faces"] = [[round(f[0], 3), round(f[1], 3)] for f in o.get("faces", []) if f[4] >= 0.3]   # x0, x1 of every face
        rec["mtime"] = os.path.getmtime(f"{D}/{k}.jpg"); rec["v"] = 3; db[k] = rec
json.dump(db, open(OUT, "w"), indent=1)
print(f"{len(todo)} pieces measured, {len(keys)} in {D} -> {OUT}")
