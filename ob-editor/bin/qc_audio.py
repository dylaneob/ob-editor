#!/usr/bin/env python3
"""qc_audio: the gate checks that make the music and sound-effect decisions provable (called by qc_route.py / qc_gate.py).

Why (AUDIT-AUDIO sections 3 and 6): the old checks SKIPped when no plan or music was passed (the level-kit reels D, G, H and R1 shipped
code-made thuds at 15 a minute unseen), trusted path prefixes (a bank file copied to another drive WARNed; a renamed blocked track
passed), let "not heard clearly" sounds ship as WARNs, and nothing looked at whether a shortlist existed. OB 11-07: "You always go
so depressing", "You have a bank of so many choices", "use the sound effects from the bank first before making your own always".

  run(ctx) -> {check: (status, detail)}      ctx = dict(path, sha256, work, route, cfg, job, long, dur, segs, sfx_plan, music, report)
  record_problems(route, work, job) -> [str]  one line per missing/failed decision record (music_candidates.json, sfx_plan.json, manifest.json)
  python3 -I qc_audio.py FILE --route ROUTE --work WORK     run the checks on a file and print the table
  python3 -I qc_audio.py --selftest

Checks: bank (sha256 against ~/ob-editor/assets/bank_index.json), music_pick, bed_level, music_story, sfx_link, sfx_repeat, sfx_cap,
sfx_heard, audio_manifest. Every number comes from formats.json (defaults.music, defaults.sfx, the route's sfx_per_min, music, sfx).
A crash inside a check is returned as a FAIL row with the exception. A missing required input is a FAIL that names the command to run.
"""
import glob, json, os, sys, traceback
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank_index as BI   # noqa: E402

SR = 48000


def jload(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def _cfg(ctx):
    return BI.load_cfg(ctx.get("route"))


def _kind(ctx):
    k = (ctx.get("job") or {}).get("kind") if isinstance(ctx.get("job"), dict) else None
    r = ctx.get("route") or ""
    return k if k in BI.KINDS else ("reaction" if r == "reel-reaction" else "fdoe" if r == "reel-fdoe" else "educational")


def music_files(ctx):
    """tracks used: manifest music, else ctx['music'] / OB_MUSIC, else the newest story/score*.json cues."""
    w = ctx.get("work")
    man = jload(f"{w}/audio/manifest.json") if w else None
    if man and man.get("music"):
        return [m["file"] for m in man["music"]]
    m = ctx.get("music")
    if m:
        return [x for x in (list(m) if isinstance(m, (list, tuple)) else str(m).split(os.pathsep)) if x]
    if w:
        sheets = sorted(glob.glob(f"{w}/story/score*.json"), key=os.path.getmtime)
        if sheets:
            d = jload(sheets[-1], {}); cues = d.get("cues", []) if isinstance(d, dict) else d
            return [c["track"] for c in cues if isinstance(c, dict) and c.get("track")]
    return []


def sfx_hits(ctx):
    p = ctx.get("sfx_plan") or (f"{ctx['work']}/story/sfx_plan.json" if ctx.get("work") else None)
    if p and os.path.exists(p):
        return jload(p, {}).get("hits", []), p
    return [], p


def events_of(ctx):
    w = ctx.get("work"); out = {}
    if not w:
        return out
    ev = jload(f"{w}/events_resolved.json")
    if ev:
        for e in (ev.get("events", ev) if isinstance(ev, dict) else ev):
            if isinstance(e, dict) and e.get("edit_in") is not None:
                out[str(e.get("id"))] = float(e["edit_in"])
    for m in jload(f"{w}/plan/moments.json", []) or []:
        out[str(m.get("id"))] = float(m["t"])
    return out


# ---------------------------------------------------------------- the checks
def c_bank(ctx, cfg, idx):
    tracks = music_files(ctx); hits, plan = sfx_hits(ctx); kind = _kind(ctx)
    F, W = [], []
    for t in dict.fromkeys(tracks):
        if not os.path.exists(t):
            F.append(f"music file missing: {os.path.basename(t)}"); continue
        k, sha, e = BI.lookup_path(t, idx)
        if not e:
            F.append(f"{os.path.basename(t)}: not in the bank index (sha {sha[:10]}): index it first (bank_index.py build) after the page check")
        elif k != "music":
            F.append(f"{os.path.basename(t)} is a sound effect, used as music")
        else:
            why = BI.music_ineligible(e, cfg, kind)
            if why:
                F.append(f"{e['title']}: {why}")
    for h in hits:
        f = h.get("file")
        if not f:
            continue
        if not os.path.exists(f):
            F.append(f"sound file missing: {os.path.basename(f)}"); continue
        k, sha, e = BI.lookup_path(f, idx)
        if not e or k != "sfx":
            F.append(f"{os.path.basename(f)} at {h.get('t')}: not in the bank index (sha {sha[:10]}): index it first")
        elif e.get("code_made"):
            (W if h.get("bank_miss") else F).append(f"made-in-code sound {os.path.basename(f)} at {h.get('t')}" + (f" (bank searched: {str(h['bank_miss'])[:60]})" if h.get("bank_miss") else ": the bank first (M59), or say what was searched in bank_miss"))
        elif e.get("banned_family"):
            F.append(f"{os.path.basename(f)} at {h.get('t')}: banned family '{e['banned_family']}' (OB 11-06 'I also hated that sound effect you used')")
    if not tracks and not hits:
        return ("PASS", "no music and no sound effects in this file (audio_manifest decides whether the route allows that)")
    head = f"{len(set(tracks))} tracks, {len(hits)} sounds"
    if F:
        return ("FAIL", head + "; " + " | ".join(F[:4]) + (f" (+{len(F) - 4} more)" if len(F) > 4 else ""))
    if W:
        return ("WARN", head + "; " + " | ".join(W[:4]))
    return ("PASS", head + ", all in the bank by hash" + ("; lanes fit the route" if tracks else ""))


def c_music_pick(ctx, cfg, idx):
    mc = cfg["music"]; need = cfg["music_need"]; tracks = music_files(ctx)
    if need == "none":
        return ("PASS", "route has no music") if not tracks else ("FAIL", "this route has no music but the mix uses " + os.path.basename(tracks[0]))
    if not tracks and need != "bed":
        return ("PASS", "music optional on this route and none used")
    cj = jload(f"{ctx['work']}/audio/music_candidates.json") if ctx.get("work") else None
    if not cj:
        return ("FAIL", f"no WORK/audio/music_candidates.json: run `music_pick.py WORK --route {ctx.get('route')}` and use its pick (a track chosen without a scored shortlist is the default-track trap)")
    F = []
    if cj.get("n_candidates", len(cj.get("candidates", []))) < mc["min_candidates"] and not cj.get("bank_short"):
        F.append(f"only {cj.get('n_candidates')} candidates scored (need {mc['min_candidates']}) and bank_short is not declared")
    pk = cj.get("pick")
    if not pk:
        F.append("the record has no pick")
    else:
        if not pk.get("is_top_score") and not pk.get("written_reason"):
            F.append("the pick is not the top score and has no written reason")
        used = {os.path.realpath(t) for t in tracks}
        shas = set()
        for t in tracks:
            if os.path.exists(t):
                shas.add(BI.sha256_file(t))
        picked = {c.get("sha256") for c in pk.get("cues", [])} | {pk.get("sha256")}
        if shas and not (shas & picked):
            F.append("the music in the mix is not the track music_pick.py picked (" + pk.get("title", "?") + ")")
        u = jload(f"{BI.ED}/qc/music_usage.json", {"edits": []})
        edit = cj.get("edit")
        rows = [r for r in u.get("edits", []) if r.get("edit") != edit][-mc["no_reuse_last_edits"]:]
        reused = [r["edit"] for r in rows if shas & set(r.get("sha256", []))]
        if reused:
            F.append(f"the track was used in {', '.join(reused)} (one of the last {mc['no_reuse_last_edits']} edits)")
    if F:
        return ("FAIL", "; ".join(F))
    short = " BANK SHORT: the delivery note must say the bank needs new tracks." if cj.get("bank_short") else ""
    return ("PASS" if not short else "WARN", f"{cj.get('n_candidates')} candidates scored, pick '{pk['title']}'" + (" is the top score" if pk.get("is_top_score") else f" by written reason: {pk.get('written_reason')}") + "." + short)


def _stems(ctx):
    man = jload(f"{ctx['work']}/audio/manifest.json") if ctx.get("work") else None
    if not man or not man.get("voice") or not man.get("bed") or not os.path.exists(man["voice"]) or not os.path.exists(man["bed"]):
        return None, man
    return man, man


def c_bed_level(ctx, cfg, idx):
    mc = cfg["music"]
    if cfg["music_need"] == "none" or (cfg["music_need"] == "optional" and not music_files(ctx)):
        return ("PASS", "no music bed on this route / file")
    man, _ = _stems(ctx)
    if not man:
        return ("FAIL", "no voice and bed stems in WORK/audio/manifest.json: run `music_pick.py apply WORK` (it writes voice.wav, bed.wav and the manifest) so the level can be measured stem against stem")
    v = BI.decode(man["voice"], SR, 1); b = BI.decode(man["bed"], SR, 2)
    n = min(len(v), len(b)); v, b = v[:n], b[:n]
    segs = []
    if ctx.get("long") and man.get("music") and len(man["music"]) > 1:
        cues = man["music"]
        for i, c in enumerate(cues):
            t0 = float(c["start"]); t1 = float(cues[i + 1]["start"]) if i + 1 < len(cues) else n / SR
            segs.append((t0, t1))
    else:
        segs = [(0.0, n / SR)]
    rows, bad = [], []
    for t0, t1 in segs:
        i0, i1 = int(t0 * SR), int(t1 * SR)
        if i1 - i0 < SR:
            continue
        d = BI.lufs(v[i0:i1]) - BI.lufs(b[i0:i1]); rows.append(round(d, 1))
        if abs(d - mc["bed_lu_under_voice"]) > mc["bed_tol_lu"]:
            bad.append(f"{t0:.0f}-{t1:.0f} s: {d:.1f} LU under his voice")
    if not rows:
        return ("FAIL", "stems too short to measure")
    if bad:
        return ("FAIL", f"bed must sit {mc['bed_lu_under_voice']} +/- {mc['bed_tol_lu']} LU under his voice (stem vs stem); " + " | ".join(bad[:4]) + ": re-run `music_pick.py apply WORK`")
    return ("PASS", f"bed {', '.join(map(str, rows[:6]))} LU under his voice (target {mc['bed_lu_under_voice']} +/- {mc['bed_tol_lu']})")


def c_music_story(ctx, cfg, idx):
    mc = cfg["music"]
    if cfg["music_need"] == "none" or (cfg["music_need"] == "optional" and not music_files(ctx)):
        return ("PASS", "no music bed")
    w = ctx.get("work"); prof = jload(f"{w}/audio/edit_profile.json") if w else None
    man, _ = _stems(ctx)
    if not man or not prof:
        return ("FAIL", "no edit_profile.json / stems: run `music_pick.py WORK --route ROUTE` then `music_pick.py apply WORK`")
    F, notes = [], []
    if ctx.get("long"):
        chapters = [s["t0"] for s in prof.get("sections", []) if s.get("name", "").startswith("ch")]
        cues = [float(c["start"]) for c in man.get("music", [])]
        for ct in chapters:
            if not cues or min(abs(ct - c) for c in cues) > 0.5:
                F.append(f"no music cue within 0.5 s of the chapter card at {ct:.1f} s")
        notes.append(f"{len(chapters)} chapter cards, {len(cues)} cues")
    b = BI.decode(man["bed"], SR, 2).mean(1)
    for p in prof.get("punch_lines", []):
        a, e = float(p["t0"]), float(p["t1"])
        if e - a < 0.3 or e * SR > len(b):
            continue
        inside = 10 * np.log10((b[int(a * SR):int(e * SR)] ** 2).mean() + 1e-12)
        before = 10 * np.log10((b[max(0, int((a - 2.0) * SR)):int((a - 0.2) * SR)] ** 2).mean() + 1e-12)
        if before - inside < mc["punch_drop_db"]:
            F.append(f"punch line {a:.1f}-{e:.1f} s: bed only {before - inside:.1f} dB down (needs {mc['punch_drop_db']})")
        elif inside > mc["punch_floor_db"]:
            F.append(f"punch line {a:.1f}-{e:.1f} s: bed at {inside:.1f} dB, above the {mc['punch_floor_db']} dB floor")
    notes.append(f"{len(prof.get('punch_lines', []))} punch lines marked")
    return ("FAIL", "; ".join(F[:4])) if F else ("PASS", "; ".join(notes) + ": cues on the chapters, bed dead under the punch lines")


def c_sfx_link(ctx, cfg, idx):
    hits, plan = sfx_hits(ctx); sc = cfg["sfx"]
    if not hits:
        return ("PASS", "no sound effects planned") if cfg["sfx_need"] != "plan" else ("FAIL", f"route {ctx.get('route')} needs a sound-effect plan: run `sfx_pick.py WORK --route {ctx.get('route')}`")
    ev = events_of(ctx)
    if not ev:
        return ("FAIL", "no events_resolved.json or plan/moments.json in WORK to link the sounds to")
    F = []
    for h in hits:
        where = f"hit at {h.get('t')}"
        if not h.get("event") or str(h["event"]) not in ev:
            F.append(f"{where}: event '{h.get('event')}' is not an on-screen event"); continue
        if not (h.get("object_line") or "").strip():
            F.append(f"{where}: no object_line (what the thing on screen is and does)")
        if len(h.get("runner_ups") or []) < sc["min_runner_ups"] and not h.get("bank_miss"):
            F.append(f"{where}: {len(h.get('runner_ups') or [])} runner-ups (need {sc['min_runner_ups']}) or a bank_miss")
        peak = float(h["t"]) + float(h.get("lead_s", 0.0)); d = (peak - ev[str(h["event"])]) * 1000
        if d < -sc["sync_early_ms"] or d > sc["sync_late_ms"]:
            F.append(f"{where}: its loudest moment lands {d:+.0f} ms from event {h['event']} (window -{sc['sync_early_ms']}/+{sc['sync_late_ms']} ms)")
    return ("FAIL", f"{len(hits)} hits; " + " | ".join(F[:4]) + (f" (+{len(F) - 4} more)" if len(F) > 4 else "")) if F else ("PASS", f"{len(hits)} hits, each on an existing event with an object line and runner-ups, loudest moment on the frame")


def _rec(h, idx):
    if h.get("recording_id"):
        return h["recording_id"]
    try:
        k, sha, e = BI.lookup_path(h["file"], idx)
        return e["recording_id"] if e else "file:" + os.path.realpath(h["file"])
    except Exception:
        return "file:" + str(h.get("file"))


def c_sfx_repeat(ctx, cfg, idx):
    hits, _ = sfx_hits(ctx); sc = cfg["sfx"]
    if not hits:
        return ("PASS", "no sound effects planned")
    mx = sc["repeat_max_long"] if ctx.get("long") else sc["repeat_max_reel"]
    hs = sorted(hits, key=lambda h: float(h["t"])); recs = [_rec(h, idx) for h in hs]; F = []
    counts = {}
    for r in recs:
        counts[r] = counts.get(r, 0) + 1
    for r, n in counts.items():
        if n > mx:
            F.append(f"one recording ({r}) used {n} times (max {mx}; pitch variants of one recording count together)")
    if not sc["back_to_back"]:
        for i in range(1, len(recs)):
            if recs[i] == recs[i - 1]:
                F.append(f"the same recording twice in a row at {float(hs[i - 1]['t']):.1f} and {float(hs[i]['t']):.1f} s")
    return ("FAIL", " | ".join(F[:4])) if F else ("PASS", f"{len(counts)} different recordings in {len(hits)} hits, none over {mx}, none back to back")


def c_sfx_cap(ctx, cfg, idx):
    hits, _ = sfx_hits(ctx); pm = cfg["sfx_per_min"]
    if not hits:
        return ("PASS", "no sound effects planned")
    if not pm or ctx.get("dur") in (None, 0):
        return ("FAIL", "no cap for this route in formats.json or no duration given to the check")
    rate = len(hits) / (float(ctx["dur"]) / 60)
    if rate > pm["fail"]:
        return ("FAIL", f"{rate:.1f} sounds a minute; fail line {pm['fail']} on {ctx.get('route')}")
    if rate > pm["cap"]:
        return ("WARN", f"{rate:.1f} sounds a minute; cap {pm['cap']} on {ctx.get('route')}")
    sc = cfg["sfx"]
    early = [h for h in hits if float(h["t"]) < sc["first_s_none"]]
    if early:
        return ("FAIL", f"a sound at {float(early[0]['t']):.2f} s (none in the first {sc['first_s_none']} s)")
    return ("PASS", f"{rate:.1f} a minute (cap {pm['cap']})")


def c_sfx_heard(ctx, cfg, idx):
    hits, _ = sfx_hits(ctx)
    if not hits:
        return ("PASS", "no sound effects planned")
    import sfx_check
    path = ctx.get("path")
    if not path or not os.path.exists(path):
        return ("FAIL", "no rendered file to listen to")
    F, W, rows = sfx_check.mix_check(path, hits, ctx.get("dur"))
    heard = [w for w in F + W if "not heard" in w]
    other = [f for f in F if "off its cue" in f or "louder than him" in f]
    bad = heard + other
    return ("FAIL", f"{len(bad)} planned sound(s) not found in the mix: " + " | ".join(bad[:3])) if bad else ("PASS", f"all {len(rows)} planned sounds found on their frame in the mix")


def c_audio_manifest(ctx, cfg, idx):
    man = jload(f"{ctx['work']}/audio/manifest.json") if ctx.get("work") else None
    tracks = music_files(ctx); hits, _ = sfx_hits(ctx)
    mn, sn = cfg["music_need"], cfg["sfx_need"]
    if not man:
        # only a route that needs a bed or a sound plan needs the manifest (same rule as record_problems below)
        if mn != "bed" and sn != "plan" and not tracks and not hits:
            return ("PASS", "route needs no music bed or sound plan and none were found")
        return ("FAIL", "no WORK/audio/manifest.json {voice, bed, sfx, music, declared}: `music_pick.py apply WORK` writes it; without it the gate cannot tell a missing bed from a silent one")
    d = man.get("declared") or {}
    F = []
    if mn == "bed" and not d.get("music"):
        F.append("this route needs a music bed but the manifest declares none")
    if sn == "plan" and not d.get("sfx"):
        F.append("this route needs a sound-effect plan but the manifest declares none")
    if mn == "none" and (d.get("music") or tracks):
        F.append("this route forbids music but music is declared/used")
    if sn == "none" and (d.get("sfx") or hits):
        F.append("this route forbids sound effects but they are declared/used")
    if (tracks and not d.get("music")) or (hits and not d.get("sfx")):
        F.append("music or sounds are in use but not declared in the manifest")
    return ("FAIL", "; ".join(F)) if F else ("PASS", f"declared music={bool(d.get('music'))} sfx={bool(d.get('sfx'))} matches route (music {mn}, sfx {sn})")


CHECKS = [("bank", c_bank), ("music_pick", c_music_pick), ("bed_level", c_bed_level), ("music_story", c_music_story), ("sfx_link", c_sfx_link),
          ("sfx_repeat", c_sfx_repeat), ("sfx_cap", c_sfx_cap), ("sfx_heard", c_sfx_heard), ("audio_manifest", c_audio_manifest)]


def run(ctx):
    out = {}
    if not ctx.get("route"):
        return {"audio_manifest": ("FAIL", "no route given to qc_audio: pass the job's route (formats.json routes) so the audio checks know what is required")}
    try:
        cfg = _cfg(ctx); idx = BI.load_index(cfg)
    except SystemExit as ex:
        return {n: ("FAIL", str(ex)) for n, _ in CHECKS}
    except Exception as ex:
        return {n: ("FAIL", f"cannot load config/index: {ex}") for n, _ in CHECKS}
    for name, fn in CHECKS:
        try:
            out[name] = fn(ctx, cfg, idx)
        except SystemExit as ex:
            out[name] = ("FAIL", str(ex))
        except Exception as ex:
            out[name] = ("FAIL", f"crashed: {type(ex).__name__}: {ex} ({traceback.format_exc().splitlines()[-3].strip()[:80]})")
    return out


def record_problems(route, work, job=None):
    """Decision records the route requires (formats.json route.records: music, sfx, audio_manifest). One line each, saying what to run."""
    cfg = BI.load_cfg(route); mc = cfg["music"]; P = []
    w = BI.xp(work)
    if cfg["music_need"] == "bed":
        cj = jload(f"{w}/audio/music_candidates.json")
        if not cj:
            P.append(f"music: no {w}/audio/music_candidates.json: run `music_pick.py {w} --route {route}`")
        else:
            if cj.get("n_candidates", 0) < mc["min_candidates"] and not cj.get("bank_short"):
                P.append(f"music: {cj.get('n_candidates')} candidates scored, need {mc['min_candidates']} (or bank_short)")
            pk = cj.get("pick")
            if not pk:
                P.append("music: music_candidates.json has no pick")
            elif not pk.get("is_top_score") and not pk.get("written_reason"):
                P.append("music: the pick is not the top score and has no written reason")
    if cfg["sfx_need"] == "plan":
        pl = jload(f"{w}/story/sfx_plan.json")
        if not pl:
            P.append(f"sfx: no {w}/story/sfx_plan.json: run `sfx_pick.py {w} --route {route}`")
        else:
            bad = [h for h in pl.get("hits", []) if not h.get("event") or not h.get("object_line") or (len(h.get("runner_ups") or []) < cfg["sfx"]["min_runner_ups"] and not h.get("bank_miss"))]
            if bad:
                P.append(f"sfx: {len(bad)} hit(s) lack an event, an object_line or {cfg['sfx']['min_runner_ups']} runner-ups (first at t={bad[0].get('t')})")
    if cfg["music_need"] in ("bed",) or cfg["sfx_need"] == "plan":
        if not os.path.exists(f"{w}/audio/manifest.json"):
            P.append(f"audio_manifest: no {w}/audio/manifest.json: run `music_pick.py apply {w}`")
    return P


# ---------------------------------------------------------------- selftest
def selftest():
    import shutil
    base = os.path.expanduser("~/ob-scratch/skill-rebuild/WP2/qc_selftest"); 
    os.makedirs(f"{base}/WORK/audio", exist_ok=True); os.makedirs(f"{base}/WORK/story", exist_ok=True); os.makedirs(f"{base}/WORK/plan", exist_ok=True)
    W = f"{base}/WORK"; ok = True
    def chk(name, got, want):
        nonlocal ok
        good = got[0] == want; ok &= good
        print(("PASS " if good else "FAIL ") + f"{name}: wanted {want}, got {got[0]}  ({got[1][:100]})")
    import music_pick as MP
    # real bank files: a clean youtube-safe track and sounds
    idx = BI.load_index()
    yt = next(e for e in idx["music"].values() if e["lane"] == "youtube-safe" and e["title"] == "Basketball Training")
    viral = next(e for e in idx["music"].values() if e["lane"] == "viral")
    tapis = next(e for e in idx["music"].values() if e["title"] == "Tapis")
    kit = next(e for e in idx["sfx"].values() if e["code_made"])
    good_sfx = [e for e in idx["sfx"].values() if not e["code_made"] and not e.get("banned_family") and e["pack"] == "openverse"][:4]
    glitch = next(e for e in idx["sfx"].values() if e.get("banned_family"))
    ytp = next(p for p in yt["paths"] if os.path.exists(p))
    renamed = f"{base}/renamed_innocent.mp3"; shutil.copy2(next(p for p in tapis["paths"] if os.path.exists(p)), renamed)
    copied = f"{base}/bank_copy_elsewhere.mp3"; shutil.copy2(ytp, copied)
    unknown = f"{base}/unknown.wav"; MP.write_wav(unknown, np.random.default_rng(1).normal(0, 0.05, SR * 2), 1)
    rt = "long-form"
    base_ctx = dict(path=None, work=W, route=rt, long=True, dur=240.0, job={"kind": "educational"}, sfx_plan=None)
    ev = {"events": [{"id": f"E{i}", "type": "plate", "edit_in": 10.0 + 20 * i, "edit_out": 12.0 + 20 * i} for i in range(6)]}
    json.dump(ev, open(f"{W}/events_resolved.json", "w"))
    mk = lambda e, i, **kw: dict({"t": 10.0 + 20 * i - float(e.get("loud10_s") or 0), "lead_s": float(e.get("loud10_s") or 0), "event": f"E{i}", "object_line": "a card slides in", "file": e["paths"][0], "recording_id": e["recording_id"],
                                  "runner_ups": [{"file": "x"}, {"file": "y"}], "db": -22}, **kw)
    def put_plan(hits):
        json.dump({"hits": hits}, open(f"{W}/story/sfx_plan.json", "w"))
    # bank
    chk("bank: a clean bank track in its own copy passes", c_bank(dict(base_ctx, music=[ytp]), BI.load_cfg(rt), idx), "PASS")
    chk("bank: a bank file copied anywhere still passes (by hash)", c_bank(dict(base_ctx, music=[copied]), BI.load_cfg(rt), idx), "PASS")
    chk("bank: a renamed blocked track (Tapis) FAILs", c_bank(dict(base_ctx, music=[renamed]), BI.load_cfg(rt), idx), "FAIL")
    chk("bank: an unknown file FAILs 'index it first'", c_bank(dict(base_ctx, music=[unknown]), BI.load_cfg(rt), idx), "FAIL")
    vp = next(p for p in viral["paths"] if os.path.exists(p))
    chk("bank: a viral song on long form FAILs (lane vs route)", c_bank(dict(base_ctx, music=[vp]), BI.load_cfg(rt), idx), "FAIL")
    chk("bank: a viral song on a reel passes", c_bank(dict(base_ctx, music=[vp], route="reel-talking", long=False), BI.load_cfg("reel-talking"), idx), "PASS")
    put_plan([mk(kit, 0)]); chk("bank: a code-made sound without bank_miss FAILs", c_bank(dict(base_ctx, music=None), BI.load_cfg(rt), idx), "FAIL")
    put_plan([mk(glitch, 0)]); chk("bank: a banned-family sound FAILs", c_bank(dict(base_ctx, music=None), BI.load_cfg(rt), idx), "FAIL")
    # sfx link / repeat / cap
    hs = [mk(e, i) for i, e in enumerate(good_sfx)]
    put_plan(hs); cfgl = BI.load_cfg(rt)
    chk("sfx_link: linked hits pass", c_sfx_link(base_ctx, cfgl, idx), "PASS")
    put_plan([dict(hs[0], event="NOPE")]); chk("sfx_link: an event that does not exist FAILs", c_sfx_link(base_ctx, cfgl, idx), "FAIL")
    put_plan([dict(hs[0], object_line="")]); chk("sfx_link: no object line FAILs", c_sfx_link(base_ctx, cfgl, idx), "FAIL")
    put_plan([dict(hs[0], runner_ups=[])]); chk("sfx_link: no runner-ups FAILs", c_sfx_link(base_ctx, cfgl, idx), "FAIL")
    put_plan([dict(hs[0], t=hs[0]["t"] + 0.2)]); chk("sfx_link: sound 200 ms off its event FAILs", c_sfx_link(base_ctx, cfgl, idx), "FAIL")
    put_plan(hs); chk("sfx_repeat: varied recordings pass", c_sfx_repeat(base_ctx, cfgl, idx), "PASS")
    put_plan([dict(hs[0], t=10.0 + 20 * i, event=f"E{i}") for i in range(2)]); chk("sfx_repeat: same recording back to back FAILs", c_sfx_repeat(base_ctx, cfgl, idx), "FAIL")
    put_plan([dict(hs[0], t=10.0 + 20 * i, event=f"E{i}") if i % 2 == 0 else dict(hs[1], t=10.0 + 20 * i, event=f"E{i}") for i in range(8)])
    chk("sfx_repeat: one recording over the cap FAILs", c_sfx_repeat(base_ctx, cfgl, idx), "FAIL")
    put_plan(hs); chk("sfx_cap: 4 sounds in 240 s pass", c_sfx_cap(base_ctx, cfgl, idx), "PASS")
    put_plan([dict(hs[i % 4], t=0.5 + i * 3.0) for i in range(30)]); chk("sfx_cap: 30 sounds in 240 s FAILs on long form", c_sfx_cap(base_ctx, cfgl, idx), "FAIL")
    # heard: build a 10 s file with sound 1 present at its cue and sound 2 absent
    s1 = good_sfx[0]; s2 = good_sfx[1]
    tt = np.arange(SR * 10) / SR
    x = np.zeros(SR * 10) + 0.2 * np.sin(2 * np.pi * 180 * tt) * ((np.sin(2 * np.pi * 3 * tt) > -0.2) & (tt > 5.0) & (tt < 6.5))
    snd = BI.decode(s1["paths"][0], SR, 1);
    mixp = f"{base}/mix.wav"; i0 = int(3.0 * SR); x[i0:i0 + len(snd)] += snd * 0.15; MP.write_wav(mixp, x, 1)
    put_plan([dict(mk(s1, 0), t=3.0, event="E0", lead_s=0.0), dict(mk(s2, 1), t=7.0, event="E1", lead_s=0.0, file=s2["paths"][0])])
    r = c_sfx_heard(dict(base_ctx, path=mixp, dur=10.0), cfgl, idx); chk("sfx_heard: a planned sound missing from the mix FAILs", r, "FAIL")
    put_plan([dict(mk(s1, 0), t=3.0, event="E0", lead_s=0.0)]); chk("sfx_heard: a present sound passes", c_sfx_heard(dict(base_ctx, path=mixp, dur=10.0), cfgl, idx), "PASS")
    # manifest
    for f in ("manifest.json",):
        if os.path.exists(f"{W}/audio/{f}"):
            os.replace(f"{W}/audio/{f}", f"{W}/audio/{f}.prev")
    chk("audio_manifest: route wants music and sfx, no manifest FAILs", c_audio_manifest(dict(base_ctx, music=None), cfgl, idx), "FAIL")
    json.dump({"declared": {"music": False, "sfx": False}}, open(f"{W}/audio/manifest.json", "w"))
    chk("audio_manifest: declared none where the route needs a bed FAILs", c_audio_manifest(dict(base_ctx, music=None), cfgl, idx), "FAIL")
    json.dump({"declared": {"music": True, "sfx": True}}, open(f"{W}/audio/manifest.json", "w")); put_plan(hs)
    chk("audio_manifest: declared music and sfx pass", c_audio_manifest(dict(base_ctx, music=[ytp]), cfgl, idx), "PASS")
    yc = BI.load_cfg("yt-clips"); chk("audio_manifest: yt-clips forbids music (declared one) FAILs", c_audio_manifest(dict(base_ctx, route="yt-clips", music=[ytp]), yc, idx), "FAIL")
    # bed level on synthetic stems
    t = np.arange(SR * 20) / SR; voice = 0.15 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 3 * t) > -0.2)
    mcfg = cfgl["music"]
    for name, db in (("good", mcfg["bed_lu_under_voice"]), ("loud", mcfg["bed_lu_under_voice"] - 10)):
        bed = np.stack([np.sin(2 * np.pi * 300 * t)] * 2, 1) * 0.1
        lv = BI.lufs(voice); lb = BI.lufs(bed); bed = bed * 10 ** ((lv - db - lb) / 20)
        MP.write_wav(f"{W}/audio/voice.wav", voice, 1); MP.write_wav(f"{W}/audio/bed.wav", bed, 2)
        json.dump({"voice": f"{W}/audio/voice.wav", "bed": f"{W}/audio/bed.wav", "music": [{"file": ytp, "start": 0.0, "offset": 0}], "declared": {"music": True, "sfx": True}}, open(f"{W}/audio/manifest.json", "w"))
        chk(f"bed_level: bed {db:.0f} LU under -> {'PASS' if name == 'good' else 'FAIL'}", c_bed_level(dict(base_ctx, long=False, music=[ytp]), cfgl, idx), "PASS" if name == "good" else "FAIL")
    # no stems
    json.dump({"declared": {"music": True, "sfx": True}}, open(f"{W}/audio/manifest.json", "w"))
    r = c_bed_level(dict(base_ctx, long=False, music=[ytp]), cfgl, idx); chk("bed_level: no stems FAILs and names music_pick.py apply", r if "music_pick.py apply" in r[1] else ("X", r[1]), "FAIL")
    # music_pick record
    cand = lambda **k: dict({"n_candidates": 3, "bank_short": False, "edit": "CTEST", "candidates": [], "pick": {"title": "Basketball Training", "is_top_score": True, "written_reason": None, "sha256": yt["sha256"], "cues": [{"sha256": yt["sha256"]}]}}, **k)
    json.dump({"edits": []}, open(f"{base}/usage_unused.json", "w"))
    json.dump(cand(), open(f"{W}/audio/music_candidates.json", "w")); chk("music_pick: 3 candidates, top pick passes", c_music_pick(dict(base_ctx, music=[ytp]), cfgl, idx), "PASS")
    json.dump(cand(n_candidates=1), open(f"{W}/audio/music_candidates.json", "w")); chk("music_pick: one candidate without bank_short FAILs", c_music_pick(dict(base_ctx, music=[ytp]), cfgl, idx), "FAIL")
    json.dump(cand(n_candidates=1, bank_short=True), open(f"{W}/audio/music_candidates.json", "w")); chk("music_pick: one candidate with bank_short only WARNs", c_music_pick(dict(base_ctx, music=[ytp]), cfgl, idx), "WARN")
    c3 = cand(); c3["pick"]["is_top_score"] = False; json.dump(c3, open(f"{W}/audio/music_candidates.json", "w")); chk("music_pick: pick not top and no reason FAILs", c_music_pick(dict(base_ctx, music=[ytp]), cfgl, idx), "FAIL")
    os.replace(f"{W}/audio/music_candidates.json", f"{W}/audio/music_candidates.json.prev")
    chk("music_pick: no record FAILs and names music_pick.py", c_music_pick(dict(base_ctx, music=[ytp]), cfgl, idx), "FAIL")
    # run(): the whole table, a crash is a FAIL row
    res = run(dict(base_ctx, music=[ytp], path=mixp)); print("run() rows:", {k: v[0] for k, v in res.items()})
    ok &= len(res) == len(CHECKS)
    probs = record_problems(rt, W + "_nowhere"); ok &= len(probs) >= 3; print("PASS record_problems lists missing records:" if len(probs) >= 3 else "FAIL record_problems", len(probs))
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return 0
    if a[0] == "--selftest":
        return selftest()
    opt = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
    route = opt("--route"); work = opt("--work"); cfg = BI.load_cfg(route) if route else {"long": False}
    ctx = dict(path=BI.xp(a[0]), work=BI.xp(work) if work else None, route=route, long=cfg["long"], dur=float(opt("--dur")) if opt("--dur") else None, job={}, sfx_plan=None, music=opt("--music"))
    if ctx["dur"] is None and ctx["path"] and os.path.exists(ctx["path"]):
        import subprocess
        ctx["dur"] = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ctx["path"]], capture_output=True, text=True).stdout.strip() or 0)
    res = run(ctx); worst = 0
    for k, (s, d) in res.items():
        print(f"{s:5} {k:15} {d}"); worst = max(worst, {"PASS": 0, "SKIP": 0, "WARN": 1, "FAIL": 2}[s])
    return 1 if worst == 2 else 0


if __name__ == "__main__":
    sys.exit(main())
