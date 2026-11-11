#!/usr/bin/env python3
"""
window.py — turn a cleaned YouTube auto-sub SRT into candidate clip windows.

Reuses ob-clipper's clean_srt de-dup to recover a clean word stream with
timestamps, rebuilds sentences (with real start/end), then slides windows of
~15-60s snapped to sentence boundaries so a hook is never cut mid-thought.

Used as a library by score.py; also runnable standalone for inspection:
    python3 window.py work/<id>.en.srt
"""
import sys, re, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean_srt import parse_srt, dedup_words

SENT_END = re.compile(r'[.!?]["\')]?$')


def sentences_from_srt(path):
    """[(word,ts)] -> [{start,end,text,speaker_change}] on sentence boundaries.

    Multi-speaker audio: YouTube auto-subs mark speaker turns with '>>'. Those
    markers must never reach headlines/captions, and a turn is a hard sentence
    boundary — the next sentence carries speaker_change=True so the scorer can
    penalize windows that straddle rapid back-and-forth banter."""
    words = dedup_words(parse_srt(path))
    sents, cur, start = [], [], None
    pending_change = False

    def flush(mark_next_change=False):
        nonlocal cur, start, pending_change
        if cur:
            end = cur[-1][1]
            sents.append({
                "start": round(start, 2),
                "end": round(max(end, start + 0.5), 2),
                "text": " ".join(w for w, _ in cur),
                "speaker_change": pending_change,
            })
            pending_change = False
        cur, start = [], None
        if mark_next_change:
            pending_change = True

    for tok, ts in words:
        if ">>" in tok:
            leftover = tok.replace(">>", "").strip()
            flush(mark_next_change=True)
            if leftover:
                start = ts
                cur.append((leftover, ts))
            continue
        if start is None:
            start = ts
        cur.append((tok, ts))
        if SENT_END.search(tok):
            flush()
    flush()
    return sents


def make_windows(sents, targets=(16, 26, 40), min_s=12, max_s=55):
    """For each sentence start, emit the window closest to each target length."""
    cands, seen, cid, n = [], set(), 0, len(sents)
    for i in range(n):
        for tgt in targets:
            j, best = i, None
            while j < n:
                dur = sents[j]["end"] - sents[i]["start"]
                if dur > max_s:
                    break
                if dur >= min_s and (best is None or abs(dur - tgt) < abs(best[1] - tgt)):
                    best = (j, dur)
                j += 1
            if not best:
                continue
            j, dur = best
            key = (sents[i]["start"], sents[j]["end"])
            if key in seen:
                continue
            seen.add(key)
            cands.append({
                "id": cid,
                "start": sents[i]["start"],
                "end": sents[j]["end"],
                "dur": round(dur, 1),
                "first_sentence": sents[i]["text"],
                "n_sentences": j - i + 1,
                "text": " ".join(s["text"] for s in sents[i:j + 1]),
                "sents": [dict(s) for s in sents[i:j + 1]],   # for hook-point re-cut
                # speaker turns INSIDE the window (excluding its first sentence):
                # rapid banter makes incoherent clips
                "speaker_changes": sum(1 for s in sents[i + 1:j + 1] if s.get("speaker_change")),
            })
            cid += 1
    return cands


if __name__ == "__main__":
    sents = sentences_from_srt(sys.argv[1])
    cands = make_windows(sents)
    print(f"{len(sents)} sentences -> {len(cands)} candidate windows", file=sys.stderr)
    print(json.dumps(cands, indent=2))
