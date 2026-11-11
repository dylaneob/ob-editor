#!/usr/bin/env python3
"""Squeeze the dead space out of a finished lecture-style EDL. OB 2026-10-16 on Losers: "you need to cut more of the
dead space" (Losers had 0.57 s of air in its first 2 s, 0.37 s after "ocean", 0.38 s at the end, and ~15 line
breaks of 0.15-0.19 s).

  python3 squeeze_edl.py EDL.json TAKE_48k.wav [--split ROW:WORD ...] [--dry] [--sentence 0.10] [--mid 0.08] [--end 0.25]

Lessons from the first version (it cut a soft "And", the quick "if they're", the burst at the end of "worked", and
split "support" at its P): a fixed loudness threshold calls quiet words silence on a take with night noise, and a
stop consonant's closure looks like a pause. So:
  - speech is measured against the noise floor around each break (5th percentile of +-1.5 s of source + 12 dB),
    with 10 ms frames; the last/first loud frame of each line is its edge
  - only row boundaries are trimmed: the earlier row keeps 60 ms after its last loud frame, the next row 50 ms
    before its first; the gap is what's left of the target (sentence end --sentence, else --mid); explicit_out rows
    keep their out point
  - a line is split inside only where you name it (--split '13:you."' splits row 13 after that caption word; WORD#2 = its 2nd use), and only
    if Whisper medium hears both halves whole (padded with 0.5 s of silence so the last word isn't dropped)
  - every trimmed edge is re-heard the same way: the last word of the earlier line and the first word of the next
    must still be there, or that boundary goes back to how it was
Saves the original as *_v1.json (once), writes the EDL in place unless --dry, prints every change.
"""
import difflib, json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

TAIL, HEAD, OVER = 0.06, 0.05, 12.0


def norm(w): return re.sub(r"[^a-z0-9%]", "", w.lower().replace("’", "'").replace("'", ""))


class Take:
    def __init__(self, wav):
        self.sr, x = wavfile.read(wav); x = x.astype(np.float64); x = x.mean(1) if x.ndim > 1 else x; self.x = x / 32768.0
        hop = int(self.sr * 0.01); n = len(self.x) // hop
        self.L = 10 * np.log10(np.convolve((self.x[:n * hop].reshape(n, hop) ** 2).mean(1), np.ones(3) / 3, mode="same") + 1e-12)

    def lv(self, a, b): return self.L[int(round(a * 100)):int(round(b * 100))]

    def hear(self, t0, t1):
        seg = resample_poly(self.x[int(t0 * self.sr):int(t1 * self.sr)], 1, 3)
        seg = np.concatenate([np.zeros(8000), seg, np.zeros(8000)])
        with tempfile.TemporaryDirectory() as td:
            p = f"{td}/a.wav"; wavfile.write(p, 16000, (np.clip(seg, -1, 1) * 32767).astype(np.int16))
            r = subprocess.run(["whisper-cli", "-m", os.path.expanduser("~/.whisper-models/ggml-medium.en.bin"), "-f", p, "-nt", "-t", "4"],
                               capture_output=True, text=True)
        return [norm(w) for w in " ".join(l.strip() for l in r.stdout.splitlines()).split() if norm(w)]


def close(a, b):
    """Same word, allowing Whisper's small spelling drift (worked/work is NOT close: the ending is the point)."""
    return a == b or (len(a) > 3 and len(b) > 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.85 and a[-2:] == b[-2:])


def main():
    a = sys.argv
    edl, wav = a[1], a[2]
    opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
    SENT, MID, END = opt("--sentence", 0.10), opt("--mid", 0.08), opt("--end", 0.25)
    splits = [s for k, s in zip(a, a[1:]) if k == "--split"]
    spec = json.load(open(edl)); rows = [dict(r) for r in spec["rows"]]
    tk = Take(wav); log = []

    # 1. named splits inside a line, verified by ear
    for sp in splits:
        ri, word = sp.split(":", 1); ri = int(ri); r = rows[ri]
        word, nth = (word.rsplit("#", 1)[0], int(word.rsplit("#", 1)[1])) if re.search(r"#\d+$", word) else (word, 1)
        cw = r["caption"].split()
        hits = [m + 1 for m, w in enumerate(cw) if w == word] or [m + 1 for m, w in enumerate(cw) if norm(w) == norm(word)]
        cut = hits[nth - 1] if len(hits) >= nth else None
        if not cut or cut >= len(cw): sys.exit(f"--split {sp}: '{word}' isn't a word inside row {ri}: {r['caption']}")
        # the pause = the longest stretch near the row's own noise floor, away from its edges
        seg = tk.lv(r["src_in"], r["src_out"]); amb = np.percentile(seg, 10)
        q = seg < amb + OVER; best, k = (0, 0, 0), 0
        while k < len(q):
            if q[k]:
                j = k
                while j < len(q) and q[j]: j += 1
                if j - k > best[0] and k > 5 and j < len(q) - 5: best = (j - k, k, j)
                k = j
            else: k += 1
        if best[0] < 8: log.append(f"split {sp}: no pause of 80 ms+ inside row {ri}, kept whole"); continue
        s0, s1 = r["src_in"] + best[1] / 100, r["src_in"] + best[2] / 100
        A = dict(r, src_out=round(s0 + TAIL, 3), caption=" ".join(cw[:cut]),
                 gap=round(max(0.0, (SENT if re.search(r"[.!?]\W*$", cw[cut - 1]) else MID) - TAIL - HEAD), 3))
        B = dict(r, src_in=round(s1 - HEAD, 3), caption=" ".join(cw[cut:]))
        for kx in ("explicit_out", "fill", "keep_join"): A.pop(kx, None)
        for kx in ("freeze_until", "freeze_frame"): B.pop(kx, None)
        ha, hb = tk.hear(A["src_in"], A["src_out"]), tk.hear(B["src_in"], B["src_out"])
        wa, wb = [norm(w) for w in A["caption"].split()], [norm(w) for w in B["caption"].split()]
        ok = ha and hb and close(ha[-1], wa[-1]) and close(hb[0], wb[0]) and \
            difflib.SequenceMatcher(None, wa, ha).ratio() > 0.8 and difflib.SequenceMatcher(None, wb, hb).ratio() > 0.8
        if not ok: log.append(f"split {sp}: halves not heard whole ({' '.join(ha)} | {' '.join(hb)}), kept whole"); continue
        rows[ri:ri + 1] = [A, B]
        log.append(f"split row {ri} after '{cw[cut - 1]}': pause {s0:.2f}-{s1:.2f} -> {A['src_out']:.2f} / {B['src_in']:.2f}, "
                   f"gap {A['gap']:.2f}  [heard: ...{' '.join(ha[-3:])} | {' '.join(hb[:3])}...]")

    # 2. boundaries between lines, measured against the local noise, every trimmed edge re-heard
    for i in range(len(rows)):
        r = rows[i]; last = i == len(rows) - 1
        nxt = None if last else rows[i + 1]
        if not last and r.get("gap", 0) == 0 and abs(r["src_out"] - nxt["src_in"]) < 0.002:
            continue                                                        # joined in the source: nothing between
        tail_end = r["src_out"] + (0 if r.get("fill") == "room" else r.get("gap", 0))
        t_from = max(r["src_in"], r["src_out"] - 0.6)
        ta = tk.lv(t_from, tail_end)
        hb_ = tk.lv(nxt["src_in"], min(nxt["src_out"], nxt["src_in"] + 0.6)) if nxt else np.array([])
        # the floor comes from real silence nearby (5th pct of +-1.5 s around the break): a window that is mostly
        # speech put the cutoff inside soft endings (realistic, hobby, journey, off) in the second version
        wide = np.concatenate([tk.lv(max(0.0, r["src_out"] - 1.5), tail_end + 0.2),
                               tk.lv(max(0.0, nxt["src_in"] - 0.2), nxt["src_in"] + 1.5) if nxt else np.array([])])
        amb = np.percentile(wide, 5) if len(wide) else -60.0
        loud_t = np.where(ta > amb + OVER)[0]
        off = t_from + (loud_t[-1] + 1) / 100 if len(loud_t) else r["src_out"]
        new_out = r["src_out"] if r.get("explicit_out") else round(min(r["src_out"], off + TAIL), 3)
        w_end = norm(r["caption"].split()[-1])
        if new_out < r["src_out"]:                       # the earlier line's tail, re-heard on its own
            h_end = tk.hear(max(r["src_in"], new_out - 1.4), new_out)
            if not (h_end and close(h_end[-1], w_end)):
                log.append(f"row {i}: tail trim to {new_out:.2f} would lose '{w_end}' (heard ...{' '.join(h_end[-2:])}), tail kept")
                new_out = r["src_out"]
        kept_tail = max(0.0, new_out - off)
        if last:
            old = (r["src_out"], r.get("gap", 0)); r["src_out"] = new_out; r["gap"] = round(max(0.0, END - kept_tail), 3)
            log.append(f"end: row {i} out {old[0]:.2f}->{r['src_out']:.2f}, final gap {old[1]:.2f}->{r['gap']:.2f}")
            continue
        loud_h = np.where(hb_ > amb + OVER)[0]
        on = nxt["src_in"] + loud_h[0] / 100 if len(loud_h) else nxt["src_in"]
        new_in = round(max(nxt["src_in"], on - HEAD), 3)
        w_start = norm(nxt["caption"].split()[0])
        if new_in > nxt["src_in"]:                       # the next line's head, re-heard on its own
            h_start = tk.hear(new_in, min(nxt["src_out"], new_in + 1.4))
            if not (h_start and close(h_start[0], w_start)):
                log.append(f"row {i + 1}: head trim to {new_in:.2f} would lose '{w_start}' (heard {' '.join(h_start[:2])}...), head kept")
                new_in = nxt["src_in"]
        target = SENT if re.search(r"[.!?,]\W*$", r["caption"]) else MID
        new_gap = round(max(0.0, target - kept_tail - max(0.0, on - new_in)), 3)
        if (new_out, new_in, new_gap) == (r["src_out"], nxt["src_in"], r.get("gap", 0)): continue
        old = (r["src_out"], nxt["src_in"], r.get("gap", 0))
        r["src_out"], nxt["src_in"], r["gap"] = new_out, new_in, new_gap
        saved = (old[0] - new_out) + (new_in - old[1]) + (old[2] - new_gap)
        log.append(f"row {i}->{i + 1} '{r['caption'].split()[-1]}' | '{nxt['caption'].split()[0]}': out {old[0]:.2f}->{new_out:.2f}, "
                   f"in {old[1]:.2f}->{new_in:.2f}, gap {old[2]:.2f}->{new_gap:.2f}  (-{saved:.2f} s, noise {amb:.0f} dB)")
    t = 0.0
    for r in rows:
        d = r["src_out"] - r["src_in"]; r["edit_in"] = round(t, 3); r["edit_out"] = round(t + d, 3); t += d + r.get("gap", 0)
    print("\n".join(log))
    print(f"{edl}: {len(spec['rows'])} -> {len(rows)} rows, {spec['duration']:.2f} s -> {t:.2f} s")
    if "--dry" in a: return
    v1 = edl.replace(".json", "_v1.json")
    if not os.path.exists(v1): shutil.copy(edl, v1)
    spec["rows"] = rows; spec["duration"] = round(t, 2)
    json.dump(spec, open(edl, "w"), indent=1)


if __name__ == "__main__":
    main()
