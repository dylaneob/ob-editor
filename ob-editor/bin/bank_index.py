#!/usr/bin/env python3
"""bank_index: tag every music track and sound effect once, by content hash, so picks are scored choices and not defaults.

Why (OB 2026-11-07): "You always go so depressing", "You have a bank of so many choices", "use the sound effects from the bank
first before making your own always, we have so many to pick from". Before this file no track or sound had a BPM, key, mood,
loudness, licence or usage history, and the gate trusted path prefixes (a bank file copied anywhere WARNed, a renamed blocked
track passed). Identity here is the sha256 of the bytes: the T7 original and the internal-disk copy are ONE entry (`paths`).

  python3 -I bank_index.py build [--no-copy] [--no-audio] [--limit N]   copy the banks off the T7 (read-only there), hash,
                                                                         analyse new files only, write bank_index.json + BANK.md
                                                                         (re-execs under the earshot venv: librosa, earshot)
  python3 -I bank_index.py lookup FILE                                  the entry for any path, by hash (a copy anywhere resolves)
  python3 -I bank_index.py eligible [--route ROUTE] [--kind educational|reaction|fdoe|story]   the music a route may use today
  python3 -I bank_index.py report                                       rewrite BANK.md from the existing index
  python3 -I bank_index.py --selftest

Locations come from ~/ob-editor/qc/formats.json `paths` (bank_index, music_bank, sfx_banks). NEVER writes to /Volumes/T7.
Importable helpers used by music_pick.py, sfx_pick.py, qc_audio.py: load_cfg, load_index, lookup_path, sha256_file, music_ineligible,
tone_score, decode, lufs, env_db.
"""
import ast, csv, datetime, glob, hashlib, json, os, re, shutil, subprocess, sys
import numpy as np

ED = os.path.expanduser("~/ob-editor")
FORMATS = f"{ED}/qc/formats.json"
T7 = "/Volumes/T7"
KINDS = ("educational", "reaction", "fdoe", "story")
TONE_KINDS = ("educational", "reaction", "fdoe")          # M57: upbeat, bright, major
UP = ["uplifting and hopeful music", "playful and quirky music", "energetic and driving music", "triumphant and heroic music",
      "confident and cool music", "celebratory and joyful music"]
DOWN = ["dark and tense music", "sad and melancholic music", "calm and relaxing music", "dreamy and ethereal music",
        "mysterious music", "suspenseful build-up music", "aggressive music"]
# route_lanes: a track in lane X is accepted where the route accepts one of LANE_ACCEPT[X]'s partners (youtube-safe is also royalty-free)
LANE_ACCEPT = {"viral": {"viral"}, "royalty-free": {"royalty-free", "youtube-safe"}, "youtube-safe": {"youtube-safe"}}   # route lane -> track lanes it accepts
ALL_LANES = ["viral", "royalty-free", "youtube-safe"]
SFX_CLASSES = {  # class -> earshot phrase (fallback when the name says nothing)
    "swish": "a fast whoosh", "impact": "a punchy impact hit", "ui": "a soft UI button tap", "paper": "paper rustling",
    "glass": "a glass ting", "camera": "a camera shutter click", "riser": "a rising riser building tension",
    "tap": "a finger tapping on wood", "ding": "a notification ding", "thud": "a heavy thud", "click": "a mouse click",
    "pop": "a bubble pop", "boom": "a deep cinematic boom", "glitch": "a digital glitch"}
CLASS_KW = [("riser", r"riser|rise|charge|build"), ("boom", r"boom|sub[_ -]?drop"), ("glitch", r"glitch|flicker|maximize|minimize"),
            ("swish", r"whoosh|swish|swipe|swoosh|swing|flick|woosh"), ("thud", r"thud|thump|punch|knock"),
            ("impact", r"impact|slam|stamp|hit"), ("camera", r"camera|shutter|flash"), ("paper", r"paper|pencil|page|draw|paint"),
            ("glass", r"glass|bottle|clink"), ("ding", r"ding|chime|bell|bing|notif|pling|ting"), ("pop", r"pop|bubble"),
            ("click", r"click|snap|button|knob|switch|tick"), ("tap", r"\btap|pen\b"),
            ("ui", r"beep|bleep|blip|hi[_-]?tech|arcade|data|interface|ui")]
# OB's verdicts on tracks (AUDIT-AUDIO 5B step 3; picked / rejected). key = substring of the file name or title, lowercase.
OB_VERDICTS = [
    ("funkavenue-feel-good-funk-anthem", "2026-10-17", "picked", "Feel Good Funk Anthem (his pick)", "AUDIT-AUDIO 5B step 3"),
    ("mixkit_609", "2026-11-04", "picked", "\"moon walk as music\"", "AUDIT-AUDIO 5B step 3"),
    ("mixkit_729", "2026-11-07", "picked", "Pop Track 03 (re-render with better music)", "C4424 v3"),
    ("mixkit_644", "2026-11-08", "picked", "picked B (Upbeat Jazz) from 4 previews", "C4441 PICKS.md"),
    ("588903", "2026-10-28", "rejected", "\"bad background music choice\" (Lofi Soul)", "AUDIT-AUDIO 5B step 3"),
    ("mixkit_615", "2026-11-07", "rejected", "\"Oddly depressing\" (Tapis)", "AUDIT-AUDIO 5B step 3"),
    ("mixkit_184", "2026-11-07", "rejected", "\"Oddly depressing\" (Vastness)", "AUDIT-AUDIO 5B step 3"),
    ("spice-intrigue", "2026-11-07", "rejected", "\"You use the worse music I swear\" (Spice Intrigue)", "AUDIT-AUDIO 5B step 3")]
# earshot's AudioSet/CLAP singing signal does not separate these (checked 11-10: Jalen reads 0.0, an instrumental reads 0.37), so the title decides
VOCALS_KNOWN = [("jalen ngonda", True), ("lord huron", False), ("(instrumental)", False)]
# uses the state logs record (AUDIT-AUDIO 2): (key, edit, date, format)
KNOWN_USES = [("mixkit_729", "C4424", "2026-11-07", "long-form"), ("mixkit_615", "C4424", "2026-11-06", "long-form"),
              ("mixkit_644", "C4441", "2026-11-08", "long-form"), ("mixkit_33", "C4465", "2026-11-10", "long-form"),
              ("funkavenue-feel-good-funk-anthem", "D-fruit-sugar", "2026-11-07", "reel")]


# ---------------------------------------------------------------- config and paths
def xp(p):
    return os.path.abspath(os.path.expanduser(str(p)))


def load_cfg(route=None):
    """formats.json, one place. Returns dict(paths, music (defaults), sfx (defaults), route, music_need, sfx_need, sfx_per_min,
    music_lanes, long, raw). qc_route.cfg is not used on purpose: its shape is not fixed yet; this is the only reader here."""
    fpath = os.environ.get("OB_FORMATS") or FORMATS   # tests point this at a temp copy, as qc_route does
    d = json.load(open(fpath))
    r = d.get("routes", {}).get(route, {}) if route else {}
    if route and route not in d.get("routes", {}):
        raise SystemExit(f"unknown route '{route}'; routes in {fpath}: {', '.join(sorted(d.get('routes', {})))}")
    return {"paths": d["paths"], "music": d["defaults"]["music"], "sfx": d["defaults"]["sfx"], "route": route, "raw": r,
            "music_need": r.get("music"), "sfx_need": r.get("sfx"), "sfx_per_min": r.get("sfx_per_min") or {},
            "music_lanes": r.get("music_lanes"), "long": bool(r.get("long")), "enforce": d.get("enforce")}


def index_path(cfg=None):
    return xp((cfg or load_cfg())["paths"]["bank_index"])


def load_index(cfg=None):
    p = index_path(cfg)
    if not os.path.exists(p):
        raise SystemExit(f"no bank index at {p}: run `python3 -I {ED}/bin/bank_index.py build`")
    return json.load(open(p))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lookup_path(path, idx=None):
    """(kind, sha, entry) for any file by content hash, or (None, sha, None) when it is not in the bank."""
    idx = idx or load_index()
    sha = sha256_file(path)
    for kind in ("music", "sfx"):
        if sha in idx[kind]:
            return kind, sha, idx[kind][sha]
    return None, sha, None


# ---------------------------------------------------------------- audio helpers (numpy + scipy; ffmpeg decodes)
def decode(path, sr=48000, ch=1, start=None, dur=None):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error"] + (["-ss", str(start)] if start else []) + (["-t", str(dur)] if dur else []) + \
          ["-i", path, "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    return a.reshape(-1, ch) if ch > 1 else a


def env_db(x, sr, win=0.01):
    fr = max(1, int(win * sr)); n = len(x) // fr
    if n < 1:
        return np.array([-120.0])
    return 10 * np.log10((x[: n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12)


def lufs(x, gate=True):
    """BS.1770-4 integrated loudness of a 48 kHz signal (n,) = dual mono (a stereo copy of the voice, as the long-form preset
    measures) or (n, 2). Returns LUFS, -120 for silence."""
    from scipy.signal import lfilter
    x = np.asarray(x, np.float64)
    ch = [x, x] if x.ndim == 1 else [x[:, i] for i in range(x.shape[1])]
    zs = []
    for c in ch:
        y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], c)
        y = lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y)
        cs = np.concatenate([[0.0], np.cumsum(y ** 2)])
        L, H = 19200, 4800
        if len(y) < L:
            return -120.0
        s = np.arange(0, len(y) - L + 1, H)
        zs.append((cs[s + L] - cs[s]) / L)
    z = np.sum(zs, axis=0)
    l = -0.691 + 10 * np.log10(z + 1e-12)
    keep = l > -70.0
    if not keep.any():
        return -120.0
    if gate:
        rel = -0.691 + 10 * np.log10(z[keep].mean() + 1e-12) - 10.0
        keep = keep & (l > rel)
        if not keep.any():
            return -120.0
    return float(-0.691 + 10 * np.log10(z[keep].mean() + 1e-12))


# ---------------------------------------------------------------- eligibility (shared with music_pick and qc_audio)
def route_accepts(lane, route_lanes):
    """Does a route whose music_lanes is `route_lanes` (None = reels: every lane) accept a track of this lane?"""
    allowed = route_lanes or ALL_LANES
    return any(lane in LANE_ACCEPT.get(l, set()) for l in allowed)


def tone_score(entry):
    """Upbeat minus gloomy, from the cached earshot mood tags: mean z of the 2 best UP terms minus the 2 best DOWN terms."""
    z = entry.get("mood_all") or {m["term"]: m["z"] for m in entry.get("mood", [])}
    if not z:
        return None
    up = sorted((z[t] for t in UP if t in z), reverse=True)[:2]
    dn = sorted((z[t] for t in DOWN if t in z), reverse=True)[:2]
    if not up or not dn:
        return None
    return round(float(np.mean(up) - np.mean(dn)), 2)


def music_ineligible(e, cfg, kind="educational"):
    """None when the track may be used for this route and kind of job, else the one-line reason."""
    lane = e.get("lane")
    if not route_accepts(lane, cfg.get("music_lanes")):
        return f"lane '{lane}' not allowed on {cfg.get('route') or 'this route'} ({'/'.join(cfg.get('music_lanes') or ALL_LANES)} only)"
    if not e.get("licence"):
        return "no licence record in the index"
    if lane == "youtube-safe" and not (e.get("ai_label_checked") and e.get("content_id_checked")):
        return "lane youtube-safe needs ai_label_checked and content_id_checked dates (page check)"
    bf = e.get("banned_for") or {}
    for k in ("all", kind):
        if k in bf:
            return f"banned for {k}: {bf[k]}"
    return None


# ---------------------------------------------------------------- analysis (runs under the earshot venv)
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def analyse_music(path, api):
    import librosa
    sr, hop = 22050, 512
    y = decode(path, sr, 1).astype(np.float32)
    dur = len(y) / sr
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop)
    bt = librosa.frames_to_time(beats, sr=sr, hop_length=hop)
    tempo = float(np.atleast_1d(tempo)[0])
    if len(bt) > 4:
        d = np.diff(bt); reg = float(np.clip(1 - d.std() / (d.mean() + 1e-9), 0, 1))
        stren = float(np.clip((oenv[beats[beats < len(oenv)]].mean() / (oenv.mean() + 1e-9) - 1) / 1.5, 0, 1))
        conf = round(0.5 * reg + 0.5 * stren, 2)
    else:
        conf = 0.0
    ch = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=4096, hop_length=2048).mean(1)
    cm = [(float(np.corrcoef(np.roll(KS_MAJ, k), ch)[0, 1]), k, "major") for k in range(12)]
    cn = [(float(np.corrcoef(np.roll(KS_MIN, k), ch)[0, 1]), k, "minor") for k in range(12)]
    best = max(cm + cn); other = max(cn if best[2] == "major" else cm)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=1024)) ** 2
    fq = librosa.fft_frequencies(sr=sr, n_fft=2048)
    share = float(S[(fq >= 1000) & (fq <= 4000)].sum() / (S.sum() + 1e-12))
    cent = float(librosa.feature.spectral_centroid(S=np.sqrt(S), sr=sr).mean())
    n2 = int(dur // 2)
    energy = [round(float(10 * np.log10((y[i * 2 * sr:(i + 1) * 2 * sr] ** 2).mean() + 1e-12)), 1) for i in range(n2)]
    mf = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=2048)
    k = int(np.clip(dur / 20, 3, 10))
    bounds = librosa.segment.agglomerative(mf, k)
    sections = [round(float(t), 1) for t in librosa.frames_to_time(bounds, sr=sr, hop_length=2048)[1:]]
    de = api.describe(path, top=16)
    m = de["measurements"]
    tags = de.get("tags", {})
    vp = max([a["p"] for a in de.get("audioset", []) if re.search(r"sing|vocal|choir|speech|rap|voice|chant|a cappella", a["label"], re.I)] or [0.0])
    return {"duration_s": round(dur, 2), "lufs": m["lufs"], "lra_lu": m["lra_lu"], "true_peak_dbtp": m["true_peak_dbtp"],
            "bpm_1x": round(tempo, 1), "bpm_2x": round(tempo * 2, 1), "bpm_conf": conf, "beats": [round(float(b), 3) for b in bt],
            "key": NOTES[best[1]], "mode": best[2], "key_conf": round(best[0], 2), "mode_margin": round(best[0] - other[0], 3),
            "energy_2s_db": energy, "sections_s": sections, "centroid_hz": round(cent), "share_1_4k": round(share, 3),
            "vocals": bool(vp >= 0.2), "vocal_p": round(float(vp), 2),
            "mood": [{"term": t["term"], "z": t["z"]} for t in tags.get("music_mood", [])],
            "genre": [{"term": t["term"], "z": t["z"]} for t in tags.get("music_genre", [])[:4]],
            "instruments": [t["term"] for t in tags.get("instruments", [])[:4]], "summary": de.get("summary", "")[:240]}


def analyse_sfx(path, api):
    sr = 32000
    x = decode(path, sr, 1)
    n = len(x); dur = n / sr
    a = np.abs(x); e10 = env_db(x, sr, 0.01)
    on = np.nonzero(a > 10 ** (-40 / 20))[0]
    fr100 = int(0.1 * sr)
    r100 = 10 * np.log10(((x[: max(1, n // fr100) * fr100].reshape(-1, fr100) ** 2).mean(1)).max() + 1e-12) if n >= fr100 else float(10 * np.log10((x ** 2).mean() + 1e-12))
    li = int(np.argmax(e10)); above = np.nonzero(e10 > -50)[0]
    after = np.nonzero(e10[li:] < e10[li] - 30)[0]
    spec = np.abs(np.fft.rfft(x * np.hanning(n))) if n > 8 else np.zeros(2)
    fq = np.fft.rfftfreq(n, 1 / sr) if n > 8 else np.zeros(2)
    out = {"duration_s": round(dur, 3), "onset_s": round(float(on[0] / sr), 4) if len(on) else None,
           "peak_s": round(float(np.argmax(a) / sr), 4), "loud10_s": round((li + 0.5) * 0.01, 3), "rms100_db": round(float(r100), 1),
           "peak_db": round(float(20 * np.log10(a.max() + 1e-12)), 1),
           "tail_s": round(float(dur - (above[-1] + 1) * 0.01), 3) if len(above) else round(dur, 3),
           "decay_s": round(float(after[0] * 0.01), 3) if len(after) else round(float((len(e10) - li) * 0.01), 3),
           "hiss_floor_db": round(float(np.percentile(e10, 10)), 1), "brightness_hz": round(float((spec * fq).sum() / (spec.sum() + 1e-12)))}
    try:
        out["realness"] = round(float(api.realness(path)["p_real"]), 3)
    except Exception as ex:
        out["realness"] = None
    return out


# ---------------------------------------------------------------- sources: where the banks are and what we know about them
def sidecars():
    """licence / source records that already exist, keyed by file basename."""
    rec = {}
    for p in (f"{T7}/OB-EDITS/sfx-library/openverse/SOURCES.csv", f"{ED}/assets/sfx_library/openverse/SOURCES.csv"):
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                rec["ov:" + os.path.basename(r["file"])] = r
    for name in ("sfx_tai", "sfx_real"):
        p = f"{ED}/assets/{name}/LEVELS.json"
        if os.path.exists(p):
            for f, v in json.load(open(p)).items():
                rec[f"{name}:{f}"] = v
    p = f"{ED}/assets/sfx_ob_drive/SOURCES.csv"
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            rec["drive:" + r["file"]] = r
    for p in glob.glob(f"{T7}/OB-EDITS/C43*-edit/music_dl/LICENSE-RECORD.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        rec["mixkit-licence"] = d.get("license", {})
        for m in d.get("music", []):
            rec[f"mk:{m.get('id')}"] = m
        for m in d.get("sfx", d.get("sound_effects", [])):
            rec[f"mksfx:{m.get('id')}"] = m
    return rec


def music_sources():
    """[(path, hints)] for every music file in AUDIT-AUDIO 1b. hints: lane, licence, source, checks, group."""
    out = []
    mixlic = "Mixkit Stock Music Free License (commercial use, YouTube included; mixkit.co/license)"
    pixlic = "Pixabay Content License (free commercial use, no attribution)"
    for f in sorted(glob.glob(f"{T7}/MUSIC/*.mp3")):
        b = os.path.basename(f).lower()
        if "construction" in b:
            continue  # an SFX
        if "jazzyfrenchy" in b:
            out.append((f, dict(lane="unchecked", licence="Bensound (terms never checked: lane A only after checking)", group="T7-MUSIC")))
        else:
            out.append((f, dict(lane="viral", licence="commercial song OB saved (reels only; never ads, never YouTube)", group="T7-MUSIC")))
    for f in sorted(glob.glob(f"{T7}/*.mp3")):
        b = os.path.basename(f).lower()
        if "funk" in b:
            out.append((f, dict(lane="royalty-free", licence=pixlic, source="https://pixabay.com/ (FunkAvenue, Feel Good Funk Anthem 572932)",
                                ai_label_checked="2026-11-07", group="T7-root")))
        else:
            out.append((f, dict(lane="viral", licence="song of unknown source (reels only; never YouTube)", group="T7-root")))
    for f in sorted(glob.glob(f"{T7}/OB-EDITS/music/mixkit-2026-11-07/*.mp3")):
        out.append((f, dict(lane="youtube-safe", licence=mixlic, ai_label_checked="2026-11-07", content_id_checked="2026-11-07",
                            source="https://mixkit.co/free-stock-music/ (page check 11-07: C4441 PICKS.md)", group="mixkit-2026-11-07")))
    for f in sorted(glob.glob(f"{T7}/OB-EDITS/music/mixkit-2026-11-11/*.mp3")):   # workshop ad 4: bank short for ad/educational (11-11)
        out.append((f, dict(lane="royalty-free", licence=mixlic, ai_label_checked="2026-11-11",
                            source="https://mixkit.co/free-stock-music/ (pages' JSON-LD: human artist, published 2020-01-28; SOURCES.txt 2026-11-11)", group="mixkit-2026-11-11")))
    for f in sorted(glob.glob(f"{T7}/OB-EDITS/music/pixabay/*.mp3")):
        out.append((f, dict(lane="royalty-free", licence=pixlic, source="Pixabay (OB-EDITS/music/pixabay/SOURCES.txt)", group="pixabay")))
    for f in sorted(glob.glob(f"{T7}/OB-EDITS/music/pixabay-2026-11-07/*/*.mp3")):
        out.append((f, dict(lane="royalty-free", licence=pixlic, ai_label_checked="2026-11-07", source="Pixabay (SOURCES.txt, page checked 11-07)", group="pixabay-2026-11-07")))
    for d in ("C4367-edit", "C4372-edit"):
        for f in sorted(glob.glob(f"{T7}/OB-EDITS/{d}/music_dl/*.mp3")):
            out.append((f, dict(lane="royalty-free", licence=mixlic, source="https://mixkit.co/free-stock-music/ (LICENSE-RECORD.json 2026-10-20)", group="mixkit-music_dl")))
    return out


def sfx_sources():
    out = []
    for f in sorted(glob.glob(f"{T7}/OB-EDITS/sfx-library/openverse/*/*.mp3")):
        out.append((f, dict(pack="openverse", dest="openverse")))
    seen = set()
    for d in ("C4367-edit", "C4372-edit"):
        for f in sorted(glob.glob(f"{T7}/OB-EDITS/{d}/sfx_dl/*.wav")):
            if os.path.basename(f) in seen:
                continue
            seen.add(os.path.basename(f)); out.append((f, dict(pack="mixkit", dest="mixkit")))
    for pack, sub in (("ob-drive", "sfx_ob_drive"), ("tai", "sfx_tai"), ("kenney-real", "sfx_real")):
        for f in sorted(glob.glob(f"{ED}/assets/{sub}/*.[mw][pa][3v]")):
            out.append((f, dict(pack=pack)))
    for f in sorted(glob.glob(f"{ED}/vendor/kenney/*/Audio/*.ogg")):
        out.append((f, dict(pack="kenney-raw")))
    for f in sorted(glob.glob(f"{ED}/assets/sfx/*.wav")):
        out.append((f, dict(pack="code-kit", code_made=True)))
    return out


def blocked_map():
    """qc_gate.MUSIC_BLOCKED, read from the source text (no import: qc_gate is being edited and is heavy)."""
    try:
        t = ast.parse(open(f"{ED}/bin/qc_gate.py").read())
        for n in t.body:
            if isinstance(n, ast.Assign) and any(getattr(x, "id", "") == "MUSIC_BLOCKED" for x in n.targets):
                return ast.literal_eval(n.value)
    except Exception:
        pass
    return {"568181": "AI generated", "588230": "AI generated + Content ID", "591196": "AI generated + Content ID",
            "spice-intrigue": "Content ID Registered", "618233": "uploader posts AI music", "568174": "uploader posts AI music",
            "588903": "uploader posts AI music", "584902": "uploader posts AI music", "608133": "uploader posts AI music",
            "mixkit_615": "Tapis, banned for educational videos (M57)", "mixkit_184": "Vastness, banned for educational videos (M57)"}


def banned_for(keytext):
    bf = {}
    for k, why in blocked_map().items():
        if k.lower() in keytext:
            if "educational" in why.lower():
                for kd in TONE_KINDS:
                    bf[kd] = why
            else:
                bf["all"] = why
    return bf


def slug_title(path):
    b = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[-_]+", " ", re.sub(r"-?\d{5,7}$", "", b)).strip().title()


def music_entry_base(path, h, rec, mixtitles):
    b = os.path.basename(path); key = (path + " " + b).lower()
    e = {"title": slug_title(path), "artist": None, "source": h.get("source"), "licence": h.get("licence"), "lane": h["lane"],
         "ai_label_checked": h.get("ai_label_checked"), "content_id_checked": h.get("content_id_checked"), "group": h.get("group")}
    m = re.match(r"mixkit_(\d+)", b)
    if m:
        i = m.group(1)
        if i in mixtitles:
            e["title"], e["artist"] = mixtitles[i]
        r = rec.get("mk:" + i) or rec.get("mk:" + str(int(i)))
        if r:
            e["title"] = r.get("title") or e["title"]; e["artist"] = r.get("artist") or e["artist"]
            e["source"] = r.get("page") or r.get("url") or r.get("category_page") or e["source"]
    e["banned_for"] = banned_for(key)
    return e


def mix_titles():
    t = {}
    for p in (f"{T7}/OB-EDITS/music/mixkit-2026-11-07/SOURCES.txt", f"{T7}/OB-EDITS/music/mixkit-2026-11-11/SOURCES.txt"):
        if os.path.exists(p):
            for i, ti, ar in re.findall(r"(\d+) ([^|(]+?) \(([^)]+)\)", open(p).read()):
                t[i] = (ti.strip(), ar.strip())
    return t


def sfx_entry_base(path, h, rec, src_dir_names):
    b = os.path.basename(path); pack = h["pack"]; r = {}
    e = {"pack": pack, "code_made": bool(h.get("code_made")), "licence": None, "title": os.path.splitext(b)[0], "recording_id": None}
    if pack == "openverse":
        r = rec.get("ov:" + b, {}); e.update(title=r.get("title") or e["title"], licence=f"{r.get('license', '?')} {r.get('license_version', '')} via {r.get('source', 'openverse')}".strip(),
                                           source=r.get("landing_page"), query=r.get("query"))
    elif pack == "mixkit":
        e["licence"] = "Mixkit Sound Effects Free License (mixkit.co/license)"
    elif pack == "tai":
        r = rec.get("sfx_tai:" + b, {}); e["licence"] = r.get("licence"); e["recording_id"] = "tai:" + os.path.splitext(os.path.basename(r.get("source", b)))[0]; e["note"] = r.get("why")
    elif pack == "kenney-real":
        r = rec.get("sfx_real:" + b, {}); e["licence"] = "CC0 (Kenney)"; e["recording_id"] = "kenney:" + (r.get("source") or b); e["note"] = r.get("why")
    elif pack == "kenney-raw":
        rel = "/".join(path.split("/")[-3:]); e["licence"] = "CC0 (Kenney)"; e["recording_id"] = "kenney:" + rel
    elif pack == "ob-drive":
        r = rec.get("drive:" + b, {}); e["licence"] = f"OB's Drive pack ({r.get('owner', 'shared with OB')}); no licence column"
    elif pack == "code-kit":
        e["licence"] = "made in code by sfx.py"
    low = (path + " " + e["title"] + " " + str(e.get("recording_id") or "")).lower()
    fam = None
    if "glitch" in low or re.search(r"maximize|minimize", low):
        fam = "glitch"
    elif "kenney" in low and re.search(r"tick", low):
        fam = "kenney tick"
    e["banned_family"] = fam
    cl = None
    for c, kw in CLASS_KW:
        if re.search(kw, (e["title"] + " " + b + " " + str(e.get("query") or "")).lower()):
            cl = c; break
    e["class"], e["class_src"] = cl, ("name" if cl else None)
    return e


# ---------------------------------------------------------------- build
def copy_unique(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
        return dst
    if os.path.exists(dst):
        dst = re.sub(r"(\.\w+)$", r"-" + sha256_file(src)[:8] + r"\1", dst)
    shutil.copy2(src, dst)
    return dst


def build(args):
    cfg = load_cfg()
    P = cfg["paths"]; idxp = index_path(cfg); mdir = xp(P["music_bank"]); sdir = xp(P["sfx_banks"][-1])
    for p in (idxp, mdir, sdir):
        if p.startswith(T7):
            raise SystemExit(f"refusing to write under {T7}: {p}")
    if shutil.disk_usage(os.path.dirname(mdir)).free < 2 << 30:
        raise SystemExit("less than 2 GB free on the internal disk: not copying")
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    old = json.load(open(idxp)) if os.path.exists(idxp) else {"version": 1, "music": {}, "sfx": {}, "filecache": {}}
    fc = old.setdefault("filecache", {})
    rec = sidecars(); mt = mix_titles()

    def sha_of(p):
        st = os.stat(p); k = f"{p}|{st.st_size}|{int(st.st_mtime)}"
        if k not in fc:
            fc[k] = sha256_file(p)
        return fc[k]

    music = {}; sfx = {}
    msrc = music_sources(); ssrc = sfx_sources()
    if limit:
        msrc, ssrc = msrc[:limit], ssrc[:limit]
    for p, h in msrc:
        s = sha_of(p)
        if s not in music:
            music[s] = {"paths": [], "_h": h, "_src": p}
        music[s]["paths"].append(p)
    for p, h in ssrc:
        s = sha_of(p)
        if s not in sfx:
            sfx[s] = {"paths": [], "_h": h, "_src": p}
        sfx[s]["paths"].append(p)
    print(f"sources: {sum(len(v['paths']) for v in music.values())} music files = {len(music)} unique; "
          f"{sum(len(v['paths']) for v in sfx.values())} sounds = {len(sfx)} unique", flush=True)
    # copy (T7 originals stay; the copy is paths[0])
    if "--no-copy" not in args:
        for s, v in music.items():
            if v["paths"][0].startswith(T7):
                dst = copy_unique(v["_src"], f"{mdir}/{v['_h']['lane']}/{os.path.basename(v['_src'])}")
                v["paths"].insert(0, dst)
        for s, v in sfx.items():
            if v["paths"][0].startswith(T7):
                dst = copy_unique(v["_src"], f"{sdir}/{v['_h']['dest']}/" + ("" if v["_h"]["dest"] == "mixkit" else os.path.basename(os.path.dirname(v["_src"])) + "/") + os.path.basename(v["_src"]))
                v["paths"].insert(0, dst)
        rd = f"{mdir}/_records"
        for src in [f"{T7}/OB-EDITS/music/mixkit-2026-11-07/SOURCES.txt", f"{T7}/OB-EDITS/music/pixabay/SOURCES.txt",
                    f"{T7}/OB-EDITS/music/pixabay-2026-11-07/SOURCES.txt", f"{T7}/OB-EDITS/music/MUSIC-LIBRARY.md",
                    f"{T7}/OB-EDITS/C4367-edit/music_dl/LICENSE-RECORD.json", f"{T7}/OB-EDITS/C4367-edit/music_dl/mixkit-license-page-2026-10-20.jpg",
                    f"{T7}/OB-EDITS/sfx-library/openverse/SOURCES.csv"]:
            if os.path.exists(src):
                parts = src.split("/")
                copy_unique(src, (f"{sdir}/openverse/SOURCES.csv" if src.endswith("openverse/SOURCES.csv") else f"{rd}/{parts[-2]}/{parts[-1]}"))
        rec = sidecars()
    # entries: keep old analysis for known hashes
    new_m, new_s = [], []
    for s, v in music.items():
        e = old["music"].get(s) or {}
        base = music_entry_base(v["_src"], v["_h"], rec, mt)
        keep = {k: e[k] for k in e if k not in base and k != "paths"} if e else {}
        music[s] = {**base, **keep, "sha256": s, "paths": [xp(p) for p in v["paths"]]}
        if "bpm_1x" not in music[s]:
            new_m.append(s)
    for s, v in sfx.items():
        e = old["sfx"].get(s) or {}
        base = sfx_entry_base(v["_src"], v["_h"], rec, None)
        keep = {k: e[k] for k in e if k not in base and k != "paths"} if e else {}
        sfx[s] = {**base, **keep, "sha256": s, "paths": [xp(p) for p in v["paths"]]}
        if not sfx[s].get("class") and sfx[s].get("class_scores"):   # name gave nothing: earshot's class from the stored scores
            cs = sfx[s]["class_scores"]; sfx[s]["class"], sfx[s]["class_src"] = max(cs, key=cs.get), "earshot"
        if "duration_s" not in sfx[s]:
            new_s.append(s)
    print(f"to analyse: {len(new_m)} tracks, {len(new_s)} sounds", flush=True)
    emb = {}
    ep = idxp.replace(".json", "_embeddings.npz")
    if os.path.exists(ep):
        z = np.load(ep); emb = {k: z[k] for k in z.files}
    if "--no-audio" not in args and (new_m or new_s):
        os.environ.setdefault("EARSHOT_HOME", f"{ED}/earshot-home"); os.environ.setdefault("EARSHOT_OFFLINE", "1"); os.environ.setdefault("EARSHOT_THREADS", "3")
        from earshot import api, vocab
        for i, s in enumerate(new_m):
            e = music[s]; p = next(q for q in e["paths"] if os.path.exists(q))
            e.update(analyse_music(p, api)); e["tone"] = tone_score(e)
            emb[s] = vocab.embed_files([p])[0].astype(np.float32)
            print(f"  music {i + 1}/{len(new_m)} {e['title'][:34]:34} {e['bpm_1x']:6.1f} bpm {e['key']} {e['mode']:5} {e['lufs']:6.1f} LUFS tone {e['tone']}", flush=True)
        if new_s:
            paths = [next(q for q in sfx[s]["paths"] if os.path.exists(q)) for s in new_s]
            for i in range(0, len(paths), 24):
                A = vocab.embed_files(paths[i:i + 24])
                for j, s in enumerate(new_s[i:i + 24]):
                    emb[s] = A[j].astype(np.float32)
            for i, s in enumerate(new_s):
                sfx[s].update(analyse_sfx(paths[i], api))
            v = vocab.get(); names = list(SFX_CLASSES)
            T = v.embed_text([SFX_CLASSES[c] for c in names]); A = np.stack([emb[s] for s in new_s])
            Z = v.calibrate(A, T)["z_q"]
            for i, s in enumerate(new_s):
                sfx[s]["class_scores"] = {c: round(float(Z[i, j]), 2) for j, c in enumerate(names)}
                if not sfx[s].get("class"):
                    sfx[s]["class"], sfx[s]["class_src"] = names[int(np.argmax(Z[i]))], "earshot"
            print(f"  sounds analysed: {len(new_s)}", flush=True)
    # full mood vector (earshot's describe only lists the tags above its threshold, so a gloomy term can be missing): every track x all 16 mood phrases
    need = [s for s, e in music.items() if "mood_all" not in e and s in emb]
    if need and "--no-audio" not in args:
        os.environ.setdefault("EARSHOT_HOME", f"{ED}/earshot-home"); os.environ.setdefault("EARSHOT_OFFLINE", "1")
        from earshot import vocab
        v = vocab.get(); names = list(v.cats["music_mood"])
        Z = v.calibrate(np.stack([emb[s] for s in need]), v.embed_text(names))["z_q"]
        for i, s in enumerate(need):
            music[s]["mood_all"] = {n: round(float(Z[i, j]), 2) for j, n in enumerate(names)}
        print(f"  mood vectors: {len(need)} tracks", flush=True)
    # usage and verdicts
    for e in list(music.values()) + list(sfx.values()):
        e["used_in"] = []
    scrape_usage(music, sfx)
    for e in music.values():
        key = (" ".join(e["paths"]) + " " + e["title"]).lower()
        e["ob_verdict"] = [{"date": d, "words": w, "file": f, "verdict": vv} for k, d, vv, w, f in OB_VERDICTS if k in key]
        for k, ed, d, fm in KNOWN_USES:
            if k in key and not any(u["edit"] == ed for u in e["used_in"]):
                e["used_in"].append({"edit": ed, "date": d, "format": fm, "src": "AUDIT-AUDIO 2"})
        e["tone"] = tone_score(e)
        for k, val in VOCALS_KNOWN:
            if k in key:
                e["vocals"], e["vocal_p"], e["vocals_src"] = val, (1.0 if val else 0.0), f"title ('{k}')"; break
    # recording ids for sounds with none: one per unique file
    for s, e in sfx.items():
        if not e.get("recording_id"):
            e["recording_id"] = "sha:" + s[:10]
    idx = {"version": 1, "built": datetime.datetime.now().isoformat(timespec="seconds"), "music": music, "sfx": sfx, "filecache": fc}
    os.makedirs(os.path.dirname(idxp), exist_ok=True)
    tmp = idxp + ".tmp"; json.dump(idx, open(tmp, "w"), indent=1); os.replace(tmp, idxp)
    if emb:
        np.savez(ep.replace(".npz", "") + ".tmp.npz", **emb); os.replace(ep.replace(".npz", "") + ".tmp.npz", ep)
    seed_usage(idx)
    write_md(idx, cfg)
    print(f"wrote {idxp} ({len(music)} tracks, {len(sfx)} sounds) and BANK.md", flush=True)


def scrape_usage(music, sfx):
    roots = [os.path.expanduser("~/ob-work"), "/Volumes/OB-ARCHIVE/OB-EDITS", f"{T7}/OB-EDITS"]
    by_base = {}
    for s, e in list(music.items()) + list(sfx.items()):
        for p in e["paths"]:
            by_base.setdefault(os.path.basename(p).lower(), []).append(e)
    for r in roots:
        for pat in ("*/WORK/story/score*.json", "*/story/score*.json", "*/*/WORK/story/score*.json"):
            for f in glob.glob(os.path.join(r, pat)):
                try:
                    d = json.load(open(f)); cues = d.get("cues", []) if isinstance(d, dict) else d
                except Exception:
                    continue
                edit = (re.search(r"C\d{3,5}", f) or re.search(r"([^/]+)/(?:WORK/)?story/", f)).group(0).split("/")[0]
                date = datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat()
                for c in cues:
                    for e in by_base.get(os.path.basename(str(c.get("track", ""))).lower(), []):
                        if "bpm_1x" in e or "title" in e and "pack" not in e:
                            if not any(u["edit"] == edit for u in e["used_in"]):
                                e["used_in"].append({"edit": edit, "date": date, "format": "long-form" if len(cues) > 2 else "reel", "src": os.path.basename(f)})
        for pat in ("*/WORK/story/sfx_plan*.json", "*/story/sfx_plan*.json"):
            for f in glob.glob(os.path.join(r, pat)):
                try:
                    hits = json.load(open(f)).get("hits", [])
                except Exception:
                    continue
                edit = (re.search(r"C\d{3,5}", f) or re.search(r"([^/]+)/(?:WORK/)?story/", f)).group(0).split("/")[0]
                date = datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat()
                for h in hits:
                    for e in by_base.get(os.path.basename(str(h.get("file", ""))).lower(), []):
                        if "pack" in e and not any(u["edit"] == edit for u in e["used_in"]):
                            e["used_in"].append({"edit": edit, "date": date, "format": "plan", "src": os.path.basename(f)})


def jl(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def seed_usage(idx, force=False):
    """qc/music_usage.json: the reuse ledger music_pick.py reads (and `music_pick.py use WORK` appends to). Seeded once."""
    p = f"{ED}/qc/music_usage.json"
    if os.path.exists(p) and not force and not (jl(p) or {}).get("_seeded_by"):
        return
    rows = {}
    for s, e in idx["music"].items():
        for u in e.get("used_in", []):
            r = rows.setdefault(u["edit"], {"edit": u["edit"], "date": u["date"], "format": u["format"], "sha256": [], "titles": []})
            r["sha256"].append(s); r["titles"].append(e["title"])
    json.dump({"_seeded_by": "bank_index.py build (replaced by the first `music_pick.py use`)", "_about": "music used per delivered edit, oldest first; music_pick.py reads the last no_reuse_last_edits edits",
               "edits": sorted(rows.values(), key=lambda r: (r["date"], r["edit"]))}, open(p, "w"), indent=1)


def write_md(idx, cfg):
    L = ["# Bank index (generated by bank_index.py; do not edit)", f"Built {idx.get('built')}. {len(idx['music'])} tracks, {len(idx['sfx'])} sounds, by sha256.", "",
         "## Music eligible today, by route and kind", "", "| route | kind | eligible | of which upbeat (tone > 0) | names |", "|---|---|---|---|---|"]
    routes = json.load(open(FORMATS))["routes"]
    for r, rv in routes.items():
        if rv.get("music") == "none":
            continue
        c = load_cfg(r)
        for kind in (("educational",) if r != "reel-reaction" else ("reaction",)):
            ok = [e for e in idx["music"].values() if not music_ineligible(e, c, kind)]
            up = [e for e in ok if (e.get("tone") or -9) > 0 and e.get("mode") == "major"]
            L.append(f"| {r} | {kind} | {len(ok)} | {len(up)} | {', '.join(sorted(e['title'] for e in up))[:150]} |")
    L += ["", "## Music", "", "| title | artist | lane | bpm (1x/2x) | key | LUFS | LRA | tone | vocals | ai/CID checked | banned | used in |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in sorted(idx["music"].values(), key=lambda e: (e["lane"], e["title"])):
        L.append(f"| {e['title']} | {e.get('artist') or ''} | {e['lane']} | {e.get('bpm_1x')}/{e.get('bpm_2x')} | {e.get('key')} {e.get('mode') or ''} | {e.get('lufs')} | {e.get('lra_lu')} | "
                 f"{e.get('tone')} | {'y' if e.get('vocals') else 'n'} | {e.get('ai_label_checked') or '-'}/{e.get('content_id_checked') or '-'} | "
                 f"{'; '.join(sorted(set(e['banned_for'].values())))[:40]} | {', '.join(u['edit'] for u in e['used_in'])} |")
    L += ["", "## Sounds by pack and class", ""]
    packs = sorted({e["pack"] for e in idx["sfx"].values()})
    classes = sorted({e.get("class") or "?" for e in idx["sfx"].values()})
    L.append("| pack | n | recordings | " + " | ".join(classes) + " |"); L.append("|---|---|---|" + "---|" * len(classes))
    for p in packs:
        es = [e for e in idx["sfx"].values() if e["pack"] == p]
        L.append(f"| {p} | {len(es)} | {len({e['recording_id'] for e in es})} | " + " | ".join(str(sum(1 for e in es if (e.get('class') or '?') == c)) for c in classes) + " |")
    ban = [e for e in idx["sfx"].values() if e.get("banned_family")]
    L += ["", f"Banned-family sounds (never picked): {len(ban)}. Code-made (never picked): {sum(1 for e in idx['sfx'].values() if e['code_made'])}."]
    out = os.path.join(os.path.dirname(index_path(cfg)), "BANK.md")
    open(out, "w").write("\n".join(L) + "\n")


# ---------------------------------------------------------------- CLI and selftest
def selftest():
    import tempfile
    work = os.path.expanduser("~/ob-scratch/skill-rebuild/WP2/bank_selftest"); os.makedirs(work, exist_ok=True)
    ok = True
    def chk(name, cond, detail=""):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    sr = 48000; t = np.arange(sr * 2) / sr
    x = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    f1, f2 = f"{work}/a.f32", f"{work}/b.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", f2], input=x.tobytes(), check=True)
    f3 = f"{work}/renamed_innocent_name.wav"; shutil.copy2(f2, f3)
    s = sha256_file(f2)
    chk("a copy under another name has the same hash", sha256_file(f3) == s)
    idx = {"music": {s: {"sha256": s, "title": "Tapis (planted)", "lane": "youtube-safe", "licence": "x", "ai_label_checked": "2026-11-07",
                         "content_id_checked": "2026-11-07", "banned_for": banned_for("mixkit_615")}}, "sfx": {}}
    json.dump(idx, open(f"{work}/idx.json", "w"))
    kind, sha, e = lookup_path(f3, idx)
    chk("lookup finds a renamed copy by hash", kind == "music" and e["title"].startswith("Tapis"))
    chk("renamed blocked track is ineligible for educational", music_ineligible(e, load_cfg("long-form"), "educational") is not None,
        str(music_ineligible(e, load_cfg("long-form"), "educational")))
    e2 = dict(e, banned_for={}); chk("same track unbanned is eligible on long-form", music_ineligible(e2, load_cfg("long-form")) is None)
    e3 = dict(e2, content_id_checked=None); chk("youtube-safe without a Content ID date is ineligible", music_ineligible(e3, load_cfg("long-form")) is not None)
    e4 = dict(e2, lane="viral"); chk("a viral song is ineligible on long-form and on ads", music_ineligible(e4, load_cfg("long-form")) and music_ineligible(e4, load_cfg("ad")))
    chk("a viral song is eligible on a reel", music_ineligible(e4, load_cfg("reel-talking")) is None)
    k, sh, nothing = lookup_path(f"{work}/a.f32" if os.path.exists(f"{work}/a.f32") else f2, {"music": {}, "sfx": {}})
    chk("an unknown file is not found", nothing is None)
    v = (0.1 * np.sin(2 * np.pi * 200 * np.arange(sr * 4) / sr))
    chk("lufs: -20 dBFS sine is about -20 LUFS (dual mono +3)", -19 < lufs(v) + 3.0 < -15 or -23 < lufs(v) < -14, f"{lufs(v):.1f}")
    chk("lufs: 10 dB quieter reads 10 LU lower", abs((lufs(v) - lufs(v * 10 ** -0.5)) - 10) < 0.3)
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return 0
    if a[0] == "--selftest":
        return selftest()
    if a[0] == "build":
        try:
            import librosa  # noqa: F401
        except Exception:
            if "--no-audio" not in a:
                py = f"{ED}/venvs/earshot/bin/python"
                os.execv(py, [py, os.path.abspath(__file__)] + a)
        build(a); return 0
    if a[0] == "lookup" and len(a) > 1:
        k, sha, e = lookup_path(a[1])
        if not e:
            print(f"NOT IN THE BANK: {a[1]} (sha256 {sha[:12]}): index it first (bank_index.py build)"); return 1
        e = {x: y for x, y in e.items() if x not in ("beats", "energy_2s_db")}
        print(json.dumps({"kind": k, **e}, indent=1)); return 0
    if a[0] == "eligible":
        r = a[a.index("--route") + 1] if "--route" in a else "long-form"; kd = a[a.index("--kind") + 1] if "--kind" in a else "educational"
        c = load_cfg(r); idx = load_index(c); n = 0
        for e in sorted(idx["music"].values(), key=lambda e: e["title"]):
            why = music_ineligible(e, c, kd)
            print(("ok     " if not why else "reject ") + f"{e['title'][:34]:34} {e['lane']:13} {e.get('mode') or '?':5} tone {e.get('tone')}  {why or ''}")
            n += not why
        print(f"{n} eligible for {r} / {kd}"); return 0
    if a[0] == "report":
        c = load_cfg(); write_md(load_index(c), c); print("BANK.md rewritten"); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
