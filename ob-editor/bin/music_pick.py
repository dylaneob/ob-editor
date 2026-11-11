#!/usr/bin/env python3
"""music_pick: the background music is a SCORED CHOICE from at least `min_candidates` tracks, tied to this cut, and recorded.

Why (OB 2026-11-07): "You use the worse music I swear", "You always go so depressing", "You have a bank of so many choices";
OB 11-07 "Education content should be upbeat and higher enegery", "turn the background music down"; M57 never reuse another video's
bed; M58 viral songs first for reels, copyright-friendly on YouTube. Before this the editor took one track (C4465: copied from the
last edit, cues at (37 x chapter) mod 66 s) and the gate could not tell.

  python3 -I music_pick.py WORK --route ROUTE [--kind educational|reaction|fdoe|story] [--voice VOICE.wav] [--tone "upbeat, bright"]
                           [--top 3] [--dur S] [--no-previews]
        reads the cut in WORK (job.json, events_resolved.json / plan/moments.json, cutlist.json, words_clean.json, plan/punch_lines.json,
        plan/sections.json: it prints which it used) and writes WORK/audio/edit_profile.json, WORK/audio/music_candidates.json,
        WORK/story/score.json (cue sheet, score.py shape) and 30 s previews of the top 3 under his voice in WORK/audio/previews/
  python3 -I music_pick.py apply WORK [--route ROUTE] [--voice VOICE.wav] [--pick N]
        mixes the chosen bed under the voice at the config level (bed_lu_under_voice, stem vs stem), held duck, punch-line drop-outs,
        fade; writes WORK/audio/voice.wav, bed.wav and manifest.json {voice, bed, sfx, music: [{file, sha256, start, offset}], declared}
  python3 -I music_pick.py mix WORK VIDEO [--out OUT.mp4] [--route ROUTE]
        voice + bed + every sound in story/sfx_plan.json -> master (formats.json defaults.master) -> WORK/audio/final_mix.wav -> muxed onto VIDEO's
        copied picture as OUT (default VIDEO_mix.mp4 beside it); recorded pieces carried over; manifest updated; prints the gate command
  python3 -I music_pick.py use WORK            appends the picked track to qc/music_usage.json (run when the pick is rendered)
  python3 -I music_pick.py --selftest

All numbers (levels, candidate count, reuse window, margin, duck timing, punch drop) are read from ~/ob-editor/qc/formats.json.
Scoring weights below are this tool's own and are printed in every record so a wrong score can be argued with.
"""
import datetime, glob, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank_index as BI   # noqa: E402

ED = BI.ED
WEIGHTS = {"beat": 18, "energy": 22, "under_voice": 20, "taste": 15, "tone": 25}   # sums to 100; this tool's own
BEAT_TOL = 0.06           # s: a picture change within 60 ms of a beat or half beat (AUDIT-AUDIO 5B step 3)
SUSTAIN_FLOOR_DB, SWING_MAX_DB = -28.0, 7.0   # youtube-longform PRESET: Fragments of Bangkok left the title card 37 dB under his voice
MAX_DROPS = {"long": 4, "reel": 2}            # youtube-longform PRESET: at most 4 silences; reels: the D reel had 2 punch lines
DUCK_DB = {"long": 2.5, "reel": 4.0}          # preset "held duck 2.5 dB" (long form); score.py / music_mix 4-5 dB (reels)
SECTION_REL = {"hook": 0.0, "teach": 0.0, "body": 0.0, "verdict": 2.0, "proof": 1.0, "confession": -3.0, "payoff": 2.0, "cta": 1.0}
TONE_LO, TONE_HI = -0.5, 1.5                  # tone_score range mapped to 0..1 (measured bank: -2.3 .. 2.1; OB's picks sit at 0.8-1.2)
UPBEAT_MIN = 0.0                              # educational/reaction/FDOE: earshot tone_score must be above this
MINOR_OK_TONE = 0.75                          # a chroma "minor" reading is overruled when earshot says clearly upbeat: key detection confuses
                                              # relative keys, and it reads Upbeat Jazz (OB's 11-08 pick) as minor. 0.75 = lowest tone of his picks


def jload(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


# ---------------------------------------------------------------- reading the cut
def find_work(work):
    """Everything that exists in WORK that tells us about the cut. Returns (info, used) where used lists what was read."""
    w = BI.xp(work); used = []
    info = {"events": [], "cuts": [], "words": [], "segments": [], "dur": None, "job": {}}
    job = jload(f"{w}/job.json")
    if job:
        info["job"] = job; used.append("job.json")
    ev = jload(f"{w}/events_resolved.json")
    if ev:
        ev = ev.get("events", ev) if isinstance(ev, dict) else ev
        info["events"] = [{"id": e.get("id"), "type": e.get("type"), "t": float(e["edit_in"]), "t1": float(e.get("edit_out", e["edit_in"])),
                           "text": " ".join(c[0] for c in e.get("chunks", []) if c) if e.get("chunks") else (e.get("text") or e.get("desc") or "")}
                          for e in ev if isinstance(e, dict) and e.get("edit_in") is not None]
        used.append(f"events_resolved.json ({len(info['events'])} events)")
    mo = jload(f"{w}/plan/moments.json")
    if mo and not info["events"]:
        info["events"] = [{"id": m.get("id"), "type": m.get("type", "moment"), "t": float(m["t"]), "t1": float(m["t"]), "text": m.get("what", "")} for m in mo]
        used.append(f"plan/moments.json ({len(mo)} moments)")
    cl = jload(f"{w}/cutlist.json")
    if cl and cl.get("segments"):
        info["segments"] = cl["segments"]
        info["cuts"] = sorted(float(s["edit_in"]) for s in cl["segments"] if s.get("edit_in") and float(s["edit_in"]) > 0)
        info["dur"] = max(float(s.get("edit_out", 0)) for s in cl["segments"])
        used.append(f"cutlist.json ({len(cl['segments'])} segments)")
    for name in ("words_clean.json", "story/words_dtw.json", "story/words_base.json"):
        wd = jload(f"{w}/{name}")
        if wd and wd.get("words"):
            info["words"] = [(float(a), float(b), str(t)) for a, b, t in wd["words"]]; used.append(name); break
    if info["dur"] is None:
        info["dur"] = (job or {}).get("dur") or (max([e["t1"] for e in info["events"]]) if info["events"] else None)
    return info, used


def edit_words(info):
    """words in EDIT time (mapped through the cut list when it exists)."""
    out = []
    segs = info["segments"]
    for a, b, t in info["words"]:
        if segs:
            for s in segs:
                if float(s["src_in"]) <= a < float(s["src_out"]):
                    out.append((float(s["edit_in"]) + a - float(s["src_in"]), float(s["edit_in"]) + b - float(s["src_in"]), t)); break
        else:
            out.append((a, b, t))
    return out


def sentences(words, gap=0.8):
    S, cur = [], []
    for a, b, t in words:
        if t in (".", "?", "!", ">>", ",") and not cur:
            continue
        if cur and (a - cur[-1][1] > gap):
            S.append(cur); cur = []
        if t not in (".", ">>"):
            cur.append((a, b, t))
        if t.endswith((".", "?", "!")) or t == ".":
            if cur:
                S.append(cur); cur = []
    if cur:
        S.append(cur)
    return [{"t0": s[0][0], "t1": s[-1][1], "text": " ".join(x[2] for x in s)} for s in S if len(s) >= 2]


TURN = re.compile(r"^(but|however|yet|except|turns out|here'?s the thing|the problem|the catch|the truth)\b", re.I)
NUMBER = re.compile(r"\b\d+(\.\d+)?\s?(%|percent|x\b|times|pounds|lbs|kg|weeks|calories|grams)", re.I)


def build_profile(info, used, route, kind, dur, tone_words, cfg, work):
    ew = edit_words(info) if info["words"] else []
    sents = sentences(ew)
    long = cfg["long"]
    ev = info["events"]
    # sections
    over = jload(f"{work}/plan/sections.json")
    secs = []
    if over:
        secs = [{"name": s.get("name", "section"), "t0": float(s["t0"]), "t1": float(s["t1"]), "job": s.get("job", "teach")} for s in over]; used.append("plan/sections.json")
    else:
        chap = sorted([e for e in ev if e["type"] == "chapter"], key=lambda e: e["t"])
        if long and chap:
            secs.append({"name": "intro", "t0": 0.0, "t1": chap[0]["t"], "job": "hook"})
            for i, c in enumerate(chap):
                t1 = chap[i + 1]["t"] if i + 1 < len(chap) else dur
                txt = c["text"].lower()
                job = "confession" if re.search(r"couldn.?t|i felt|the week i|struggl|hardest", txt) else ("verdict" if (i == len(chap) - 1 or re.search(r"verdict|worth|should you|bottom line|result", txt)) else "teach")
                secs.append({"name": f"ch{i + 1}: {c['text'][:40]}", "t0": c["t"], "t1": t1, "job": job})
        else:
            h = min(6.0, max(2.0, 0.2 * dur)); cta = min(4.0, 0.12 * dur)
            if sents and sents[0]["t1"] < 0.4 * dur:
                h = max(2.0, min(6.0, sents[0]["t1"]))
            secs = [{"name": "hook", "t0": 0.0, "t1": h, "job": "hook"}, {"name": "body", "t0": h, "t1": 0.7 * dur, "job": "body"},
                    {"name": "payoff", "t0": 0.7 * dur, "t1": dur - cta, "job": "payoff"}, {"name": "cta", "t0": dur - cta, "t1": dur, "job": "cta"}]
    secs = [s for s in secs if s["t1"] - s["t0"] > 0.5]
    # turn and punch lines
    turn, punch = [], []
    for i, s in enumerate(sents):
        if TURN.match(s["text"]):
            turn.append(dict(s, why="starts with a turn word"))
        if NUMBER.search(s["text"]) and 0.6 < s["t1"] - s["t0"] < 5 and s["t0"] > 3:
            punch.append(dict(s, why="a number lands"))
    if sents:
        last = [s for s in sents if s["t1"] < dur - 3]
        if last:
            punch.append(dict(last[-1], why="last line before the CTA"))
    punch += [dict(s, why="turn line") for s in turn]
    pl = jload(f"{work}/plan/punch_lines.json")
    if pl:
        punch = [{"t0": float(p[0] if isinstance(p, list) else p["t0"]), "t1": float(p[1] if isinstance(p, list) else p["t1"]), "text": "", "why": "plan/punch_lines.json (editor)"} for p in pl]
        used.append("plan/punch_lines.json")
    cap = MAX_DROPS["long" if long else "reel"]; keep = []
    for p in sorted(punch, key=lambda p: p["t0"]):
        if not keep or p["t0"] - keep[-1]["t1"] > 8.0:
            keep.append(p)
    punch = keep[:cap]
    nw = len(ew); cuts = info["cuts"]
    prof = {"route": route, "kind": kind, "long": long, "dur_s": round(dur, 2), "inputs_used": used,
            "pace": {"words_per_s": round(nw / dur, 2) if nw else None, "cuts_per_min": round(len(cuts) / (dur / 60), 1) if cuts else None,
                     "median_shot_s": round(float(np.median(np.diff([0] + cuts + [dur]))), 2) if cuts else None,
                     "graphic_entrances_per_min": round(len(ev) / (dur / 60), 1) if ev else None},
            "sections": secs, "turn_lines": turn, "punch_lines": punch,
            "target_mood": tone_words, "cut_times": [round(c, 3) for c in cuts], "entrance_times": [round(e["t"], 3) for e in ev],
            "note": "turn/punch lines are proposed from the words (turn word, a number landing, the last line before the CTA); the editor may overwrite with plan/punch_lines.json and plan/sections.json"}
    return prof


# ---------------------------------------------------------------- scoring
def beat_grid(e):
    b = np.array(e.get("beats") or [])
    if len(b) < 4:
        return np.array([])
    mids = (b[:-1] + b[1:]) / 2
    return np.sort(np.concatenate([b, mids]))


def beat_share(G, T, o):
    if len(G) == 0 or len(T) == 0:
        return None
    p = np.asarray(T) + o
    i = np.clip(np.searchsorted(G, p), 1, len(G) - 1)
    d = np.minimum(np.abs(G[i] - p), np.abs(G[i - 1] - p))
    return float((d <= BEAT_TOL).mean())


def win_stats(E, o, t0, t1):
    """median and swing of the track's 2 s energy bins under edit window [t0,t1] when the track starts at offset o (wraps)."""
    n = len(E)
    i0 = int((o + t0) // 2); i1 = max(i0 + 1, int(np.ceil((o + t1) / 2)))
    w = E[np.arange(i0, i1) % n]
    sw = float(np.percentile(w, 90) - np.percentile(w, 10)) if len(w) >= 5 else float(w.max() - w.min())   # p90-p10: one fill must not disqualify a stretch
    return float(np.median(w)), sw, float(w.min())


def energy_fit(e, o, secs):
    """0..1: how well the track's energy from offset o follows the sections (steady hook, lift at payoff, dip on a confession),
    sustained (no near-silent stretch, no swing over SWING_MAX_DB)."""
    E = np.array(e.get("energy_2s_db") or [])
    if len(E) < 4:
        return None, []
    med = float(np.median(E)); parts = []
    for s in secs:
        L = min(s["t1"] - s["t0"], 40.0)
        m, sw, mn = win_stats(E, o, s["t0"], s["t0"] + L)
        want = SECTION_REL.get(s["job"], 0.0)
        match = 1 - min(1.0, abs((m - med) - want) / 6.0)
        sus = 1.0 if (m > SUSTAIN_FLOOR_DB and sw <= SWING_MAX_DB) else 0.3
        steady = 1.0
        if s["job"] == "hook":
            hm, hs, _ = win_stats(E, o, s["t0"], s["t0"] + 4.0); steady = 1.0 if hs <= 3.0 else 0.5
        parts.append({"section": s["name"], "job": s["job"], "fit": round(0.5 * match + 0.3 * sus + 0.2 * steady, 3), "track_db": round(m, 1), "swing_db": round(sw, 1)})
    return float(np.mean([p["fit"] for p in parts])), parts


def best_offset(e, prof, secs, events_t):
    """start offset (s into the track) maximising 0.5 beat + 0.5 energy; returns (offset, beat_share, beat_norm, energy, energy_parts)."""
    tdur = float(e["duration_s"]); dur = prof["dur_s"]
    span = max(0.0, tdur - min(dur, tdur)); span = min(span if span > 0 else 20.0, 60.0)
    grid = np.arange(0.0, span + 1e-9, 0.1)
    G = beat_grid(e); conf = float(e.get("bpm_conf") or 0.0)
    T = [t for t in events_t if t < min(dur, 90.0)]
    per = float(np.mean(np.diff(G))) if len(G) > 2 else 0.25
    chance = min(0.9, 2 * BEAT_TOL / max(per, 1e-3))
    best = None
    for o in grid:
        bs = beat_share(G, T, o)
        bn = None if bs is None else max(0.0, min(1.0, (bs - chance) / (1 - chance)))
        bpart = (conf * bn + (1 - conf) * 0.35) if bn is not None else 0.5
        ef, parts = energy_fit(e, o, secs)
        ef = 0.5 if ef is None else ef
        j = 0.5 * bpart + 0.5 * ef
        if best is None or j > best[0]:
            best = (j, o, bs, bn, ef, parts, bpart)
    j, o, bs, bn, ef, parts, bpart = best
    return o, bs, bpart, ef, parts, round(chance, 2)


def under_voice(e):
    sh = float(e.get("share_1_4k") or 0.4); lra = float(e.get("lra_lu") or 6.0); vp = float(e.get("vocal_p") or 0.0)
    a = 1 - min(1, max(0, (sh - 0.25) / 0.25)); b = 1 - min(1, vp * 1.5); c = 1 - min(1, max(0, (lra - 3) / 7))
    return 0.4 * a + 0.3 * b + 0.3 * c, {"share_1_4k": sh, "vocal_p": vp, "lra_lu": lra}


def taste(idx, emb, sha):
    liked = [s for s, e in idx["music"].items() if any(v["verdict"] == "picked" for v in e.get("ob_verdict", [])) and s != sha and s in emb]
    rej = [s for s, e in idx["music"].items() if any(v["verdict"] == "rejected" for v in e.get("ob_verdict", [])) and s != sha and s in emb]
    if sha not in emb or not liked:
        return 0.5, {"note": "no embedding or no liked tracks"}
    v = emb[sha]; cl = float(np.mean([v @ emb[s] for s in liked])); cr = float(np.mean([v @ emb[s] for s in rej])) if rej else cl
    return float(np.clip(0.5 + 2.0 * (cl - cr) + 1.0 * (cl - 0.5), 0, 1)), {"cos_liked": round(cl, 3), "cos_rejected": round(cr, 3), "liked_n": len(liked), "rejected_n": len(rej)}


def tone_part(e):
    t = BI.tone_score(e)
    if t is None:
        return 0.5, None
    return float(np.clip((t - TONE_LO) / (TONE_HI - TONE_LO), 0, 1)), t


def load_usage():
    p = f"{ED}/qc/music_usage.json"
    return jload(p, {"edits": []})


def recent_shas(usage, n, current_edit=None):
    rows = [r for r in usage.get("edits", []) if r.get("edit") != current_edit][-n:]
    return {s: r["edit"] for r in rows for s in r.get("sha256", [])}


def edit_name(work):
    m = re.search(r"(C\d{3,5})", BI.xp(work))
    return m.group(1) if m else os.path.basename(os.path.dirname(BI.xp(work)))


def pick(work, route, idx, emb, usage, kind=None, dur=None, tone_words="upbeat, bright, confident", top=3, cfg=None, write=True):
    cfg = cfg or BI.load_cfg(route); mc = cfg["music"]
    kind = kind or ("reaction" if route == "reel-reaction" else "fdoe" if route == "reel-fdoe" else "educational")
    info, used = find_work(work)
    dur = dur or info["dur"]
    if not dur:
        raise SystemExit("music_pick: cannot tell how long the edit is: WORK has no cutlist.json / events / job.json dur. Pass --dur SECONDS.")
    if not (info["events"] or info["cuts"]):
        used.append("NO events or cuts found: beat fit not measured (write plan/moments.json [{id,t,what}] to measure it)")
    prof = build_profile(info, used, route, kind, dur, [w.strip() for w in tone_words.split(",")], cfg, BI.xp(work))
    secs = prof["sections"]; events_t = sorted(set(prof["cut_times"] + prof["entrance_times"]))
    recent = recent_shas(usage, mc["no_reuse_last_edits"], edit_name(work))
    cands, rejects = [], []
    for sha, e in idx["music"].items():
        why = BI.music_ineligible(e, cfg, kind)
        if not why and sha in recent:
            why = f"used in {recent[sha]} (one of the last {mc['no_reuse_last_edits']} edits; M57 never reuse another video's bed)"
        if not why and any(v["verdict"] == "rejected" for v in e.get("ob_verdict", [])):
            v = [v for v in e["ob_verdict"] if v["verdict"] == "rejected"][0]; why = f"OB rejected it {v['date']}: {v['words']}"
        if not why and kind in BI.TONE_KINDS:
            t = BI.tone_score(e)
            if e.get("mode") == "minor" and (e.get("mode_margin") or 0) >= 0.03 and (t is None or t < MINOR_OK_TONE):
                why = f"minor key ({e.get('key')} minor) and not clearly upbeat (tone {t}): educational/reaction/FDOE are major and upbeat (M57)"
            elif t is None:
                why = "no earshot mood tags in the index: run bank_index.py build"
            elif t <= UPBEAT_MIN:
                why = f"earshot mood reads gloomy/calm (tone {t}, needs > {UPBEAT_MIN}): '{(e.get('mood') or [{}])[0].get('term', '?')}'"
        if why:
            rejects.append({"sha256": sha, "title": e["title"], "lane": e["lane"], "reason": why}); continue
        o, bs, bpart, ef, parts, chance = best_offset(e, prof, secs, events_t) if events_t or True else (0, None, 0.5, 0.5, [], 0)
        uv, uvd = under_voice(e); ta, tad = taste(idx, emb, sha); tp, tv = tone_part(e)
        P = {"beat": bpart, "energy": ef, "under_voice": uv, "taste": ta, "tone": tp}
        score = sum(WEIGHTS[k] * P[k] for k in WEIGHTS)
        path = next((p for p in e["paths"] if os.path.exists(p)), e["paths"][0])
        cands.append({"sha256": sha, "title": e["title"], "artist": e.get("artist"), "lane": e["lane"], "file": path, "score": round(score, 1), "offset_s": round(float(o), 2),
                      "parts": {k: {"value": round(P[k], 3), "weight": WEIGHTS[k], "points": round(WEIGHTS[k] * P[k], 1)} for k in P},
                      "detail": {"beat_share": None if bs is None else round(bs, 2), "beat_chance": chance, "bpm": [e.get("bpm_1x"), e.get("bpm_2x")], "bpm_conf": e.get("bpm_conf"),
                                 "key": f"{e.get('key')} {e.get('mode')}", "tone": tv, "sections": parts, "under_voice": uvd, "taste": tad, "lufs": e.get("lufs")}})
    cands.sort(key=lambda c: -c["score"])
    for i, c in enumerate(cands):
        c["rank"] = i + 1; c["reason"] = reason_text(c, prof)
    n_ok = len(cands); short = n_ok < mc["min_candidates"]
    # viral-first (M58): a viral song wins unless a non-viral track scores more than the margin higher
    vf = {"applied": False, "margin": mc["viral_first_margin"]}
    chosen = cands[0] if cands else None
    if cands and not cfg["music_lanes"]:
        vir = [c for c in cands if c["lane"] == "viral"]
        if vir and cands[0]["lane"] != "viral" and cands[0]["score"] - vir[0]["score"] <= mc["viral_first_margin"]:
            chosen = vir[0]; vf = {"applied": True, "margin": mc["viral_first_margin"], "gap": round(cands[0]["score"] - vir[0]["score"], 1),
                                    "reason": f"viral song '{vir[0]['title']}' is within {mc['viral_first_margin']} points of '{cands[0]['title']}' (M58: his saved viral songs first)"}
    out = {"route": route, "kind": kind, "edit": edit_name(work), "made": datetime.datetime.now().isoformat(timespec="seconds"),
           "min_candidates": mc["min_candidates"], "n_candidates": n_ok, "bank_short": short,
           "searched": {"tracks_in_bank": len(idx["music"]), "lanes": cfg["music_lanes"] or BI.ALL_LANES, "kind": kind,
                        "filters": ["lane allowed on the route", "licence record", "youtube-safe needs dated AI-label + Content ID checks", "banned_for", f"not in the last {mc['no_reuse_last_edits']} edits",
                                    "not rejected by OB", "major mode + upbeat mood (educational/reaction/FDOE)"]},
           "weights": WEIGHTS, "candidates": cands, "rejects": rejects, "viral_first": vf, "pick": None}
    if short:
        out["bank_short_note"] = (f"only {n_ok} track(s) pass the filters for {route}/{kind}; need {mc['min_candidates']}. The delivery note must say the bank needs new tracks "
                                  f"(searched {len(idx['music'])} tracks; rejects listed below).")
    if chosen:
        top1 = cands[0]
        wr = None if chosen is top1 else vf.get("reason")
        cues = make_cues(chosen, idx["music"][chosen["sha256"]], prof, mc)
        out["pick"] = {"sha256": chosen["sha256"], "title": chosen["title"], "file": chosen["file"], "offset_s": chosen["offset_s"], "score": chosen["score"],
                       "is_top_score": chosen is top1, "written_reason": wr, "cues": cues, "runner_ups": [c["title"] for c in cands if c is not chosen][:2],
                       "credit": f"Music: \"{chosen['title']}\" by {chosen.get('artist') or 'unknown'} (Mixkit/Pixabay license)" if chosen["lane"] != "viral" else None,
                       "delivery_note": f"Music: {chosen['title']} (score {chosen['score']}). Runner-ups: {', '.join([c['title'] for c in cands if c is not chosen][:2])}. "
                                        f"Swap = one audio-only redo from WORK/audio/voice.wav." + (" BANK SHORT: the bank needs new tracks." if short else "")}
    if write:
        wd = BI.xp(work); os.makedirs(f"{wd}/audio", exist_ok=True); os.makedirs(f"{wd}/story", exist_ok=True)
        json.dump(prof, open(f"{wd}/audio/edit_profile.json", "w"), indent=1)
        json.dump(out, open(f"{wd}/audio/music_candidates.json", "w"), indent=1)
        if chosen:
            json.dump(cue_sheet(out["pick"], mc, prof), open(f"{wd}/story/score.json", "w"), indent=1)
    return out, prof


def reason_text(c, prof):
    p = c["parts"]; d = c["detail"]
    best = max(p, key=lambda k: p[k]["value"] * 1.0); worst = min(p, key=lambda k: p[k]["value"])
    bs = d["beat_share"]
    s = f"{c['title']} ({c['lane']}, {d['key']}, {d['bpm'][0]} bpm): strongest on {best.replace('_', ' ')}, weakest on {worst.replace('_', ' ')}"
    if bs is not None:
        s += f"; {int(bs * 100)}% of picture changes land on a beat (chance {int(d['beat_chance'] * 100)}%)"
    return s + f"; starts at {c['offset_s']} s into the track."


def make_cues(c, e, prof, mc):
    """cue list. Reels / one-section edits: one cue. Long form: one cue per section with its own best offset (replaces (37 x chapter) mod 66)."""
    dur = prof["dur_s"]; tdur = float(e["duration_s"]); E = np.array(e.get("energy_2s_db") or [0, 0])
    secs = prof["sections"]
    if not prof["long"] or len(secs) <= 1:
        return [{"track": c["file"], "sha256": c["sha256"], "t0": 0.0, "t1": round(dur, 2), "start": c["offset_s"], "fade_in": 0.4, "fade_out": mc["fade_out_s"], "loop": dur > tdur - c["offset_s"], "why": "reel: one bed, best beat and energy offset"}]
    cues, used = [], []
    bounds = [0.0] + list(e.get("sections_s") or []) + [tdur]
    med = float(np.median(E))
    for s in secs:
        L = min(s["t1"] - s["t0"], 16.0); want = SECTION_REL.get(s["job"], 0.0); best = None
        starts = sorted(set([round(b, 1) for b in bounds[:-1]] + [round(x, 1) for x in np.arange(0, max(1.0, tdur - min(L, tdur)), 2.0)]))
        for o in starts:
            m, sw, mn = win_stats(E, o, 0, L)
            sc = 1 - min(1.0, abs((m - med) - want) / 6.0)
            if m <= SUSTAIN_FLOOR_DB or sw > SWING_MAX_DB:
                sc -= 0.5   # not sustained: only chosen when nothing better exists, and the cue says so
            sc += 0.1 if any(abs(o - b) < 0.6 for b in bounds[:-1]) else 0.0
            sc -= 0.4 * sum(1 for u in used if abs(u - o) < 8.0)
            if best is None or sc > best[0]:
                best = (sc, o, m, sw)
        o = best[1] if best else c["offset_s"]
        used.append(o)
        cues.append({"track": c["file"], "sha256": c["sha256"], "t0": round(s["t0"], 2), "t1": round(s["t1"], 2), "start": round(float(o), 2),
                     "fade_in": 1.2, "fade_out": 1.2, "loop": bool((s["t1"] - s["t0"]) > (tdur - o)), "section": s["name"], "job": s["job"],
                     "why": (f"best stretch of the track for a '{s['job']}' section (level {best[2]:.1f} dB, swing {best[3]:.1f} dB" + ("" if (best[2] > SUSTAIN_FLOOR_DB and best[3] <= SWING_MAX_DB) else ", NOT sustained: no better stretch") + ")") if best else "no stretch found; fell back to the whole-edit offset"})
    cues[-1]["fade_out"] = mc["fade_out_s"]
    return cues


def cue_sheet(pk, mc, prof):
    long = prof["long"]
    return {"note": f"written by music_pick.py: {pk['title']} (score {pk['score']}); bed {mc['bed_lu_under_voice']} LU under his voice, stem vs stem (apply mixes it exactly; score.py's db is vs speech RMS, so use `music_pick.py apply`)",
            "duck_db": DUCK_DB["long" if long else "reel"], "ceiling_db": -6, "swells": [], "dips": [[p["t0"], p["t1"]] for p in prof["punch_lines"]],
            "cues": [{"track": c["track"], "t0": c["t0"], "t1": c["t1"], "start": c["start"], "db": -mc["bed_lu_under_voice"], "fade_in": c["fade_in"], "fade_out": c["fade_out"], "loop": c["loop"]} for c in pk["cues"]],
            "OB_MUSIC": pk["file"]}


# ---------------------------------------------------------------- mixing (apply, previews)
SR = 48000


def read_voice(path):
    v = BI.decode(path, SR, 1)
    return v


def load_track(path, start, length):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{max(0.0, start):.3f}", "-i", path, "-t", f"{length:.3f}", "-af",
                          "equalizer=f=2500:t=q:w=1.0:g=-3,lowshelf=f=150:g=-2", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def cue_audio(c, n):
    """n samples of the cue's track from c['start'], looping with a 1.5 s crossfade when the track runs out."""
    need = n / SR
    x = load_track(c["track"], c["start"], need + 0.2)
    if len(x) >= n:
        return x[:n]
    full = load_track(c["track"], 0.0, 1e4); xf = int(1.5 * SR); out = x
    while len(out) < n:
        nxt = full[: max(xf * 3, len(full))]
        a = np.linspace(1, 0, xf)[:, None]
        out = np.concatenate([out[:-xf], out[-xf:] * a + nxt[:xf] * (1 - a), nxt[xf:]])
    return out[:n]


def duck_env(voice, hold, release, depth_db):
    """gain per sample: down `depth_db` while the voice is active, held `hold` s after it stops, released over `release` s."""
    hop = int(SR * 0.02); n = len(voice) // hop + 1
    v = np.pad(voice, (0, n * hop - len(voice)))
    lev = 10 * np.log10((v.reshape(n, hop) ** 2).mean(1) + 1e-12)
    act = (lev > -42).astype(float)
    env = np.zeros(n); a_up = 1 - np.exp(-0.02 / 0.08); a_dn = 1 - np.exp(-0.02 / max(release / 3, 0.02)); held = 0
    for i in range(n):
        prev = env[i - 1] if i else 0.0
        if act[i] > 0:
            held = int(hold / 0.02)
        tgt = 1.0 if (act[i] > 0 or held > 0) else 0.0
        held = max(0, held - 1)
        env[i] = prev + ((a_up if tgt > prev else a_dn) * (tgt - prev))
    return np.repeat(10 ** (-depth_db * env / 20), hop)[: len(voice)]


def punch_env(n, punches, drop_db):
    g = np.ones(n); r = int(0.03 * SR)
    for a, b in punches:
        i0, i1 = max(0, int(a * SR) - r), min(n, int(b * SR))
        if i1 <= i0:
            continue
        gd = 10 ** (-drop_db / 20)
        g[i0:i1] = np.minimum(g[i0:i1], gd)
        ramp_dn = np.linspace(1, gd, r)[: max(0, min(r, i1 - i0))]
        g[i0:i0 + len(ramp_dn)] = np.minimum(g[i0:i0 + len(ramp_dn)], ramp_dn)
        j1 = min(n, i1 + r)
        g[i1:j1] = np.minimum(g[i1:j1], np.linspace(gd, 1, j1 - i1))
    return g


def build_bed(voice, cues, punches, mc, long, t_off=0.0):
    """stereo bed (n,2) for `voice` (mono, SR), the exact config level per cue (LU stem vs stem), returns (bed, per_cue_report)."""
    n = len(voice); bed = np.zeros((n, 2)); rep = []
    duck = duck_env(voice, mc["duck_hold_s"], mc["duck_release_s"], DUCK_DB["long" if long else "reel"])
    pe = punch_env(n, [(a - t_off, b - t_off) for a, b in punches], mc["punch_drop_db"] * 3)
    target = mc["bed_lu_under_voice"]
    for c in cues:
        i0 = max(0, int((c["t0"] - t_off) * SR)); i1 = min(n, int((c["t1"] - t_off) * SR))
        if i1 - i0 < SR // 2:
            continue
        x = cue_audio(c, i1 - i0)
        fi, fo = int(c["fade_in"] * SR), int(c["fade_out"] * SR)
        env = np.ones(i1 - i0); env[:fi] = np.linspace(0, 1, min(fi, len(env))) if fi else env[:0]
        if fo:
            env[-fo:] = np.minimum(env[-fo:], np.linspace(1, 0, min(fo, len(env))))
        seg = x * (env * duck[i0:i1] * pe[i0:i1])[:, None]
        lv, lb = BI.lufs(voice[i0:i1]), BI.lufs(seg)
        g = 10 ** ((lv - target - lb) / 20) if lb > -100 else 1.0
        bed[i0:i1] += seg * g
        rep.append({"t0": c["t0"], "t1": c["t1"], "voice_lufs": round(lv, 2), "bed_lufs": round(lb + 20 * np.log10(g), 2), "lu_under": round(lv - (lb + 20 * np.log10(g)), 2)})
    return bed, rep


def write_wav(path, x, ch):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(ch), "-i", "-", "-c:a", "pcm_s24le", path],
                   input=x.astype(np.float32).tobytes(), check=True)


def find_voice(work, given):
    if given:
        return BI.xp(given)
    for c in ("audio/voice.wav", "story/edit_voice.wav", "audio/edit_voice.wav", "master_synced.wav", "out.wav"):
        if os.path.exists(f"{work}/{c}"):
            return f"{work}/{c}"
    raise SystemExit("music_pick: no voice stem found in WORK (audio/voice.wav, story/edit_voice.wav, master_synced.wav). Pass --voice VOICE.wav (his voice only, mono or stereo).")


def previews(work, out, prof, mc, voice, top):
    d = f"{work}/audio/previews"; os.makedirs(d, exist_ok=True); made = []
    n = min(len(voice), 30 * SR); v = voice[:n]
    for c in out["candidates"][:top]:
        e_cue = [{"track": c["file"], "t0": 0.0, "t1": n / SR, "start": c["offset_s"], "fade_in": 0.3, "fade_out": 0.8, "loop": True}]
        bed, rep = build_bed(v, e_cue, [(p["t0"], p["t1"]) for p in prof["punch_lines"] if p["t1"] < 30], mc, prof["long"])
        mix = np.stack([v, v], 1) * 1.0 + bed
        pk = np.abs(mix).max()
        if pk > 0.98:
            mix *= 0.98 / pk
        m4a = f"{d}/{c['rank']:02d}_{re.sub('[^A-Za-z0-9]+', '-', c['title'])[:30]}.m4a"
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "aac", "-b:a", "160k", m4a],
                       input=mix.astype(np.float32).tobytes(), check=True)
        made.append(m4a)
    return made


def apply(work, route, voice_path, pick_n=None):
    work = BI.xp(work); cj = jload(f"{work}/audio/music_candidates.json")
    if not cj or not cj.get("pick"):
        raise SystemExit(f"music_pick apply: {work}/audio/music_candidates.json has no pick: run `music_pick.py {work} --route ROUTE` first")
    pk = cj["pick"]; prof = jload(f"{work}/audio/edit_profile.json"); cfg = BI.load_cfg(route or cj["route"]); mc = cfg["music"]
    if pick_n:
        c = next(c for c in cj["candidates"] if c["rank"] == int(pick_n)); idx = BI.load_index(cfg)
        pk = {"sha256": c["sha256"], "file": c["file"], "title": c["title"], "cues": make_cues(c, idx["music"][c["sha256"]], prof, mc)}
    voice = read_voice(find_voice(work, voice_path))
    bed, rep = build_bed(voice, pk["cues"], [(p["t0"], p["t1"]) for p in prof["punch_lines"]], mc, prof["long"])
    write_wav(f"{work}/audio/voice.wav", voice, 1); write_wav(f"{work}/audio/bed.wav", bed, 2)
    sfxp = f"{work}/story/sfx_plan.json"
    man = {"voice": f"{work}/audio/voice.wav", "bed": f"{work}/audio/bed.wav", "sfx": sfxp if os.path.exists(sfxp) else None,
           "music": [{"file": c["track"], "sha256": c["sha256"], "start": c["t0"], "offset": c["start"]} for c in pk["cues"]],
           "declared": {"music": True, "sfx": os.path.exists(sfxp)}, "bed_lu_target": mc["bed_lu_under_voice"], "measured": rep,
           "punch_lines": [[p["t0"], p["t1"]] for p in prof["punch_lines"]], "made": datetime.datetime.now().isoformat(timespec="seconds")}
    old = jload(f"{work}/audio/manifest.json")
    if old and old.get("sfx") and not man["sfx"]:
        man["sfx"] = old["sfx"]; man["declared"]["sfx"] = True
    json.dump(man, open(f"{work}/audio/manifest.json", "w"), indent=1)
    print(f"apply: wrote {work}/audio/voice.wav, bed.wav, manifest.json; bed {', '.join(str(r['lu_under']) for r in rep[:6])} LU under his voice (target {mc['bed_lu_under_voice']})")
    return man


def use(work):
    work = BI.xp(work); cj = jload(f"{work}/audio/music_candidates.json")
    if not cj or not cj.get("pick"):
        raise SystemExit("music_pick use: no pick recorded in WORK/audio/music_candidates.json")
    p = f"{ED}/qc/music_usage.json"; u = jload(p, {"edits": []})
    shas = sorted({c["sha256"] for c in cj["pick"]["cues"]}); ed = edit_name(work)
    u["edits"] = [r for r in u["edits"] if r["edit"] != ed] + [{"edit": ed, "date": datetime.date.today().isoformat(), "format": cj["route"], "sha256": shas, "titles": [cj["pick"]["title"]]}]
    json.dump(u, open(p, "w"), indent=1); print(f"use: {ed} -> {cj['pick']['title']} recorded in {p}")


# ---------------------------------------------------------------- mix: voice + bed + planned sounds -> master -> onto the picture
def measure_tp(x):
    """true peak (dBTP) by 4x oversampling; x (n,) or (n,2)."""
    from scipy.signal import resample_poly
    return float(20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max() + 1e-12))


def mix(work, video, out=None, route=None):
    """voice.wav + bed.wav (from `apply`) + every hit of story/sfx_plan.json -> master (formats.json defaults.master) ->
    WORK/audio/final_mix.wav -> muxed onto VIDEO's picture (video copied) -> OUT; pieces carried over; manifest updated."""
    import sfx_check
    work, video = BI.xp(work), BI.xp(video)
    job = jload(f"{work}/job.json", {}) or {}
    route = route or job.get("route")
    if not route:
        raise SystemExit("music_pick mix: no route: WORK/job.json has none; pass --route ROUTE")
    cfg = BI.load_cfg(route); M = json.load(open(BI.FORMATS))["defaults"]["master"]
    out = BI.xp(out) if out else os.path.join(os.path.dirname(video), os.path.splitext(os.path.basename(video))[0] + "_mix" + os.path.splitext(video)[1])
    if out.startswith(BI.T7) or BI.xp(f"{work}/audio/final_mix.wav").startswith(BI.T7):
        raise SystemExit(f"music_pick mix: refusing to write under {BI.T7}; use a WORK/out path on the internal disk or OB-ARCHIVE")
    if not os.path.exists(video):
        raise SystemExit(f"music_pick mix: picture file not found: {video}")
    vp = f"{work}/audio/voice.wav"
    if not os.path.exists(vp):
        raise SystemExit(f"music_pick mix: no {vp}: write his voice stem there (or run `music_pick.py apply {work} --voice VOICE.wav`)")
    voice = BI.decode(vp, SR, 1); n = len(voice)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip() or 0)
    n = int(dur * SR) if dur else n
    voice = np.pad(voice, (0, max(0, n - len(voice))))[:n]
    mixd = np.stack([voice, voice], 1)
    bp = f"{work}/audio/bed.wav"; have_bed = os.path.exists(bp)
    if have_bed:
        bed = BI.decode(bp, SR, 2); mixd += np.pad(bed, ((0, max(0, n - len(bed))), (0, 0)))[:n]
    elif cfg["music_need"] == "bed":
        print(f"WARNING: route {route} needs a music bed but {bp} is missing: mixing voice and sounds only (run music_pick.py apply)")
    sp = f"{work}/story/sfx_plan.json"; hits = (jload(sp, {}) or {}).get("hits", []) if os.path.exists(sp) else []
    sp_db = sfx_check.speech_db(voice, SR) if hits else 0.0; placed = 0
    for h in hits:
        if not os.path.exists(h["file"]):
            raise SystemExit(f"music_pick mix: planned sound missing: {h['file']}")
        x = BI.decode(h["file"], SR, 1)
        g = 10 ** ((sp_db + float(h["db"]) - sfx_check.peak100(x, SR)) / 20); i0 = int(round(float(h["t"]) * SR))
        a = max(0, -i0); i0 = max(0, i0); seg = x[a:a + max(0, n - i0)] * g
        mixd[i0:i0 + len(seg)] += seg[:, None]; placed += 1
    pre = f"{work}/audio/premaster.wav"; write_wav(pre, mixd, 2)
    T, TP = M["lufs"], M["true_peak_max"]
    TPm = TP - 0.5   # 2026-11-11 (C4465 fix): the AAC 256k encode below adds about 0.3 dB of true peak (a -1.0 dBTP master measured -0.7
                     # in the delivered file and the gate FAILed it), so the master leaves 0.5 dB of headroom under the route's maximum
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", pre, "-af", f"loudnorm=I={T}:TP={TPm}:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    fm = f"{work}/audio/final_mix.wav"
    ln = (f"loudnorm=I={T}:TP={TPm}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", pre, "-af", ln, "-ar", str(SR), "-c:a", "pcm_s24le", fm], check=True)
    fin = BI.decode(fm, SR, 2); L, tp = BI.lufs(fin), measure_tp(fin)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for enc in ("aac_at", "aac"):
        rc = subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", video, "-i", fm, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", enc, "-b:a", "256k", "-ar", str(SR),
                             "-movflags", "+faststart", "-t", f"{dur:.3f}", out], capture_output=True)
        if rc.returncode == 0:
            break
    else:
        raise SystemExit("music_pick mix: ffmpeg mux failed: " + rc.stderr.decode()[-300:])
    pieces = False
    try:
        import qc_gate
        if os.path.exists(qc_gate.pieces_path(video)):
            qc_gate.copy_pieces(video, out); pieces = True
    except Exception as ex:
        print(f"WARNING: recorded pieces not carried over ({ex}); record them: ob_job.py pieces WORK {out} SEGS.json")
    man = jload(f"{work}/audio/manifest.json", {}) or {}
    man.setdefault("music", []); man.setdefault("declared", {})
    man["declared"].update(music=bool(have_bed and man["music"]), sfx=bool(hits)); man["sfx"] = sp if hits else man.get("sfx")
    man.update(final_mix=fm, mix_out=out, mix_lufs=round(L, 2), mix_true_peak=round(tp, 2), mixed_from=video)
    json.dump(man, open(f"{work}/audio/manifest.json", "w"), indent=1)
    print(f"mix: voice + {'bed' if have_bed else 'no bed'} + {placed} sounds -> {fm}: {L:.1f} LUFS (target {T} +/- {M['lufs_tol']}), true peak {tp:.1f} dBTP (max {TP}); picture copied; pieces {'carried over' if pieces else 'none to carry'}")
    print(f"wrote {out}\nnext: python3 -I {ED}/bin/ob_job.py gate {work} {out}")
    return out


def mix_selftest():
    ok = True
    def chk(name, cond, detail=""):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    wk = os.path.expanduser("~/ob-scratch/skill-rebuild/WP2/mix_selftest"); os.makedirs(f"{wk}/audio", exist_ok=True); os.makedirs(f"{wk}/story", exist_ok=True)
    vid = f"{wk}/pic.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=30:duration=8", "-c:v", "libx264", "-pix_fmt", "yuv420p", vid], check=True)
    t = np.arange(SR * 8) / SR
    voice = 0.2 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 2 * t) > -0.3)
    bed = np.stack([0.2 * np.sin(2 * np.pi * 330 * t)] * 2, 1) * 0.02
    write_wav(f"{wk}/audio/voice.wav", voice, 1); write_wav(f"{wk}/audio/bed.wav", bed, 2)
    click = 0.9 * np.sin(2 * np.pi * 1500 * np.arange(int(0.2 * SR)) / SR) * np.hanning(int(0.2 * SR)); write_wav(f"{wk}/click.wav", click, 1)
    json.dump({"hits": [{"t": 5.0, "file": f"{wk}/click.wav", "db": -12}]}, open(f"{wk}/story/sfx_plan.json", "w"))
    json.dump({"music": [{"file": "x", "sha256": "0", "start": 0, "offset": 0}], "declared": {"music": False, "sfx": False}}, open(f"{wk}/audio/manifest.json", "w"))
    out = mix(wk, vid, route="reel-talking")
    M = json.load(open(BI.FORMATS))["defaults"]["master"]
    fin = BI.decode(f"{wk}/audio/final_mix.wav", SR, 2)
    chk("master loudness inside formats.json tolerance", abs(BI.lufs(fin) - M["lufs"]) <= M["lufs_tol"], f"{BI.lufs(fin):.1f} LUFS")
    chk("true peak at or under the route maximum", measure_tp(fin) <= M["true_peak_max"] + 0.05, f"{measure_tp(fin):.2f} dBTP")
    pr = lambda f, k: subprocess.run(["ffprobe", "-v", "error", "-select_streams", k, "-show_entries", "stream=codec_name,nb_frames", "-of", "csv=p=0", f], capture_output=True, text=True).stdout.split()
    a, b = pr(vid, "v:0"), pr(out, "v:0")
    chk("picture stream copied, not re-encoded (same codec and frame count)", a and a == b, f"{a} vs {b}")
    chk("output carries AAC audio", "aac" in "".join(pr(out, "a:0")))
    seg = lambda x, t0: float(np.sqrt((x[int(t0 * SR):int((t0 + 0.2) * SR)] ** 2).mean()))
    chk("the planned sound is in the mix on its frame (louder at 5.0 s than at 6.2 s)", seg(fin, 5.0) > 1.2 * seg(fin, 6.2), f"{seg(fin, 5.0):.4f}")
    man = json.load(open(f"{wk}/audio/manifest.json"))
    chk("manifest declares music and sounds after the mix", man["declared"]["music"] and man["declared"]["sfx"] and man["mix_out"] == out)
    try:
        mix(wk, vid.replace(wk, BI.T7 + "/x"), out=f"{BI.T7}/x_mix.mp4", route="reel-talking"); chk("refuses to write under the T7", False)
    except SystemExit as ex:
        chk("refuses to write under the T7", "T7" in str(ex))
    return ok


# ---------------------------------------------------------------- selftest
def selftest():
    work = os.path.expanduser("~/ob-scratch/skill-rebuild/WP2/music_selftest"); os.makedirs(f"{work}/audio", exist_ok=True)
    ok = True
    def chk(name, cond, detail=""):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    cfg = BI.load_cfg("long-form"); rcfg = BI.load_cfg("reel-talking")
    def wavtrack(name, f, secs=40):
        t = np.arange(int(SR * secs)) / SR
        x = 0.2 * np.sin(2 * np.pi * f * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
        p = f"{work}/{name}.wav"; write_wav(p, x, 1); return p
    beats = [round(0.5 * i, 3) for i in range(80)]
    def ent(i, title, lane="youtube-safe", mode="major", tone=2.5, **kw):
        e = {"sha256": f"{i:064x}", "title": title, "lane": lane, "licence": "test", "ai_label_checked": "2026-11-07", "content_id_checked": "2026-11-07", "banned_for": {},
             "paths": [wavtrack(f"t{i}", 220 + 40 * i)], "duration_s": 40.0, "bpm_1x": 120.0, "bpm_2x": 240.0, "bpm_conf": 0.8, "beats": beats, "key": "C", "mode": mode,
             "mode_margin": 0.2, "energy_2s_db": [-20 + (i % 3) for _ in range(20)], "sections_s": [10.0, 20.0, 30.0], "share_1_4k": 0.3, "lra_lu": 3.0, "vocals": False, "vocal_p": 0.0,
             "mood_all": {UPT: tone, DNT: 0.0}, "used_in": [], "ob_verdict": []}
        e.update(kw); return e
    UPT, DNT = BI.UP[0], BI.DOWN[0]
    idx = {"music": {}, "sfx": {}}
    for i, (ti, kw) in enumerate([("Good A", {}), ("Good B", {}), ("Good C", {}), ("Good D", {}), ("Minor Gloom", {"mode": "minor", "tone": 0.3}), ("Sad Tone", {"tone": -3.0}),
                                  ("Viral Song", {"lane": "viral"}), ("Banned", {"banned_for": {"all": "AI generated"}}), ("Recent", {}), ("No Dates", {"content_id_checked": None})]):
        e = ent(i + 1, ti, **kw); idx["music"][e["sha256"]] = e
    recent_sha = f"{9:064x}"
    usage = {"edits": [{"edit": "C0001", "sha256": [recent_sha]}]}
    # synthetic WORK: 60 s edit with events every 2 s (on the beat grid) and a cut list
    wk = f"{work}/WORK"; os.makedirs(wk, exist_ok=True)
    json.dump({"events": [{"id": f"E{i}", "type": "pills", "chunks": [["x", "c0", "x"]], "edit_in": 2.0 * i, "edit_out": 2.0 * i + 1} for i in range(1, 25)]}, open(f"{wk}/events_resolved.json", "w"))
    json.dump({"segments": [{"src_in": 0, "src_out": 60, "edit_in": 0.0, "edit_out": 60.0}]}, open(f"{wk}/cutlist.json", "w"))
    out, prof = pick(wk, "reel-talking", idx, {}, usage, dur=60.0, cfg=rcfg, write=True)
    names = [c["title"] for c in out["candidates"]]
    chk("returns at least min_candidates candidates", out["n_candidates"] >= out["min_candidates"] and not out["bank_short"], f"{out['n_candidates']} candidates")
    rj = {r["title"]: r["reason"] for r in out["rejects"]}
    chk("minor key rejected for an educational reel", "Minor Gloom" in rj and "minor" in rj["Minor Gloom"], rj.get("Minor Gloom", ""))
    chk("gloomy tone rejected", "Sad Tone" in rj)
    chk("banned track rejected", "Banned" in rj)
    chk("track used in the last edits rejected", "Recent" in rj and "last" in rj["Recent"], rj.get("Recent", ""))
    chk("youtube-safe style track with no Content ID date still fine on a reel (lane check is route-based)", "No Dates" in names or "No Dates" in rj)
    chk("a viral song is allowed on a reel", "Viral Song" in names or "Viral Song" in rj)
    lo, _ = pick(wk, "long-form", idx, {}, usage, dur=60.0, cfg=cfg, write=False)
    lr = {r["title"]: r["reason"] for r in lo["rejects"]}
    chk("long form rejects the viral song and the undated track", "Viral Song" in lr and "No Dates" in lr, f"{lr.get('Viral Song', '')[:50]} | {lr.get('No Dates', '')[:40]}")
    small = {"music": {k: v for k, v in list(idx["music"].items())[:2]}, "sfx": {}}
    so, _ = pick(wk, "long-form", small, {}, {"edits": []}, dur=60.0, cfg=cfg, write=False)
    chk("fewer than min_candidates sets bank_short with a note", so["bank_short"] and "bank needs new tracks" in so["bank_short_note"], so.get("bank_short_note", "")[:60])
    chk("every candidate carries scores and a plain-words reason", all(c["reason"] and len(c["parts"]) == 5 for c in out["candidates"]))
    chk("the pick is the top score or has a written reason", out["pick"]["is_top_score"] or out["pick"]["written_reason"])
    # viral margin: make the viral song score slightly below the best -> it wins
    v = {k: json.loads(json.dumps(e)) for k, e in idx["music"].items()}
    vo, _ = pick(wk, "reel-talking", idx, {}, usage, dur=60.0, cfg=rcfg, write=False)
    chk("viral-first margin recorded", "applied" in vo["viral_first"])
    # apply: stems at the config level
    voice = np.zeros(SR * 20); t = np.arange(len(voice)) / SR
    voice[:] = 0.15 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 3 * t) > -0.2)
    write_wav(f"{wk}/audio/voice.wav", voice, 1)
    prof["punch_lines"] = [{"t0": 8.0, "t1": 10.0}]
    pkc = out["pick"]["cues"][0]; pkc = dict(pkc, t1=20.0, fade_out=0.8)
    bed, rep = build_bed(voice, [pkc], [(8.0, 10.0)], rcfg["music"], False)
    diff = rep[0]["lu_under"]
    chk("bed sits at the config LU under the voice (stem vs stem)", abs(diff - rcfg["music"]["bed_lu_under_voice"]) <= rcfg["music"]["bed_tol_lu"], f"{diff} LU vs {rcfg['music']['bed_lu_under_voice']}")
    a = bed[int(8.3 * SR):int(9.7 * SR)]; b = bed[int(5.0 * SR):int(6.5 * SR)]
    drop = 10 * np.log10((b ** 2).mean() / ((a ** 2).mean() + 1e-20))
    chk("bed is dead under the marked punch line", drop >= rcfg["music"]["punch_drop_db"], f"{drop:.1f} dB down")
    tail = np.abs(bed[-int(0.05 * SR):]).max()
    chk("bed fades to silence by the last frame", tail < 1e-3, f"{tail:.5f}")
    ok &= mix_selftest()
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return 0
    if a[0] == "--selftest":
        return selftest()
    opt = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
    if a[0] == "apply" and len(a) > 1:
        apply(a[1], opt("--route"), opt("--voice"), opt("--pick")); return 0
    if a[0] == "mix" and len(a) > 2:
        mix(a[1], a[2], opt("--out"), opt("--route")); return 0
    if a[0] == "use" and len(a) > 1:
        use(a[1]); return 0
    work = a[0]; route = opt("--route")
    if not route:
        raise SystemExit("music_pick: --route ROUTE is required (routes in ~/ob-editor/qc/formats.json), e.g. --route long-form or --route reel-talking")
    cfg = BI.load_cfg(route)
    if cfg["music_need"] == "none":
        raise SystemExit(f"music_pick: route {route} has no music (formats.json music: none)")
    idx = BI.load_index(cfg); ep = BI.index_path(cfg).replace(".json", "_embeddings.npz")
    emb = {}
    if os.path.exists(ep):
        z = np.load(ep); emb = {k: z[k] for k in z.files}
    out, prof = pick(work, route, idx, emb, load_usage(), kind=opt("--kind"), dur=float(opt("--dur")) if opt("--dur") else None,
                     tone_words=opt("--tone", BI.load_cfg()["music"]["edu_tone"].split(";")[0]), top=int(opt("--top", 3)), cfg=cfg)
    print("read: " + "; ".join(prof["inputs_used"]))
    print(f"{out['n_candidates']} candidates scored ({len(out['rejects'])} rejected), min {out['min_candidates']}{'  BANK SHORT' if out['bank_short'] else ''}")
    for c in out["candidates"][:int(opt("--top", 3))]:
        print(f"  #{c['rank']} {c['score']:5.1f}  {c['title'][:30]:30} {c['lane']:12} off {c['offset_s']:5.1f}s  " + " ".join(f"{k}={v['points']}" for k, v in c["parts"].items()))
        print(f"        {c['reason']}")
    for r in out["rejects"][:8]:
        print(f"  reject {r['title'][:30]:30} {r['reason'][:100]}")
    if out["pick"]:
        print(f"PICK: {out['pick']['title']} (top score: {out['pick']['is_top_score']}) -> {out['pick']['delivery_note']}")
    if "--no-previews" not in a and out["candidates"]:
        try:
            voice = read_voice(find_voice(BI.xp(work), opt("--voice")))
            ps = previews(BI.xp(work), out, prof, cfg["music"], voice, int(opt("--top", 3)))
            print("previews: " + ", ".join(ps))
        except SystemExit as ex:
            print(f"previews skipped: {ex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
