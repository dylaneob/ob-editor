#!/usr/bin/env python3
"""whisper-cli word JSON (-ml 1 -sow -oj) -> mic_words_clean.json {"words": [[t0, t1, word]]} + mic_sentences.txt
(one line per phrase: breaks at pauses >= 0.7 s or after . ? !), times in recording seconds.

  python3 -I mic_words_clean.py WORK_DIR   (reads WORK_DIR/mic_words.json)
"""
import json, re, sys
W = sys.argv[1]
J = json.load(open(f"{W}/mic_words.json"))["transcription"]
words = []
for x in J:
    w = x["text"].strip()
    if not w or re.fullmatch(r"[\[\(].*[\]\)]", w): continue   # [BLANK_AUDIO], (music) ...
    words.append([round(x["offsets"]["from"] / 1000, 3), round(x["offsets"]["to"] / 1000, 3), w])
json.dump({"words": words}, open(f"{W}/mic_words_clean.json", "w"))
tc = lambda t: f"{int(t // 60):02d}:{t % 60:04.1f}"
lines, cur = [], []
for k, w in enumerate(words):
    if cur and (w[0] - cur[-1][1] >= 0.7): lines.append(cur); cur = []
    cur.append(w)
    if re.search(r"[.?!]$", w[2]): lines.append(cur); cur = []
if cur: lines.append(cur)
open(f"{W}/mic_sentences.txt", "w").write("".join(f"{tc(l[0][0])}-{tc(l[-1][1])}  {' '.join(w[2] for w in l)}\n" for l in lines))
print(f"{len(words)} words, {len(lines)} lines")
