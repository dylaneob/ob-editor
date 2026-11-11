"""Beat adapter for a LONG-FORM YouTube edit made with bin/assemble.py (the youtube-longform preset). Built 2026-11-08.

  python3 -I beats.py map   longform:<project>             number the beats (cuts, graphic/card entrances, caption-line changes), grouped by chapter
  python3 -I beats.py build longform:<project> [--force]   cut the finished edit into per-chapter segment encodes (seg/sNN.mp4), join them, mux the audio
  python3 -I beats.py redo  longform:<project> 12 40 ...   re-render ONLY those beats' units, re-encode ONLY the segments that contain them, join, gate
  python3 -I beats.py sfx   longform:<project> 12 swap 1 <file>   audio only: remix, loudnorm, mux with the picture copied
  python3 -I beats.py check longform:<project>             A/V sync of the joined file + the QC gate
  python3 -I studio.py serve longform:<project>             open it in OB Studio

<project> = a key in longform_projects.json (next to this file), or a path to a project .json, or a work dir that holds lf_project.json.
Fields: work (cutlist.json, events_resolved.json, hf/, story/), src (the camera file), render_dir (assemble's units/events cache), env
(the OB_* variables the project's render_final.sh exports), final (the delivered master, only ever READ), beats_dir, readonly, words, mic ...

WHY THIS IS NOT THE FRAME-CACHE ADAPTER (ozempic). assemble.py keeps no PNG per frame: it renders UNITS (an A-roll piece, or one HyperFrames
event) and joins them. A 40 minute video is 70,000 frames; a beat note must not touch 69,000 of them. So:
  1. beats = state(k) per frame (the same ownership table assemble.py builds: events, holes, inlays, cutlist shots) + the spoken lines
  2. segments = the chapters (split at unit boundaries when longer than seg_max_s), each an independent H.264 encode with the chapter labels
     burned in, every one starting on a keyframe (the same VideoToolbox settings as the labels pass of render_final.sh)
  3. redo = invalidate the units of the beat -> assemble.py --range <segment> (OB_VIDEO_ONLY=1: the picture only; every cached unit is reused by
     its key) -> burn the labels into that segment -> join all segments with the concat demuxer (-c copy, keyframe aligned) -> audio stream
     copied from the previous file (or remixed + loudnormed if the sound plan changed) -> frame-count / PTS / A-V duration check -> gate
  4. the rest of the film is proven untouched: the other segments' md5 and every other frame's packet hash are compared with the previous file.
Nothing here writes into `final` (the delivered master). `readonly: true` projects refuse redo (they can still open in the studio).
"""
import os, sys, re, json, glob, math, hashlib, shutil, subprocess, time, bisect
import numpy as np

BIN = os.path.expanduser("~/ob-editor/bin")
HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "longform_projects.json")
if BIN not in sys.path: sys.path.insert(0, BIN)
FPS_N, FPS_D = 30000, 1001
FPS = FPS_N / FPS_D
def fr(t): return int(round(t * FPS))
def ft(f): return f * FPS_D / FPS_N
def sh(*cmd, **kw): return subprocess.run(list(cmd), capture_output=True, text=True, **kw)
PALETTE = ["#4aa3ff", "#ff7a3d", "#3ddc97", "#b48cff", "#ffbe4d", "#2fd3c3", "#ff6fa8", "#9bd13c", "#7aa2ff"]


def load_spec(arg):
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    if arg in reg: d = dict(reg[arg]); d["key"] = arg
    elif os.path.isfile(arg): d = json.load(open(arg)); d["key"] = d.get("key") or os.path.splitext(os.path.basename(arg))[0]
    elif os.path.isfile(os.path.join(arg, "lf_project.json")): d = json.load(open(os.path.join(arg, "lf_project.json"))); d["key"] = d.get("key") or os.path.basename(arg.rstrip("/"))
    else: sys.exit(f"no long-form project '{arg}' (keys in {REG}: {', '.join(reg) or 'none'})")
    home = os.path.expanduser("~")
    d["work"] = os.path.expanduser(d["work"]); d.setdefault("render_dir", d["work"] + "/render"); d.setdefault("tmp_dir", home + "/ob-scratch/lf-tmp")
    d.setdefault("beats_dir", home + "/ob-work/longform/" + d["key"])
    sub = lambda v: os.path.expanduser(v.replace("{work}", d["work"]).replace("{render_dir}", os.path.expanduser(d["render_dir"])).replace("{beats_dir}", os.path.expanduser(d["beats_dir"]))) if isinstance(v, str) else v
    d = {k: (sub(v) if isinstance(v, str) else v) for k, v in d.items()}
    d["env"] = {k: sub(v) for k, v in d.get("env", {}).items()}
    d.setdefault("words", d["work"] + "/qc/words_edit.json"); d.setdefault("labels", d["work"] + "/story/labels.json")
    d.setdefault("sfx_plan", d["work"] + "/story/sfx_plan.json"); d.setdefault("score", d["work"] + "/story/score.json")
    d.setdefault("mic", d["render_dir"] + "/master.wav"); d.setdefault("seg_max_s", 40); d.setdefault("readonly", False)
    return d


class Adapter:
    name = "longform"
    exits_are_not_beats = True          # beats.compute_beats: a graphic LEAVING is not a beat (a cut, an entrance or a new caption line is)
    abitrate = "320k"
    proxy_h = 540                         # OB Studio: a 540p proxy of the 4K master

    def __init__(self, beats_dir, h, arg):
        import assemble as AS
        self.AS = AS; self.h = h; sp = self.spec = load_spec(arg); self.key = sp["key"]; self.name = "longform:" + self.key
        self.W, self.R, self.H = sp["work"], sp["render_dir"], sp["work"] + "/hf"
        self.beats_dir = os.path.abspath(os.path.expanduser(beats_dir)) if beats_dir else sp["beats_dir"]
        self.fps = FPS; self.readonly = bool(sp.get("readonly"))
        self.src = sp["env"].get("OB_SRC") or sp.get("src")
        # ---- frame grid (as assemble.main)
        self.shots, ef = [], 0
        for s in json.load(open(self.W + "/cutlist.json"))["segments"]:
            a0, b0 = fr(s["src_in"]), fr(s["src_out"])
            if b0 <= a0: continue
            self.shots.append(dict(i=s["i"], src0=a0, src1=b0, e0=ef, e1=ef + (b0 - a0), framing=s["framing"], hold=bool(s.get("hold")), clip=s.get("clip"),
                                   pre=s.get("pre_vf", ""), punch=sorted(fr(t) for t in s.get("punch_at", [])), src_in=s["src_in"], src_out=s["src_out"]))
            ef += b0 - a0
        self.n_frames = self.N = ef
        self.evs = json.load(open(self.W + "/events_resolved.json"))["events"]
        for e in self.evs: e["f0"], e["f1"] = fr(e["edit_in"]), min(self.N, fr(e["edit_out"]))
        self._ownership()
        self.seg_of = np.zeros(self.N, np.int32)
        for k, s in enumerate(self.shots): self.seg_of[s["e0"]:s["e1"]] = k
        # ---- spoken words (edit time) and caption lines
        w = json.load(open(sp["words"]))["words"]
        self.ob_words = [dict(w=x[2], s=x[0], e=x[1], who="ob") for x in w]
        self.lines = h.caption_lines(self.ob_words); self.line_of, self.line_text = {}, []
        for li, (a, b) in enumerate(self.lines):
            self.line_text.append(" ".join(x["w"].strip() for x in self.ob_words[a:b + 1]))
            for i in range(a, b + 1): self.line_of[i] = li
        self.cap = self._caption_table()
        # ---- sound
        hits = json.load(open(sp["sfx_plan"]))["hits"] if os.path.exists(sp["sfx_plan"]) else []
        self.base_plan = [(x["file"], float(x["t"]), float(x.get("db", -14.0)), re.sub(r"[_-]?\d+$", "", os.path.splitext(os.path.basename(x["file"]))[0])) for x in hits]
        self.cues = json.load(open(sp["score"])).get("cues", []) if os.path.exists(sp["score"]) else []
        self.chs = self._chapters()
        self._segs = None

    # ------------------------------------------------------------------ the ownership table (assemble.py's own rules)
    def _ownership(self):
        AS, N = self.AS, self.N; evs = self.evs
        own = [None] * N
        for e in sorted([e for e in evs if not e.get("inlay")], key=lambda e: -e["f0"]):
            a_, b_ = max(e["f0"], 0), min(e["f1"], N); own[a_:b_] = [e] * (b_ - a_)
            for h0, h1 in e.get("holes", []):
                for f in range(max(fr(h0), a_), min(fr(h1), b_)):
                    if own[f] is e: own[f] = None
        for e in sorted([e for e in evs if e.get("inlay")], key=lambda e: (e["type"] == "ffcover", e["f0"])):
            a_, b_ = max(e["f0"], 0), min(e["f1"], N); own[a_:b_] = [e] * (b_ - a_)
        self.own = own; self.cover = {id(e): AS.is_cover(e) for e in evs}
        self.units = []                                     # [{"kind","f0","f1","ev"|"piece","off"}]
        f = 0
        while f < N:
            g = f
            while g < N and own[g] is own[f]: g += 1
            if own[f] is None:
                cur = f
                for p in self.src_pieces(f, g):
                    self.units.append(dict(kind="aroll", f0=cur, f1=cur + p[1], piece=p)); cur += p[1]
            else: self.units.append(dict(kind="event", f0=f, f1=g, ev=own[f], off=f - own[f]["f0"]))
            f = g

    def src_pieces(self, f0, f1):
        out = []
        for s in self.shots:
            lo, hi = max(f0, s["e0"]), min(f1, s["e1"])
            if hi <= lo: continue
            edges = [lo] + [p for p in s["punch"] if lo < p < hi] + [hi]
            for a_, b_ in zip(edges, edges[1:]):
                k = sum(1 for p in s["punch"] if p <= a_)
                fram = s["framing"] if k % 2 == 0 else ("wide" if s["framing"] == "punch" else "punch")
                out.append((s["src0"] + (a_ - s["e0"]), b_ - a_, fram, s["pre"]))
        return out

    def _caption_table(self):
        W, N = self.ob_words, self.N; cap = [-1] * N; idx = -1
        for k in range(N):
            t = k / FPS
            while idx + 1 < len(W) and W[idx + 1]["s"] - 0.04 <= t: idx += 1
            if idx >= 0 and t <= W[idx]["e"] + 0.35: cap[k] = self.line_of[idx]
        return cap

    # ------------------------------------------------------------------ chapters
    def _chapters(self):
        ce = sorted([e for e in self.evs if e["type"] == "chapter"], key=lambda e: e["edit_in"])
        end = next((e for e in self.evs if e["type"] == "end"), None)
        starts = [(0.0, "Hook and intro")] + [(e["edit_in"], (e.get("title") or e["id"])) for e in ce] + ([(end["edit_in"], "Close and call to action")] if end else [])
        out = []
        for i, (t, name) in enumerate(starts):
            t1 = starts[i + 1][0] if i + 1 < len(starts) else self.N / FPS
            f0, f1 = (0 if i == 0 else fr(t)), (fr(starts[i + 1][0]) if i + 1 < len(starts) else self.N)
            out.append(dict(n=i, name=name, t0=round(f0 / FPS, 3), t1=round(f1 / FPS, 3), f0=f0, f1=f1, color=PALETTE[i % len(PALETTE)]))
        return out
    def chapters(self): return self.chs
    def chapter_at(self, t):
        for c in self.chs:
            if c["t0"] - 1e-6 <= t < c["t1"] - 1e-6: return c["n"]
        return self.chs[-1]["n"]

    # ------------------------------------------------------------------ beats.py interface: frames
    def frame_path(self, k): return None
    def render_frame(self, k): raise RuntimeError("long-form renders units, not frames: use redo")
    def state(self, k):
        e = self.own[k]; cap = self.line_text[self.cap[k]] if self.cap[k] >= 0 else None
        sg = self.shots[int(self.seg_of[k])]
        if e is None:
            return dict(shot=f"a{sg['i']}", graphic="face", caption=cap, elements=["OB on camera" + (", punched in" if self._punched(sg, k) else "")])
        desc = re.sub(r"<[^>]+>", "", e.get("desc") or f"{e['type']} {e['id']}")
        if self.cover[id(e)]: return dict(shot="ev:" + e["id"], graphic=f"{e['type']}:{e['id']}", caption=cap, elements=[f"{e['id']} full-frame {e['type']}: {desc}"[:150]])
        return dict(shot=f"a{sg['i']}", graphic=f"{e['type']}:{e['id']}", caption=cap, elements=[f"{e['id']} {e['type']} over OB: {desc}"[:150]])
    def _punched(self, sg, k): return sum(1 for p in sg["punch"] if p <= k) % 2 == 1
    def words(self): return list(self.ob_words)
    def kind_of(self, graphic):
        if not graphic or graphic == "face": return "face"
        t, _, i = graphic.partition(":")
        if t == "end": return "cta"
        e = next((x for x in self.evs if x["id"] == i), None)
        return "src" if e is not None and self.cover[id(e)] else "board"
    def kinds(self): return {"face": "OB on camera", "src": "full-frame card or b-roll", "board": "graphic over him", "cta": "end card"}

    # ------------------------------------------------------------------ sound
    def base_sfx_plan(self): return list(self.base_plan)
    def sfx_plan(self): return self.h.apply_sfx_overrides(self.base_plan, self.beats_dir)
    def music_on(self, t): return any(c["t0"] <= t < c["t1"] for c in self.cues)
    def music_file(self): return self.cues[0]["track"] if self.cues else None
    def music_db(self): return self.cues[0].get("db") if self.cues else None
    def music_tracks(self): return [dict(t0=c["t0"], t1=c["t1"], name=c.get("name") or os.path.basename(c["track"]), why=c.get("why"), db=c.get("db")) for c in self.cues]
    def families(self):
        fams = {}
        for f in sorted(glob.glob(os.path.expanduser("~/ob-editor/assets/sfx/*.wav"))):
            fam = re.sub(r"[_-]?\d+$", "", os.path.splitext(os.path.basename(f))[0]); fams.setdefault(fam, []).append(f)
        for f, _, _, fam in self.base_plan: fams.setdefault(fam, [])
        return fams
    def _mix_extra(self): return "|".join(c["track"] + str(c.get("db")) + str(c["t0"]) for c in self.cues)
    def mix_sig(self): return self.h.plan_sig(self.sfx_plan(), self._mix_extra())
    def base_mix_sig(self): return self.h.plan_sig(self.base_plan, self._mix_extra())
    def base_mix(self): return self.R + "/mix.wav"
    def audio(self, out_wav):
        """The engine's own mix.wav (voice + sfx bus + score) with its sfx bus taken out and the CURRENT plan's bus put in: audio only, same gains as assemble.py."""
        from scipy.io import wavfile
        import score as SC
        sr, mix = wavfile.read(self.R + "/mix.wav"); _, bus0 = wavfile.read(self.R + "/sfx_only.wav"); _, sc = wavfile.read(self.R + "/score_bed.wav")
        mix = mix.astype(np.float64); bus0 = bus0.astype(np.float64); sc = sc.astype(np.float64)
        voice = mix - bus0[:, None] - sc; vref = SC._speech_db(voice.mean(1)); bus = np.zeros(len(bus0)); cache = {}
        def loadf(path):
            if path not in cache:
                raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
                x = np.frombuffer(raw, np.float32).astype(np.float64); fr_ = int(0.1 * sr); k = max(1, len(x) // fr_)
                cache[path] = (x, 10 * np.log10(max(((x[: k * fr_].reshape(k, fr_) ** 2).mean(1)).max(), 1e-12)))
            return cache[path]
        for f, t, db, _ in self.sfx_plan():
            x, pk = loadf(f); g = 10 ** ((vref + db - pk) / 20); i0 = int(round(t * sr)); lo, hi = max(0, i0), min(len(bus), i0 + len(x))
            if hi > lo: bus[lo:hi] += g * x[lo - i0: hi - i0]
        wavfile.write(out_wav, sr, (mix - bus0[:, None] + bus[:, None]).astype(np.float32))

    # ------------------------------------------------------------------ output
    def final_path(self): return self.spec.get("final") or os.path.join(self.beats_dir, "out", "current.mp4")
    def full_render_s(self): return self.spec.get("full_render_s")
    def encode(self, out, wav): raise RuntimeError("long-form encodes per segment: use build / redo")
    def _vin(self, video): return ["-f", "concat", "-safe", "0", "-i", video] if video.endswith(".txt") else ["-i", video]   # a segment list or a video file
    def _tags(self): return ["-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
                              "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    def mux_audio(self, video, wav, out):
        """Picture copied, sound = wav loudnormed to -14 LUFS (two passes), AAC 320k; true peak tightened until the gate's rule holds (as assemble.py + tp_fix.py)."""
        import tp_fix, voice_master as VM
        tmp = out[:-4] + ".part.mp4"; q = None
        for tp in (-1.5, -2.0, -2.5, -3.0):
            af = tp_fix.loudnorm(wav, tp)
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + self._vin(video) + ["-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy"] + self._tags()
                           + ["-af", af + ",aresample=48000", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-shortest", tmp], check=True)
            q = VM.check(tmp); print(f"  audio mux at {tp} dBTP: {q['lufs']} LUFS, true peak {q['true_peak']} dBTP, flat tops {q['flat_tops']}", flush=True)
            if tp_fix.ok(q): break
        os.replace(tmp, out)
    def mux_copy_audio(self, video, audio_from, out):
        tmp = out[:-4] + ".part.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + self._vin(video) + ["-i", audio_from, "-map", "0:v", "-map", "1:a", "-c", "copy"] + self._tags()
                       + ["-movflags", "+faststart", tmp], check=True)    # no -shortest: the copied audio ends ~1 ms before the last picture and -shortest would drop that frame
        os.replace(tmp, out)

    def gate(self, out):
        import qc_gate as Q
        shots = [s for s in self.shots if not s["hold"]]
        segs = [(self.spec["mic"], s["src_in"], s["src_out"], round(ft(s["e0"]), 6)) for s in shots]
        cam = [(self.src, s["src_in"], s["src_out"], round(ft(s["e0"]), 6)) for s in shots]       # the camera's own sound at the same source time (the master shares its timeline)
        ok = Q.after_render(out, long=True, work=self.W, cards=Q.cover_spans(self.W), segs=segs, cam=cam,
                            sfx_plan=self.spec["sfx_plan"] if os.path.exists(self.spec["sfx_plan"]) else None)
        print("gate report:", Q.report_path(out)); return bool(ok)

    # ------------------------------------------------------------------ segments
    def segments(self):
        if self._segs is not None: return self._segs
        ub = sorted({u["f0"] for u in self.units} | {self.N}); smax = fr(self.spec["seg_max_s"]); out = []
        for c in self.chs:
            n = max(1, math.ceil((c["f1"] - c["f0"]) / smax)); cuts = [c["f0"]]
            for j in range(1, n):
                tgt = c["f0"] + (c["f1"] - c["f0"]) * j / n; i = bisect.bisect_left(ub, tgt)
                cand = [x for x in ub[max(0, i - 1):i + 1] if cuts[-1] < x < c["f1"]]
                if cand: cuts.append(min(cand, key=lambda x: abs(x - tgt)))
            cuts.append(c["f1"])
            for a, b in zip(cuts, cuts[1:]): out.append(dict(i=len(out), ch=c["n"], f0=a, f1=b))
        self._segs = out; return out
    def sdir(self): return os.path.join(self.beats_dir, "seg")
    def seg_file(self, i): return os.path.join(self.sdir(), f"s{i:02d}.mp4")
    def manifest(self): return self.h.jload(os.path.join(self.sdir(), "manifest.json"))

    def _assemble_env(self, extra=None):
        env = dict(os.environ); env.update(self.spec["env"]); env.update(OB_VIDEO_ONLY="1", OB_RENDER_DIR=self.R, OB_TMPDIR=self.spec["tmp_dir"], HYPERFRAMES_RENDER_DETACHED="1")
        env.pop("OB_SFX", None); os.makedirs(self.spec["tmp_dir"], exist_ok=True); env.update(extra or {}); return env
    def render_range(self, f0, f1, log=print):
        """assemble.py --range for [f0, f1): the picture only. Cached units are reused by key; only what changed is rendered. -> R/video.mp4, stats"""
        cmd = [sys.executable, "-I", BIN + "/assemble.py", self.W, self.beats_dir + "/tmp_unused.mp4", "--keep", "--range", f"{ft(f0):.9f}", f"{ft(f1):.9f}"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self._assemble_env()); lines = []
        for line in p.stdout:
            line = line.rstrip(); lines.append(line)
            if line.startswith(("rendered", "cached", "units:", "range", "video only")) or "FAILED" in line or "Error" in line: log("    " + line[:200])
        p.wait()
        if p.returncode: sys.exit("assemble.py failed on the range:\n" + "\n".join(lines[-25:]))
        m = next((re.search(r"units: (\d+), (\d+) encoded, (\d+) reused", l) for l in lines if l.startswith("units:")), None)
        return dict(units=int(m.group(1)) if m else None, encoded=int(m.group(2)) if m else None, events_rendered=sum(1 for l in lines if l.startswith("rendered")))

    def label_windows(self, t0, t1):
        if not os.path.exists(self.spec["labels"]): return []
        out = []
        for l in json.load(open(self.spec["labels"]))["labels"]:
            w = [[max(a, t0) - t0, min(b, t1) - t0] for a, b in l.get("windows", []) if b > t0 and a < t1]
            if w: out.append((l["png"], w))
        return out
    def encode_segment(self, s, src_video, aside=None):
        """burn the chapter labels into this segment's picture (VideoToolbox, the labels pass of render_final.sh); no labels in it: the unit concat is the segment"""
        dst = self.seg_file(s["i"]); tmp = dst[:-4] + ".part.mp4"; os.makedirs(self.sdir(), exist_ok=True); L = self.label_windows(ft(s["f0"]), ft(s["f1"]))
        if not L: shutil.copyfile(src_video, tmp)
        else:
            cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src_video] + sum((["-i", p] for p, _ in L), []); fc, last = [], "0:v"
            for k, (_, w) in enumerate(L):
                en = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in w); fc.append(f"[{last}][{k + 1}:v]overlay=x=96:y=H-h-96:enable='{en}'[v{k}]"); last = f"v{k}"
            cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-an", "-c:v", "h264_videotoolbox", "-b:v", "42M", "-maxrate", "56M", "-bufsize", "84M",
                    "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", f"{FPS_N}/{FPS_D}", "-video_track_timescale", "30000", "-g", "30", "-movflags", "+faststart", tmp]
            subprocess.run(cmd, check=True)
        if os.path.exists(dst) and aside: self.h.move_aside(dst, os.path.join(aside, "seg"))      # the old segment is moved aside, never overwritten
        os.replace(tmp, dst); return dst
    def count_frames(self, p):
        r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "default=nw=1:nk=1", p)
        return int(r.stdout.strip() or 0)
    def build_segment(self, s, log=print, aside=None):
        t0 = time.time(); st = self.render_range(s["f0"], s["f1"], log); t1 = time.time()
        self.encode_segment(s, self.R + "/video.mp4", aside); n = self.count_frames(self.seg_file(s["i"]))
        if n != s["f1"] - s["f0"]: sys.exit(f"segment s{s['i']:02d} has {n} frames, expected {s['f1'] - s['f0']}: the timing changed, run  beats.py map  and  build --force")
        return dict(i=s["i"], f0=s["f0"], f1=s["f1"], frames=n, md5=self.h.md5_file(self.seg_file(s["i"])), t_units=round(t1 - t0, 1), t_encode=round(time.time() - t1, 1), **st)
    def join(self):
        """the segment list for the concat demuxer; the mux reads it directly (-c copy), so there is no second 2 GB copy of the picture"""
        lst = os.path.join(self.sdir(), "joined.txt"); open(lst, "w").write("".join(f"file '{self.seg_file(s['i'])}'\n" for s in self.segments())); return lst

    def packet_hashes(self, p):
        r = sh("ffmpeg", "-nostdin", "-v", "error", "-i", p, "-map", "0:v:0", "-c", "copy", "-f", "framemd5", "-")
        return [l.rsplit(",", 1)[1].strip() for l in r.stdout.splitlines() if l and not l.startswith("#")]
    def sync_check(self, p, edges=None):
        """frame count, PTS spacing, keyframes on every segment start, audio length vs picture length"""
        r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", p)
        rows = [l.split(",") for l in r.stdout.splitlines() if l.strip()]; rows.sort(key=lambda x: float(x[0])); pts = np.array([float(x[0]) for x in rows]); key = [("K" in x[1]) for x in rows]
        d = np.diff(pts); dev = float(np.abs(d - FPS_D / FPS_N).max()) * 1000 if len(d) else 0.0
        info = json.loads(sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", p).stdout)["streams"]
        dur = {s["codec_type"]: float(s["duration"]) for s in info if s.get("duration")}
        edges = [s["f0"] for s in self.segments()] if edges is None else edges
        miss = [e for e in edges if e >= len(key) or not key[e]]
        ok = len(pts) == self.N and dev < 1.0 and not miss and ("audio" not in dur or abs(dur["audio"] - dur["video"]) < 0.030)
        print(f"  sync: {len(pts)} of {self.N} frames, pts spacing off by at most {dev:.3f} ms, {len(edges) - len(miss)} of {len(edges)} segment starts are keyframes"
              + (f", video {dur.get('video', 0):.3f} s / audio {dur.get('audio', 0):.3f} s (diff {abs(dur.get('audio', 0) - dur.get('video', 0)) * 1000:.0f} ms)" if "audio" in dur else "") + f"  -> {'OK' if ok else 'PROBLEM'}")
        return ok

    # ------------------------------------------------------------------ commands
    def cmd_map(self, args):
        h = self.h; t0 = time.time(); beats = h.compute_beats(self); chs = self.chs
        for b in beats:
            b["ch"] = self.chapter_at(b["t0"]); b["kind"] = self.kind_of(b["graphic"])
            b["cut"] = any(r == "cut" for r in b["reasons"])
        h.jsave(os.path.join(self.beats_dir, "beats.json"), dict(edit=self.name, fps=self.fps, n_frames=self.N, min_beat=h.MIN_BEAT, made=time.strftime("%Y-%m-%d %H:%M:%S"),
                                                                   chapters=chs, beats=beats))
        per = {c["n"]: sum(1 for b in beats if b["ch"] == c["n"]) for c in chs}
        print(f"{self.name}: {len(beats)} beats in {len(chs)} chapters, {h.fmt_t(self.N / FPS)} ({time.time() - t0:.1f}s)\n  {os.path.join(self.beats_dir, 'beats.json')}")
        for c in chs: print(f"  ch{c['n']} {h.fmt_t(c['t0'])}-{h.fmt_t(c['t1'])} {per[c['n']]:>3} beats  {c['name']}")

    def cmd_build(self, args):
        h = self.h
        if self.readonly: sys.exit(f"{self.key} is read-only (its render folder is the delivered edit's cache); build/redo run on a copy")
        segs = self.segments(); man = self.manifest(); force = "--force" in args
        keep = {m["i"]: m for m in (man or {}).get("segs", []) if not force and (m["f0"], m["f1"]) == next(((s["f0"], s["f1"]) for s in segs if s["i"] == m["i"]), None) and os.path.exists(self.seg_file(m["i"]))}
        if "--resume" in args and not force:      # a build cut off by a restart: trust segment files already on disk whose frame count is right
            for s_ in segs:
                f_ = self.seg_file(s_["i"])
                if s_["i"] not in keep and os.path.exists(f_) and not f_.endswith(".part.mp4") and self.count_frames(f_) == s_["f1"] - s_["f0"]:
                    keep[s_["i"]] = dict(i=s_["i"], f0=s_["f0"], f1=s_["f1"], frames=s_["f1"] - s_["f0"], md5=h.md5_file(f_), t_units=0, t_encode=0, units=None, encoded=0, events_rendered=0)
            print(f"resume: {len(keep)} segment files kept", flush=True)
        h.wait_free(); T0 = time.time(); rows = []; aside = os.path.join(self.beats_dir, "aside", time.strftime("%Y%m%d-%H%M%S"))
        for n, s in enumerate(segs, 1):
            if s["i"] in keep: rows.append(keep[s["i"]]); continue
            r = self.build_segment(s, aside=aside); rows.append(r); print(f"  rendered {n}/{len(segs)}  s{s['i']:02d} ch{s['ch']} frames {s['f0']}-{s['f1'] - 1}: units {r['t_units']}s ({r['encoded']} encoded, {r['events_rendered']} events), labels {r['t_encode']}s", flush=True)
        os.makedirs(self.sdir(), exist_ok=True); h.jsave(os.path.join(self.sdir(), "manifest.json"), dict(made=time.strftime("%Y-%m-%d %H:%M:%S"), n_frames=self.N, segs=rows))
        tj = time.time(); joined = self.join(); st = h.jload(os.path.join(self.beats_dir, "state.json"), {}); wav, remix = h.ensure_mix(self, st)
        out = os.path.join(self.beats_dir, "out", "current.mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out): h.move_aside(out, aside)
        self.mux_audio(joined, wav, out); h.jsave(os.path.join(self.beats_dir, "state.json"), st); t_join = time.time() - tj
        ok = self.sync_check(out); total = time.time() - T0
        print(f"\nBUILD {len(segs)} segments ({len(rows) - len(keep)} built, {len(keep)} kept) in {total:.1f}s (join + audio {t_join:.1f}s)\n  output: {out}")
        return ok

    def invalidate(self, f0, f1, aside):
        """move aside (never delete) everything the picture of frames [f0, f1) is cached in, so the next render makes it fresh"""
        R, AS = self.R, self.AS; moved = []; lut = os.path.getmtime(AS.LUT)
        def mv(p, sub):
            for q in (p, p + ".key"):
                if os.path.exists(q): os.makedirs(os.path.join(aside, sub), exist_ok=True); shutil.move(q, os.path.join(aside, sub, os.path.basename(q))); moved.append(os.path.basename(q))
        seen = set()
        def unit_name(key): return f"{R}/units/k{hashlib.sha1(key.encode()).hexdigest()[:16]}.mp4"
        for u in self.units:
            if u["f1"] <= f0 or u["f0"] >= f1: continue
            if u["kind"] == "aroll":
                s0, n, fram, pre = u["piece"]; mv(unit_name(f"{s0}:{n}:{fram}:{lut}" + (f":{pre}" if pre else "")), "units")
            else:
                e = u["ev"]; kp = f"{R}/events/{e['id']}.mp4.key"
                if os.path.exists(kp):
                    hk = open(kp).read(); n = u["f1"] - u["f0"]; mv(unit_name(hk + (f":{n}" if u["off"] == 0 else f":{u['off']}:{n}")), "units")
                if e["id"] in seen: continue
                seen.add(e["id"]); mv(f"{R}/events/{e['id']}.mp4", "events")
                if not self.cover[id(e)]:
                    mv(f"{self.H}/assets/aroll/{e['id']}.mp4", "aroll")
                    for j, (s0, nn, fram, pre) in enumerate(self.src_pieces(e["f0"], e["f1"])): mv(f"{R}/units/ar_{e['id']}_{j}.mp4", "aroll")
        return moved

    def cmd_redo(self, args):
        h = self.h; ids = [int(a) for a in args if a.isdigit()]
        if not ids: sys.exit("usage: beats.py redo longform:<project> <beat#>... [--no-force] [--no-gate]")
        if self.readonly: sys.exit(f"{self.key} is the delivered edit opened read-only: redo runs on a copy (a project with readonly false)")
        man = self.manifest()
        if not man: sys.exit("no segment encodes yet: run  beats.py build longform:" + self.key)
        beats = h.load_beats(self); sel = h.pick(beats, ids); segs = self.segments()
        if [(m["i"], m["f0"], m["f1"]) for m in man["segs"]] != [(s["i"], s["f0"], s["f1"]) for s in segs]: sys.exit("the segment map changed (cutlist or events): run  build --force")
        T0 = time.time(); ks = sorted({k for b in sel for k in range(b["k0"], b["k1"])}); nb = len(ks)
        touched = [s for s in segs if any(s["f0"] <= b["k0"] < s["f1"] or s["f0"] < b["k1"] <= s["f1"] for b in sel)]
        bd = self.beats_dir; stamp = time.strftime("%Y%m%d-%H%M%S"); aside = os.path.join(bd, "aside", stamp); out = os.path.join(bd, "out", "current.mp4")
        before = self.packet_hashes(out) if os.path.exists(out) else None
        h.wait_free(); moved = []
        if "--no-force" not in args:
            for b in sel: moved += self.invalidate(b["k0"], b["k1"], aside)
            print(f"invalidated {len(moved)} cached files for {len(sel)} beat(s) (moved aside to {aside})", flush=True)
        tr = time.time(); rows = {m["i"]: m for m in man["segs"]}
        for n, s in enumerate(touched, 1):
            r = self.build_segment(s, aside=aside); rows[s["i"]] = r
            print(f"  rendered {n}/{len(touched)}  s{s['i']:02d} ch{s['ch']}: units {r['t_units']}s ({r['encoded']} units encoded, {r['events_rendered']} events rendered), labels {r['t_encode']}s", flush=True)
        t_seg = time.time() - tr
        same = [s["i"] for s in segs if s["i"] not in {t["i"] for t in touched} and h.md5_file(self.seg_file(s["i"])) == rows[s["i"]]["md5"]]
        print(f"verify: {len(same)} of {len(segs) - len(touched)} other segments byte-identical (md5 against the manifest)")
        if len(same) != len(segs) - len(touched): sys.exit("STOP: a segment outside the redo changed")
        h.jsave(os.path.join(self.sdir(), "manifest.json"), dict(made=time.strftime("%Y-%m-%d %H:%M:%S"), n_frames=self.N, segs=[rows[s["i"]] for s in segs]))
        tj = time.time(); joined = self.join(); st = h.jload(os.path.join(bd, "state.json"), {}); wav, remix = h.ensure_mix(self, st)
        prev = h.move_aside(out, aside) if os.path.exists(out) else None; os.makedirs(os.path.dirname(out), exist_ok=True)
        if remix or not prev: self.mux_audio(joined, wav, out)
        else: self.mux_copy_audio(joined, prev, out)
        h.jsave(os.path.join(bd, "state.json"), st); t_join = time.time() - tj
        after = self.packet_hashes(out); lo = min(s["f0"] for s in touched); hi = max(s["f1"] for s in touched)
        if before and len(before) != len(after): sys.exit(f"STOP: the new file has {len(after)} frames, the previous one {len(before)}; the previous file is in {aside}")
        if before:
            outside = [k for k in range(len(after)) if not (lo <= k < hi) and before[k] != after[k]]; inside = sum(1 for k in range(lo, hi) if before[k] != after[k])
            print(f"verify: {len(after) - (hi - lo)} frames outside the re-encoded segment compared with the previous file: {len(outside)} differ; inside it {inside} of {hi - lo} differ")
            if outside: sys.exit(f"STOP: frames outside the redo changed {outside[:5]}; the previous file is in {aside}")
        self.sync_check(out)
        ok = None; t_gate = 0.0
        if "--no-gate" not in args: tg = time.time(); ok = self.gate(out); t_gate = time.time() - tg
        total = time.time() - T0; full = self.full_render_s(); sf = sum(s["f1"] - s["f0"] for s in touched)
        print(f"\nREDO beats {ids}: {nb} of {self.N} frames ({100 * nb / self.N:.1f}%) re-rendered, in {len(touched)} of {len(segs)} segments ({sf} frames re-encoded)\n  units+labels {t_seg:.1f}s"
              f" + join/mux {t_join:.1f}s" + (f" + gate {t_gate:.1f}s" if ok is not None else "") + f"  = {total:.1f}s total ({total - t_gate:.1f}s without the gate)"
              + f"\n  full render: {('%.0fs (last cold full render of this edit)' % full) if full else 'n/a'}" + f"\n  output: {out}"
              + (f"\n  GATE: {'PASS' if ok else 'NOT PASS'}" if ok is not None else "\n  gate skipped"))
        return ok

    def cmd_check(self, args):
        out = os.path.join(self.beats_dir, "out", "current.mp4"); out = out if os.path.exists(out) else self.final_path()
        print("checking", out); ok = self.sync_check(out) if os.path.exists(self.sdir() + "/manifest.json") else None
        if ok is None: self.sync_check(out, edges=[0])
        if "--no-gate" not in args: print("GATE:", "PASS" if self.gate(out) else "NOT PASS")


def make(beats_dir, h, arg="c4423"): return Adapter(beats_dir, h, arg)
