#!/usr/bin/env python3
"""
ig_post.py — the ob-moments Instagram POST package generator.

Consumes work/<id>.moments.json (score.py's output) and produces, for every
gate-passed moment, a full IG post package: caption (hook + body + CTA),
hashtags, posting window, cover-frame timestamp, and a loop note. Grounded in
data/ig-performance-patterns.json's actual findings from posts-master.csv
(6,387 real Reels) — not generic social-media advice.

Deterministic, stdlib-only, no LLM calls. Reuses score.py's mmss()/hook
archetype machinery and advise.py's brand-safety pass (no em-dashes, no
"not X it's Y" stacking, never "free", never a price) so this tool can never
ship copy that violates OB's brand rules.

Writes:
  - work/<id>.igposts.md            (human-readable package per clip)
  - work/<id>.moments.json          (read-modify-write: merges an "ig_post"
                                      object into each gate-passed moment,
                                      preserving every other field untouched)

Usage:
    python3 bin/ig_post.py work/<id>.moments.json
"""
import sys, os, re, json, argparse, copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import mmss, NUMBER

# reuse advise.py's brand-safety detectors so "no em-dash / no AI-tell" stays
# in exactly one place across the toolset
from advise import brand_flags, strip_brand_issues, EM_DASH

# ---- hard brand rules (in addition to advise.py's em-dash / AI-tell pass) --
FREE_WORD = re.compile(r"\bfree\b", re.I)
PRICE_RE = re.compile(r"\$\s?\d|\b\d+\s?(?:dollars?|bucks?|/mo|per month|a month)\b", re.I)
YT_DOMAIN = re.compile(r"ob-health\.com", re.I)


def brand_flags_full(text):
    """OB's full IG brand-safety pass: advise.py's em-dash/AI-tell check,
    plus the three rules unique to this tool (no 'free', no price, never
    route to ob-health.com — that domain is YouTube-only per CTA routing)."""
    flags = list(brand_flags(text))
    if FREE_WORD.search(text):
        flags.append("'free' used in an offer context — never use 'free' in OB copy")
    if PRICE_RE.search(text):
        flags.append("price/dollar amount detected — never name a price in pre-call/IG copy")
    if YT_DOMAIN.search(text):
        flags.append("routes to ob-health.com — IG must route to comment-keyword or bio, "
                      "never the YouTube-only domain")
    return flags


# ---- caption-topic -> comment-keyword lexicon ------------------------------
# OB's proven pattern per data/ig-performance-patterns.json's
# caption_templates_from_winners: "comment WORD and I'll ..." / "DM me or
# comment READY for 1 on 1 fitness coaching". The keyword should read like a
# natural instruction tied to the clip's own topic, not a generic READY every
# time — variety keyed off topic, falling back to READY (the account's most
# reused winning template) when no topic keyword matches.
_TOPIC_KEYWORD = [
    (r"\bfiber\b", "FIBER"),
    (r"\bprotein\b", "PROTEIN"),
    (r"\bcalor(?:ie|y)|maintenance calories\b", "CALORIES"),
    (r"\bmeal plans?\b", "PLAN"),
    (r"\bhormones?\b", "HORMONES"),
    (r"\byo-?yo|gain(?:ed)? back|regain\b", "RESET"),
    (r"\bcardio\b", "CARDIO"),
    (r"\bhabits?\b", "HABITS"),
    (r"\bmetaboli[sz]m\b", "METABOLISM"),
]


def topic_keyword(text, hook=""):
    """Pick the keyword for the clip's DOMINANT topic, not the first lexicon entry
    that happens to appear anywhere. (Bug caught by the W4 adversarial verify: a
    protein clip that merely mentioned fiber got 'Comment FIBER' — bait-and-switch.)
    Score = occurrence count in the clip text, +3 if the topic is in the hook line."""
    best_kw, best_score = "READY", 0
    for pat, kw in _TOPIC_KEYWORD:
        n = len(re.findall(pat, text, re.I))
        if not n:
            continue
        score = n + (3 if hook and re.search(pat, hook, re.I) else 0)
        if score > best_score:
            best_kw, best_score = kw, score
    return best_kw


def comment_cta(m):
    """Build the CTA line. Comment-lever clips (or any clip whose text reads
    as a live debate) get a debate question instead of a coaching pitch,
    per the brief. Everything else gets OB's proven comment-keyword CTA,
    reusing the account's single most-reused winning template shape:
    '<short reaction/line>, comment <WORD> and I'll <payoff>.'"""
    lever = m.get("engagement_lever")
    if lever == "comment":
        return debate_question(m)
    kw = topic_keyword(m.get("text", ""), m.get("hook_line", ""))
    payoff_map = {
        "FIBER": "send you the exact daily fiber target for your gender",
        "PROTEIN": "send you how to figure out your daily protein target",
        "CALORIES": "walk you through how to find your real maintenance calories",
        "PLAN": "explain why a generic plan keeps failing you and what actually works",
        "HORMONES": "break down what's actually happening with your hormones",
        "RESET": "show you how to stop the regain cycle for good",
        "CARDIO": "explain what actually moves the needle instead",
        "HABITS": "send you the habit-tracking system my clients use",
        "METABOLISM": "explain what's really going on with your metabolism",
        "READY": "walk you through 1 on 1 coaching",
    }
    payoff = payoff_map.get(kw, "walk you through it")
    return f"Comment {kw} and I'll {payoff}."


def debate_question(m):
    """A one-line debate question built from the clip's own text, for
    comment-lever clips (per the brief: 'comment-lever clips get a debate
    question instead'). Deterministic — pulled from the clip's own claim,
    never invented."""
    text = m.get("text", "")
    nm = NUMBER.search(text)
    if nm:
        return f"Agree or disagree: {m['hook_line'].rstrip('.!?')}? Tell me in the comments."
    return f"Where do you land on this: {m['hook_line'].rstrip('.!?')}? Comment below."


# ---- caption body -----------------------------------------------------------
def hook_line_for_caption(m):
    """First caption line = clip's own onscreen_hook, punched up slightly if
    it trails off with an ellipsis (onscreen_hook is a truncated preview
    string in moments.json), else the full hook_line."""
    onscreen = (m.get("onscreen_hook") or "").strip()
    hook = (m.get("hook_line") or "").strip()
    if onscreen and not onscreen.endswith("…") and not onscreen.endswith("..."):
        base = onscreen
    else:
        base = hook if hook else onscreen.rstrip(".… ")
    base = base.rstrip(".")
    if not base.endswith((".", "!", "?")):
        base += "."
    return strip_brand_issues(base)


# body sentences drawn straight from the clip's own text (no fabrication) —
# split on sentence boundaries, drop the first sentence (already used as the
# hook), keep 2-4 short follow-on lines that carry the payoff.
SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')


def body_lines(m, n=3):
    text = m.get("text", "")
    sents = [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]
    hook_first = sents[0] if sents else ""
    rest = sents[1:] if len(sents) > 1 else []
    # prefer short, punchy sentences (<=18 words) for an IG caption body;
    # keep original order (don't reshuffle the clip's own logic)
    short_rest = [s for s in rest if len(s.split()) <= 18]
    pool = short_rest if len(short_rest) >= 2 else rest
    out = []
    for s in pool:
        s = s.strip()
        if not s or s == hook_first:
            continue
        if not s.endswith((".", "!", "?")):
            s += "."
        out.append(strip_brand_issues(s))
        if len(out) >= n:
            break
    if not out and rest:
        s = rest[0].strip()
        if not s.endswith((".", "!", "?")):
            s += "."
        out = [strip_brand_issues(s)]
    return out[:4] if len(out) > 1 else (out if out else [])


def build_caption(m):
    hook = hook_line_for_caption(m)
    body = body_lines(m, n=3)
    if len(body) < 2:
        body = body_lines(m, n=4)
    cta = comment_cta(m)
    lines = [hook] + body + [cta]
    return "\n".join(lines)


# ---- hashtags ---------------------------------------------------------------
# per ig-performance-patterns.json: hashtags are essentially unused/deprecated
# on this account (0.046 avg top-decile vs 0.037 rest — negligible, low
# confidence, thin post-2024 sample). We surface that finding directly rather
# than inventing a hashtag strategy the data doesn't support, and fall back to
# a small 3-5 niche-tag set only as the brief's explicit fallback.
_FALLBACK_HASHTAGS = ["#fatloss", "#fitnesscoach", "#weightlosstips", "#sustainableweightloss",
                      "#fitover40"]
_TOPIC_HASHTAG = [
    (r"\bfiber\b", "#fiber"),
    (r"\bprotein\b", "#proteintips"),
    (r"\bcalor(?:ie|y)\b", "#caloriedeficit"),
    (r"\bhormones?\b", "#hormonehealth"),
    (r"\bmetaboli[sz]m\b", "#metabolism"),
    (r"\byo-?yo\b", "#yoyodieting"),
    (r"\bcardio\b", "#cardio"),
]


def hashtags_for(m):
    """Per the patterns file: OB's account essentially doesn't use hashtags
    (near-zero, deprecated tactic, no evidence they help). Recommend
    following that account precedent (0 hashtags) as the primary call, but
    hand over the brief's explicit fallback (3-5 niche tags) as an
    alternative in case OB wants to test them on this clip."""
    matched = [tag for pat, tag in _TOPIC_HASHTAG if re.search(pat, m.get("text", ""), re.I)]
    fallback = matched[:2] + [t for t in _FALLBACK_HASHTAGS if t not in matched]
    fallback = fallback[:5] if len(fallback) >= 3 else (fallback + _FALLBACK_HASHTAGS)[:5]
    return {
        "recommended": "0 hashtags — matches account precedent (hashtags are essentially "
                       "unused/deprecated on this account per ig-performance-patterns.json; "
                       "no evidence they help, thin sample post-2024).",
        "fallback_if_testing": fallback,
    }


# ---- posting window ---------------------------------------------------------
POSTING_WINDOW = {
    "primary": "4am-6am or 9am (cohort-controlled overrepresentation among top-decile "
               "posts; medium confidence, correlational, not proven causal).",
    "day": "Sunday or Saturday mildly favored; avoid Wednesday if choosing (small effect, "
           "low confidence — don't over-index on this alone).",
    "caveat": "Duration/posting-hour/day are all secondary to content/hook per the patterns "
              "file's strongest finding: the account's biggest hits are commentary/reaction "
              "content, not caption or scheduling mechanics.",
}


# ---- cover-frame timestamp ---------------------------------------------------
def cover_frame_timestamp(m):
    """Second (relative to clip start) of the quotable_line/peak moment, for
    picking the grid cover. Falls back to the highest-subscore proxy point
    (hook-heavy moments peak early, payoff-heavy moments peak later) when no
    quotable_line is present, since none of this dataset's moments carry a
    populated quotable_line."""
    start = m["start"]
    q = (m.get("quotable_line") or "").strip()
    if q:
        text = m.get("text", "")
        idx = text.find(q)
        if idx >= 0:
            frac = idx / max(1, len(text))
            rel = round(frac * m["dur"], 1)
            return rel, "quotable_line text position (proportional estimate within the clip)"
    # no quotable_line: use subscores to place the cover on hook (early) vs
    # payoff (later) peak — deterministic, no fabrication of a timestamp we
    # don't have data for.
    s = m.get("subscores", {})
    if s.get("payoff", 0) >= s.get("hook", 0):
        rel = round(m["dur"] * 0.75, 1)
        basis = "no quotable_line in this clip; payoff subscore >= hook subscore, so cover " \
                "placed near the clip's back third (where the payoff lands)."
    else:
        rel = round(min(3.0, m["dur"] * 0.08), 1)
        basis = "no quotable_line in this clip; hook subscore is dominant, so cover placed " \
                "at the opening beat (first ~3s) where the hook reads on mute."
    return rel, basis


# ---- loop note ---------------------------------------------------------------
_STOPWORDS = {"the", "a", "an", "and", "or", "but", "so", "of", "to", "in", "on",
              "is", "it", "you", "your", "i", "im", "that", "this", "for", "with",
              "was", "were", "at", "be", "as", "if", "then", "just", "we", "my"}


def _keywords(s):
    words = re.findall(r"[a-z']+", s.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def loop_note(m):
    """Whether the clip's last line feeds back into its first, read from
    both lines' own text. Deterministic keyword-overlap check (no fabricated
    'yes it loops' claims) plus a concrete one-line fix when it doesn't."""
    text = m.get("text", "")
    sents = [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]
    if len(sents) < 2:
        return {
            "loops": False,
            "evidence": "clip is a single sentence; nothing to compare first/last against.",
            "fix": "extend the out-point by one sentence so the clip ends on a line that "
                   "echoes the opening hook, or add a spoken/on-screen callback line in the edit.",
        }
    first, last = sents[0], sents[-1]
    first_kw, last_kw = _keywords(first), _keywords(last)
    overlap = first_kw & last_kw
    if overlap:
        return {
            "loops": True,
            "evidence": f"last line ('{last[:80]}{'…' if len(last) > 80 else ''}') shares "
                        f"{', '.join(sorted(overlap))} with the opening hook "
                        f"('{first[:80]}{'…' if len(first) > 80 else ''}') — replay reads as "
                        "intentional, good for retention.",
            "fix": "",
        }
    return {
        "loops": False,
        "evidence": f"last line ('{last[:80]}{'…' if len(last) > 80 else ''}') does not share "
                    f"any keyword with the opening hook ('{first[:80]}{'…' if len(first) > 80 else ''}') "
                    "— a replay will feel like a hard cut, not a loop.",
        "fix": f"trim the out-point back to a sentence that reuses the hook's own key term, "
               f"or add one final on-screen/spoken line that restates \"{first[:60]}"
               f"{'…' if len(first) > 60 else ''}\" so the loop is intentional.",
    }


# ---- per-clip package assembly -----------------------------------------------
def build_ig_post(m):
    caption = build_caption(m)
    ht = hashtags_for(m)
    cover_ts, cover_basis = cover_frame_timestamp(m)
    loop = loop_note(m)

    all_proposed_text = caption + "\n" + " ".join(ht["fallback_if_testing"])
    flags = brand_flags_full(all_proposed_text)

    return {
        "caption": caption,
        "hashtags": ht,
        "posting_window": POSTING_WINDOW,
        "cover_frame": {
            "timestamp_sec": cover_ts,
            "timestamp_mmss": mmss(cover_ts),
            "basis": cover_basis,
        },
        "loop_note": loop,
        "brand_flags": flags,
    }


# ---- markdown writer ---------------------------------------------------------
def write_md(path, vid, moments_with_posts):
    lines = [f"# IG post packages — {vid}",
             f"_ob-moments IG post generator · {len(moments_with_posts)} gate-passed "
             "clip(s) · grounded in data/ig-performance-patterns.json_\n"]
    for rank, m in enumerate(moments_with_posts, 1):
        ig = m["ig_post"]
        lines += [
            f"## {rank}. {m['title']}  ({mmss(m['start'])}-{mmss(m['end'])}, {m['dur']}s) "
            f"· score {m['score']} · lever: **{m['engagement_lever']}**",
            "",
            "**CAPTION:**",
            "```",
            ig["caption"],
            "```",
            "",
            "**HASHTAGS:**",
            f"- Recommended: {ig['hashtags']['recommended']}",
            f"- Fallback if testing: {' '.join(ig['hashtags']['fallback_if_testing'])}",
            "",
            "**POSTING WINDOW:**",
            f"- Time: {ig['posting_window']['primary']}",
            f"- Day: {ig['posting_window']['day']}",
            f"- Caveat: {ig['posting_window']['caveat']}",
            "",
            "**COVER-FRAME TIMESTAMP:**",
            f"- {ig['cover_frame']['timestamp_mmss']} into the clip "
            f"({ig['cover_frame']['timestamp_sec']}s) — {ig['cover_frame']['basis']}",
            "",
            "**LOOP NOTE:**",
            f"- Loops: {'yes' if ig['loop_note']['loops'] else 'no'}",
            f"- {ig['loop_note']['evidence']}",
        ]
        if ig["loop_note"]["fix"]:
            lines.append(f"- Fix: {ig['loop_note']['fix']}")
        lines.append("")
        lines.append("**BRAND CHECK:**")
        if ig["brand_flags"]:
            for f in ig["brand_flags"]:
                lines.append(f"- FLAG: {f}")
        else:
            lines.append("- clean — no em-dashes, no 'free', no price, no ob-health.com routing.")
        lines.append("")
    open(path, "w").write("\n".join(lines))


# ---- main ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("moments_json")
    a = ap.parse_args()

    path = a.moments_json
    d = json.load(open(path))
    vid = d.get("video_id", os.path.splitext(os.path.basename(path))[0])
    workdir = os.path.dirname(os.path.abspath(path))

    moments = d.get("moments", [])
    passed_with_posts = []
    updated_moments = []
    for m in moments:
        m2 = copy.deepcopy(m)
        if m2.get("gate_passed"):
            m2["ig_post"] = build_ig_post(m2)
            passed_with_posts.append(m2)
        updated_moments.append(m2)

    # read-modify-write moments.json safely: only add/replace the "ig_post"
    # key on each gate-passed moment; every other field/order is preserved.
    d["moments"] = updated_moments
    tmp_path = path + ".tmp"
    json.dump(d, open(tmp_path, "w"), indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)

    mdpath = os.path.join(workdir, f"{vid}.igposts.md")
    write_md(mdpath, vid, passed_with_posts)

    print(f"[ig_post] {len(passed_with_posts)}/{len(moments)} gate-passed clip(s) -> "
          f"{mdpath}\n[ig_post] merged ig_post objects into -> {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
