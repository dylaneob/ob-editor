#!/usr/bin/env python3
"""skill_lint.py: keeps the short-form-editor skill true to itself.

usage: python3 -I ~/ob-editor/bin/skill_lint.py [SKILL_DIR] [--selftest]
       SKILL_DIR defaults to ~/.claude/skills/short-form-editor

It reads SKILL.md, routes/*.md and subjects/*.md (never history/ or references/) and FAILs when:
  core        SKILL.md is too big to survive a compaction, or lost the two headings the app hook reads
  sizes       a route or subject file is over its limit
  routes      a route in formats.json has no file, or SKILL.md names a file that is not there
  paths       a path or tool named in the text does not exist (a volume that is not mounted is a WARN)
  commands    a sub-command is named that the tool does not have
  holds       an approval hold, "ask OB", "OB" or a dash came back
  cheap       a banned shortcut is named without saying no to it (WARN)
  t7          a line writes, saves or delivers to the T7
  numbers     a number that lives in formats.json is restated in prose
  ledger      an active rule in the mistakes ledger has no enforcer
  agents      the builder or reviewer agent is missing, or the reviewer lost its FILE / SHA256 lines
  hooks       the app hooks are not registered (WARN)
Exit 1 on any FAIL.
"""
import json, os, re, shutil, subprocess, sys, tempfile

HOME = os.path.expanduser("~")
BIN, QC = f"{HOME}/ob-editor/bin", f"{HOME}/ob-editor/qc"
DEFAULT = f"{HOME}/.claude/skills/short-form-editor"
CORE_MAX, CORE_TOK_MAX, DESC_MAX, ROUTE_MAX, SUBJ_MAX = 14000, 5000, 1536, 15500, 12000   # routes: 15,000 until 11-10, raised to fit the pieces and mix steps
NEG = re.compile(r"\b(no|not|never|don't|do not|without|nothing|banned|blocks?|refuses?|removed?|instead of|except(ed|ion)?|only)\b", re.I)
HOLD = [(r"\bask OB\b", "ask OB"), (r"\bOB approves\b", "OB approves"), (r"\bOB's OK\b", "OB's OK"), (r"\bOB picks\b", "OB picks"),
        (r"\bpending OB\b", "pending OB"), (r"\bwait for OB\b", "wait for OB"), (r"\bOB signs off\b", "OB signs off"),
        (r"\bif unsure\b", "if unsure")]
ALWAYS = [(r"\bOB\b(?! Page)", "OB (he is OB)"), ("—", "em dash"), ("–", "en dash")]
CHEAP = [(r"phone copy", "phone copy"), (r"voice-only copy", "voice-only copy"), (r"punch-?ins?\b", "punch-in"), (r"zoom kick", "zoom kick"),
         (r"Vision (mask|matte|cutout)", "Vision mask"), (r"code-made", "code-made sound"), (r"default (track|renderer)", "default track/renderer")]
T7W = re.compile(r"(--to\b|--out\b|\s-o\s|>\s|\bcp\b|\bmv\b|\bsaves?\b|\bwrites?\b|\brender(s|ed)? (to|into)\b|\bdeliver(s|ed|y)?\b|\boutput\b)", re.I)
DUP = [(r"-\s?14(\.\d)?\s*LUFS", "master loudness"), (r"\b27\s*(LU|dB)\b", "bed level"), (r"\b0\.45\s*s\b", "voiceless limit"),
       (r"\b0\.15\s*s\b", "join limit"), (r"\b(220|420)\s*px\b", "Instagram bands"), (r"\b(269|672)\b", "ad safe zone"),
       (r"-\s?1(\.0)?\s*dBTP", "true peak")]
RATE = re.compile(r"\b\d+(\.\d+)?\s*(a|per|/)\s*min(ute)?\b", re.I)
PH = set("WORK FILE ROUTE NAME SCRIPT CAM MIC OUT IN VIDEO VIDEO_ID URL REF FOLDER WHAT DATE JOB SRC CAMERA PIECES WORDS EDL PLAN TRACK "
         "CLIP REEL ID KIND TAG QUERY EVENT".split())
TOOLS = "ob_job qc_route ledger music_pick sfx_pick bank_index qc_assets qc_look qc_audio".split()
PREFIX = ("~/", "/Volumes/", "/Users/", "routes/", "subjects/", "references/", "history/")


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def cut(p):
    """The checkable part of a path: stop at a placeholder (<x>, {x}, *, WORK, FILE...)."""
    p = p.strip().rstrip(".,;:)")
    m = re.search(r"[<{*#$]|\.\.\.", p)
    if m:
        p = p[:m.start()]
        p = p[:p.rfind("/") + 1] if "/" in p else ""
    keep = []
    for c in p.split("/"):
        stem = c.split(".")[0]
        if stem in PH or re.fullmatch(r"[A-Z]\d*", stem or "-"):
            break
        keep.append(c)
    return "/".join(keep).rstrip("/")


def exists(p, base):
    p = cut(p)
    if not p or p in ("~", "/Volumes", "/Users"):
        return True, ""
    full = os.path.expanduser(p) if p.startswith(("~", "/")) else os.path.join(base, p)
    if os.path.exists(full):
        return True, ""
    if p.startswith("/Volumes/"):
        vol = "/".join(p.split("/")[:3])
        if not os.path.exists(vol):
            return True, f"{vol} not mounted"
    return False, p


def path_problems(text, base):
    bad, notes = [], set()
    for n, line in enumerate(text.splitlines(), 1):
        cands = []
        for span in re.findall(r"`([^`\n]+)`", line):
            s = span.strip()
            if s.startswith(PREFIX):
                ok, _ = exists(s, base)
                if ok and " " in s and not s.startswith(("routes/", "subjects/", "references/", "history/")):
                    # a command, or a path with spaces that exists whole: check each path-like word unless the whole thing is a real path
                    whole = os.path.expanduser(cut(s))
                    if os.path.exists(whole) and cut(s) == s.rstrip(".,;:)"):
                        continue
                cands += [w for w in s.split() if w.startswith(PREFIX)] if " " in s and not os.path.exists(os.path.expanduser(s)) else [s]
        bare = re.sub(r"`[^`\n]+`", " ", line)
        cands += re.findall(r"(?<![\w.])(~/[^\s`\"')\]]+|/(?:Volumes|Users)/[^\s`\"')\]]+)", bare)
        for c in cands:
            ok, why = exists(c, base)
            if not ok:
                bad.append((n, f"missing: {why}"))
            elif why:
                notes.add(why)
    return bad, notes


def command_problems(text):
    bad = []
    for n, line in enumerate(text.splitlines(), 1):
        # only real command text: inside backticks, or a bare command line in a code block
        segs = re.findall(r"`([^`\n]+)`", line) + ([line] if "python3 -I" in line and "`" not in line else [])
        for seg in segs:
            for tool, sub in re.findall(r"\b(" + "|".join(TOOLS) + r")\.py\s+([a-z][a-z-]+)\b", seg):
                src = f"{BIN}/{tool}.py"
                if os.path.exists(src):
                    s = read(src)
                    if f'"{sub}"' not in s and f"'{sub}'" not in s:
                        bad.append((n, f"{tool}.py has no sub-command {sub}"))
    return bad


def scan(text, pats, negated_ok):
    bad = []
    for n, line in enumerate(text.splitlines(), 1):
        for rx, what in pats:
            if re.search(rx, line) and not (negated_ok and NEG.search(line)):
                bad.append((n, what))
    return bad


def fmt(hits, limit=8):
    out = [f"{f}:{n} {w}" for f, n, w in hits[:limit]]
    return "; ".join(out) + (f"; +{len(hits) - limit} more" if len(hits) > limit else "")


def lint(d, local_only=False):
    rows = []
    add = lambda c, s, det="": rows.append((c, s, det))
    core = os.path.join(d, "SKILL.md")
    if not os.path.exists(core):
        return [("core", "FAIL", f"no SKILL.md in {d}")]
    files = [("SKILL.md", core)]
    for sub in ("routes", "subjects"):
        sd = os.path.join(d, sub)
        if os.path.isdir(sd):
            files += [(f"{sub}/{f}", os.path.join(sd, f)) for f in sorted(os.listdir(sd)) if f.endswith(".md")]
    texts = {name: read(p) for name, p in files}
    t = texts["SKILL.md"]

    # core
    size = len(t.encode("utf-8")); tok = int(size / 3.5)
    m = re.search(r"^description:\s*(.+)$", t, re.M)
    desc = len(m.group(1)) if m else 0
    probs = []
    if size > CORE_MAX: probs.append(f"{size} bytes (limit {CORE_MAX})")
    if tok > CORE_TOK_MAX: probs.append(f"about {tok} tokens (limit {CORE_TOK_MAX}: the rest is dropped after a compaction)")
    if not m or desc > DESC_MAX: probs.append(f"description {desc} chars (limit {DESC_MAX})")
    a, b = t.find("## Never again"), t.find("## When OB gives a note")
    if a < 0 or b < 0 or b < a: probs.append('headings "## Never again" and "## When OB gives a note" must both exist, in that order (the app hook reads the block between them)')
    add("core", "FAIL" if probs else "PASS", "; ".join(probs) or f"{size} bytes, about {tok} tokens, description {desc} chars")

    # sizes
    big = [f"{n} {len(x.encode('utf-8'))} bytes (limit {ROUTE_MAX if n.startswith('routes/') else SUBJ_MAX})" for n, x in texts.items()
           if (n.startswith("routes/") and len(x.encode("utf-8")) > ROUTE_MAX) or (n.startswith("subjects/") and len(x.encode("utf-8")) > SUBJ_MAX)]
    add("sizes", "FAIL" if big else "PASS", "; ".join(big) or f"{len(texts) - 1} route and subject files within limits")

    # routes
    probs = []
    named = set(re.findall(r"\b((?:routes|subjects|references)/[\w.-]+\.md)\b", "\n".join(texts.values())))
    for f in sorted(named):
        if not os.path.exists(os.path.join(d, f)): probs.append(f"{f} is named but missing")
    if not local_only:
        try:
            fm = json.load(open(f"{QC}/formats.json"))
            for r, v in fm.get("routes", {}).items():
                f = v.get("file")
                if not f: probs.append(f"route {r} has no file in formats.json")
                elif not os.path.exists(os.path.join(d, f)): probs.append(f"route {r}: {f} missing")
                elif f"`{r}`" not in t and r != "mock": probs.append(f"route {r} is not in SKILL.md's table")
        except Exception as e:
            probs.append(f"formats.json unreadable: {e}")
    orphans = [n for n in texts if n != "SKILL.md" and n not in t]
    add("routes", "FAIL" if probs else ("WARN" if orphans else "PASS"),
        "; ".join(probs) or ("not named in SKILL.md: " + ", ".join(orphans) if orphans else f"{len(named)} files named, all present"))

    # per-line checks
    P, C, H, K, T, N, notes = [], [], [], [], [], [], set()
    for name, x in texts.items():
        bad, nt = path_problems(x, d); P += [(name, n, w) for n, w in bad]; notes |= nt
        C += [(name, n, w) for n, w in command_problems(x)]
        H += [(name, n, w) for n, w in scan(x, HOLD, True)] + [(name, n, w) for n, w in scan(x, ALWAYS, False)]
        K += [(name, n, w) for n, w in scan(x, CHEAP, True)]
        bar = False   # "## The bar" holds what an approved exemplar measured: those are measurements, not rules
        for n, line in enumerate(x.splitlines(), 1):
            if line.startswith("## "): bar = line.lower().startswith("## the bar")
            if "/Volumes/T7" in line and T7W.search(line) and not NEG.search(line) and "read" not in line.lower():
                T.append((name, n, "writes to the T7"))
            if bar: continue
            for rx, what in DUP:
                if re.search(rx, line): N.append((name, n, what))
            if RATE.search(line) and re.search(r"sound effect|sfx", line, re.I): N.append((name, n, "sound-effect rate"))
    add("paths", "FAIL" if P else ("WARN" if notes else "PASS"), fmt(P) or ("; ".join(sorted(notes)) or "every named path exists"))
    add("commands", "FAIL" if C else "PASS", fmt(C) or "every sub-command exists")
    add("holds", "FAIL" if H else "PASS", fmt(H) or "no approval holds, no dashes")
    add("cheap", "WARN" if K else "PASS", fmt(K) or "no shortcut named without a no")
    add("t7", "FAIL" if T else "PASS", fmt(T) or "nothing writes to the T7")
    add("numbers", "FAIL" if N else "PASS", fmt(N) or "no formats.json number restated")
    if local_only:
        return rows

    # ledger
    lp = f"{BIN}/ledger.py"
    if not os.path.exists(lp):
        add("ledger", "FAIL", "ledger.py is missing")
    else:
        r = subprocess.run(["python3", "-I", lp, "coverage"], capture_output=True, text=True, timeout=120)
        tail = " | ".join((r.stdout + r.stderr).strip().splitlines()[-3:])
        add("ledger", "PASS" if r.returncode == 0 else "FAIL", tail[:300])

    # agents
    probs = []
    ad = f"{HOME}/.claude/agents"
    for f in ("ob-editor.md", "video-reviewer.md"):
        if not os.path.exists(f"{ad}/{f}"): probs.append(f"{f} missing")
    if os.path.exists(f"{ad}/video-reviewer.md"):
        rv = read(f"{ad}/video-reviewer.md")
        for need in ("SHA256:", "FILE:", "VERDICT:"):
            if need not in rv: probs.append(f"video-reviewer.md lost its {need} line")
    add("agents", "FAIL" if probs else "PASS", "; ".join(probs) or "builder and reviewer agents in place")

    # hooks
    try:
        st = read(f"{HOME}/.claude/settings.json")
        want = ["agent-pre", "send-pre", "bash-pre", "subagent-stop", "session-start", "ob_editor_hooks.py prompt"]
        miss = [w for w in want if w not in st]
        add("hooks", "WARN" if miss else "PASS", ("not registered: " + ", ".join(miss)) if miss else "all six app hooks registered")
    except Exception as e:
        add("hooks", "WARN", f"settings.json unreadable: {e}")
    return rows


def show(rows):
    w = max(len(c) for c, _, _ in rows)
    for c, s, det in rows:
        print(f"{c.ljust(w)}  {s.ljust(4)}  {det}")
    fails = [c for c, s, _ in rows if s == "FAIL"]
    print("SKILL LINT " + ("FAILED: " + ", ".join(fails) if fails else "PASSED"))


def selftest():
    tmp = tempfile.mkdtemp(prefix="skill_lint_")
    try:
        good, bad = os.path.join(tmp, "good"), os.path.join(tmp, "bad")
        for d in (good, bad):
            os.makedirs(os.path.join(d, "routes")); os.makedirs(os.path.join(d, "subjects"))
        head = "---\nname: x\ndescription: a short one\n---\n# X\n## Never again\n1. rule\n## When OB gives a note\nRead `routes/a.md`.\n"
        open(os.path.join(good, "SKILL.md"), "w").write(head)
        open(os.path.join(good, "routes", "a.md"), "w").write("# Route\nRun `python3 -I ~/ob-editor/bin/qc_gate.py --selftest`. No punch-ins. Never ask OB to pick.\n")
        open(os.path.join(bad, "SKILL.md"), "w").write(head.replace("## Never again\n", "") + "Read `subjects/gone.md`.\n" + "x" * 15000)
        open(os.path.join(bad, "routes", "a.md"), "w").write(
            "Then ask OB which one.\nUse a dash — here.\nMaster at -14 LUFS.\nAdd a zoom kick on the hook.\n"
            "Deliver with `deliver.py FILE --to \"/Volumes/T7/OB-EDITS/AIRDROP x\"`.\nRun `~/ob-editor/bin/not_a_real_tool_zz.py`.\n"
            "Sound effects at 4 a minute.\n")
        g = {c: s for c, s, _ in lint(good, True)}
        b = {c: s for c, s, _ in lint(bad, True)}
        want_bad = {"core": "FAIL", "routes": "FAIL", "paths": "FAIL", "holds": "FAIL", "cheap": "WARN", "t7": "FAIL", "numbers": "FAIL"}
        ok = all(s == "PASS" for s in g.values()) and all(b.get(c) == s for c, s in want_bad.items())
        if not ok:
            print("good:", g); print("bad: ", b); print("wanted bad:", want_bad)
        print("SELFTEST " + ("PASSED" if ok else "FAILED"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__); return 0
    if "--selftest" in sys.argv:
        return selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    d = os.path.abspath(os.path.expanduser(args[0])) if args else DEFAULT
    rows = lint(d)
    show(rows)
    return 1 if any(s == "FAIL" for _, s, _ in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
