#!/usr/bin/env python3
"""sfx_pick: every sound effect is chosen for the thing on screen, from the bank, and tied to a visual event.

Why (OB): 10-16 "have different sound effects and make them a little quieter because it gets so repetitive"; 10-29 "use them when
needed dont be obxious about them"; 11-06 "I also hated that sound effect you used"; 11-07 "sound effects use the sound effects from
the bank first before making your own always, we have so many to pick from". Before this, sfx_plan.py mapped event TYPE to a
rotation (chapter = whoosh_1..3), the bank rule was a WARN, hits carried no event id, and the loudest moment of a sound was
placed by a hand-typed LEAD.

  python3 -I sfx_pick.py WORK --route ROUTE [--dur S]
        moments: events_resolved.json (every event with an edit_in) or plan/moments.json [{"id","t","what","object_line"?,"weight"?,"list"?}]
        object line per moment: the editor may write plan/object_lines.json {"<event id>": "a paper card slides in, light, under 0.4 s"};
        otherwise this tool proposes one from the event type and text (printed, and stored in the plan)
        writes WORK/story/sfx_plan.json   {"hits": [{t, event, object_line, file, sha256, recording_id, rank_score, runner_ups, db, why}],
                                           "bank_misses": [...], "dropped": [...]}   (sfx_check.py / assemble.py keys kept: t, file, db, why)
              WORK/audio/sfx_candidates.json   per object line: the class filter, the top candidates with earshot scores
  python3 -I sfx_pick.py --selftest

Rules read from ~/ob-editor/qc/formats.json: sfx.level_db_vs_voice, first_s_none, min_gap_s, list_tick_gap_s, repeat_max_reel/long,
back_to_back, min_runner_ups, banned_families; the route's sfx_per_min.cap. Never picks a code-made sound or a banned family. A moment with
no plausible bank sound is a `bank_misses` row with the search that ran and an Openverse query to try (openverse_sfx.py), never a silent
fallback to the code kit. The sound's loudest 10 ms (indexed by bank_index.py) is put on the event's frame.
"""
import json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bank_index as BI   # noqa: E402
import music_pick as MP   # noqa: E402

FPS = 29.97
TYPE_W = {"chapter": 1.0, "stat_bars": 0.9, "photo": 0.7, "photo_overlay": 0.7, "reel": 0.7, "plate": 0.6, "facequote": 0.6, "label": 0.3, "pills": 0.3, "ffcover": 0.2}
# object-line words -> sound classes that can do that job (bank_index CLASS_KW names)
CLASS_HINTS = [(r"swoosh|swish|whoosh|slide|slides|swipe|fly|flies|wipe|sweep", {"swish"}), (r"paper|page|card slides|notepad|note", {"paper", "swish", "tap"}),
               (r"camera|shutter|photo|snap|flash", {"camera", "click", "pop"}), (r"number|ding|chime|success|stat|bars|score", {"ding", "glass", "ui"}),
               (r"\bpop|label|bubble|appears", {"pop", "click", "tap", "ui"}), (r"lands|drops|heavy|thud|stamp|slam", {"thud", "impact", "boom"}),
               (r"rise|riser|build", {"riser"}), (r"glass|ting|clink", {"glass", "ding"}), (r"click|tap|type|key", {"click", "tap", "ui"})]
DEFAULT_CLASSES = {"swish", "paper", "camera", "ding", "glass", "pop", "click", "tap", "ui", "thud", "impact"}   # no riser/boom unless the line asks


def propose_line(ev):
    t = (ev.get("type") or "").lower(); tx = (ev.get("text") or "").lower()
    if ev.get("object_line"):
        return ev["object_line"]
    if t == "moment" and len(tx.split()) >= 3:
        return ev["text"].strip()      # plan/moments.json "what" already describes the object
    if t == "chapter":
        return "a chapter title card swooshes in, medium weight, under 0.6 s"
    if t == "stat_bars":
        return "bars grow and a number lands, medium, a short ding"
    if t in ("photo", "photo_overlay") or re.search(r"photo|proof|client|before|after", tx):
        return "a photo snaps onto the screen, light, like a camera click"
    if t == "reel":
        return "a video window pops open, light, a short swish"
    if t == "plate":
        return "a title plate slides in, light, a short swish"
    if t == "facequote":
        return "a quote card slides in, light, like paper"
    if re.search(r"\d", tx) and re.search(r"%|lbs|pounds|kg|weeks", tx):
        return "a number lands on screen, light, a soft ding"
    return "a small text label pops in, light, under 0.3 s"


def allowed_classes(line):
    cl = set()
    for rx, cs in CLASS_HINTS:
        if re.search(rx, line.lower()):
            cl |= cs
    return cl or set(DEFAULT_CLASSES)


def moments(work, info, dur):
    w = BI.xp(work); ol = MP.jload(f"{w}/plan/object_lines.json", {}) or {}
    mo = MP.jload(f"{w}/plan/moments.json")
    out = []
    if mo:
        for m in mo:
            out.append({"id": str(m.get("id")), "t": float(m["t"]), "type": m.get("type", "moment"), "text": m.get("what", ""), "object_line": m.get("object_line") or ol.get(str(m.get("id"))),
                        "weight": float(m.get("weight", 0.6)), "list": bool(m.get("list"))})
    else:
        for e in info["events"]:
            out.append({"id": str(e["id"]), "t": e["t"], "type": e["type"], "text": e["text"], "object_line": ol.get(str(e["id"])), "weight": TYPE_W.get(e["type"], 0.5), "list": False})
    return [m for m in out if 0 <= m["t"] < dur]


def pool_for(idx, cfg, line, classes):
    """sounds that may be heard for this line: bank only, no code-made, no banned family, a plausible class, a sane length."""
    banned = set(cfg["sfx"]["banned_families"])
    P = []
    for s, e in idx["sfx"].items():
        if e.get("code_made") or (e.get("banned_family") and e["banned_family"] in banned) or e.get("banned_family"):
            continue
        if e.get("class") not in classes:
            continue
        if (e.get("duration_s") or 0) > 3.0 and e.get("class") not in ("riser", "boom"):
            continue
        if (e.get("loud10_s") or 0) > 0.7 and e.get("class") not in ("riser", "boom"):
            continue   # a late peak would put the sound early on the cut
        if (e.get("duration_s") or 9) < 0.05:
            continue
        P.append(s)
    return P


def earshot_ranker(idx, emb):
    """rank_fn(lines, shas) -> (z matrix [len(lines), len(shas)], verdicts matrix of str), via earshot's calibrated CLAP score."""
    os.environ.setdefault("EARSHOT_HOME", f"{BI.ED}/earshot-home"); os.environ.setdefault("EARSHOT_OFFLINE", "1"); os.environ.setdefault("EARSHOT_THREADS", "3")
    from earshot import vocab, search
    v = vocab.get()
    def rank(lines, shas):
        A = np.stack([emb[s] for s in shas]); T = v.embed_text(lines)
        Z = v.calibrate(A, T)["z_q"]            # (n_sounds, n_lines)
        Z = np.round(Z.T, 2)
        V = np.array([[search.verdict(float(z)) for z in row] for row in Z])
        return Z, V
    return rank


def plan(work, route, idx, rank_fn, cfg=None, dur=None, write=True):
    cfg = cfg or BI.load_cfg(route); sc = cfg["sfx"]
    if cfg["sfx_need"] == "none":
        raise SystemExit(f"sfx_pick: route {route} has no sound effects (formats.json sfx: none)")
    info, used = MP.find_work(work)
    dur = dur or info["dur"]
    if not dur:
        raise SystemExit("sfx_pick: cannot tell how long the edit is: no cutlist.json / events in WORK. Pass --dur SECONDS.")
    ms = moments(work, info, dur)
    if not ms:
        raise SystemExit("sfx_pick: no visual events: WORK has no events_resolved.json with edit_in times and no plan/moments.json. "
                         "Write plan/moments.json as [{\"id\":\"M1\",\"t\":12.4,\"what\":\"a paper card slides in\"}].")
    cap = float((cfg["sfx_per_min"] or {}).get("cap") or 4.0); allowed = int(cap * dur / 60.0 + 1e-9)
    long = cfg["long"]; rep_max = sc["repeat_max_long"] if long else sc["repeat_max_reel"]
    lo, hi = sc["level_db_vs_voice"]; frac = 0.5 if long else 0.25
    for m in ms:
        m["line"] = propose_line(m)
    lines = sorted({m["line"] for m in ms})
    cand_by_line, rows = {}, []
    allsha = [s for s, e in idx["sfx"].items()]
    for ln in lines:
        cls = allowed_classes(ln); P = pool_for(idx, cfg, ln, cls)
        cand_by_line[ln] = {"classes": sorted(cls), "pool": P}
    # one batched earshot call over the union pool
    union = sorted({s for v in cand_by_line.values() for s in v["pool"]})
    Z, V = rank_fn(lines, union) if union else (np.zeros((len(lines), 0)), np.empty((len(lines), 0), dtype=str))
    col = {s: i for i, s in enumerate(union)}
    for li, ln in enumerate(lines):
        pool = cand_by_line[ln]["pool"]
        sc_list = sorted(((float(Z[li, col[s]]), str(V[li, col[s]]), s) for s in pool), reverse=True)
        cand_by_line[ln]["ranked"] = sc_list
        rows.append({"object_line": ln, "classes": cand_by_line[ln]["classes"], "pool_size": len(pool), "searched": f"{len(pool)} bank sounds of classes {sorted(cand_by_line[ln]['classes'])}",
                     "top": [{"file": idx["sfx"][s]["paths"][0], "sha256": s, "recording_id": idx["sfx"][s]["recording_id"], "class": idx["sfx"][s]["class"], "pack": idx["sfx"][s]["pack"], "score": z, "verdict": v}
                             for z, v, s in sc_list[:8]]})
    # phase 1: which moments get a sound (highest weight first). A moment with no plausible bank sound is a bank miss and does not use up the cap.
    acc, dropped, misses = [], [], []
    for m in sorted(ms, key=lambda m: (-m["weight"], m["t"])):
        ranked = cand_by_line[m["line"]]["ranked"]
        if not any(v in ("strong", "plausible") for _, v, _ in ranked):
            best = ranked[0] if ranked else None
            misses.append({"event": m["id"], "t": round(m["t"], 2), "object_line": m["line"],
                           "bank_miss": f"searched {len(cand_by_line[m['line']]['pool'])} bank sounds of classes {sorted(cand_by_line[m['line']]['classes'])}; "
                                        + (f"best was {idx['sfx'][best[2]]['title']} ({best[1]}, z {best[0]:.2f})" if best else "no sound of those classes in the bank"),
                           "suggest_openverse": re.sub(r"\s+", " ", re.sub(r"\b(a|an|the|in|on|onto|like|under|s|light|medium|heavy|weight)\b", " ", re.sub(r"[^a-z ]", " ", m["line"].lower().split(",")[0]))).strip()[:50]})
            continue
        if len(acc) >= allowed:
            dropped.append({"event": m["id"], "t": round(m["t"], 2), "why": f"over the cap: {allowed} sounds in {dur:.0f} s at {cap:g}/min on {route}"}); continue
        if m["t"] < sc["first_s_none"] + 0.05:
            dropped.append({"event": m["id"], "t": round(m["t"], 2), "why": f"inside the first {sc['first_s_none']} s"}); continue
        if any(abs(m["t"] - a["t"]) < (sc["list_tick_gap_s"] if (m["list"] and a["list"]) else sc["min_gap_s"]) for a in acc):
            dropped.append({"event": m["id"], "t": round(m["t"], 2), "why": f"within {sc['min_gap_s']} s of a stronger moment"}); continue
        acc.append(m)
    acc.sort(key=lambda m: m["t"])
    # phase 2: choose a sound per moment, varied by recording id
    hits, use, last = [], {}, []
    for m in acc:
        ranked = cand_by_line[m["line"]]["ranked"]
        plaus = [(z, v, s) for z, v, s in ranked if v in ("strong", "plausible")]
        def ok(s, strict):
            r = idx["sfx"][s]["recording_id"]
            if use.get(r, 0) >= rep_max:
                return False
            if not sc["back_to_back"] and last and last[-1] == r:
                return False
            return not (strict and r in last[-2:])
        choice = next((x for x in plaus if ok(x[2], True)), None) or next((x for x in plaus if ok(x[2], False)), None)
        if not choice:
            misses.append({"event": m["id"], "t": round(m["t"], 2), "object_line": m["line"], "bank_miss": f"every plausible sound is at its repeat cap ({rep_max} per recording) or would repeat back to back; "
                                                                                                           f"{len(plaus)} plausible, {len(set(idx['sfx'][s]['recording_id'] for _, _, s in plaus))} recordings",
                           "suggest_openverse": "more variants of: " + m["line"][:40]}); continue
        z, v, s = choice; e = idx["sfx"][s]; r = e["recording_id"]
        seen, ru = {r}, []
        for z2, v2, s2 in plaus:
            r2 = idx["sfx"][s2]["recording_id"]
            if r2 in seen:
                continue
            seen.add(r2); ru.append({"file": idx["sfx"][s2]["paths"][0], "sha256": s2, "recording_id": r2, "score": round(float(z2), 2)})
            if len(ru) >= max(sc["min_runner_ups"], 3):
                break
        adj = -1.5 if "light" in m["line"].lower() else (1.5 if "heavy" in m["line"].lower() else 0.0)
        db = round(float(np.clip(lo + (hi - lo) * frac + adj, lo, hi)), 1)
        lead = float(e.get("loud10_s") or e.get("peak_s") or 0.0)
        t = round(round((m["t"]) * FPS) / FPS - lead, 3)
        if t < sc["first_s_none"]:
            dropped.append({"event": m["id"], "t": round(m["t"], 2), "why": f"{e['title']}'s loudest moment is {lead:.2f} s in, which puts its start inside the first {sc['first_s_none']} s"}); continue
        use[r] = use.get(r, 0) + 1; last.append(r)
        hits.append({"t": t, "event": m["id"], "event_t": round(m["t"], 3), "object_line": m["line"], "file": e["paths"][0], "sha256": s, "recording_id": r, "pack": e["pack"], "class": e["class"],
                     "rank_score": round(float(z), 2), "verdict": v, "runner_ups": ru, "db": db, "lead_s": round(lead, 3), "why": m["line"]})
    out = {"route": route, "dur_s": round(dur, 2), "cap_per_min": cap, "n_hits": len(hits), "per_min": round(len(hits) / (dur / 60), 2), "moments": len(ms),
           "hits": hits, "bank_misses": misses, "dropped": dropped, "inputs_used": used}
    if write:
        wd = BI.xp(work); os.makedirs(f"{wd}/story", exist_ok=True); os.makedirs(f"{wd}/audio", exist_ok=True)
        json.dump(out, open(f"{wd}/story/sfx_plan.json", "w"), indent=1)
        json.dump({"route": route, "lines": rows, "note": "scores are earshot's calibrated CLAP z for the object line; verdict strong/plausible are the only ones used"}, open(f"{wd}/audio/sfx_candidates.json", "w"), indent=1)
    return out, rows


# ---------------------------------------------------------------- selftest
def selftest():
    work = os.path.expanduser("~/ob-scratch/skill-rebuild/WP2/sfx_selftest"); os.makedirs(work, exist_ok=True)
    ok = True
    def chk(name, cond, detail=""):
        nonlocal ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail else ""))
    def snd(i, cls, rec, **kw):
        e = {"sha256": f"{i:064x}", "paths": [f"/bank/s{i}.wav"], "title": f"s{i}", "pack": "test", "class": cls, "recording_id": rec, "code_made": False, "banned_family": None,
             "duration_s": 0.4, "loud10_s": 0.05, "peak_s": 0.05}
        e.update(kw); return e["sha256"], e
    sfx = dict([snd(1, "swish", "A"), snd(2, "swish", "A"), snd(3, "swish", "B"), snd(4, "swish", "C"), snd(5, "swish", "D", code_made=True), snd(6, "swish", "E", banned_family="glitch"),
                snd(7, "paper", "P"), snd(8, "camera", "K"), snd(9, "swish", "F", loud10_s=0.3)])
    idx = {"sfx": sfx, "music": {}}
    def rank(lines, shas):   # stand-in for earshot: swish is plausible for swish lines, paper for paper lines; camera never matches a swish
        Z = np.array([[3.0 if (idx["sfx"][s]["class"] == "swish" and "swoosh" in ln) or (idx["sfx"][s]["class"] == "paper" and "paper" in ln) else -1.0 for s in shas] for ln in lines])
        V = np.array([["strong" if z > 2 else "no match" for z in row] for row in Z]); return Z, V
    wk = f"{work}/WORK"; os.makedirs(f"{wk}/plan", exist_ok=True)
    json.dump([{"id": f"M{i}", "t": 2.0 + 3.0 * i, "what": "a card swooshes in, light", "weight": 0.6} for i in range(10)] + [{"id": "EARLY", "t": 0.2, "what": "a card swooshes in"}, {"id": "TOOCLOSE", "t": 5.4, "what": "a card swooshes in"}], open(f"{wk}/plan/moments.json", "w"))
    cfg = BI.load_cfg("reel-talking")
    out, rows = plan(wk, "reel-talking", idx, rank, cfg=cfg, dur=120.0, write=True)
    hs = out["hits"]; reps = {}
    for h in hs:
        reps[h["recording_id"]] = reps.get(h["recording_id"], 0) + 1
    chk("hits stay under the route's per-minute cap", len(hs) <= int(cfg["sfx_per_min"]["cap"] * 120 / 60 + 1e-9), f"{len(hs)} hits in 120 s, cap {cfg['sfx_per_min']['cap']}/min")
    chk("no code-made sound and no banned family is ever picked", all(h["recording_id"] not in ("D", "E") for h in hs))
    chk("no sound inside the first 0.5 s", all(h["t"] >= cfg["sfx"]["first_s_none"] for h in hs) and all(d["event"] != "EARLY" or True for d in out["dropped"]))
    chk("EARLY moment dropped with a reason", any(d["event"] == "EARLY" for d in out["dropped"]))
    chk("no recording over the repeat cap", all(n <= cfg["sfx"]["repeat_max_reel"] for n in reps.values()), str(reps))
    chk("never the same recording back to back", all(a["recording_id"] != b["recording_id"] for a, b in zip(hs, hs[1:])))
    chk("every hit carries event, object_line, file, sha256, db, runner_ups", all(h["event"] and h["object_line"] and h["file"] and h["sha256"] and "db" in h and h["runner_ups"] is not None for h in hs))
    chk("the loudest 10 ms is on the event frame (t = event - loud10, frame-snapped)", all(abs((h["t"] + h["lead_s"]) - h["event_t"]) < 0.02 for h in hs))
    chk("level sits inside the config band", all(cfg["sfx"]["level_db_vs_voice"][0] <= h["db"] <= cfg["sfx"]["level_db_vs_voice"][1] for h in hs))
    json.dump([{"id": "Q1", "t": 5.0, "what": "a glass bottle clinks"}], open(f"{wk}/plan/moments.json", "w"))
    o2, _ = plan(wk, "reel-talking", idx, rank, cfg=cfg, dur=20.0, write=False)
    chk("no plausible bank sound -> bank_miss with the search, no hit, no code-kit fallback", not o2["hits"] and o2["bank_misses"] and "searched" in o2["bank_misses"][0]["bank_miss"], o2["bank_misses"][0]["bank_miss"][:70] if o2["bank_misses"] else "")
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return 0
    if a[0] == "--selftest":
        return selftest()
    try:
        import earshot  # noqa: F401
    except Exception:
        py = f"{BI.ED}/venvs/earshot/bin/python"
        os.execv(py, [py, os.path.abspath(__file__)] + a)
    opt = lambda k, d=None: (a[a.index(k) + 1] if k in a else d)
    route = opt("--route")
    if not route:
        raise SystemExit("sfx_pick: --route ROUTE is required (routes in ~/ob-editor/qc/formats.json), e.g. --route reel-graphics")
    cfg = BI.load_cfg(route); idx = BI.load_index(cfg); ep = BI.index_path(cfg).replace(".json", "_embeddings.npz")
    if not os.path.exists(ep):
        raise SystemExit(f"sfx_pick: no embeddings at {ep}: run bank_index.py build")
    z = np.load(ep); emb = {k: z[k] for k in z.files}
    out, rows = plan(a[0], route, idx, earshot_ranker(idx, emb), cfg=cfg, dur=float(opt("--dur")) if opt("--dur") else None)
    print("read: " + "; ".join(out["inputs_used"]))
    print(f"{out['n_hits']} sounds in {out['dur_s']} s = {out['per_min']}/min (cap {out['cap_per_min']}/min), {len(out['bank_misses'])} bank misses, {len(out['dropped'])} moments dropped")
    for h in out["hits"][:int(opt("--show", 12))]:
        print(f"  t={h['t']:7.2f} {h['event']:>6} [{h['pack']}/{h['class']}] {os.path.basename(h['file'])[:34]:34} z={h['rank_score']:5.2f} {h['db']:5.1f} dB  <- {h['object_line'][:60]}")
        print(f"            runner-ups: " + ", ".join(f"{os.path.basename(r['file'])[:22]} ({r['score']})" for r in h["runner_ups"][:3]))
    for m in out["bank_misses"][:5]:
        print(f"  BANK MISS {m['event']} t={m['t']}: {m['bank_miss'][:110]}  -> openverse query: {m['suggest_openverse']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
