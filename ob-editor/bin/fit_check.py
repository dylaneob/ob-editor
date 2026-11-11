#!/usr/bin/env python3
"""Fill-the-frame gate (general version of C4367's story/fit_cards.py; OB 2026-10-20: "so much black space").

bin/stage.py scales each full-frame card's content up to fill the safe area (x 6-94 %, y 9-91 %: 230-3610 by 195-1965 px of 3840x2160),
centred, capped at 1.8x, from WORK/story/fit.json. That file is measured on the card mocks, so it goes stale when a mock changes
(PRESET: "re-run fit_cards.py after adding images ... pushes content off the edge"). This check re-measures every card with
bin/fit_measure.js (one headless Chrome over hf/compositions/ID.mock.html, nothing rendered) and compares it with the stored fit:

  python3 -I fit_check.py WORK [--stored-only] [--write [PATH]] [--ids ID,ID] [--events FILE]

Fails (exit 1) when, with the stored fit applied to the card as it is NOW,
  overflow   the fit scales the card up (s > 1) and its content then reaches more than 40 px outside the safe area (cut off or on the
             edge). A card that already fills or is bigger than the safe area gets no scale-up (the fit never shrinks), so a full-bleed
             drawn scene, like C4367's find and detector cards, is left alone;
  underfill  the stored fit leaves 15 % or more of the scale-up undone (the card still has black space).
Warns (not counted) when the stored fit differs from a fresh one by more than 3 % scale or 30 px but both rules above still hold.
Cards checked: the types that fill the frame by design (math, checklist, timeline, detector, coins, dose, find, slider, num, versus,
disclaimer, scissors) and full docs; not inlays, a num card with a photo, or a doc with a real PDF `page` (a page bigger than the frame
pushes in on its own; measuring it would scale up its source tag). A card without a mock file is listed and skipped.
  --stored-only  no browser: only checks fit.json against the events (stale ids, boxes) and its age against the mocks. Fast, weaker.
  --write [PATH] after measuring, write a fresh fit file (default WORK/story/fit.json; same format fit_cards.py wrote; an existing file
                 is first copied to fit.json.DATE-prewrite). The fix for a FAIL. Never done by default: the check itself reads only.
Exit codes: 0 clean, 1 overflow or underfill, 2 missing input or the measure failed.
"""
import argparse, datetime, json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_lib as G

SX0, SX1, SY0, SY1, CAP = 230, 3610, 195, 1965, 1.8          # the safe area and the cap, as story/fit_cards.py
TYPES = {"math", "checklist", "timeline", "detector", "coins", "dose", "find", "slider", "num", "versus", "disclaimer", "doc", "scissors", "title_x"}
OVER_PX, UNDER = 40, 1.15


def candidates(events):
    out, skipped = [], []
    for e in events:
        if e["type"] not in TYPES or e.get("inlay"): continue
        if e["type"] == "doc" and not e.get("full"): continue          # a side doc is not a full-frame card
        if e["type"] == "doc" and e.get("page"): skipped.append((e["id"], "doc with a real page")); continue
        if e["type"] == "num" and e.get("image"): skipped.append((e["id"], "num with a photo fills already")); continue
        out.append(e)
    return out, skipped


def fresh_fit(e, bx):
    """the fit story/fit_cards.py would store for this measured box (or None when the card already fills and is centred)"""
    x0, y0, x1, y1 = bx; w, h = x1 - x0, y1 - y0
    s = min((SX1 - SX0) / w, (SY1 - SY0) / h, CAP)
    if e["type"] == "doc": s = min(s / 1.07, CAP)       # the document pushes in 7 % on its own
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if s < 1.06 and abs(cy - 1080) < 80 and abs(cx - 1920) < 120: return None
    s = max(min(s, CAP), 1.0)
    return {"s": round(s, 4), "tx": round(1920 - s * cx, 1), "ty": round(1080 - s * cy, 1), "box": [round(v) for v in bx]}


def apply(f, bx):
    """the box after stage.py applies a stored fit (it only applies s > 1)"""
    if not f or f.get("s", 1) <= 1.0: return list(bx)
    s, tx, ty = f["s"], f["tx"], f["ty"]
    return [s * bx[0] + tx, s * bx[1] + ty, s * bx[2] + tx, s * bx[3] + ty]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work")
    ap.add_argument("--stored-only", action="store_true"); ap.add_argument("--write", nargs="?", const="", default=None, metavar="PATH")
    ap.add_argument("--ids", default=None); ap.add_argument("--events", default=None)
    a = ap.parse_args(); W = a.work.rstrip("/")
    if a.write is not None and (a.ids or a.stored_only):
        print("fit_check: --write measures every card; do not combine it with --ids or --stored-only", file=sys.stderr); return 2
    evp = a.events or f"{W}/events_resolved.json"; fitp = f"{W}/story/fit.json"
    try:
        events = json.load(open(evp))["events"]
        stored = json.load(open(fitp)) if os.path.exists(fitp) else {}
    except (OSError, ValueError, KeyError) as e:
        print(f"fit_check: cannot read inputs in {W}: {e}", file=sys.stderr); return 2
    cards, skipped = candidates(events)
    if a.ids: cards = [e for e in cards if e["id"] in set(a.ids.split(","))]
    mock = lambda i: f"{W}/hf/compositions/{i}.mock.html"
    have = [e for e in cards if os.path.exists(mock(e["id"]))]; nomock = [e["id"] for e in cards if not os.path.exists(mock(e["id"]))]
    print(f"fit check on {W}: {len(cards)} cards to fit, {len(have)} with a mock, stored fits {len(stored)}"
          + (f"; skipped: {', '.join(f'{i} ({why})' for i, why in skipped)}" if skipped else ""))
    if nomock: print(f"  no mock file, not checked: {', '.join(nomock)}")
    fails, warns = [], []

    if a.stored_only:
        ids = {e["id"] for e in events}
        for i in stored:
            if i not in ids: warns.append(f"{i}: in fit.json but no such event any more")
        if not stored and have: fails.append(f"no story/fit.json but {len(have)} cards fill the frame by design: run fit_check.py WORK --write")
        for i, f in stored.items():
            b = apply(f, f["box"])
            over = max(SX0 - b[0], b[2] - SX1, SY0 - b[1], b[3] - SY1)
            if f.get("s", 1) > 1.0 and over > OVER_PX: fails.append(f"{i}: the stored fit puts the content {over:.0f} px outside the safe area")
        if os.path.exists(fitp):
            fm = os.path.getmtime(fitp); newer = [e["id"] for e in have if os.path.getmtime(mock(e["id"])) > fm + 1]
            if newer: warns.append(f"fit.json is older than {len(newer)} mocks ({', '.join(newer[:8])}{'...' if len(newer) > 8 else ''}): "
                                   f"measure again (drop --stored-only)")
    else:
        if not have: print("  nothing to measure"); boxes = {}
        else:
            r = subprocess.run(["node", os.path.join(G.HERE, "fit_measure.js"), f"{W}/hf", evp] + [e["id"] for e in have], capture_output=True, text=True, timeout=900)
            if r.returncode or not r.stdout.strip():
                print(f"fit_check: fit_measure.js failed: {(r.stderr or r.stdout)[-1500:]}", file=sys.stderr); return 2
            boxes = json.loads(r.stdout.strip().splitlines()[-1])
        fresh = {}
        for e in have:
            bx = boxes.get(e["id"])
            if not bx: continue
            fr_ = fresh_fit(e, bx); st = stored.get(e["id"])
            if fr_: fresh[e["id"]] = fr_
            eff = apply(st, bx)
            over = max(SX0 - eff[0], eff[2] - SX1, SY0 - eff[1], eff[3] - SY1)
            s_have = st["s"] if st and st.get("s", 1) > 1.0 else 1.0; s_want = fr_["s"] if fr_ else 1.0
            if s_have > 1.0 and over > OVER_PX:
                fails.append(f"overflow  {e['id']} ({e['type']}): content reaches {over:.0f} px outside the safe area"
                             + (f" with the stored fit x{s_have:.2f} (fresh x{s_want:.2f})" if st else " and has no fit")
                             + (f"; stored box {st['box']}, measured {[round(v) for v in bx]}" if st else ""))
            elif s_want / s_have >= UNDER:
                fails.append(f"underfill {e['id']} ({e['type']}): stored x{s_have:.2f}, a fresh fit is x{s_want:.2f} (black space left)"
                             + ("" if st else "; no stored fit"))
            elif max(s_have, s_want) > 1.0 and (abs(s_want - s_have) > 0.03 or (st and fr_ and (abs(fr_["tx"] - st["tx"]) > 30
                                                                                                 or abs(fr_["ty"] - st["ty"]) > 30))):
                warns.append(f"stale     {e['id']} ({e['type']}): stored x{s_have:.2f} vs fresh x{s_want:.2f}, still inside the safe area")
        if a.write is not None:
            out = a.write or fitp
            if os.path.exists(out):   # keep the old file: fit.json.DATE-prewrite (never overwritten, never deleted)
                bak = f"{out}.{datetime.date.today().isoformat()}-prewrite"
                if not os.path.exists(bak): shutil.copy2(out, bak); print(f"  old file kept as {bak}")
            json.dump(fresh, open(out, "w"), indent=1)
            print(f"  wrote {len(fresh)} fits to {out}")
    for w in warns: print("warn " + w)
    for f in fails: print("FIT " + f)
    print(f"fit_check: {'FAIL' if fails else 'OK'}: {len(fails)} problem(s)" + (f", {len(warns)} warning(s)" if warns else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
