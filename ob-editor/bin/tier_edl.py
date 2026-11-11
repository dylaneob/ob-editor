#!/usr/bin/env python3
"""Tier-list reels (C4079 cardio, C4080 food, 2026-10-16): a segment plan becomes a tight EDL plus the
board's pop/place events, in the RESET_edl.json row format.

  python3 tier_edl.py islands TAKE_16k.wav OUT.json [--th -45] [--pause 0.15]
  python3 tier_edl.py build PLAN.json TAKE_16k.wav OUT_EDL.json
  python3 tier_edl.py level TAKE_16k.wav A B          # print the 10 ms level, for checking one cut

islands: speech runs from a 10 ms level (30 ms smoothing) split at every pause of 0.15 s or more, each one
  transcribed on its own with Whisper base.en (one call, word times inside a short clip). Whisper's
  full-take word times drift up to ~1.3 s on these takes, so plans are written against island times.

build: PLAN = {"take", "name", "title", "board", "rows": [{"src": [a, b], "say": "...", "ev": [...]}, ...]}
  Each edge snaps to the energy near the planned time:
    - an island edge within 0.10 s: onset walked back up to 0.18 s (a longer inhale is dead air) and
      decay walked forward up to 0.20 s at max(-48 dB, floor + 8), bridging 60 ms stop closures, 30 ms pad
    - no island edge there (continuous speech): the quietest 10 ms within 0.12 s
  Gap after a row: 0.08 s after a sentence (say ends . ? !), 0.03 s mid-sentence, or "gap" in the row.
  Rows that run on in the source (planned edges within 0.02 s, or a natural pause no longer than the
  designed gap + 0.06 s) are joined at the quietest 10 ms between them with gap 0, so speech runs through.
  A gap that would reach the next sound in the source gets room tone ("fill": "room").
  Row events (source seconds): {"k": "pop"|"place"|"win"|"tag"|"cta", "t": SRC, ...} ("row" = board row).
  They are clamped into their shot and get edit times; the EDL keeps both ("src", "edit") and the shot index.
"""
import json, os, re, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile

MODEL = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")   # 2026-11-03 M5 Pro: medium for word times (was base.en)
FPS = 100                                   # level frames per second (10 ms)


def level(wav):
    sr, x = wavfile.read(wav); x = x.astype(np.float64); x = x.mean(1) if x.ndim > 1 else x; x /= 32768.0
    hop = sr // FPS; n = len(x) // hop
    P = (x[:n * hop].reshape(n, hop) ** 2).mean(1)
    return 10 * np.log10(np.convolve(P, np.ones(3) / 3, mode="same") + 1e-12), sr, x


def runs_of(mask):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            out.append([i, j]); i = j
        else: i += 1
    return out


def find_islands(L, th=-45.0, pause=0.15, min_len=0.06):
    rs = runs_of(L > th)
    if not rs: return []
    merged = [rs[0]]
    for a, b in rs[1:]:
        if a - merged[-1][1] < pause * FPS: merged[-1][1] = b
        else: merged.append([a, b])
    return [[a / FPS, b / FPS] for a, b in merged if (b - a) >= min_len * FPS]


def cmd_islands(wav, out, th, pause):
    L, sr, x = level(wav)
    isl = find_islands(L, th, pause)
    res = []
    with tempfile.TemporaryDirectory() as td:
        clips = []
        for k, (s, e) in enumerate(isl):
            s0, e0 = max(0.0, s - 0.10), e + 0.15
            p = os.path.join(td, f"i{k:04d}.wav"); wavfile.write(p, sr, (x[int(s0 * sr):int(e0 * sr)] * 32767).astype(np.int16))
            clips.append((p, s0))
        for c0 in range(0, len(clips), 60):                       # one model load per 60 clips
            subprocess.run(["whisper-cli", "-m", MODEL, "-ml", "1", "-sow", "-oj", "-np"] + [p for p, _ in clips[c0:c0 + 60]],
                           capture_output=True, text=True)
        for k, ((s, e), (p, s0)) in enumerate(zip(isl, clips)):
            words = []
            try:
                for seg in json.load(open(p + ".json"))["transcription"]:
                    w = seg["text"].strip()
                    if w: words.append({"w": w, "t0": round(s0 + seg["offsets"]["from"] / 1000, 2), "t1": round(s0 + seg["offsets"]["to"] / 1000, 2)})
            except Exception:
                pass
            pk = float(L[int(s * FPS):int(e * FPS)].max())
            txt = " ".join(w["w"] for w in words)
            res.append({"id": k, "start": s, "end": e, "peak_db": round(pk, 1), "text": txt, "words": words})
            print(f"#{k:03d} {s:7.2f}-{e:7.2f} ({e - s:4.2f}s) {pk:6.1f} | {txt}", flush=True)
    json.dump(res, open(out, "w"), indent=1)


class Snapper:
    def __init__(self, wav, th=-45.0, pause=0.15):
        self.L, _, _ = level(wav)
        self.n = len(self.L)
        self.th = max(-48.0, float(np.percentile(self.L, 10)) + 8)
        self.isl = find_islands(self.L, th, pause)
        self.starts = [a for a, _ in self.isl]; self.ends = [b for _, b in self.isl]

    def hot(self, t): i = int(round(t * FPS)); return 0 <= i < self.n and self.L[i] > self.th
    def near(self, t, d): return any(self.hot(t + k * 0.01 * d) for k in range(1, 7))   # bridges 60 ms closures

    def quiet(self, lo, hi):
        i0, i1 = max(0, int(round(lo * FPS))), min(self.n, int(round(hi * FPS)) + 1)
        return round((i0 + int(np.argmin(self.L[i0:i1]))) / FPS, 3)

    def onset(self, t):
        """In-edge for planned time t: (cut, kind). kind 'edge' = after a silence, 'cont' = mid-speech."""
        c = [s for s in self.starts if abs(s - t) <= 0.10]
        if not c: return self.quiet(t - 0.12, t + 0.12), "cont"
        s = min(c, key=lambda q: abs(q - t))
        prv = max([e for e in self.ends if e <= s - 0.02] + [s - 0.6])
        a = s
        while a - 0.01 > max(prv + 0.04, s - 0.18) and self.near(a, -1): a -= 0.01
        return round(max(prv + 0.02, a - 0.03), 3), "edge"

    def decay(self, t):
        c = [e for e in self.ends if abs(e - t) <= 0.10]
        if not c: return self.quiet(t - 0.12, t + 0.12), "cont"
        e = min(c, key=lambda q: abs(q - t))
        nxt = min([s for s in self.starts if s >= e + 0.02] + [e + 0.6])
        b = e
        while b + 0.01 < min(nxt - 0.04, e + 0.20) and self.near(b, 1): b += 0.01
        return round(min(nxt - 0.02, b + 0.03), 3), "edge"

    def next_sound(self, t):
        """First hot frame after t (the next thing the source would play)."""
        i = int(round(t * FPS)) + 1
        while i < self.n and self.L[i] <= self.th: i += 1
        return i / FPS


def sentence_end(say): return bool(re.search(r"[.?!][\"')”]*\s*$", say.strip()))


def cmd_build(plan_p, wav, out):
    plan = json.load(open(plan_p)); S = Snapper(wav)
    rows = []
    for r in plan["rows"]:
        a, ka = S.onset(r["src"][0]); b, kb = S.decay(r["src"][1])
        if r.get("in"): a, ka = r["in"], "fixed"            # hand-checked edges win
        if r.get("out"): b, kb = r["out"], "fixed"
        gap = r["gap"] if "gap" in r else (0.08 if sentence_end(r["say"]) else 0.03)
        rows.append({"src_in": a, "src_out": b, "caption": r["say"], "cue": r.get("cue"), "gap": gap,
                     "_k": (ka, kb), "_plan": r, **({"fill": r["fill"]} if r.get("fill") else {})})
    # joins: rows that run on in the source share one cut at the quietest 10 ms, gap 0
    for i in range(len(rows) - 1):
        r, q = rows[i], rows[i + 1]
        pa, pb = r["_plan"]["src"][1], q["_plan"]["src"][0]
        nat = q["src_in"] - r["src_out"]
        touching = abs(pb - pa) <= 0.02 or (-0.05 <= pb - pa and nat <= r["gap"] + 0.06 and pb >= pa - 0.05)
        if r["_plan"].get("cut") or not touching: continue
        lo, hi = sorted((r["src_out"], q["src_in"]))
        k = S.quiet(lo - 0.05, hi + 0.05)
        r["src_out"] = k; q["src_in"] = k; r["gap"] = 0.0; r["keep_join"] = True
    # leaks: the gap plays the source after src_out; room tone if the next sound would come through
    for i, r in enumerate(rows):
        if r["gap"] > 0 and S.next_sound(r["src_out"]) < r["src_out"] + r["gap"] + 0.02: r["fill"] = "room"
    t = 0.0; events = []
    for i, r in enumerate(rows):
        d = r["src_out"] - r["src_in"]; r["edit_in"] = round(t, 3); r["edit_out"] = round(t + d, 3)
        for ev in r["_plan"].get("ev", []):
            s = min(max(ev["t"], r["src_in"]), r["src_out"] - 0.02)
            events.append(dict({k: v for k, v in ev.items() if k != "t"}, src=round(s, 3), edit=round(r["edit_in"] + s - r["src_in"], 3), shot=i))
        t += d + r["gap"]
    for i, r in enumerate(rows):
        r["edges"] = list(r.pop("_k")); r.pop("_plan")
        r["src_in"], r["src_out"] = round(r["src_in"], 3), round(r["src_out"], 3)
        r["framing"] = r.get("framing") or ("punch" if i % 2 else "wide")
    spec = {"take": plan["take"], "title": plan["name"], "frame1": None, "kicker": None, "cover": plan.get("cover"),
            "board_title": plan["title"], "board": plan["board"], "rows": rows, "items": [], "events": events,
            "duration": round(t, 2), "music": plan.get("music"), "captions": plan.get("captions", False)}
    json.dump(spec, open(out, "w"), indent=1)
    cont = sum(1 for r in rows for k in r["edges"] if k == "cont")
    print(f"{out}: {len(rows)} rows, {spec['duration']} s, {len(events)} events, "
          f"{sum(1 for r in rows if r.get('keep_join'))} joins, {cont} mid-speech edges, {sum(1 for r in rows if r.get('fill'))} room fills (th {S.th:.1f} dB)")
    for i, r in enumerate(rows):
        print(f"  {i:2d} {r['edit_in']:6.2f}-{r['edit_out']:6.2f}  src {r['src_in']:7.3f}-{r['src_out']:7.3f} {'/'.join(r['edges']):10s} "
              f"gap {r['gap']:.2f}{' room' if r.get('fill') else ''}{' join' if r.get('keep_join') else ''} | {r['caption'][:60]}")


def cmd_level(wav, a, b):
    L, _, _ = level(wav); th = max(-48.0, float(np.percentile(L, 10)) + 8)
    for i in range(int(a * FPS), int(b * FPS)):
        v = L[i]; print(f"{i / FPS:8.2f} {v:6.1f} {'#' * max(0, int((v + 60) / 1.5))}{'  <th' if v <= th else ''}")


if __name__ == "__main__":
    a = sys.argv
    opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
    if a[1] == "islands": cmd_islands(a[2], a[3], opt("--th", -45.0), opt("--pause", 0.15))
    elif a[1] == "build": cmd_build(a[2], a[3], a[4])
    elif a[1] == "level": cmd_level(a[2], float(a[3]), float(a[4]))
    else: sys.exit(__doc__)
