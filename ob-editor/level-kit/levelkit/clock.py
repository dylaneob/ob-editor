"""The edit clock of one video, read from its plan (plan.json). See ../README.md for the plan schema.

Two clocks:
  camera clock  seconds of the A-roll file (C4422.MP4) and of its mic wav (already synced to the camera, checked to 1 ms)
  edit clock    seconds of the finished video. pieces = [[edit_in, cam_a, cam_b, line_id], ...] butt-joined in order.

Cues are named moments on the edit clock. In plan["cues"] each one is
  12.34                                   an edit time in seconds
  {"word": "hunger", "line": "job1"}      the start of that word in that line (first time it is said there)
  {"word": "hunger", "line": "job1", "n": 2, "at": "e", "off": -0.04}   2nd time, its end, 40 ms earlier
  {"cue": "T_ONE", "off": 0.25}           relative to another cue
Words come from Apple's speech words (camera clock) mapped onto the pieces, so a cue never drifts when the cut changes."""
import json, math, os, re

FPS = 30000 / 1001


class Plan:
    def __init__(self, path):
        self.path = os.path.abspath(path); self.dir = os.path.dirname(self.path)
        self.p = json.load(open(path))
        p = self.p
        self.fps = p.get("fps", FPS)
        self.cam, self.mic, self.words_path = p["cam"], p["mic"], p["words"]
        self.lut = os.path.expanduser(p.get("lut", "~/ob-editor/luts/ob_grade_warmtan_hald.png"))
        self.work = os.path.expanduser(p["work"]); os.makedirs(self.work, exist_ok=True)
        self.pieces = [tuple(x) for x in p.get("pieces", [])]
        self.end = (self.pieces[-1][0] + self.pieces[-1][2] - self.pieces[-1][1] + p.get("tail", 0.12)) if self.pieces else 0.0
        self.n = int(round(self.end * self.fps))
        self._words = None; self._cues = {}

    # ---------------- time maps ----------------
    def piece_of(self, t):
        k = 0
        for i, q in enumerate(self.pieces):
            if t >= q[0] - 1e-9: k = i
        return k

    def cam_time(self, t):
        e, a, b, _ = self.pieces[self.piece_of(t)]
        return a + (t - e)

    def cam_frame(self, k):
        """Camera frame index shown on edit frame k."""
        return int(round(self.cam_time(k / self.fps) * self.fps))

    def edit_frames(self):
        """[(edit frame k, camera frame j)] for the whole video."""
        return [(k, self.cam_frame(k)) for k in range(self.n)]

    def cam_frames_needed(self):
        return sorted({j for _, j in self.edit_frames()})

    def line_start(self, lid):
        return min(q[0] for q in self.pieces if q[3] == lid)

    def line_end(self, lid):
        return max(q[0] + q[2] - q[1] for q in self.pieces if q[3] == lid)

    # ---------------- words ----------------
    def words(self):
        """Apple's words on the edit clock, clipped to each piece; a word split by a join inside one phrase is merged."""
        if self._words is not None: return self._words
        w = json.load(open(self.words_path)); out = []
        for fx in self.p.get("word_patches", []):             # Apple's timing or spelling slips, fixed by hand (heard by whisper)
            for x in w:
                if x["w"] == fx["match"] and abs(x["s"] - fx["cam_s"]) < 0.05:
                    x["w"] = fx.get("w", x["w"]); x["s"] = fx.get("s", x["s"]); x["e"] = fx.get("e", x["e"])
        for i, (e, a, b, lid) in enumerate(self.pieces):
            for x in w:
                if x["e"] > a + 0.03 and x["s"] < b - 0.03:
                    s = max(x["s"], a); en = min(x["e"], b)
                    out.append({"w": x["w"], "s": round(e + s - a, 3), "e": round(e + en - a, 3), "piece": i, "line": lid})
        merged = []
        for x in out:
            if merged and x["w"] == merged[-1]["w"] and x["piece"] == merged[-1]["piece"] + 1 and abs(x["s"] - merged[-1]["e"]) < 0.25:
                merged[-1]["e"] = x["e"]; continue
            merged.append(dict(x))
        self._words = merged; return merged

    def word(self, w, line=None, n=1):
        norm = lambda s: re.sub(r"[^a-z0-9%']", "", s.lower())
        hits = [x for x in self.words() if norm(x["w"]) == norm(w) and (line is None or x["line"] == line)]
        if len(hits) < n: raise KeyError(f"word {w!r} #{n} not found in line {line!r}")
        return hits[n - 1]

    def cue(self, name):
        if name in self._cues: return self._cues[name]
        spec = self.p.get("cues", {})[name]
        self._cues[name] = v = self.resolve(spec); return v

    def resolve(self, spec):
        if isinstance(spec, (int, float)): return float(spec)
        if isinstance(spec, str): return self.cue(spec)
        off = spec.get("off", 0.0)
        if "cue" in spec: return self.cue(spec["cue"]) + off
        if "line" in spec and "word" not in spec: return (self.line_start(spec["line"]) if spec.get("at", "s") == "s" else self.line_end(spec["line"])) + off
        x = self.word(spec["word"], spec.get("line"), spec.get("n", 1))
        return x["s" if spec.get("at", "s") == "s" else "e"] + off

    def all_cues(self):
        return {k: round(self.cue(k), 3) for k in self.p.get("cues", {})}

    # ---------------- files ----------------
    def wpath(self, *a):
        p = os.path.join(self.work, *a); os.makedirs(os.path.dirname(p), exist_ok=True); return p

    def aroll_path(self, j):
        return os.path.join(self.work, "aroll", f"c_{j:06d}.jpg")

    def matte_path(self, j):
        return os.path.join(self.work, "matte", f"a_{j:06d}.png")


def nearest_existing(path_fn, j, span=6):
    for d in range(span + 1):
        for jj in (j - d, j + d):
            if os.path.exists(path_fn(jj)): return path_fn(jj)
    raise FileNotFoundError(path_fn(j))
