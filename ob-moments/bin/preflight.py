#!/usr/bin/env python3
"""
preflight.py — post-scoring pick-quality lint. Catches the whack-a-mole defect
classes BEFORE rendering ever starts (no video renders anywhere in this tool).

Consumes work/<id>.moments.json (score.py's output, optionally after
ig_post.py has merged in "ig_post" objects) and lints every GATE-PASSED
moment for the concrete failure classes that have shipped before:

  - garbled openers: doubled words ("the the"), article collisions
    ("a most serving sizes"), or a hook/onscreen line starting lowercase
    mid-clause (reads like a chopped transcript fragment, not a real hook)
  - fragment/conjunction openers: hook line starts with a bare conjunction
    or trails off as a sub-4-word fragment
  - headline defects: onscreen_hook/title >12 words, or containing a literal
    '[' (unfilled template placeholder), an em-dash, or '>>'
  - duration outside [12s, 55s]
  - all-same-CTA across the picks (reads ig_post.caption's CTA line when
    present; the account already has a "just spam READY every time" failure
    mode this catches)
  - banter leakage: multi-speaker windows that read as incoherent cross-talk

Exit 0 (clean) or 1 (defects found, printed as a readable report). clip.py
calls this after pick() and ABORTS before rendering when it exits 1 — pass
--force on either preflight.py or clip.py to override and render anyway.

Usage:
    python3 bin/preflight.py work/<id>.moments.json [--n N] [--force]
"""
import sys, os, re, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import mmss, CONJ_OPENER, DISCOURSE_OPENER

MIN_DUR, MAX_DUR = 12.0, 55.0
MAX_HEADLINE_WORDS = 12

# doubled word ("the the", "and and") — case-insensitive, word-boundary safe
DOUBLED_WORD = re.compile(r"\b(\w+)\s+\1\b", re.I)
# article collisions: "a most serving sizes", "the a", "an the" — an article
# directly followed by a determiner/quantifier it can't grammatically precede
ARTICLE_COLLISION = re.compile(r"\b(?:a|an|the)\s+(?:most|many|all|the|a|an)\b", re.I)
# bare conjunction / fragment opener
CONJUNCTION_OPENER = re.compile(r"^\s*(and|but|or|so|because|cuz|'?cause|then)\b", re.I)
# a hook/onscreen line that starts lowercase mid-clause (not a sentence start) —
# real hooks start capitalized; a lowercase-first-letter opener signals a
# chopped transcript fragment, not an intentional headline
LOWERCASE_START = re.compile(r"^\s*[a-z]")
BAD_HEADLINE_CHARS = re.compile(r"\[|—|>>")
EM_DASH_OR_DBL = re.compile(r"[—–]|--")


def _words(s):
    return (s or "").split()


def lint_garbled_opener(text):
    """Doubled words, article collisions, or a lowercase mid-clause start in
    the moment's own spoken opener (the first sentence of `text`)."""
    defects = []
    first = _first_sentence(text)
    if DOUBLED_WORD.search(first):
        m = DOUBLED_WORD.search(first)
        defects.append(f"doubled word in opener: \"{m.group(0)}\" (from: \"{_trunc(first)}\")")
    if ARTICLE_COLLISION.search(first):
        m = ARTICLE_COLLISION.search(first)
        defects.append(f"article collision in opener: \"{m.group(0)}\" (from: \"{_trunc(first)}\")")
    if LOWERCASE_START.match(first) and not DISCOURSE_OPENER.match(first):
        defects.append(f"opener starts lowercase mid-clause (reads like a chopped "
                       f"fragment): \"{_trunc(first)}\"")
    return defects


def lint_fragment_opener(headline):
    """The BURNED-IN headline (onscreen_hook, falling back to title) is a bare
    conjunction lead-in, or too short to carry any meaning as a standalone
    opener (<4 words after stripping filler). Checked against what actually
    renders on-screen, not the raw spoken hook_line reference field — score.py's
    clean_headline()/short_hook() already strip conjunction lead-ins from the
    spoken line when building onscreen_hook, so a stray leftover here means
    that cleanup didn't catch this specific case and it would ship as-is."""
    defects = []
    hl = (headline or "").strip()
    if not hl:
        return defects
    if CONJUNCTION_OPENER.match(hl):
        defects.append(f"conjunction/fragment opener in burned-in headline: \"{_trunc(hl)}\"")
    stripped = DISCOURSE_OPENER.sub("", hl).strip()
    stripped = CONJ_OPENER.sub("", stripped).strip()
    if len(_words(stripped)) < 4:
        defects.append(f"burned-in headline is a sub-4-word fragment after stripping "
                       f"filler: \"{_trunc(hl)}\"")
    return defects


def lint_headline(m):
    """Headline defects on onscreen_hook (what's actually burned in) and,
    secondarily, title (used as a filename/summary fallback)."""
    defects = []
    for field in ("onscreen_hook", "title"):
        val = (m.get(field) or "").strip()
        if not val:
            continue
        n_words = len(_words(val))
        if n_words > MAX_HEADLINE_WORDS:
            defects.append(f"{field} is {n_words} words (max {MAX_HEADLINE_WORDS}): "
                           f"\"{_trunc(val)}\"")
        bad = BAD_HEADLINE_CHARS.search(val)
        if bad:
            reason = {"[": "unfilled template placeholder '['", "—": "em-dash",
                      ">": "'>>' fragment marker"}.get(bad.group(0)[0], bad.group(0))
            defects.append(f"{field} contains {reason}: \"{_trunc(val)}\"")
    return defects


def lint_duration(dur):
    if dur is None:
        return []
    if dur < MIN_DUR:
        return [f"duration {dur}s is under the {MIN_DUR}s floor (too short to be a clip)"]
    if dur > MAX_DUR:
        return [f"duration {dur}s is over the {MAX_DUR}s ceiling (too long for short-form)"]
    return []


def lint_banter(m):
    """Multi-speaker windows that read as incoherent cross-talk cold, mirroring
    score.py's own gate threshold (>=3 speaker changes is an outright gate
    failure there; this catches the >=2 case that clears the gate but still
    reads as banter, and anything with speaker_changes flagged that somehow
    slipped through gate_passed)."""
    changes = m.get("speaker_changes", 0) or 0
    if changes >= 2:
        return [f"banter leakage: {changes} speaker turns inside one clip window "
               "(reads as cross-talk, not a coherent standalone moment)"]
    return []


def _cta_line(m):
    """The CTA text to compare across picks for the all-same-CTA check.
    Prefers ig_post's actual generated caption's last line (the real CTA
    that would ship) when ig_post.py has already run; falls back to
    engagement_lever as a coarser proxy when ig_post hasn't been generated
    yet (preflight must still be useful before ig_post.py runs)."""
    ig = m.get("ig_post")
    if ig and ig.get("caption"):
        lines = [l for l in ig["caption"].splitlines() if l.strip()]
        if lines:
            return lines[-1].strip()
    return f"(no ig_post yet) lever={m.get('engagement_lever', '?')}"


def lint_all_same_cta(moments):
    """Cross-pick check: if every gate-passed pick under review resolves to
    the exact same CTA line, that's a defect (an IG grid of 3-4 identical
    CTAs reads as spam/laziness, not a varied content slate)."""
    if len(moments) < 2:
        return []
    ctas = [_cta_line(m) for m in moments]
    uniq = set(ctas)
    if len(uniq) == 1:
        return [f"all {len(moments)} picks resolve to the IDENTICAL CTA "
                f"(\"{_trunc(ctas[0], 100)}\") — vary engagement_lever/topic or "
                "re-run ig_post.py so the grid isn't a wall of the same ask"]
    return []


def _first_sentence(text):
    m = re.match(r'^.*?[.!?]["\')]?(?:\s|$)', (text or "").strip())
    return (m.group(0) if m else (text or "")[:160]).strip()


def _trunc(s, n=80):
    s = s or ""
    return s if len(s) <= n else s[:n] + "…"


def lint_moment(m):
    """All per-moment lints for one gate-passed moment. Returns a list of
    defect strings (empty = clean)."""
    defects = []
    defects += lint_garbled_opener(m.get("text", ""))
    defects += lint_fragment_opener(m.get("onscreen_hook") or m.get("title") or "")
    defects += lint_headline(m)
    defects += lint_duration(m.get("dur"))
    defects += lint_banter(m)
    return defects


def run_preflight(moments, n=None):
    """Run every lint over the moments that would actually be picked/rendered
    (gate_passed, optionally capped to the first `n` — mirrors clip.py's
    pick() count so preflight lints exactly what will ship).
    Returns (ok: bool, report_lines: list[str])."""
    passed = [m for m in moments if m.get("gate_passed")]
    if n is not None:
        passed = passed[:n]

    report = []
    any_defect = False
    for m in passed:
        defects = lint_moment(m)
        if defects:
            any_defect = True
            report.append(f"[{m.get('id')}] {mmss(m.get('start', 0))}-{mmss(m.get('end', 0))} "
                          f"\"{_trunc(m.get('onscreen_hook') or m.get('title') or '', 60)}\"")
            for d in defects:
                report.append(f"    - {d}")

    cross = lint_all_same_cta(passed)
    if cross:
        any_defect = True
        report.append("[cross-pick]")
        for d in cross:
            report.append(f"    - {d}")

    return (not any_defect), report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("moments_json")
    ap.add_argument("--n", type=int, default=None,
                    help="cap the lint to the first N gate-passed moments (mirrors "
                         "clip.py's pick count); default = all gate-passed moments")
    ap.add_argument("--force", action="store_true",
                    help="print the report but always exit 0 (override the gate)")
    a = ap.parse_args()

    d = json.load(open(a.moments_json))
    vid = d.get("video_id", os.path.splitext(os.path.basename(a.moments_json))[0])
    moments = d.get("moments", [])

    ok, report = run_preflight(moments, n=a.n)

    if ok:
        n_checked = len([m for m in moments if m.get("gate_passed")][:a.n] if a.n
                        else [m for m in moments if m.get("gate_passed")])
        print(f"[preflight] {vid}: PASS — {n_checked} gate-passed pick(s) clean, "
              "no defects found.", file=sys.stderr)
        sys.exit(0)

    print(f"[preflight] {vid}: FAIL — defects found in the picks below:", file=sys.stderr)
    for line in report:
        print(line, file=sys.stderr)
    if a.force:
        print("[preflight] --force set: exiting 0 anyway (defects above were NOT fixed).",
              file=sys.stderr)
        sys.exit(0)
    print("[preflight] aborting before render. Fix the flagged picks, or re-run with "
          "--force to render anyway.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
