#!/usr/bin/env python3
"""Quote cards that clear OB's face over the whole shot (C4395 10-28: the facequote text block, 1300 px wide 150 px from the
edge, was placed from one still; when he leaned toward the text its first letters touched his cheek).

  python3 -I face_clear.py WORK_DIR --ids M326,M615 [--margin 80] [--write]   measure, and with --write narrow those cards
  python3 -I face_clear.py WORK_DIR --refit [--ids ...] [--write]            re-fit the font of stored cards (widths kept)
  python3 -I face_clear.py WORK_DIR --reapply                                re-apply story/face_clear.json after a rebuild

For each card: his face box (Apple Vision, bin/faces) on its bare A-roll (hf/assets/aroll/ID.mp4) at 15 fps (8 fps before 2026-11-03); the block's inner
edge goes --margin px (4K) past the furthest his face reaches during the card (side R: his right edge; side L: his left), so
"w" = 3840 - 150 - reach - margin (side R). The text stays right/left-aligned. A narrower block with the same font rewraps
(C4395 v2, 10-29: 12 of 22 cards broke badly, a lone ".", "out- / exercise", "500 / lb"), so the card also gets "size": the
largest font that keeps the approved line breaks (the ones at its old width and font), measured in Chrome by fq_fit.js.
--write stores {"w", "size", "w0", "fs0"} in story/face_clear.json and sets "w" and "size" in events_resolved.json; build.sh
runs --reapply after snap_ends.py so a rebuild keeps them (re-run --write if a stored card's words change). Which cards:
overlay_touch.py lists them (FAIL or WARN) after a render.
"""
import json, os, subprocess, sys, tempfile

BIN = os.path.dirname(os.path.abspath(__file__)); W4, EDGE, BW = 3840, 150, 1300   # cards.py facequote: right/left:150px, default w 1300
sys.path.insert(0, BIN); import cards


def font(e, bw):
    """The card's font at block width bw, as cards.py facequote sizes it (an explicit "size" wins; a block taller than 1480 shrinks)."""
    lines = e["text"].split("\n"); L = max(len(x) for x in lines); ul = e.get("underline") or ""; CW = 0.33
    unit = max([len(w) for x in lines for w in x.split()] + [len(ul)])
    fs = e.get("size") or int(min(250 if L <= 16 else 220 if L <= 26 else 195, 0.9 * bw / (CW * max(unit, 1))))
    bh = sum(max(1, -(-int(len(x) * CW * fs) // bw)) for x in lines) * fs * 1.04 + (96 if e.get("kicker") else 0)
    return int(fs * 1480 / bh) if bh > 1480 else fs


def fit(work, todo):
    """todo: [(event, w0, fs0, w)]. The largest font at w that keeps the line breaks the card had at (w0, fs0)."""
    job = {"font": f"{work}/hf/assets/fonts/DINCondensed-Bold.ttf",
           "cards": [{"id": e["id"], "rows": [cards.underline(x, e.get("underline")) for x in e["text"].split("\n")], "fs0": fs0, "w0": w0, "w": w,
                      "fsNow": font(dict(e, w=w), w)} for e, w0, fs0, w in todo]}
    out = subprocess.run(["node", os.path.join(BIN, "fq_fit.js")], input=json.dumps(job), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def reach(work, e):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", f"{work}/hf/assets/aroll/{e['id']}.mp4", "-vf", "fps=15,scale=960:540", "-q:v", "3", f"{td}/%04d.jpg"], check=True)
        js = sorted(f for f in os.listdir(td) if f.endswith(".jpg"))
        out = subprocess.run([os.path.join(BIN, "faces")] + [f"{td}/{f}" for f in js], capture_output=True, text=True).stdout.splitlines()
    xs = [[4 * int(float(v)) for v in ln.split(" ", 1)[1].split("|")[0].split()] for ln in out if len(ln.split(" ", 1)) == 2 and not ln.split(" ", 1)[1].startswith(("none", "error"))]
    if not xs: return None
    return max(b[2] for b in xs) if e.get("side", "L") == "R" else min(b[0] for b in xs)


def apply(work, store):
    p = f"{work}/events_resolved.json"; R = json.load(open(p)); n = 0
    for e in R["events"]:
        s = store.get(e["id"])
        if s is None: continue
        new = {k: v for k, v in (s if isinstance(s, dict) else {"w": s}).items() if k in ("w", "size")}   # before 10-29 the store held the width alone
        if any(e.get(k) != v for k, v in new.items()): e.update(new); n += 1
    open(p + ".tmp", "w").write(json.dumps(R, indent=1)); os.replace(p + ".tmp", p); return n


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    work = a[0]; opt = lambda k: a[a.index(k) + 1] if k in a else None; store = f"{work}/story/face_clear.json"
    S = json.load(open(store)) if os.path.exists(store) else {}
    if "--reapply" in a:
        print(f"face_clear: {apply(work, S)} of {len(S)} quote cards re-applied (width and font)"); return
    ids = [i for i in (opt("--ids") or "").split(",") if i] or (list(S) if "--refit" in a else []); margin = int(opt("--margin") or 80)
    E = {e["id"]: e for e in json.load(open(f"{work}/events_resolved.json"))["events"]}
    todo = []
    for i in ids:
        e = E[i]; s = S.get(i); s = {"w": s} if isinstance(s, int) else s
        if e["type"] != "facequote": print(f"  {i}: {e['type']}, not a quote card: move or retime it by hand"); continue
        # the approved layout: as stored; or the default block (a width-only entry from before 10-29); or the card as it is now
        w0, fs0 = (s["w0"], s["fs0"]) if s and "w0" in s else (BW, font(dict(e, w=BW), BW)) if s else (e.get("w", BW), font(e, e.get("w", BW)))
        if "--refit" in a: new = s["w"] if s else e.get("w", BW)
        else:
            r = reach(work, e)
            if r is None: print(f"  {i}: no face found on its A-roll"); continue
            side = e.get("side", "L"); allowed = (W4 - EDGE - r - margin) if side == "R" else (r - margin - EDGE)
            new = min(e.get("w", BW), allowed); print(f"  {i} side {side}: his face reaches x={r}; block {e.get('w', BW)} -> {new} px")
        todo.append((e, w0, fs0, new))
    F = fit(work, [t for t in todo if t[3] < t[1]]) if todo else {}
    for e, w0, fs0, new in todo:
        f = F.get(e["id"]); S[e["id"]] = {"w": new, "size": f["fs"], "w0": w0, "fs0": fs0} if f else {"w": new}
        if f: print(f"  {e['id']}: block {w0} -> {new} px, font {fs0} -> {f['fs']}" + ("" if f["kept"] else " (proportional: no larger size kept the breaks)")
                    + f"\n      approved {' / '.join(' | '.join(r) for r in f['lines'])}\n      was      {' / '.join(' | '.join(r) for r in f['now'])}")
    if "--write" in a:
        open(store + ".tmp", "w").write(json.dumps(S, indent=1)); os.replace(store + ".tmp", store)
        print(f"face_clear: {apply(work, S)} cards updated in events_resolved.json; widths and fonts kept in story/face_clear.json")


if __name__ == "__main__":
    main()
