#!/usr/bin/env python3
"""
score.py — the ob-moments Phase-1 virality brain.

Scores candidate clip windows from a transcript on a 10-feature, research-backed
rubric (weights sum to 100), applies two hard gates, tags each survivor with its
engagement lever + buyer-relevance, and writes work/<id>.moments.{json,md}.

Two scoring paths, and the deterministic one is a first-class fallback:
  • LLM path (optional): a single batched pass refines the subjective features
    (hook nuance, arousal, controversy, quotable) via `claude -p`, then the
    Anthropic API if ANTHROPIC_API_KEY is set.
  • Deterministic path (default when no backend / --no-llm): every feature is
    scored purely with regex + curated lexicons (a ~140-term high-arousal lexicon
    with a valence-swing bonus, aphorism/contrast/metaphor quotable detection, an
    open-loop curiosity detector) plus the hook-archetype library. No new deps.
The deterministic path always runs first, so the tool produces usable picks even
when the LLM pass is skipped or unavailable; the LLM pass only overwrites the four
subjective features when a backend answers.

Weights are calibration-informed (2026-07, era-adjusted n=544 Shorts) — see W.

Usage:
    python3 score.py work/<id>.en.srt [--id VIDEO_ID] [--no-llm] [--top N]
"""
import sys, os, re, json, subprocess, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from window import sentences_from_srt, make_windows

# ---- weights (sum = 100) ---------------------------------------------------
# CALIBRATION-INFORMED (2026-07, era-adjusted n=544 real Shorts). The Shorts-views
# test had low statistical power, so these are evidence-nudges, NOT a wholesale refit
# (a full data-refit would overfit ~544 noisy points). Findings that moved the dial:
#   • controversy ρ = -0.106 (NEGATIVE) — OB's 30-45 buyers penalize hot-takes/ragebait.
#     Anti-ragebait is on-brand, so controversy is de-weighted 8 -> 3 AND high controversy
#     is turned into a mild DEMOTION downstream (see finalize()'s brand-safety penalty).
#   • numbers/specificity ρ = +0.085 (positive) — concrete stats travel. Raised 6 -> 10.
#   • hook ρ ≈ 0 on Shorts VIEWS — no measurable signal — but the hook still decides
#     whether the BODY is ever watched, so it stays the top CLIP-SELECTION weight (22 -> 23,
#     absorbing the +1 that re-normalizes the set to 100). Its multiplier is separately
#     SOFTENED in finalize() so a middling opener is no longer punished as hard.
# Re-normalized to sum to exactly 100. Other modules import W by these exact keys — do
# not rename keys or change the set of features.
W = {
    "hook": 23, "curiosity": 14, "arousal": 14, "context": 12, "payoff": 10,
    "numbers": 10, "list": 5, "you": 5, "quotable": 4, "controversy": 3,
}

# ---- lexicons / patterns ---------------------------------------------------
CONTRARIAN = re.compile(r"\b(everyone thinks|most people think|the truth is|nobody tells you|"
                        r"what (?:no one|nobody) (?:tells|talks about)|myth|you'?re wrong|"
                        r"it'?s a lie|the industry|they lie|stop believing|actually)\b", re.I)
WARNING = re.compile(r"\b(stop|never|don'?t|the mistake|worst|avoid|warning|ruin(?:ed|ing)?|destroy)\b", re.I)
NUMBER = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(%|percent|lbs?|pounds?|kg|calories?|cals?|grams?|g\b|"
                    r"months?|weeks?|days?|years?|hours?|minutes?|x|times|dollars?|\$)", re.I)
NUM_ANY = re.compile(r"\b\d+(?:[.,]\d+)?\b")
QUESTION = re.compile(r"\?")
YOU = re.compile(r"\b(you|your|you'?re|you'?ve|yourself)\b", re.I)
CURIOSITY = re.compile(r"\b(here'?s why|the reason|what most people don'?t|let me tell you|"
                       r"the crazy part|here'?s the thing|what happened|the secret|"
                       r"you won'?t believe|this is why|the problem is)\b", re.I)
PAYOFF = re.compile(r"\b(so the answer|that'?s why|the point is|do this instead|here'?s what|"
                    r"the key is|what i (?:did|do|teach)|the solution|instead of|that'?s how)\b", re.I)
CONTEXT_NEG = re.compile(r"\b(like i said|as i (?:said|mentioned)|as we (?:talked|discussed)|"
                         r"that thing|like we (?:said|were saying)|earlier i|going back to)\b", re.I)
LIST = re.compile(r"\b(\d+\s+(?:things|ways|reasons|mistakes|steps|tips|secrets|rules)|"
                  r"first(?:ly)?|second(?:ly)?|third(?:ly)?|number one|the one thing|"
                  r"here are)\b", re.I)
# ---- high-arousal lexicon (curated, ~140 terms across 4 affect clusters) ----
# Deterministic emotion signal for the NO-LLM path. High-arousal = strong activation
# regardless of valence (awe/excitement, anger, fear/anxiety, plus disgust/urgency),
# which is what actually predicts sharing — NOT calm-positive or calm-negative words.
# Multi-word phrases are matched first (see AROUSAL_PHRASES); single tokens allow simple
# suffixes via the \w* tail so "shock" catches shocked/shocking/shockingly.
_AROUSAL_AWE = [  # awe / excitement / astonishment (high positive activation)
    "insane", "insanely", "unreal", "unbelievable", "incredible", "incredibly",
    "mindblowing", "jaw", "staggering", "astonishing", "astounding", "shock",
    "shocking", "stunned", "stunning", "explode", "explosive", "wild", "crazy",
    "mind", "epic", "phenomenal", "extraordinary", "insanity", "unimaginable",
    "gamechanger", "revolutionary", "breakthrough", "obsessed", "addicted",
    "electric", "spectacular", "miracle", "unstoppable", "life-changing",
    "lifechanging", "supercharge", "skyrocket", "skyrocketed", "exploded",
]
_AROUSAL_ANGER = [  # anger / outrage (high negative activation)
    "furious", "outraged", "outrageous", "outrage", "rage", "enraged", "livid",
    "fuming", "pissed", "disgusted", "disgusting", "disgust", "sick", "fed",
    "infuriating", "infuriated", "scam", "scams", "scammed", "fraud", "lied",
    "lie", "lies", "lying", "liar", "cheat", "cheated", "cheating", "ripoff",
    "rip-off", "robbed", "betrayed", "betrayal", "shameless", "criminal",
    "corrupt", "predatory", "exploit", "exploited", "exploiting", "hate",
    "hated", "despise", "appalling", "appalled", "unacceptable",
]
_AROUSAL_FEAR = [  # fear / anxiety / dread (high negative activation)
    "terrified", "terrifying", "terror", "scared", "scary", "afraid", "fear",
    "feared", "petrified", "panic", "panicked", "panicking", "dread", "dreaded",
    "horrified", "horrifying", "horror", "nightmare", "dangerous", "danger",
    "deadly", "lethal", "fatal", "toxic", "poison", "poisoning", "kill",
    "killing", "killed", "died", "dying", "death", "ruin", "ruined", "ruining",
    "destroy", "destroyed", "destroying", "wreck", "wrecked", "devastating",
    "devastated", "catastrophe", "catastrophic", "disaster", "disastrous",
    "collapse", "collapsed", "crisis", "emergency", "warning", "alarming",
    "threat", "threatening", "risk", "risky", "trapped", "helpless", "hopeless",
    "desperate", "desperation", "spiral", "spiraling", "overwhelmed", "brutal",
    "brutally", "horrible", "horrific",
]
_AROUSAL_URGENCY = [  # surprise / urgency / near-miss intensifiers
    "suddenly", "instantly", "nearly", "barely", "almost", "finally",
    "immediately", "urgent", "urgently", "critical", "crucial", "desperately",
    "screaming", "crying", "sobbing", "trembling", "shaking", "heartbreaking",
    "heartbroken", "gut-wrenching", "shattered", "broke", "broken",
]
_AROUSAL_WORDS = set(_AROUSAL_AWE + _AROUSAL_ANGER + _AROUSAL_FEAR + _AROUSAL_URGENCY)
AROUSAL = re.compile(r"\b(" + "|".join(sorted(_AROUSAL_WORDS, key=len, reverse=True))
                     + r")\w*\b", re.I)
# multi-word high-arousal phrases (checked separately so word-boundary tokens can't miss them)
AROUSAL_PHRASES = re.compile(
    r"(blew my mind|blow your mind|mind[- ]?blowing|out of nowhere|scared to death|"
    r"worst mistake|can'?t believe|couldn'?t believe|never seen anything|"
    r"changed my life|freaked out|lost everything|hit rock bottom|fell apart|"
    r"woke me up|red flag|wake[- ]?up call|the truth about|nobody warns you)", re.I)
# valence swing: a negative setup that resolves positive inside the same clip = arc payoff
_NEG_CUE = re.compile(r"\b(struggl\w*|fail\w*|stuck|broke|broken|rock bottom|worst|"
                      r"couldn'?t|gave up|hopeless|miserable|lost|fat|ashamed|"
                      r"embarrass\w*|hated|depress\w*|desperate|quit|plateau\w*)\b", re.I)
_POS_CUE = re.compile(r"\b(finally|transform\w*|breakthrough|turned (?:it |things )?around|"
                      r"changed everything|now i|today i|figured (?:it|this) out|"
                      r"the answer|freedom|in control|thriving|unstoppable|proud|"
                      r"never looked back|best shape|down \d+|lost \d+)\b", re.I)
CONTROVERSY = re.compile(r"\b(unpopular opinion|hot take|people won'?t like|controversial|"
                         r"everyone is wrong|the industry lies|scam|lie to you|hate me|"
                         r"triggered|say it louder)\b", re.I)
PRONOUN_START = re.compile(r"^\s*(and |but |or |so |because |he |she |they |it |that |this |then |"
                           r"which |where |cuz |'?cause)", re.I)
# conversational-filler openers signal a mid-conversation lead-in, not a scroll-stopper.
# The trigger counter can't tell "Seriously, because you don't..." (filler + surface
# question/you/warning tokens) from a real hook, so we demote these openers explicitly.
DISCOURSE_OPENER = re.compile(r"^\s*(seriously|honestly|basically|literally|actually|anyway|"
                              r"anyways|look|listen|okay|ok|well|like|yeah|right|frankly|"
                              r"i mean|you know|you see|real talk|now)\b[,\s]", re.I)

FIRST_SENT = re.compile(r'^.*?[.!?]["\')]?(?:\s|$)')


def first_sentence(text):
    m = FIRST_SENT.match(text.strip())
    return (m.group(0) if m else text[:160]).strip()


def short_hook(sentence, maxwords=9):
    """A clean, short on-screen headline from a sentence: strip a filler opener,
    cap at a WORD boundary (never mid-word), drop trailing punctuation. Used so the
    burned-in headline is a real hook, not a chopped '...to gi' transcript fragment."""
    # strip BOTH a discourse opener and a leading conjunction ("So,"/"And,"/"But,")
    # BEFORE counting words — otherwise the opener eats a word slot and the real
    # hook truncates a word early ("...for your caloric…" instead of the complete
    # "...for your caloric intake"). clean_headline strips CONJ_OPENER too, but that
    # runs downstream, after this cap has already chopped the noun phrase.
    s = DISCOURSE_OPENER.sub("", sentence.strip()).strip()
    s = CONJ_OPENER.sub("", s).strip()
    words = s.split()
    if len(words) <= maxwords:
        return s.rstrip(" ,;:—-") or sentence[:40]
    kept = words[:maxwords]
    # never end a burned-in headline on a dangling function word ("...FOR YOUR
    # CALORIC..." read broken on a real render) — backtrack past the trailing
    # prepositional/possessive tail to the last content word
    _TAIL = {"for", "your", "my", "our", "their", "a", "an", "the", "of", "to",
             "with", "in", "on", "at", "and", "or", "but", "that", "this", "is",
             "are", "was", "be", "you", "it"}
    while len(kept) > 3 and kept[-1].strip(".,!?:;\"'").lower() in _TAIL:
        kept.pop()
    return " ".join(kept).rstrip(" ,;:—-") + "…"


def _quotable_headline(llm):
    """Use the LLM's extracted quote as the headline only if it's short enough."""
    q = ((llm or {}).get("quotable_line") or "").strip()
    return q if q and len(q.split()) <= 12 else None


# conjunction lead-ins safe to strip from a headline ("So, it's not your fault"
# -> "It's not your fault"). Deliberately excludes pronouns (stripping "it/this"
# would break the sentence).
CONJ_OPENER = re.compile(r"^\s*(and|but|or|so|then|because|cuz|'?cause)\b[,\s]+", re.I)
_PLACEHOLDER = re.compile(r"\[([A-Z][A-Z0-9 /_-]*)\]")


def clean_headline(s):
    """Brand-safe headline: no em-dashes (OB's #1 AI tell), no double spaces,
    no leading conjunction/filler, capitalized first letter."""
    if not s:
        return s
    s = re.sub(r"\s*—\s*", ", ", s).strip()
    s = DISCOURSE_OPENER.sub("", s)
    s = CONJ_OPENER.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,;:-")
    return (s[:1].upper() + s[1:]) if s else s


def fill_onscreen_template(tmpl, text):
    """Fill an archetype on-screen template's [PLACEHOLDERS] strictly from the
    clip's OWN text (never invent facts). Numbers pop in order for [N]/[NUMBER];
    [AGE] needs an explicit 'over NN' in the clip. Any unfillable placeholder
    makes the whole template unusable -> None (caller falls back to the spoken
    hook), so a raw '[AGE]' can never be burned into a clip again."""
    if not tmpl:
        return None
    numbers = NUM_ANY.findall(text)
    out = tmpl
    for m in _PLACEHOLDER.finditer(tmpl):
        key = m.group(1).strip()
        if key == "AGE":
            m2 = re.search(r"\bover\s+(\d{2})\b", text, re.I)
            val = m2.group(1) if m2 else None
        elif key in ("N", "NUMBER"):
            # UNIT-AWARE fill: "[N] LBS"/"[N] MONTHS" must take a number that is
            # actually attached to that unit in the clip's text — naive in-order
            # filling once produced "20 LBS IN 25 MONTHS" from "lost 20 lbs...
            # gained 25 lbs back" (real numbers, fabricated pairing).
            after = tmpl[m.end():].lstrip()
            unit_m = re.match(r"([A-Za-z]{3,})", after)
            if unit_m:
                stem = unit_m.group(1)[:4]
                m2 = re.search(rf"\b(\d+(?:[.,]\d+)?)\s*{re.escape(stem)}", text, re.I)
                val = m2.group(1) if m2 else None
            else:
                val = numbers.pop(0) if numbers else None
        else:
            val = None                     # unknown placeholder -> unusable
        if val is None:
            return None
        out = out.replace(m.group(0), val, 1)
    return clean_headline(out)


# broad bracket-content matcher (unlike _PLACEHOLDER, which requires an
# UPPERCASE-leading key) — some rewrite_templates use a lowercase/digit-leading
# literal example inside brackets as a stand-in for a semantic slot (e.g. the
# hook library's own "[40s]", "[25]", "[280]", "[180]"), which _PLACEHOLDER
# silently ignores and fill_onscreen_template would then pass straight through
# unfilled. Any survivor of this broad pattern after filling means the template
# is unusable here -> reject it rather than ever burn a literal bracket in.
_ANY_BRACKET = re.compile(r"\[[^\]]*\]")


def fill_rewrite_template(tmpl, text):
    """Fill a hook-library REWRITE template (a full rewritten opening line, not
    the ALL-CAPS onscreen shape) using the exact same strictly-from-clip-text
    discipline as fill_onscreen_template: only [AGE] (from an explicit 'over NN')
    and [N]/[NUMBER] (unit-aware, in-order fallback) are fillable; any other
    placeholder — including lowercase/digit-leading literal-example brackets
    like '[40s]'/'[25]' that fill_onscreen_template's stricter key regex doesn't
    even recognize as a placeholder — makes the template unusable -> None so the
    caller tries the next template rather than ever burning a literal
    '[BRACKET]' into a headline."""
    filled = fill_onscreen_template(tmpl, text)
    if filled is None:
        return None
    if _ANY_BRACKET.search(filled):
        return None
    return filled


def rewrite_headline(text):
    """VIRAL-FIRST headline rewrite (2026-07): when a moment's spoken opener
    doesn't match a known hook archetype and its regex hook score is weak, the
    on-screen headline is the strongest lever we control (research basis: on
    mute, the burned-in first-frame text IS the hook). Try each archetype's
    rewrite_templates in strength order — same fill-or-skip discipline as
    fill_onscreen_template — and return the first one that fills cleanly from
    the clip's OWN text. Returns None if nothing fills (caller keeps the
    current spoken-hook-derived headline unchanged).

    GATED on the archetype's OWN spoken_cues actually matching this clip's text
    (not just "does the template fill") — a bracket-free canned template like
    relatable_pain_pov's "POV: you've counted every calorie..." has nothing to
    fill and would otherwise trivially "succeed" on ANY clip, stamping the same
    generic line onto unrelated moments across different episodes. Requiring the
    archetype to actually match keeps the rewrite grounded in this clip's content.

    FALLS BACK to the hook BANK (data/hook-bank.json) when no archetype rewrite
    fills: picks a quality-a bank hook whose topic_fit matches this clip's own
    topic keywords and whose placeholders (if any) are strictly fillable, See
    bank_headline() for the topic/fill/mechanism-diversity discipline — same
    "never invent facts, reject rather than guess" rule as the archetype path."""
    for a in HOOK_ARCHETYPES:
        if not any(p.search(text) for p in a["pats"]):
            continue
        for tmpl in a.get("rewrite_templates", []):
            filled = fill_rewrite_template(tmpl, text)
            if filled:
                return filled
    return bank_headline(text)


# ---- regex feature scorers (0-100 each) ------------------------------------
def f_hook(text, first=None):
    # `first` = the window's REAL first sentence when known. The regex fallback
    # runs to the next '.', which on unpunctuated speaker-turn fragments ("If you
    # don't") silently swallows the NEXT speaker's words too.
    s = first if first is not None else first_sentence(text)
    trig = 0
    if QUESTION.search(s): trig += 1
    if CONTRARIAN.search(s): trig += 1
    if NUMBER.search(s): trig += 1
    if WARNING.search(s): trig += 1
    if YOU.search(s): trig += 1
    score = min(100, 40 * trig)
    if PRONOUN_START.match(s):        # context-leak opener
        score = max(0, score - 35)
    if DISCOURSE_OPENER.match(s):     # conversational-filler lead-in ("Seriously,", "I mean,")
        score = max(0, score - 30)
    if len(s.split()) < 4:            # fragment opener ("If you don't") — trigger
        score = min(score, 25)        # words without substance can't carry a hook
    # ASR-garble opener ("If A MOST serving sizes...", doubled words): burned into
    # the headline, this reads broken and kills credibility in the first second
    if (re.search(r"\b(?:a|an|the)\s+(?:most|many|all|the|a|an)\b", s, re.I)
            or re.search(r"\b(\w+)\s+\1\b", s, re.I)):
        score = min(score, 25)
    return score


def f_curiosity(text):
    """Open-loop / information-gap strength in the clip's opening. Layers the
    explicit curiosity cues, an unresolved question, and softer gap signals
    (demonstratives without a referent, teased reveals, 'reason/why' framing)."""
    head = " ".join(text.split()[:40])
    score = 15
    if CURIOSITY.search(head):
        score = max(score, 70)
    if QUESTION.search(head):
        score = max(score, 40)
    # softer open-loop signals
    if re.search(r"\b(here'?s (?:the|what|why|how)|turns out|it turns out|"
                 r"what (?:i|they|you) (?:found|learned|realized)|the (?:real |one )?reason|"
                 r"nobody (?:tells|talks about)|until (?:i|you)|watch what happens)\b",
                 head, re.I):
        score = max(score, 60)
    # a demonstrative pointing at a not-yet-named thing = dangled gap
    if re.search(r"\b(this one|that one|this thing|one (?:mistake|trick|habit|thing|reason))\b",
                 head, re.I):
        score = max(score, 55)
    return score


def f_arousal(text):
    """Peak emotional activation from a curated lexicon (awe/anger/fear/urgency),
    high-arousal phrases, and a valence-swing (neg setup -> pos resolution) bonus.
    Distinct lemmas count more than the same word repeated, so intensity isn't
    faked by one word echoed; density is length-normalized so a long calm clip
    with two hot words doesn't read as white-hot."""
    lc = text.lower()
    lemmas = {m.group(0).lower() for m in AROUSAL.finditer(lc)}
    total_hits = len(AROUSAL.findall(lc))
    phrase_hits = len(AROUSAL_PHRASES.findall(lc))
    n_words = max(1, len(text.split()))
    if not lemmas and not phrase_hits:
        base = 15
    else:
        # distinct emotional lemmas drive the peak; repeats + phrases add less
        base = 30 + 16 * len(lemmas) + 6 * max(0, total_hits - len(lemmas)) + 22 * phrase_hits
        # length-normalize: reward emotional *density*, not just a long transcript
        density = (total_hits + phrase_hits) / n_words
        if density < 0.012 and base > 55:
            base = 55 + (base - 55) * 0.5      # damp long low-density clips
    # valence-swing bonus: negative setup early that resolves positive later = arc
    head = " ".join(text.split()[: n_words // 2])
    tail = " ".join(text.split()[n_words // 2 :])
    if _NEG_CUE.search(head) and _POS_CUE.search(tail):
        base += 18
    return int(min(100, max(15, base)))


def f_context(text):
    neg = len(CONTEXT_NEG.findall(text))
    score = 80 - neg * 30
    if PRONOUN_START.match(first_sentence(text)):
        score -= 20
    return max(0, min(100, score))


def f_payoff(text):
    tail = " ".join(text.split()[-45:])
    return 75 if PAYOFF.search(tail) else 30


def f_controversy(text):
    return min(100, len(CONTROVERSY.findall(text)) * 55) if CONTROVERSY.search(text) else \
        (40 if CONTRARIAN.search(text) else 10)


def f_numbers(text):
    n = len(NUMBER.findall(text)) or (1 if NUM_ANY.search(text) else 0)
    return min(100, n * 30)


def f_list(text):
    return 70 if LIST.search(text) else 10


def f_you(text):
    words = text.split()
    if not words:
        return 0
    density = len(YOU.findall(text)) / len(words)
    return min(100, int(density * 900))


# quotable-line signal patterns (aphorism / contrast / metaphor / imperative)
_Q_CONTRAST = re.compile(r"\b(\w+),?\s+not\s+\w+", re.I)                      # "X not Y"
_Q_CONTRAST2 = re.compile(r"\bit'?s not (?:about )?\w+.*?\bit'?s\b", re.I)     # "it's not X it's Y"
_Q_APHORISM = re.compile(r"\b(always|never|every|no one|nobody|everyone|the only|"
                         r"the moment|once you|if you (?:want|can'?t)|you can'?t|"
                         r"you don'?t|the secret to|the difference between)\b", re.I)
_Q_METAPHOR = re.compile(r"\b(is (?:a|like|just) |are (?:a|like|just) |think of it (?:as|like)|"
                         r"it'?s like|that'?s (?:a|the) )\w+", re.I)
_Q_EQUATION = re.compile(r"\b\w+\s+is\s+\w+", re.I)                            # "X is Y" definition
_Q_IMPERATIVE = re.compile(r"^\s*(stop|start|never|always|do|don'?t|remember|forget|quit)\b", re.I)


def f_quotable(text):
    """Best single tweetable line in the clip. Rewards crisp aphoristic length,
    contrast constructions ('X not Y', 'it's not X it's Y'), definitional/metaphor
    frames ('X is Y', 'it's like ...'), and punchy imperatives — the shapes that
    survive as standalone captions/on-screen text."""
    best = 0
    for s in re.split(r'(?<=[.!?])\s+', text):
        w = s.split()
        n = len(w)
        if not (4 <= n <= 16):
            continue
        score = 38
        if 5 <= n <= 11:                       # tightest, most quotable band
            score += 8
        if _Q_CONTRAST.search(s) or _Q_CONTRAST2.search(s):
            score += 30                        # contrast is the strongest quotable shape
        if _Q_APHORISM.search(s):
            score += 20
        if _Q_METAPHOR.search(s):
            score += 16
        elif _Q_EQUATION.search(s):
            score += 10                        # plain definition (weaker than a metaphor)
        if _Q_IMPERATIVE.match(s):
            score += 12
        if NUM_ANY.search(s):
            score += 8
        if YOU.search(s):
            score += 8
        if s.rstrip().endswith("."):           # a closed declarative reads more quotable
            score += 4
        best = max(best, min(100, score))
    return best


REGEX = {
    "hook": f_hook, "curiosity": f_curiosity, "arousal": f_arousal, "context": f_context,
    "payoff": f_payoff, "controversy": f_controversy, "numbers": f_numbers, "list": f_list,
    "you": f_you, "quotable": f_quotable,
}


# ---- hook archetype library (from the hook-trend bot swarm) -----------------
def _load_hook_lib():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hook-library.json")
    try:
        lib = json.load(open(p))
    except Exception:
        return []
    out = []
    for a in lib.get("hook_archetypes", []):
        # Floor: skip archetypes with strength_prior < 45 (fatigued/low-confidence
        # patterns, e.g. general_viral tier entries explicitly scored 45-55 for
        # saturating formats). detect_archetype() returns the first regex match in
        # this list, sorted strongest-first, so a weak archetype never shadows a
        # stronger one when both match a line -- but it CAN still be the ONLY match
        # on a line and get returned, feeding a noisy low strength into
        # max(f_hook, arch["strength"]) downstream. Filtering here keeps the list
        # (now 30+ archetypes across ob_buyer + general_viral tiers) from letting
        # weak/fatigued patterns set the hook score floor, while still allowing the
        # documented 45-85 strength_prior range (e.g. legacy_meme at 48) to fire.
        if a.get("strength_prior", 60) < 45:
            continue
        pats = []
        for c in a.get("spoken_cues", []):
            try:
                pats.append(re.compile(c, re.I))
            except re.error:
                pass
        out.append({"name": a["name"], "strength": a.get("strength_prior", 60),
                    "pats": pats, "onscreen": (a.get("onscreen_templates") or [None])[0],
                    # full onscreen_templates list (not just the first) so a rewritten
                    # headline can try more than one shape per archetype before giving up
                    "onscreen_templates": a.get("onscreen_templates") or [],
                    "rewrite_templates": a.get("rewrite_templates") or []})
    out.sort(key=lambda a: -a["strength"])
    return out


HOOK_ARCHETYPES = _load_hook_lib()


# ---- hook BANK (curated verbatim/near-verbatim lines, not archetype templates) ---
# Miner-built data/hook-bank.json: 268 pre-written hooks (quality a/b/c) pulled
# from OB's own filming-ready library + curated viral-hook templates + the
# 1000-Viral-Hooks corpus. Distinct from HOOK_ARCHETYPES (which are structural
# PATTERNS with [PLACEHOLDER] templates to fill) -- bank hooks are mostly
# complete, ready-to-use LINES. Used as rewrite_headline()'s fallback when no
# archetype rewrite_template fills, so a clip never falls through to its own
# weak spoken opener when a strong bank line is topically eligible.
_BANK_TOPIC_LEXICON = {
    "fatloss": re.compile(r"\b(fat loss|belly fat|weight loss|lose weight|losing weight|"
                          r"plateau|scale|stubborn fat|lean|shred|cut(?:ting)?)\b", re.I),
    "nutrition": re.compile(r"\b(calor(?:ie|y)|protein|carbs?|fiber|macros?|diet|meal|"
                            r"food|eating|nutrition|fasting|keto)\b", re.I),
    "training": re.compile(r"\b(train(?:ing)?|workout|gym|lift(?:ing)?|cardio|reps?|sets?|"
                           r"exercise|muscle)\b", re.I),
    "mindset": re.compile(r"\b(motivation|discipline|habit|identity|mindset|willpower|"
                          r"consisten\w*|accountab\w*)\b", re.I),
}
_BANK_QUALITY_RANK = {"a": 3, "b": 2, "c": 1}


def _load_hook_bank():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hook-bank.json")
    try:
        bank = json.load(open(p))
    except Exception:
        return [], {}
    hooks = [h for h in bank.get("hooks", []) if h.get("quality") == "a"]
    # TONE GATE for the deterministic path: persona-heavy mechanisms (confession,
    # dare, deadpan, POV skits) put words in OB's mouth that must FIT the clip's
    # voice — a judgment call regex can't make. Preflight checks form, not tone,
    # so without an LLM to judge fit these mechanisms are excluded here; only
    # tone-neutral mechanisms (facts, questions, contradictions, curiosity) may
    # headline a clip deterministically. The LLM path is unaffected.
    _TONE_NEUTRAL = {"contradiction", "specificity", "question", "curiosity_gap",
                     "pattern_interrupt", "status_reframe", "identity_recognition"}
    hooks = [h for h in hooks if (h.get("mechanism") or "").split(":")[0] in _TONE_NEUTRAL]
    return hooks, (bank.get("rehook") or {})


HOOK_BANK, HOOK_BANK_REHOOK = _load_hook_bank()


_BANK_ONSCREEN_MAX_WORDS = 12  # same cap as _quotable_headline / preflight's onscreen_hook lint


def _bank_hook_fillable(hook_text):
    """Bank hooks mostly have no [PLACEHOLDER]s at all (always eligible). The
    handful that do use non-standard '(insert X)'/'[use for ...]' authoring
    notes rather than the archetype library's [PLACEHOLDER] convention, so we
    don't attempt to fill them -- any bracket/paren content makes the hook
    unusable here (reject, don't guess). Also reject hooks longer than the
    onscreen word cap: bank hooks are ready-to-SPEAK lines, not ready-to-BURN-IN
    on-screen text, and truncating a verbatim quote would fabricate a fragment
    -- so an overlong hook is simply ineligible here rather than chopped."""
    if _ANY_BRACKET.search(hook_text) or re.search(r"\([^)]*\)", hook_text):
        return False
    return len(hook_text.split()) <= _BANK_ONSCREEN_MAX_WORDS


def _bank_topics_for(text):
    return {topic for topic, pat in _BANK_TOPIC_LEXICON.items() if pat.search(text)}


def _mechanism_overlap(mechanism, existing_text):
    """Crude mechanism-diversity check: does the clip's OWN existing text
    already read like the same mechanism the candidate bank hook uses? Keeps
    picks deterministic (no LLM) while avoiding stacking two near-identical
    'contradiction' style lines when the clip's own opener already reads that
    way. Not exhaustive -- just a same-family regex tripwire per mechanism."""
    fam_pats = {
        "contradiction": CONTRARIAN,
        "specificity": NUMBER,
        "contrarian_hot_take": CONTRARIAN,
        "correction_myth": WARNING,
        "insider_secret": re.compile(r"\bnobody tells you|no one tells you|the truth about\b", re.I),
        "fear_warning_mistake": WARNING,
    }
    pat = fam_pats.get(mechanism)
    return bool(pat and pat.search(existing_text))


def bank_headline(text):
    """Pick the best quality-a bank hook whose topic_fit matches this clip's
    text AND whose placeholders (if any) are strictly fillable, preferring the
    hook whose mechanism is NOT already echoed by the clip's own existing text
    (mechanism diversity). Deterministic: ties broken by bank order (already
    quality/source curated), never random. Returns None if nothing matches --
    caller keeps the current headline unchanged."""
    if not HOOK_BANK:
        return None
    clip_topics = _bank_topics_for(text)
    candidates = []
    for h in HOOK_BANK:
        fits = set(h.get("topic_fit") or [])
        if "any" not in fits and clip_topics and not (fits & clip_topics):
            continue
        if "any" not in fits and not clip_topics:
            continue  # no detected topic on the clip -> only "any"-tagged hooks eligible
        if not _bank_hook_fillable(h["text"]):
            continue
        diverse = not _mechanism_overlap(h.get("mechanism", ""), text)
        candidates.append((diverse, len(fits & clip_topics), h))
    if not candidates:
        return None
    # prefer mechanism-diverse, then more specific topic overlap, stable order otherwise
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return clean_headline(candidates[0][2]["text"])


def detect_archetype(sentence):
    """first (strongest) archetype whose current-data cues fire in the opening line."""
    for a in HOOK_ARCHETYPES:
        if any(p.search(sentence) for p in a["pats"]):
            return a
    return None


def hook_of(sentence):
    """deterministic hook strength of a single opening line (regex trigger or archetype)."""
    arch = detect_archetype(sentence)
    return max(f_hook(sentence), arch["strength"] if arch else 0)


def optimize_hookpoint(cand, min_s=15, max_trim=3):
    """Re-cut the clip's IN-POINT to open on a recognized hook.

    ARCHETYPE-GATED (conservative on purpose): only trims leading sentences to land
    the start on a sentence that matches a data-backed hook archetype, and only when
    the current opener does NOT already match one. Raw regex trigger-counts are too
    easily fooled (a question mark + 'you' scores high on a weak context-leak line),
    so we never re-cut on those alone. Nuanced re-cuts (e.g. an analogy hook the
    archetype library doesn't yet know) are left to the LLM pass / the advisor."""
    sents = cand.get("sents")
    if not sents or len(sents) < 2 or detect_archetype(sents[0]["text"]):
        return cand
    best_t = 0
    for t in range(1, min(max_trim, len(sents) - 1) + 1):
        if cand["end"] - sents[t]["start"] < min_s:
            break
        if detect_archetype(sents[t]["text"]):
            best_t = t
            break
    if best_t == 0:
        return cand
    kept = sents[best_t:]
    cand = dict(cand)
    cand.update({
        "start": kept[0]["start"],
        "dur": round(cand["end"] - kept[0]["start"], 1),
        "first_sentence": kept[0]["text"],
        "text": " ".join(s["text"] for s in kept),
        "sents": kept,
        "hook_recut": True,
        "dropped_lead": " ".join(s["text"] for s in sents[:best_t]),
    })
    return cand


def baseline(cand):
    fs = cand.get("first_sentence") or first_sentence(cand["text"])
    arch = detect_archetype(fs)
    cand["_archetype"] = arch["name"] if arch else None
    cand["_onscreen"] = arch["onscreen"] if arch else None
    cand["_arch_strength"] = arch["strength"] if arch else 0
    sub = {k: fn(cand["text"]) for k, fn in REGEX.items()}
    sub["hook"] = f_hook(cand["text"], fs)    # score the REAL opening sentence
    if arch:                                  # a matched buyer-hook floors the hook score
        sub["hook"] = max(sub["hook"], arch["strength"])
    total = sum(sub[k] * W[k] for k in W) / 100.0
    return sub, round(total, 1)


# ---- non-max suppression by time overlap -----------------------------------
def overlap(a, b):
    inter = max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    span = min(a["dur"], b["dur"]) or 1
    return inter / span


def nms(cands, thresh=0.5):
    kept = []
    for c in sorted(cands, key=lambda x: -x["_base"]):
        if all(overlap(c, k) < thresh for k in kept):
            kept.append(c)
    return kept


# ---- claude -p subjective enrichment (one batched call) --------------------
LLM_PROMPT = """You are scoring candidate short-form clips pulled from a fitness coach's podcast (brand: OB Health, high-ticket fat-loss coaching; buyer is 30-45 and would PAY for coaching). For EACH candidate, judge it as a standalone Reel.

Return ONLY a JSON array (no prose, no code fence). One object per candidate id with EXACTLY these fields:
- id (int)
- hook_score (0-100): how hard the FIRST sentence stops the scroll in 1.7s
- arousal (0-100): peak emotional intensity — high for awe/anger/shock/fear, low for calm/neutral
- controversy (0-100): polarizing hot-take likely to drive comments
- quotable_line (string): the single most tweetable line, verbatim from the text, <=15 words, or ""
- buyer_relevance (0-100): relevance to a 30-45yo who'd buy coaching, vs generic under-25 reach
- engagement_lever (one of: "share","save","comment")
- title (string): punchy 4-7 word clip title

Candidates:
%s
"""


def _llm_call(prompt, timeout=240):
    """Return model text via whichever backend is available, else None.
    1) `claude -p` (if the CLI is logged in)  2) Anthropic API (if ANTHROPIC_API_KEY).

    The prompt is passed via STDIN, not argv: a batch of ~8-22 candidates'
    transcript text can push the rendered prompt past 50-100KB, and very long
    argv strings are fragile (OS ARG_MAX limits, shell/subprocess quoting
    edge cases, some `claude` CLI builds truncating or rejecting oversized
    single args). STDIN has no such ceiling. `claude -p` reads the prompt from
    stdin when no prompt argument is given, so the argv form is kept ONLY as a
    fallback if the stdin call returns nothing usable (belt-and-suspenders for
    older CLI builds that require the positional arg)."""
    # 1) claude -p, prompt on STDIN (primary path)
    try:
        out = subprocess.run(["claude", "-p"], input=prompt, capture_output=True,
                             text=True, timeout=timeout)
        txt = out.stdout.strip()
        if out.returncode == 0 and txt and not txt.startswith("Not logged in"):
            return txt
    except Exception:
        pass
    # 2) claude -p "<prompt>" on argv, fallback only (fragile at large sizes)
    try:
        out = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True,
                             timeout=timeout)
        txt = out.stdout.strip()
        if out.returncode == 0 and txt and not txt.startswith("Not logged in"):
            return txt
    except Exception:
        pass
    # 3) direct Anthropic API, if a key is configured
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            import urllib.request
            body = json.dumps({
                "model": os.environ.get("OB_MOMENTS_MODEL", "claude-opus-4-8"),
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": prompt}],
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            return "".join(b.get("text", "") for b in data.get("content", []))
        except Exception:
            pass
    return None


def _strip_fences(raw):
    """Strip a leading/trailing ```json / ``` markdown fence some model
    responses wrap the array in, despite the prompt saying 'no code fence'."""
    s = raw.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.S)
    return m.group(1) if m else s


def _outermost_json_array(raw):
    """Find the OUTERMOST top-level JSON array in raw text by bracket-depth
    scanning (not a greedy/naive regex, which can grab the wrong span when the
    response has nested arrays or stray brackets in prose/quotes)."""
    start = raw.find("[")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return raw[start:i + 1]
    return None


def _clamp_score(v, lo=0, hi=100, default=0):
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _validate_item(o, valid_ids=None):
    """Validate + coerce one LLM-scored item. Returns a cleaned dict or None
    if the item is unusable (bad/missing/foreign id) — callers must never
    crash on a single malformed item, just drop it and move on.
    valid_ids=None skips the batch-membership check (used by --llm-json
    injection, which isn't scoped to a single scored batch)."""
    if not isinstance(o, dict):
        return None
    try:
        oid = int(o.get("id"))
    except (TypeError, ValueError):
        return None
    if valid_ids is not None and oid not in valid_ids:
        return None
    out = {"id": oid}
    for k in ("hook_score", "arousal", "controversy", "buyer_relevance"):
        if k in o:
            out[k] = _clamp_score(o[k])
    out["quotable_line"] = str(o.get("quotable_line") or "").strip()
    out["title"] = str(o.get("title") or "").strip()
    lever = o.get("engagement_lever")
    out["engagement_lever"] = lever if lever in ("share", "save", "comment") else None
    return out


def _parse_scores(raw, valid_ids=None):
    """Parse a (possibly fenced, possibly noisy) model response into
    {id: item}. Per-item validation: a malformed item is dropped with a
    stderr note rather than raising, so one bad entry in a batch can't take
    down the whole batch's results."""
    stripped = _strip_fences(raw)
    arr_text = _outermost_json_array(stripped)
    try:
        arr = json.loads(arr_text if arr_text is not None else stripped)
    except json.JSONDecodeError:
        # last-ditch: the naive "first [ to last ]" span, for truncated/odd output
        m = re.search(r"\[.*\]", stripped, re.S)
        if not m:
            raise
        arr = json.loads(m.group(0))
    if not isinstance(arr, list):
        raise ValueError("parsed JSON is not an array")
    out = {}
    dropped = 0
    for o in arr:
        v = _validate_item(o, valid_ids)
        if v is None:
            dropped += 1
            continue
        out[v["id"]] = v
    if dropped:
        print(f"[score] dropped {dropped} invalid LLM item(s) from a batch "
              "(bad/foreign id or unparseable fields)", file=sys.stderr)
    return out


def llm_enrich(cands, timeout=120, batch_size=8):
    """Batch candidates into groups of `batch_size`, scoring each batch with
    its own `timeout`-second budget. One failed/timed-out/unparseable batch
    only drops THAT batch's candidates back to the deterministic baseline —
    it must never abort the other batches or the run as a whole."""
    batches = [cands[i:i + batch_size] for i in range(0, len(cands), batch_size)]
    merged = {}
    ok_batches, failed_batches = 0, 0
    for bi, batch in enumerate(batches):
        valid_ids = {c["id"] for c in batch}
        payload = [{"id": c["id"], "first_sentence": c["first_sentence"], "text": c["text"]}
                   for c in batch]
        raw = None
        try:
            raw = _llm_call(LLM_PROMPT % json.dumps(payload, ensure_ascii=False), timeout)
        except Exception as e:
            print(f"[score] LLM batch {bi + 1}/{len(batches)} raised "
                  f"{type(e).__name__}: {e}; that batch falls back to regex baseline.",
                  file=sys.stderr)
        if not raw:
            failed_batches += 1
            print(f"[score] LLM batch {bi + 1}/{len(batches)} ({len(batch)} candidates) "
                  "got no usable backend response; falling back to the deterministic "
                  "lexicon path for this batch.", file=sys.stderr)
            continue
        try:
            scores = _parse_scores(raw, valid_ids)
        except Exception as e:
            failed_batches += 1
            print(f"[score] LLM batch {bi + 1}/{len(batches)} output unparseable "
                  f"({type(e).__name__}); that batch falls back to regex baseline.",
                  file=sys.stderr)
            continue
        if not scores:
            failed_batches += 1
            print(f"[score] LLM batch {bi + 1}/{len(batches)} returned zero valid items; "
                  "that batch falls back to regex baseline.", file=sys.stderr)
            continue
        ok_batches += 1
        merged.update(scores)

    n_scored, n_total = len(merged), len(cands)
    n_fallback = n_total - n_scored
    if n_total:
        print(f"[score] LLM enrichment: {n_scored}/{n_total} candidate(s) got LLM scores "
              f"({ok_batches} batch(es) ok, {failed_batches} batch(es) fell back), "
              f"{n_fallback} fell back to the deterministic lexicon path.", file=sys.stderr)
    if not merged:
        print("[score] no LLM backend available at all (claude CLI not logged in, no "
              "ANTHROPIC_API_KEY); every candidate uses the deterministic lexicon path "
              "(fully usable). Pass --llm-json to inject scores, or run "
              "bin/llm_check.py to diagnose.", file=sys.stderr)
    return merged


# ---- final scoring ---------------------------------------------------------
def finalize(cand, llm):
    sub = dict(cand["_sub"])
    if llm:
        # with model judgment available, combine it only with the trustworthy
        # archetype strength — NOT the noisy regex keyword-count prior
        sub["hook"] = max(llm.get("hook_score", 0), cand.get("_arch_strength", 0))
        sub["arousal"] = llm.get("arousal", sub["arousal"])
        sub["controversy"] = llm.get("controversy", sub["controversy"])
        if llm.get("quotable_line"):
            sub["quotable"] = max(sub["quotable"], 70)

    weighted = sum(sub[k] * W[k] for k in W) / 100.0
    # HOOK GATES DISTRIBUTION: the first 1-3s decides whether the body is ever seen,
    # so hook quality multiplies the whole score rather than just adding to it
    # (Berger/practitioner: a weak opener suppresses even a strong body).
    # SOFTENED 2026-07 from 0.4+0.6*h to 0.55+0.45*h: calibration found hook ρ≈0 on
    # Shorts views (no measurable signal), so the old multiplier over-punished
    # middling openers. Floor raised 0.40 -> 0.55; a dead hook is still gated below.
    hook_mult = 0.55 + 0.45 * (sub["hook"] / 100.0)
    total = round(weighted * hook_mult, 1)

    # VIRAL-FIRST DURATION BONUS (2026-07): completion rate GATES distribution on
    # every short-form platform (TikTok/Shorts/Reels all rank on watch-through), so a
    # clip's own length is itself a reach lever, not just an editorial preference.
    # Shorter clips are structurally more likely to be watched to the end, so they get
    # a small multiplicative nudge; long clips get a small tax. This stacks with (does
    # not replace) the window-target shift toward 16/26/40s in window.py.
    dur = cand["dur"]
    if dur <= 30:
        total = round(total * 1.10, 1)
    elif dur <= 40:
        total = round(total * 1.0, 1)
    else:
        total = round(total * 0.88, 1)

    # BRAND-SAFETY DEMOTION: controversy ρ = -0.106 (negative) with OB's 30-45 buyers;
    # OB is anti-ragebait. A genuinely hot take is a mild demerit, not a boost — enough
    # to break ties against a hostile clip without nuking a merely-spicy one.
    if sub["controversy"] >= 70:
        total = round(total * 0.90, 1)
    elif sub["controversy"] >= 50:
        total = round(total * 0.95, 1)

    # multi-speaker penalty: a clip that straddles speaker turns reads as
    # incoherent banter cold; one handoff is tolerable, more is not
    changes = cand.get("speaker_changes", 0)
    if changes:
        sub["context"] = max(0, sub["context"] - 30 * changes)
        total = round(total * (0.85 if changes == 1 else 0.6), 1)

    # hard gates
    gate_ok, reason = True, ""
    if changes >= 3:
        gate_ok, reason = False, f"rapid multi-speaker banter ({changes} speaker turns)"
    elif sub["context"] < 15:
        gate_ok, reason = False, "needs prior context (unintelligible cold)"
    elif sub["hook"] < 12:
        gate_ok, reason = False, "dead hook (dies in first 3s)"

    lever = (llm or {}).get("engagement_lever")
    if not lever:
        lever = max([("share", sub["you"] + sub["arousal"]),
                     ("save", sub["numbers"] + sub["list"]),
                     ("comment", sub["controversy"])], key=lambda x: x[1])[0]

    onscreen_hook = (fill_onscreen_template(cand.get("_onscreen"), cand["text"])
                     or clean_headline((llm or {}).get("title", "").strip()
                                       or _quotable_headline(llm)
                                       or short_hook(cand["first_sentence"], 9)))

    # VIRAL-FIRST HEADLINE REWRITE (2026-07): the on-screen headline is the
    # strongest lever we control (85%+ watch on mute — see hook-library.json's
    # current_trends). When gate_ok and the clip has NO recognized hook archetype
    # AND its hook subscore is weak (<60), the spoken opener alone is not carrying
    # the clip — try to generate a stronger rewritten headline from the hook
    # library instead of shipping the (weak) spoken-derived one.
    headline_is_rewrite = False
    if gate_ok and cand.get("_archetype") is None and sub["hook"] < 60:
        rewritten = rewrite_headline(cand["text"])
        if rewritten:
            onscreen_hook = rewritten
            headline_is_rewrite = True

    onscreen_hook = clean_headline(onscreen_hook)

    return {
        "id": cand["id"],
        "start": cand["start"], "end": cand["end"], "dur": cand["dur"],
        "title": clean_headline((llm or {}).get("title", "").strip()
                                or short_hook(cand["first_sentence"], 8)),
        "hook_line": cand["first_sentence"],
        "hook_archetype": cand.get("_archetype"),
        "onscreen_hook": onscreen_hook,
        "headline_is_rewrite": headline_is_rewrite,
        "quotable_line": (llm or {}).get("quotable_line", "").strip(),
        "score": total,
        "subscores": sub,
        "engagement_lever": lever,
        "buyer_relevance": (llm or {}).get("buyer_relevance"),
        "gate_passed": gate_ok,
        "gate_reason": reason,
        "hook_recut": cand.get("hook_recut", False),
        "dropped_lead": cand.get("dropped_lead", ""),
        "text": cand["text"],
    }


def mmss(t):
    return f"{int(t)//60:02d}:{int(t)%60:02d}"


def write_md(path, vid, moments):
    passed = [m for m in moments if m["gate_passed"]]
    lines = [f"# Viral-moment shortlist — {vid}",
             f"_ob-moments transcript brain · {len(passed)} candidates cleared the gates_\n"]
    for rank, m in enumerate(passed, 1):
        s = m["subscores"]
        br = f" · buyer {m['buyer_relevance']}" if m["buyer_relevance"] is not None else ""
        arch = f" · hook: **{m['hook_archetype']}**" if m.get("hook_archetype") else ""
        lines += [
            f"## {rank}. {m['title']}  ·  score {m['score']}",
            f"**{mmss(m['start'])}–{mmss(m['end'])}** ({m['dur']}s) · lever: **{m['engagement_lever']}**{br}{arch}",
            f"- Hook line: _{m['hook_line']}_",
            (f"- 🎬 On-screen hook: **{m['onscreen_hook']}**" if m.get("onscreen_hook") else ""),
            (f"- Quote: _{m['quotable_line']}_" if m['quotable_line'] else ""),
            f"- Subscores: hook {s['hook']} · curiosity {s['curiosity']} · arousal {s['arousal']} "
            f"· context {s['context']} · payoff {s['payoff']} · controversy {s['controversy']} "
            f"· numbers {s['numbers']} · list {s['list']} · you {s['you']} · quotable {s['quotable']}",
            "",
        ]
    rejected = [m for m in moments if not m["gate_passed"]]
    if rejected:
        lines.append(f"\n---\n_Gated out ({len(rejected)}): "
                     + ", ".join(f"{mmss(m['start'])} ({m['gate_reason']})" for m in rejected[:8])
                     + ("…" if len(rejected) > 8 else "") + "_")
    open(path, "w").write("\n".join(l for l in lines if l is not None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--id", default=None)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--enrich", type=int, default=22, help="candidates sent to the LLM pass")
    ap.add_argument("--dump-pool", default=None, help="write the enrich pool to JSON and exit")
    ap.add_argument("--llm-json", default=None, help="inject precomputed subjective scores (JSON array)")
    a = ap.parse_args()
    vid = a.id or os.path.splitext(os.path.basename(a.srt))[0].replace(".en", "")

    sents = sentences_from_srt(a.srt)
    cands = [optimize_hookpoint(c) for c in make_windows(sents)]
    for c in cands:
        c["_sub"], c["_base"] = baseline(c)
    kept = nms(cands)
    kept.sort(key=lambda x: -x["_base"])
    print(f"[score] {len(sents)} sentences -> {len(cands)} windows -> {len(kept)} after NMS",
          file=sys.stderr)

    pool = kept[:a.enrich]
    if a.dump_pool:
        json.dump([{"id": c["id"], "start": c["start"], "end": c["end"], "dur": c["dur"],
                    "first_sentence": c["first_sentence"], "text": c["text"]} for c in pool],
                  open(a.dump_pool, "w"), indent=2, ensure_ascii=False)
        print(f"[score] wrote enrich pool ({len(pool)}) -> {a.dump_pool}", file=sys.stderr)
        return

    if a.llm_json:
        llm = _parse_scores(open(a.llm_json).read())
        print(f"[score] injected {len(llm)} LLM scores from {a.llm_json}", file=sys.stderr)
    else:
        llm = {} if a.no_llm else llm_enrich(pool)
    n_llm = sum(1 for c in pool if c["id"] in llm)
    print(f"[score] final: {n_llm}/{len(pool)} candidate(s) scored by LLM, "
          f"{len(pool) - n_llm} by deterministic fallback.", file=sys.stderr)
    moments = [finalize(c, llm.get(c["id"], {})) for c in pool]
    moments.sort(key=lambda m: (m["gate_passed"], m["score"]), reverse=True)
    moments = moments[:a.top]

    workdir = os.path.dirname(os.path.abspath(a.srt))
    jpath = os.path.join(workdir, f"{vid}.moments.json")
    mpath = os.path.join(workdir, f"{vid}.moments.md")
    json.dump({"video_id": vid, "source_srt": a.srt, "generated_from": "transcript",
               "used_llm": bool(llm), "weights": W, "moments": moments},
              open(jpath, "w"), indent=2)
    write_md(mpath, vid, moments)
    print(f"[score] wrote {jpath}\n[score] wrote {mpath}", file=sys.stderr)


if __name__ == "__main__":
    main()
