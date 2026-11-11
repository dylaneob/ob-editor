#!/usr/bin/env python3
"""Does any graphic touch OB's face? (OB 10-25: "why tf are you covering my face with text"; C4395 10-28: 10 quote cards touched
his cheek when he leaned toward the text, which the 2 s OCR gate caught only twice.) Long-form check after a render:

  python3 -I overlay_touch.py WORK_DIR [--json OUT.json] [--ids M326,M615]

For every event that keeps his A-roll on screen (not assemble.is_cover), at 4 fps and 960x540: the event's render
(render/events/ID.mp4, A-roll + graphic) minus its bare A-roll (hf/assets/aroll/ID.mp4). The graphic is every pixel brightened
by 60+ luma (white text, pills, borders, photos) or darkened to half or less (boxes, plates, text-shadow cores). A quote card's
soft side shade (a gradient about a third dark where his face can be) is not counted: it is the card's approved look, and on
C4395 v2 it was all that still reached him (the text sat 150+ px clear at 4K). His face box: Apple Vision (bin/faces) on the
bare A-roll.
  FAIL  25+ graphic pixels inside his face box in any frame
  WARN  graphic pixels within 15 px (60 px at 4K) of his face box
Events whose layout moves the A-roll (study/stat cards beside him, the end card: the subtraction lights up the whole frame
in 10%+ of frames) can't be measured this way and are listed as skipped. Exit 1 on any FAIL.
Fix a quote card with face_clear.py (narrows its text block to clear his face over the whole shot).
"""
import json, os, subprocess, sys, tempfile
import numpy as np

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN); import assemble
FPS, w, h, INSIDE, NEAR = 4, 960, 540, 25, 15


def gray(p):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-vf", f"fps={FPS},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w)


def graphic(d, b):
    """The graphic's pixels from render minus bare A-roll (luma): brightened 60+, or darkened to half or less (not a soft shade)."""
    return (d > 60) | ((-d > 30) & (-d > 0.5 * b) & (b > 40))


def faces(p, n):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-vf", f"fps={FPS},scale={w}:{h}", "-q:v", "3", f"{td}/%04d.jpg"], check=True)
        js = sorted(f for f in os.listdir(td) if f.endswith(".jpg"))[:n]
        out = subprocess.run([os.path.join(BIN, "faces")] + [f"{td}/{f}" for f in js], capture_output=True, text=True).stdout.splitlines()
    boxes = []
    for ln in out:
        p_ = ln.split(" ", 1)
        boxes.append(None if len(p_) < 2 or p_[1].startswith(("none", "error")) else [int(float(v)) for v in p_[1].split("|")[0].split()])
    return boxes + [None] * (n - len(boxes))


def check(e, work):
    ev, ar = f"{work}/render/events/{e['id']}.mp4", f"{work}/hf/assets/aroll/{e['id']}.mp4"
    if not (os.path.exists(ev) and os.path.exists(ar)): return {"id": e["id"], "status": "SKIP", "why": "no event render or bare A-roll"}
    A, B = gray(ev), gray(ar); n = min(len(A), len(B)); F = faces(ar, n)
    touch, gap, moved = [], 9e9, 0
    fw = e.get("face")   # a reel that cuts back to him (10-29): only its face windows show him; the footage in between is the cover
    for i in range(n):
        if fw and not any(x <= i / FPS < y for x, y in fw): continue
        a, b = A[i].astype(np.int16), B[i].astype(np.int16); d = a - b
        if (np.abs(d) > 60).mean() > 0.25: moved += 1; continue
        m = graphic(d, b)
        if not F[i]: continue
        x0, y0, x1, y1 = F[i]; inside = int(m[max(0, y0):y1, max(0, x0):x1].sum())
        if inside >= INSIDE: touch.append([round(i / FPS, 2), inside]); gap = 0; continue
        ys, xs = np.nonzero(m)
        if len(xs): gap = min(gap, float(np.maximum(np.maximum(x0 - xs, xs - x1), np.maximum(y0 - ys, ys - y1)).clip(0).min()))
    r = {"id": e["id"], "type": e["type"], "t": e["edit_in"], "frames": n, "touch": touch, "gap": None if gap == 9e9 else gap}
    if moved > 0.1 * n and not fw: r.update(status="SKIP", why=f"layout moves the A-roll in {moved}/{n} frames")
    else: r["status"] = "FAIL" if touch else ("WARN" if r["gap"] is not None and r["gap"] < NEAR else "PASS")
    return r


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    work = a[0]; opt = lambda k: a[a.index(k) + 1] if k in a else None
    ids = set((opt("--ids") or "").split(",")) - {""}
    E = [e for e in json.load(open(f"{work}/events_resolved.json"))["events"] if not assemble.is_cover(e) and (not ids or e["id"] in ids)]
    tc = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
    R = []
    for e in E:
        r = check(e, work); R.append(r)
        if r["status"] in ("FAIL", "WARN"):
            print(f"  {r['status']} {r['id']:7s} {r['type']:11s} {tc(r['t'])} " + (f"on his face in {len(r['touch'])}/{r['frames']} frames, worst {max(x[1] for x in r['touch'])} px at +{max(r['touch'], key=lambda x: x[1])[0]}s"
                  if r["touch"] else f"{r['gap']:.0f} px from his face (at 960 wide)"), flush=True)
    if opt("--json"): json.dump(R, open(opt("--json"), "w"), indent=1)
    c = {s: sum(r["status"] == s for r in R) for s in ("PASS", "WARN", "FAIL", "SKIP")}
    print(f"overlay_touch: {len(R)} graphics on his shots: {c['PASS']} clear, {c['WARN']} within {NEAR * 4} px (4K), {c['FAIL']} on his face, {c['SKIP']} not measurable"
          + (" (" + ", ".join(f"{r['id']}: {r['why']}" for r in R if r["status"] == "SKIP")[:300] + ")" if c["SKIP"] else ""))
    sys.exit(1 if c["FAIL"] else 0)


if __name__ == "__main__":
    main()
