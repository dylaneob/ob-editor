#!/usr/bin/env python3
"""B-roll and news clip edge check (C4367, 2026-10-20: "downloads hide dissolves and 1-3 frame shot changes at the edges"). Report only.

For every footage window the edit uses, looks 0.4 s either side of the in point and the out point in the SOURCE file for a shot change:
a hard cut, or a dissolve (told from a pan or a zoom by its histogram change and by its middle frame being the average of its ends;
scene scores missed dissolves). It counts the frames of the other shot that the window would still contain (an input -ss keeps the
frames at or after it; the window ends before its out point):
  INSIDE  one or more frames of the other shot are inside the window: the clip opens (or ends) on a flash (dissolves: 3+ frames).
  EDGE    none yet, but the change is within half a frame of the in/out point (or catches 1-2 frames of a dissolve), so rounding in the
          prep can let a frame of the other shot slip in.
  near    a change within the margin and clear of the window (listed with --all).
Windows come from WORK/story/broll.json {"broll": [{"id", "src", "in", "out"}]} (src absolute or relative to WORK) and
WORK/story/clips.json {"clips": [{"id", "file", "in", "out"}]} (file = a stem under WORK/clips/dl*/; the finished cut is
snap_in/snap_out from story/clips_prepped.json when present). Holds without a file are skipped.
Suggested times are in seconds of the source file and sit half a frame before the cut (an input -ss keeps frames at or after it, so
the in point then starts on the first frame of the shot and an out point ends on the last frame before the cut); for a dissolve, half
a frame after its end (in) or before its start (out).

  python3 -I broll_edges.py WORK [--margin 0.4] [--ids ID,ID] [--all] [--json OUT.json]

Reads only: ffmpeg on 1.5 s windows at -threads 2, about 0.5 s per edge (more while other renders run), never a full decode.
Exit codes: 0 always when it ran (report only), 2 when there is no window list or no ffmpeg.
"""
import argparse, glob, json, os, re, subprocess, sys
import numpy as np

FFMPEG = "/opt/homebrew/bin/ffmpeg"
VID = (".mp4", ".mov", ".mkv", ".webm", ".m4v")
TW, TH = 160, 90


def grab(src, t0, t1):
    """frames of src between t0 and t1 (source seconds) as (times, [n, TH, TW] float32 gray); input -ss is frame accurate"""
    r = subprocess.run([FFMPEG, "-nostdin", "-loglevel", "info", "-threads", "2", "-copyts", "-ss", f"{max(0.0, t0):.3f}", "-t", f"{t1 - max(0.0, t0):.3f}",
                        "-i", src, "-an", "-vf", f"showinfo,scale={TW}:{TH}:flags=area,format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, timeout=180)
    times = [float(x) for x in re.findall(rb"pts_time:(-?[\d.]+)", r.stderr)]
    n = min(len(r.stdout) // (TW * TH), len(times))
    return np.array(times[:n]), np.frombuffer(r.stdout[:n * TW * TH], np.uint8).reshape(n, TH, TW).astype(np.float32) if n else np.zeros((0, TH, TW), np.float32)


def shot_changes(times, fr):
    """[(kind, a, b)] by frame differences. 'cut': a = first frame after the first jump, b = first frame after the last jump (b > a is
    a flash of 1-3 frames of another shot); 'dissolve': the span of the blend"""
    n = len(times)
    if n < 6: return []
    d1 = np.abs(fr[1:] - fr[:-1]).mean(axis=(1, 2)) / 255.0
    base = float(np.median(d1)); thr = max(0.07, 4.0 * base)
    out, k = [], 0
    while k < len(d1):
        if d1[k] >= thr:
            j = k
            while j + 1 < len(d1) and d1[j + 1] >= thr and j + 1 - k <= 3: j += 1
            out.append(("cut", float(times[k + 1]), float(times[j + 1]))); k = j + 1
        else: k += 1
    # dissolves: a steady blend shows as a change between frames m apart (about 0.25 s) that is the SUM of the small frame-to-frame
    # changes (a pan or a person moving saturates instead), with no single big jump in it
    m = max(4, int(round(0.25 / max(np.median(np.diff(times)), 1e-3))))
    if n > m + 2:
        dm = np.abs(fr[m:] - fr[:-m]).mean(axis=(1, 2)) / 255.0
        thr_dm = max(0.09, 2.5 * float(np.percentile(dm, 25))); base1 = float(np.median(d1)); i = 0
        while i < len(dm):
            if dm[i] < thr_dm: i += 1; continue
            j = i
            while j + 1 < len(dm) and dm[j + 1] >= thr_dm: j += 1
            pk = i + int(np.argmax(dm[i:j + 1])); peak = float(dm[pk]); i0 = i1 = pk
            while i0 - 1 >= i and dm[i0 - 1] >= 0.8 * peak: i0 -= 1
            while i1 + 1 <= j and dm[i1 + 1] >= 0.8 * peak: i1 += 1
            seg = d1[i0:min(i1 + m, len(d1))]; span_frames = i1 - i0 + m
            ok = len(seg) and seg.max() < 0.6 * peak and np.clip(seg - base1, 0, None).sum() <= 1.35 * peak * span_frames / m
            a_, b_ = i0, min(i1 + m, n - 1); t0, t1 = float(times[a_]), float(times[b_])
            if ok:   # a real blend changes the picture (histogram), and its middle frame is the average of its ends; a slow zoom or a pan is the same scene
                ha, hb = (np.histogram(fr[k], bins=32, range=(0, 256))[0] / fr[k].size for k in (a_, b_))
                dab = float(np.abs(fr[b_] - fr[a_]).mean()) / 255.0; c_ = (a_ + b_) // 2
                err = float(np.abs(fr[c_] - 0.5 * (fr[a_] + fr[b_])).mean()) / 255.0
                ok = 0.5 * float(np.abs(ha - hb).sum()) >= 0.30 and err / max(dab, 1e-6) <= 0.30
            if ok and not any(t0 - 0.05 <= c[1] <= t1 + 0.05 for c in out if c[0] == "cut"): out.append(("dissolve", t0, t1))
            i = j + 1
    return sorted(out, key=lambda c: c[1])


def windows(work):
    w, prepped = [], {}
    pp = f"{work}/story/clips_prepped.json"
    if os.path.exists(pp):
        for c in json.load(open(pp)).get("clips", []): prepped[c["id"]] = c
    p = f"{work}/story/broll.json"
    if os.path.exists(p):
        for b in json.load(open(p)).get("broll", []):
            src = b["src"] if b["src"].startswith("/") else f"{work}/{b['src']}"
            w.append({"id": b["id"], "src": src, "in": b["in"], "out": b["out"], "list": "broll.json"})
    p = f"{work}/story/clips.json"
    if os.path.exists(p):
        for c in json.load(open(p)).get("clips", []):
            if not c.get("file"): continue
            hit = [f for d in sorted(glob.glob(f"{work}/clips/dl*")) for f in glob.glob(f"{d}/{c['file']}.*") if f.lower().endswith(VID)]
            pc = prepped.get(c["id"], {})
            w.append({"id": c["id"], "src": hit[0] if hit else f"{work}/clips/dl/{c['file']}.mp4",
                      "in": pc.get("snap_in", c["in"]), "out": pc.get("snap_out", c["out"]), "list": "clips.json"})
    return w


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work"); ap.add_argument("--margin", type=float, default=0.4); ap.add_argument("--ids", default=None)
    ap.add_argument("--all", action="store_true"); ap.add_argument("--json", default=None)
    a = ap.parse_args(); W = a.work.rstrip("/")
    if not os.path.exists(FFMPEG): print("broll_edges: no ffmpeg at " + FFMPEG, file=sys.stderr); return 2
    wins = windows(W)
    if a.ids: wins = [x for x in wins if x["id"] in set(a.ids.split(","))]
    if not wins: print(f"broll_edges: no windows (story/broll.json or story/clips.json) in {W}", file=sys.stderr); return 2
    rows, nflag, missing = [], 0, []
    print(f"broll edge check on {W}: {len(wins)} windows, margin {a.margin:g} s")
    for x in wins:
        if not os.path.exists(x["src"]): missing.append(x["id"]); continue
        notes, fd = [], 1 / 29.97
        for edge, t in (("IN", x["in"]), ("OUT", x["out"])):
            times, fr = grab(x["src"], t - a.margin - 0.3, t + a.margin + 0.3)
            if len(times) > 3: fd = float(np.median(np.diff(times)))
            for kind, c0, c1 in shot_changes(times, fr):
                # frames of the other shot that the window keeps: IN keeps frames >= t, so those before the clean shot starts (c1);
                # OUT keeps frames < t, so those from the change on (c0)
                if edge == "IN":
                    foreign = [tt for tt in times if t - 1e-4 <= tt < c1 - 1e-4]
                    gap = 0 if foreign else ((t - float(max([tt for tt in times if tt < c0] or [c0 - fd]))) if kind == "cut" else t - c1)
                else:
                    foreign = [tt for tt in times if c0 - 1e-4 <= tt < t - 1e-4]; gap = 0 if foreign else c0 - t
                if kind == "cut":
                    if abs((c0 - t)) > a.margin and abs(c1 - t) > a.margin: continue
                    what = f"cut at {c0:.3f} ({c0 - t:+.2f} s from {edge.lower()}" + (f", a {c1 - c0 + fd:.2f} s flash in the cut" if c1 > c0 else "") + ")"
                else:
                    if (edge == "IN" and not (c1 > t - a.margin and c0 < t + a.margin)) or (edge == "OUT" and not (c0 < t + a.margin and c1 > t - a.margin)): continue
                    what = f"dissolve {c0:.3f}-{c1:.3f} ({c0 - t:+.2f} s from {edge.lower()})"
                if foreign and (kind == "cut" or len(foreign) >= 3): sev, what = "INSIDE", what + f": {len(foreign)} frame(s), {len(foreign) * fd:.2f} s of the other shot kept"
                elif foreign: sev, what = "EDGE", what + f": the {edge.lower()} frame(s) catch {len(foreign)} frame(s) of the blend"
                elif gap < 0.5 * fd: sev, what = "EDGE", what + ": within half a frame, one frame can slip in"
                else: sev = "near"
                if kind == "cut": sug = round(c1 - 0.5 * fd, 3) if edge == "IN" else round(c0 - 0.5 * fd, 3)
                else: sug = round(c1 + 0.5 * fd, 3) if edge == "IN" else round(c0 - 0.5 * fd, 3)
                notes.append({"edge": edge, "sev": sev, "what": what, "at": round(t, 3), "suggest": sug if sev != "near" else None, "frames": len(foreign)})
        bad = [n for n in notes if n["sev"] != "near"]
        nflag += 1 if bad else 0
        rec = dict(x, notes=notes, flagged=bool(bad)); rows.append(rec)
        if bad or (a.all and notes):
            new_in = next((n["suggest"] for n in notes if n["edge"] == "IN" and n["suggest"] is not None), x["in"])
            new_out = next((n["suggest"] for n in notes if n["edge"] == "OUT" and n["suggest"] is not None), x["out"])
            print(f"{x['id']:16s} {os.path.basename(x['src'])[:38]:38s} {x['in']:8.3f} -> {x['out']:8.3f}  ({x['out'] - x['in']:.2f} s)")
            for n in notes:
                print(f"    {n['edge']:3s} {n['sev']:6s} {n['what']}" + (f"  -> snap {n['edge'].lower()} to {n['suggest']:.3f}" if n["suggest"] is not None else ""))
            if bad: print(f"    suggested window {new_in:.3f} -> {new_out:.3f} ({new_out - new_in:.2f} s, {new_out - new_in - (x['out'] - x['in']):+.2f} s)")
    if missing: print(f"source file missing, not checked: {', '.join(missing)}")
    print(f"broll_edges: {len(rows)} windows checked, {nflag} with a shot change inside or on an edge (report only, nothing changed)")
    if a.json: json.dump({"work": W, "margin": a.margin, "windows": rows, "missing": missing}, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
