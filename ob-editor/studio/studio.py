#!/usr/bin/env python3
"""OB Studio: a local video-editor page over beats.py (built 2026-11-07, laid out like chase_ai_'s "Beat Review v2").

  python3 studio.py serve <edit> [--dir D] [--port 8765]    open http://localhost:8765
  python3 studio.py requests <edit> [--dir D] [--all]        what OB sent (queued + Claude working; --all for every request)
  python3 studio.py mark <edit> <id> working|done|failed [--reply "what changed"] [--dir D]
  python3 studio.py lanes <edit> [--dir D]                   (internal) the sound + music lanes as JSON

<edit> and --dir mean what they mean for beats.py (an adapter name such as ozempic, or a path to an adapter .py).
The page shows the newest render (D/out/current.mp4 or the adapter's final file, whichever is newer) as a 720p proxy,
a timeline with three tracks (beats, sound effects, music), the beat list, the sound cues and OB's notes.
OB taps a beat, a sound or the music, types a request, and presses Send to Claude.

FILES (all inside D, the beats folder; nothing else is written)
  D/requests.json      every request. status: draft (not sent) -> queued (sent to Claude) -> working -> done | failed;
                       rendering = the studio is running it. Claude: read the queued ones, mark them working, act,
                       re-render, then mark done with a one-line reply. The page polls this file and reloads the
                       preview when the video changes.
  D/studio/            proxy cache (cache/proxy-<ver>.mp4, strip-<ver>.jpg, thumbs-<ver>/ for the long-form beat list), lanes.json, jobs.log
Mechanical requests (redo a beat, swap a sound) can run from the page (Render): they call beats.py redo / sfx swap,
one job at a time. Nothing here delivers anything: no AirDrop, no READY folder. Delivery stays manual, after the gate.
"""
import os, sys, json, time, glob, math, fcntl, hashlib, mimetypes, subprocess, threading, urllib.parse, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.expanduser("~/ob-editor/bin")
BEATS = os.path.join(BIN, "beats.py")
if BIN not in sys.path: sys.path.insert(0, BIN)
import beats as H   # helpers only (importing beats.py renders nothing)

STATUS = ("draft", "queued", "working", "rendering", "done", "failed", "withdrawn")
HOW = ("OB Studio requests. status draft = not sent yet; queued = OB pressed Send to Claude. Claude: mark each one working "
       "(python3 ~/ob-editor/studio/studio.py mark <edit> <id> working), make the change, re-render (beats.py redo <edit> <beat> "
       "for a beat-local change, beats.py map <edit> again if timing changed), then mark it done with --reply \"what changed\". "
       "action = a mechanical job the page can run itself (redo / swap). Never deliver from here.")


def now(): return time.strftime("%Y-%m-%d %H:%M:%S")
def py(): return sys.executable or "python3"


# ------------------------------------------------------------------ requests.json (locked read-modify-write)
class Requests:
    def __init__(self, bd, edit):
        self.p = os.path.join(bd, "requests.json"); self.lockp = self.p + ".lock"; self.edit = edit
    def _read(self):
        try: j = json.load(open(self.p))
        except FileNotFoundError: j = {}
        except json.JSONDecodeError as e: raise RuntimeError(f"{self.p} is not valid JSON ({e}); fix it by hand, nothing was written")
        j.setdefault("requests", []); return j
    def read(self):
        with open(self.lockp, "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_SH); return self._read()
    def change(self, fn):
        with open(self.lockp, "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX); j = self._read(); out = fn(j)
            j["edit"] = j.get("edit") or self.edit; j["how"] = HOW; j["updated"] = now(); H.jsave(self.p, j); return out


def next_id(j):
    n = [int(r["id"][1:]) for r in j["requests"] if re.fullmatch(r"r\d+", str(r.get("id", "")))]
    return "r%d" % (max(n) + 1 if n else 1)


# ------------------------------------------------------------------ lanes (runs the adapter, in a subprocess from the server)
def cmd_lanes(edit, bdir):
    A = H.load_adapter(edit, bdir); bd = A.beats_dir; fps = A.fps; N = A.n_frames
    bj = H.jload(os.path.join(bd, "beats.json"), {}) or {}; beats = bj.get("beats", [])
    W = sorted(A.words(), key=lambda w: w["s"]); plan = A.sfx_plan(); base = A.base_sfx_plan()
    fams = A.families() if hasattr(A, "families") else {}
    bymame = {}
    for fs in fams.values():
        for f in fs: bymame.setdefault(os.path.basename(f), f)
    def absp(f):
        if os.path.isabs(f): return f
        if hasattr(A, "sfx_abspath"): return A.sfx_abspath(f)
        for r in H.SFX_ROOTS:
            if os.path.exists(os.path.join(r, f)): return os.path.join(r, f)
        return bymame.get(os.path.basename(f), f)
    def beat_at(on):
        for b in beats:
            if b["t0"] - H.LEAD <= on < b["t1"] - H.LEAD: return b
        return beats[-1] if beats and on >= beats[-1]["t0"] else None
    sfx = []
    for i, (item, bi) in enumerate(zip(plan, base)):
        on = A.sfx_onset(item) if hasattr(A, "sfx_onset") else item[1]; b = beat_at(on); idx = None
        if b:
            for j, s in enumerate(b.get("sfx", []), 1):
                if abs(s["t"] - item[1]) < 0.0015: idx = j; break
        near = [w for w in W if on - 0.2 <= w["s"] <= on + 0.4]
        w = min(near, key=lambda w: abs(w["s"] - on)) if near else None
        sfx.append(dict(i=i, file=item[0], abs=absp(item[0]), base=bi[0], name=os.path.basename(item[0]), was=os.path.basename(bi[0]),
                        swapped=item[0] != bi[0], fam=item[3], t=round(item[1], 3), onset=round(on, 3), db=item[2],
                        beat=b["id"] if b else None, idx=idx, word=w["w"].strip(" ,.?!") if w else None, who=w.get("who", "ob") if w else None,
                        ctx=(b["on_screen"][0] if b and b.get("on_screen") else "")))
    segs, cur = [], None
    for k in range(N):
        on = bool(A.music_on(k / fps))
        if on and cur is None: cur = k
        if not on and cur is not None: segs.append([round(cur / fps, 3), round(k / fps, 3)]); cur = None
    if cur is not None: segs.append([round(cur / fps, 3), round(N / fps, 3)])
    eng = getattr(A, "B", None)                                   # engine module, when the adapter wraps one (ozempic does)
    mfile = A.music_file() if hasattr(A, "music_file") else getattr(eng, "MUSIC", None)
    mdb = A.music_db() if hasattr(A, "music_db") else getattr(eng, "MUSIC_DB", None)
    music = dict(file=mfile, name=os.path.basename(mfile) if mfile else None, db=mdb, segments=segs)
    if hasattr(A, "music_tracks"): music["tracks"] = A.music_tracks()                  # long-form: one track per chapter, named in the music lane
    chs = A.chapters() if hasattr(A, "chapters") else []                                # long-form: the chapter lane + chapter headers in the beat list
    return dict(edit=A.name, beats_dir=bd, fps=fps, n_frames=N, dur=round(N / fps, 3), final=A.final_path(),
                stale=bool(bj) and bj.get("n_frames") != N, mapped=bj.get("made"), sfx=sfx, music=music,
                chapters=[{k: c[k] for k in ("n", "name", "t0", "t1", "color")} for c in chs], proxy_h=getattr(A, "proxy_h", None),
                kinds=A.kinds() if hasattr(A, "kinds") else None, readonly=bool(getattr(A, "readonly", False)),
                families={k: [absp(f) for f in v] for k, v in fams.items()})


def run_lanes(edit, bdir):
    cmd = [py(), "-I", os.path.abspath(__file__), "lanes", edit] + (["--dir", bdir] if bdir else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    line = next((l for l in reversed(r.stdout.splitlines()) if l.startswith("LANES_JSON ")), None)
    if not line: raise RuntimeError("lanes failed:\n" + (r.stderr or r.stdout)[-2000:])
    return json.loads(line[len("LANES_JSON "):])


# ------------------------------------------------------------------ the server
class Studio:
    def __init__(self, edit, bdir):
        self.edit, self.bdir = edit, bdir
        print("reading the edit (adapter) ...", flush=True)
        self.lanes = run_lanes(edit, bdir); self.bd = self.lanes["beats_dir"]
        self.sd = os.path.join(self.bd, "studio"); self.cache = os.path.join(self.sd, "cache"); os.makedirs(self.cache, exist_ok=True)
        H.jsave(os.path.join(self.sd, "lanes.json"), self.lanes)
        self.req = Requests(self.bd, self.lanes["edit"]); self.lk = threading.Lock(); self.joblock = threading.Lock()
        self.job = dict(running=False, lines=[], pct=None, label="", ok=None, ended=None)
        self.proxy = {}; self.building = None; self.lanes_key = self._lanes_key(); self.meta_ver = self._meta_ver()
        def fix(j):                                                    # a render cut off by a stopped server
            for r in j["requests"]:
                if r.get("status") == "rendering": r.update(status="failed", reply="the studio stopped during the render; run it again", updated=now())
        self.req.change(fix)
        self.video = self._video(); self._ensure_proxy(self.video, wait=True)
        threading.Thread(target=self._watch, daemon=True).start()

    # --- what is on disk
    def _video(self):
        cur = os.path.join(self.bd, "out", "current.mp4"); fin = self.lanes.get("final")
        c = [p for p in (cur, fin) if p and os.path.exists(p)]
        if not c: return None
        p = max(c, key=os.path.getmtime); st = os.stat(p)
        return dict(path=p, ver=hashlib.md5(f"{os.path.abspath(p)}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:8], mtime=st.st_mtime)
    def _lanes_key(self):
        fs = [os.path.join(self.bd, "beats.json"), os.path.join(self.bd, "sfx_overrides.json")]
        return "|".join(str(os.path.getmtime(f)) if os.path.exists(f) else "-" for f in fs)
    def _meta_ver(self):
        return hashlib.md5((self._lanes_key() + json.dumps(self.lanes.get("music")) + str(len(self.lanes.get("sfx", [])))).encode()).hexdigest()[:8]
    def gate(self, path):
        try:
            import qc_gate; rp = qc_gate.report_path(path)
            j = H.jload(rp)
            if j and abs(j.get("mtime", 0) - os.path.getmtime(path)) < 0.01: return j.get("result")
        except Exception: pass
        return None

    # --- proxy + filmstrip for one video version
    def _ensure_proxy(self, v, wait=False):
        if not v or v["ver"] in self.proxy: return
        if self.building == v["ver"]: return
        self.building = v["ver"]
        t = threading.Thread(target=self._build, args=(v,), daemon=True); t.start()
        if wait: t.join()
    def _build(self, v):
        try:
            out = os.path.join(self.cache, f"proxy-{v['ver']}.mp4"); strip = os.path.join(self.cache, f"strip-{v['ver']}.jpg"); mp = strip[:-4] + ".json"
            if not (os.path.exists(out) and os.path.exists(strip) and os.path.exists(mp)):
                print(f"proxy {v['ver']} from {v['path']} ...", flush=True); t0 = time.time()
                try:
                    import render_slots; render_slots.wait_free(log=print)
                except Exception as e: print("render_slots:", e)
                pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                                                "-of", "json", v["path"]], capture_output=True, text=True).stdout)
                w, h = pr["streams"][0]["width"], pr["streams"][0]["height"]; dur = float(pr["format"]["duration"]); tall = h >= w
                tmp = out[:-4] + ".part.mp4"
                ph = int(self.lanes.get("proxy_h") or 720)                       # long-form: a 540p proxy (the source is 4K and 40 minutes)
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", v["path"], "-vf", "scale=720:-2" if tall else f"scale=-2:{ph}",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-g", "12", "-keyint_min", "12", "-sc_threshold", "0",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", tmp], check=True)
                os.replace(tmp, out)
                iv = max(0.25, dur / (640 if self.lanes.get("proxy_h") else 400)); n = max(1, math.ceil(dur / iv)); cols = 20; rows = math.ceil(n / cols); cw, ch = (72, 128) if tall else (128, 72)
                tmp = strip[:-4] + ".part.jpg"
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", out, "-vf", f"fps=1/{iv},scale={cw}:{ch},tile={cols}x{rows}",
                                "-frames:v", "1", "-q:v", "4", tmp], check=True)
                os.replace(tmp, strip); H.jsave(mp, dict(cols=cols, rows=rows, cw=cw, ch=ch, n=n, interval=iv, dur=dur, w=w, h=h))
                print(f"proxy {v['ver']} ready in {time.time() - t0:.1f}s", flush=True)
            self.proxy[v["ver"]] = dict(mp4=out, strip=strip, meta=H.jload(mp))
        except Exception as e:
            print("proxy build failed:", e, flush=True)
        finally:
            self.building = None

    def _watch(self):
        while True:
            time.sleep(1.5)
            try:
                v = self._video()
                if v and (not self.video or v["ver"] != self.video["ver"]): self._ensure_proxy(v)
                if v and v["ver"] in self.proxy: self.video = v
                k = self._lanes_key()
                if k != self.lanes_key and not self.job["running"]:
                    self.lanes = run_lanes(self.edit, self.bdir); self.lanes_key = k
                    H.jsave(os.path.join(self.sd, "lanes.json"), self.lanes); self.meta_ver = self._meta_ver()
            except Exception as e:
                print("watch:", e, flush=True)

    # --- payloads
    def meta(self):
        bj = H.jload(os.path.join(self.bd, "beats.json"), {}) or {}
        return dict(lanes=self.lanes, beats=bj.get("beats", []), meta_ver=self.meta_ver)
    def state(self):
        v = self.video; p = self.proxy.get(v["ver"]) if v else None; j = self.req.read()
        live = [r for r in j["requests"] if r.get("status") != "withdrawn"]
        done = [r for r in live if r.get("status") == "done" and r.get("round")]
        last = max((r["round"] for r in done), default=None)
        changed = sorted({b for r in done if r["round"] == last for b in r.get("beats", [])})
        return dict(edit=self.lanes["edit"], video=dict(ver=v["ver"], name=os.path.basename(v["path"]), path=v["path"], mtime=v["mtime"],
                                                       ready=bool(p), strip=p["meta"] if p else None) if v else None,
                    building=self.building, gate=self.gate(v["path"]) if v else None, meta_ver=self.meta_ver,
                    stale=self.lanes.get("stale"), requests=live, changed=changed,
                    job={k: self.job[k] for k in ("running", "pct", "label", "ok", "ended")} | dict(lines=self.job["lines"][-12:]))

    # --- request edits from the page
    def add(self, body):
        tgt = body.get("target") or {}; text = (body.get("text") or "").strip(); act = body.get("action")
        if not text and not act: raise ValueError("empty request")
        if act and act.get("type") not in ("redo", "swap"): raise ValueError("unknown action")
        def f(j):
            r = dict(id=next_id(j), status="draft", created=now(), updated=now(), target=tgt, text=text, action=act,
                     beats=sorted({int(b) for b in ([tgt.get("beat")] if tgt.get("beat") else []) + ((act or {}).get("beats") or [])}),
                     t=tgt.get("t"), reply="")
            j["requests"].append(r); return r
        return self.req.change(f)
    def update(self, body):
        rid = body.get("id")
        def f(j):
            for r in j["requests"]:
                if r["id"] == rid:
                    if "text" in body and r["status"] in ("draft", "queued"): r["text"] = body["text"].strip()
                    if body.get("status") == "withdrawn" and r["status"] in ("draft", "queued", "failed", "done"): r["status"] = "withdrawn"
                    r["updated"] = now(); return r
            raise ValueError("no request " + str(rid))
        return self.req.change(f)
    def send(self):
        def f(j):
            rnd = max([r.get("round") or 0 for r in j["requests"]] + [0]) + 1; n = 0
            for r in j["requests"]:
                if r["status"] == "draft": r.update(status="queued", round=rnd, sent=now(), updated=now()); n += 1
            return dict(sent=n, round=rnd)
        return self.req.change(f)

    # --- mechanical jobs (beats.py), one at a time
    def run(self, ids=None):
        if not self.joblock.acquire(blocking=False): raise RuntimeError("a render is already running")
        try:
            def pick(j):
                rnd = max([r.get("round") or 0 for r in j["requests"]] + [0]) + 1; sel = []
                for r in j["requests"]:
                    if r.get("action") and r["status"] in ("draft", "queued", "failed") and (not ids or r["id"] in ids):
                        r.update(status="rendering", round=r.get("round") or rnd, updated=now()); sel.append(r)
                return sel
            sel = self.req.change(pick)
        except Exception:
            self.joblock.release(); raise
        if not sel:
            self.joblock.release(); return dict(started=0)
        threading.Thread(target=self._run, args=(sel,), daemon=True).start()
        return dict(started=len(sel), ids=[r["id"] for r in sel])
    def _cmd(self, *a):
        return [py(), "-I", BEATS] + list(a[:1]) + [self.edit] + list(a[1:]) + (["--dir", self.bdir] if self.bdir else [])
    def _exec(self, cmd, label):
        self.job.update(label=label, pct=None); start = len(self.job["lines"]); self.job["lines"].append("$ " + " ".join(os.path.basename(c) if c == BEATS else c for c in cmd[2:]))
        log = open(os.path.join(self.sd, "jobs.log"), "a"); log.write(f"\n[{now()}] {' '.join(cmd)}\n")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout:
            line = line.rstrip(); log.write(line + "\n"); log.flush()
            if not line: continue
            self.job["lines"].append(line[:300]); m = re.search(r"rendered (\d+)/(\d+)", line)
            if m: self.job["pct"] = round(100 * int(m.group(1)) / int(m.group(2)))
            if line.startswith("verify:"): self.job["pct"] = 100
        p.wait(); log.close(); return p.returncode, self.job["lines"][start + 1:]
    def _run(self, sel):
        self.job.update(running=True, ok=None, ended=None, lines=[], pct=None)
        try:
            swaps = [r for r in sel if r["action"]["type"] == "swap"]; redos = [r for r in sel if r["action"]["type"] == "redo"]
            jobs = []
            for i, r in enumerate(swaps):
                a = r["action"]; last = i == len(swaps) - 1 and not redos
                jobs.append(([r], self._cmd("sfx", str(a["beat"]), "swap", str(a["old"]), a["new"], *(["--gate"] if last else [])),
                             f"swap {os.path.basename(a.get('was') or '')} to {os.path.basename(a['new'])} in b{a['beat']:02d}",
                             f"Swapped {os.path.splitext(os.path.basename(a.get('was') or ''))[0]} to {os.path.splitext(os.path.basename(a['new']))[0]} "
                             f"in b{a['beat']:02d}: audio remixed, picture untouched"))
            if redos:
                bs = sorted({b for r in redos for b in r["action"]["beats"]})
                jobs.append((redos, self._cmd("redo", *[str(b) for b in bs]), "redo " + " ".join(f"b{b:02d}" for b in bs),
                             "Re-rendered " + " ".join(f"b{b:02d}" for b in bs)))
            allok = True
            for rs, cmd, label, done_msg in jobs:
                t0 = time.time(); rc, lines = self._exec(cmd, label)
                gate = next((l.split("GATE:")[1].strip() for l in reversed(lines) if "GATE:" in l), None)
                fr = next((re.search(r"(\d+ of \d+ frames)", l).group(1) for l in lines if re.search(r"\d+ of \d+ frames", l)), None)
                tail = done_msg + (f" ({fr})" if fr else "") + f" in {time.time() - t0:.0f}s"
                ok = rc == 0
                allok &= ok
                def f(j, rs=rs, ok=ok, gate=gate, tail=tail, rc=rc, lines=lines):
                    for r in j["requests"]:
                        if any(r["id"] == x["id"] for x in rs):
                            r.update(status="done" if ok else "failed", updated=now(), done=now() if ok else None,
                                     reply=(tail.strip() + (f" · gate {gate}" if gate else "")) if ok else f"exit {rc}: " + " | ".join(lines[-3:]))
                self.req.change(f)
            self.job.update(ok=allok)
        except Exception as e:
            self.job["lines"].append(f"error: {e}"); self.job["ok"] = False
            def f(j):
                for r in j["requests"]:
                    if r["status"] == "rendering": r.update(status="failed", reply=str(e), updated=now())
            self.req.change(f)
        finally:
            self.job.update(running=False, ended=now(), label=self.job["label"]); self.joblock.release()

    def thumb(self, ver, bid):
        """one small still of a beat, cut from the proxy on first request and cached (the long-form beat list loads them lazily)"""
        p = self.proxy.get(ver)
        if not p: return None
        b = next((x for x in self.meta()["beats"] if x["id"] == bid), None)
        if not b: return None
        d = os.path.join(self.cache, "thumbs-" + ver); os.makedirs(d, exist_ok=True); out = os.path.join(d, f"b{bid}.jpg")
        if not os.path.exists(out):
            tmp = out + f".{threading.get_ident()}.part.jpg"; t = b["t0"] + min((b["t1"] - b["t0"]) * 0.5, 1.0)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", p["mp4"], "-frames:v", "1", "-vf", "scale=256:-2", "-q:v", "5", tmp], check=True)
            os.replace(tmp, out)
        return out
    def library(self):
        out = []
        for d, fs in H.sfx_catalog().items():
            root = H.SFX_ROOTS[0] if d.startswith("lib/") else H.SFX_ROOTS[1]
            rel = d.split("/", 1)[1]
            out.append(dict(folder=d, files=[dict(name=f, path=os.path.normpath(os.path.join(root, rel, f))) for f in fs]))
        return dict(folders=out, families=self.lanes.get("families", {}))
    def audio_ok(self, p):
        rp = os.path.realpath(p)
        if not rp.lower().endswith(H.AUDIO_EXT) or not os.path.isfile(rp): return False
        roots = [os.path.realpath(r) for r in H.SFX_ROOTS]
        known = {os.path.realpath(s["abs"]) for s in self.lanes.get("sfx", [])} | {os.path.realpath(f) for v in self.lanes.get("families", {}).values() for f in v}
        return any(rp.startswith(r + os.sep) for r in roots) or rp in known


def make_handler(S):
    class Hd(BaseHTTPRequestHandler):
        server_version = "OBStudio/1"
        def log_message(self, *a): pass
        def _json(self, o, code=200):
            b = json.dumps(o).encode(); self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(b)
        def _file(self, path, ctype=None, cache=False):
            if not path or not os.path.isfile(path): return self._json(dict(error="not found"), 404)
            size = os.path.getsize(path); ctype = ctype or mimetypes.guess_type(path)[0] or "application/octet-stream"
            rng = self.headers.get("Range"); start, end = 0, size - 1
            if rng and rng.startswith("bytes="):
                a, _, b = rng[6:].split(",")[0].strip().partition("-")
                try:
                    if a == "": start = max(0, size - int(b))
                    else: start = int(a); end = min(int(b), size - 1) if b else size - 1
                except ValueError: start, end = 0, size - 1
                if start >= size or start > end:
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
                self.send_response(206); self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else: self.send_response(200)
            self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "max-age=31536000, immutable" if cache else "no-store"); self.end_headers()
            try:
                with open(path, "rb") as f:
                    f.seek(start); left = end - start + 1
                    while left > 0:
                        chunk = f.read(min(1 << 16, left))
                        if not chunk: break
                        self.wfile.write(chunk); left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError): pass
        def do_GET(self):
            u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); p = u.path
            try:
                if p in ("/", "/index.html"): return self._file(os.path.join(HERE, "index.html"), "text/html; charset=utf-8")
                if p == "/api/state": return self._json(S.state())
                if p == "/api/meta": return self._json(S.meta())
                if p == "/api/library": return self._json(S.library())
                m = re.fullmatch(r"/video/([0-9a-f]{8})\.mp4", p)
                if m: return self._file((S.proxy.get(m.group(1)) or {}).get("mp4"), "video/mp4", cache=True)
                m = re.fullmatch(r"/strip/([0-9a-f]{8})\.jpg", p)
                if m: return self._file((S.proxy.get(m.group(1)) or {}).get("strip"), "image/jpeg", cache=True)
                m = re.fullmatch(r"/thumb/([0-9a-f]{8})/(\d+)\.jpg", p)
                if m: return self._file(S.thumb(m.group(1), int(m.group(2))), "image/jpeg", cache=True)
                if p == "/audio":
                    f = (q.get("p") or [""])[0]
                    return self._file(f) if S.audio_ok(f) else self._json(dict(error="not a library sound"), 403)
                return self._json(dict(error="not found"), 404)
            except Exception as e: return self._json(dict(error=str(e)), 500)
        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            try:
                if self.path == "/api/requests": return self._json(S.add(body))
                if self.path == "/api/requests/update": return self._json(S.update(body))
                if self.path == "/api/send": return self._json(S.send())
                if self.path == "/api/run": return self._json(S.run(body.get("ids")))
                return self._json(dict(error="not found"), 404)
            except (ValueError, RuntimeError) as e: return self._json(dict(error=str(e)), 409)
            except Exception as e: return self._json(dict(error=str(e)), 500)
    return Hd


# ------------------------------------------------------------------ CLI
def beats_dir_of(edit, bdir):
    if bdir: return bdir
    A = H.load_adapter(edit, None); return A.beats_dir

def main(argv):
    if len(argv) < 3 or argv[1] in ("-h", "--help"): print(__doc__); return
    cmd, edit = argv[1], argv[2]; rest = list(argv[3:]); bdir = None; port = 8765
    if "--dir" in rest: i = rest.index("--dir"); bdir = os.path.abspath(os.path.expanduser(rest[i + 1])); del rest[i:i + 2]
    if "--port" in rest: i = rest.index("--port"); port = int(rest[i + 1]); del rest[i:i + 2]
    if cmd == "lanes":
        print("LANES_JSON " + json.dumps(cmd_lanes(edit, bdir))); return
    if cmd == "serve":
        S = Studio(edit, bdir)
        try: srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(S))
        except OSError as e: sys.exit(f"port {port} is busy ({e}); stop the other server or pass --port")
        print(f"OB Studio: {S.lanes['edit']} ({len(S.meta()['beats'])} beats) on http://localhost:{port}\n  beats folder {S.bd}\n  requests {S.req.p}", flush=True)
        try: srv.serve_forever()
        except KeyboardInterrupt: pass
        return
    bd = beats_dir_of(edit, bdir); R = Requests(bd, os.path.splitext(os.path.basename(edit))[0])
    if cmd == "requests":
        j = R.read(); rs = [r for r in j["requests"] if "--all" in rest or r.get("status") in ("queued", "working")]
        print(f"{R.p}: {len(rs)} request(s)" + ("" if "--all" in rest else " queued or in progress"))
        for r in rs:
            t = r.get("target") or {}; where = f"b{t['beat']:02d}" if t.get("beat") else "-"
            what = r.get("text") or (r.get("action") or {}).get("type", "")
            print(f"  {r['id']:>4} {r['status']:<9} {where} {t.get('kind', ''):<5} t={t.get('t', '')}  {what}" + (f"  [action {json.dumps(r['action'])}]" if r.get("action") else ""))
            if t.get("kind") == "sfx": print(f"        sound {t.get('name')} ({t.get('fam')}) at {t.get('onset')}s, {t.get('db')} dB")
        return
    if cmd == "mark":
        if len(rest) < 2 or rest[1] not in ("working", "done", "failed", "queued"): sys.exit("usage: studio.py mark <edit> <id> working|done|failed [--reply TEXT]")
        rid, st = rest[0], rest[1]; reply = rest[rest.index("--reply") + 1] if "--reply" in rest else None
        def f(j):
            rnd = max([r.get("round") or 0 for r in j["requests"]] + [0])
            for r in j["requests"]:
                if r["id"] == rid:
                    r.update(status=st, updated=now()); r["round"] = r.get("round") or rnd or 1
                    if st == "done": r["done"] = now()
                    if reply is not None: r["reply"] = reply
                    return r
            sys.exit(f"no request {rid} in {R.p}")
        r = R.change(f); print(f"{r['id']} -> {r['status']}" + (f": {r['reply']}" if r.get("reply") else "")); return
    sys.exit(f"unknown command {cmd}")

if __name__ == "__main__": main(sys.argv)
