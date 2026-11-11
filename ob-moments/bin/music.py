#!/usr/bin/env python3
"""
music.py — recommend background music per scored moment, across two legal lanes.

Reuses the scorer's output (arousal, controversy, engagement lever, topic) to pick
a VIBE, then recommends:
  Lane A  burned-in royalty-free bed under the voice (business-safe, exportable)
  Lane B  in-app trending sound to add for reach (never burned in on a monetizing acct)

Never auto-applies. Reads work/<id>.moments.json, writes music picks back into it
plus a readable work/<id>.music.md. Prefers data/music-library.json (from the
music-trend bot swarm) and falls back to built-in profiles so it works immediately.

Usage: python3 bin/music.py work/<id>.moments.json
"""
import os, sys, json, re
from datetime import datetime, timezone

LEGAL = ("Lane A is safe to burn into the export (business-safe royalty-free). "
         "Never burn a licensed/viral chart track into the MP4 on a monetizing "
         "account — it mutes/throttles. Trending viral sounds are Lane B (in-app) only.")

TRENDING_MAX_AGE_DAYS = 14

# simple genre/mood keyword buckets to match a vibe's Lane B trend description
# against the current trending-sounds.json entries by name/note text.
VIBE_TO_SOUND_KEYWORDS = {
    "tense_hot_take":   ["dark", "alternative", "tense", "dramatic", "hip-hop", "hip hop", "rock"],
    "motivational":     ["dance", "pop", "electronic", "uplifting", "afrobeats", "upbeat"],
    "emotional_story":  ["pop", "r&b", "rnb", "ballad", "sad", "piano", "folk", "indie"],
    "calm_educational": ["indie", "folk", "lofi", "acoustic", "chill", "r&b", "rnb"],
}


def load_trending_sounds():
    """Load data/trending-sounds.json if present and fresh (< TRENDING_MAX_AGE_DAYS old).

    Returns a list of sound dicts, or [] if missing, stale, or unparseable — callers
    should treat an empty list as "no live suggestions available" and fall back to the
    existing generic Lane B text.
    """
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "trending-sounds.json")
    try:
        d = json.load(open(p))
    except Exception:
        return []
    try:
        fetched = datetime.strptime(d["fetched_at"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return []
    age_days = (datetime.now(timezone.utc) - fetched).days
    if age_days > TRENDING_MAX_AGE_DAYS:
        return []
    return d.get("sounds", [])


def match_trending_sounds(key, sounds, limit=3):
    """Pick up to `limit` trending sounds whose name/note loosely matches the vibe's
    genre/mood keywords. Falls back to the first `limit` sounds if nothing matches,
    so Lane B always has concrete current options when fresh data exists."""
    if not sounds:
        return []
    kws = VIBE_TO_SOUND_KEYWORDS.get(key, [])
    scored = []
    for s in sounds:
        haystack = f"{s.get('name','')} {s.get('note','')}".lower()
        hit = any(kw in haystack for kw in kws)
        scored.append((hit, s))
    matched = [s for hit, s in scored if hit]
    picks = matched if matched else [s for _, s in scored]
    return picks[:limit]

# canonical vibe -> keywords that identify a matching profile in either library
VIBE_KEYS = {
    "tense_hot_take":   ["tense", "hot", "dramatic", "tension", "dark", "suspense"],
    "motivational":     ["motiv", "uplift", "inspir", "energetic", "epic", "driving"],
    "emotional_story":  ["emotion", "story", "sad", "reflective", "heartfelt", "sentimental"],
    "calm_educational": ["calm", "educational", "lofi", "chill", "clean", "study", "ambient"],
}

FALLBACK = {
    "tense_hot_take": {
        "vibe": "tense / hot-take",
        "lane_a_style": "dark minimal tension bed — low pulse, no melody, stays under the voice",
        "lane_a_search_terms": ["tense", "dark", "suspense", "minimal underscore", "dramatic"],
        "lane_b_trend": "a punchy/dramatic trending sound that adds edge to a hot take",
        "bpm_range": "70-90", "energy": "medium"},
    "motivational": {
        "vibe": "motivational",
        "lane_a_style": "uplifting cinematic build — soft piano into strings, driving but not busy",
        "lane_a_search_terms": ["inspirational", "uplifting", "motivational", "cinematic build", "hopeful"],
        "lane_b_trend": "an uplifting/motivational trending audio",
        "bpm_range": "90-120", "energy": "high"},
    "emotional_story": {
        "vibe": "emotional / story",
        "lane_a_style": "emotional solo piano — sparse, sad-to-hopeful, lets the story breathe",
        "lane_a_search_terms": ["emotional piano", "sad piano", "reflective", "heartfelt", "sentimental"],
        "lane_b_trend": "an emotional / storytime trending sound",
        "bpm_range": "60-80", "energy": "low"},
    "calm_educational": {
        "vibe": "calm / educational",
        "lane_a_style": "clean lo-fi / soft beat — unobtrusive, keeps energy without distracting",
        "lane_a_search_terms": ["lofi", "chill beat", "clean background", "soft groove", "study"],
        "lane_b_trend": "a subtle clean / lo-fi trending sound",
        "bpm_range": "70-90", "energy": "low-medium"},
}

STORY_CUES = re.compile(r"\b(i lost|i gained|when i first|i thought|nearly|almost|ruined|"
                        r"destroyed|i was|my (?:story|life))\b", re.I)


def load_library():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "music-library.json")
    try:
        return json.load(open(p)).get("vibe_profiles", [])
    except Exception:
        return []


def pick_key(m):
    s = m["subscores"]
    lever = m.get("engagement_lever", "")
    arousal, controversy = s["arousal"], s["controversy"]
    story = bool(STORY_CUES.search(m.get("text", "")))
    if controversy >= 55 or (lever == "comment" and arousal >= 55):
        return "tense_hot_take"
    if story and 45 <= arousal <= 78:
        return "emotional_story"
    if arousal >= 62 and lever != "comment":
        return "motivational"
    if arousal < 48 and (s["numbers"] >= 60 or s["list"] >= 60):
        return "calm_educational"
    return "motivational" if arousal >= 55 else "calm_educational"


def profile_for(key, lib):
    """find a matching profile in the bot library, else the built-in fallback."""
    for p in lib:
        v = (p.get("vibe", "") + " " + p.get("lane_a_style", "")).lower()
        if any(kw in v for kw in VIBE_KEYS[key]):
            return p, "bot-library"
    return FALLBACK[key], "built-in"


def recommend(m, lib, trending_sounds=None):
    key = pick_key(m)
    p, src = profile_for(key, lib)
    lane_b = {
        "burn_in": False,
        "trend": p.get("lane_b_trend", ""),
        "apply": "add in-app at ~12-18% volume under the voice",
    }
    picks = match_trending_sounds(key, trending_sounds or [])
    if picks:
        lane_b["current_suggestions"] = [
            {
                "name": s.get("name", ""),
                "artist": s.get("artist", ""),
                "platform": s.get("platform", ""),
                "note": s.get("note", ""),
                "caveat": "verify business-safe in-app before using",
            }
            for s in picks
        ]
    return {
        "vibe": p.get("vibe", key),
        "source": src,
        "lane_a": {
            "burn_in": True,
            "style": p.get("lane_a_style", ""),
            "search_terms": p.get("lane_a_search_terms", []),
            "get_from": "Meta Sound Collection / Uppbeat / your ~/ob-moments/music folder",
        },
        "lane_b": lane_b,
        "bpm_range": p.get("bpm_range", ""),
        "energy": p.get("energy", ""),
        "legal": p.get("legal_note", LEGAL),
    }


def mmss(t):
    return f"{int(t)//60:02d}:{int(t)%60:02d}"


def main():
    path = sys.argv[1]
    d = json.load(open(path))
    lib = load_library()
    trending = load_trending_sounds()
    used = "bot-researched music-library.json" if lib else "built-in fallback profiles"
    trend_note = (f"live trending-sounds.json ({len(trending)} sounds)" if trending
                  else "no fresh trending-sounds.json (missing/stale) — Lane B is generic")
    lines = [f"# Music picks — {d['video_id']}", f"_source: {used}; {trend_note}_\n"]
    for m in d["moments"]:
        m["music"] = recommend(m, lib, trending)
    for rank, m in enumerate([x for x in d["moments"] if x["gate_passed"]], 1):
        mu = m["music"]
        lines += [
            f"## {rank}. {m['title']}  ·  {mmss(m['start'])}–{mmss(m['end'])}",
            f"**Vibe: {mu['vibe']}** ({mu['energy']}, {mu['bpm_range']} bpm)",
            f"- 🎵 **Lane A (burn in, safe):** {mu['lane_a']['style']}  \n"
            f"  search: _{', '.join(mu['lane_a']['search_terms'])}_ · from {mu['lane_a']['get_from']}",
            f"- 🔥 **Lane B (in-app, reach):** {mu['lane_b']['trend']} — {mu['lane_b']['apply']}",
        ]
        for s in mu["lane_b"].get("current_suggestions", []):
            lines.append(
                f"  - **current pick:** \"{s['name']}\" — {s['artist']} ({s['platform']}) "
                f"[{s['note']}] — _{s['caveat']}_"
            )
        lines.append("")
    lines.append(f"\n---\n_{LEGAL}_")
    json.dump(d, open(path, "w"), indent=2)
    mpath = path.replace(".moments.json", ".music.md")
    open(mpath, "w").write("\n".join(lines))
    print(f"[music] {used}; wrote picks into {path} and {mpath}", file=sys.stderr)


if __name__ == "__main__":
    main()
