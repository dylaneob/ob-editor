#!/usr/bin/env python3
"""The route layer of the QC gate: fail-closed checks, run log, WARN answers, overrides, decision records and the reviewer's
verdict, all keyed by the file's SHA-256 (editor rebuild WP1, 2026-11-10; OB: "no more mistakes"). 59 of his notes were repeats;
nine came from checks that were blind, skipped or overridden: the gate SKIPped a check when its input was missing, a weaker re-run
overwrote a failing report (report laundering, AUDIT-ENGINES T6), WARNs shipped unread (T20), files reached the delivery folders by
hand (T7). This module closes those holes. Every number and every route's required checks come from ~/ob-editor/qc/formats.json.

  python3 -I qc_route.py verdict FILE              per check: the latest run in which it actually ran (SKIP never erases a result)
  python3 -I qc_route.py problems FILE [--work W]  everything that blocks delivery, one line each with what to do (exit 1 if any)
  python3 -I qc_route.py routes                    the routes in formats.json
  python3 -I qc_route.py --selftest                plants each hole and proves it is closed

Library: cfg(route), routes(), paths(), sha256(path), log_run(...), verdict(path), apply(R, route, job), apply_all(R, ctx),
warn_problems(v, work, route), record_problems(route, work, job), review(path), review_problem(path), delivery_problems(path, work).
Run log: qc/runs/<sha256>/<UTC>.json (the old qc/reports/<name>__<hash>.json is still written by qc_gate.save, unchanged).
Reviewer verdicts: qc/reviews/<sha256>.json, written by ~/.claude/hooks/ob_editor_hooks.py when the video-reviewer agent ends.
Tests may point the state folders (runs, reviews, jobs, sha cache, allow_send) at a temp dir with OB_QC_STATE, formats.json with
OB_FORMATS, the deliver roots with OB_DELIVER_ROOT and the delivery log with OB_DELIVERIES_LOG.
"""
import datetime, glob, hashlib, importlib, json, os, re, sys, time

BIN = os.path.dirname(os.path.abspath(__file__)); QC = os.path.join(os.path.dirname(BIN), "qc")
if BIN not in sys.path: sys.path.insert(0, BIN)
PLUGINS = ("qc_audio", "qc_assets", "qc_look")
RECORD_MODULE = {"music": "qc_audio", "sfx": "qc_audio", "audio_manifest": "qc_audio", "assets": "qc_assets"}
NOT_RUN = ("SKIP", "N/A")
WHAT = {   # what to pass so a required check runs (strict mode's FAIL line)
    "words": "a script (ob_job.py start ... --script FILE, or --no-script \"why\")",
    "edges": "the render's pieces (after_render segs=, or a cut list in WORK) so every splice is checked",
    "lookoff": "camera pieces: WORK/pieces.json plus the camera (ob_job.py start ... --camera FILE)",
    "clients": "the WORK folder with events_resolved.json (ob_job.py gate WORK FILE)",
    "opener": "the WORK folder with events_resolved.json (ob_job.py gate WORK FILE)",
    "sfx": "story/sfx_plan.json in WORK (or start the job with --sfx none)",
    "bank": "story/sfx_plan.json or the music (audio/manifest.json, story/score*.json)",
    "lipsync": "the camera map the render recorded (after_render cam=), or declare separate_mic false in job.json",
    "captions": "a file under 5 minutes (the gate skips captions on long files)",
    "hook": "a file under 5 minutes (the gate skips the hook on long files)",
    "silence": "a portrait file (landscape files skip silence)",
}


def state(key):
    """runs | reviews | jobs | cache | allow_send.json: under OB_QC_STATE when set (tests), else the real qc folder."""
    root = os.environ.get("OB_QC_STATE")
    if root: return os.path.join(root, key)
    return paths().get(key) or os.path.join(QC, key)


def load():
    return json.load(open(os.environ.get("OB_FORMATS") or os.path.join(QC, "formats.json")))


def _merge(a, b):
    out = dict(a)
    for k, v in b.items(): out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def routes():
    return {k: v for k, v in load()["routes"].items() if not k.startswith("_")}


def cfg(route):
    """The route's settings merged over `defaults`. defaults.records (record -> file) is kept as `record_files`;
    the route's `records` (the list it requires) wins under `records`."""
    F = load(); d = dict(F["defaults"]); rf = d.pop("records", {})
    r = F["routes"].get(route)
    if r is None: raise KeyError(f"unknown route {route!r}: one of {', '.join(routes())}")
    c = _merge(d, {k: v for k, v in r.items() if not (isinstance(d.get(k), dict) and not isinstance(v, dict))})
    for k, v in r.items():   # a route's "music": "bed" / "sfx": "plan" is a mode; the defaults' dict of numbers stays under the name
        if isinstance(d.get(k), dict) and not isinstance(v, dict): c[k + "_mode"] = v
    c["record_files"] = rf; c["records"] = list(r.get("records", [])); c["required"] = list(r.get("required", []))
    c["na"] = dict(r.get("na", {})); c["route"] = route; c["enforce"] = F.get("enforce", {}); return c


def paths():
    p = {k: (os.path.expanduser(v) if isinstance(v, str) else [os.path.expanduser(x) for x in v] if isinstance(v, list) else v)
         for k, v in load()["paths"].items() if not k.startswith("_")}
    if os.environ.get("OB_DELIVER_ROOT"): p["deliver_roots"] = [os.path.expanduser(os.environ["OB_DELIVER_ROOT"])]
    return p


def log_path():
    return os.environ.get("OB_DELIVERIES_LOG") or os.path.join(QC, "deliveries.log")


def _jdump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"; json.dump(obj, open(tmp, "w"), indent=1); os.replace(tmp, path)


def _jload(path, default=None):
    try: return json.load(open(path))
    except (OSError, ValueError): return default


# ---------- file identity ----------
def sha256(path):
    """SHA-256 of the file, cached by (absolute path, size, mtime) in qc/cache/sha256.json."""
    ap = os.path.abspath(path); st = os.stat(ap); cp = os.path.join(state("cache"), "sha256.json")
    c = _jload(cp, {}) or {}; hit = c.get(ap)
    if hit and hit[0] == st.st_size and abs(hit[1] - st.st_mtime) < 1e-6: return hit[2]
    h = hashlib.sha256()
    with open(ap, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    c = _jload(cp, {}) or {}; c[ap] = [st.st_size, st.st_mtime, h.hexdigest()]
    try: _jdump(c, cp)
    except OSError: pass
    return h.hexdigest()


# ---------- run log (T6: no laundering) ----------
def log_run(path, R, inputs=None, job=None, route=None):
    """Append this gate run to qc/runs/<sha256>/<UTC>.json with its checks and the inputs it was given. Never overwrites."""
    sh = sha256(path); now = datetime.datetime.now(datetime.timezone.utc)
    d = {"file": os.path.abspath(path), "sha256": sh, "size": os.path.getsize(path), "mtime": os.path.getmtime(path),
         "when": now.isoformat(timespec="seconds"), "t": now.timestamp(), "cwd": os.getcwd(), "pid": os.getpid(),
         "route": route or (job or {}).get("route"), "job": (job or {}).get("name"), "work": (inputs or {}).get("work") or (job or {}).get("work"),
         "inputs": inputs or {}, "checks": {k: {"status": s, "detail": str(dd)} for k, (s, dd) in R.items()}}
    p = os.path.join(state("runs"), sh, now.strftime("%Y%m%dT%H%M%S.%fZ") + ".json"); _jdump(d, p); return p


def runs(path=None, sh=None):
    sh = sh or sha256(path)
    return [x for x in (_jload(f) for f in sorted(glob.glob(os.path.join(state("runs"), sh, "*.json")))) if x]


def _ran(name, row):
    """A row counts as the check having run: not SKIP/N/A, and not a row the route layer itself wrote (strict FAIL, route, declares)."""
    return row["status"] not in NOT_RUN and name not in ("route", "declares") and not str(row.get("detail", "")).startswith("required for ")


def verdict(path=None, sh=None):
    """{check: {status, detail, when, t}}: for each check, the latest run in which it actually ran. A later run with fewer inputs
    (SKIP) can neither erase a FAIL nor a PASS; a check that never ran is SKIP."""
    out = {}
    for r in runs(path, sh):
        for k, row in r["checks"].items():
            if _ran(k, row): out[k] = dict(status=row["status"], detail=row["detail"], when=r["when"], t=r["t"])
            elif k not in out and k not in ("route", "declares"): out[k] = dict(status="SKIP", detail=row["detail"], when=r["when"], t=r["t"])
    return out


# ---------- jobs ----------
def load_job(work):
    return _jload(os.path.join(work, "job.json")) if work else None


def find_job(path, work=None):
    """(job, work) for a file: --work first; else the newest logged run of this exact file that named a WORK; else a job whose
    WORK holds the file. (None, None) = a legacy file with no job."""
    if work: return load_job(work), work
    try:
        for r in reversed(runs(path)):
            if r.get("work") and load_job(r["work"]): return load_job(r["work"]), r["work"]
    except OSError: pass
    ap = os.path.abspath(path)
    for f in glob.glob(os.path.join(state("jobs"), "*.json")):
        w = (_jload(f) or {}).get("work")
        if w and ap.startswith(os.path.abspath(w) + os.sep) and load_job(w): return load_job(w), w
    return None, None


OB_QUOTE = re.compile(r"\bOB\b\s*(?:\d{1,2}[-/]\d{1,2}\s*)?(?::|[\"“])\s*\S")


def declaration_problems(route, job):
    """A declaration the route forbids: music none on a route with a bed, or no sound effects on a route that plans them,
    without OB's own words ("OB: ...") in the why."""
    c = cfg(route); d = (job or {}).get("declares", {}); out = []
    if d.get("music") == "none" and c.get("music_mode") == "bed" and not OB_QUOTE.search(str(d.get("music_none_why") or "")):
        out.append(f"music declared none but {route} runs a bed: start with --music-none-why \"OB: <his words>\" or give it music")
    if d.get("sfx") == "none" and c.get("sfx_mode") == "plan" and not OB_QUOTE.search(str(d.get("sfx_none_why") or "")):
        out.append(f"sfx declared none but {route} plans sound effects: add sfx_none_why \"OB: <his words>\" to job.json declares or write story/sfx_plan.json")
    if "script" in d and d["script"] is None and not str(d.get("no_script_why") or "").strip():
        out.append("no script declared without no_script_why: start with --no-script \"why\"")
    return out


def declared_away(check, job, route):
    """The reason a job declared this check away, or None."""
    d = (job or {}).get("declares", {}); c = cfg(route)
    if check == "words" and "script" in d and d["script"] is None and str(d.get("no_script_why") or "").strip(): return f"no script: {d['no_script_why']}"
    sfx_none = d.get("sfx") == "none" and (c.get("sfx_mode") != "plan" or OB_QUOTE.search(str(d.get("sfx_none_why") or "")))
    music_none = d.get("music") == "none" and (c.get("music_mode") != "bed" or OB_QUOTE.search(str(d.get("music_none_why") or "")))
    if check == "sfx" and sfx_none: return "declared: no sound effects in this edit"
    if check == "bank" and sfx_none and music_none: return "declared: no music and no sound effects"
    if check == "lipsync" and d.get("separate_mic") is False: return "declared: one camera, no separate mic"
    return None


def apply(R, route, job=None):
    """Strict mode: a required check that SKIPped (or never ran) is a FAIL that says what to pass, unless the route's `na`
    names it (N/A with its reason) or the job declared it away with an allowed reason. A forbidden declaration is a FAIL row."""
    c = cfg(route); R = dict(R)
    for k in c["required"]:
        st = R.get(k, ("SKIP", "never ran"))[0]
        if st not in ("SKIP",): continue
        if k in c["na"]: R[k] = ("N/A", c["na"][k]); continue
        why = declared_away(k, job, route)
        prev = str(R.get(k, ("", "never ran"))[1])
        R[k] = ("N/A", why) if why else ("FAIL", prev if prev.startswith("required for ") else f"required for {route}: pass {WHAT.get(k, 'the input this check needs')} ({prev})")
    for k in c["na"]:
        if R.get(k, ("SKIP",))[0] == "SKIP": R[k] = ("N/A", c["na"][k])
    dp = declaration_problems(route, job)
    if dp: R["declares"] = ("FAIL", "; ".join(dp))
    return R


def _plugin(name):
    """The plug-in module, None when it is not installed. Any other import error is raised (a crash is a FAIL, never silence)."""
    try: return importlib.import_module(name)
    except ModuleNotFoundError as e:
        if e.name == name: return None
        raise


def apply_all(R, ctx):
    """Called at the end of qc_gate.gate(). No route (older engines, other tabs): unchanged but one row `route SKIP`.
    With a route: the plug-in checks (qc_audio, qc_assets, qc_look) when installed, then strict mode."""
    route, job = ctx.get("route"), ctx.get("job")
    if not route: R["route"] = ("SKIP", "no job (legacy render)"); return R
    if route not in routes(): R["route"] = ("FAIL", f"unknown route {route!r}: python3 -I ~/ob-editor/bin/qc_route.py routes"); return R
    ctx = dict(ctx); ctx.setdefault("cfg", cfg(route)); ctx.setdefault("sha256", sha256(ctx["path"])); ctx.setdefault("report", dict(R))
    for name in PLUGINS:
        try:
            m = _plugin(name)
            if m is None or not hasattr(m, "run"): continue
            for k, v in (m.run(ctx) or {}).items(): R[k] = (str(v[0]), str(v[1]))
        except Exception as e: R[name] = ("FAIL", f"{name}.run crashed: {e!r} (fix the plug-in, then re-gate)")
    R = apply(R, route, job)
    R["route"] = ("PASS", f"{route}, job {(job or {}).get('name', '?')}: strict (required SKIP = FAIL)")
    return R


# ---------- WARN answers (T20) ----------
def warn_problems(v, work, route):
    """Every WARN whose policy is `answer` needs a non-empty line under its check in WORK/qc/warn_answers.json, written after the
    run that raised it. An answer is a string (dated by the file's mtime) or {"answer": ..., "when": ISO time}."""
    c = cfg(route)
    if not c["enforce"].get("warn_answers_required", True): return []
    pol = c.get("warn_policy", {}); f = os.path.join(work or "", c["record_files"].get("warn_answers", "qc/warn_answers.json"))
    ans = _jload(f, {}) if work and os.path.exists(f) else {}; fm = os.path.getmtime(f) if work and os.path.exists(f) else 0
    out = []
    for k, x in v.items():
        if x["status"] != "WARN" or pol.get(k, pol.get("default", "answer")) != "answer": continue
        a = (ans or {}).get(k); text, when = (a, fm) if isinstance(a, str) else ((a or {}).get("answer"), (a or {}).get("when")) if isinstance(a, dict) else (None, 0)
        if isinstance(when, str):
            try: when = datetime.datetime.fromisoformat(when).timestamp()
            except ValueError: when = 0
        when = when or fm
        if not str(text or "").strip():
            out.append(f"WARN {k} unanswered ({str(x['detail'])[:110]}): write what you checked under \"{k}\" in {f}")
        elif when < x["t"]:
            out.append(f"WARN {k} answer is stale (written before the run that raised it): re-check and rewrite \"{k}\" in {f}")
    return out


# ---------- overrides ----------
def overrides(work):
    return (_jload(os.path.join(work, "qc", "gate_overrides.json"), {}) or {}) if work else {}


def override_ok(e):
    """(ok, why): a FAIL is overridden only with OB's own words (ob_words) or proof (the frame or time showing the check is wrong)."""
    if not isinstance(e, dict): return False, "an override must be {\"why\", \"ob_words\" or \"proof\", \"date\"}"
    if str(e.get("ob_words") or "").strip() or str(e.get("proof") or "").strip(): return True, str(e.get("ob_words") or e.get("proof"))
    return False, "needs ob_words (OB's own words) or proof (the frame or time that shows the check is wrong on this file)"


def log_line(kind, path, *parts):
    """One line in qc/deliveries.log with the file's absolute path, sha256 and size."""
    ap = os.path.abspath(path)
    try: sh, sz = sha256(ap), os.path.getsize(ap)
    except OSError: sh, sz = "?", 0
    line = "\t".join([datetime.datetime.now().isoformat(timespec="seconds"), kind, ap, *[str(p) for p in parts], f"sha256: {sh}", f"size: {sz}"])
    with open(log_path(), "a") as f: f.write(line + "\n")


# ---------- decision records ----------
def _script_of(work, job):
    s = ((job or {}).get("inputs") or {}).get("script")
    for p in [s] + [os.path.join(work, x) for x in ("script.txt", "script.json", "story/script.txt")]:
        if p and os.path.exists(p): return p
    return None


def _rows(d, key):
    return d if isinstance(d, list) else (d or {}).get(key, []) if isinstance(d, dict) else []


def record_problems(route, work, job=None):
    """The route's `records`: each decision file must exist in WORK and pass. breakdown, format_check, react_windows and
    warn_answers are checked here; music, sfx and audio_manifest by qc_audio, assets by qc_assets (FAIL when not installed)."""
    c = cfg(route); rf = c["record_files"]; out = []; mods = []
    if not work or not os.path.isdir(work): return [f"no WORK folder for the records ({', '.join(c['records'])}): pass --work WORK"] if c["records"] else []
    d = (job or {}).get("declares", {})
    music_none = d.get("music") == "none" and (c.get("music_mode") != "bed" or OB_QUOTE.search(str(d.get("music_none_why") or "")))
    for rec in c["records"]:
        if rec == "music" and music_none: continue
        if rec == "sfx" and declared_away("sfx", job, route): continue
        if rec in RECORD_MODULE:
            if RECORD_MODULE[rec] not in mods: mods.append(RECORD_MODULE[rec])
            continue
        f = os.path.join(work, rf.get(rec, rec))
        try:
            if rec == "breakdown":
                sc = _script_of(work, job)
                if not os.path.exists(f) or os.path.getsize(f) == 0: out.append(f"record breakdown: write {f} (shot by shot, real stills) and have a fresh agent check it")
                elif sc and os.path.getmtime(f) < os.path.getmtime(sc): out.append(f"record breakdown: {f} is older than the script {sc}: update it")
            elif rec == "format_check":
                d = _jload(f)
                if d is None: out.append(f"record format_check: write {f} (rows of ours / reference / ok from the creator's measured numbers)"); continue
                rows = _rows(d, "rows")
                if not rows: out.append(f"record format_check: {f} has no rows")
                for i, r in enumerate(rows):
                    miss = [k for k in ("ours", "reference", "ok") if not isinstance(r, dict) or k not in r]
                    if miss: out.append(f"record format_check: row {i + 1} lacks {', '.join(miss)} in {f}")
                    elif r["ok"] is not True: out.append(f"record format_check: row {i + 1} ({r.get('what', '?')}) is not ok: ours {r['ours']} vs reference {r['reference']}")
            elif rec == "react_windows":
                d = _jload(f)
                if d is None: out.append(f"record react_windows: write {f} (each window picked by react_window_audit.py: method sound_match, frame_sheet, reacts true)"); continue
                ws = _rows(d, "windows")
                if not ws: out.append(f"record react_windows: {f} has no windows")
                for i, w in enumerate(ws):
                    w = w if isinstance(w, dict) else {}; fs = w.get("frame_sheet")
                    if w.get("method") != "sound_match": out.append(f"record react_windows: window {i + 1} method is {w.get('method')!r}, not sound_match: pick it with react_window_audit.py")
                    if not fs or not os.path.exists(fs if os.path.isabs(str(fs)) else os.path.join(work, str(fs))): out.append(f"record react_windows: window {i + 1} frame_sheet {fs!r} not found: make it (frame_sheet.py) and look at it")
                    if w.get("reacts") is not True: out.append(f"record react_windows: window {i + 1} reacts is not true: he must be visibly watching")
            elif rec == "warn_answers":
                if os.path.exists(f) and not isinstance(_jload(f), dict): out.append(f"record warn_answers: {f} is not a JSON object {{check: answer}}")
            else: out.append(f"record {rec}: no checker for it in qc_route.py")
        except Exception as e: out.append(f"record {rec}: check crashed: {e!r}")
    for name in mods:
        try:
            m = _plugin(name)
            if m is None or not hasattr(m, "record_problems"):
                out.append(f"record {'/'.join(r for r in c['records'] if RECORD_MODULE.get(r) == name)}: {name} not installed (needs ~/ob-editor/bin/{name}.py)"); continue
            out += [f"record ({name}): {p}" for p in (m.record_problems(route, work, job) or [])]
        except Exception as e: out.append(f"record ({name}): record_problems crashed: {e!r}")
    return out


# ---------- the reviewer's verdict ----------
def review(path=None, sh=None):
    return _jload(os.path.join(state("reviews"), (sh or sha256(path)) + ".json"))


def review_problem(path):
    sh = sha256(path); r = review(sh=sh)
    run = f"run the video-reviewer agent on {os.path.abspath(path)} (its last message needs VERDICT:, FILE: and SHA256: lines)"
    if not r: return f"no reviewer verdict for this exact file (sha256 {sh[:12]}): {run}"
    if str(r.get("verdict")).upper() != "PASS": return f"the reviewer said {r.get('verdict')} ({str(r.get('summary', ''))[:120]}): fix what it flagged, re-render, re-gate, {run}"
    try: when = datetime.datetime.fromisoformat(str(r.get("when"))).timestamp()
    except ValueError: when = 0
    if when < os.path.getmtime(path) - 1: return f"the reviewer's PASS ({r.get('when')}) is older than the file: {run}"
    return None


# ---------- delivery ----------
def legacy_open(now=None):
    until = load().get("enforce", {}).get("legacy_until")
    return bool(until) and (now or datetime.date.today()) <= datetime.date.fromisoformat(until)


def report(path, work=None, use_overrides=True, now=None):
    """{problems, overrides_used, job, work, route, sha256, verdict}. problems = strict FAILs + required SKIPs + unanswered WARNs +
    record problems + the review problem (+ "no job" once legacy deliveries end)."""
    job, work = find_job(path, work); route = (job or {}).get("route"); sh = sha256(path); v = verdict(sh=sh)
    out = dict(problems=[], overrides_used=[], job=job, work=work, route=route, sha256=sh, verdict=v)
    P = out["problems"]
    if not v: P.append(f"no gate run logged for this exact file (sha256 {sh[:12]}): python3 -I ~/ob-editor/bin/ob_job.py gate WORK {os.path.abspath(path)}")
    R = {k: (x["status"], x["detail"]) for k, x in v.items()}
    if route:
        if route not in routes(): P.append(f"job route {route!r} is not in formats.json"); return out
        R = apply(R, route, job)
    ov = overrides(work)
    for k, (s, d) in R.items():
        if s != "FAIL": continue
        if use_overrides and k in ov:
            ok, why = override_ok(ov[k])
            if ok: out["overrides_used"].append((k, why)); continue
            P.append(f"{k}: override refused: {why} (WORK/qc/gate_overrides.json)"); continue
        P.append(f"{k} FAIL: {str(d)[:160]} -> fix it, re-render, then ob_job.py gate WORK FILE")
    if route:
        P += warn_problems(v, work, route)
        P += record_problems(route, work, job)
    if load().get("enforce", {}).get("review_required", True):
        rp = review_problem(path)
        if rp: P.append(rp)
    if not job and not legacy_open(now):
        P.append(f"no job for this file and legacy deliveries ended {load()['enforce'].get('legacy_until')}: "
                 "python3 -I ~/ob-editor/bin/ob_job.py start ROUTE WORK, gate it, then ob_job.py finish WORK FILE")
    return out


def delivery_problems(path, work=None, use_overrides=True, now=None):
    """The one list deliver.py, ob_job.py finish and the send hook read. Empty = clear to deliver."""
    return report(path, work, use_overrides, now)["problems"]


# ---------- selftest ----------
def selftest():
    ok = True; root = os.path.expanduser("~/ob-scratch/skill-rebuild/wp1/qc_route_selftest_" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(root, exist_ok=True); old = {k: os.environ.get(k) for k in ("OB_QC_STATE", "OB_FORMATS", "OB_DELIVERIES_LOG")}
    os.environ["OB_QC_STATE"] = os.path.join(root, "state"); os.environ["OB_DELIVERIES_LOG"] = os.path.join(root, "deliveries.log")
    F = json.load(open(os.path.join(QC, "formats.json")))
    F["routes"]["t-route"] = {"title": "selftest", "file": "x.md", "long": False, "music": "bed", "sfx": "plan",
                              "required": ["format", "words", "clients", "hook", "sfx"], "na": {"hook": "clip plays from frame 1"},
                              "records": ["breakdown", "warn_answers"]}
    F["routes"]["t-music"] = dict(F["routes"]["t-route"], records=["music"], required=["format"])
    F["enforce"]["review_required"] = True
    fp = os.path.join(root, "formats.json"); json.dump(F, open(fp, "w")); os.environ["OB_FORMATS"] = fp
    def chk(good, what):
        nonlocal ok; ok &= bool(good); print(f"  {'ok ' if good else 'BAD'} {what}")
    try:
        work = os.path.join(root, "WORK"); os.makedirs(os.path.join(work, "qc")); vid = os.path.join(work, "cut.mp4")
        open(vid, "wb").write(b"not a real video, a stand-in with fixed bytes")
        job = {"name": "t1", "route": "t-route", "work": work, "declares": {}, "inputs": {}}; json.dump(job, open(os.path.join(work, "job.json"), "w"))
        # strict mode
        R = apply({"format": ("PASS", "ok"), "words": ("SKIP", "no --script"), "hook": ("SKIP", "skipped"), "sfx": ("SKIP", "no plan")}, "t-route", job)
        chk(R["words"][0] == "FAIL" and "required for t-route" in R["words"][1], "required SKIP (words) -> FAIL saying what to pass")
        chk(R["clients"][0] == "FAIL", "required check that never ran (clients) -> FAIL")
        chk(R["hook"][0] == "N/A", "route `na` (hook) -> N/A, not FAIL")
        j2 = dict(job, declares={"script": None, "no_script_why": "FDOE: numbers only", "sfx": "none", "sfx_none_why": "OB 11-09: \"no sound effects on this one\""})
        R2 = apply({"words": ("SKIP", ""), "sfx": ("SKIP", "")}, "t-route", j2)
        chk(R2["words"][0] == "N/A" and R2["sfx"][0] == "N/A" and "declares" not in R2, "declared away with allowed reasons -> N/A")
        R3 = apply({}, "t-route", dict(job, declares={"music": "none", "music_none_why": "felt like it"}))
        chk(R3.get("declares", ("",))[0] == "FAIL", "music none on a bed route without OB's words -> FAIL")
        R4 = apply({}, "t-route", dict(job, declares={"music": "none", "music_none_why": "OB: \"do no background music i will find a good version\""}))
        chk("declares" not in R4, "music none quoting OB -> allowed")
        # laundering
        log_run(vid, {"clients": ("FAIL", "no client proof at 12.0s"), "format": ("PASS", "ok")}, {"work": work}, job)
        time.sleep(0.01); log_run(vid, {"clients": ("SKIP", "needs --work"), "format": ("PASS", "ok")}, {}, None)
        chk(verdict(vid)["clients"]["status"] == "FAIL", "run A FAILs clients, run B without work SKIPs it -> verdict still FAIL")
        time.sleep(0.01); log_run(vid, {"clients": ("PASS", "proof on screen"), "format": ("PASS", "ok")}, {"work": work}, job)
        chk(verdict(vid)["clients"]["status"] == "PASS", "run C with work PASSes -> PASS")
        time.sleep(0.01); log_run(vid, {"clients": ("SKIP", "x"), "format": ("SKIP", "x")}, {}, None)
        chk(verdict(vid)["clients"]["status"] == "PASS", "a later SKIP cannot erase a PASS either")
        # WARN answers
        time.sleep(0.01); log_run(vid, {"hook": ("WARN", "11 words in the first 3 s"), "size": ("WARN", "40 MB")}, {"work": work}, job)
        v = verdict(vid); wp = warn_problems(v, work, "t-route")
        chk(any("hook unanswered" in p for p in wp) and not any(" size " in p for p in wp), "unanswered WARN (hook) blocks; info WARN (size) does not")
        af = os.path.join(work, "qc", "warn_answers.json"); json.dump({"hook": "counted on frame: 9 words, OCR split one"}, open(af, "w"))
        chk(warn_problems(verdict(vid), work, "t-route") == [], "answered WARN passes")
        os.utime(af, (time.time() - 3600, time.time() - 3600))
        chk(any("stale" in p for p in warn_problems(verdict(vid), work, "t-route")), "an answer older than the run that raised the WARN blocks (stale)")
        os.utime(af, None)
        # overrides
        log_run(vid, {"format": ("FAIL", "1080x1350")}, {"work": work}, job)
        json.dump({"format": {"why": "looks fine to me", "date": "2026-11-10"}}, open(os.path.join(work, "qc", "gate_overrides.json"), "w"))
        rp = report(vid, work)
        chk(any("override refused" in p for p in rp["problems"]), "override without OB's words or proof is refused")
        json.dump({"format": {"why": "4:5 feed post", "ob_words": "make this one 4:5 for the feed", "date": "2026-11-10"}}, open(os.path.join(work, "qc", "gate_overrides.json"), "w"))
        rp = report(vid, work)
        chk(not any(p.startswith("format") for p in rp["problems"]) and rp["overrides_used"], "override with OB's words is accepted (and reported for the log)")
        # records
        chk(any("record breakdown" in p for p in rp["problems"]), "missing BREAKDOWN.md blocks (record)")
        rm = record_problems("t-music", work, job)
        chk(any("qc_audio" in p for p in rm) if _plugin("qc_audio") is None else True, "a required record handled by a missing module -> 'not installed'")
        # review
        chk(any("no reviewer verdict" in p for p in rp["problems"]), "review missing blocks")
        sh = sha256(vid); rv = os.path.join(state("reviews"), sh + ".json")
        _jdump({"sha256": sh, "file": vid, "verdict": "FAIL", "when": datetime.datetime.now().isoformat(timespec="seconds"), "summary": "music too loud"}, rv)
        chk("said FAIL" in (review_problem(vid) or ""), "review FAIL blocks")
        _jdump({"sha256": sh, "file": vid, "verdict": "PASS", "when": "2020-01-01T00:00:00"}, rv)
        chk("older than the file" in (review_problem(vid) or ""), "review PASS older than the file blocks")
        _jdump({"sha256": sh, "file": vid, "verdict": "PASS", "when": datetime.datetime.now().isoformat(timespec="seconds")}, rv)
        chk(review_problem(vid) is None, "fresh review PASS for this hash clears")
        # legacy
        lv = os.path.join(root, "legacy.mp4"); open(lv, "wb").write(b"legacy render bytes")
        until = datetime.date.fromisoformat(F["enforce"]["legacy_until"])
        before = report(lv, now=until)["problems"]; after = report(lv, now=until + datetime.timedelta(days=1))["problems"]
        chk(not any("legacy deliveries ended" in p for p in before) and any("legacy deliveries ended" in p for p in after),
            "legacy file: allowed on legacy_until, refused the day after")
        R5 = apply_all({"format": ("PASS", "")}, {"path": lv})
        chk(R5 == {"format": ("PASS", ""), "route": ("SKIP", "no job (legacy render)")}, "gate without a route: unchanged except `route SKIP`")
        chk(find_job(vid)[1] == work, "a file's job is found from its logged runs")
        print("  -- drift test: not built (scope cut 11-10); see reports/WP1.md")
    except Exception as e:
        import traceback; traceback.print_exc(); ok = False
    finally:
        for k, v in old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    return ok


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); sys.exit(0 if a else 2)
    if a[0] == "--selftest": sys.exit(0 if selftest() else 1)
    if a[0] == "routes":
        for k, r in routes().items(): print(f"{k:14s} {r.get('file', ''):24s} {r.get('title', '')}")
        return
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    if a[0] == "verdict" and len(a) > 1:
        v = verdict(a[1]); job, work = find_job(a[1])
        print(f"{os.path.basename(a[1])}  sha256 {sha256(a[1])[:12]}  route {(job or {}).get('route', '- (legacy)')}  runs {len(runs(a[1]))}")
        for k, x in v.items(): print(f"  {x['status']:4s} {k:10s} {str(x['detail'])[:110]}  ({x['when']})")
        return
    if a[0] == "problems" and len(a) > 1:
        r = report(a[1], opt("--work"))
        for k, why in r["overrides_used"]: print(f"OVERRIDE {k}: {why}")
        for i, p in enumerate(r["problems"], 1): print(f"{i}. {p}")
        if not r["problems"]: print(f"CLEAR: {os.path.basename(a[1])} has no delivery problems")
        sys.exit(1 if r["problems"] else 0)
    print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
