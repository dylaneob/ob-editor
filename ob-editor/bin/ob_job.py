#!/usr/bin/env python3
"""One command to start an edit, one to finish it (editor rebuild WP1, 2026-11-10; OB: "no more mistakes", "not just doing the
easiest and fastest"). `start` checks the drives, models and banks, writes WORK/job.json and prints the rules for the route;
`gate` runs the QC gate with every input found in WORK, strict for the route; `finish` delivers only when the gate, the WARN
answers, the decision records and the video-reviewer's PASS for that exact file (sha256) are all clear. Numbers and each route's
required checks come from ~/ob-editor/qc/formats.json (qc_route.cfg); the rules from the ledger (ledger.py).

  python3 -I ob_job.py routes
  python3 -I ob_job.py start ROUTE WORK [--name N] [--camera F] [--mic F] [--script F | --no-script "why"] [--template T17] [--ref URL]
                                        [--music none --music-none-why "OB: ..."] [--sfx none [--sfx-none-why "OB: ..."]]
  python3 -I ob_job.py rules ROUTE [--hash]          the block to paste into a builder's brief (starts "EDITOR RULES <route> <hash>")
  python3 -I ob_job.py brief WORK [--out WORK/BRIEF.md]
  python3 -I ob_job.py lint-brief FILE               FAIL on a missing/stale rules hash or a ban that contradicts the ledger
  python3 -I ob_job.py status WORK                   each required check and record: done / missing / stale, and the next command
  python3 -I ob_job.py gate WORK FILE                the gate with every input found by convention, strict for the route
  python3 -I ob_job.py finish WORK FILE [--to WHAT] [--as NAME] [--override "why"]
  python3 -I ob_job.py allow-send FILE --why "..."   one-off: lets a raw or reference video be sent in chat (the send hook reads it)
  python3 -I ob_job.py --selftest
`pieces WORK FILE SEGS.json [--cam CAM.json]` records where each cut piece plays, for engines and build scripts that do not
(SEGS rows: [source, start s, end s, where it plays in FILE s]; CAM rows: [camera file, start s, end s, where it plays]).
Inputs found by `gate`: job.json inputs; WORK/script.txt|script.json|story/script.txt; the render's recorded pieces and camera map
(qc/pieces); story/sfx_plan.json; music from audio/manifest.json (else the gate reads story/score*.json); events_resolved.json cards;
WORK/pieces.json + the job's camera for look-off; for long form without recorded pieces, segs from WORK/cutlist.json (master audio).
Tests: OB_DELIVER_ROOT, OB_QC_STATE, OB_FORMATS, OB_DELIVERIES_LOG (see qc_route.py).
"""
import datetime, hashlib, json, os, re, shutil, subprocess, sys, time

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
import qc_route as QR, ledger as L

STANDING = ("Standing order (OB 11-09): he gives an instruction, we do it; no approval holds, option menus or swaps of our own. "
            "OB is never the verifier (11-10): gate + a fresh video-reviewer PASS on the exact file before anything reaches him. "
            "Never write to /Volumes/T7. Deliver only with ob_job.py finish.")
AUDIO = (".wav", ".mp3", ".m4a", ".aif", ".aiff", ".flac")
BANS = [(r"\bno (client|clients)\b", "bans client proof (M56: clients on screen when he says clients)"),
        (r"\bno (proof|before.?and.?after|before.?after)\b", "bans client proof (M56)"),
        (r"\bskip(ping)? (the )?(qc )?gate\b", "skips the gate (M27)"), (r"\bOB_QC\s*=\s*0\b", "turns the gate off (M27)"),
        (r"\bno speech model\b", "drops the speech model the cue and word checks need (M02, M03)"),
        (r"\bno (apple )?vision\b", "drops Apple Vision, which the text-on-face and framing checks need (M05, M46)"),
        (r"\b(use|using|with|run)\b[^.\n]{0,30}\b(grabcut|vision (person )?masks?|drawn masks?)\b", "cutouts are BiRefNet only (OB 11-06, 11-09)"),
        (r"\bpick (it|one|the music|a track|the song) (yourself|by feel|by ear)\b", "music is picked from 3+ scored candidates (M57, M58, record:music)"),
        (r"(/Volumes/T7/[^\s`'\"]*|\bT7\b)[^.\n]{0,40}\b(output|deliver|write|save|render to|WORK)\b|\b(output|deliver|write|save|render)\w*\b[^.\n]{0,40}(/Volumes/T7\b|\bT7\b)",
         "writes to the T7 (full on 11-06 and 11-10): work and deliveries go elsewhere")]


def sha12(s): return hashlib.sha256(s.encode()).hexdigest()[:12]


def die(msg, code=1): print(msg); sys.exit(code)


def numbers(c):
    out = []
    for sec in ("master", "voice", "music", "sfx", "picture", "text", "delivery"):
        d = c.get(sec, {})
        kv = [f"{k}={'/'.join(map(str, v)) if isinstance(v, list) else v}" for k, v in d.items() if not k.startswith("_") and k not in ("edu_tone", "banned_words")]
        out.append(f"{sec}: " + " ".join(kv))
    if c.get("sfx_per_min"): out.append(f"sfx per minute: cap {c['sfx_per_min']['cap']}, fail {c['sfx_per_min']['fail']}")
    out.append(f"music tone (teaching): {c['music'].get('edu_tone', '')}")
    out.append(f"banned on screen: {', '.join(c['text'].get('banned_words', []))}; banned files: {', '.join(c['assets'].get('banned_files', []))}; lean photo {c['assets'].get('lean_photo')}")
    return out


def rules_block(route):
    c = QR.cfg(route)
    body = "\n".join([STANDING, f"Route {route}: {c['title']}. Read ~/.claude/skills/short-form-editor/{c['file']}.",
                      f"Music {c.get('music_mode')}, SFX {c.get('sfx_mode')}. Required checks: {', '.join(c['required'])}. Records: {', '.join(c['records']) or 'none'}.",
                      "Active rules (id rule [enforcer]):"] + [L.rule_line(m, 54, 2) for m in L.active(route)] +
                     ["Numbers (formats.json; never restate them in prose):"] + numbers(c) +
                     ["Finish: ob_job.py gate WORK FILE -> video-reviewer (FILE: + SHA256: lines) -> ob_job.py finish WORK FILE."])
    h = sha12(body)
    return f"EDITOR RULES {route} {h}\n{body}\nEND EDITOR RULES", h


def free_gb(p):
    while p and not os.path.exists(p): p = os.path.dirname(p)
    return shutil.disk_usage(p or "/").free / 2 ** 30


def deliver_root():
    P = QR.paths()
    for r in P.get("deliver_roots", []):
        if os.path.isdir(r) and os.access(r, os.W_OK) and free_gb(r) >= P.get("deliver_min_free_gb", 0): return r
    return None


def checklist(route, job):
    c = QR.cfg(route); rows = []
    for k in c["required"]:
        why = c["na"].get(k) or QR.declared_away(k, job, route)
        rows.append(f"  check  {k:10s} " + (f"N/A: {why}" if why else QR.WHAT.get(k, "runs on the file itself")))
    for r in c["records"]: rows.append(f"  record {r:10s} {os.path.join(job['work'], c['record_files'].get(r, r))}")
    rows.append(f"  review            video-reviewer PASS for the exact file -> {QR.state('reviews')}/<sha256>.json")
    return rows


def opt(a, k):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None


def cmd_start(a):
    if len(a) < 2: die("usage: ob_job.py start ROUTE WORK [...]  (routes: ob_job.py routes)", 2)
    route, work = a[0], os.path.abspath(os.path.expanduser(a[1]))
    if route not in QR.routes(): die(f"unknown route {route!r}: python3 -I ~/ob-editor/bin/ob_job.py routes", 2)
    P = QR.paths(); fatal = []; lines = []
    bad = [n for n in P.get("never_write_work", []) if os.path.realpath(work).startswith(os.path.realpath(n)) or work.startswith(n)]
    lines.append(("FAIL" if bad else "OK  ") + f" WORK {work}" + (f" is under {bad[0]}: use {P['work_roots'][0]}/<name>" if bad else ""))
    if bad: fatal.append("WORK")
    fg = free_gb(work); low = fg < P.get("work_min_free_gb", 0)
    lines.append(("FAIL" if low else "OK  ") + f" free space for WORK {fg:.0f} GB (need {P.get('work_min_free_gb')})"); fatal += ["space"] if low else []
    dr = deliver_root(); lines.append(("OK  " if dr else "MISSING") + f" deliver root: {dr or 'none of ' + ', '.join(P.get('deliver_roots', [])) + ' is writable with room'}")
    try: rs = subprocess.run(["python3", "-I", os.path.join(BIN, "render_slots.py"), "list"], capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[:1]
    except Exception as e: rs = [f"unavailable ({e!r})"]
    lines.append(f"INFO render slots: {(rs or ['?'])[0]}")
    for name, p in (("whisper medium", "~/.whisper-models/ggml-medium.en.bin"), ("ffmpeg-full", os.path.join(BIN, "ffmpeg-full")),
                    ("earshot venv", "~/ob-editor/venvs/earshot/bin/python"), ("bank_index.json", P.get("bank_index", ""))):
        lines.append(("OK  " if os.path.exists(os.path.expanduser(p)) else "MISSING") + f" {name} ({os.path.expanduser(p)})")
    for flag in ("--camera", "--mic", "--script"):
        v = opt(a, flag)
        if v and not os.path.exists(os.path.expanduser(v)): lines.append(f"FAIL {flag} {v} not found"); fatal.append(flag)
    dec = {"separate_mic": bool(opt(a, "--mic"))}
    if opt(a, "--script"): dec["script"] = os.path.abspath(os.path.expanduser(opt(a, "--script")))
    if "--no-script" in a: dec["script"], dec["no_script_why"] = None, opt(a, "--no-script") or ""
    if opt(a, "--music") == "none": dec["music"], dec["music_none_why"] = "none", opt(a, "--music-none-why") or ""
    if opt(a, "--sfx") == "none": dec["sfx"], dec["sfx_none_why"] = "none", opt(a, "--sfx-none-why") or ""
    name = opt(a, "--name") or os.path.basename(work.rstrip("/")) or "job"
    job = {"name": name, "route": route, "started": datetime.datetime.now().isoformat(timespec="seconds"), "work": work,
           "inputs": {k: os.path.abspath(os.path.expanduser(opt(a, "--" + k))) for k in ("camera", "mic", "script") if opt(a, "--" + k)},
           "declares": dec, "template": opt(a, "--template"), "ref": opt(a, "--ref")}
    dp = QR.declaration_problems(route, job)
    for x in dp: lines.append(f"FAIL declares: {x}"); fatal.append("declares")
    print(f"ob_job start {route} {work}"); print("\n".join("  " + l for l in lines))
    if fatal: die(f"NOT STARTED ({', '.join(fatal)}): fix the FAIL lines above and run start again", 1)
    for d in ("audio", "story", "qc", "plan"): os.makedirs(os.path.join(work, d), exist_ok=True)
    jf = os.path.join(work, "job.json")
    if os.path.exists(jf): shutil.copy2(jf, jf + ".prev")
    json.dump(job, open(jf, "w"), indent=1)
    wa = os.path.join(work, "qc", "warn_answers.json")
    if not os.path.exists(wa): json.dump({}, open(wa, "w"))
    QR._jdump({"name": name, "work": work, "route": route, "started": job["started"]}, os.path.join(QR.state("jobs"), name + ".json"))
    print(f"STARTED job {name}: {jf}\n"); print(rules_block(route)[0]); print("\nChecklist (what satisfies each):"); print("\n".join(checklist(route, job)))
    print(f"\nNext: build the cut in {work}, then: python3 -I ~/ob-editor/bin/ob_job.py gate {work} FILE")


def need_job(work):
    work = os.path.abspath(os.path.expanduser(work)); job = QR.load_job(work)
    if not job: die(f"no {work}/job.json: python3 -I ~/ob-editor/bin/ob_job.py start ROUTE {work}", 2)
    return work, job


def music_from_manifest(work):
    d = QR._jload(os.path.join(work, "audio", "manifest.json"))
    if d is None: return None
    found = []
    def walk(x, key=""):
        if isinstance(x, dict): [walk(v, f"{key}/{k}") for k, v in x.items()]
        elif isinstance(x, list): [walk(v, key) for v in x]
        elif isinstance(x, str) and x.lower().endswith(AUDIO) and re.search(r"music|bed|track|song", key, re.I): found.append(os.path.expanduser(x))
    walk(d); return ":".join(dict.fromkeys(found)) or None


def gather(work, path, job):
    """Every gate input found by convention. Returns (kwargs for qc_gate.gate, notes)."""
    import qc_gate as Q
    c = QR.cfg(job["route"]); notes = []; dec = job.get("declares", {}); kw = {"work": work, "route": job["route"], "job": job}
    kw["long"] = True if c.get("long") else None
    if not ("script" in dec and dec["script"] is None):
        kw["script"] = QR._script_of(work, job); notes.append(f"script: {kw['script'] or 'none found (words will be required)'}")
    pp = Q.pieces_path(path); rec = QR._jload(pp, {}) if os.path.exists(pp) else {}
    if rec and abs(rec.get("mtime", 0) - os.path.getmtime(path)) < 1e-3:
        kw["segs"] = rec.get("pieces") or None; kw["theirs"] = rec.get("theirs"); notes.append(f"recorded pieces: {len(rec.get('pieces') or [])} (camera map: {'yes' if rec.get('cam') else 'no'})")
    else: notes.append("recorded pieces: none for this exact file (record them: ob_job.py pieces WORK FILE SEGS.json [--cam CAM.json])")
    cl = os.path.join(work, "cutlist.json")
    if not kw.get("segs") and c.get("long") and os.path.exists(cl):
        d = QR._jload(cl, {}); segsd = d.get("segments") or []; m = d.get("master")
        mp = os.path.normpath(os.path.join(work, m)) if m and not os.path.isabs(m) else m
        dur = float(Q.probe(path).get("format", {}).get("duration", 0) or 0)
        ok = segsd and mp and os.path.exists(mp) and all({"src_in", "src_out", "edit_in"} <= set(s) for s in segsd) and abs(max(s.get("edit_out", 0) for s in segsd) - dur) < 0.5
        if ok:
            kw["segs"] = [(mp, float(s["src_in"]), float(s["src_out"]), float(s["edit_in"])) for s in segsd]
            notes.append(f"segs: {len(segsd)} from cutlist.json on {os.path.basename(mp)} (audio_shift_ms ignored; ends match the file within 0.5 s)")
        else: notes.append("segs: cutlist.json does not map onto this file (master missing or length differs): inner edges unchecked")
    sp = os.path.join(work, "story", "sfx_plan.json")
    if os.path.exists(sp): kw["sfx_plan"] = sp
    kw["music"] = music_from_manifest(work); notes.append(f"sfx plan: {kw.get('sfx_plan') or 'none'}; music: {kw['music'] or 'gate reads story/score*.json if any'}")
    if os.path.exists(os.path.join(work, "events_resolved.json")):
        try: kw["cards"] = Q.cover_spans(work); notes.append(f"cards: {len(kw['cards'])} cover spans")
        except Exception as e: notes.append(f"cards: events_resolved.json unreadable ({e!r})")
    pj, cam = os.path.join(work, "pieces.json"), (job.get("inputs") or {}).get("camera")
    if os.path.exists(pj) and cam: kw["pieces"], kw["src"] = pj, cam
    return kw, notes


def run_gate(work, path, job):
    import qc_gate as Q
    kw, notes = gather(work, path, job); print("inputs: " + " | ".join(notes)); t0 = time.time()
    R = Q.gate(path, kw.get("script"), kw.get("long"), kw.get("pieces"), kw.get("src"), segs=kw.get("segs"), cards=kw.get("cards"),
               theirs=kw.get("theirs"), sfx_plan=kw.get("sfx_plan"), work=work, music=kw.get("music"), route=job["route"], job=job)
    ok = Q.show(path, R); Q.save(path, R, ok)
    QR.log_run(path, R, {k: (len(v) if k in ("segs", "cards") and v else v) for k, v in kw.items() if k not in ("job", "theirs") and v not in (None, [], "")} | {"via": "ob_job.py gate"}, job)
    job.update(last_file=os.path.abspath(path), last_sha=QR.sha256(path), last_gate=datetime.datetime.now().isoformat(timespec="seconds"))
    json.dump(job, open(os.path.join(work, "job.json"), "w"), indent=1)
    print(f"gate took {time.time() - t0:.0f} s")
    return ok


def cmd_gate(a):
    if len(a) < 2: die("usage: ob_job.py gate WORK FILE", 2)
    work, job = need_job(a[0]); path = os.path.abspath(a[1]); ok = run_gate(work, path, job)
    pr = QR.delivery_problems(path, work)
    print(f"{len(pr)} delivery problem(s) left" + (": python3 -I ~/ob-editor/bin/ob_job.py status " + work if pr else f": finish with ob_job.py finish {work} {path}"))
    sys.exit(0 if ok else 1)


def cmd_status(a):
    if not a: die("usage: ob_job.py status WORK", 2)
    work, job = need_job(a[0]); route = job["route"]; c = QR.cfg(route); f = job.get("last_file")
    print(f"job {job['name']}  route {route}  WORK {work}")
    nxt = None
    if not f or not os.path.exists(f):
        print("  no gate run yet"); nxt = f"python3 -I ~/ob-editor/bin/ob_job.py gate {work} FILE"
    else:
        sh = QR.sha256(f); stale = sh != job.get("last_sha"); v = QR.verdict(sh=sh)
        R = QR.apply({k: (x["status"], x["detail"]) for k, x in v.items()}, route, job); wp = QR.warn_problems(v, work, route)
        print(f"  file {f}" + ("  (CHANGED since the last gate: stale)" if stale else ""))
        for k in c["required"] + [k for k in R if k not in c["required"] and R[k][0] in ("FAIL", "WARN")]:
            s, d = R.get(k, ("SKIP", "never ran")); ans = not any(p.startswith(f"WARN {k} ") for p in wp)
            word = "stale" if stale else "done" if s in ("PASS", "N/A") or (s == "WARN" and ans) else "missing" if s == "SKIP" or "required for" in str(d) else s.lower() if s != "WARN" else "answer"
            print(f"  {word:7s} check  {k:10s} {s:4s} {str(d)[:90]}")
        if stale or not v: nxt = f"python3 -I ~/ob-editor/bin/ob_job.py gate {work} {f}"
    rp = QR.record_problems(route, work, job)
    for r in c["records"]:
        mine = [p for p in rp if p.startswith(f"record {r}") or f"({QR.RECORD_MODULE.get(r)})" in p]
        print(f"  {'missing' if mine else 'done':7s} record {r:10s} {mine[0][:100] if mine else ''}")
    if f and os.path.exists(f):
        rv = QR.review_problem(f); print(f"  {'missing' if rv else 'done':7s} review {'' if not rv else rv[:100]}")
        pr = QR.delivery_problems(f, work)
        nxt = nxt or (f"fix: {pr[0]}" if pr else f"python3 -I ~/ob-editor/bin/ob_job.py finish {work} {f}")
    print(f"NEXT: {nxt}")


def delivery_note(work, path, dst, rep, job):
    v = rep["verdict"]; R = QR.apply({k: (x["status"], x["detail"]) for k, x in v.items()}, job["route"], job)
    wa = QR._jload(os.path.join(work, "qc", "warn_answers.json"), {}) or {}; mc = QR._jload(os.path.join(work, "audio", "music_candidates.json"))
    L_ = [f"# Delivery: {job['name']} ({job['route']})", "", f"- delivered: `{dst}`", f"- source: `{path}`", f"- sha256: `{rep['sha256']}`",
          f"- when: {datetime.datetime.now().isoformat(timespec='seconds')}", "", "## Gate (latest run in which each check ran, strict for the route)", "",
          "| check | status | detail |", "|---|---|---|"] + [f"| {k} | {s} | {str(d)[:140].replace('|', '/')} |" for k, (s, d) in R.items()]
    L_ += ["", "## WARN answers", ""] + ([f"- {k}: {x if isinstance(x, str) else (x or {}).get('answer')}" for k, x in wa.items()] or ["- none"])
    L_ += ["", "## Overrides", ""] + ([f"- {k}: {why}" for k, why in rep["overrides_used"]] or ["- none"])
    if mc:
        L_ += ["", "## Music", "", f"- pick: {mc.get('winner') or mc.get('pick')}", f"- why: {mc.get('why', '')}"]
        cands = mc.get("candidates") or []
        L_ += [f"- runner-up: {c.get('file') or c.get('track') or c}" for c in cands[1:4] if isinstance(c, dict)]
    open(os.path.join(work, "DELIVERY.md"), "w").write("\n".join(L_) + "\n")


def cmd_finish(a):
    if len(a) < 2: die("usage: ob_job.py finish WORK FILE [--to WHAT] [--as NAME] [--override \"why\"]", 2)
    work, job = need_job(a[0]); path = os.path.abspath(a[1])
    if not os.path.exists(path): die(f"{path} not found", 2)
    sh = QR.sha256(path)
    if not any(r.get("job") == job["name"] and r.get("route") == job["route"] for r in QR.runs(sh=sh)):
        print("no strict gate run for this exact file yet: running it now"); run_gate(work, path, job); job = QR.load_job(work)
    rep = QR.report(path, work, use_overrides=bool(opt(a, "--override")))
    if rep["problems"]:
        print(f"NOT DELIVERED: {len(rep['problems'])} problem(s) for {os.path.basename(path)} (sha256 {sh[:12]}). Fix each:")
        for i, p in enumerate(rep["problems"], 1): print(f"  {i}. {p}")
        print(f"Then run again: python3 -I ~/ob-editor/bin/ob_job.py finish {work} {path}"); sys.exit(1)
    root = deliver_root()
    if not root: die(f"no deliver root with {QR.paths().get('deliver_min_free_gb')} GB free among {QR.paths().get('deliver_roots')}: free space, then finish again")
    c = QR.cfg(job["route"]); pat = QR.paths()["deliver_folder_long" if c.get("long") else "deliver_folder"]
    to = os.path.join(root, pat.format(what=opt(a, "--to") or job["name"], date=datetime.date.today().isoformat()))
    import deliver as D
    if not D.deliver(path, to, opt(a, "--as"), work=work, override=opt(a, "--override")): die("deliver.py refused it (lines above): fix and finish again")
    dst = os.path.abspath(os.path.join(to, opt(a, "--as") or os.path.basename(path)))
    delivery_note(work, path, dst, rep, job); print(f"DELIVERED: {dst}\nnote: {os.path.join(work, 'DELIVERY.md')}")


def cmd_allow_send(a):
    if not a or not opt(a, "--why"): die("usage: ob_job.py allow-send FILE --why \"OB asked to see the raw take\"", 2)
    p = os.path.abspath(os.path.expanduser(a[0]))
    if not os.path.isfile(p): die(f"{p} not found", 2)
    f = QR.state("allow_send.json") if os.environ.get("OB_QC_STATE") else os.path.join(QR.QC, "allow_send.json")
    d = QR._jload(f, {}) or {}; d[p] = {"why": opt(a, "--why"), "when": datetime.datetime.now().isoformat(timespec="seconds"), "sha256": QR.sha256(p)}
    QR._jdump(d, f); QR.log_line("ALLOW-SEND", p, f"why: {opt(a, '--why')}"); print(f"allowed once: {p} ({f})")


def cmd_brief(a):
    if not a: die("usage: ob_job.py brief WORK [--out FILE]", 2)
    work, job = need_job(a[0]); out = opt(a, "--out") or os.path.join(work, "BRIEF.md"); block, h = rules_block(job["route"])
    txt = "\n".join([f"# Brief: {job['name']} ({job['route']})", "", "## Job", f"- WORK: `{work}`", f"- route file: `~/.claude/skills/short-form-editor/{QR.cfg(job['route'])['file']}` (read it first)",
                     f"- inputs: {json.dumps(job.get('inputs', {}))}", f"- declares: {json.dumps(job.get('declares', {}))}", f"- template: {job.get('template')}  ref: {job.get('ref')}", "",
                     "## Rules (generated; do not edit this block)", "", block, "", "## Finish", "",
                     f"1. `python3 -I ~/ob-editor/bin/ob_job.py gate {work} FILE`", "2. the video-reviewer agent on FILE (last message: VERDICT, FILE, SHA256 lines)",
                     f"3. `python3 -I ~/ob-editor/bin/ob_job.py finish {work} FILE`", "", "## This job", "", ""])
    open(out, "w").write(txt); print(f"brief written: {out} (EDITOR RULES {job['route']} {h})")


def lint_text(txt):
    out = []; m = re.search(r"EDITOR RULES (\S+) ([0-9a-f]{12})", txt)
    if not m: out.append("no `EDITOR RULES <route> <hash>` line: paste the block from ob_job.py rules ROUTE (or ob_job.py brief WORK)")
    else:
        try:
            cur = rules_block(m.group(1))[1]
            if cur != m.group(2): out.append(f"rules block is stale ({m.group(2)}; current {cur}): regenerate with ob_job.py rules {m.group(1)}")
        except KeyError: out.append(f"unknown route {m.group(1)} in the EDITOR RULES line")
    body = re.sub(r"EDITOR RULES \S+ [0-9a-f]{12}.*?END EDITOR RULES", "", txt, flags=re.S)
    for pat, why in BANS:
        for x in re.finditer(pat, body, re.I):
            line = body.count("\n", 0, x.start()) + 1; out.append(f"line ~{line}: \"{x.group(0)[:60]}\" {why}")
    return out


def cmd_lint(a):
    if not a: die("usage: ob_job.py lint-brief FILE", 2)
    pr = lint_text(open(a[0]).read())
    for p in pr: print(f"FAIL {p}")
    print("PASS brief" if not pr else f"FAIL brief: {len(pr)} problem(s)"); sys.exit(1 if pr else 0)


# ---------- selftest ----------
def selftest():
    import contextlib, io
    ok = True; root = os.path.expanduser("~/ob-scratch/skill-rebuild/wp1/ob_job_selftest_" + time.strftime("%Y%m%d-%H%M%S")); os.makedirs(root)
    env = {"OB_QC_STATE": os.path.join(root, "state"), "OB_DELIVER_ROOT": os.path.join(root, "deliver"), "OB_DELIVERIES_LOG": os.path.join(root, "deliveries.log"),
           "OB_FORMATS": os.path.join(root, "formats.json")}
    old = {k: os.environ.get(k) for k in env}; os.environ.update(env); os.makedirs(env["OB_DELIVER_ROOT"])
    F = json.load(open(os.path.join(QR.QC, "formats.json")))
    F["routes"]["t-selftest"] = {"title": "ob_job selftest", "file": "subjects/qc.md", "long": False, "music": "optional", "sfx": "optional",
                                 "required": ["format", "cues", "edges", "audio", "motion", "text_face", "text_lint", "words"], "records": ["breakdown", "warn_answers"]}
    json.dump(F, open(env["OB_FORMATS"], "w"))
    def chk(good, what):
        nonlocal ok; ok &= bool(good); print(f"  {'ok ' if good else 'BAD'} {what}")
    def call(fn, args):
        buf = io.StringIO(); code = 0
        with contextlib.redirect_stdout(buf):
            try: fn(args)
            except SystemExit as e: code = e.code if isinstance(e.code, int) else 1
        return code, buf.getvalue()
    try:
        work = os.path.join(root, "WORK"); clip = os.path.join(root, "src", "cut.mp4"); os.makedirs(os.path.dirname(clip))
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x6a7f99:s=1080x1920:r=30:d=6", "-f", "lavfi", "-i",
                        "aevalsrc=0.25*sin(2*PI*(170+25*sin(2*PI*2*t))*t)*(0.6+0.4*sin(2*PI*3*t))+0.01*(random(0)-0.5):s=48000:d=6",
                        "-af", "afade=t=in:d=0.4,afade=t=out:st=5.5:d=0.5",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", clip], check=True)
        code, o = call(cmd_start, ["t-selftest", work, "--name", "wp1-selftest"])
        chk(code == 0 and os.path.exists(os.path.join(work, "job.json")) and "EDITOR RULES t-selftest" in o, "start: WORK made, job.json written, rules printed")
        chk(call(cmd_start, ["t-selftest", "/Volumes/T7/OB-EDITS/x-WORK"])[0] == 1, "start refuses a WORK on the T7")
        rb, h = rules_block("reel-talking"); chk(len(rb) < 9000, f"rules block for reel-talking is {len(rb)} chars (< 9000: it grew with the ledger on 11-10; a brief and the 10,000-char hook limit still hold it)")
        bf = os.path.join(root, "brief.md"); open(bf, "w").write(rb + "\nUse the client photos. Pick the music from the scored candidates.\n")
        chk(lint_text(open(bf).read()) == [], "lint-brief: a brief with the current block and no bans passes")
        bad = rb.replace(h, "0" * 12) + "\nNo client photos this time. Run with OB_QC=0 and pick the music yourself. Use GrabCut for the cutout. Render to /Volumes/T7/OB-EDITS.\n"
        chk(len(lint_text(bad)) >= 6, f"lint-brief: stale hash + 5 bans caught ({len(lint_text(bad))} problems)")
        work_job = QR.load_job(work)
        code, o = call(cmd_gate, [work, clip]); print("    " + "\n    ".join(l for l in o.splitlines() if re.match(r"\s+(PASS|WARN|FAIL|SKIP|N/A)", l)))
        v = QR.verdict(clip); chk(v.get("words", {}).get("status") == "SKIP" and QR.runs(clip), "gate: run logged by sha256 (words SKIP: no script)")
        code, o = call(cmd_status, [work]); chk("missing" in o and "NEXT:" in o, "status lists missing items and the next command")
        code, o = call(cmd_finish, [work, clip])
        want = ["words FAIL: required for t-selftest", "record breakdown", "no reviewer verdict"]
        chk(code == 1 and all(w in o for w in want), "finish blocked with: required words, breakdown record, review")
        warns = [k for k, x in QR.verdict(clip).items() if x["status"] == "WARN"]
        chk(all(f"WARN {k} unanswered" in o for k in warns if QR.cfg('t-selftest')['warn_policy'].get(k, 'answer') == 'answer'), f"finish lists unanswered WARNs ({', '.join(warns) or 'none'})")
        print("    " + "\n    ".join(l for l in o.splitlines() if re.match(r"\s+\d+\.", l)))
        fails = [k for k, x in QR.verdict(clip).items() if x["status"] == "FAIL"]
        chk(not fails, f"no real FAIL on the clean synthetic clip ({', '.join(fails) or 'none'})")
        # satisfy every problem with planted files
        j = QR.load_job(work); j["declares"].update(script=None, no_script_why="selftest clip: a tone, no words"); json.dump(j, open(os.path.join(work, "job.json"), "w"))
        json.dump({k: f"selftest: checked {k} on the synthetic clip, expected for a flat tone" for k in warns}, open(os.path.join(work, "qc", "warn_answers.json"), "w"))
        open(os.path.join(work, "BREAKDOWN.md"), "w").write("# Breakdown\n1. 0-6 s flat colour, tone (selftest)\n")
        sh = QR.sha256(clip)
        QR._jdump({"sha256": sh, "file": clip, "verdict": "PASS", "when": datetime.datetime.now().isoformat(timespec="seconds"), "reviewer": "selftest", "summary": "planted"},
                  os.path.join(QR.state("reviews"), sh + ".json"))
        code, o = call(cmd_finish, [work, clip, "--to", "WP1 selftest"])
        dl = [l for l in o.splitlines() if l.startswith("DELIVERED: ")]
        dst = dl[-1].split(": ", 1)[1] if dl else ""
        chk(code == 0 and dst.startswith(env["OB_DELIVER_ROOT"]) and os.path.exists(dst) and QR.sha256(dst) == sh, f"finish delivers into the test root: {dst}")
        chk(os.path.exists(os.path.join(work, "DELIVERY.md")) and "DELIVERED" in open(env["OB_DELIVERIES_LOG"]).read() and f"sha256: {sh}" in open(env["OB_DELIVERIES_LOG"]).read(),
            "DELIVERY.md written; log line has sha256")
        if not (code == 0): print(o[-1500:])
        code, o = call(cmd_allow_send, [clip, "--why", "selftest"]); chk(clip in json.load(open(QR.state("allow_send.json"))), "allow-send records the file")
        _ = work_job
    except Exception:
        import traceback; traceback.print_exc(); ok = False
    finally:
        for k, v in old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
    print(f"(test files: {root})"); print("SELFTEST " + ("PASSED" if ok else "FAILED")); return ok


def cmd_pieces(a):
    """Record where each cut piece plays in FILE, for engines and build scripts that do not (edges and lip-sync need it)."""
    import json as _json
    import qc_gate as Q
    use = ("usage: ob_job.py pieces WORK FILE SEGS.json [--cam CAM.json]\n"
           "  SEGS.json  [[source file, start s, end s, where it plays in FILE s], ...]  one row per piece of his voice\n"
           "  CAM.json   [[camera file, start s, end s, where it plays in FILE s], ...]  when his voice comes from a separate mic")
    cam_p = a[a.index("--cam") + 1] if "--cam" in a and a.index("--cam") + 1 < len(a) else None
    pos = [x for i, x in enumerate(a) if x != "--cam" and not (i > 0 and a[i - 1] == "--cam")]
    if len(pos) != 3: die(use, 2)
    work, path, segs_p = os.path.abspath(os.path.expanduser(pos[0])), os.path.abspath(os.path.expanduser(pos[1])), os.path.expanduser(pos[2])
    if not os.path.isfile(path): die(f"no such file: {path}", 2)

    def rows(p, what):
        try: d = _json.load(open(p))
        except Exception as e: die(f"{what}: cannot read {p}: {e}", 2)
        ok = lambda r: isinstance(r, list) and len(r) == 4 and isinstance(r[0], str) and all(isinstance(x, (int, float)) for x in r[1:]) and r[2] > r[1]
        if not isinstance(d, list) or not d or not all(ok(r) for r in d):
            die(f"{what}: {p} must be a non-empty list of [file, start s, end s, where it plays s] rows with end after start", 2)
        gone = sorted({r[0] for r in d if not os.path.exists(os.path.expanduser(r[0]))})
        if gone: die(f"{what}: source not found: {gone[0]}", 2)
        return [(os.path.abspath(os.path.expanduser(r[0])), float(r[1]), float(r[2]), float(r[3])) for r in d]

    segs = rows(segs_p, "SEGS"); cam = rows(os.path.expanduser(cam_p), "CAM") if cam_p else None
    Q.record_pieces(path, segs, cam)
    print(f"recorded {len(segs)} pieces" + (f" and a camera map of {len(cam)} rows" if cam else " (no camera map: lip-sync cannot be measured for a separate mic)")
          + f" for {os.path.basename(path)}")
    print(f"next: python3 -I ~/ob-editor/bin/ob_job.py gate {work} {path}")


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); sys.exit(0 if a else 2)
    cmd, rest = a[0], a[1:]
    if cmd == "--selftest": sys.exit(0 if selftest() else 1)
    if cmd == "routes":
        for k, r in QR.routes().items(): print(f"{k:14s} {r.get('file', ''):24s} {r.get('title', '')}")
        return
    if cmd == "rules":
        if not rest: die("usage: ob_job.py rules ROUTE [--hash]", 2)
        b, h = rules_block(rest[0]); print(h if "--hash" in rest else b); return
    fn = {"start": cmd_start, "gate": cmd_gate, "status": cmd_status, "finish": cmd_finish, "allow-send": cmd_allow_send,
          "brief": cmd_brief, "lint-brief": cmd_lint, "pieces": cmd_pieces}.get(cmd)
    if not fn: print(__doc__); sys.exit(2)
    fn(rest)


if __name__ == "__main__":
    main()
