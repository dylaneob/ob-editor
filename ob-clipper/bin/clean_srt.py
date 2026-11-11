#!/usr/bin/env python3
"""
clean_srt.py — turn YouTube rolling auto-sub SRT into a de-duplicated,
timestamped transcript suitable for clip-finding.

YouTube auto-subs repeat the visible caption every cue (rolling window),
so naive text extraction duplicates every word ~2x. This reconstructs a
single clean word stream by appending only the *new* words in each cue,
tagging the first new word of each cue with that cue's start time.

Usage: clean_srt.py INPUT.srt [--sentences]  > transcript.txt
Output: one [mm:ss] timestamp per sentence (default) or per cue-boundary.
"""
import sys, re

def parse_srt(path):
    cues = []
    block = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.strip() == "":
            if block:
                cues.append(block); block = []
        else:
            block.append(line.rstrip("\n"))
    if block:
        cues.append(block)
    out = []
    ts_re = re.compile(r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d)[,.](\d\d\d)")
    for b in cues:
        # find the timestamp line
        tsi = next((i for i, l in enumerate(b) if "-->" in l), None)
        if tsi is None:
            continue
        m = ts_re.search(b[tsi])
        if not m:
            continue
        h1, m1, s1, ms1 = map(int, m.group(1, 2, 3, 4))
        start = h1*3600 + m1*60 + s1 + ms1/1000.0
        text = " ".join(l for l in b[tsi+1:] if l.strip())
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append((start, text))
    return out

def dedup_words(cues):
    """Append only new words per cue; tag first new word of each cue w/ start."""
    words = []       # list of (word, timestamp)
    emitted = []     # just the word strings, for overlap matching
    for start, text in cues:
        w = text.split()
        maxk = min(len(emitted), len(w))
        k = 0
        for cand in range(maxk, -1, -1):
            if emitted[-cand:] == w[:cand] if cand else True:
                k = cand
                break
        new = w[k:]
        for i, tok in enumerate(new):
            ts = start if i == 0 else None
            words.append((tok, ts))
            emitted.append(tok)
    # forward-fill timestamps
    last = 0.0
    filled = []
    for tok, ts in words:
        if ts is not None:
            last = ts
        filled.append((tok, last))
    return filled

def fmt(t):
    return f"{int(t)//60:02d}:{int(t)%60:02d}"

def group_sentences(words):
    """Group the word stream into sentences with a leading start timestamp."""
    lines = []
    cur = []
    cur_start = None
    for tok, ts in words:
        if cur_start is None:
            cur_start = ts
        cur.append(tok)
        if re.search(r"[.!?]$", tok):
            lines.append((cur_start, " ".join(cur)))
            cur = []; cur_start = None
    if cur:
        lines.append((cur_start or 0.0, " ".join(cur)))
    return lines

def main():
    path = sys.argv[1]
    words = dedup_words(parse_srt(path))
    for start, sent in group_sentences(words):
        print(f"[{fmt(start)}] {sent}")

if __name__ == "__main__":
    main()
