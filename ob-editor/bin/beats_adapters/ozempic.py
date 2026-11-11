"""Beat adapter for the Ozempic bone-loss reaction (T17 Trainbloom, ~/ob-work/2026-11-07-shoot/ozempic/oz_build.py).
Pilot adapter, 2026-11-07. See the docstring of bin/beats.py for the interface; this one wraps oz_build's own functions
(render(k), the w_full_z/out frame cache, SFX_PLAN, audio(), the final encode and gate_full.py's gate call) without changing them."""
import os, sys, re, glob, json, subprocess

OZ = os.path.expanduser("~/ob-work/2026-11-07-shoot/ozempic")
EDIT_BIN = os.path.expanduser("~/ob-editor/bin")

class Adapter:
    name = "ozempic"
    def __init__(self, beats_dir, h):
        self.h = h; self.beats_dir = beats_dir or os.path.join(OZ, "beats")
        for p in (OZ, EDIT_BIN):
            if p not in sys.path: sys.path.insert(0, p)
        old = sys.argv; sys.argv = [old[0], "full"]          # oz_build reads its MODE from argv at import
        try: import oz_build as B
        finally: sys.argv = old
        self.B = B; self.fps = B.FPS; self.n_frames = B.N
        self.cache = os.path.join(B.WK, "out"); self.base_plan = list(B.SFX_PLAN)
        self.t_ob = B.SEGS[len(B.SRC_SEGS)]["t0"]
        ow = [w for w in B.EW]; self.ob_words = ow; self.lines = h.caption_lines(ow)
        self.line_of = {}; self.line_text = []
        for li, (a, b) in enumerate(self.lines):
            self.line_text.append(" ".join(w["w"].strip() for w in ow[a:b + 1]))
            for i in range(a, b + 1): self.line_of[i] = li
        self.tg = next((w["s"] for w in ow if w["w"].strip(",.").upper() == "GLP"), None)
        tl = B.word_t("looking"); self.drop = (tl - 0.05, B.word_t("before", tl) + 0.45)
        self.peek_ok = len(glob.glob(os.path.join(B.PEEK, "f_*.png"))) >= B.PMAP["n1"] + B.PMAP["n2"]
        self.seg_index = {id(s): i for i, s in enumerate(B.SEGS)}

    # --- frames
    def frame_path(self, k): return os.path.join(self.cache, f"f_{k:05d}.png")
    def render_frame(self, k): return self.B.render(k)
    def state(self, k):
        B = self.B; t = k / self.fps; lay, s = B.layout_at(t); shot = self.seg_index[id(s)]; els = []; cap = None
        if lay == "src":
            els.append(f"her clip, line {s['line'] + 1} of 3 (own captions)")
            if self.peek_ok and k >= B.PMAP["k_peek0"]: els.append("OB peeking at it, bottom right")
        elif lay in ("face", "cta"):
            els.append("OB on camera, locked off")
            idx = None
            for i, w in enumerate(self.ob_words):
                if w["s"] - 0.04 <= t: idx = i
            if idx is not None and t <= self.ob_words[idx]["e"] + 0.35:
                cap = self.line_text[self.line_of[idx]]; els.append("caption word: " + B.FIX.get(self.ob_words[idx]["w"].strip(",."), self.ob_words[idx]["w"].strip(",.")))
            if t < self.t_ob + 2.2: els.append("'Not medical advice' disclaimer")
            if lay == "cta" and self.tg is not None and t >= self.tg - 0.15: els.append("CTA card: COMMENT GLP")
        else:
            doc = (B.BOARDS[lay].__doc__ or "").strip().splitlines()[0]; els.append(f"board {lay}: {doc[:130]}")
        return dict(shot=shot, graphic=lay, caption=cap, elements=els)
    def words(self):
        B = self.B; out = [dict(w=w["w"], s=w["s"], e=w["e"], who="ob") for w in self.ob_words]
        sw = B.src_words()
        for s in B.SEGS:
            if s["kind"] != "src": continue
            for w in sw:
                if s["a"] - 1e-6 <= w["s"] < s["b"]: out.append(dict(w=w["w"], s=s["t0"] + w["s"] - s["a"], e=s["t0"] + min(w["e"], s["b"]) - s["a"], who="her"))
        return sorted(out, key=lambda w: w["s"])

    # --- sound
    def base_sfx_plan(self): return list(self.base_plan)
    def sfx_plan(self): return self.h.apply_sfx_overrides(self.base_plan, self.beats_dir)
    def sfx_onset(self, item): return item[1] - 0.9 if item[3] == "rise" else item[1]
    def music_on(self, t): return self.t_ob <= t < self.B.END - 0.05 and not (self.drop[0] <= t < self.drop[1])
    def families(self): return {k: [(f if f.startswith("/") else self.B.SFX + f) for f in v] for k, v in self.B.FAM.items()}
    def mix_sig(self): return self.h.plan_sig(self.sfx_plan(), f"{self.B.MUSIC}|{self.B.MUSIC_SS}|{self.B.MUSIC_DB}")
    def base_mix_sig(self): return self.h.plan_sig(self.base_plan, f"{self.B.MUSIC}|{self.B.MUSIC_SS}|{self.B.MUSIC_DB}")
    def base_mix(self): return os.path.join(self.B.WK, "mix.wav")
    def audio(self, out_wav):
        B = self.B; keep = (B.SFX_PLAN, B.WK); work = os.path.join(self.beats_dir, "audio_work"); os.makedirs(work, exist_ok=True)
        B.SFX_PLAN = self.sfx_plan(); B.WK = work       # the engine's audio() reads both as module globals; its scratch mix_raw.f32 lands in beats/audio_work
        try: B.audio(out_wav=out_wav)
        finally: B.SFX_PLAN, B.WK = keep

    # --- output
    def encode(self, out, wav):
        B = self.B
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-framerate", "30000/1001", "-i", os.path.join(self.cache, "f_%05d.png"), "-i", wav, "-frames:v", str(B.N),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-r", "30000/1001", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out], check=True)
    def gate(self, out):
        B = self.B; import qc_gate
        ob = [s for s in B.SEGS if s["kind"] == "ob"]
        segs = [(B.MIC, s["a"], s["b"], s["t0"]) for s in ob]; cam = [(B.CAM, s["a"] - B.OFF, s["b"] - B.OFF, s["t0"]) for s in ob]   # cam = mic - OFF, as gate_full.py
        ok = qc_gate.after_render(out, segs=segs, script=os.path.join(OZ, "script_words.txt"), cam=cam)
        print("gate report:", qc_gate.report_path(out)); return bool(ok)
    def final_path(self): return os.path.join(OZ, "Ozempic bone loss - Trainbloom full v3.mp4")
    def full_render_s(self):
        p = os.path.join(OZ, "build_full.time")
        if not os.path.exists(p): return None
        m = re.search(r"(\d+):(\d+\.\d+) total", open(p).read()); return int(m.group(1)) * 60 + float(m.group(2)) if m else None

def make(beats_dir, h): return Adapter(beats_dir, h)
