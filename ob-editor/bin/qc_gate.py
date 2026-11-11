#!/usr/bin/env python3
"""The QC gate: one command every finished video passes before OB sees it (2026-10-28; OB: "have quality control and a loop of
upgrades so you dont make the same mistake twice"). Each check guards mistakes OB has flagged, listed in his words in the ledger
~/ob-editor/qc/mistakes.json. A new note from OB goes into the ledger with a check (or a manual line) and a planted fixture in
~/ob-editor/qc/regress that the check must fail; --selftest proves every check still catches its mistake.

  python3 -I qc_gate.py FILE [--script SCRIPT.txt|.json] [--long] [--pieces PIECES.json --src CAMERA.mp4]
                             [--vmaf REF:REF_START:DIST_START:DUR] [--json OUT.json] [--skip CHECK,...] [--work WORK_DIR]
                             [--sfx-plan story/sfx_plan.json] [--music A.mp3:B.mp3]
  python3 -I qc_gate.py --rules        the never-again list: read it before every edit
  python3 -I qc_gate.py --selftest     every check against its planted mistake

Checks (FAIL blocks delivery; WARN is read and answered in the delivery note):
  format     1080x1920 9:16 for short form (FAIL otherwise), 29.97/30 fps, AAC 48 kHz 192k+, video 6 Mbps+
  size       over 30 MB: make a 720p phone preview too (WARN)
  cues       his retake call ("cut that, Claude", heard as cloud/clock/clod) anywhere in the audio: FAIL; a bare "cut that" or
             "Claude": WARN. Read from whisper AND Apple's speech_words: whisper drops false starts and the cue with them
  words      with --script: every script word heard. A run of 2+ missing words, or 3+ missing in all, FAILs; single
             differences are listed (WARN) to check by ear, since ASR spelling differs ("gonna"/"going to")
  silence    short form: silence (under p90 - 32 dB) 3% or less and none over 0.2 s (zero_dead.py)
  edges      no word cut off: the file doesn't start or end while he is talking; with segs (the engine's pieces) every piece
             edge sits outside his words in the source audio (OB 10-28: "stop cutting me off when im saying a word")
  audio      0 flat-topped (clipped) peaks, true peak -1 dBTP or lower (FAIL); loudness -14 +-1.5 LUFS (WARN) (voice_master.py)
  motion     0 one-frame flashes (FAIL); first move by 1.5 s (WARN); the live score is reported (motion_score.py)
  text_face  no on-screen text over HIS face (FAIL). His face is the face track present in most sampled frames, so photos
             of other people in a grid or a clip don't count. Text of 2 characters or fewer (a cap logo) is ignored, and so
             are digits in dots ('.44.', the LA on his cap read as a number). A face hidden under text is only assumed
             while his A-roll is on screen: --work (long-form) reads the edit's full-screen events (cards, b-roll covers,
             client clips: assemble.is_cover) and frames inside them don't borrow his face from the shots around them
  text_lint  on-screen text: an em or en dash FAILs anywhere; in short copy (8 words or fewer) a hyphen used as a dash FAILs too
             (OCR reads an em dash as "-"; a suspended hyphen, "Low- vs high-load", is a hyphen), and "free" or "team" WARN
             (his spoken words in captions may be fine)
  text_safe  text inside the IG UI bands, top 220 px / bottom 420 px of 1920 (WARN)
  hook       text on frame 1 and 9 words or fewer in the first 3 s (WARN)
  captions   every caption word (short lines, lower part, changing with his speech) is heard within 2.5 s of it (WARN: check
             each listed word by eye; titles, labels and cards on screen 3 s+ are left to the other text checks)
  lookoff    with --pieces and --src: no piece edge on him looking down or away (zero_dead.py lookoff)
  clients    with --work (the edit's events_resolved.json): every line where OB says his clients, coaching people, "over a decade"
             with coaching, or "I help hundreds" has a client-proof overlay on screen within about 1 s (an event tagged
             "client_proof": true, or one that uses a Progress Photos / Client & Testimonial file): FAIL if one is missing
             (ledger M56, OB 11-07: "when i say clients you are suppose to put clients on screen for proof")
  sfx        with a sound-effects plan (--sfx-plan, --work with story/sfx_plan.json, or OB_SFX_PLAN in the render): M17's caps
             (reels about 3-4 a minute, long-form up to 2.9; none in the first 0.5 s; never two within 1.5 s, a list's ticks
             0.25 s; never planned louder than his voice) FAIL, and every planned sound is found in the finished audio on its
             frame (FAIL if it sits a frame or more off its cue) and under his voice; buried, repeated, clipped, hissy or
             late-starting sounds WARN (sfx_check.py: step 3 and step 5 of the Openverse -> earshot -> Real SFX chain, 11-07)
  bank       the SFX plan and the music (--music A.mp3:B.mp3, OB_MUSIC, or --work's newest story/score*.json): a sound from our
             code-made kit (assets/sfx, sfx.py) or earshot forge without "bank_miss" in its plan hit, music we made, a commercial or
             unknown-source song on YouTube, an AI-labelled or Content ID track, Tapis or Vastness FAIL; a sound or track outside
             the known banks WARNs (ledger M58 + M59, OB 11-07: "use the sound effects from the bank first before making your own
             always"; YouTube "copy right friendly")
  vmaf       with --vmaf: mean 93+ against the source (vmaf_check.py)
Frames for the text checks are read every 0.5 s (2 s over 5 minutes) with Apple Vision (bin/frame_obstacles: faces + text
boxes). They and Apple's words are cached per file (path, size, mtime) in ~/ob-editor/qc/cache, so a re-run is instant.
Exit 1 on any FAIL. The report goes to ~/ob-editor/qc/reports/<name>__<hash>.json (and --json). Every engine calls
after_render() at the end of a render; deliver.py copies to an AirDrop folder only on a PASS. Landscape files get the
long-form rules automatically; files over 5 minutes take the lighter set (see gate()).
"""
import difflib, json, os, re, subprocess, sys, tempfile, time
import numpy as np

BIN = os.path.dirname(os.path.abspath(__file__)); QC = os.path.join(os.path.dirname(BIN), "qc")
_RAM_GB = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout or 0) / 2 ** 30
VISION_JOBS = 4 if _RAM_GB >= 32 else 1   # frame_obstacles calls at a time (Apple Vision); 1 on the 8 GB Air
MOTION_MAX_S = 2700 if _RAM_GB >= 32 else 300   # longest file the motion scan reads (it holds every frame at 256x144)
WHISPER_LONG = _RAM_GB >= 32   # whisper reads the retake cues on files over 5 minutes too
sys.path.insert(0, BIN)
LEDGER = os.path.join(QC, "mistakes.json")
CUE = re.compile(r"\b(cut|got|cuts)\s+that[,.]?\s+(claude|cloud|clock|clod|clyde|clawed)\b", re.I)   # his retake call
CUE_WEAK = re.compile(r"\b(cut that|claude)\b", re.I)


# 2026-11-02 (EkkoVision Nov 2, iPhone takes): the edges check calls a pause "floor + 6 dB", the floor being the quietest 10% of frames. On the MOTIV mic
# (floor -70 dB, flat) that is right. A phone mic in a quiet room sits at -47 dB with +-3 dB wander, so p10 + 6 lands under the typical noise and room
# noise before a soft word ("White.") reads as speech. OB_QC_EDGE_FLOOR_MARGIN raises the margin for such takes; the default stays 6 (nothing else changes).
EDGE_FLOOR_MARGIN = float(os.environ.get("OB_QC_EDGE_FLOOR_MARGIN", "6"))
OURS = re.compile(r"/AIRDROP [^/]+/|/finals/")   # where our own renders live: a file there is an edit, not a raw take


def pieces_path(path):
    """~/ob-editor/qc/pieces/<name>__<8 hex>.json: the raw pieces a render is made of (record_pieces), named like its report."""
    return report_path(path).replace(os.sep + "reports" + os.sep, os.sep + "pieces" + os.sep)


def parent_pieces(src):
    """The raw pieces inside one of our renders as [(source, start, end, t_out)]; [] when src is ours but its pieces were
    never recorded (or it changed since); None when src is raw (a camera original, a mic, a downloaded video)."""
    if src.lower().endswith((".wav", ".aif", ".aiff", ".m4a", ".mp3", ".flac")): return None
    p = pieces_path(src)
    if os.path.exists(p):
        d = json.load(open(p))
        if abs(d.get("mtime", 0) - os.path.getmtime(src)) < 1e-3: return [tuple(x) for x in d["pieces"]] if not d.get("unknown") else []
        return []
    return [] if (OURS.search(os.path.abspath(src)) or os.path.exists(report_path(src))) else None


def lineage(segs, depth=0):
    """segs [(src, start, end[, t_out])] -> (raw pieces [(src, start, end, t_out)], our renders whose own cuts are unknown).
    A piece taken from one of our renders is replaced by that render's own raw pieces, so the cuts INSIDE it are checked
    too (OB 2026-10-28 "you still fucking cut me off on fdoe": the counter mock was cut from the posted FDOE render, and
    only the mock's own two edges were checked; the cut-offs were inside the render). t_out: where the piece plays in the
    file; without it the pieces play back to back."""
    if not segs: return [], []
    if any(len(x) < 4 for x in segs):
        t, s2 = 0.0, []
        for x in segs: s2.append((x[0], float(x[1]), float(x[2]), t)); t += float(x[2]) - float(x[1])
        segs = s2
    out, unknown = [], []
    for src, a, b, t in segs:
        par = parent_pieces(src) if depth < 4 else None
        if par is None: out.append((src, a, b, t)); continue
        if not par: unknown.append(src); out.append((src, a, b, t)); continue
        sub = []
        for s2, a2, b2, t2 in par:
            lo, hi = max(a, t2), min(b, t2 + (b2 - a2))
            if hi - lo > 1e-3: sub.append((s2, a2 + lo - t2, a2 + hi - t2, t + lo - a))
        o2, u2 = lineage(sub, depth + 1); out += o2; unknown += u2
    return out, unknown


def record_pieces(path, segs, cam=None, theirs=None):
    """Every render that knows its pieces records them (raw sources, with where each plays in the file), so any clip, mock
    or move cut from it later is checked down to the raw take."""
    raw, unknown = lineage(segs)
    os.makedirs(os.path.join(QC, "pieces"), exist_ok=True)
    json.dump({"file": os.path.abspath(path), "mtime": os.path.getmtime(path), "pieces": [list(x) for x in raw],
               "unknown": sorted(set(unknown)), **({"cam": [list(x) for x in cam]} if cam else {}), **({"theirs": [list(x) for x in theirs]} if theirs else {})}, open(pieces_path(path), "w"), indent=1)


def ours_path(path):
    """~/ob-editor/qc/ours/<name>__<8 hex>.json: the spans where the render's own graphics are on screen (react renders, C4415 11-04)."""
    import hashlib
    return os.path.join(QC, "ours", os.path.basename(path) + "__" + hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:8] + ".json")


def copy_pieces(src, dst):
    """deliver.py's copy into an AirDrop folder keeps the render's pieces (copy2 keeps the mtime)."""
    p = pieces_path(src)
    if os.path.exists(p):
        d = json.load(open(p)); d.update(file=os.path.abspath(dst), mtime=os.path.getmtime(dst), copy_of=os.path.abspath(src))
        json.dump(d, open(pieces_path(dst), "w"), indent=1)
    o = ours_path(src)
    if os.path.exists(o):
        d = json.load(open(o)); d.update(mtime=os.path.getmtime(dst)); os.makedirs(os.path.dirname(ours_path(dst)), exist_ok=True)
        json.dump(d, open(ours_path(dst), "w"))


def report_path(path):
    """~/ob-editor/qc/reports/<name>__<8 hex of the full path>.json: one report per file, even when two files share a name."""
    import hashlib
    h = hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:8]
    return os.path.join(QC, "reports", f"{os.path.splitext(os.path.basename(path))[0]}__{h}.json")


def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,bit_rate",
                        "-show_entries", "format=duration,size,bit_rate", "-of", "json", path], capture_output=True, text=True).stdout
    return json.loads(o or "{}")


def c_format(path, info, long):
    v = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), None); a = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), None)
    if not v: return "FAIL", "no video stream"
    w, h = int(v["width"]), int(v["height"]); n, d = (int(x) for x in v["r_frame_rate"].split("/")); fps = n / d
    bad, warn = [], []
    if not long and abs(w / h - 9 / 16) > 0.01: bad.append(f"{w}x{h} is not 9:16")
    elif not long and w != 1080: warn.append(f"{w}x{h} (expected 1080x1920)")
    if not 29.9 <= fps <= 30.01: warn.append(f"{fps:.2f} fps")
    if not a: bad.append("no audio")
    else:
        if a.get("codec_name") != "aac" or a.get("sample_rate") != "48000": warn.append(f"audio {a.get('codec_name')} {a.get('sample_rate')} Hz")
        if int(a.get("bit_rate") or 0) < 192000: warn.append(f"audio {int(a.get('bit_rate') or 0) // 1000}k")
    vb = int(v.get("bit_rate") or info.get("format", {}).get("bit_rate") or 0)
    if vb and vb < 6_000_000: warn.append(f"video {vb / 1e6:.1f} Mbps")
    return ("FAIL" if bad else "WARN" if warn else "PASS"), "; ".join(bad + warn) or f"{w}x{h} {fps:.2f} fps, video {vb / 1e6:.1f} Mbps"


def c_size(path, info):
    mb = int(info.get("format", {}).get("size", 0)) / 1e6
    return ("WARN" if mb > 30 else "PASS"), f"{mb:.0f} MB" + (" (send a 720p preview to his phone)" if mb > 30 else "")


def transcript(path):
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, "a.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
        o = subprocess.run(["whisper-cli", "-m", os.path.expanduser("~/.whisper-models/ggml-medium.en.bin"), "-f", w, "-ml", "1", "-sow", "-np"],
                           capture_output=True, text=True).stdout
    out = []
    for l in o.splitlines():
        m = re.match(r"\[(\d+):(\d+):([\d.]+) --> [\d:.]+\]\s*(.*)", l)
        if m and m[4].strip() and not m[4].strip().startswith(("(", "[", "♪")): out.append((int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), m[4].strip()))
    return out


_APPLE_DOWN = [0.0]   # until when Apple speech counts as unavailable (time.time())


def _speech_words(wav):
    """speech_words' output for wav, or None when Apple speech is unavailable (11-03 Mac mini: while another job holds a big
    Vision model, the Neural Engine refuses the speech model and speech_words crashes). Back off 10 s, then 20 s; after that
    Apple counts as down for 2 minutes, so the rest of a contended gate run doesn't wait again and says so instead."""
    if time.time() < _APPLE_DOWN[0]: return None
    for wait in (10, 20, None):
        r = subprocess.run([os.path.join(BIN, "speech_words"), "words", wav], capture_output=True, text=True)
        if r.returncode == 0 and "[" in r.stdout and not re.search(r"ANE|Espresso", r.stderr): return r.stdout
        if wait: time.sleep(wait)
    _APPLE_DOWN[0] = time.time() + 120; return None


def apple_words(path):
    """Apple's on-device transcript (bin/speech_words), word for word. Whisper smooths over false starts: on the raw 10/10 take
    it heard only the redo and dropped "...have it. Cut that cloud." Apple keeps them, so retake cues are read from both."""
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, "a.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
        o = _speech_words(w)
    if o is None: return None   # unavailable: c_cues says so instead of passing on a scan that never ran
    try: return [(x["s"], x["w"]) for x in json.loads(o[o.index("["):])]
    except ValueError: return None


_SW = {}
def source_words(src, t, half=10.0):
    """Apple's words (with its punctuation) of `src` within `half` s of t, in source seconds."""
    lo = max(0.0, t - half); key = (src, round(lo, 1))
    if key not in _SW:
        with tempfile.TemporaryDirectory() as td:
            w = os.path.join(td, "w.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{lo:.3f}", "-t", f"{2 * half:.3f}", "-i", src, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
            o = _speech_words(w)
        if o is None: _SW[key] = None   # unavailable (11-03): valley_cut and the sentence checks report the edge unchecked
        else:
            try: _SW[key] = [dict(w=x["w"], s=x["s"] + lo, e=x["e"] + lo) for x in json.loads(o[o.index("["):])]
            except ValueError: _SW[key] = []
    return _SW[key]


def speech_env(src):
    """Z.level_env of a source with the rumble under 150 Hz filtered out, for the edge check. Mic handling, a desk thump or room
    rumble isn't his voice: on C4416 (11-04) him picking up the mic before his first line sat at -40 dB full band, 25 dB under
    his speech, steady with no dip, and read as talking at a clean cut 60 ms before his "I". Words keep their level through the
    filter (most of a word's energy sits above 150 Hz), so a clipped word still reads as speech."""
    import zero_dead as Z
    from scipy.signal import butter, sosfiltfilt
    x = Z.decode(src) if isinstance(src, str) else np.asarray(src, np.float32)
    if len(x) < 64: return Z.level_env(x)
    return Z.level_env(sosfiltfilt(butter(2, 150, "highpass", fs=16000, output="sos"), x.astype(np.float64)).astype(np.float32))


def valley_cut(src, e, t):
    """An edge between two words said in one breath where the other word is not used: the FDOE's "...start the day." runs
    straight into a discarded "Research shows" with only a dip between them (2026-10-28), so no pause exists to test. It is
    clean when it sits at Apple's word boundary (60 ms either side) and 15 dB under the sound on both sides within 80 ms. A
    cut inside a word fails one or the other: mid-vowel is no dip, and a stop inside a word ("Tri|ple") is no word boundary."""
    import zero_dead as Z
    i = int(round(t / Z.HOP))
    if i < 9 or i + 9 >= len(e): return False
    v = float(e[i - 1:i + 2].min())
    if v > float(e[i - 8:i + 1].max()) - 15 or v > float(e[i:i + 9].max()) - 15: return False
    ws = source_words(src, t)
    if ws is None: return None   # Apple's word edges unavailable: unchecked, which the edge check never counts as clean
    return any(w0["e"] - 0.06 <= t <= w1["s"] + 0.06 for w0, w1 in zip(ws, ws[1:]))


def c_edges(path, segs=None):
    """No word cut off (OB 2026-10-25 "you cut me off mid word"; 10-28 "stop cutting me off when im saying a word").
    Always: the file must not start or end while he is talking (the first or last 10 ms at full speech level, with no onset
    rise at the start). With segs, the render's pieces in order as [(source_audio, start_s, end_s), ...] (every engine knows
    them): each piece's start and end must sit outside his words in the SOURCE audio, below the line's speech level
    (p90 - 20 dB over the 2 s around it). That is where the mocks of 10-28 failed: clip edges picked by time.
    A piece cut from one of our own renders is followed down to that render's recorded raw pieces (lineage), so every cut
    INSIDE it is checked too; a render whose pieces were never recorded fails closed (M27: the counter mock was cut from the
    posted FDOE, whose own cuts clipped him, and only the mock's two outer edges were checked).
    A sound-only splice detector was tried first and dropped: in voiced speech a 2 ms window between glottal pulses looks
    like a fade notch, so it flagged clean files. Found on 10-28: the posted C4378 1B ends on "follow" still sounding."""
    import zero_dead as Z
    x = Z.decode(path); sr = 16000
    if len(x) < sr: return "SKIP", "too short"
    bad, unknown, inh, soft = [], [], set(), []
    if segs:   # down to the raw take (lineage), then pieces that run straight on (same source, same place in the file) are one
        # stretch of his voice: the picture may cut there, the sound does not ("615 calories. I love ...": one breath, two shots)
        given = {x[0] for x in segs}; segs, unknown = lineage(segs); mg = []
        inh = {os.path.basename(g) for g in given - {x[0] for x in segs}}   # renders whose inner cuts were checked through them
        for src, a, b, t in segs:
            if mg and mg[-1][0] == src and abs(mg[-1][2] - a) < 0.002 and abs(mg[-1][3] + mg[-1][2] - mg[-1][1] - t) < 0.002:
                mg[-1] = (src, mg[-1][1], b, mg[-1][3])
            else: mg.append((src, a, b, t))
        segs = mg
        for u in dict.fromkeys(unknown):
            bad.append(f"cut from {os.path.basename(u)}, an edited render whose own cuts were never recorded: every cut inside it "
                       f"is unchecked, so rebuild from the raw take (or record that render's pieces)")
    env = Z.level_env(x); P = float(np.percentile(env, 90))
    def rms(sig, a, b):
        a, b = max(0, int(a * sr)), min(len(sig), int(b * sr))
        return 20 * np.log10(np.sqrt(np.mean(sig[a:b].astype(np.float64) ** 2)) + 1e-9) if b > a else -120.0
    dur = len(x) / sr
    # past the 5 ms edge fades: a clean start is quiet and then rises into the first word; a clean end has decayed. A cut word
    # is already loud right after the fade-in, or still loud right before the fade-out (no decay)
    first, later = rms(x, 0.006, 0.020), rms(x, 0.040, 0.060)
    if first > P - 20 and first > later - 6: bad.append(f"the file starts mid-word ({first:.0f} dB right at the start)")
    last, before = rms(x, dur - 0.045, dur - 0.025), rms(x, dur - 0.090, dur - 0.065)   # AAC softens the final ~20 ms
    if last > P - 20 and last > before - 6: bad.append(f"the file ends mid-word ({last:.0f} dB right at the end)")
    n_checked = 0
    if segs:
        cache = {}
        for k, (src, a, b, _t) in enumerate(segs):
            if src not in cache: cache[src] = speech_env(src)
            e = cache[src]
            for side, t in (("starts", a), ("ends", b)):
                i = int(round(t / Z.HOP)); w = e[max(0, i - 100):i + 100]
                if len(w) < 10: continue
                # outside the piece, the 0.1 s just before a start or just after an end must be a pause: 15 dB under his
                # speaking level (the FDOE's clip and music bed sit about -35 dB under him, so "silent" can't be the test)
                Pl = float(np.percentile(w, 90)); o = e[max(0, i - 10):i] if side == "starts" else e[i:i + 10]
                lv = float(20 * np.log10(np.mean(10 ** (o / 20)) + 1e-9)) if len(o) else -120.0
                # a pause: 25 dB under his speech on a clean mic (a soft "-ness" tail at -18 is still the word), or down near
                # the bed where one runs under him (the FDOE: his pauses sit about -35 dB, 6 dB over the bed's floor)
                floor = float(np.percentile(e[max(0, i - 300):i + 300], 10)); lim = max(floor + EDGE_FLOOR_MARGIN, Pl - 25)
                n_checked += 1
                vc = valley_cut(src, e, t) if lv > lim else True
                if vc is None: bad.append(f"piece {k + 1} {side} unchecked: sound at the edge and Apple's word edges unavailable (Neural Engine busy?), rerun the gate ({os.path.basename(src)} {t:.2f}s)")
                elif not vc: bad.append(f"piece {k + 1} {side} inside his speech ({os.path.basename(src)} {t:.2f}s, {lv:.0f} dB vs speech {Pl:.0f})")
    if segs:   # the clip's own first and last words: whole sentences (OB 10-28: "you still cut off on the fdoe"; it ended on
        # "...a probiotic for your gut health" with "and high protein, triple whammy" still to come)
        for side, (src, t) in (("starts", (segs[0][0], segs[0][1])), ("ends", (segs[-1][0], segs[-1][2]))):
            ws = source_words(src, t)
            if ws is None: soft.append(f"the clip's {'first' if side == 'starts' else 'last'} sentence unchecked (Apple's words unavailable: Neural Engine busy?), rerun the gate"); continue
            if not ws: continue
            e2 = cache.get(src) if segs else None
            if e2 is None: e2 = cache[src] = speech_env(src)
            Pt = float(np.percentile(e2[max(0, int(t / Z.HOP) - 100):int(t / Z.HOP) + 100], 90))
            def sounds(w, lo, hi):   # the word makes sound between lo and hi (the ASR stretches words over pauses: "So" before
                i0, i1 = int(max(w["s"], lo) / Z.HOP), int(min(w["e"], hi) / Z.HOP)   # the 10-28 kick clip's end had no sound in it)
                return i1 > i0 and float(e2[i0:i1].max()) > Pt - 15
            def said(lo, hi):   # real speech between lo and hi, heard on its own: Apple wrote a "For" over the intro music of
                # C4364's reacted reel (10-28) and the music is loud enough to "sound"; whisper medium heard "(upbeat music)" there
                # and Apple, given that span alone, heard nothing. A real word just outside the clip is still heard alone.
                lo = max(0.0, lo)
                if hi - lo < 0.05: return False
                with tempfile.TemporaryDirectory() as td:
                    a = os.path.join(td, "w.wav")
                    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{lo:.3f}", "-t", f"{hi - lo:.3f}", "-i", src, "-af",
                                    "adelay=400:all=1,apad=pad_dur=0.4", "-ac", "1", "-ar", "16000", a], check=True)
                    o = _speech_words(a)
                if o is None:   # can't tell: block the edge as unchecked rather than pass it
                    soft.append(f"the clip {side} on an unchecked sentence edge (Apple's words unavailable: Neural Engine busy?), rerun the gate"); return False
                try: return bool(json.loads(o[o.index("["):]))
                except ValueError: return False
            if side == "starts":
                f = next((k for k, w in enumerate(ws) if w["e"] > t + 0.02 and sounds(w, t, 1e9)), None)
                if f is not None and f > 0 and not ws[f - 1]["w"].rstrip('"\'').endswith((".", "?", "!")) and ws[f]["s"] - ws[f - 1]["e"] < 0.6 \
                        and said(ws[f - 1]["s"] - 0.25, t):
                    bad.append(f"the clip starts mid-sentence ('...{ws[f - 1]['w']} | {ws[f]['w']}...')")
            else:
                l = max((k for k, w in enumerate(ws) if w["s"] < t - 0.02 and sounds(w, 0, t)), default=None)
                if l is not None and l + 1 < len(ws) and not ws[l]["w"].rstrip('"\'').endswith((".", "?", "!")) and ws[l + 1]["s"] - ws[l]["e"] < 0.6 \
                        and said(t, ws[l + 1]["e"] + 0.25):
                    bad.append(f"the clip ends mid-sentence ('...{ws[l]['w']} | {ws[l + 1]['w']}...')")
    note = (f"{n_checked} piece edges checked against the raw take" + (f" (incl. the cuts inside {', '.join(sorted(inh))})" if inh else "")
            if segs else "file start and end only (pass segs for every splice)")
    if not bad and soft: return "WARN", "; ".join(soft[:3]) + f" ({note})"
    return ("FAIL", "; ".join(bad[:6])) if bad else ("PASS", f"no word cut off; {note}")


def c_cues(heard, apple, dur=0.0):
    """apple None = speech_words failed (11-03: the Neural Engine refused its model). That is never "no retake cues heard":
    with whisper words the scan is whisper-only (WARN, or FAIL on a cue); with no words at all it FAILs over 5 minutes."""
    if not heard and not apple and dur > 20:
        return ("FAIL" if dur > 300 else "WARN"), ("no words heard: Apple's speech_words failed (Neural Engine busy?) and whisper heard nothing; rerun the gate"
                                                   if apple is None else "no words heard by whisper or Apple: the transcriber failed (rerun the gate) or the file has no speech")
    hits = []
    for name, ws in (("whisper", heard), ("apple", apple or [])):
        text = " ".join(w for t, w in ws)
        for m in CUE.finditer(text):
            k = len(text[:m.start()].split()); hits.append((ws[min(k, len(ws) - 1)][0], m.group(0), name))
    if hits: return "FAIL", "heard: " + ", ".join(f"'{w}' at {t:.1f}s ({n})" for t, w, n in hits[:6])
    weak = [(t, w) for ws in (heard, apple or []) for t, w in ws if CUE_WEAK.search(w)]
    if apple is None: return "WARN", "Apple words unavailable (speech_words failed: Neural Engine busy?): whisper-only cue scan" + (", check by ear: " + ", ".join(f"'{w}' at {t:.1f}s" for t, w in weak[:4]) if weak else ", no cues heard")
    return ("WARN", "check by ear: " + ", ".join(f"'{w}' at {t:.1f}s" for t, w in weak[:4])) if weak else ("PASS", "no retake cues heard (whisper + Apple)")


SPOKEN = {"gonna": ["going", "to"], "wanna": ["want", "to"], "gotta": ["got", "to"]}


def stoks(text):
    """takes.toks with the spoken forms spelled out: whisper writes "gonna" where Apple (and the script) wrote "going to" for the
    same sound (11-04 C4418: three "going to" -> "gonna" counted as missing words and failed a clean cut)."""
    import takes as K
    return [y for x in K.toks(text) for y in SPOKEN.get(x, [x])]


def _heard_in_window(path, at, toks, half=2.5):
    """A word the full-file pass missed, looked for again in a 5 s window around it. Whisper over 2 minutes can slip on context
    (10-29, OB-1010-GUT-FEED: "you only need" came back as "donate", yet a 5 s window of the same file hears it clearly, and so
    did the full pass on the music copy of the same voice). A word the cut really took stays missing in the window too."""
    import takes as K
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, "w.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0.0, at - half):.2f}", "-t", f"{2 * half:.2f}", "-i", path,
                        "-vn", "-ac", "1", "-ar", "16000", w], check=True)
        got = iter([t for _, h in transcript(w) for t in stoks(h)])
    return all(t in got for t in toks)   # all of them, in order


def _heard_in_raw(segs, at, toks, half=4.0):
    """A word the render's whisper missed, listened for again in the RAW take: the kept pieces within 4 s of it, joined as the edit
    joins them, without the bed (C4401 10-30: "the guac is going to be" came back as "guacas could" over the music, and one of its
    pauses was cut, so it spans two pieces; whisper on the raw pieces hears it clearly). Kept pieces are copied verbatim, so words
    heard in them are in the render too; a word the cut removed lies in no kept piece and is never found here (and every piece
    edge is checked word by word in c_edges)."""
    import takes as K
    near = [sg[:4] for sg in (segs or ()) if len(sg) >= 4 and sg[3] < at + half and sg[3] + (sg[2] - sg[1]) > at - half]
    if not near: return False
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for k, (src, a, b, t0) in enumerate(near):
            lo, hi = max(a, a + (at - half - t0)), min(b, a + (at + half - t0))
            if hi - lo < 0.05: continue
            w = os.path.join(td, f"p{k:02d}.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{lo:.3f}", "-t", f"{hi - lo:.3f}", "-i", src, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
            parts.append(w)
        if not parts: return False
        lst = os.path.join(td, "l.txt"); open(lst, "w").write("".join(f"file '{x}'\n" for x in parts)); j = os.path.join(td, "j.wav")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", j], check=True)
        got = iter([t for _, h in transcript(j) for t in stoks(h)])
    return all(t in got for t in toks)


def c_words(heard, script_path, path=None, segs=None):
    import takes as K
    raw = open(script_path).read()
    try: lines = json.loads(raw); lines = [l[1] if isinstance(l, (list, tuple)) else l for l in lines]
    except ValueError: lines = [l for l in raw.splitlines() if l.strip()]
    exp = [t for l in lines for t in stoks(l)]; got = [(t, at) for at, w in heard for t in stoks(w)]
    sm = difflib.SequenceMatcher(None, exp, [t for t, _ in got], autojunk=False); miss, runs, diffs = 0, 0, []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal": continue
        at = got[j1][1] if j1 < len(got) else (got[-1][1] if got else 0)
        diffs.append(f"{at:.1f}s {op} [{' '.join(exp[i1:i2])}] -> [{' '.join(t for t, _ in got[j1:j2])}]")
        if op in ("delete", "replace"):
            k = (i2 - i1) - (j2 - j1 if op == "replace" else 0)
            if k > 0 and path and _heard_in_window(path, at, exp[i1:i2]):
                diffs[-1] += " (heard in a 5 s window: a full-file slip, not counted)"; continue
            if k > 0 and segs and _heard_in_raw(segs, at, exp[i1:i2]):
                diffs[-1] += " (heard in the raw take inside a kept piece: whisper slipped on the mix, not counted)"; continue
            if k > 0: miss += k
            if op == "delete" and i2 - i1 >= 2: runs += 1
    st = "FAIL" if runs or miss >= 3 else ("WARN" if diffs else "PASS")
    missed = [d for d in diffs if (" delete [" in d or " replace [" in d) and "not counted" not in d]
    return st, f"match {sm.ratio():.3f}, {miss} missing{' in ' + str(runs) + ' runs' if runs else ''}; " + ("; ".join((missed + [d for d in diffs if d not in missed])[:10]) if diffs else "every script word heard")


VOICE_GAP_MAX = 0.45


def c_silence(path):
    """Dead air: silence over 0.2 s, and (11-04) no voice over 0.45 s on the voice band. C4416's first line opened on 2.3 s of
    him picking up the mic: thumps and rumble at -20 to -40 dB full band, so not "silence", but no voice at all (OB 11-03:
    "still feels like there is dead space after im done talking, needs to be faster pace")."""
    import zero_dead as Z
    pm = float(os.environ.get("OB_QC_PAUSE_MAX", 0) or 0)   # T21 (Sarah Snow) keeps her breaths: the plan's keep_pauses + 0.15 s
    d = Z.dead_space(path); bad = d["silent_pct"] > (12.0 if pm else 3.0) or d["longest_silence"] > max(0.2, pm)
    x = Z.decode(path); gap, at = 0.0, 0.0
    if len(x) > 16000:
        from scipy.signal import butter, sosfiltfilt
        e = Z.level_env(sosfiltfilt(butter(2, 150, "highpass", fs=16000, output="sos"), x.astype(np.float64)).astype(np.float32))[30:-30]
        q = e < np.percentile(e, 90) - Z.TAIL; k = 0
        while k < len(q):
            if q[k]:
                j = k
                while j < len(q) and q[j]: j += 1
                if (j - k) * Z.HOP > gap: gap, at = (j - k) * Z.HOP, (k + 30) * Z.HOP
                k = j
            else: k += 1
    vbad = gap > max(VOICE_GAP_MAX, pm)
    det = f"silence {d['silent_pct']}% (longest {d['longest_silence']} s), dead {d['dead_pct']}%, longest without voice {gap:.2f} s"
    if vbad: det += f" at {at:.1f}s (rumble or handling noise, not a pause: cut it)"
    return ("FAIL" if bad or vbad else "PASS"), det


def c_audio(path):
    import voice_master as VM
    r = VM.check(path); fail = r["flat_tops"] > 0 or (r["true_peak"] is not None and r["true_peak"] > -1.0)
    warn = r["lufs"] is None or not -15.5 <= r["lufs"] <= -12.5
    return ("FAIL" if fail else "WARN" if warn else "PASS"), f"{r['lufs']} LUFS, true peak {r['true_peak']}, flat-topped peaks {r['flat_tops']}, LRA {r['lra']}"


def c_motion(path):
    import motion_score as M
    m = M.measure(path, 1.2)
    if m is None: return "FAIL", "unreadable"
    if m["flash"]: return "FAIL", f"one-frame flashes at {', '.join(f'{t:.2f}s' for t in m['flash'][:8])}"
    st = "WARN" if (m["first"] or 0) > 1.5 else "PASS"
    return st, f"live {m['live']}/10, idle {m['idle_share']:.0%}, first move {m['first']} s, {m['events_min']} events/min"


def frames_text(path, every=0.5):
    """[(t, W, H, faces[[x,y,w,h]], texts[[x,y,w,h,str]])] every `every` s, via bin/frame_obstacles, VISION_JOBS frames at a time.
    A frame whose call crashes (the Neural Engine refusing a model, 11-03) is retried once; if more than a fifth still fail, the
    gate stops instead of passing text checks it never ran."""
    from concurrent.futures import ThreadPoolExecutor
    def one(f):
        for k in range(2):
            r = subprocess.run([os.path.join(BIN, "frame_obstacles"), f], capture_output=True, text=True)
            try: return json.loads(r.stdout)
            except ValueError: time.sleep(2)
        return None
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", f"fps={1 / every}", "-q:v", "3", os.path.join(td, "f%05d.jpg")], check=True)
        fs = [os.path.join(td, f) for f in sorted(os.listdir(td))]
        with ThreadPoolExecutor(VISION_JOBS) as ex: ds = list(ex.map(one, fs))
    bad = sum(d is None for d in ds)
    if fs and bad > 0.2 * len(fs): raise RuntimeError(f"frame_obstacles failed on {bad} of {len(fs)} frames (Apple Vision / Neural Engine): rerun the gate")
    return [(k * every, d["w"], d["h"], d.get("faces", []), d.get("texts", [])) for k, d in enumerate(ds) if d]


_DICT = None
def real_text(s):
    """Text a viewer reads: at least one dictionary word of 3+ letters (or a 2+ digit number). Apple's fast OCR reads gym
    equipment, shirts and wood grain as junk ("rli", "Jll:Ill,"), which isn't text on screen."""
    global _DICT
    if _DICT is None:
        try: _DICT = {w.strip().lower() for w in open("/usr/share/dict/words")}
        except OSError: _DICT = set()
    ch = [c for c in str(s) if not c.isspace()]
    if not ch or sum(c in "Il1|!i:;,.'`" for c in ch) > 0.5 * len(ch): return False   # vertical stripes read as I, l, 1
    if re.fullmatch(r"[.,:;'`|!]+\d{1,3}[.,:;'`|!]+", "".join(ch)): return False   # a logo read as digits in dots ('.44.' = the LA on his cap, C4395 0:50)
    if re.fullmatch(r"[a-z]\d{1,3}|\d{1,3}[a-z]", "".join(ch)): return False   # the LA on his cap read as a lowercase letter glued to digits ('r41', C4407 test 18.5 s); our overlays are upper case, so "10K" is still text
    if re.fullmatch(r"[.,:;'`|!\-]*(?:TT\d{1,3}|\d{1,3}TT)[.,:;'`|!\-Il]*", "".join(ch)): return False   # the same LA read as doubled T glued to digits ('TT41' C4415 v4 0:04, '74TT,-I' v3 8:06)
    toks = re.findall(r"[A-Za-z']+|\d{2,}", str(s))
    return any(t.isdigit() or (len(t) >= 3 and (t.lower().strip("'") in _DICT or t.lower().rstrip("s") in _DICT)) for t in toks)


def his_track(fr):
    """His face: the face cluster (by centre) present in the most sampled frames (at least 30% of them)."""
    cents = [((x + w / 2) / W, (y + h / 2) / H, t) for t, W, H, fs, ts in fr for x, y, w, h in fs if w * h > 0.002 * W * H]
    if not cents: return None
    best, bc = 0, None
    for cx, cy, _ in cents:
        n = len({t for x, y, t in cents if abs(x - cx) < 0.12 and abs(y - cy) < 0.10})
        if n > best: best, bc = n, (cx, cy)
    return bc if best >= 0.3 * len(fr) else None


def his_face(fr, k, track, card=False):
    """His face box in frame k: the detected face near his track; when text hides his face from the detector (it can't see
    a face under "WATCH THIS"), his box from the nearest frame within 1 s that has it, if there is one on both sides or he
    is in the same place on one side (he hasn't left the shot). Not inside a full-screen card (card=True): the card
    replaced the A-roll, so no face of his is under its text (C4395: all 15 chapter cards borrowed his box and failed).
    Only from a frame with more faces than this one: text that hides his face leaves one fewer. The same count or more means
    the shot changed between them (C4397 at 26.0 s, 10-29: a split frame, her face on top and his below, borrowed his
    full-frame punch-in box from 1 s before and failed on its seam caption)."""
    def near(i):
        t, W, H, fs, ts = fr[i]
        c = [f for f in fs if abs((f[0] + f[2] / 2) / W - track[0]) < 0.15 and abs((f[1] + f[3] / 2) / H - track[1]) < 0.12]
        return max(c, key=lambda f: f[2] * f[3]) if c else None
    faces = lambda i: sum(f[2] * f[3] > 0.002 * fr[i][1] * fr[i][2] for f in fr[i][3])
    f = near(k)
    if f or card: return f
    before = next((near(i) for i in range(k - 1, max(-1, k - 3), -1) if near(i) and faces(i) > faces(k)), None)
    after = next((near(i) for i in range(k + 1, min(len(fr), k + 3)) if near(i) and faces(i) > faces(k)), None)
    return before or after if (before and after) else None


def dashy(s, short=True):
    """A dash on screen: an em or en dash anywhere; in short copy also a hyphen used as one, since OCR reads an em dash as "-"
    ("FAT LOSS- THE TRUTH"). Long lines are other people's text, where a study's "p = 0.05" reads as "p - 0.05". A suspended
    hyphen is a hyphen ("Low- vs high-load", "pre- and post-workout": the Schoenfeld 2017 study card on C4395)."""
    if re.search(r"[—–]", s): return True
    s = re.sub(r"(\w)-(\s+(?:vs\.?|and|or|to|&)\s+\w+-\w)", r"\1\2", s, flags=re.I)
    # a dash joins two words: "SEARCH- ." was the mic beside the punch word "NO RESEARCH" (C4364 R/G/S at 13.0 s, 10-28), no dash
    # and a real word (2+ characters) sits before it: OCR read the sleeve beside her caption "BECAUSE THAT'S HOW," as
    # "I -BECAUSE" (C4380 R at 11.0 s, 10-29)
    # a hyphen between two numbers is a range, not a dash: Hally's own caption "so it was like 10 - 12g of fiber." on the top screen
    # (C4413 at 47.0 s, 11-03; OCR: ".ww,likoa4- 12gi")
    s = re.sub(r"(\d)\s*-\s*(?=\d)", r"\1 to ", s)
    # our client cards' date labels "BEFORE · Jul 2025" / "AFTER · Sep 2025": OCR reads the middle dot as "-" (C4424 v2 at 19.5 s, 11-07)
    s = re.sub(r"\b(BEFORE|AFTER)\s*-\s*(?=(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s*\d)", r"\1 ", s, flags=re.I)
    return bool(short and re.search(r"[A-Za-z0-9]{2,}\s*-\s+\w|[A-Za-z0-9]{2,}\s+-\w", s))


def cover_spans(work):
    """[edit_in, edit_out] of every event of a long-form edit that leaves no A-roll on screen (assemble.is_cover: chapter,
    num, versus, checklist and other full cards, b-roll inserts, client clips, any "full" side card)."""
    sys.path.insert(0, BIN); import assemble
    out = []
    for e in json.load(open(os.path.join(work, "events_resolved.json")))["events"]:
        if assemble.is_cover(e): out.append([e["edit_in"], e["edit_out"]])
        elif e.get("face"):   # a reel that cuts back to him (10-29): only its footage stretches hide him
            t = e["edit_in"]
            for a0, a1 in sorted(e["face"]):
                if e["edit_in"] + a0 > t: out.append([t, e["edit_in"] + a0])
                t = e["edit_in"] + a1
            if t < e["edit_out"]: out.append([t, e["edit_out"]])
    return out


def _cache(kind, path, fn, *key):
    """frames_text and apple_words per file (path, size, mtime) in ~/ob-editor/qc/cache: on a 34-minute long-form file the OCR
    pass takes about 25 minutes, and a gate fix shouldn't cost another (C4395, 2026-10-28). Empty results aren't kept."""
    import hashlib
    st = os.stat(path); tag = f"{os.path.abspath(path)}|{st.st_size}|{st.st_mtime}|{kind}|{key}"
    cp = os.path.join(QC, "cache", hashlib.sha1(tag.encode()).hexdigest()[:16] + ".json")
    if os.path.exists(cp): return json.load(open(cp))
    v = fn()
    if v: os.makedirs(os.path.dirname(cp), exist_ok=True); json.dump(v, open(cp + ".tmp", "w")); os.replace(cp + ".tmp", cp)
    return v


def spoken_caption(s, t, said):
    """OCR's "-" between two words of a caption of his (C4361 10-30: "PROGRESSIVELV- OVERLOAD VOUR" where the white word meets
    the yellow live word, and "LONGE,ST- HEALTHIES.T_, LIFE"): a line whose every word he said within 2.5 s is our caption of his
    own words, which never carry a dash. An em or en dash still FAILs, and so does a dash in a line he didn't say."""
    import takes as K
    if not said or re.search(r"[\u2014\u2013]", s): return False
    s = re.sub(r"[^\w\s'-]|_", "", s)   # OCR scatters dots and commas inside words ("LONGE,ST", "HEALTHIES.T_")
    toks = [x for x in K.toks(s.replace("-", " ")) if len(x) >= 2]; near = [z for tt, z in said if abs(tt - t) <= 2.5]
    return bool(toks) and bool(near) and all(max(K.sim(x, z) for z in near) >= 0.7 for x in toks)


def cam_spoken(s, t, said):
    """any token of an OCR reading resembles a word said within 3 s of it (our captions are the speaker's words)"""
    import takes as K
    toks = [x for x in K.toks(re.sub(r"[^\w\s%+]", " ", s)) if x]; near = [z for tt, z in said if abs(tt - t) <= 3.0]
    return any(K.sim(x, z) >= 0.6 for x in toks for z in near)


def c_text(fr, long, cards=None, said=None, theirs=None, ours=None):
    """theirs: [t0, t1(, x0, y0, x1, y1)] where the screen (or that rect of it) shows another creator's own footage: her burned-in
    captions are not our copy, so the dash lint skips them (11-03 C4413: Hally's "10 - 12g" OCR'd as "likoolq- 12").
    cards: [t0, t1] edit spans with no A-roll on screen (cover_spans). ffmpeg's fps filter keeps the last frame of each
    interval, so sampled frame k shows about k * every + every / 2 (C4395's '88.0 s' frame was 0.9 s into its chapter card).
    ours: [t0, t1] spans where the render's own graphics are on screen. A reading on his face outside all of them is the camera's own
    picture, not our copy (C4415 v3 8:06, 11-04: OCR read his LA cap and the mic print as '74TT,-I' with no overlay on screen)."""
    track = his_track(fr); over, lint_f, lint_w, unsafe, ear, cam_txt = [], [], [], [], [], []
    every = fr[1][0] - fr[0][0] if len(fr) > 1 else 0.5
    covered = lambda t: any(a - 0.05 <= t + every / 2 <= b + 0.05 for a, b in (cards or ()))
    hers = lambda t, x, y, w, h: any(r[0] - 0.05 <= t + every / 2 <= r[1] + 0.05 and (len(r) < 6 or (x >= r[2] - 12 and y >= r[3] - 12 and
                                     x + w <= r[4] + 12 and y + h <= r[5] + 12)) for r in (theirs or ()))
    for k, (t, W, H, fs, ts) in enumerate(fr):
        face = his_face(fr, k, track, covered(t)) if track else None
        for x, y, w, h, s in ts:
            s = str(s).strip()
            if len(s.replace(" ", "")) <= 2 or not real_text(s): continue
            if face:
                lead = len(s) - len(s.lstrip("'\"`)]}|!:;,. \u2022&*~^"))   # OCR reads his ear or hair beside a line as "') " (C4395 2:59)
                # or "'\u2022& " (C4398 v2 0:52, the box stretched over his head to the words): not text
                m_ = re.match(r"^[\W_]*(?:[A-Za-z]{1,2}[\W_]+){1,2}(?=[A-Z]{3,}|[A-Z]+'[A-Z])", s)   # and as short junk tokens before our copy:
                if m_ and len(m_.group(0)) > lead: lead = len(m_.group(0))   # "_.JA '& FOR BERR" (C4415 rev 2, 1:50: his ear + cap edge glued to a tag)
                x, w = x + w * lead / len(s), w * (1 - lead / len(s))
                ix = max(0, min(x + w, face[0] + face[2]) - max(x, face[0])); iy = max(0, min(y + h, face[1] + face[3]) - max(y, face[1]))
                if (ix * iy > 0.25 * w * h or ix * iy > 0.08 * face[2] * face[3]) and ours is not None and not any(a - 0.15 <= t + every / 2 <= b + 0.15 for a, b in ours):
                    cam_txt.append((t, s))
                elif ((ix * iy > 0.25 * w * h or ix * iy > 0.08 * face[2] * face[3]) and said and not re.search(r"[A-Za-z]{3}", s)
                      and not cam_spoken(s, t, said)):
                    # 11-06 Rythm (Client R): '14bl' (her mic transmitter), '-41' (kitchen background), 'F741' (the heat pack label at her
                    # chin) FAILed text_face. No 3-letter word and nothing she said within 3 s: the camera's own picture, not our copy.
                    # Our captions are her words, so a caption on her face (numbers included, "25%") still matches what she said.
                    cam_txt.append((t, s))
                elif ((ix * iy > 0.25 * w * h or ix * iy > 0.08 * face[2] * face[3]) and h < 0.07 * face[3]
                      and (not re.search(r"[A-Za-z]{3}", s) or (h < 22 * H / 1920 and len(re.sub(r"[^A-Za-z]", "", s)) <= 4))):
                    # 11-10 workshop ad 4 talking, 43.0 s: '":of44', 46x15 px on his upper-lip stubble (face 284 px tall, checked by eye).
                    # Our smallest copy over a face is a caption (~45 px read at 58 pt): a reading under 7% of his face height with no
                    # 3-letter word is his skin, not our text. 11-11 ad 4 talking V08, 42.5 s: '.ILA' (42x13 px at his upper lip, face 282 px
                    # tall) read 'Ila', a dictionary word: a reading under 22 px (a third of our smallest copy) with 4 letters or fewer is skin too.
                    cam_txt.append((t, s))
                elif ix * iy > 0.25 * w * h or ix * iy > 0.08 * face[2] * face[3]:
                    # a short lower-case reading across the side edge of his face box, small next to his face, is his ear or hair
                    # (C4407 2:57, 11-03: 'rie', a Web2 dictionary word, on his ear). Our copy is upper case and longer; it's a WARN to check
                    if (len(re.sub(r"[^A-Za-z]", "", s)) <= 3 and s == s.lower() and h < 0.15 * face[3]
                            and (x < face[0] < x + w or x < face[0] + face[2] < x + w)): ear.append((t, s))
                    else: over.append((t, s))
            short = len(s.split()) <= 8   # our copy (titles, hooks, captions); long lines are screenshots of other people's text
            if dashy(s, short) and not spoken_caption(s, t, said) and not hers(t, x, y, w, h): lint_f.append((t, s))
            if short and re.search(r"\b(free|team)\b", s, re.I): lint_w.append((t, s))
            sc = H / 1920
            if not long and (y < 220 * sc or y + h > H - 420 * sc): unsafe.append((t, s))
    fmt = lambda L: ", ".join(f"{t:.1f}s '{s[:28]}'" for t, s in L[:5])
    res = {"text_face": ("FAIL", f"{len(over)} hits: {fmt(over)}") if over else (("WARN", f"{len(ear)} short readings at the edge of his face (his ear or hair?), check by eye: {fmt(ear)}") if ear else
                        ("PASS" if track else "WARN", ("no text on his face" + (f"; {len(cam_txt)} readings outside our graphics are the camera's own picture (his cap, the mic): {fmt(cam_txt)}" if cam_txt else "")) if track else "his face track not found: check by eye")),
           "text_lint": ("FAIL", f"dash: {fmt(lint_f)}") if lint_f else (("WARN", f"check: {fmt(lint_w)}") if lint_w else ("PASS", "no dashes, 'free' or 'team'")),
           "text_safe": ("WARN", f"{len(unsafe)} in the IG bands: {fmt(unsafe)}") if unsafe else ("PASS", "clear of the IG bands")}
    first = [s for t, W, H, fs, ts in fr if t == 0 for x, y, w, h, s in ts if real_text(s)]
    words3 = len(" ".join({str(s) for t, W, H, fs, ts in fr if t <= 3 for x, y, w, h, s in ts if real_text(s)}).split())
    res["hook"] = ("WARN", "no text on frame 1") if not first else (("WARN", f"{words3} words on screen in the first 3 s (a reacted clip's own text counts too)") if words3 > 9 and not long else ("PASS", f"frame 1: '{' '.join(map(str, first))[:50]}'"))
    return res


def c_captions(fr, apple, heard):
    """Captions say what he said: a caption word (3+ letters, lower part of the frame) must be heard within 2.5 s of it, in
    Apple's word-for-word transcript or whisper's (sim 0.7+). The 10/10 captions needed hand fixes ("bam" for "bare minimum",
    "Speeding up" for "Speed it up") because they came from the script, not from what he said. A word only counts when it
    is on screen in 2+ readings (0.5 s+): captions that slide in show cut-off fragments ("eanE" of "beans") for one reading,
    and a fragment that is part of a word he said nearby is not a mistake. WARN only: every listed word is checked by eye."""
    import takes as K
    said = [(t, x) for t, w in list(apple) + list(heard) for x in K.toks(w)]
    end = fr[-1][0] if fr else 0
    def part_of(tok, words):   # a cut-off piece of a heard word ("ple" of "people")
        return any(difflib.SequenceMatcher(None, tok, z).find_longest_match(0, len(tok), 0, len(z)).size >= 0.75 * len(tok) for z in words)
    seen = {}
    for t, W, H, fs, ts in fr:
        for x, y, w, h, s in ts: seen.setdefault(" ".join(K.toks(str(s))), set()).add(t)
    miss = {}
    for t, W, H, fs, ts in fr:
        if t > end - 1.0: continue   # the audio may end mid-sentence
        for x, y, w, h, s in ts:
            # captions: short lines in the lower part that change with his speech; a line on screen 3 s+ is a title, a label
            # or a card (her clip's own text, the Cronometer rows), checked by the other text checks instead
            if y < 0.45 * H or y > 0.90 * H or not real_text(s) or len(str(s).split()) > 6: continue
            if len(seen.get(" ".join(K.toks(str(s))), ())) > 6: continue
            for tok in K.toks(str(s)):
                if len(tok) < 3 or not tok.isalpha(): continue
                near = [z for tt, z in said if abs(tt - t) <= 2.5]
                if near and max(K.sim(tok, z) for z in near) < 0.7 and not part_of(tok, near): miss.setdefault(tok, []).append((t, str(s)))
    bad = [(v[0][0], tok, v[0][1]) for tok, v in miss.items() if len({t for t, s in v}) >= 2]
    if not bad: return "PASS", "every caption word was heard"
    bad.sort()
    return "WARN", f"{len(bad)} caption words never heard near them: " + ", ".join(f"{t:.1f}s '{tok}' in '{s[:26]}'" for t, tok, s in bad[:8])


def c_lookoff(src, pieces):
    import zero_dead as Z
    rows = Z.lookoff(src, json.load(open(pieces))); bad = [r for r in rows if r[5]]
    return ("FAIL" if bad else "PASS"), (f"{len(bad)} of {len(rows)} edges: " + ", ".join(f"{r[2]:.1f}s {r[5]}" for r in bad[:6])) if bad else f"{len(rows)} edges, eyes on"


OPEN_FACE_S = 3.0
def c_opener(cards, long):
    """M35 (OB 10-30, C4402: "my face is alwasy in the opener"): a long-form video opens on his face. No full-screen insert
    (stock, his own b-roll, a clip, a full card: anything assemble.is_cover counts) before 3 s. Reads the edit's cover spans,
    so it needs --work; a reel's opener is the hook check's job."""
    if not long: return "SKIP", "long-form rule (reels: hook)"
    if cards is None: return "SKIP", "needs --work (the edit's cover spans)"
    first = min((a for a, b in cards), default=None)
    if first is not None and first < OPEN_FACE_S:
        return "FAIL", f"a full-screen insert covers him from {first:.2f} s; his face holds at least the first {OPEN_FACE_S:.0f} s"
    return "PASS", ("no insert anywhere" if first is None else f"his face holds the first {first:.2f} s")


def c_vmaf(path, spec):
    ref, rs, ds, dur = spec.split(":")
    r = subprocess.run([sys.executable, "-I", os.path.join(BIN, "vmaf_check.py"), ref, path, "--ref-start", rs, "--dist-start", ds, "--dur", dur], capture_output=True, text=True)
    return ("FAIL" if r.returncode == 3 else "PASS" if r.returncode == 0 else "WARN"), (r.stdout.strip().splitlines() or ["no output"])[-1][:120]


CLIENT_TRIG = re.compile(
    r"\b(?:my|a|our)\s+clients?\b"
    r"|\bclients?\s+of\s+mine\b"
    r"|\bi(?:'ve|\s+have)?\s+(?:coached|worked\s+with|helped|help|trained)\b(?:\W+\w+){0,6}?\W+(?:people|clients|women|men|hundreds|thousands)\b"
    r"|\b(?:coach(?:ed|ing)?|clients?)\b(?:\W+\w+){0,8}?\W+over\s+a\s+decade\b"
    r"|\bover\s+a\s+decade\b(?:\W+\w+){0,6}?\W+(?:coach(?:ed|ing)?|clients?)\b", re.I)
CLIENT_PROOF = re.compile(r"client_proof|Progress Photos|Client & Testimonial|testimonial|before_after|transformation", re.I)


def client_triggers(words):
    """Times where OB talks about his own clients or his coaching tenure (ledger M56). words: [(t, word)] in order.
    "coaches are scared they won't get clients" (other coaches) doesn't count."""
    text, starts = "", []
    for t, w in words:
        starts.append((len(text), t)); text += str(w).strip() + " "
    out = []
    for m in CLIENT_TRIG.finditer(text):
        t = next((tt for pos, tt in reversed(starts) if pos <= m.start()), 0.0)
        if not out or t - out[-1][0] > 4.0: out.append((t, " ".join(m.group(0).split())))
    return out


def client_proof_spans(work):
    p = os.path.join(work, "events_resolved.json") if work else ""
    if not p or not os.path.exists(p): return None
    d = json.load(open(p)); ev = d if isinstance(d, list) else d.get("events", [])
    return [(float(e["edit_in"]), float(e.get("edit_out", float(e["edit_in"]) + 2.0))) for e in ev
            if e.get("edit_in") is not None and (e.get("client_proof") or CLIENT_PROOF.search(json.dumps(e)))]


def clients_verdict(trig, spans):
    if not trig: return "PASS", "no lines about his clients"
    if spans is None: return "SKIP", f"{len(trig)} client line(s) heard; needs --work (events_resolved.json) to check the proof on screen"
    miss = [(t, s) for t, s in trig if not any(a <= t + 3.0 and b >= t - 1.0 for a, b in spans)]
    if miss: return "FAIL", f"{len(miss)} of {len(trig)} client lines with no client on screen: " + ", ".join(f"{int(t // 60)}:{t % 60:04.1f} '{s[:40]}'" for t, s in miss[:6])
    return "PASS", f"all {len(trig)} client lines have client proof on screen"


def c_clients(heard, apple, work):
    words = heard or apple or []
    return clients_verdict(client_triggers(words), client_proof_spans(work))


def c_sfx(path, plan, long, dur):
    """Ledger M17 (OB 10-29: "use them when needed dont be obxious about them"), as code from 11-07 (sfx_check.py)."""
    if not plan or not os.path.exists(plan): return "SKIP", "no sound-effects plan (--sfx-plan, or --work with story/sfx_plan.json)"
    import sfx_check as SC
    st, detail, rows = SC.check(path, plan, bool(long), dur or None)
    return st, detail

# Ledger M58 + M59 (OB 11-07: "use real music first for short form and the viral ones that are in the bank before ever making it
# yourself, yt is a little different because of copyright rules so do copyright friendly", "use the sound effects from the bank
# first before making your own always"). Add a new pack or music folder here when it joins the bank.
_HOME = os.path.expanduser("~")
SFX_BANKS = (f"{_HOME}/ob-editor/assets/sfx_ob_drive/", f"{_HOME}/ob-editor/assets/sfx_tai/", f"{_HOME}/ob-editor/assets/sfx_real/",
             "/Volumes/T7/OB-EDITS/sfx-library/", f"{_HOME}/ob-editor/vendor/", "/Volumes/T7/MUSIC/freesound_community-")
SFX_MADE = (f"{_HOME}/ob-editor/assets/sfx/",)     # sfx.py's code-made kit (pop, whoosh, tick, thud): last resort only
MUSIC_BANKS = ("/Volumes/T7/MUSIC/", "/Volumes/T7/OB-EDITS/music/", "/Volumes/T7/funkavenue-feel-good-funk-anthem-572932.mp3",
               "/Volumes/T7/Nineteen.mp3", "/Volumes/T7/Chopin - Nocturne op.9 No.2.mp3")
MUSIC_MADE = re.compile(r"(?<![a-z])(forge|videomusicmaker|techguyver|suno|udio)(?![a-z])|\.midi?$")   # beds written by code or AI
SFX_FORGED = re.compile(r"(?<![a-z])forge(?![a-z])")   # earshot forge output (made in code)
MUSIC_NOT_YT = ("/Volumes/T7/MUSIC/", "/Volumes/T7/Nineteen.mp3", "/Volumes/T7/Chopin", "background.m4a")   # Lane B: commercial or unknown source
MUSIC_BLOCKED = {   # page checks 11-06 and 11-07 (MUSIC-LIBRARY.md); M57 for Tapis and Vastness
    "568181": "AI generated (Soul Jazz Sunny Cafe)", "sunny-cafe": "AI generated (Soul Jazz Sunny Cafe)",
    "588230": "AI generated + Content ID (Sugar Maple Groove)", "sugar-maple": "AI generated + Content ID (Sugar Maple Groove)",
    "591196": "AI generated + Content ID (Soul, echoes_of_lumen)", "spice-intrigue": "Content ID Registered (Spice Intrigue)",
    "618233": "its uploader posts AI music (Soul RnB)", "568174": "its uploader posts AI music (Soul Jazz Rainy Night)",
    "588903": "its uploader posts AI music (Lofi Soul)", "584902": "its uploader posts AI music (Funk And Soul Music)",
    "608133": "its uploader posts AI music (Soul Music)",
    "mixkit_615": "Tapis, banned for educational videos (M57)", "tapis": "Tapis, banned for educational videos (M57)",
    "mixkit_184": "Vastness, banned for educational videos (M57)", "vastness": "Vastness, banned for educational videos (M57)"}


def bank_verdict(hits, tracks, long):
    """hits = the SFX plan's [{"t", "file", "bank_miss"?}], tracks = the music files, long = YouTube's copyright rules."""
    F, W, ns, nm = [], [], 0, 0
    absp = lambda p: os.path.abspath(os.path.expanduser(str(p)))
    for h in hits or []:
        f = absp(h.get("file", "")) if h.get("file") else ""
        if not f: continue
        ns += 1; b = os.path.basename(f); at = f" at {float(h['t']):.1f} s" if h.get("t") is not None else ""
        made = f.startswith(SFX_MADE) or (bool(SFX_FORGED.search(f.lower())) and not f.startswith(SFX_BANKS))
        if made and not h.get("bank_miss"): F.append(f"made-in-code sound {b}{at}: the bank first (M59), or say what was searched in bank_miss")
        elif made: W.append(f"made-in-code sound {b}{at} (bank searched: {str(h['bank_miss'])[:60]})")
        elif not f.startswith(SFX_BANKS): W.append(f"sound outside the known banks: {b}{at} (add its pack to SFX_BANKS)")
    for t in dict.fromkeys(absp(x) for x in (tracks or []) if x):
        nm += 1; low = t.lower(); b = os.path.basename(t)
        why = next((w for k, w in MUSIC_BLOCKED.items() if k in low), None)
        if MUSIC_MADE.search(low) and not t.startswith(MUSIC_BANKS): F.append(f"music we made: {b} (real music from the bank first, M58)")
        elif why: F.append(f"{b}: {why}")
        elif long and any(k in t for k in MUSIC_NOT_YT): F.append(f"{b} on YouTube: a commercial or unknown-source song (Content ID; copyright-friendly only, M58)")
        elif not t.startswith(MUSIC_BANKS): W.append(f"music outside the bank: {b} (check its page, then add it to MUSIC-LIBRARY.md)")
    if not ns and not nm: return "SKIP", "no sound-effects plan and no music listed (--music, OB_MUSIC or --work's story/score*.json)"
    head = f"{ns} sounds, {nm} music tracks"
    if F: return "FAIL", head + "; " + " | ".join(F[:4]) + (f" (+{len(F) - 4} more)" if len(F) > 4 else "")
    if W: return "WARN", head + "; " + " | ".join(W[:4]) + (f" (+{len(W) - 4} more)" if len(W) > 4 else "")
    return "PASS", head + ", all from the bank" + ("; the music is copyright-friendly for YouTube" if long and nm else "")


def music_tracks(music, work):
    """The edit's music: --music / OB_MUSIC (paths joined with ':'), else the newest story/score*.json in --work."""
    if music: return [m for m in (list(music) if isinstance(music, (list, tuple)) else str(music).split(os.pathsep)) if m]
    if work:
        import glob
        sheets = sorted(glob.glob(os.path.join(work, "story", "score*.json")), key=os.path.getmtime)
        if sheets:
            d = json.load(open(sheets[-1])); cues = d.get("cues", []) if isinstance(d, dict) else d
            return [c["track"] for c in cues if isinstance(c, dict) and c.get("track")]
    return []


def c_bank(plan, work, long, music=None):
    """Ledger M58 + M59 (OB 11-07): music and sound effects from the bank first, never made by us; YouTube music copyright-friendly."""
    hits = json.load(open(plan)).get("hits", []) if plan and os.path.exists(plan) else []
    return bank_verdict(hits, music_tracks(music, work), bool(long))


def gate(path, script=None, long=None, pieces=None, src=None, vmaf=None, skip=(), segs=None, cards=None, every=None, theirs=None, ours=None,
         sfx_plan=None, work=None, music=None, route=None, job=None):
    """long=None: landscape files get the long-form rules. Files over 5 minutes skip the caption check and read text every 2 s
    instead of every 0.5 s. On a Mac under 32 GB they also skip whisper (Apple's transcript reads the cues; pass --script to
    diff the words anyway) and the motion scan. On the Mac mini (32 GB or more, 11-03) whisper reads the cues on long files too
    (25 minutes in 67 s), so a busy Neural Engine refusing Apple's speech model can't leave the scan empty, and the motion scan
    (flash frames; it holds every frame at 256x144, ~10 GB for 25 minutes) runs on files up to 45 minutes. final_deliver.py
    checks black and frozen frames."""
    info = probe(path); R = {}
    v = next((x for x in info.get("streams", []) if x["codec_type"] == "video"), {})
    if long is None: long = int(v.get("width", 0)) > int(v.get("height", 1))
    dur = float(info.get("format", {}).get("duration", 0) or 0); big = dur > 300
    if big: skip = tuple(skip) + (("motion",) if dur > MOTION_MAX_S else ()) + ("captions", "hook") + (() if script else ("words",))
    run = lambda k, f: R.__setitem__(k, ("SKIP", "skipped") if k in skip else f())
    run("format", lambda: c_format(path, info, long)); run("size", lambda: c_size(path, info))
    heard = transcript(path) if (not {"words", "captions"} <= set(skip) and not (big and not script)) or (big and WHISPER_LONG and "cues" not in skip) else []
    apple = _cache("apple", path, lambda: apple_words(path)) if not {"cues", "captions"} <= set(skip) else []
    run("cues", lambda: c_cues(heard, apple, dur))
    R["words"] = c_words(heard, script, path, segs) if script and "words" not in skip else ("SKIP", "no --script")
    R["silence"] = ("SKIP", "long-form keeps its own join rule") if long else (("SKIP", "skipped") if "silence" in skip else c_silence(path))
    R["edges"] = ("SKIP", "skipped") if ("edges" in skip or (big and not segs)) else c_edges(path, segs)   # 11-10 T1: long files with pieces get it
    run("audio", lambda: c_audio(path)); run("motion", lambda: c_motion(path))
    if not {"text_face", "text_lint", "text_safe", "hook", "captions"} <= set(skip):
        ev = every or (2.0 if big else 0.5); fr = _cache("frames", path, lambda: frames_text(path, ev), ev)
        import takes as K
        said = [(t, x) for t, w in list(apple or []) + list(heard) for x in K.toks(w)]
        if theirs is None:   # recorded with the render's pieces (record_pieces), so a later re-gate (deliver.py --script) still has them
            pp = pieces_path(path); dd = json.load(open(pp)) if os.path.exists(pp) else {}
            theirs = dd.get("theirs") if abs(dd.get("mtime", 0) - os.path.getmtime(path)) < 1e-3 else None
        if ours is None and os.path.exists(ours_path(path)):
            od = json.load(open(ours_path(path))); ours = od.get("ours") if abs(od.get("mtime", 0) - os.path.getmtime(path)) < 1e-3 else None
        for k, v in c_text(fr, long, cards, said, theirs, ours).items(): R[k] = ("SKIP", "skipped") if k in skip else v
        run("captions", lambda: c_captions(fr, apple or [], heard))
    run("opener", lambda: c_opener(cards, long))
    R["lookoff"] = c_lookoff(src, pieces) if pieces and src else ("SKIP", "needs --pieces and --src")
    run("sfx", lambda: c_sfx(path, sfx_plan, long, dur))
    run("bank", lambda: c_bank(sfx_plan, work, long, music))
    run("clients", lambda: c_clients(heard, apple, work))
    R["lipsync"] = ("SKIP", "skipped") if "lipsync" in skip else c_lipsync(path)
    R["vmaf"] = c_vmaf(path, vmaf) if vmaf else ("SKIP", "needs --vmaf REF:REF_START:DIST_START:DUR")
    try:   # 11-10 rebuild: route layer (strict mode + plug-in checks); no route = unchanged but one row `route SKIP`
        import qc_route
        R = qc_route.apply_all(R, dict(path=path, work=work, route=route, job=job, long=long, dur=dur, segs=segs, sfx_plan=sfx_plan, music=music, report=report_path(path)))
    except Exception as e: R["route"] = ("FAIL", f"route layer crashed: {e!r}")
    return R


def _route_job(work):
    """WORK/job.json (written by ob_job.py start) -> (route, job); (None, None) for a render with no job."""
    try:
        import qc_route; j = qc_route.load_job(work) if work else None; return (j or {}).get("route"), j
    except Exception: return None, None


def _log_run(path, R, inputs, job):
    """Every gate run appended to qc/runs/<sha256>/ with its inputs (qc_route.log_run), so a weaker re-run cannot launder a FAIL."""
    try:
        import qc_route; qc_route.log_run(path, R, {k: v for k, v in inputs.items() if v not in (None, (), [], "", False)}, job)
    except Exception as e: print(f"qc_gate: run log not written ({e!r})")


def after_render(out, **kw):
    """The end of every video engine calls this (2026-10-28, OB: "wire it in"): the gate on the new render, its table
    printed, its report saved. It never raises, so a gate problem can't lose a render; deliver.py is what blocks a FAIL
    from reaching an AirDrop folder. OB_QC=0 skips it (test renders only)."""
    if os.environ.get("OB_QC", "1") == "0": print(f"qc_gate: skipped for {out} (OB_QC=0)"); return None
    try:
        if kw.get("segs"): record_pieces(out, kw["segs"], kw.get("cam"), kw.get("theirs"))
        if kw.get("ours") is not None:
            os.makedirs(os.path.dirname(ours_path(out)), exist_ok=True)
            json.dump({"file": os.path.abspath(out), "mtime": os.path.getmtime(out), "ours": [list(x) for x in kw["ours"]]}, open(ours_path(out), "w"))
        R = gate(out, kw.get("script"), kw.get("long"), kw.get("pieces"), kw.get("src"), kw.get("vmaf"), tuple(kw.get("skip", ())), kw.get("segs"),
                 kw.get("cards"), kw.get("every"), kw.get("theirs"), kw.get("ours"), kw.get("sfx_plan") or os.environ.get("OB_SFX_PLAN"), kw.get("work"),
                 music=kw.get("music") or os.environ.get("OB_MUSIC"), route=_route_job(kw.get("work"))[0], job=_route_job(kw.get("work"))[1])
        ok = show(out, R); save(out, R, ok)
        _log_run(out, R, dict(script=kw.get("script"), work=kw.get("work"), segs=len(kw.get("segs") or []), cam=bool(kw.get("cam")), pieces=kw.get("pieces"), src=kw.get("src"),
                              sfx_plan=kw.get("sfx_plan") or os.environ.get("OB_SFX_PLAN"), music=kw.get("music") or os.environ.get("OB_MUSIC"), skip=list(kw.get("skip", ())), via="after_render"), _route_job(kw.get("work"))[1])
        return ok
    except Exception as e:
        print(f"qc_gate: could not run on {out}: {e!r} (the render is fine; run qc_gate.py on it by hand)"); return None


def c_lipsync(path):
    """Ledger M36 (OB 11-03: "the lean guy also the lips dont sync, you have been doing that"): every piece of his voice found in
    the camera's own sound at its picture's place (lipsync_check.py). Needs the camera map the render recorded (after_render cam=);
    a render that cut his voice from a separate mic and recorded no map gets a WARN, never a silent pass."""
    p = pieces_path(path); d = json.load(open(p)) if os.path.exists(p) else {}
    if d and abs(d.get("mtime", 0) - os.path.getmtime(path)) > 1e-3: d = {}
    if d.get("cam"):
        import lipsync_check as LS
        return LS.check(path, d["cam"])
    if any(str(x[0]).lower().endswith((".wav", ".aif", ".aiff", ".flac")) for x in d.get("pieces", [])):
        return "WARN", "not measured: his voice comes from a separate mic and the render recorded no camera map (after_render cam=)"
    return "SKIP", "no separate mic"


def save(path, R, ok, extra=None):
    os.makedirs(os.path.join(QC, "reports"), exist_ok=True)
    d = {"file": os.path.abspath(path), "mtime": os.path.getmtime(path), "result": "PASS" if ok else "FAIL",
         "checks": {k: {"status": s, "detail": dd} for k, (s, dd) in R.items()}}
    if extra: d.update(extra)
    json.dump(d, open(report_path(path), "w"), indent=1); return report_path(path)


def show(path, R):
    led = json.load(open(LEDGER))["mistakes"]; guards = {}
    for m in led: guards.setdefault(m["check"], []).append(m["id"])
    print(f"QC gate: {os.path.basename(path)}")
    for k, (st, d) in R.items(): print(f"  {st:4s} {k:9s} [{','.join(guards.get(k, ['-']))}] {d}")
    man = [m for m in led if m["check"] == "manual"]
    print(f"  Manual ({len(man)}): " + " | ".join(f"{m['id']} {m['rule']}" for m in man))
    fails = [k for k, (st, d) in R.items() if st == "FAIL"]
    print("  RESULT: " + ("FAIL (" + ", ".join(fails) + ")" if fails else "PASS (answer every WARN in the delivery note)"))
    return not fails


def selftest():
    fx = json.load(open(os.path.join(QC, "regress", "fixtures.json"))); ok = True
    miss = [f["file"] for f in fx if not os.path.exists(os.path.join(QC, "regress", f["file"]))]
    if miss: print(f"  skip {len(miss)} fixture clips not on this Mac (plant your own in {QC}/regress, see fixtures.json)")
    fx = [f for f in fx if f["file"] not in miss]
    import lipsync_check as LS   # M36: a planted 300 ms offset must FAIL, in sync must PASS (11-03)
    good = LS.selftest(); ok &= good; print(f"  {'ok ' if good else 'BAD'} lipsync planted offsets")
    import sfx_check as SC   # M17: planted caps breaks must FAIL, a sound slipped 80 ms must be caught (11-07)
    good = SC.selftest(); ok &= good; print(f"  {'ok ' if good else 'BAD'} sfx planted plans and slips")
    for f in fx:
        R = gate(os.path.join(QC, "regress", f["file"]), long=f.get("long", False), skip=tuple(f.get("skip", [])), segs=f.get("segs"),
                 cards=f.get("cards"), every=f.get("every"),
                 script=os.path.join(QC, "regress", f["script"]) if f.get("script") else None)   # the word check needs one (10-29)
        for k in f.get("must_fail", []):
            good = R[k][0] == "FAIL"; ok &= good; print(f"  {'ok ' if good else 'BAD'} {f['file']:22s} {k:9s} must FAIL: got {R[k][0]} ({R[k][1][:70]})")
        for k in f.get("must_pass", []):
            good = R[k][0] in ("PASS", "WARN"); ok &= good; print(f"  {'ok ' if good else 'BAD'} {f['file']:22s} {k:9s} must not fail: got {R[k][0]} ({R[k][1][:70]})")
        for k in f.get("must_warn", []):
            good = R[k][0] in ("WARN", "FAIL"); ok &= good; print(f"  {'ok ' if good else 'BAD'} {f['file']:22s} {k:9s} must flag: got {R[k][0]} ({R[k][1][:70]})")
        for k, want in f.get("must_status", {}).items():
            good = R[k][0] == want; ok &= good; print(f"  {'ok ' if good else 'BAD'} {f['file']:22s} {k:9s} must be {want}: got {R[k][0]} ({R[k][1][:70]})")
    fr = [(2.0 * k, 1920, 1080, [] if k == 2 else [[860, 300, 200, 240]], [[700, 420, 520, 60, "You won't get bulky by accident"]] if k == 2 else []) for k in range(6)]
    unit = [(stoks("they're gonna cause harm") == stoks("they're going to cause harm"),
             "whisper's 'gonna' is the script's 'going to' (C4418 11-04: three of them failed a clean cut)"),
            (not real_text(".44."), "a logo read as digits in dots isn't text ('.44.', the LA on his cap, C4395 0:50)"),
            (real_text("20%+") and real_text("3,400") and real_text("2 OF 15"), "numbers on cards are still text"),
            (not dashy("Low- vs high-load training to failure"), "a suspended hyphen isn't a dash ('Low- vs high-load', C4395 study card)"),
            (dashy("FAT LOSS- THE TRUTH") and dashy("A decade \u2014 condensed"), "an em dash, or one OCR read as '-', still FAILs"),
            (not dashy("AFTER- Sep 202") and not dashy("BEFORE - Jul 2025") and dashy("AFTER- THE TRUTH"),
             "a client card's 'AFTER · Sep 2025' (middle dot read as '-') isn't a dash; a real dash after AFTER still FAILs (C4424 v2 19.5 s)"),
            (spoken_caption("PROGRESSIVELV- OVERLOAD VOUR", 33.0, [(32.6, "progressively"), (33.1, "overload"), (33.4, "your")]),
             "OCR's '-' between two caption words he said isn't a dash (C4361 10-30)"),
            (spoken_caption("LONGE,ST- HEALTHIES.T_, LIFE", 64.5, [(63.9, "longest"), (64.3, "healthiest"), (64.8, "life")]),
             "the same with OCR's stray dots and commas inside the words (C4361 10-30)"),
            (not spoken_caption("FAT LOSS- THE TRUTH", 3.0, [(2.0, "so"), (3.5, "loss")]) and not spoken_caption("A decade \u2014 condensed", 1.0, [(1.0, "a"), (1.2, "decade"), (1.4, "condensed")]),
             "a dash in a line he didn't say, or an em dash, still FAILs"),
            (c_text(fr, True)["text_face"][0] == "FAIL", "text hiding his face on the A-roll still FAILs"),
            (c_text(fr, True, [[4.5, 6.6]])["text_face"][0] == "PASS", "a full-screen card doesn't borrow his face (C4395 chapter cards)"),
            (c_text([(0.5 * k, 1080, 1920, [[262, 249, 232, 232], [415, 1260, 206, 206]] if k in (2, 3) else [[251, 505, 496, 496]],
                      [[318, 916, 445, 71, "IN ALL FACETS"]] if k in (2, 3) else []) for k in range(6)], False)["text_face"][0] == "PASS",
             "a split frame (her face on top, his below) doesn't borrow his full-frame box (C4397 seam caption, 10-29)"),
            (c_text([(0.5 * k, 1080, 1920, [[100 + 120 * k, 249, 232, 232]] + ([] if k == 2 else [[415, 1260, 206, 206]]),
                      [[380, 1240, 300, 80, "HERE'S THE THING"]] if k == 2 else []) for k in range(6)], False)["text_face"][0] == "FAIL",
             "text hiding his face in a split frame (her face moving on top) still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 600, 260, 110, "r41"]])], True)["text_face"][0] == "PASS",
             "the LA on his cap read as 'r41' isn't text on his face (C4407 test, 11-03)"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "10K"]])], True)["text_face"][0] == "FAIL",
             "a real number over his face ('10K') still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 600, 260, 110, "TT41"]])], True)["text_face"][0] == "PASS",
             "the LA on his cap read as 'TT41' isn't text on his face (C4415 v4 0:04)"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "B12"]])], True)["text_face"][0] == "FAIL",
             "a vitamin name over his face ('B12') still FAILs"),
            (c_text([(0.0, 1080, 1920, [[388, 484, 284, 284]], [[466, 660, 46, 15, '":of44']])], True)["text_face"][0] == "PASS",
             "his stubble read as a tiny '\":of44' isn't text on his face (workshop ad 4 talking, 11-10)"),
            (c_text([(0.0, 1080, 1920, [[388, 484, 284, 284]], [[440, 640, 140, 45, "25%"]])], True)["text_face"][0] == "FAIL",
             "a caption-size number over his face ('25%') still FAILs"),
            (c_text([(0.0, 1080, 1920, [[397, 458, 282, 282]], [[533, 658, 42, 13, '.ILA']])], True)["text_face"][0] == "PASS",
             "his stubble read as a tiny '.ILA' (a dictionary word) isn't text on his face (workshop ad 4 talking V08, 11-11)"),
            (c_text([(0.0, 1080, 1920, [[397, 458, 282, 282]], [[480, 640, 120, 45, "ILA"]])], True)["text_face"][0] == "FAIL",
             "the same letters at caption size over his face still FAIL"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "PRO 74"]])], True, ours=[[5.0, 9.0]])["text_face"][0] == "PASS",
             "a reading of the set (cap, mic print) outside every one of our graphics is the camera's picture, not our copy (C4415 v3 8:06)"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "PRO 74"]])], True, ours=[[0.0, 2.0]])["text_face"][0] == "FAIL",
             "the same reading while one of our graphics is up still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[2208, 555, 1482, 398, "') 2+ years in my"]])], True)["text_face"][0] == "PASS",
             "his ear read as \"') \" before a line beside him isn't text on his face (C4395 2:59)"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[2208, 555, 1482, 398, "2+ years in my apartment"]])], True)["text_face"][0] == "FAIL",
             "the same line really over his face still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1397, 682, 270, 270]], [[1392, 644, 1864, 375, "'\u2022& i DON'T SELL"]])], True)["text_face"][0] == "PASS",
             "his hair read as \"'\u2022& \" before a line beside him isn't text on his face (C4398 v2 0:52)"),
            (c_text([(0.0, 3840, 2160, [[1397, 682, 270, 270]], [[1392, 644, 1864, 375, "_.JA '& FOR BERR"]])], True)["text_face"][0] == "PASS",
             "his ear and cap edge glued to a tag beside him ('_.JA '& FOR BERR') isn't text on his face (C4415 rev 2, 1:50)"),
            (c_text([(0.0, 3840, 2160, [[1397, 682, 270, 270]], [[1400, 690, 260, 120, "_.JA '& FOR BERR"]])], True)["text_face"][0] == "FAIL",
             "the same reading with the words really on his face still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1397, 682, 270, 270]], [[1392, 644, 1864, 375, "I DON'T SELL PEPTIDES"]])], True)["text_face"][0] == "FAIL",
             "the same line really starting on his face still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1406, 598, 578, 578]], [[1344, 766, 104, 58, "rie"]])], True)["text_face"][0] == "WARN",
             "a short lower-case reading across the side of his face box is his ear: WARN, not FAIL (C4407 2:57 'rie', 11-03)"),
            (c_text([(0.0, 3840, 2160, [[1406, 598, 578, 578]], [[1344, 766, 104, 58, "YES"]])], True)["text_face"][0] == "FAIL",
             "an upper-case word at the side of his face still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1406, 598, 578, 578]], [[1600, 900, 104, 58, "you"]])], True)["text_face"][0] == "FAIL",
             "a short lower-case word inside his face box still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "14bl"]])], True, said=[(0.0, "off"), (0.3, "kit")])["text_face"][0] == "PASS",
             "junk with no 3-letter word and nothing said near it is the camera's picture (Rythm 13: '14bl', her mic transmitter, 11-06)"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "25%"]])], True, said=[(0.2, "25"), (0.5, "off")])["text_face"][0] == "FAIL",
             "a caption number she said ('25%') over her face still FAILs"),
            (c_text([(0.0, 3840, 2160, [[1723, 660, 608, 608]], [[1880, 700, 300, 140, "B12"]])], True, said=[(0.2, "b12"), (0.5, "levels")])["text_face"][0] == "FAIL",
             "'B12' over his face while he says it still FAILs"),
            (c_text([(0.0, 1080, 1920, [], [[60, 220, 600, 40, ".ww,likoolq- 12"]])], False, theirs=[[0.0, 1.0, 40, 196, 1040, 896]])["text_lint"][0] == "PASS",
             "a creator's own caption inside her footage isn't our dash (C4413 47 s)"),
            (c_text([(0.0, 1080, 1920, [], [[60, 1300, 600, 40, ".ww,likoolq- 12"]])], False, theirs=[[0.0, 1.0, 40, 196, 1040, 896]])["text_lint"][0] == "FAIL",
             "the same dash in our own text below her footage still FAILs")]
    W = lambda s, t0=0.0: [(t0 + 0.3 * i, w) for i, w in enumerate(s.split())]   # M56 (11-07): clients on screen when he mentions them
    unit += [(len(client_triggers(W("With a piggy bank. I've coached people through fat loss for over a decade. And this works"))) == 1,
              "'I've coached people through fat loss for over a decade' is a client line (C4424 0:17)"),
             (not client_triggers(W("a lot of coaches are scared they're not going to get clients because it's so simple")),
              "other coaches' clients aren't his (C4424 3:47)"),
             (len(client_triggers(W("I mean, I have a client right now. Her name is Sarah. She's down five pounds"))) == 1,
              "'I have a client right now. Her name is Sarah' is one client line (C4424 4:45)"),
             (clients_verdict(client_triggers(W("I give it to my clients and myself", 376.0)), [])[0] == "FAIL",
              "a client line with no client on screen FAILs (C4424 v1 shipped like that)"),
             (clients_verdict(client_triggers(W("I give it to my clients and myself", 376.0)), [(376.5, 379.0)])[0] == "PASS",
              "the same line with a client before/after up within 1 s passes")]
    A, MU = os.path.expanduser("~/ob-editor/assets"), "/Volumes/T7/MUSIC/Jalen Ngonda - If You Don't Want My Love (Official Audio).mp3"   # M58 + M59 (11-07)
    unit += [(bank_verdict([{"t": 6.3, "file": f"{A}/sfx/pop_1.wav"}], [], True)[0] == "FAIL",
              "a pop from our code-made kit with no bank_miss FAILs (C4424's pops and whooshes)"),
             (bank_verdict([{"t": 6.3, "file": f"{A}/sfx/pop_1.wav", "bank_miss": "no pop in the 4 banks or Openverse"}], [], True)[0] == "WARN",
              "the same pop with bank_miss is a WARN"),
             (bank_verdict([{"t": 6.3, "file": f"{A}/sfx_ob_drive/camera-click.mp3"}], ["/Volumes/T7/OB-EDITS/music/mixkit-2026-11-07/mixkit_729.mp3"], True)[0] == "PASS",
              "a bank sound plus Pop Track 03 on YouTube passes (C4424 v3's music)"),
             (bank_verdict([{"t": 3.0, "file": "/tmp/new/whoosh.wav"}], [], False)[0] == "WARN",
              "a sound from outside the known banks WARNs"),
             (bank_verdict([], [MU], True)[0] == "FAIL", "a commercial song he saved FAILs on YouTube (Content ID)"),
             (bank_verdict([], [MU], False)[0] == "PASS", "the same viral song passes on a reel (the bank's viral songs come first)"),
             (bank_verdict([{"t": 4.0, "file": "/Volumes/T7/OB-EDITS/sfx-library/openverse/anvil/anvil_01_Blacksmith-forge-hit.mp3"}], [], False)[0] == "PASS",
              "a real bank sound with 'forge' in its name is not a forged one"),
             (bank_verdict([], ["/Volumes/T7/OB-EDITS/music/pixabay/aurec-sugar-maple-groove-588230.mp3"], False)[0] == "FAIL",
              "an AI-labelled track FAILs anywhere (Sugar Maple Groove)"),
             (bank_verdict([], ["/Volumes/T7/OB-EDITS/C4367-edit/music_dl/mixkit_615.mp3"], True)[0] == "FAIL", "Tapis FAILs (M57, C4424 v1)"),
             (bank_verdict([], [os.path.expanduser("~/.techguyver-tools/soundtrack/out/bed.wav")], False)[0] == "FAIL",
              "a code-written music bed FAILs (never make music while the bank has one)")]
    for good, what in unit: ok &= bool(good); print(f"  {'ok ' if good else 'BAD'} logic: {what}")
    print("SELFTEST " + ("PASSED: every check still catches its mistake" if ok else "FAILED: a check no longer catches its mistake"))
    return ok


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    if a[0] in ("--help", "-h"): print(__doc__); return
    if a[0] == "--rules":   # 11-10: only active ledger rules, for one route when given (ledger.py)
        try:
            import ledger
            for m in ledger.active(a[1] if len(a) > 1 else None): print(ledger.rule_line(m, 400) + f"  (OB {m['date']}: \"{m['said'][:90]}\")")
            return
        except Exception as e: print(f"(ledger.py unavailable: {e!r}; full ledger below)")
        for m in json.load(open(LEDGER))["mistakes"]: print(f"{m['id']} [{m['check']}] {m['rule']}  (OB {m['date']}: \"{m['said'][:90]}\")")
        return
    if a[0] == "--selftest": sys.exit(0 if selftest() else 1)
    if a[0] == "--ok":   # before any video goes to OB by chat or AirDrop (M27): a fresh PASS report, or it doesn't go
        bad = 0
        for f in a[1:]:
            rp = report_path(f); d = json.load(open(rp)) if os.path.exists(rp) else None
            fresh = d is not None and abs(d.get("mtime", 0) - os.path.getmtime(f)) < 1e-3
            fails = [k for k, v in (d or {}).get("checks", {}).items() if v["status"] == "FAIL"] if fresh else []
            ok = fresh and not fails; bad += not ok
            print(f"{'OK  ' if ok else 'STOP'} {os.path.basename(f)}: " + ("PASS" if ok else ("no fresh gate report: run the gate" if not fresh else "FAIL " + ", ".join(fails))))
        sys.exit(1 if bad else 0)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    sfx = opt("--sfx-plan") or (os.path.join(opt("--work"), "story", "sfx_plan.json") if opt("--work") else None)
    R = gate(a[0], opt("--script"), True if "--long" in a else None, opt("--pieces"), opt("--src"), opt("--vmaf"), tuple((opt("--skip") or "").split(",")),
             cards=cover_spans(opt("--work")) if opt("--work") else None, sfx_plan=sfx if sfx and os.path.exists(sfx) else None, work=opt("--work"),
             music=opt("--music"), route=_route_job(opt("--work"))[0], job=_route_job(opt("--work"))[1])
    ok = show(a[0], R); rp = save(a[0], R, ok)
    _log_run(a[0], R, dict(script=opt("--script"), work=opt("--work"), pieces=opt("--pieces"), src=opt("--src"), sfx_plan=sfx if sfx and os.path.exists(sfx) else None,
                           music=opt("--music"), skip=[x for x in (opt("--skip") or "").split(",") if x], via="qc_gate.py cli"), _route_job(opt("--work"))[1])
    if opt("--json"): json.dump(json.load(open(rp)), open(opt("--json"), "w"), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
