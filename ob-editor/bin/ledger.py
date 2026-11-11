#!/usr/bin/env python3
"""The mistakes ledger (~/ob-editor/qc/mistakes.json): every note OB gave on an edit, the rule it became and what enforces it
(editor rebuild WP1, 2026-11-10; OB: "no more mistakes", and the standing rule "Any note OB gives twice goes into the checklist or
the QC gate the same day"). New fields, old ones kept so qc_gate.show() still works:
  status       active | superseded | merged
  superseded_by  the newer rule or OB's newer words
  routes       ["all"] or route names from qc/formats.json
  enforcer     ["gate:<check>", "record:<name>", "review:R<nn>", "hook:<name>", "engine:<file>", "route:<file>" (prose only)]

  python3 -I ledger.py add --said "OB's words" --date YYYY-MM-DD --rule "..." --check NAME|manual --routes a,b --enforcer gate:x[,review:R10]
  python3 -I ledger.py supersede M24 --by "OB 11-09 'just do what i tell you'"
  python3 -I ledger.py list [--route R] [--active]
  python3 -I ledger.py coverage      active rules by enforcer type; exit 1 if an active rule has no enforcer
  python3 -I ledger.py migrate       one-off (11-10): fill status, routes, enforcer for the existing entries (backs up first)
Every write backs the ledger up first as mistakes.json.bak-<date>-<what>.
"""
import datetime, json, os, re, shutil, sys

BIN = os.path.dirname(os.path.abspath(__file__)); QC = os.path.join(os.path.dirname(BIN), "qc")
LEDGER = os.environ.get("OB_LEDGER") or os.path.join(QC, "mistakes.json")
CHECKLIST = os.path.join(QC, "REVIEW-CHECKLIST.md")
GATE_CHECKS = ("format", "size", "cues", "words", "silence", "edges", "audio", "motion", "text_face", "text_lint", "text_safe", "hook",
               "captions", "lookoff", "clients", "sfx", "bank", "opener", "lipsync", "vmaf")
KINDS = ("gate", "record", "review", "hook", "engine", "route")
SHORT = ["reel-talking", "reel-graphics", "reel-lists", "reel-reaction", "reel-fdoe", "reel-lecture", "yt-clips", "repost-trials", "ad", "mock"]
REACT = ["reel-reaction", "reel-fdoe", "long-form"]

# migrate (11-10): routes and extra enforcers per rule, from the rule text and AUDIT-MISTAKES section 1
ROUTES = {"M08": SHORT, "M10": SHORT, "M12": SHORT, "M14": ["repost-trials"], "M29": ["reel-lists"], "M31": REACT, "M33": ["yt-clips"],
          "M34": ["reel-reaction", "reel-fdoe"], "M35": ["long-form"], "M39": REACT, "M40": ["reel-talking", "reel-graphics", "reel-reaction"],
          "M42": ["reel-reaction", "reel-fdoe"], "M43": ["reel-reaction", "reel-fdoe"], "M47": REACT, "M50": ["reel-reaction", "reel-fdoe"],
          "M51": REACT, "M53": ["long-form"], "M54": ["long-form"]}
EXTRA = {"M16": ["record:assets"], "M20": ["record:music"], "M21": ["record:assets"], "M22": ["record:assets"], "M28": ["record:assets"],
         "M34": ["record:react_windows"], "M57": ["record:music"], "M17": ["record:sfx"], "M59": ["record:sfx"], "M58": ["record:music"],
         "M45": ["engine:deliver.py"], "M53": ["route:routes/long-form.md"], "M32": ["route:subjects/tools.md"], "M33": ["route:routes/yt-clips.md"],
         "M41": ["route:subjects/proof-clients.md"], "M52": ["route:subjects/graphics.md"], "M40": ["route:routes/short-form.md"],
         "M43": ["route:routes/fdoe.md"], "M39": ["review:R07", "route:routes/reaction.md"], "M46": ["route:subjects/tools.md"], "M51": ["route:routes/reaction.md"]}
SUPERSEDE = {"M24": "OB 11-09 'just do what i tell you': no approval hold; the breakdown is written to WORK (record:breakdown) and checked by a fresh agent before the full render",
             "M54": "OB 11-09 'just do what i tell you': the editor picks music from 3+ scored candidates (record:music, M57/M58), runner-ups named at delivery",
             "M30": "OB 11-07/11-09: M57 (upbeat bed) + M58 (bank first) + 3+ scored candidates (record:music); Lane A/B retired",
             "M19": "M56 (OB 11-07 'when i say clients you are suppose to put clients on screen for proof')"}
MERGED = {"M15": "M01"}


def load():
    return json.load(open(LEDGER))


def save(d, what):
    bak = f"{LEDGER}.bak-{datetime.date.today().isoformat()}-{what}"
    if not os.path.exists(bak): shutil.copy2(LEDGER, bak)
    tmp = LEDGER + ".tmp"; json.dump(d, open(tmp, "w"), indent=1, ensure_ascii=False); os.replace(tmp, LEDGER); return bak


def is_active(m): return m.get("status", "active") == "active"


def for_route(m, route): return route is None or "all" in m.get("routes", ["all"]) or route in m.get("routes", [])


def active(route=None):
    return [m for m in load()["mistakes"] if is_active(m) and for_route(m, route)]


def rule_line(m, width=118, enf_max=9):
    e = m.get("enforcer") or [m.get("check", "?")]; enf = ",".join(e[:enf_max]) + ("+" if len(e) > enf_max else "")
    s = f"{m['id']} {m['rule']}"
    return (s if len(s) <= width else s[:width - 1].rstrip() + "…") + f" [{enf}]"


def checklist_map():
    """{M##: [R##, ...]} from the reviewer checklist lines '- R07 ... (M34, M47)'."""
    out = {}
    try: lines = open(CHECKLIST).read().splitlines()
    except OSError: return out
    for l in lines:
        r = re.match(r"\s*-\s*(R\d\d)\b", l)
        if r:
            for m in re.findall(r"\bM\d\d\b", l): out.setdefault(m, []).append(r.group(1))
    return out


def enforcers_for(m, cm):
    chk = str(m.get("check", "")); e = []
    if chk.startswith("engine:"): e.append("engine:" + chk.split(":", 1)[1].strip().split()[0])
    else: e += [f"gate:{c}" for c in GATE_CHECKS if re.search(rf"\b{c}\b", chk)]
    if chk == "first3": e.append("engine:first3_check.py")
    e += EXTRA.get(m["id"], []); e += [f"review:{r}" for r in cm.get(m["id"], [])]
    return list(dict.fromkeys(e))


def migrate():
    d = load(); cm = checklist_map(); bak = save(d, "pre-migrate-rebuild"); n = 0
    for m in d["mistakes"]:
        m.setdefault("status", "active"); m.setdefault("routes", ROUTES.get(m["id"], ["all"]))
        if not m.get("enforcer"): m["enforcer"] = enforcers_for(m, cm)
        if m["id"] in SUPERSEDE: m["status"], m["superseded_by"] = "superseded", SUPERSEDE[m["id"]]
        if m["id"] in MERGED: m["status"], m["superseded_by"] = "merged", MERGED[m["id"]]
        n += 1
    d["about"] = d.get("about", "") + ("" if "status/routes/enforcer" in d.get("about", "") else
                                         " | 11-10 rebuild: each rule has status/routes/enforcer (ledger.py); qc_gate --rules and ob_job.py rules print active ones.")
    save(d, "migrate"); print(f"migrated {n} entries (backup {bak})"); coverage()


def coverage():
    rules = active(); none, prose = [], []; by = {k: [] for k in KINDS}
    for m in rules:
        kinds = {e.split(":", 1)[0] for e in m.get("enforcer", [])}
        if not kinds: none.append(m["id"]); continue
        for k in kinds & set(KINDS): by[k].append(m["id"])
        if kinds <= {"route", "review"}: prose.append(m["id"])
    print(f"{len(rules)} active rules")
    for k in KINDS: print(f"  {k:7s} {len(by[k]):3d}  {' '.join(by[k])}")
    print(f"  not checked by code (route/review only) {len(prose)}: {' '.join(prose)}")
    if none: print(f"  NO ENFORCER ({len(none)}): {' '.join(none)}  -> give each one: ledger.py needs an enforcer"); return False
    return True


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); sys.exit(0 if a else 2)
    opt = lambda k: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None
    if a[0] == "migrate": migrate(); return
    if a[0] == "coverage": sys.exit(0 if coverage() else 1)
    if a[0] == "list":
        for m in load()["mistakes"]:
            if ("--active" in a and not is_active(m)) or not for_route(m, opt("--route")): continue
            print(f"{m.get('status', 'active')[:6]:6s} {rule_line(m)}" + (f"  -> {m['superseded_by']}" if m.get("superseded_by") else ""))
        return
    if a[0] == "supersede" and len(a) > 1 and opt("--by"):
        d = load(); m = next((x for x in d["mistakes"] if x["id"] == a[1]), None)
        if not m: sys.exit(f"no {a[1]} in the ledger")
        m["status"], m["superseded_by"] = "superseded", opt("--by"); save(d, f"supersede-{a[1]}"); print(f"{a[1]} superseded by {opt('--by')}"); return
    if a[0] == "add":
        need = [k for k in ("--said", "--date", "--rule", "--check", "--enforcer") if not opt(k)]
        if need: sys.exit(f"missing {', '.join(need)}: " + __doc__.split("\n\n")[1].splitlines()[0])
        enf = [e.strip() for e in opt("--enforcer").split(",") if e.strip()]
        bad = [e for e in enf if e.split(":", 1)[0] not in KINDS or ":" not in e]
        if bad: sys.exit(f"enforcer must be one of {', '.join(k + ':<x>' for k in KINDS)}: {bad}")
        datetime.date.fromisoformat(opt("--date"))
        d = load(); nid = "M%02d" % (max(int(m["id"][1:]) for m in d["mistakes"]) + 1)
        d["mistakes"].append({"id": nid, "date": opt("--date"), "said": opt("--said"), "rule": opt("--rule"), "check": opt("--check"),
                              "status": "active", "routes": (opt("--routes") or "all").split(","), "enforcer": enf})
        bak = save(d, f"add-{nid}"); print(f"added {nid} (backup {bak})"); return
    print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
