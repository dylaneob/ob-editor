"""Overlay frequency of a talking-head video, frame by frame (2 fps, Apple Vision faces + text via bin/frame_obstacles).
  python3 -I freq.py VIDEO OUT.json [--fps 2]
Classes per frame: CLEAN (presenter's face, no on-screen text), TEXT (presenter's face + text/graphics beside him),
CUT (no presenter face: b-roll or a full graphic). Background text (in the same spot in >25% of frames) is ignored."""
import json, os, subprocess, sys, tempfile, collections
sys.path.insert(0, os.path.expanduser("~/ob-editor/bin")); import qc_gate as Q
V, OUT = sys.argv[1], sys.argv[2]; FPS = float(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 2.0
OBS = os.path.expanduser("~/ob-editor/bin/frame_obstacles")
rows = []
with tempfile.TemporaryDirectory() as td:
    subprocess.run(["nice", "-n", "5", "ffmpeg", "-nostdin", "-v", "error", "-i", V, "-vf", f"fps={FPS},scale=640:-2", "-q:v", "4", f"{td}/f%05d.jpg"], check=True)
    for k, f in enumerate(sorted(os.listdir(td))):
        try: d = json.loads(subprocess.run([OBS, f"{td}/{f}"], capture_output=True, text=True).stdout or "{}")
        except ValueError: d = {}
        Wd, Hd = d.get("w", 640), d.get("h", 360)
        faces = [[x / Wd, y / Hd, w / Wd, h / Hd] for x, y, w, h in d.get("faces", [])]
        texts = [[x / Wd, y / Hd, w / Wd, h / Hd, s] for x, y, w, h, s in d.get("texts", []) if Q.real_text(s)]
        rows.append({"t": round((k + 0.5) / FPS, 2), "faces": faces, "texts": texts})
# presenter track: the most common (x, y, h) bin of the biggest face
big = [max(r["faces"], key=lambda f: f[3]) for r in rows if r["faces"]]
bins = collections.Counter((round((f[0] + f[2] / 2) * 10), round((f[1] + f[3] / 2) * 10), round(f[3] * 20)) for f in big)
(cx, cy, ch), _ = bins.most_common(1)[0]; cx, cy, ch = cx / 10, cy / 10, ch / 20
def presenter(r):   # a face near his usual size (punch-ins and side shifts allowed: he may move right for a panel)
    return any(0.55 * ch <= f[3] <= 1.9 * ch and abs((f[1] + f[3] / 2) - cy) < 0.22 for f in r["faces"])
# background text: same rounded spot in >25% of frames
spots = collections.Counter((round(x * 20), round(y * 20)) for r in rows for x, y, w, h, s in r["texts"])
bg = {s for s, n in spots.items() if n > 0.25 * len(rows)}
cls = []
for r in rows:
    tx = [t for t in r["texts"] if (round(t[0] * 20), round(t[1] * 20)) not in bg]
    cls.append("CLEAN" if presenter(r) and not tx else ("TEXT" if presenter(r) else "CUT"))
n = len(cls); T = n / FPS
share = {c: round(100 * cls.count(c) / n, 1) for c in ("CLEAN", "TEXT", "CUT")}
runs = []; cur = None
for k, c in enumerate(cls):
    o = c != "CLEAN"
    if cur and cur[0] == o: cur[2] = k
    else: cur = [o, k, k]; runs.append(cur)
# merge overlay gaps of one frame (a blink of clean between two overlays is one overlay moment)
ov = [(a, b) for o, a, b in runs if o]; cl = [(a, b) for o, a, b in runs if not o]
ovd = sorted((b - a + 1) / FPS for a, b in ov); cld = sorted((b - a + 1) / FPS for a, b in cl)
med = lambda L: L[len(L) // 2] if L else 0
res = {"video": V, "seconds": T, "presenter": [cx, cy, ch], "share_pct": share, "overlays": len(ov), "per_min": round(len(ov) / (T / 60), 2),
       "overlay_median_s": med(ovd), "overlay_mean_s": round(sum(ovd) / max(1, len(ovd)), 2), "clean_median_s": med(cld),
       "clean_mean_s": round(sum(cld) / max(1, len(cld)), 2), "cut_runs": sum(1 for o, a, b in runs if o and all(cls[i] == "CUT" for i in range(a, b + 1))),
       "longest_clean_s": max(cld) if cld else 0, "bg_text_spots": len(bg)}
json.dump({"summary": res, "cls": cls, "rows": rows}, open(OUT, "w"))
print(json.dumps(res))
