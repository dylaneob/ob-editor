#!/usr/bin/env python3
"""Cut audit for a talking-head edit: is any word clipped at a cut, and does every join breathe naturally?

  python3 -I cut_audit.py WORK_DIR [--master WAV]

Reads cutlist.json (segments with optional audio_shift_ms / audio_head_mute_ms / audio_tail_mute_ms, exactly as
assemble.py plays them) and the synced master audio. For every shot it measures, on the audio that will actually play:
  lead  = silence from the shot's first sample to the first speech (a word starting closer than 60 ms to a cut is at risk)
  tail  = silence from the last speech to the shot's last sample
  edge  = level of the first/last 20 ms (speech right at the edge = a clipped word)
and for every join the pause the viewer hears (tail of one shot + lead of the next):
  under 140 ms feels rushed (sentences run together), over 650 ms feels like dead air.
Speech = 10 ms RMS above max(-45 dBFS, noise floor + 14 dB). Writes qc/cut_audit.json and prints the flags.
"""
import json, subprocess, sys
import numpy as np

W = sys.argv[1]
MASTER = sys.argv[sys.argv.index("--master") + 1] if "--master" in sys.argv else f"{W}/master_synced.wav"
FPS = 30000 / 1001; SR = 16000; HOP = 160   # 10 ms
segs = json.load(open(f"{W}/cutlist.json"))["segments"]
raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", MASTER, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
n = len(x) // HOP; db = 20 * np.log10(np.sqrt((x[: n * HOP].reshape(n, HOP) ** 2).mean(1)) + 1e-9)
floor = float(np.percentile(db, 10)); thr = max(-45.0, floor + 14.0)
fr = lambda t: int(round(t * FPS)); ft = lambda f: f / FPS
rows, edit_t = [], 0.0
for s in segs:
    a0, b0 = fr(s["src_in"]), fr(s["src_out"])
    if b0 <= a0: continue
    sh = s.get("audio_shift_ms", 0.0) / 1000
    t0, t1 = ft(a0) - sh, ft(b0) - sh                      # the audio this shot really plays
    t0 += s.get("audio_head_mute_ms", 0.0) / 1000; t1 -= s.get("audio_tail_mute_ms", 0.0) / 1000
    i0, i1 = int(t0 * 100), int(t1 * 100)
    seg = db[i0:i1]; sp = np.where(seg > thr)[0]
    lead = int(sp[0] * 10) if len(sp) else None; tail = int((len(seg) - 1 - sp[-1]) * 10) if len(sp) else None
    rows.append({"i": s["i"], "edit_in": round(edit_t, 2), "src_in": s["src_in"], "src_out": s["src_out"], "lead_ms": lead, "tail_ms": tail,
                 "edge_in_db": round(float(seg[:2].max()), 1), "edge_out_db": round(float(seg[-2:].max()), 1)})
    edit_t += ft(b0 - a0)
flags = []
for r in rows:
    if r["lead_ms"] is not None and r["lead_ms"] < 60 and r["i"] != 0:
        flags.append(f'shot {r["i"]:2d} starts {r["lead_ms"]} ms before speech (edit {r["edit_in"]:.1f}s, src {r["src_in"]}): first word may be clipped')
    if r["tail_ms"] is not None and r["tail_ms"] < 60:
        flags.append(f'shot {r["i"]:2d} ends {r["tail_ms"]} ms after speech (src {r["src_out"]}): last word may be clipped')
    if r["edge_in_db"] > thr and r["i"] != 0: flags.append(f'shot {r["i"]:2d} begins mid-sound ({r["edge_in_db"]} dB at the cut)')
    if r["edge_out_db"] > thr: flags.append(f'shot {r["i"]:2d} ends mid-sound ({r["edge_out_db"]} dB at the cut)')
joins = []
for p, q in zip(rows, rows[1:]):
    if p["tail_ms"] is None or q["lead_ms"] is None: continue
    gap = p["tail_ms"] + q["lead_ms"]; joins.append({"after_shot": p["i"], "edit_t": q["edit_in"], "pause_ms": gap})
    if gap < 140: flags.append(f'join {p["i"]}->{q["i"]} at edit {q["edit_in"]:.1f}s: only {gap} ms of pause (rushed)')
    if gap > 650: flags.append(f'join {p["i"]}->{q["i"]} at edit {q["edit_in"]:.1f}s: {gap} ms of pause (dead air)')
json.dump({"threshold_db": round(thr, 1), "noise_floor_db": round(floor, 1), "shots": rows, "joins": joins, "flags": flags}, open(f"{W}/qc/cut_audit.json", "w"), indent=1)
pz = [j["pause_ms"] for j in joins]
print(f"speech threshold {thr:.1f} dBFS (noise floor {floor:.1f}); {len(rows)} shots, {len(joins)} joins; "
      f"join pauses median {np.median(pz):.0f} ms, range {min(pz)}-{max(pz)} ms")
for r in rows: print(f'  shot {r["i"]:2d} edit {r["edit_in"]:6.1f}s  lead {r["lead_ms"]} ms  tail {r["tail_ms"]} ms  edges {r["edge_in_db"]}/{r["edge_out_db"]} dB')
print("FLAGS:" if flags else "no flags"); [print("  !", f) for f in flags]
