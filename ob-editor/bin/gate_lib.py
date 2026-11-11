#!/usr/bin/env python3
"""Shared parts of the long-form precheck gates (flicker_check, lookaway_check, coverage_check, pace_check, fit_check).
Not a tool: no command line. Written 2026-10-21 from the C4367 one-off checks (story/flash_check.py, coverage.py, pace.py,
tools/pupilscan.py) so the next edit gets one definition of "what is on screen".

What it mirrors, on purpose, from assemble.py (so a check sees the frames the render will paint):
  - the frame grid: each shot is fr(src_out) - fr(src_in) frames, laid end to end (fr = round(t x 30000/1001));
  - one owner per frame: events sorted by start, the earlier one wins where two touch; a card's "holes" (face breaks) hand its frames
    back to the A-roll; "inlay" events are painted last, on top of their parent;
  - the cover set: assemble.py's COVER types, or any event with "full": true (read from assemble.py itself when it can be parsed,
    so a new full-frame type there reaches every gate; the copy below is only the fallback).
A frame is COVER when its owner is a cover event, otherwise FACE (the A-roll, with or without a pill, plate or self-quote on it).

Import from a script run with `python3 -I` by putting this folder on sys.path first:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import gate_lib as G
"""
import bisect, json, os, re

FPS_N, FPS_D = 30000, 1001
FPS = FPS_N / FPS_D
HERE = os.path.dirname(os.path.abspath(__file__))


def fr(t): return int(round(t * FPS))
def ft(f): return f * FPS_D / FPS_N
def tc(t): return f"{int(t // 60)}:{t % 60:05.2f}"


_COVER_FALLBACK = {"chapter", "quote", "myths", "clip", "doc", "photo_full", "num", "math", "dose", "coins", "timeline", "title",
                   "disclaimer", "wall", "versus", "checklist", "scissors", "detector", "find", "slider", "insert"}


def cover_types():
    """assemble.py's COVER set, parsed from its source (no import: importing it would run its setup)."""
    try:
        src = open(os.path.join(HERE, "assemble.py")).read()
        m = re.search(r"^COVER\s*=\s*\{(.*?)\}", src, re.S | re.M)
        got = set(re.findall(r'"([a-z_0-9]+)"', re.sub(r"#[^\n]*", "", m.group(1))))
        if len(got) >= 8 and {"chapter", "insert", "clip"} <= got: return got
    except Exception:
        pass
    return set(_COVER_FALLBACK)


COVER = cover_types()


def is_cover(e):   # any side card can run full frame ("full": true, C4367); a "beside" paper card or a doc beside him (no "full") shows OB (C4372)
    if e.get("face"): return False   # 10-29: a card that cuts back to OB in those windows (reel, or a full side card) needs the A-roll
    if e.get("full"): return True
    if e.get("beside") or e["type"] == "doc": return False
    return e["type"] in COVER


class Timeline:
    """The painted timeline of one edit. Reads WORK/cutlist.json and WORK/events_resolved.json (never writes)."""

    def __init__(self, work, events=None, cutlist=None):
        self.work = work
        self.cut = json.load(open(cutlist or f"{work}/cutlist.json"))
        self.segs = self.cut["segments"]
        self.events = json.load(open(events or f"{work}/events_resolved.json"))["events"]
        self.shots, ef = [], 0
        for s in self.segs:
            a0, b0 = fr(s["src_in"]), fr(s["src_out"])
            if b0 <= a0: continue
            self.shots.append({"i": s["i"], "seg": s, "src0": a0, "src1": b0, "e0": ef, "e1": ef + b0 - a0,
                               "hold": bool(s.get("hold")), "punch": sorted(fr(t) for t in s.get("punch_at", []))})
            ef += b0 - a0
        self.N, self.T = ef, ft(ef)
        self._e0 = [s["e0"] for s in self.shots]
        for e in self.events:
            e["_f0"], e["_f1"] = fr(e["edit_in"]), min(self.N, fr(e["edit_out"]))
        own = [None] * self.N
        for e in sorted([e for e in self.events if not e.get("inlay")], key=lambda e: -e["_f0"]):
            a, b = max(e["_f0"], 0), e["_f1"]
            own[a:b] = [e] * max(0, b - a)
            for h0, h1 in e.get("holes", []):
                for f in range(max(fr(h0), a), min(fr(h1), b)):
                    if own[f] is e: own[f] = None
        for e in sorted([e for e in self.events if e.get("inlay")], key=lambda e: (e["type"] == "ffcover", e["_f0"])):   # as assemble.py: ffcover on top
            a, b = max(e["_f0"], 0), e["_f1"]
            own[a:b] = [e] * max(0, b - a)
        self.own = own
        self.cov = bytearray(1 if (o is not None and is_cover(o)) else 0 for o in own)
        for e in self.events:   # a reel with face windows (reel_cards, C4395 10-29): footage covers him, except in those windows
            if not e.get("face"): continue
            fw = [(fr(e["edit_in"] + a0), fr(e["edit_in"] + a1)) for a0, a1 in e["face"]]
            for f in range(max(e["_f0"], 0), e["_f1"]):
                if own[f] is e: self.cov[f] = 0 if any(x <= f < y for x, y in fw) else 1

    def shot_index(self, f):
        """index into self.shots of the shot holding edit frame f"""
        return max(0, bisect.bisect_right(self._e0, f) - 1)

    def runs(self):
        """[(kind, f0, f1)], kind 'C' (a cover owns the frame) or 'F' (his face shows), alternating, frame ranges [f0, f1)"""
        out, st, N = [], 0, self.N
        for f in range(1, N + 1):
            if f == N or self.cov[f] != self.cov[st]:
                out.append(("C" if self.cov[st] else "F", st, f)); st = f
        return out

    def owners(self, f0, f1):
        """event ids owning frames [f0, f1), in order of first appearance"""
        seen = []
        for f in range(f0, min(f1, self.N)):
            o = self.own[f]
            if o is not None and o["id"] not in seen: seen.append(o["id"])
        return seen

    def label(self, f):
        o = self.own[f]
        if o is not None: return o["id"]
        sh = self.shots[self.shot_index(f)]
        return ("HOLD!" if sh["hold"] else f"A{sh['i']}")

    def hold_gaps(self):
        """frames of clip holds that are not under a cover (assemble.py exits on these): [(f0, f1)]"""
        out = []
        for sh in self.shots:
            if not sh["hold"]: continue
            a = None
            for f in range(sh["e0"], sh["e1"]):
                if not self.cov[f]:
                    if a is None: a = f
                elif a is not None:
                    out.append((a, f)); a = None
            if a is not None: out.append((a, sh["e1"]))
        return out

    def src_to_edit(self, frames):
        """Map sorted SOURCE frame numbers (combined source) to edit frames through the A-roll shots (holds skipped).
        Returns [(shot_index_in_self.shots, source_frame, edit_frame)] in edit order."""
        out = []
        for k, sh in enumerate(self.shots):
            if sh["hold"]: continue
            lo, hi = bisect.bisect_left(frames, sh["src0"]), bisect.bisect_left(frames, sh["src1"])
            for sf in frames[lo:hi]:
                out.append((k, sf, sh["e0"] + sf - sh["src0"]))
        return out


# ---- gaze rows: [frame, t, pitch, yaw, pupil_y, pupil_x, open]; frame numbers of the file they were scanned from -----------------
def load_gaze(work, cut, extra=()):
    """All gaze rows on the combined source's frame numbers, sorted. WORK/gaze/raw.json is the first file (offset 0). Every other
    source in cutlist["sources"] (name -> [first_frame, end_frame] in the combined file) reads WORK/<name>/gaze_raw.json, whose
    frames are local to that camera file, so its start frame is added (C4367: c4368 starts at frame 83115 = 2773.2705 s).
    `extra` = [(path, offset_seconds)] adds files by hand. Returns (rows, files_used)."""
    files = []
    p = f"{work}/gaze/raw.json"
    if os.path.exists(p): files.append((p, 0))
    for name, rng in (cut.get("sources") or {}).items():
        q = f"{work}/{name}/gaze_raw.json"
        if rng and rng[0] > 0 and os.path.exists(q): files.append((q, int(rng[0])))
    for path, off in extra: files.append((path, fr(off)))
    rows, seen = [], set()
    for path, off in files:
        for r in json.load(open(path))["rows"]:
            f = r[0] + off
            if f in seen: continue
            seen.add(f); rows.append([f] + list(r[1:]))
    rows.sort(key=lambda r: r[0])
    return rows, files


# one gaze sample's state
UP, LOW, SHUT, NOFACE, UNKNOWN = "up", "low", "shut", "noface", "unknown"
DOWN_KINDS = (LOW, SHUT, NOFACE)


def gaze_state(r, th=0.45, shut=0.13, bad=0.60, yaw=None):
    """One gaze row -> UP (on the lens), LOW (pupils low: pupil_y >= th with the eyes open enough to see them), SHUT (open < shut: the
    pupil is not measurable, so pupil_y is ignored), NOFACE (no face found: a bowed head under the cap hides it) or UNKNOWN (open > bad:
    a failed eye contour, not a wide eye; or numbers missing). LOW, SHUT and NOFACE are 'down'. `yaw` (optional): also LOW when the head
    is turned past it (the pickups, where he reads a prompt off to the side). Unknown is never down and it ends a run."""
    pitch, yw, py, px, op = r[2], r[3], r[4], r[5], r[6]
    if pitch is None and op is None and py is None: return NOFACE
    if op is not None and op > bad: return UNKNOWN
    if op is not None and op < shut: return SHUT
    if py is not None and py >= th: return LOW
    if yaw is not None and yw is not None and yw < yaw: return LOW
    if py is None or op is None: return UNKNOWN
    return UP


def load_exempt(work, path=None):
    """story/gaze_exempt.json {"spans": [[a, b, note]]} in source seconds: look-aways eye-checked as expression, not reading."""
    p = path or f"{work}/story/gaze_exempt.json"
    if not os.path.exists(p): return []
    return [(x[0], x[1]) for x in json.load(open(p)).get("spans", [])]
