#!/usr/bin/env python3
"""ytclip_look: the clipper's look since 11-04. OB rejected the 10-28 seed-oil R1 pack ("im not on the screen at all", 10-30);
this is the rebuild to his rules since: Dylan Page's split for a story told to camera (styles/dylan-page-split.md, the 10-30 and
11-04 passes; ledger M37-M40, M44-M45), on the Mac mini.

  split  a RECEIPT for his claim fills the top panel (1080x876, seam y 876): the long-form's own B-roll, a document page with
         the yellow marker sweeping on his words, a photo, or its sourced data (an odometer count, bars, a study, a
         comparison) on his own studio, blurred and warm (M38: never black). He sits chest-up in the 1044 px panel under it:
         his 4K frame at full height, the same framing all the way (Dylan Page: no punch-ins in the split)
  full   him full frame (the 9:16 crop) on a line with no receipt, the turns into and out of a clip, and the closer.
         Never stock, never a text card (M28, M40)
  clip   a clip playing its own sound: full frame, 3:4 around its speaker over its own blur, its words captioned (M37 lets
         footage go full screen only while he is silent)
Moves (measured on DfQDZtxMo50, tmpl_fx): the panel drops in (0.45 s ease-out, first frame 75% down) and slides up (0.30 s,
accelerating); a receipt changes by cut, push or blur, never the same move twice running; a look-down at a cut inside a
full-frame line switches to the split for that moment (M37: the screen + PiP, never a cutaway).
Text (brand.json): Big Shoulders on the picture with a soft shadow and no boxes. His captions (3 words, the live word
#FFD400) sit just above the seam in the split and under his chin full frame; the story's 2-4 word label is on frame 0 and
leaves at the first receipt change; a person's name types on above the seam the first time he names them. One file per reel
(M45).

  python3 -I ytclip_look.py chunk PLAN.json F0 F1 OUT.mp4     (the render's worker: frames [F0, F1) of one reel)
"""
import json, math, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
import tmpl_fx as FX   # noqa: E402  (the brand's shared elements; read-only here)
_spring0 = FX.spring
FX.spring = lambda t, freq=3.2, damp=0.92: _spring0(t, freq, 0.92)   # 11-07: entrance springs damped at 0.92 in this process only, no bounce

FW, FH, SEAM = 1080, 1920, 876
PH = FH - SEAM                    # his panel: 1044 px
SC = PH / 2160                    # his 4K frame at full height in the panel (0.483): face ~330 px, cap ~110 px under the seam
LEAD = 0.45                       # the silent prop beat before his first word (PROVEN-OPENERS #4)
CAP_SPLIT, CAP_CLIP = 836, 1350   # captions: just above the seam / under a clip's speaker, clear of Instagram's bottom 420 px
LABEL_SPLIT, LABEL_FULL = 742, 330
CREDIT_Y = 236                    # a receipt's source, under Instagram's top bar
HOLD_MAX, HOLD_MIN, SHORT = 6.0, 2.5, 0.6   # a receipt holds to its line's end, at least 2.5 s, at most 6 s (median 3.5 in the reference)
DROP, SLIDE, MOVE = 0.45, 0.30, 0.28
CLIP_Y, CLIP_H = 240, 1440        # a clip with its own sound: 3:4 at full width, its own blur above and below
YEL, WHITE = FX.YEL, FX.WHITE
KIND = {"insert": "video", "photo_full": "photo", "doc": "doc", "num": "count", "stat_bars": "bars", "versus": "versus", "study": "study"}
RATE = 30000 / 1001


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode: raise RuntimeError(" ".join(str(c) for c in cmd[:8]) + "\n" + p.stderr[-1500:])
    return p.stdout


def asset(c, rel): return os.path.join(c["longform"], "hf", "assets", rel)


# ---------------------------------------------------------------------------------------------------- the plan
def chin_low(c, shots):
    """His lowest chin in each full-frame shot: Vision at the shot's start and end too, not only its middle. He leans in, and
    on 11-04 (R3 46.75 s) his chin sat on the caption line the middle frame put 165 px lower. Cached like faces_of."""
    import ytclip_pic as P
    cp = os.path.join(c["work"], "cache", "faces_edges.json"); cache = json.load(open(cp)) if os.path.exists(cp) else {}
    want = [(s, t) for s in shots if s["kind"] == "ob" for t in (s["a"] + 0.08, max(s["a"] + 0.08, s["b"] - 0.08)) if f"{t:.3f}" not in cache]
    if want:
        with tempfile.TemporaryDirectory() as td:
            imgs = []
            for k, (s, t) in enumerate(want):
                p = os.path.join(td, f"f{k}.jpg"); P.grab(c, t, p); imgs.append(p)
            for line in P.run([os.path.join(P.BIN, "faces")] + imgs).splitlines():
                path, rest = line.split(" ", 1); k = int(os.path.basename(path)[1:-4])
                cache[f"{want[k][1]:.3f}"] = None if rest.strip() in ("none", "error") else [float(v) * 2 for v in rest.split("|")[0].split()]
        os.makedirs(os.path.dirname(cp), exist_ok=True); json.dump(cache, open(cp, "w"))
    for s in shots:
        if s["kind"] != "ob": continue
        w, h, x, y = s["crop"]
        for t in (s["a"] + 0.08, max(s["a"] + 0.08, s["b"] - 0.08)):
            b = cache.get(f"{t:.3f}")
            if b and abs((b[0] + b[2]) / 2 - (s["face"][0] + s["face"][2]) / 2) < 600:   # him, not a stray box
                s["chin"] = max(s["chin"], (b[3] - y) * FH / h)


def build(c, r):
    """Everything one reel needs, saved as reels/R?/look.json so the stills, the render's workers and QA read the same plan:
    shots (his crops), his words and the clip's, the receipts, the spans with their moves, the label and the names."""
    import ytclip_pic as P
    d = os.path.join(c["work"], "reels", r["id"]); cut = json.load(open(os.path.join(d, "cut.json")))
    shots, nf = P.timeline(c, cut); P.faces_of(c, shots); P.crops(shots); chin_low(c, shots)
    for s in shots:
        if s["kind"] != "ob": continue
        x0f, y0f, x1f, y1f = s["face"]; w = int(round(PH / SC / 2) * 2)
        x = int(min(max((x0f + x1f) / 2 - w / 2, 0), 3840 - w)) // 2 * 2
        s["vcrop"] = [w, 2160, x, 0]; s["vface"] = [round((x0f - x) * SC), round(SEAM + y0f * SC), round((x1f - x) * SC), round(SEAM + y1f * SC)]
    for s in shots:   # a clip's 3:4 window sits on its speaker (clipper.json "split" fx: B_LK_DENY 1.0, F12 0.77)
        if s["kind"] == "clip": s["fx"] = ((c.get("split") or {}).get(s["clip"]) or {}).get("fx", 0.5)
    clip_ids = {l["id"] for l in cut["lines"] if l.get("clip")}
    ws = P.words_reel(c, cut, shots)
    words = [dict(w=w["w"], s=round(w["t"], 3), e=round(ws[k + 1]["t"] if k + 1 < len(ws) else w["t"] + 0.45, 3), clip=w["line"] in clip_ids)
             for k, w in enumerate(ws)]
    for w in words: w["e"] = round(min(w["e"], w["s"] + 0.9), 3)
    T = nf / c["fps"]
    lines = {}
    for s in shots: lines.setdefault(s["line"], [s["t0"], s["t1"], s["kind"]]); lines[s["line"]][1] = s["t1"]
    recs = receipts(c, r, cut, shots, lines)
    flags = json.load(open(os.path.join(d, "lookoff.json"))) if os.path.exists(os.path.join(d, "lookoff.json")) else []
    K = dict(reel=r["id"], fps=c["fps"], frames=nf, T=T, shots=shots, words=words, lines=lines, recs=recs,
             label=r.get("label", ""), accent=r.get("accent", ""), names=r.get("names", []),
             camera=c["camera"], camera_offset=float(c.get("camera_offset", 0.0)), lut=c["lut"], longform=c["longform"], work=c["work"])
    for rc in recs:   # a receipt's source line, where it won't touch a face in it
        if rc.get("credit") and rc["kind"] in ("video", "photo"):
            pic = one(top_cmd(rc, rc["boff"] + 0.3, 1)) if rc["kind"] == "video" else FX.fit_cover(FX.load(rc["path"], "RGB"), FW, SEAM)
            rc["credit_y"] = credit_spot(pic, rc["credit"])
    K["spans"] = spans_of(K, flags)
    json.dump(K, open(os.path.join(d, "look.json"), "w"), indent=1, default=str)
    return K


def receipts(c, r, cut, shots, lines):
    """The long-form's own proof for each claim, in reel time: every event of a receipt kind whose anchor word is in a kept
    piece, or within 1.5 s of one (R1's FDA page sat just past its kept words). Text-only cards (quotes, pills, stamps,
    checklists) are not receipts: his words are captioned. picks "receipts" can place an event on a line by hand."""
    import ytclip_pic as P
    evs = json.load(open(os.path.join(c["longform"], "events_resolved.json")))["events"]; by_id = {e["id"]: e for e in evs}
    obs = [s for s in shots if s["kind"] == "ob"]; out = []
    def place(a):
        best = None
        for s in obs:
            dd = 0.0 if s["a"] <= a <= s["b"] else min(abs(a - s["a"]), abs(a - s["b"]))
            if dd <= 1.5 and (best is None or dd < best[0]): best = (dd, s)
        if best is None: return None, None
        s = best[1]; return round(s["t0"] + min(max(a - s["a"], 0.0), s["b"] - s["a"]), 3), s["line"]
    hand = {h["event"]: h for h in r.get("receipts", [])}
    for e in evs:
        k = KIND.get(e["type"]); a = e.get("anchor_src")
        if not k or a is None or e["id"] in r.get("skip_receipts", []): continue
        t0, line = place(a)
        if e["id"] in hand and hand[e["id"]].get("line") in lines: t0, line = round(lines[hand[e["id"]]["line"]][0], 3), hand[e["id"]]["line"]
        if t0 is None: continue
        rc = dict(id=e["id"], kind=k, t0=t0, line=line, ev=e, sub={})
        for key, val in (e.get("at") or {}).items():   # item times (the number lands on its word)
            if isinstance(val, dict) and "src" in val:
                tt, _ = place(val["src"]); rc["sub"][key] = round(tt - t0, 3) if tt is not None else 0.6
            elif isinstance(val, (int, float)): rc["sub"][key] = float(val)
        if k == "video":
            p = asset(c, f"broll/{e['broll']}.mp4")
            if not os.path.exists(p): continue
            rc.update(path=p, view=view(c, p))
            if rc["view"]["mode"] == "card": rc.update(kind="quote", text=rc["view"]["text"])
        elif k == "photo":
            p = asset(c, e.get("image", ""))
            if not e.get("image") or not os.path.exists(p): continue
            rc["path"] = p
        rc["credit"] = credit_of(e)
        out.append(rc)
    for h in r.get("receipts", []):   # events placed by hand that no kept word anchors
        if h["event"] in by_id and h.get("line") in lines and not any(x["id"] == h["event"] for x in out):
            e = by_id[h["event"]]; k = KIND.get(e["type"])
            if k: out.append(dict(id=e["id"], kind=k, t0=round(lines[h["line"]][0], 3), line=h["line"], ev=e, sub={}, credit=credit_of(e),
                                  **({"path": asset(c, f"broll/{e['broll']}.mp4"), "view": view(c, asset(c, f"broll/{e['broll']}.mp4"))} if k == "video" else {}),
                                  **({"path": asset(c, e["image"])} if k == "photo" else {})))
    out.sort(key=lambda x: x["t0"]); keep = []
    for rc in out:   # one receipt per moment
        if keep and rc["t0"] - keep[-1]["t0"] < SHORT: continue
        keep.append(rc)
    cur = {}   # a B-roll used twice carries on from where it stopped (R5's aisle showed 4 moments, not one)
    for rc in keep:
        if rc["kind"] != "video": continue
        p = rc["path"]; o = cur.get(p, 0.2)
        rc["boff"] = round(o if o + 2.5 <= P.clean_end(p) else 0.2, 3); cur[p] = rc["boff"] + 2.5
    return keep


def faces_in(img):
    """Apple Vision face boxes [x0, y0, x1, y1] in a PIL image ([] when none; a Vision failure raises, M46)."""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "f.jpg"); img.convert("RGB").save(p, quality=90); o = run([os.path.join(BIN, "faces"), p]).strip()
    rest = o.split(" ", 1)[1].strip() if " " in o else "none"
    return [] if rest in ("none", "error") else [[float(v) for v in b.split()] for b in rest.split("|") if b.strip()]


_BIG = {}
def biggest_face(path, t):
    """The biggest face in a video at second t, in the file's pixels, or None."""
    if (path, t) not in _BIG:
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "f.png"); run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", p])
            im = Image.open(p).convert("RGB")
        try: fs = faces_in(im)
        except RuntimeError: fs = []
        _BIG[(path, t)] = max(fs, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])) if fs else None
    return _BIG[(path, t)]


def credit_spot(img, text):
    """Where a receipt's source line can sit without touching a face in it: top left under Instagram's bar, else lower on the
    left, else nowhere (a credit never covers a face; R2's sat on Liver King's hair, 11-04)."""
    try: fs = faces_in(img)
    except RuntimeError: return CREDIT_Y
    w = FX.font(32, "ExtraBold").getlength(text) + 30
    for y in (CREDIT_Y, CREDIT_Y + 64, SEAM - 250):
        if not any(f[0] - 20 < 36 + w and f[2] + 20 > 36 and f[1] - 20 < y + 24 and f[3] + 20 > y - 24 for f in fs): return y
    return None


def credit_of(e):
    tag = (e.get("tag") or "").strip(); sub = (e.get("sub") or "").replace("link in the description", "").strip(" ·")
    return f"{tag} · {sub}" if tag and sub else tag


def view(c, path):
    """How a B-roll or clip fills the top panel (1080x876). Default: edge to edge around the middle (his reference crops TV
    footage this way). clipper.json "split" per file: crop [x0, y0, x1, y1] (trims a TV lower third so it isn't cut
    mid-word), fx / fy (where the crop sits), fit (a wide graphic keeps its whole width over its own blur) or card (a title
    too small to read: a quote card in his brand). A vertical phone video is cropped into the panel (it only goes full frame
    while it plays its own sound)."""
    import ytclip_pic as P
    box, (W, H) = P.probe_box(path, 1.0); name = os.path.splitext(os.path.basename(path))[0]
    o = (c.get("split") or {}).get(name, {})
    if o.get("card"): return dict(mode="card", text=o["card"])
    if box:
        rx, ry, rw, rh = box[0], 0, box[2] - box[0], H; o = dict(o, fy=o.get("fy", 0.3))
        i = o.get("inset", 0.0); rx, rw = rx + rw * i, rw * (1 - 2 * i)   # a loose box edge shows a strip of the blur (R3 TikTok, 11-04)
    else:
        x0, y0, x1, y1 = o.get("crop") or (0, 0, 1, 1); rx, ry, rw, rh = x0 * W, y0 * H, (x1 - x0) * W, (y1 - y0) * H
    if o.get("fit"):
        hh = int(round(rh * FW / rw / 2) * 2); return dict(mode="fit", rect=[int(rw), int(rh), int(rx), int(ry)], h=hh, y=int(min(max(505 - hh / 2, 0), SEAM - hh)))
    A = FW / SEAM
    if rw / rh > A: cw, ch = rh * A, rh; cx, cy = rx + (rw - cw) * o.get("fx", 0.5), ry
    else: cw, ch = rw, rw / A; cx, cy = rx, ry + (rh - ch) * o.get("fy", 0.5)
    manual = (c.get("split") or {}).get(name, {})
    if "fx" not in manual and "fy" not in manual:   # a person in the footage keeps their whole head (R2's Liver King lost his, 11-04)
        f = biggest_face(path, 1.0)
        if f:
            fx0, fy0, fx1, fy1 = f
            cx = min(max((fx0 + fx1) / 2 - cw / 2, rx), rx + rw - cw); cy = min(max(fy0 - 0.22 * ch, ry), ry + rh - ch)
    return dict(mode="cover", rect=[int(cw) // 2 * 2, int(ch) // 2 * 2, int(cx), int(cy)])


def spans_of(K, flags):
    """The reel as spans [{t0, t1, state, rc, cover, move}] from 0 to T. A receipt holds from its claim's first word to the
    end of its line (at least 2.5 s, at most 6 s, never past the next receipt); it stops before a clip, the line into or out
    of a clip, and the closer. A look-down at a cut inside a full-frame line gets the split for 0.67 s (M37), with the
    nearest receipt on top. Full stretches under 0.6 s between two receipts are held over (no flicker)."""
    T, recs, lines = K["T"], K["recs"], K["lines"]
    order = sorted(lines, key=lambda k: lines[k][0]); clip_ids = [k for k in order if lines[k][2] == "clip"]
    clips = []
    for k in clip_ids:
        a, b = lines[k][0], lines[k][1]
        if clips and a - clips[-1][1] < 0.05: clips[-1][1] = b
        else: clips.append([a, b])
    turns = set()
    for i, k in enumerate(order):
        if lines[k][2] != "clip" and ((i + 1 < len(order) and lines[order[i + 1]][2] == "clip") or (i > 0 and lines[order[i - 1]][2] == "clip")): turns.add(k)
    closer = next((k for k in reversed(order) if lines[k][2] != "clip"), None)
    stops = sorted([a for a, b in clips] + [lines[k][0] for k in turns | ({closer} if closer else set())])
    win = []
    for i, rc in enumerate(recs):
        st = rc["t0"]; nxt = recs[i + 1]["t0"] if i + 1 < len(recs) else T
        lend = lines.get(rc["line"], [st, st + HOLD_MIN])[1]
        en = min(nxt, max(lend, st + HOLD_MIN), st + HOLD_MAX)
        if rc["ev"].get("until") is not None: en = min(nxt, float(rc["ev"]["until"]))   # 11-09 3D graphics: a hand-set end (reel seconds)
        en = min([en] + [s for s in stops if s > st + 0.05])
        if any(a - 0.02 <= st < b for a, b in clips): continue
        if en - st >= SHORT: win.append(dict(t0=st, t1=en, rc=rc["id"], cover=False))
    def free(a, b): return not any(w["t0"] < b and w["t1"] > a for w in win) and not any(x < b and y > a for x, y in clips)
    if recs:
        for f in flags:   # M37: a look-down at a cut becomes the screen + PiP, never a cutaway
            te = f["reel_t"]; a, b = (te - 0.12, te + 0.55) if f["side"] == "start" else (te - 0.55, te + 0.12)
            a, b = max(a, 0.0), min(b, T)
            if b - a < 0.2 or not free(a, b): continue
            # the receipt he was just on (a card shown before its own claim would be empty), else the first one
            near = max((x for x in recs if x["t0"] <= te), key=lambda x: x["t0"], default=None) or recs[0]
            win.append(dict(t0=a, t1=b, rc=near["id"], cover=True))
    win.sort(key=lambda w: w["t0"]); merged = []
    if win and 0 < win[0]["t0"] < 1.0 and not any(a < win[0]["t0"] for a, b in clips): win[0]["t0"] = 0.0   # frame 0 is the split (the reference)
    for w in win:   # a gap under 1.2 s between two splits holds the first over (no flicker in and out of the split)
        if merged and w["t0"] - merged[-1]["t1"] < 1.2 and free(merged[-1]["t1"], w["t0"]) and (merged[-1]["rc"] == w["rc"] or not w["cover"]):
            if merged[-1]["rc"] == w["rc"]: merged[-1]["t1"] = max(merged[-1]["t1"], w["t1"]); merged[-1]["cover"] = merged[-1]["cover"] and w["cover"]; continue
            merged[-1]["t1"] = w["t0"]   # a short gap between two receipts: the first holds to the second
        merged.append(dict(w))
    out, t = [], 0.0
    def full_or_clip(a, b):
        cur = a
        for x, y in clips:
            if y <= cur or x >= b: continue
            if x > cur + 1e-3: out.append(dict(t0=cur, t1=x, state="full"))
            out.append(dict(t0=max(x, cur), t1=min(y, b), state="clip")); cur = min(y, b)
        if b > cur + 1e-3: out.append(dict(t0=cur, t1=b, state="full"))
    for w in merged:
        if w["t0"] > t + 1e-3: full_or_clip(t, w["t0"])
        out.append(dict(t0=w["t0"], t1=w["t1"], state="split", rc=w["rc"], cover=w["cover"])); t = w["t1"]
    if T > t + 1e-3: full_or_clip(t, T)
    out = [s for s in out if s["t1"] - s["t0"] > 1e-3]
    if out and out[0]["t0"] > 0: out[0]["t0"] = 0.0
    i = 1
    while i < len(out):   # under 0.5 s of full frame after a split is a blink: the split holds over it (R2 19.5 s, before its clip)
        if out[i]["state"] == "full" and out[i]["t1"] - out[i]["t0"] < 0.5 and out[i - 1]["state"] == "split":
            out[i - 1]["t1"] = out[i]["t1"]; del out[i]; continue
        i += 1
    last = None
    for i, s in enumerate(out):   # the moves into each span
        p = out[i - 1] if i else None; mv = "cut"
        if p and s["state"] == "split" and p["state"] == "full" and not (s.get("cover") or p.get("cover")): mv = "drop"
        elif p and s["state"] == "full" and p["state"] == "split" and not p.get("cover"): mv = "cut"   # back to him full frame is a hard cut: a slide hid his face for 0.3 s (M37, R3 11-04)
        elif p and s["state"] == "split" and p["state"] == "split" and s["rc"] != p["rc"]:
            mv = next(m for m in ("push", "blur", "cut") if m != last); last = mv
            sa, sb = (next((r["ev"].get("scene") for r in recs if r["id"] == x), None) for x in (p["rc"], s["rc"]))
            if sa and sa == sb: mv = "cut"   # 11-09: two chapters of one continuous 3D scene are seamless, no move between them
        s["move"] = mv
        for k in ("t0", "t1"): s[k] = round(s[k], 3)
    return out


# ---------------------------------------------------------------------------------------------------- frames in
def span_at(K, t):
    for s in K["spans"]:
        if s["t0"] <= t < s["t1"]: return s
    return K["spans"][-1]


def shot_at(K, t):
    for s in K["shots"]:
        if s["t0"] <= t < s["t1"] + 1e-6: return s
    return K["shots"][-1] if t >= K["shots"][-1]["t0"] else K["shots"][0]


def ob_shot_at(K, t):
    """His camera shot at t: the shot itself, or (in the lead before his first word) the first shot run backwards in time."""
    s = shot_at(K, t)
    if s["kind"] == "ob": return s
    obs = [x for x in K["shots"] if x["kind"] == "ob"]
    return min(obs, key=lambda x: min(abs(x["t0"] - t), abs(x["t1"] - t)))


def cam_time(s, t): return s["a"] + (t - s["t0"])   # reel t to camera seconds (cam_cmd subtracts K camera_offset when the camera is a window copy)


def cam_cmd(K, s, t, n, full):
    """ffmpeg for n frames of his camera from reel time t: the full 9:16 crop, or the split panel (his whole 4K height)."""
    w, h, x, y = s["crop"] if full else s["vcrop"]; size = (FW, FH) if full else (FW, PH)
    g = f"[0:v]crop={w}:{h}:{x}:{y},scale={size[0]}:{size[1]}:flags=lanczos[a];[a][1:v]haldclut=interp=tetrahedral,format=rgb24"
    return ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{cam_time(s, t) - K.get('camera_offset', 0.0) - 0.25 / K['fps']:.4f}", "-i", K["camera"], "-i", K["lut"],
            "-filter_complex", g, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], size


_DARK = {}


def _dark(path, a):
    """True when the clip's own blur would read as black bands above and below it (M38: B_LK_DENY's dark room, 11-04)."""
    if path in _DARK: return _DARK[path]
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, a):.3f}", "-i", path, "-vf",
                        "crop=ih*9/16:ih,scale=36:64,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True)
    g = np.frombuffer(r.stdout, np.uint8)
    _DARK[path] = len(g) == 36 * 64 and min(g[:36 * 8].mean(), g[-36 * 8:].mean()) < 34
    return _DARK[path]


def _studio_full(K, s):
    """His studio behind a dark clip: the nearest frame of him, full 9:16, blurred and warm with the dot grid, made once."""
    out = os.path.join(K["work"], "reels", K["reel"], f"studio_{s['clip']}.png")
    if os.path.exists(out): return out
    o = ob_shot_at(K, s["t0"]); cam = one(cam_cmd(K, o, min(max(s["t0"], o["t0"]), o["t1"] - 0.05), 1, True))
    sm = cam.convert("RGB").resize((135, 240), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
    a = np.asarray(sm, np.float32) * 0.6; a[..., 0] *= 1.05; a[..., 2] *= 0.93
    bg = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((FW, FH), Image.BICUBIC).convert("RGBA")
    d = Image.new("RGBA", (FW, FH), (0, 0, 0, 0)); dr = ImageDraw.Draw(d)
    for y in range(18, FH, 36):
        for x in range(18, FW, 36): dr.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255, 24))
    bg.alpha_composite(d); tmp = out + f".{os.getpid()}.png"; bg.convert("RGB").save(tmp); os.replace(tmp, out); return out


def clip_cmd(K, s, t, n):
    """A clip with its own sound: 3:4 around its speaker at full width over its own blur, darkened a little (never black).
    A dark clip goes over his studio instead, since its own blur would be black bands."""
    path = os.path.join(K["longform"], "hf", "assets", "clips", s["clip"] + ".mp4"); fx = s.get("fx", 0.5)
    fg = f"crop=ih*3/4:ih:(iw-ih*3/4)*{fx}:0,scale={FW}:{CLIP_H}:flags=lanczos[fg]"
    ss = ["-ss", f"{max(0.0, s['a'] + (t - s['t0'])):.4f}", "-i", path]
    if _dark(path, s["a"]):
        g = f"[0:v]setpts=PTS-STARTPTS,fps=30000/1001,{fg};[1:v]setpts=PTS-STARTPTS,format=rgb24[bg];[bg][fg]overlay=0:{CLIP_Y}:shortest=1:eof_action=endall,format=rgb24"
        ins = ss + ["-loop", "1", "-framerate", "30000/1001", "-i", _studio_full(K, s)]
    else:
        g = (f"[0:v]fps=30000/1001,split[a][b];[a]scale={FW}:{FH}:force_original_aspect_ratio=increase,crop={FW}:{FH},gblur=sigma=40,"
             f"eq=brightness=-0.08:saturation=0.9[bg];[b]{fg};[bg][fg]overlay=0:{CLIP_Y},format=rgb24")
        ins = ss
    return ["ffmpeg", "-nostdin", "-v", "error"] + ins + ["-filter_complex", g,
            "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, FH)


def top_cmd(rc, toff, n):
    """A video receipt as 1080x876 frames from second toff of its file; past its clean end its last clean frame holds."""
    import ytclip_pic as P
    path, v = rc["path"], rc["view"]; end = P.clean_end(path); t = min(max(toff, 0.0), end - 0.04)
    src = f"[0:v]trim=end={end - t:.4f},setpts=PTS-STARTPTS,fps=30000/1001,tpad=stop_mode=clone:stop_duration=60"
    w, h, x, y = v["rect"]; src += f",crop={w}:{h}:{x}:{y}"
    if v["mode"] == "cover": g = f"{src},scale={FW}:{SEAM}:flags=lanczos,format=rgb24"
    else: g = (f"{src},split[ta][tb];[ta]scale={FW}:{SEAM}:force_original_aspect_ratio=increase,crop={FW}:{SEAM},gblur=sigma=30,"
               f"eq=brightness=-0.06[tbg];[tb]scale={FW}:{v['h']}:flags=lanczos[tfg];[tbg][tfg]overlay=0:{v['y']},format=rgb24")
    return ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-filter_complex", g, "-frames:v", str(n),
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], (FW, SEAM)


def frames_of(cmd, size, n):
    W, H = size; fsz = W * H * 3; p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL); last = None
    for _ in range(n):
        buf = p.stdout.read(fsz)
        if len(buf) == fsz: last = Image.frombuffer("RGB", (W, H), buf, "raw", "RGB", 0, 1).convert("RGBA")
        yield last if last is not None else Image.new("RGBA", (W, H), (40, 34, 30, 255))
    p.stdout.close(); p.wait()


def one(cmd_size): return next(frames_of(*cmd_size, 1))


def rc_by(K, rid): return next(r for r in K["recs"] if r["id"] == rid)


def toff(rc, sp, t):
    """Where a video receipt is in its file at reel time t: its own claim plays on from boff; a look-down switch shows its start."""
    if rc["ev"].get("reel_clock"): return t   # 11-09: a 3D master rendered on the reel's own clock, frame for frame
    if sp.get("cover"): return rc["boff"] + 0.4 + (t - sp["t0"])
    return rc["boff"] + max(0.0, t - rc["t0"])


# ---------------------------------------------------------------------------------------------------- drawing
_DOTS, _ST = None, [None, None]
def studio(panel):
    """His own studio from the same frame, blurred and warm, with the faint dot grid (M38): the background of every card
    receipt and of the top while the panel drops in. It moves with him (made once per frame)."""
    global _DOTS
    if _ST[0] is panel: return _ST[1].copy()
    s = panel.convert("RGB").resize((135, 130), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
    a = np.asarray(s, np.float32) * 0.6; a[..., 0] *= 1.05; a[..., 2] *= 0.93
    bg = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((FW, SEAM), Image.BICUBIC).convert("RGBA")
    if _DOTS is None:
        _DOTS = Image.new("RGBA", (FW, SEAM), (0, 0, 0, 0)); d = ImageDraw.Draw(_DOTS)
        for y in range(18, SEAM, 36):
            for x in range(18, FW, 36): d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255, 24))
    bg.alpha_composite(_DOTS); _ST[0], _ST[1] = panel, bg; return bg.copy()


def _text(im, xy, s, size, color=WHITE, weight="Black", anchor="mm", track=0, alpha=255):
    FX.shadow_text(im, xy, s, FX.font(size, weight), color, anchor=anchor, track=track, alpha=alpha)


def _fit_size(s, size, maxw, weight="Black"):
    while size > 30 and FX.font(size, weight).getlength(s) > maxw: size -= 2
    return size


def _wrap(s, size, maxw, weight="ExtraBold"):
    out, cur = [], ""
    for w in s.split():
        nxt = (cur + " " + w).strip()
        if cur and FX.font(size, weight).getlength(nxt) > maxw: out.append(cur); cur = w
        else: cur = nxt
    return out + ([cur] if cur else [])


def _source(im, s):
    """A number's source (rule 7: numbers only with a source), small under the card. Image credits ("Pen", one word) aren't one."""
    s = (s or "").split(":")[0].strip()
    for tail in (", via", " via"):
        if s.lower().endswith(tail): s = s[:-len(tail)].strip()
    if len(s) <= 12: return
    for cand in (s, s.split(" (")[0], s.split(";")[0], s.split(",")[0]):   # shortened at a break, never mid-word ("717,527 PEOPL")
        if len(cand.strip()) > 6 and FX.font(30, "ExtraBold").getlength(cand.strip().upper()) + 3 * len(cand) <= FW - 120: s = cand.strip(); break
    else: s = s.split(" (")[0].split(",")[0].strip()
    _head(im, s, SEAM - 120, size=30, color=(225, 225, 225), lines=1)


def _head(im, s, y, alpha=255, size=36, color=YEL, lines=2):
    """A source line that fits: its " · " parts on up to two lines (GEBN's "funded by Coca-Cola" was dropped to fit on one, 11-04)."""
    parts = [p.strip().upper() for p in str(s).replace(" | ", " · ").split(" · ") if p.strip()]
    f = FX.font(size, "ExtraBold"); width = lambda t: f.getlength(t) + 4 * len(t); out = []
    for p in parts:
        if out and width(out[-1] + " · " + p) <= FW - 120: out[-1] += " · " + p
        elif len(out) < lines and width(p) <= FW - 120: out.append(p)
        elif not out: out.append(p)
    for i, txt in enumerate(out[:lines]):
        _text(im, (FW / 2, y + i * (size + 10)), txt, _fit_size(txt, size, FW - 120, "ExtraBold"), color, "ExtraBold", track=4, alpha=alpha)


def _line_of(gray, x, y, w, h):
    """The text line a highlight box holds: the band of rows with the most ink in it (R3's boxes overlap the line above, 11-04)."""
    a = gray[y:y + h, x:x + w]; ink = (a < 150).sum(axis=1) > max(2, 0.01 * w); bands, k = [], 0
    while k < len(ink):
        if ink[k]:
            j = k
            while j < len(ink) and ink[j]: j += 1
            if bands and k - bands[-1][1] <= 3: bands[-1] = (bands[-1][0], j)   # an i-dot or a descender gap: one line
            else: bands.append((k, j))
            k = j
        else: k += 1
    if not bands: return y, h
    b = max(bands, key=lambda b: int((a[b[0]:b[1]] < 150).sum()))
    return y + max(0, b[0] - 5), (b[1] - b[0]) + 10


def _split(st, maxw):
    """A line of page pixels cut at the word gap nearest its middle until every piece is at most maxw wide."""
    if st.width <= maxw: return [st]
    a = np.asarray(st.convert("L")); blank = (a < 150).sum(axis=0) == 0; runs, k = [], 0
    space = max(5, 0.28 * (st.height - 10))   # a space between words, not the gap between two letters ("a | nd", 11-04)
    while k < len(blank):
        if blank[k]:
            j = k
            while j < len(blank) and blank[j]: j += 1
            if j - k >= space and 0 < k and j < len(blank): runs.append((k, j))
            k = j
        else: k += 1
    if not runs: return [st]
    a0, b0 = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - st.width / 2)); cut = (a0 + b0) // 2
    return _split(st.crop((0, 0, cut, st.height)), maxw) + _split(st.crop((cut, 0, st.width, st.height)), maxw)


def _num(s):
    """'60M' -> (60, '', 'M'); '+35%' -> (35, '+', '%'); '4,800' -> (4800, '', ''); text without a number -> None."""
    import re
    m = re.match(r"^\s*([+\-~$]?)([\d,]*\.?\d+)\s*(.*)$", str(s))
    if not m: return None
    v = float(m.group(2).replace(",", "")); return (v, m.group(1), m.group(3))


def _count_str(v, frac, pre, suf, dec):
    x = v if frac >= 1 else v * (1 - (1 - frac) ** 3)
    return f"{pre}{x:,.{dec}f}{suf}"


def card(K, rc, lt, bg, cover=False, label_up=False):
    """A card receipt at lt seconds after its claim's first word, on bg (his studio). Every card carries real, sourced
    content from the long-form; nothing is a designed text slide (M28, M40). A look-down switch shows a photo bare (its title
    belongs to its own line); while the label is up, a photo's title and a card's small source line wait (one text at a time)."""
    im = bg.copy(); e = rc["ev"]; k = rc["kind"]; fade = int(255 * min(1.0, max(0.0, lt) / 0.12))
    if k == "photo":
        ph = FX.load(rc["path"], "RGB"); z = 1.0 + 0.02 * min(lt, 4.0) / 2.5
        im = FX.fit_cover(ph, int(FW * z), int(SEAM * z)).convert("RGBA").crop((int(FW * (z - 1) / 2), int(SEAM * (z - 1) / 2), int(FW * (z - 1) / 2) + FW, int(SEAM * (z - 1) / 2) + SEAM))
        if e.get("title") and not (cover or label_up): _text(im, (FW / 2, 330), e["title"].upper(), _fit_size(e["title"].upper(), 104, FW - 140), YEL)
        return im
    if k == "doc":
        pg = e.get("page")
        if pg:   # the page's own pixels, only its highlighted words, cut out and stacked big on the paper (no retyping: read
            # back by OCR, R4's "'weapon'" came out "kneapon'", 11-04), the marker sweeping each line on his voice
            page = FX.load(asset_k(K, pg["img"]), "RGB"); gray = np.asarray(page.convert("L"))
            hl = pg.get("hl") or [[0, int(page.height * 0.45), page.width, int(page.height * 0.05)]]
            lines = []
            for x, y, w, h in hl:
                yy, hh = _line_of(gray, int(x), int(y), int(w), int(h))
                lines.append(page.crop((max(0, int(x) - 6), max(0, yy), min(page.width, int(x + w) + 6), min(page.height, yy + hh))))
            gh = max(8.0, float(np.median([l.height - 10 for l in lines]))); s = 56 / gh   # his words about 56 px high on a phone
            rows = []
            for i, l in enumerate(lines):   # a long line breaks at a word gap so the words can be big
                acc = 0
                for pc in _split(l, (FW - 200) / s): rows.append((pc, i, acc, l.width)); acc += pc.width
            s = min(s, (FW - 200) / max(pc.width for pc, *_ in rows), 320 / sum(pc.height for pc, *_ in rows))   # fits under a 2-line source
            at = rc["sub"].get("hl", 0.3); strips = []
            for pc, i, x0, lw in rows:   # the marker sweeps each highlighted line on his voice, one after another
                st = np.asarray(pc.resize((max(1, int(pc.width * s)), max(1, int(pc.height * s))), Image.LANCZOS)).copy()
                u = min(1.0, max(0.0, (lt - at - i * 0.35) / 0.45)); swept = min(pc.width, max(0.0, u * lw - x0))
                if swept > 0: st[:, :int(swept * s)] = np.minimum(st[:, :int(swept * s)], np.array(YEL, np.uint8))
                strips.append(Image.fromarray(st).convert("RGBA"))
            gap = int(10 * s); pw = max(x.width for x in strips) + 70; ph = sum(x.height for x in strips) + gap * (len(strips) - 1) + 56
            paper = Image.new("RGBA", (pw, ph), (252, 251, 247, 255)); yy = 28
            for x in strips: paper.alpha_composite(x, ((pw - x.width) // 2, yy)); yy += x.height + gap
            z = 1.0 + 0.015 * min(lt, 4.0); paper = paper.resize((int(pw * z), int(ph * z)), Image.LANCZOS)
            m = FX.rounded_mask(paper.width, paper.height, 18).point(lambda v: v * fade // 255)
            im.paste(paper, (int(FW / 2 - paper.width / 2), int(max(395, 600 - paper.height / 2))), m)   # below the source ("NOT A RULING")
            _head(im, " · ".join(x for x in (e.get("source"), e.get("source_sub")) if x), 290, fade)
            return im
        dc = e.get("doc") or {}; return quote(im, dc.get("text", ""), dc.get("hl", ""), dc.get("source", ""), lt, rc["sub"].get("hl", 0.3))
    if k == "study":
        st = e["study"] if isinstance(e["study"], dict) else json.loads(e["study"])
        head = f"{st.get('journal', '')} · {st.get('year', '')}".strip(" ·")
        if st.get("funder"): head += f" · funded by {st['funder']}"
        return quote(im, st.get("finding") or st.get("title", ""), st.get("hl", ""), head, lt, rc["sub"].get("hl", 0.4))
    if k == "quote": return quote(im, rc["text"], "", rc.get("credit", ""), lt, 0.3)   # GEBN's own title, "funded by Coca-Cola" on top
    if k == "count":
        if e.get("image") and os.path.exists(asset_k(K, e["image"])):
            ph = FX.fit_cover(FX.load(asset_k(K, e["image"]), "RGB"), FW, SEAM).convert("RGBA")
            ph = Image.blend(ph, Image.new("RGBA", ph.size, (28, 22, 18, 255)), 0.45); im = ph
        items = e.get("items", [])[:2]; n = len(items)
        for i, it in enumerate(items):
            at = rc["sub"].get(it[2], 0.0) if len(it) > 2 and it[2] in rc["sub"] else (0.0 if i == 0 else 0.8)
            tl = lt - at
            if tl < 0: continue
            y = (SEAM / 2 + 30) if n == 1 else (300 + i * 260); nm = _num(it[0])
            s = _count_str(nm[0], tl / 1.0, nm[1], nm[2], 0 if float(nm[0]).is_integer() else 1) if nm else str(it[0])
            _text(im, (FW / 2, y + (1 - FX.spring(tl)) * 30), s.upper(), _fit_size(s.upper(), 210 if n == 1 else 150, FW - 120), YEL if i == n - 1 else WHITE)
            for j, lab in enumerate(_wrap(str(it[1]).upper(), 40, FW - 160, "ExtraBold")[:2]):   # a long label wraps (D45 ran off)
                _text(im, (FW / 2, y + (120 if n == 1 else 92) + j * 46), lab, 40, WHITE, "ExtraBold", track=3, alpha=int(255 * min(1, tl / 0.15)))
        if not label_up: _source(im, e.get("source"))
        return im
    if k == "bars":
        bars = e.get("bars", [])[:4]; mx = max(b[1] for b in bars) or 1; ts = rc["sub"].get("bars") or [i * 0.3 for i in range(len(bars))]
        if e.get("title"): _text(im, (FW / 2, 290), e["title"].upper(), _fit_size(e["title"].upper(), 64, FW - 140), WHITE)
        top, row = 345, (SEAM - 150 - 345) / max(1, len(bars)); bh, ls = min(58, row * 0.45), min(42, row * 0.34)   # 4 rows fit (C69 overlapped)
        for i, b in enumerate(bars):
            tb = lt - (ts[i] if i < len(ts) else 0.0)
            if tb < 0: continue
            y = top + i * row; g = min(1.0, FX.ease(tb, 0.5)); wbar = (FW - 160 - 300) * b[1] / mx * g; col = YEL if b[1] == mx else WHITE
            _text(im, (80, y + ls / 2), str(b[0]).upper(), _fit_size(str(b[0]).upper(), int(ls), FW - 160, "ExtraBold"), WHITE, "ExtraBold", anchor="lm", track=2)
            d = ImageDraw.Draw(im); by = y + ls + 8; d.rounded_rectangle([80, by, 80 + max(wbar, 12), by + bh], 12, fill=col + (255,))
            v = str(b[2]).upper(); _text(im, (100 + wbar, by + bh / 2), v, _fit_size(v, int(bh * 1.15), FW - 100 - (100 + wbar)), col, anchor="lm")
        if not label_up: _source(im, e.get("source"))
        return im
    if k == "versus":
        items = e.get("items", [])[:2]; n = max(1, len(items)); cw = (FW - 120) // n
        pics = any(it[0] and os.path.exists(asset_k(K, it[0])) for it in items)
        if e.get("title"): _text(im, (FW / 2, 286), e["title"].upper(), _fit_size(e["title"].upper(), 60, FW - 140), WHITE)
        yb, size = (630, 96) if pics else (520, 170)   # with pictures: the 2-line label stays clear of the source at SEAM-120 (11-04 R1 MASA)   # with no pictures the two numbers carry the card, big and centred
        for i, it in enumerate(items):
            at = rc["sub"].get(it[3], 0.0) if len(it) > 3 and it[3] in rc["sub"] else 0.0; ti = lt - at
            if ti < 0: continue
            x = 60 + i * cw + cw / 2; sp = min(1.0, 0.8 + 0.2 * FX.spring(ti))
            if it[0] and os.path.exists(asset_k(K, it[0])):
                ph = FX.load(asset_k(K, it[0]), "RGB").copy(); ph.thumbnail((int((cw - 40) * sp), int(230 * sp)))
                m = FX.rounded_mask(ph.width, ph.height, 12); im.paste(ph.convert("RGBA"), (int(x - ph.width / 2), 345), m)
            big = str(it[1]).upper(); _text(im, (x, yb + (1 - sp) * 40), big, _fit_size(big, size, cw - 30), YEL if i == 0 else WHITE)
            ss, lg = (30, 34) if pics else (32, 38)
            pr = [q.strip() for q in str(it[2]).split(" · ")]
            sm = pr[:2] if len(pr) == 2 and all(FX.font(ss + 2, "ExtraBold").getlength(q.upper()) <= cw - 40 for q in pr) \
                else _wrap(str(it[2]), ss + 2, cw - 40, "ExtraBold")[:2]   # break at the " · " (no orphan "OZ", 11-04)
            for j, l in enumerate(sm): _text(im, (x, yb + size * 0.6 + j * lg), l.upper(), ss, (230, 230, 230), "ExtraBold", track=1)
        if n == 2: _text(im, (FW / 2, yb), "VS", 54, (200, 200, 200), "ExtraBold")
        if not label_up: _source(im, e.get("source"))
        return im
    return im


def asset_k(K, rel): return os.path.join(K["longform"], "hf", "assets", rel)


def quote(im, text, hl, head, lt, at):
    """The source's own words on his studio in white; as he reads the phrase, a yellow marker sweeps behind it and the swept
    words turn ink (11-04 pass: the highlighter follows his voice)."""
    fade = int(255 * min(1.0, max(0.0, lt) / 0.12))
    if head: _head(im, head, 290, fade)
    size = 64; lines = _wrap(text, size, FW - 160, "Black")
    while len(lines) > 6 and size > 40: size -= 4; lines = _wrap(text, size, FW - 160, "Black")
    lines = lines[:6]; lh = size * 1.18; y0 = 360 + (SEAM - 470 - len(lines) * lh) / 2
    f = FX.font(size, "Black"); hl_l = (hl or "").lower().strip(" .\"'"); flat = " ".join(lines).lower()
    a = flat.find(hl_l) if hl_l else -1; b = a + len(hl_l) if a >= 0 else -1
    u = min(1.0, max(0.0, (lt - at) / 0.6)); swept = a + (b - a) * u if a >= 0 else -1; pos = 0
    for i, l in enumerate(lines):
        y = y0 + i * lh; x = FW / 2 - f.getlength(l) / 2
        FX.shadow_text(im, (x, y), l, f, WHITE, anchor="lm", alpha=fade)
        s0, s1 = max(a, pos), min(swept, pos + len(l))
        if a >= 0 and s1 > s0:   # the swept part of the phrase on this line: marker behind, ink on top
            xa = x + f.getlength(l[:int(s0) - pos]); xm = x + f.getlength(l[:int(math.ceil(s1)) - pos])
            box = [int(xa - 6), int(y - size * 0.6), int(xm + 6), int(y + size * 0.52)]
            ImageDraw.Draw(im).rectangle(box, fill=YEL + (255,))
            ink = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(ink).text((x, y), l, font=f, fill=(20, 20, 20, 255), anchor="lm")
            m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rectangle(box, fill=255); im.paste(ink, (0, 0), Image.composite(ink.split()[3], m, m).point(lambda v: v))
        pos += len(l) + 1
    return im


def top_image(K, rc, sp, t, cam_panel, frame=None):
    """The top panel at reel time t: a video receipt's frame (decoded by the caller, or one decode here), or a card drawn on
    his studio."""
    if rc["kind"] == "video":
        return frame if frame is not None else one(top_cmd(rc, toff(rc, sp, t), 1))
    early = sp["t0"] < rc["t0"] - 0.05   # on before its own claim (frame 0, a look-down switch): shown finished, nothing pops later
    lt = (t - rc["t0"]) if not (sp.get("cover") or early) else 3.0 + (t - sp["t0"])
    return card(K, rc, lt, studio(cam_panel), cover=bool(sp.get("cover")), label_up=t < label_end(K))   # one text at a time: the label first


def label_end(K):
    """The label leaves at the first receipt change (11-04 pass: 2.5 s there), at most 5 s in."""
    sp = K["spans"]; first = next((s["t0"] for s in sp[1:] if s.get("rc") != sp[0].get("rc") or s["state"] != sp[0]["state"]), 5.0)
    return min(first, 5.0)


def overlays(K, im, t, sp):
    """Captions, the label, the receipt's source and a name, never on his face (brand.json: 60 px clear of his chin)."""
    st = sp["state"]
    if st == "split" and sp.get("rc"):
        rc = rc_by(K, sp["rc"]); cr = rc.get("credit")
        if cr and rc["kind"] in ("video", "photo") and rc.get("credit_y", CREDIT_Y) is not None:
            _text(im, (36, rc.get("credit_y", CREDIT_Y)), cr[:56], 32, WHITE, "ExtraBold", anchor="lm", track=1)
    label_up = bool(K.get("label")) and t < label_end(K)
    chin = ob_shot_at(K, t).get("chin", 1150) if st == "full" else 0
    if label_up:   # full frame, it goes under his chin (never on his face or cap) and the captions drop below it
        y = LABEL_SPLIT if st == "split" else min(max(chin + 100, 1180), 1380); words = K["label"].upper().split(); acc = K.get("accent", "").upper()
        size = _fit_size(" ".join(words), 104, FW - 120); f = FX.font(size, "Black"); x = FW / 2 - f.getlength(" ".join(words)) / 2
        for wd in words:
            FX.shadow_text(im, (x, y), wd, f, YEL if wd.strip("?!.,") in {q.strip("?!.,") for q in acc.split()} else WHITE, anchor="lm"); x += f.getlength(wd + " ")
    if st == "split":   # a name types on the first time he says it, unless the label (which already says it) is still up
        for nm in K.get("names", []):
            w0 = next((w for w in K["words"] if not w["clip"] and w["w"].lower().strip(".,!?'\"").startswith(nm["on"].lower())), None)
            if w0 and w0["s"] >= label_end(K) and w0["s"] - 0.1 <= t < w0["s"] + 2.4:
                k = int(len(nm["name"]) * min(1.0, (t - w0["s"] + 0.1) / 0.4))
                _text(im, (FW / 2, 760), nm["name"].upper()[:max(1, k)], 64, WHITE, "Black", track=3)
    words = [w for w in K["words"] if w["clip"] == (st == "clip")]
    if st == "split": y = CAP_SPLIT
    elif st == "clip": y = CAP_CLIP
    else: y = min(max(chin + 92, 1250), 1460) if not label_up else min(max(chin + 100, 1180), 1380) + 112
    FX.captions(im, t, words, y=y, n=3, size=64)


def compose(K, t, cam, clip=None, top=None, prev_top=None):
    """One finished frame at reel time t. cam: his camera (1080x1920 full, or the 1080x1044 panel in the split); clip: a clip's
    1080x1920 frame; top: the receipt panel (1080x876); prev_top: the previous receipt's last panel (for the moves)."""
    sp = span_at(K, t); st, dt, mv = sp["state"], t - sp["t0"], sp.get("move", "cut")
    if st == "clip": im = clip.copy()
    elif st == "full":
        im = cam.copy()
        if mv == "slide" and prev_top is not None and dt < SLIDE: _paste_y(im, prev_top, int(SEAM * FX.slide_up(dt)) - SEAM)
    else:
        im = Image.new("RGBA", (FW, FH)); im.paste(studio(cam), (0, 0)); im.paste(cam, (0, SEAM))
        if mv == "drop" and dt < DROP: _paste_y(im, top, int(SEAM * FX.drop_in(dt)) - SEAM)
        elif mv == "push" and prev_top is not None and dt < MOVE:
            u = FX.ease(dt, MOVE); a = prev_top.crop((int(FW * u), 0, FW, SEAM)); b = top.crop((0, 0, int(FW * u) or 1, SEAM))
            if 0.05 < u < 0.95: a = a.filter(ImageFilter.BoxBlur(10)); b = b.filter(ImageFilter.BoxBlur(10))
            im.paste(a, (0, 0)); im.paste(b, (FW - b.width, 0))
        elif mv == "blur" and prev_top is not None and dt < MOVE:
            u = dt / MOVE; r = 22 * (1 - abs(2 * u - 1))
            src = prev_top if u < 0.5 else top; im.paste(src.filter(ImageFilter.GaussianBlur(r)) if r > 0.5 else src, (0, 0))
        else: im.paste(top, (0, 0))
    overlays(K, im, t, sp)
    return im


def _paste_y(im, top, y):
    if y <= -SEAM: return
    if y < 0: im.paste(top.crop((0, -y, FW, SEAM)), (0, 0))
    else: im.paste(top, (0, y))


def still(K, t):
    """One frame at reel time t, the render's way (single-frame decodes)."""
    sp = span_at(K, t)
    if sp["state"] == "clip":
        return compose(K, t, None, clip=one(clip_cmd(K, shot_at(K, t), t, 1)))
    s = ob_shot_at(K, t); full = sp["state"] == "full"
    cam = one(cam_cmd(K, s, t, 1, full))
    top = prev = None
    if sp["state"] == "split":
        rc = rc_by(K, sp["rc"]); top = top_image(K, rc, sp, t, cam)
    i = K["spans"].index(sp); ps = K["spans"][i - 1] if i else None
    if ps and ps["state"] == "split" and sp.get("move") in ("slide", "push", "blur") and t - sp["t0"] < max(SLIDE, MOVE):
        prev = prev_top(K, ps)
    return compose(K, t, cam, top=top, prev_top=prev)


def prev_top(K, ps):
    """The panel a span ended on (for the move out of it)."""
    t = ps["t1"] - 1 / K["fps"]; rc = rc_by(K, ps["rc"]); s = ob_shot_at(K, t)
    return top_image(K, rc, ps, t, one(cam_cmd(K, s, t, 1, False)))


# ---------------------------------------------------------------------------------------------------- render
def segments(K, f0, f1):
    """Frames [f0, f1) as runs with one span and one camera or clip shot: (fa, fb, span, shot). Each frame's span and shot are
    the ones compose sees at that frame's own time, so a run never mixes states (11-04: a rounded span edge put a split-size
    camera frame into a full frame, and every later frame of that chunk came out wrapped)."""
    fps = K["fps"]; out = []
    for f in range(f0, f1):
        t = f / fps; sp = span_at(K, t); sh = shot_at(K, t) if sp["state"] == "clip" else ob_shot_at(K, t)
        if out and out[-1][2] is sp and out[-1][3] is sh: out[-1][1] = f + 1
        else: out.append([f, f + 1, sp, sh])
    return [tuple(x) for x in out]


def render_chunk(K, f0, f1, out):
    """Frames [f0, f1) of the reel to an H.264 file (one of the render's parallel workers on the Mac mini)."""
    fps = K["fps"]; n_all = f1 - f0
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FW}x{FH}",
                            "-r", "30000/1001", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                            "-profile:v", "high", "-level", "4.2", "-x264-params", "keyint=60:min-keyint=1:scenecut=40:threads=4",
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-an", out], stdin=subprocess.PIPE)
    k = 0; prev_cache = {}
    for a, b, sp, sh in segments(K, f0, f1):
        n = b - a; t0 = a / fps
        if sp["state"] == "clip":
            src = frames_of(*clip_cmd(K, sh, t0, n), n); tops = None; cams = None
        else:
            cams = frames_of(*cam_cmd(K, sh, t0, n, sp["state"] == "full"), n); src = None
            rc = rc_by(K, sp["rc"]) if sp["state"] == "split" else None
            tops = frames_of(*top_cmd(rc, toff(rc, sp, t0), n), n) if rc and rc["kind"] == "video" else None
        i = K["spans"].index(sp); ps = K["spans"][i - 1] if i else None; prev = None
        if ps and ps["state"] == "split" and sp.get("move") in ("slide", "push", "blur") and t0 - sp["t0"] < max(SLIDE, MOVE):
            key = (ps["t0"], ps["rc"]); prev = prev_cache.get(key) or prev_cache.setdefault(key, prev_top(K, ps))
        for j in range(n):
            t = (a + j) / fps
            if sp["state"] == "clip": im = compose(K, t, None, clip=next(src))
            else:
                cam = next(cams); top = None
                if sp["state"] == "split":
                    top = next(tops) if tops is not None else top_image(K, rc, sp, t, cam)
                im = compose(K, t, cam, top=top, prev_top=prev)
            if im.size != (FW, FH): raise RuntimeError(f"frame {a + j}: {im.size}, not {FW}x{FH}")
            enc.stdin.write(im.convert("RGB").tobytes()); k += 1
    enc.stdin.close(); enc.wait()
    if enc.returncode or k != n_all: raise RuntimeError(f"chunk {out}: {k}/{n_all} frames, exit {enc.returncode}")


def render(K, plan_path, out_video, workers=6, scratch=None, log=print):
    """The whole reel's picture: frames split at span edges into `workers` chunks rendered side by side (18 cores on the
    Mac mini: one process composes ~18 fps), then joined without re-encoding."""
    nf = K["frames"]; segs = segments(K, 0, nf); goal = nf / max(1, workers); cuts, acc = [0], 0
    for a, b, sp, sh in segs:
        acc += b - a
        if acc >= goal and b < nf: cuts.append(b); acc = 0
    cuts.append(nf); cuts = sorted(set(cuts))
    scratch = scratch or os.path.join(os.path.expanduser("~/ob-scratch"), "ytclip", K["reel"]); os.makedirs(scratch, exist_ok=True)
    parts, procs = [], []
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        p = os.path.join(scratch, f"chunk_{i:02d}.mp4"); parts.append(p)
        procs.append(subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "chunk", plan_path, str(a), str(b), p],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    bad = []
    for pr in procs:
        o, e = pr.communicate()
        if pr.returncode: bad.append(e[-800:])
    if bad: raise RuntimeError("render chunks failed:\n" + "\n".join(bad))
    lst = os.path.join(scratch, "concat.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_video])
    log(f"   picture: {nf} frames in {len(parts)} chunks")


def cam_map(K):
    """Every piece of his voice with its picture (all of them: he is on screen while he talks), for the gate's lip-sync check."""
    off = K.get("camera_offset", 0.0)
    return [(K["camera"], round(s["a"] - off, 4), round(s["b"] - off, 4), round(s["t0"], 4)) for s in K["shots"] if s["kind"] == "ob"]


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "chunk":
        K = json.load(open(a[1])); render_chunk(K, int(a[2]), int(a[3]), a[4])
    else: print(__doc__)
