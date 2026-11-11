#!/usr/bin/env python3
"""Keep on-frame graphics off OB's head: measure where his head goes during each overlay and place tags around it.

  python3 -I head_clear.py WORK_DIR [--write]

For every pills / photo_overlay / label event in events_resolved.json, samples the edit every 0.15 s (OB_FACE_STEP; 0.4 s before 2026-11-03), maps each sample
to the source frame (with the shot's wide/punch framing), finds his face with Apple Vision (bin/faces), and grows each
face box to cover the cap (0.8 face-heights above, 0.2 to each side). The union over the event is his head zone.
pills: --write stores per-event "slots" in events_spec.json: left tags end 110 px left of the zone, right tags start
110 px right of it, rows at the default heights. Overlays and labels are only checked: any overlap is printed.
4K coordinates throughout. Needs OB_SRC (camera file).
"""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

W = sys.argv[1]; WRITE = "--write" in sys.argv
SRC = os.environ.get("OB_SRC", "/Volumes/T7/C4352.MP4")
BIN = os.path.dirname(os.path.abspath(__file__))
PUNCH = "crop=3200:1800:320:120,"
SLOTS = {"pair_LR": [(140, 230, 1300, 1700), (2400, 230, 1300, 1700)], "pair_sm": [(380, 520, 880, 1100), (2580, 520, 880, 1100)],
         "flash": [(160, 260, 1240, 1640), (2440, 260, 1240, 1640)],
         "pair_LRn": [(80, 230, 1060, 1700), (2700, 230, 1060, 1700)], "flashn": [(80, 260, 1060, 1640), (2700, 260, 1060, 1640)],
         "portrait4": [(120, 511, 640, 1138), (820, 511, 640, 1138), (2380, 511, 640, 1138), (3080, 511, 640, 1138)],
         "landscape4": [(140, 40, 1180, 1020), (140, 1100, 1180, 1020), (2520, 40, 1180, 1020), (2520, 1100, 1180, 1020)]}
ROWS = [290, 640, 990]; MARGIN = 110
segs = json.load(open(f"{W}/cutlist.json"))["segments"]
evs = json.load(open(f"{W}/events_resolved.json"))["events"]


def e2s(t):
    for s in segs:
        if s["edit_in"] <= t < s["edit_out"]: return s["src_in"] + t - s["edit_in"], s["framing"]
    return segs[-1]["src_out"] - 0.05, segs[-1]["framing"]


def grab(job):
    t, fram, out = job
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", SRC, "-vf", (PUNCH if fram == "punch" else "") + "scale=960:540",
                    "-frames:v", "1", "-q:v", "4", out], check=True)
    return out


def pill_w(text):   # measured on the E05 mock: ~0.53 em per character at 72 px, plus icon, gap, padding and border
    return int(len(text) * 72 * 0.53 + 66 + 22 + 74 + 14)


todo = [e for e in evs if e["type"] in ("pills", "photo_overlay", "label")]
tmp = tempfile.mkdtemp(dir="/Volumes/T7/OB-EDITS/tmp")
jobs, owner = [], []
for e in todo:
    t = e["edit_in"] + 0.05
    while t < e["edit_out"]:
        s, fr = e2s(t); jobs.append((s, fr, f"{tmp}/{e['id']}_{len(jobs):04d}.jpg")); owner.append(e["id"]); t += float(os.environ.get("OB_FACE_STEP", "0.15"))   # 2026-11-03 M5 Pro: every 0.15 s (was 0.4 s on the 8 GB Air)
with ThreadPoolExecutor(12) as ex: files = list(ex.map(grab, jobs))
res = subprocess.run([f"{BIN}/faces"] + files, capture_output=True, text=True, check=True).stdout.splitlines()
faces, misses = {}, {}
for line, eid, job in zip(res, owner, jobs):
    parts = line.split(" ", 1)[1]
    if parts in ("none", "error"): misses[eid] = misses.get(eid, 0) + 1; continue
    faces.setdefault(eid, []).append(tuple(4 * float(v) for v in parts.split("|")[0].split()))
for f in files: os.remove(f)
os.rmdir(tmp)


def head(f):   # face box grown to cover the cap and hair
    x0, y0, x1, y1 = f; w, h = x1 - x0, y1 - y0
    return (x0 - 0.2 * w, y0 - 0.8 * h, x1 + 0.2 * w, y1 + 0.1 * h)


def robust(vals, lo):   # with 8+ samples ignore the single most extreme one (a stray detection)
    v = sorted(vals); return (v[1] if lo else v[-2]) if len(v) >= 8 else (v[0] if lo else v[-1])


zone = {}
for eid, fs in faces.items():
    hs = [head(f) for f in fs]
    zone[eid] = (robust([h[0] for h in hs], 1), robust([h[1] for h in hs], 1), robust([h[2] for h in hs], 0), robust([h[3] for h in hs], 0))


def drawn(slot, key, folder):   # object-fit: contain inside the slot
    from PIL import Image
    x, y, w, h = slot; iw, ih = Image.open(f"{W}/hf/assets/{folder}/{key}.jpg").size
    k = min(w / iw, h / ih); dw, dh = iw * k, ih * k
    return (x + (w - dw) / 2, y + (h - dh) / 2, x + (w + dw) / 2, y + (h + dh) / 2)


spec = json.load(open(f"{W}/events_spec.json")); byid = {e["id"]: e for e in spec["events"]}
for e in todo:
    z = zone.get(e["id"])
    if z is None: print(f"{e['id']}: no face found"); continue
    zs = f"head x {z[0]:.0f}-{z[2]:.0f}, y {max(z[1], 0):.0f}-{z[3]:.0f}" + (f" ({misses[e['id']]} frames without a face)" if e["id"] in misses else "")
    if e["type"] == "pills":
        lx, rx = int(z[0] - MARGIN), int(z[2] + MARGIN)
        slots = [("L", lx, ROWS[0]), ("R", rx, ROWS[0]), ("L", lx - 140, ROWS[1]), ("R", rx + 140, ROWS[1]), ("L", lx - 20, ROWS[2]), ("R", rx + 20, ROWS[2])]
        bad = []
        for i, it in enumerate(e["items"]):
            side, ex, _ = slots[i % len(slots)]; wpx = pill_w(it[0])
            if (side == "L" and ex - wpx < 40) or (side == "R" and ex + wpx > 3800): bad.append(f'"{it[0]}" ({wpx} px) runs off the {side} edge')
        print(f"{e['id']} pills: {zs} -> left tags end at {lx}, right tags start at {rx}" + ("; " + "; ".join(bad) if bad else ""))
        if WRITE: byid[e["id"]]["slots"] = [list(s) for s in slots]
    else:
        if e["type"] == "label": boxes = [("label", (170, 120, 1100, 370))]
        else:
            sl = SLOTS[e["layout"]]; boxes = [(it[0], drawn(sl[it[1]], it[0], e.get("folder", "proof"))) for it in e["items"]]
        face_hit = max([min(b[2], f[2]) - max(b[0], f[0]) for _, b in boxes for f in faces[e["id"]] if b[1] < f[3] and b[3] > f[1]] + [0])
        head_hit = [k for k, b in boxes if b[0] < z[2] and b[2] > z[0] and b[1] < z[3] and b[3] > max(z[1], 0)]
        print(f"{e['id']} {e['type']}: {zs} -> " + (f"COVERS HIS FACE by up to {face_hit:.0f} px" if face_hit > 0 else "face clear")
              + (f"; touches cap/hair margin: {', '.join(sorted(set(head_hit)))}" if head_hit else ""))
if WRITE:
    json.dump(spec, open(f"{W}/events_spec.json", "w"), indent=1, ensure_ascii=False); print("slots written to events_spec.json")
