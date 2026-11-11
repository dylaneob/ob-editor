#!/usr/bin/env python3
"""Which transcriber puts OB's word edges where the audio says they are? (OB 2026-10-20 picked this test.)

Compares, on the same audio:
  whisper DTW   whisper.cpp medium.en with -dtw (what the pipeline uses today): one time per word, its start
  whisper ml1   whisper.cpp medium.en, one segment per word (-ml 1 -sow): start and end per word
  apple         macOS 26 SpeechAnalyzer / SpeechTranscriber (bin/speech_words): start and end per word

The yardstick is the audio itself, at the places cuts happen: every pause (>= 0.25 s under the speech threshold) gives a true
end of the word before it and a true start of the word after it, measured on a 10 ms level. For each transcriber:
  onset / offset error = word edge minus the audio edge (median and 90th percentile of |error|, share within 50 / 100 ms)
  missed      = pauses with no word edge within 0.8 s
  false gaps  = gaps >= 0.25 s between its words where the audio is speech (cutting there would clip words)
plus wall time and how much its words agree with whisper medium's.

  python3 word_timing_test.py OUT_DIR NAME=AUDIO[@START+DUR] [...]     (any audio or video file; START/DUR in seconds)
"""
import difflib, json, os, re, subprocess, sys, time
import numpy as np

BIN = os.path.dirname(os.path.abspath(__file__)); MED = os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")


def wav16(src, start, dur, out):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + (["-ss", str(start)] if start else []) + (["-t", str(dur)] if dur else []) + \
          ["-i", src, "-vn", "-ac", "1", "-ar", "16000", out]
    subprocess.run(cmd, check=True)


def level(path):
    x = np.frombuffer(subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)
    n = len(x) // 160; e = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160).astype(np.float64) ** 2).mean(1)) + 1e-9)
    e = np.array([np.median(e[max(0, i - 1):i + 2]) for i in range(n)])           # 30 ms median: one-frame clicks don't split a pause
    return e


def pauses(e, min_len=25):
    thr = max(-50.0, float(np.percentile(e, 95)) - 30); quiet = e < thr; out, cur = [], None
    for i, q in enumerate(list(quiet) + [False]):
        if q and cur is None: cur = i
        elif not q and cur is not None:
            if i - cur >= min_len and cur > 0 and i < len(e): out.append((cur / 100, i / 100))
            cur = None
    return out, thr


def whisper_dtw(wav, base):
    t = time.time(); subprocess.run(["whisper-cli", "-m", MED, "-f", wav, "-nfa", "-dtw", "medium.en", "-ojf", "-of", base], capture_output=True, check=True)
    el = time.time() - t; d = json.load(open(base + ".json")); words = []
    for seg in d["transcription"]:
        for tk in seg.get("tokens", []):
            txt = tk["text"]
            if txt.startswith("[_") or not txt.strip(): continue
            ts = tk.get("t_dtw", -1) / 100
            if txt.startswith(" ") or not words: words.append(dict(w=txt.strip(), s=ts, e=None))
            else: words[-1]["w"] += txt.strip()
    return [w for w in words if w["s"] >= 0], el


def whisper_ml1(wav, base):
    t = time.time(); subprocess.run(["whisper-cli", "-m", MED, "-f", wav, "-ml", "1", "-sow", "-oj", "-of", base], capture_output=True, check=True)
    el = time.time() - t; d = json.load(open(base + ".json"))
    words = [dict(w=s["text"].strip(), s=s["offsets"]["from"] / 1000, e=s["offsets"]["to"] / 1000) for s in d["transcription"] if s["text"].strip()]
    return words, el


def apple(wav):
    t = time.time(); p = subprocess.run([f"{BIN}/speech_words", "words", wav], capture_output=True, text=True)
    el = time.time() - t
    if p.returncode: raise RuntimeError(p.stderr)
    return json.loads(p.stdout), el


def norm(ws): return [re.sub(r"[^a-z0-9']", "", w["w"].lower()) for w in ws if re.sub(r"[^a-z0-9']", "", w["w"].lower())]


def score(words, ps, e, thr):
    on, off, miss = [], [], 0
    starts = np.array([w["s"] for w in words]); ends = np.array([w["e"] for w in words if w["e"] is not None])
    for a, b in ps:
        k = np.argmin(np.abs(starts - b)) if len(starts) else None
        if k is not None and abs(starts[k] - b) <= 0.8: on.append(starts[k] - b)
        else: miss += 1
        if len(ends):
            j = np.argmin(np.abs(ends - a))
            if abs(ends[j] - a) <= 0.8: off.append(ends[j] - a)
            else: miss += 1
    false_gaps = 0
    if len(ends):
        ws = sorted(words, key=lambda w: w["s"])
        for x, y in zip(ws, ws[1:]):
            if x["e"] is None: continue
            g0, g1 = x["e"], y["s"]
            if g1 - g0 >= 0.25 and (e[int(g0 * 100):int(g1 * 100)] > thr).mean() >= 0.5: false_gaps += 1
    def st(v):
        if not v: return None
        a = np.abs(np.array(v)) * 1000
        return dict(n=len(v), median_ms=round(float(np.median(a))), p90_ms=round(float(np.percentile(a, 90))), within_50=round(float((a <= 50).mean()) * 100),
                    within_100=round(float((a <= 100).mean()) * 100), bias_ms=round(float(np.median(v)) * 1000))
    return dict(onset=st(on), offset=st(off), missed=miss, false_gaps=false_gaps)


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True); results = {}
    for arg in sys.argv[2:]:
        name, spec = arg.split("=", 1); src, start, dur = spec, None, None
        if "@" in spec: src, rng = spec.rsplit("@", 1); start, dur = (float(x) for x in rng.split("+"))
        wav = f"{out}/{name}.wav"; wav16(src, start, dur, wav)
        e = level(wav); ps, thr = pauses(e)
        sysw = {}
        sysw["whisper DTW"] = whisper_dtw(wav, f"{out}/{name}_dtw")
        sysw["whisper ml1"] = whisper_ml1(wav, f"{out}/{name}_ml1")
        sysw["apple"] = apple(wav)
        ref = norm(sysw["whisper ml1"][0]); r = dict(seconds=round(len(e) / 100, 1), pauses=len(ps), threshold_db=round(thr, 1))
        for k, (ws, el) in sysw.items():
            sc = score(ws, ps, e, thr); sc["seconds_to_run"] = round(el, 1); sc["words"] = len(ws)
            sc["agree_with_whisper_pct"] = round(difflib.SequenceMatcher(None, norm(ws), ref).ratio() * 100, 1)
            r[k] = sc
        results[name] = r; json.dump({k: [dict(w) for w in v[0]] for k, v in sysw.items()}, open(f"{out}/{name}_words.json", "w"))
        print(f"== {name}: {r['seconds']} s, {r['pauses']} pauses (threshold {r['threshold_db']} dB)")
        for k in sysw:
            s = r[k]; f = lambda d: f"median {d['median_ms']} ms, p90 {d['p90_ms']} ms, {d['within_50']}% <=50 ms, {d['within_100']}% <=100 ms, bias {d['bias_ms']:+d} ms" if d else "n/a"
            print(f"   {k:12s} onsets: {f(s['onset'])}\n   {'':12s} ends:   {f(s['offset'])}\n   {'':12s} missed {s['missed']}, false gaps {s['false_gaps']}, "
                  f"{s['words']} words, {s['agree_with_whisper_pct']}% same words as whisper, {s['seconds_to_run']} s to run")
    json.dump(results, open(f"{out}/results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
