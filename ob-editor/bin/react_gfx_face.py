#!/usr/bin/env python3
"""Every graphic of a reaction render against his face, frame by frame (C4407, 11-03).

  python3 -I react_gfx_face.py WORK OUT.mp4 [--fps 4] [--only G10,G32]

The gate reads one frame every 2 s on a long-form file, so a graphic that touches his face for a second between two samples
can pass it. This reads every graphic's own span at 4 fps (Apple Vision faces + text via bin/frame_obstacles) and applies the
gate's text-on-face rule (qc_gate: the same overlap test, junk filter and ear rule). C4407's first full render had tag icons on
his ear at 3:59 and 8:51 while he leaned right; react_prep now measures his face over each whole event (face_x0/face_x1).
Text closer than NEAR px to his face box at its height is a NEAR (his ear and cap stick out past the box).
Only the graphic's own words count (11-03, C4407 render 3): OCR reads his ear and hair as letters ('T riA&', 'II', ')') and
glues them to the line beside him, which made 1 false FAIL and 18 false NEARs. A reading must share a word with the event's
text, and its box is cut down to the span from the first to the last of those words.
Prints each hit and writes WORK/qc/gfx_face.json; exit 1 on a FAIL, 2 on a NEAR (2+ frames of one graphic), 0 otherwise
(a single-frame "near?" is listed for an eye check).
"""
import difflib, json, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
import qc_gate as G

a = sys.argv[1:]
W, OUT = a[0], a[1]
FPS = float(a[a.index("--fps") + 1]) if "--fps" in a else 4.0
NEAR = 140   # px at 4K: his ear and cap brim stick out 60-100 past the Vision face box (more in a punch-in)
ONLY = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
evs = json.load(open(f"{W}/react_events.json"))["events"]
evs = [e for e in evs if (not ONLY or e["id"] in ONLY) and e["type"] not in ("end",)]


def obstacles(f):
    for _ in range(2):
        r = subprocess.run([f"{BIN}/frame_obstacles", f], capture_output=True, text=True)
        try: return json.loads(r.stdout)
        except ValueError: pass
    return None


def own_words(e):
    """every word of 2+ letters or digits in the graphic's own copy, upper case"""
    out = set()
    def walk(v):
        if isinstance(v, str): out.update(m.upper() for m in re.findall(r"[A-Za-z0-9]{2,}", v))
        elif isinstance(v, (list, tuple)):
            for x in v: walk(x)
    for k in ("title", "text", "items", "value", "label", "sub", "kicker", "topic", "foot", "finding", "journal", "authors", "lines"):
        walk(e.get(k))
    return out


def ours(s, words):
    """(first char, end char) of the stretch of this OCR line that is the graphic's own words, or None"""
    hit = [m for m in re.finditer(r"[A-Za-z0-9]{2,}", s)
           if m.group().upper() in words or difflib.get_close_matches(m.group().upper(), words, 1, 0.75)]
    return (hit[0].start(), hit[-1].end()) if hit else None


def check(e, td):
    a0, a1 = e["edit_in"] + 0.08, e["edit_out"] - 0.08
    if a1 <= a0: return []
    d = f"{td}/{e['id']}"; os.makedirs(d)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a0:.3f}", "-t", f"{a1 - a0:.3f}", "-i", OUT, "-vf", f"fps={FPS}",
                    "-q:v", "3", f"{d}/f%04d.jpg"], check=True)
    hits, mine = [], own_words(e)
    for k, f in enumerate(sorted(os.listdir(d))):
        o = obstacles(f"{d}/{f}")
        if o is None: hits.append(("ERR", e["id"], round(a0 + k / FPS, 2), "vision failed")); continue
        sx = 3840 / o["w"]; t = round(a0 + (k + 0.5) / FPS, 2)
        fs = sorted([[v * sx for v in b] for b in o.get("faces", [])], key=lambda b: -b[2] * b[3])
        if not fs or fs[0][2] * fs[0][3] < 0.002 * 3840 * 2160: continue
        face = fs[0]
        for x, y, w, h, s in ([v * sx for v in b[:4]] + [b[4]] for b in o.get("texts", [])):
            s = str(s).strip()
            if len(s.replace(" ", "")) <= 2 or not G.real_text(s): continue
            span = ours(s, mine)
            if span is None: continue   # not this graphic's copy: his shirt, his cap, OCR junk on his ear
            x, w = x + w * span[0] / len(s), w * (span[1] - span[0]) / len(s)
            ix = max(0, min(x + w, face[0] + face[2]) - max(x, face[0])); iy = max(0, min(y + h, face[1] + face[3]) - max(y, face[1]))
            if ix * iy > 0.25 * w * h or ix * iy > 0.08 * face[2] * face[3]:
                hits.append(("FAIL", e["id"], t, s, [int(v) for v in face], [int(x), int(y), int(w), int(h)], f"{d}/{f}"))
            elif iy > 0.5 * h and max(face[0] - (x + w), x - (face[0] + face[2])) < NEAR:   # beside his face at its height, closer than his ear
                hits.append(("NEAR", e["id"], t, s, [int(v) for v in face], [int(x), int(y), int(w), int(h)], f"{d}/{f}"))
    # a NEAR counts when the graphic reads near him in 2+ frames: OCR glues his ear to a line now and then (one frame), a real
    # lean shows in several (the 3:59 icon on his ear: 2 frames; 8:51: 13). A single one is listed as "near?" for an eye check.
    if sum(1 for h in hits if h[0] == "NEAR") < 2: hits = [("near?",) + h[1:] if h[0] == "NEAR" else h for h in hits]
    return hits


with tempfile.TemporaryDirectory(dir=os.path.expanduser("~/ob-scratch")) as td:
    with ThreadPoolExecutor(G.VISION_JOBS if hasattr(G, "VISION_JOBS") else 2) as ex:
        res = list(ex.map(lambda e: check(e, td), evs))
    hits = [h for r in res for h in r]
    keep = f"{W}/qc/gfx_face"; os.makedirs(keep, exist_ok=True)
    for h in hits:
        if len(h) > 6 and os.path.exists(h[6]):
            dst = f"{keep}/{h[1]}_{h[2]:.2f}.jpg"; subprocess.run(["cp", h[6], dst]); h = h[:6] + (dst,)
    hits = [h[:6] + ((f"{keep}/{h[1]}_{h[2]:.2f}.jpg",) if len(h) > 6 else ()) for h in hits]
n = sum(1 for e in evs if e["edit_out"] - e["edit_in"] > 0.16)
json.dump({"out": OUT, "fps": FPS, "events": n, "hits": hits}, open(f"{W}/qc/gfx_face.json", "w"), indent=1)
for h in hits: print(*h[:4], h[4:6] if len(h) > 4 else "")
fails = [h for h in hits if h[0] in ("FAIL", "ERR")]
print(f"{n} graphics read at {FPS:g} fps: {len(fails)} FAIL, {sum(1 for h in hits if h[0] == 'NEAR')} NEAR (within {NEAR} px of his face box in 2+ frames), "
      f"{sum(1 for h in hits if h[0] == 'near?')} single-frame near (check by eye)")
sys.exit(1 if fails else (2 if any(h[0] == 'NEAR' for h in hits) else 0))
