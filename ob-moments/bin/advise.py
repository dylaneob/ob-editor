#!/usr/bin/env python3
"""
advise.py — the ob-moments improvement advisor.

Deterministic ONLY (no LLM calls) so it runs anywhere, with zero backend, in
under a second. Consumes work/<id>.moments.json (score.py's output) and the
matching work/<id>.en.srt, and writes work/<id>.advice.md with two sections:

  A) PER-CLIP critique for the top-8 gate-passed moments — hook rewrite
     (library rewrite_templates filled with the clip's OWN specifics),
     cut critique (open-loop / weak-ender flags), on-screen text alternatives,
     and a brand-safety pass (no em-dashes / AI-tell phrasing in anything we
     propose — OB is anti-AI-tells).
  B) SOURCE-VIDEO critique from the raw SRT — opening-10s hook verdict +
     stronger cold-open suggestion, words-per-minute pacing + the slowest
     60s stretch, a discourse-filler-opener tally (speaking habit), and a
     prioritized "next time you film" list.

Reuses score.py's hook archetypes, short_hook(), and DISCOURSE_OPENER, and
window.py/clean_srt.py's sentence/word utilities, so the advisor's read of
"hook" and "filler" matches the scorer's exactly.

Usage:
    python3 bin/advise.py work/<id>.moments.json
"""
import sys, os, re, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import (
    detect_archetype, short_hook, DISCOURSE_OPENER, NUMBER, mmss,
    HOOK_BANK, HOOK_BANK_REHOOK, bank_headline, _bank_topics_for,
    _BANK_TOPIC_LEXICON, _bank_hook_fillable,
)
from clean_srt import parse_srt, dedup_words
from window import sentences_from_srt

TOP_N = 8
MID_CLIP_REHOOK_MIN_DUR = 35.0  # seconds; per the task spec, only clips longer
                                # than this get a mid-clip rehook suggestion


def _load_full_hook_lib():
    """score.py's HOOK_ARCHETYPES trims each archetype down to
    name/strength/pats/onscreen (one template) for the scorer's own needs.
    The advisor needs the FULL rewrite_templates + onscreen_templates lists,
    so load data/hook-library.json directly here, compiling the same
    spoken_cues regexes score.py uses for detect_archetype consistency."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hook-library.json")
    try:
        lib = json.load(open(p))
    except Exception:
        return []
    out = []
    for a in lib.get("hook_archetypes", []):
        pats = []
        for c in a.get("spoken_cues", []):
            try:
                pats.append(re.compile(c, re.I))
            except re.error:
                pass
        out.append({
            "name": a["name"],
            "strength": a.get("strength_prior", 60),
            "pats": pats,
            "rewrite_templates": a.get("rewrite_templates") or [],
            "onscreen_templates": a.get("onscreen_templates") or [],
        })
    out.sort(key=lambda a: -a["strength"])
    return out


FULL_HOOK_LIB = _load_full_hook_lib()

# ---- brand-safety: no em-dashes, no AI-tell phrasing in anything we propose -
EM_DASH = re.compile(r"[—–]|--")  # em dash, en dash, or double-hyphen stand-in
AI_TELLS = re.compile(
    r"\b(it'?s not (?:just|only) .* it'?s\b|not just .*,? (?:it'?s|but)\b|"
    r"in (?:today'?s|this) (?:fast-paced|day and age)|unlock your|"
    r"game[- ]?changer|elevate your|dive into|delve into|in conclusion|"
    r"it'?s important to note|as an ai|let'?s dive in)\b", re.I)


def brand_flags(text):
    """Return a list of brand-safety flags for a piece of PROPOSED copy
    (rewrites / on-screen text we generate) — never silently ship an
    em-dash or an AI-tell construction."""
    flags = []
    if EM_DASH.search(text):
        flags.append("em-dash detected — rewrite without it (OB is anti-AI-tells)")
    m = AI_TELLS.search(text)
    if m:
        flags.append(f"AI-tell phrasing detected ('{m.group(0)}') — rewrite plainer")
    return flags


def strip_brand_issues(text):
    """Best-effort deterministic clean of our OWN generated text: swap em/en
    dashes for a comma or period so a rewrite we hand back never itself
    violates the no-em-dash rule."""
    # a dash between two clauses reads fine as a period; between a clause
    # and a trailing fragment reads fine as a comma. Comma is the safer
    # universal swap and never breaks grammar outright.
    return re.sub(r"\s*[—–]\s*", ", ", text).replace(" -- ", ", ")


# ---- extracting the clip's OWN specifics for deterministic template-fill ---
AGE_RE = re.compile(r"\b(?:over|after|at)\s+(\d{2})\b", re.I)
LOSS_NUM_RE = re.compile(r"\b(\d+)\s*(?:lbs?|pounds?)\b", re.I)
TIMEFRAME_RE = re.compile(r"\b(\d+)\s*(months?|weeks?|days?|years?)\b", re.I)
# an explicit "from X to Y" / "X down to Y" arc — only THIS shape counts as a
# real before/after pair; two unrelated lb-mentions (e.g. a yo-yo "lost 20,
# gained 25, lost 15") must NOT be read as a transformation arc.
FROM_TO_RE = re.compile(r"\bfrom\s+(\d+)\s*(?:lbs?|pounds?)?\s+to\s+(\d+)\s*(?:lbs?|pounds?)?\b", re.I)
YOU_RE_M = re.compile(r"\b(guy|man|men|male)\b", re.I)
YOU_RE_F = re.compile(r"\b(woman|women|female|girl)\b", re.I)

# topic/pain nouns the templates most often need (deterministic keyword hits,
# ordered by specificity so the first match wins over generic fallback)
_TOPIC_LEXICON = [
    ("belly fat", r"\bbelly fat\b"),
    ("cardio", r"\bcardio\b"),
    ("calorie deficits", r"\bcalor(?:ie|y)\b"),
    ("fiber", r"\bfiber\b"),
    ("protein", r"\bprotein\b"),
    ("meal plans", r"\bmeal plans?\b"),
    ("your metabolism", r"\bmetaboli[sz]m\b"),
    ("hormones", r"\bhormones?\b"),
    ("yo-yo dieting", r"\byo-?yo\b"),
    ("counting calories", r"\bcount(?:ing)? calories\b"),
    ("keto", r"\bketo\b"),
    ("intermittent fasting", r"\bintermittent fasting\b"),
    ("crash dieting", r"\b(?:extreme|crash) diets?\b"),
    ("your relationship with food", r"\brelationship with food\b"),
    ("fat loss", r"\bfat loss\b"),
    ("weight loss", r"\bweight loss\b"),
]
# common obvious-guess vs real-cause pairs the buyer usually assumes vs. what
# OB actually teaches — used only when the clip text doesn't hand us a
# clearer pair, so the placeholder is never left literal.
_OBVIOUS_VS_REAL = ("your calories", "your habits and systems, not the diet itself")


def extract_specifics(text):
    """Deterministic, template-fill-only extraction of a clip's own numbers,
    pains, and topic nouns. Only pulls facts that are actually present in the
    text; anything not found gets a clearly-generic (never fabricated-sounding
    specific) OB-brand fallback so no literal [BRACKET] ever survives into
    the output. `age_found`/`arc_found` flags let callers know which values
    are real vs. fallback."""
    age_m = AGE_RE.search(text)
    age_found = bool(age_m)
    age = age_m.group(1) if age_m else "40"  # fallback: OB's median buyer age

    loss_all = LOSS_NUM_RE.findall(text)
    loss_n = loss_all[0] if loss_all else "20"

    tf_m = TIMEFRAME_RE.search(text)
    timeframe = f"{tf_m.group(1)} {tf_m.group(2)}" if tf_m else "3 months"

    # before/after figures for transformation_proof ("[BEFORE] to [AFTER]"):
    # ONLY count it as a real arc when the text has an explicit "from X to Y"
    # shape. Two unrelated lb-mentions (e.g. a yo-yo "lost 20, gained 25")
    # are not a transformation and must not be forced into one.
    arc_m = FROM_TO_RE.search(text)
    arc_found = bool(arc_m)
    if arc_m:
        before_n, after_n = arc_m.group(1), arc_m.group(2)
    else:
        before_n, after_n = "before", "after"  # honest placeholder, not a guessed pair

    gender = "woman/man"
    if YOU_RE_F.search(text) and not YOU_RE_M.search(text):
        gender = "woman"
    elif YOU_RE_M.search(text) and not YOU_RE_F.search(text):
        gender = "man"

    topic = "fat loss"
    for name, pat in _TOPIC_LEXICON:
        if re.search(pat, text, re.I):
            topic = name
            break

    generic_num = None
    nm = NUMBER.search(text)
    if nm:
        generic_num = nm.group(0)

    # count occurrences of the loss number in the SOURCE text so a template
    # that uses [N] twice for two DIFFERENT meanings (e.g. "[N] LBS IN [N]
    # MONTHS") doesn't echo the same figure into both slots (see fill_template
    # occurrence-aware handling below).
    return {
        "AGE": age, "AGE+": f"{age}+", "_age_found": age_found,
        "N": loss_n, "NUMBER": generic_num or loss_n,
        "_timeframe_n": (tf_m.group(1) if tf_m else "3"),
        "X": topic, "Y": "sustainable habits",
        "TOPIC": topic,
        "BEFORE": before_n, "AFTER": after_n, "_arc_found": arc_found,
        "man/woman": gender, "woman/man": gender,
        "men/women": "men and women", "women/men": "women and men",
        "belly": "belly fat", "belly fat": "belly fat",
        "fat loss": "fat loss", "diet": "diet", "metabolism": "your metabolism",
        "calorie deficits": "calorie deficits",
        "cardio and fat loss": "cardio and fat loss",
        "exercise/diet habit": topic, "common tactic": topic,
        "common belief": f"the idea that it's all about {topic}",
        "Common belief": f"The idea that it's all about {topic}",
        "obvious guess": _OBVIOUS_VS_REAL[0], "real cause": _OBVIOUS_VS_REAL[1],
        "month two": "month two", "timeframe": timeframe,
        "surprisingly simple thing": "one small daily habit",
        "polarizing fitness claim": f"more effort isn't the fix for {topic}",
        "claim about the buyer's situation": "you're not stuck because of willpower",
        "effort": "tracking everything",
        "trainer/doctor": "trainer",
        "why you can't lose belly fat": "why the scale won't move",
        "wrong thing": "chasing a quick fix",
        "10 years of yo-yo dieting": "years of yo-yo dieting",
        "2 years": "two years",
        "90%": "most",
        "they can't lose weight no matter what": "they've tried everything and can't lose weight",
        "eating less and moving more": "eating less and moving more",
        "habit": "one habit",
        "1": "1",
        # the library authors used literal example numbers/nouns in some
        # templates ("[45]", "[40]", "[40s]", "[the belly]", "[280]",
        # "[180]") as stand-ins for a semantic slot, not real literals to
        # echo verbatim — alias them to the matching real specific so they
        # resolve to THIS clip's own numbers/topic instead of the author's
        # example figures.
        "the belly": "belly fat",
        "45": age, "40": age, "40s": f"{age}s",
        "280": before_n, "180": after_n,
    }


PLACEHOLDER = re.compile(r"\[([^\]]+)\]")

# templates that reuse the SAME placeholder key for two DIFFERENT meanings.
# "[N] LBS IN [N] MONTHS" means (lbs-lost, timeframe-number) — filling both
# occurrences from the single "N" specific would echo the lbs figure into
# the months slot, so give this exact shape an explicit per-occurrence key
# order instead of the generic single-value lookup.
_DUAL_N_TEMPLATES = {
    "[N] LBS IN [N] MONTHS": ("N", "_timeframe_n"),
}

# templates whose bracket tokens mean a before-weight/after-weight pair (not
# the generic topic-noun meaning [X]/[Y] have everywhere else, and not a
# literal example number like the template author's own "[280]"/"[180]") —
# map them onto BEFORE/AFTER instead. Each REQUIRES a real "from X to Y" arc
# in the clip (see NEEDS_ARC below), otherwise it's skipped entirely rather
# than filled with a placeholder-y "fat loss to sustainable habits" mismatch
# or an unchanged literal "280 to 180" that isn't this clip's own numbers.
_XY_AS_BEFORE_AFTER = {
    "My client went from [X] to [Y] in [timeframe] doing [surprisingly simple thing] "
    "— not what you'd expect.": ("X", "Y"),
    "I went from [280] to [180] by changing ONE [habit] — here's what it was.": ("280", "180"),
}
# templates that need a genuine before/after arc to make sense at all —
# skipped (not filled with a placeholder-y guess) when none is found.
NEEDS_ARC = set(_XY_AS_BEFORE_AFTER) | {"FROM [BEFORE] TO [AFTER] AT [AGE]"}


def fill_template(tpl, specifics):
    """Deterministic template fill: replace every [PLACEHOLDER] with the
    clip's own extracted specifics (falling back to a generic-but-on-topic
    phrase), never an LLM call. Slash-choices like [man/woman] resolve via
    the same dict key so gendered templates read naturally. Handles the
    known dual-meaning "[N] ... [N]" onscreen template, and the
    "[X] to [Y]" before/after-weight meaning, as special cases so the wrong
    specific never lands in the wrong slot. Returns None if the template
    NEEDS_ARC and the clip has no genuine "from X to Y" transformation arc
    (caller should skip it rather than ship a placeholder-y fill)."""
    if tpl in NEEDS_ARC and not specifics.get("_arc_found"):
        return None
    if tpl in _DUAL_N_TEMPLATES:
        keys = iter(_DUAL_N_TEMPLATES[tpl])
        def repl_dual(m):
            k = next(keys, "N")
            return str(specifics.get(k, specifics.get("N", "")))
        return strip_brand_issues(PLACEHOLDER.sub(repl_dual, tpl))
    if tpl in _XY_AS_BEFORE_AFTER:
        before_key, after_key = _XY_AS_BEFORE_AFTER[tpl]
        xy_specifics = dict(specifics, **{before_key: specifics["BEFORE"],
                                           after_key: specifics["AFTER"]})
        return strip_brand_issues(PLACEHOLDER.sub(
            lambda m: str(xy_specifics.get(m.group(1), m.group(1))), tpl))

    def repl(m):
        key = m.group(1)
        if key in specifics:
            return str(specifics[key])
        # numeric literal placeholders e.g. "[3]" in numbered_list_tease
        if re.fullmatch(r"\d+", key):
            return key
        # unrecognized bracket: fall back to the topic noun so nothing
        # literal like "[X]" ever survives into shipped copy
        return specifics.get("TOPIC", specifics.get("X", "fat loss"))
    out = PLACEHOLDER.sub(repl, tpl)
    return strip_brand_issues(out)


def best_archetypes_for(text, k=2):
    """Rank archetypes by (spoken-cue hit first, then strength_prior), so a
    clip whose pain matches an archetype's cues is preferred over just
    grabbing the two globally-strongest archetypes. Searched against the
    FULL clip text (not just the one-line hook) so clips whose hook is
    generic but whose body clearly fires an archetype (e.g. a fiber/protein
    breakdown) still get a topic-matched rewrite instead of always falling
    back to the two globally-strongest archetypes. Uses FULL_HOOK_LIB (not
    score.py's trimmed HOOK_ARCHETYPES) so rewrite_templates/full
    onscreen_templates are available to fill."""
    scored = []
    for a in FULL_HOOK_LIB:
        hit = any(p.search(text) for p in a["pats"])
        scored.append((1 if hit else 0, a["strength"], a))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    return [a for _, _, a in scored[:k]]


def hook_rewrites(m):
    """2-3 rewritten opening lines from the library's rewrite_templates,
    filled with the clip's own specifics, each labeled with its archetype.
    Only called when the hook needs help (archetype missing or hook < 60).
    Pulls up to 2 templates from the single best-matched archetype (so a
    clip that clearly fires ONE pattern gets two strong variants of it) plus
    1 from the runner-up, capped at 3 total. A template that NEEDS_ARC and
    has none (fill_template returns None) is skipped, not force-filled."""
    specifics = extract_specifics(m["text"])
    archs = best_archetypes_for(m["text"], k=2)
    out = []
    for rank, a in enumerate(archs):
        take = 2 if rank == 0 else 1
        got = 0
        for tpl in a.get("rewrite_templates") or []:
            if got >= take or len(out) >= 3:
                break
            filled = fill_template(tpl, specifics)
            if filled is None:
                continue
            out.append({"archetype": a["name"], "line": filled})
            got += 1
        if len(out) >= 3:
            break
    return out[:3]


def onscreen_alternatives(m):
    """2 on-screen text alternatives: the matched archetype's onscreen
    templates filled with specifics, plus the quotable_line verbatim if
    it's short enough to read as an overlay (<=12 words). A template that
    NEEDS_ARC and has none is skipped in favor of the next template."""
    specifics = extract_specifics(m["text"])
    archs = best_archetypes_for(m["text"], k=1)
    alts = []
    if archs:
        for tpl in archs[0].get("onscreen_templates") or []:
            if len(alts) >= 2:
                break
            filled = fill_template(tpl, specifics)
            if filled is None:
                continue
            alts.append(filled.upper())
    q = (m.get("quotable_line") or "").strip()
    if q and len(q.split()) <= 12:
        alts.append(q.rstrip(".!?").upper())
    if not alts:
        alts.append(short_hook(m["hook_line"], 9).upper())
    # de-dup while preserving order
    seen, uniq = set(), []
    for a in alts:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq[:2] if len(uniq) >= 2 else uniq


def bank_onscreen_alternative(m):
    """1 matched quality-a hook-BANK line as an on-screen alternative, distinct
    from onscreen_alternatives() (which fills archetype TEMPLATES) -- this
    pulls a ready-made bank LINE via score.py's bank_headline(), which already
    enforces topic-match + strict-fill + mechanism-diversity. Returns None if
    the bank has nothing eligible for this clip's text (never force a pick)."""
    line = bank_headline(m["text"])
    return line.upper() if line else None


def cut_critique(m):
    """Open-loop and weak-ender flags from the moment's own subscores."""
    notes = []
    s = m["subscores"]
    if s.get("curiosity", 0) >= 55 and s.get("payoff", 0) < 40:
        notes.append(
            "opens a loop it never closes (curiosity "
            f"{s['curiosity']} / payoff {s['payoff']}) — extend to include the "
            "resolution, or move the out-point to the sentence that answers it.")
    tail_words = m["text"].split()[-25:]
    tail = " ".join(tail_words)
    ends_mid_thought = not re.search(r'[.!?]["\')]?\s*$', m["text"].strip())
    weak_ender = bool(re.search(
        r"\b(uh+|um+|so yeah|and (?:that'?s|stuff)|you know|i guess|kind of|sort of)\.?\s*$",
        tail, re.I))
    if ends_mid_thought:
        notes.append("clip cuts off mid-sentence — trim the out-point back to the "
                      "last full sentence boundary.")
    elif weak_ender:
        notes.append(f"weak ender ('...{tail[-60:].strip()}') — trim to the strongest "
                      "line before it, or add a save/share CTA per the hook library's "
                      "SAVE/SEND-TRIGGER pattern.")
    if not notes:
        notes.append("closes its own loop cleanly — no cut change needed.")
    return notes


def hook_verdict(m):
    """One-line verdict on why the hook is/isn't strong, for clips that
    don't need a rewrite."""
    s = m["subscores"]
    if m.get("hook_archetype"):
        return (f"already strong — matches the **{m['hook_archetype']}** archetype "
                f"(hook {s['hook']}); no rewrite needed.")
    return f"hook {s['hook']} clears the bar without a named archetype match; leave as-is."


def mid_clip_rehook_note(m):
    """For clips over MID_CLIP_REHOOK_MIN_DUR seconds: a mid-clip rehook note
    pulling 1-2 mid_clip_templates straight from the hook-bank's rehook{}
    object (data/hook-bank.json). These are mid-SCRIPT retention devices, not
    opening hooks (see REHOOK-PLAYBOOK.md), so they're offered as a where-to-
    re-anchor-attention suggestion, not another headline candidate. Returns
    None for shorter clips or if the bank has no rehook templates loaded."""
    if m.get("dur", 0) <= MID_CLIP_REHOOK_MIN_DUR:
        return None
    templates = (HOOK_BANK_REHOOK.get("mid_clip_templates") or [])[:2]
    if not templates:
        return None
    mid_ts = mmss(m["start"] + m["dur"] / 2.0)
    return mid_ts, templates


def per_clip_section(m, rank):
    lines = [f"### {rank}. {m['title']}  ({mmss(m['start'])}–{mmss(m['end'])}, {m['dur']}s)"]
    s = m["subscores"]

    # compute once, reuse for both the display and the brand-safety pass
    needs_rewrite = (not m.get("hook_archetype")) or s.get("hook", 0) < 60
    rewrites = hook_rewrites(m) if needs_rewrite else []
    onscreen_alts = onscreen_alternatives(m)
    bank_alt = bank_onscreen_alternative(m)

    # -- HOOK --
    lines.append("**HOOK:**")
    if needs_rewrite:
        if rewrites:
            for r in rewrites:
                flags = brand_flags(r["line"])
                flag_note = f"  _(flag: {'; '.join(flags)})_" if flags else ""
                lines.append(f"- [{r['archetype']}] {r['line']}{flag_note}")
        else:
            lines.append("- no archetype match found in the library; keep current opener "
                          "and gate it manually before publishing.")
    else:
        lines.append(f"- {hook_verdict(m)}")

    # -- CUT --
    lines.append("**CUT:**")
    for note in cut_critique(m):
        lines.append(f"- {note}")

    # -- ON-SCREEN TEXT --
    lines.append("**ON-SCREEN TEXT:**")
    for alt in onscreen_alts:
        flags = brand_flags(alt)
        flag_note = f"  _(flag: {'; '.join(flags)})_" if flags else ""
        lines.append(f"- {alt}{flag_note}")
    if bank_alt:
        flags = brand_flags(bank_alt)
        flag_note = f"  _(flag: {'; '.join(flags)})_" if flags else ""
        lines.append(f"- [hook-bank] {bank_alt}{flag_note}")

    # -- MID-CLIP REHOOK (only for clips over the duration floor) --
    rehook = mid_clip_rehook_note(m)
    if rehook:
        mid_ts, templates = rehook
        lines.append("**MID-CLIP REHOOK:**")
        lines.append(f"- clip runs {m['dur']}s (over the {MID_CLIP_REHOOK_MIN_DUR:.0f}s floor) — "
                      f"plant a re-hook around {mid_ts} so attention resets instead of decaying:")
        for t in templates:
            lines.append(f"  - \"{t}\"")

    # -- BRAND --
    all_proposed = [r["line"] for r in rewrites] + onscreen_alts + ([bank_alt] if bank_alt else [])
    all_flags = []
    for t in all_proposed:
        all_flags += brand_flags(t)
    lines.append("**BRAND:**")
    if all_flags:
        for f in sorted(set(all_flags)):
            lines.append(f"- {f}")
    else:
        lines.append("- clean — no em-dashes or AI-tell phrasing in the proposed copy above.")

    lines.append("")
    return lines


# ---- source-video critique (from the raw SRT) ------------------------------
WPM_WINDOW = 60.0  # seconds, for the "slowest stretch" scan


def words_with_ts(srt_path):
    return dedup_words(parse_srt(srt_path))


def opening_hook_verdict(sents):
    """Verdict on whether the video's own cold open survives the first 10s,
    using the same archetype/hook machinery the scorer uses on clips."""
    if not sents:
        return "no transcript available.", None
    head_sents = [s for s in sents if s["start"] < 10.0] or [sents[0]]
    opener_text = " ".join(s["text"] for s in head_sents)
    first = sents[0]["text"]
    arch = detect_archetype(first)
    if arch:
        verdict = (f"the cold open matches the **{arch['name']}** archetype "
                    f"(strength {arch['strength']}) — a proven hook shape, keep opening this way.")
    elif DISCOURSE_OPENER.match(first.strip()):
        verdict = ("the cold open leads with a conversational filler word "
                    "(\"Seriously,\"/\"So,\"/\"I mean,\" etc.) instead of the hook itself — "
                    "this bleeds the first 1-3s that decide whether anyone stays.")
    else:
        verdict = "the cold open doesn't match a known high-pull archetype; it may survive on curiosity alone but isn't optimized."
    return verdict, opener_text


def suggest_cold_open(sents, video_id):
    """Deterministic stronger-cold-open suggestion: find the highest
    archetype-strength sentence anywhere in the first few minutes and
    propose opening there instead, template-filled from its own text."""
    window_sents = [s for s in sents if s["start"] < 240.0]
    best = None
    for s in window_sents:
        arch = detect_archetype(s["text"])
        if arch and (best is None or arch["strength"] > best[1]):
            best = (s, arch["strength"], arch)
    if not best:
        return ("no strong archetype line found in the first 4 minutes to promote to the "
                "cold open — the fix is a scripted hook line next time, not a re-cut.")
    s, strength, arch = best
    return (f"open on \"{s['text'].strip()}\" instead (at {mmss(s['start'])}) — it fires the "
            f"**{arch['name']}** archetype (strength {strength}), stronger than the current "
            "cold open.")


def wpm_pacing(words):
    """Overall words-per-minute, plus the single slowest 60s stretch (by
    words-spoken, a proxy for dead air / rambling) with its timestamp."""
    if not words:
        return None, None
    total_words = len(words)
    total_span = max(1.0, words[-1][1] - words[0][1])
    overall_wpm = total_words / (total_span / 60.0)

    # slide a 60s window every 15s across the transcript, count words inside
    t0 = words[0][1]
    t_end = words[-1][1]
    slowest = None
    t = t0
    while t + WPM_WINDOW <= t_end:
        n = sum(1 for _, ts in words if t <= ts < t + WPM_WINDOW)
        wpm = n / (WPM_WINDOW / 60.0)
        if slowest is None or wpm < slowest[0]:
            slowest = (wpm, t)
        t += 15.0
    return round(overall_wpm, 1), slowest


def discourse_filler_count(sents):
    """Count of sentences that OPEN on a discourse-filler word, using
    score.py's own DISCOURSE_OPENER regex — a speaking-habit note, not a
    scoring feature."""
    hits = []
    for s in sents:
        m = DISCOURSE_OPENER.match(s["text"].strip())
        if m:
            hits.append((s["start"], m.group(0).strip(" ,")))
    return hits


def next_time_list(hook_ok, overall_wpm, slowest, filler_hits):
    """A prioritized 3-item 'next time you film' list, built from whichever
    signals are weakest — always exactly 3, always concrete."""
    candidates = []
    if not hook_ok:
        candidates.append((3, "Script the first line before hitting record — lead with the "
                              "hook (age callout, plateau question, or a number), not a "
                              "warm-up sentence. The first 1-3s decide the whole watch."))
    if slowest and slowest[0] < 110:
        candidates.append((2, f"Cut or tighten the {mmss(slowest[1])}-{mmss(slowest[1]+WPM_WINDOW)} "
                              f"stretch ({slowest[0]:.0f} wpm vs your overall pace) — it's the "
                              "slowest minute in the episode and where viewers are most likely "
                              "to drop."))
    if len(filler_hits) >= 5:
        candidates.append((2, f"Cut the discourse fillers ({len(filler_hits)} sentences open on "
                              "\"seriously,\"/\"honestly,\"/\"I mean,\" etc.) — each one is a "
                              "small restart that costs momentum."))
    candidates.append((1, "End on the payoff line, not a trailing thought — the last sentence "
                          "should answer the hook so a clip cut from the close still lands."))
    candidates.append((1, "Keep one complete idea per 30-60s stretch so more of the episode is "
                          "directly clip-able without a re-cut."))
    candidates.sort(key=lambda c: -c[0])
    out = [c[1] for c in candidates[:3]]
    while len(out) < 3:
        out.append("Re-watch this episode's top-scoring clip and repeat that opening pattern "
                    "on purpose next time.")
    return out[:3]


def dominant_topic_bank_hooks(full_text, k=3):
    """2-3 quality-a hook-BANK lines matched to the SOURCE VIDEO's dominant
    topic (by keyword count across the whole transcript, using score.py's
    _bank_topics_for lexicon), for the 'next time you film' section. Distinct
    from bank_onscreen_alternative() (which matches ONE clip's text) -- this
    scans the full episode so the suggestion reflects what the video was
    mostly about, not just one moment. Falls back to 'any'-tagged hooks if no
    topic keyword fires anywhere in the episode. Deterministic order (bank
    order), capped at k, never duplicated."""
    if not HOOK_BANK:
        return None, []
    from collections import Counter
    counts = Counter({topic: len(pat.findall(full_text))
                      for topic, pat in _BANK_TOPIC_LEXICON.items()})
    dominant = max(counts, key=counts.get) if any(counts.values()) else None
    out = []
    for h in HOOK_BANK:
        fits = set(h.get("topic_fit") or [])
        if dominant and dominant not in fits and "any" not in fits:
            continue
        if not dominant and "any" not in fits:
            continue
        if not _bank_hook_fillable(h["text"]):
            continue
        out.append(h["text"])
        if len(out) >= k:
            break
    return dominant, out


def source_video_section(video_id, srt_path):
    lines = ["## B) Source-video critique\n"]
    if not srt_path or not os.path.exists(srt_path):
        lines.append(f"_no SRT found at {srt_path} — skipping source-video critique._")
        return lines

    sents = sentences_from_srt(srt_path)
    words = words_with_ts(srt_path)

    verdict, opener_text = opening_hook_verdict(sents)
    hook_ok = "archetype" in verdict or "keep opening" in verdict
    lines.append("**Opening-10s hook verdict:**")
    lines.append(f"- {verdict}")
    if opener_text:
        lines.append(f"  - Actual opener: _{opener_text.strip()[:200]}_")
    lines.append(f"- Stronger cold-open suggestion: {suggest_cold_open(sents, video_id)}")
    lines.append("")

    overall_wpm, slowest = wpm_pacing(words)
    lines.append("**Pacing:**")
    if overall_wpm is not None:
        lines.append(f"- Overall pace: **{overall_wpm} wpm** across the episode.")
        if slowest:
            lines.append(f"- Slowest 60s stretch: **{slowest[0]:.0f} wpm** at "
                          f"{mmss(slowest[1])}-{mmss(slowest[1] + WPM_WINDOW)} "
                          "(candidate for a tighter re-cut or a cut entirely).")
    else:
        lines.append("- not enough transcript to compute pacing.")
    lines.append("")

    filler_hits = discourse_filler_count(sents)
    lines.append("**Speaking-habit note (discourse-filler openers):**")
    lines.append(f"- {len(filler_hits)} sentence(s) open on a filler word "
                 f"(\"seriously,\"/\"honestly,\"/\"i mean,\"/etc.) out of {len(sents)} total sentences.")
    if filler_hits:
        sample = ", ".join(f"{mmss(t)} \"{w}\"" for t, w in filler_hits[:6])
        lines.append(f"  - e.g. {sample}{'…' if len(filler_hits) > 6 else ''}")
    lines.append("")

    lines.append("**Next time you film (prioritized):**")
    for i, item in enumerate(next_time_list(hook_ok, overall_wpm, slowest, filler_hits), 1):
        lines.append(f"{i}. {item}")
    lines.append("")

    full_text = " ".join(s["text"] for s in sents)
    dominant, bank_suggestions = dominant_topic_bank_hooks(full_text)
    if bank_suggestions:
        topic_note = f" (dominant topic: **{dominant}**)" if dominant else " (no dominant topic detected, general picks)"
        lines.append(f"**Hook-bank picks for next time you film{topic_note}:**")
        for h in bank_suggestions:
            flags = brand_flags(h)
            flag_note = f"  _(flag: {'; '.join(flags)})_" if flags else ""
            lines.append(f"- {h}{flag_note}")
        lines.append("")
    return lines


# ---- main --------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("moments_json")
    ap.add_argument("--top", type=int, default=TOP_N)
    a = ap.parse_args()

    d = json.load(open(a.moments_json))
    video_id = d.get("video_id", os.path.splitext(os.path.basename(a.moments_json))[0])
    workdir = os.path.dirname(os.path.abspath(a.moments_json))

    moments = [m for m in d.get("moments", []) if m.get("gate_passed")]
    moments.sort(key=lambda m: -m["score"])
    top = moments[:a.top]

    lines = [f"# Improvement advice — {video_id}",
             f"_ob-moments advisor · deterministic, no LLM · {len(top)} of "
             f"{len(moments)} gate-passed moments critiqued_\n",
             "## A) Per-clip critique\n"]
    for rank, m in enumerate(top, 1):
        lines += per_clip_section(m, rank)

    srt_path = os.path.join(workdir, f"{video_id}.en.srt")
    lines += source_video_section(video_id, srt_path)

    out_path = os.path.join(workdir, f"{video_id}.advice.md")
    open(out_path, "w").write("\n".join(lines))
    print(f"[advise] {len(top)} clip(s) critiqued -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
