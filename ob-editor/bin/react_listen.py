#!/usr/bin/env python3
"""Listen-check a reaction edit by transcript (C4353 v3, 2026-10-16): before every clip play / resume, and inside every
span the no-repeat pass removed, which words in OB's mic are the clip's own (speaker bleed: an aborted start, a replay)
and which are OB's (must not be cut). Clip words come from whisper on each clip file (qc/clip_words/c<k>.json).

  python3 -I react_listen.py WORK_DIR > qc/listen_report.txt
"""
import json, os, re, subprocess, sys
W = sys.argv[1]; MODEL = "/Users/YOU/.whisper-models/ggml-medium.en.bin"; TMP = f"{W}/qc/_listen.wav"
tc = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"
norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
names = {}
for line in open(f"{W}/clips_index.txt"):
    k, name, *_ = line.rstrip("\n").split("\t"); names[name] = k[1:]
CW = {k: [(x["offsets"]["from"] / 1000, norm(x["text"])) for x in json.load(open(f"{W}/qc/clip_words/c{k}.json"))["transcription"] if norm(x["text"])]
      for k in set(names.values()) if os.path.exists(f"{W}/qc/clip_words/c{k}.json")}


def hear(a, b):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", f"{W}/mic16.wav", "-af", "apad=pad_dur=0.5", TMP], check=True)
    r = subprocess.run(["whisper-cli", "-m", MODEL, "-f", TMP, "-l", "en", "-t", "6", "-np", "-nt"], capture_output=True, text=True)
    return [norm(w) for w in r.stdout.split() if norm(w)]


def split_words(ws, k, c0, c1):   # mark each heard word as clip (in the clip's words near clip time [c0, c1]) or OB
    near = {w for t, w in CW[k] if c0 - 4 <= t <= c1 + 4 and len(w) > 2}
    return " ".join(w.upper() if w in near else w for w in ws), sum(1 for w in ws if w not in near and len(w) > 2)


gate = json.load(open(f"{W}/gate.json"))
print("Words in CAPS are the clip's own words heard through the speakers; lowercase = OB (or unmatched).\n")
print("== The 6 s before every play / resume (raw mic)")
for g in sorted(gate, key=lambda g: g["rec_in"]):
    k = names[g["clip"]]; a = max(0, g["rec_in"] - 6); ws = hear(a, g["rec_in"])
    txt, ob = split_words(ws, k, 0 if g["clip_in"] < 1 else g["clip_in"] - 6, g["clip_in"] + 1)
    print(f"#{k} play raw {tc(g['rec_in'])} (clip {g['clip_in']}): {txt}")
pre = json.load(open(f"{W}/qc/react_cutlist_pre_norepeat.json"))["shots"]; post = json.load(open(f"{W}/qc/react_cutlist_pre_v2.json"))["shots"]
kept = sorted((s["src_in"], s["src_out"]) for s in post if s["layout"] != "insert")
print("\n== Inside every span the no-repeat pass removed (raw mic)")
for s in pre:
    if s["layout"] != "split": continue
    a, b = s["src_in"], s["src_out"]; k = names[s["clip"]]
    cur, holes = a, []
    for x0, x1 in kept:
        if x1 <= cur or x0 >= b: continue
        if x0 > cur + 0.05: holes.append((cur, x0))
        cur = max(cur, x1)
    if b > cur + 0.05 and not any(x0 <= cur < x1 for x0, x1 in kept): pass
    for h0, h1 in holes:
        ws = hear(max(0, h0 - 0.3), h1 + 0.3); txt, ob = split_words(ws, k, h0 - s["offset"], h1 - s["offset"])
        print(f"#{k} removed raw {tc(h0)}-{tc(h1)} ({h1 - h0:.2f}s): {txt}   [{ob} non-clip words]")
