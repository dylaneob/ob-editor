#!/usr/bin/env python3
"""whisper-cli DTW JSON (-nfa -dtw MODEL -ojf) -> [[t0, t1, word], ...] (C4354, 2026-10-17).

t_dtw marks where a token ENDS, so a word ends at its last token's t_dtw. Its start is the previous word's end, or
(after a pause) end minus a length estimate from the letters (0.075 s each, 0.12-0.6 s), never before the segment start.
Plain -ml 1 times drifted up to 3 s on C4354; these hold within ~0.1 s on the checks in REACT-NOTES.md.

  python3 -I dtw_words.py IN.json OUT.json [--sentences OUT.txt]
"""
import json, re, sys
J = json.load(open(sys.argv[1]))["transcription"]; words = []
for seg in J:
    s0 = seg["offsets"]["from"] / 1000; cur = []
    for tk in seg.get("tokens", []):
        tx = tk["text"]
        if tx.startswith("[_") or tk.get("t_dtw", -1) < 0: continue
        t = tk["t_dtw"] / 100
        if tx.startswith(" ") or not cur: cur.append([t, tx.strip()])
        else: cur[-1][0] = t; cur[-1][1] += tx
    prev = s0
    for end, w in cur:
        if not re.search(r"[A-Za-z0-9]", w): continue
        est = min(0.6, max(0.12, 0.075 * len(re.sub(r"[^A-Za-z0-9]", "", w))))
        st = max(prev, s0, end - est) if end - prev > est + 0.25 else prev
        words.append([round(st, 3), round(max(end, st + 0.03), 3), w]); prev = end
words.sort(key=lambda w: w[0])
json.dump({"words": words, "source": "whisper DTW (t_dtw = token end)"}, open(sys.argv[2], "w"))
if "--sentences" in sys.argv:
    tc = lambda t: f"{int(t // 60):02d}:{int(t % 60):02d}.{int(t * 10) % 10}"
    lines, cur = [], []
    for w in words:
        if cur and w[0] - cur[-1][1] >= 0.7: lines.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w[2]): lines.append(cur); cur = []
    if cur: lines.append(cur)
    open(sys.argv[sys.argv.index("--sentences") + 1], "w").write("".join(f"{tc(l[0][0])}-{tc(l[-1][1])}  {' '.join(w[2] for w in l)}\n" for l in lines))
print(f"{len(words)} words")
