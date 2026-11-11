#!/usr/bin/env python3
"""birefnet_cut: OB's cut-out masks for the render engines, BiRefNet only (built 2026-11-11, never-again rule 9, OB 11-06 / 11-09).

The engines (tmpl.py, brand_react_render.py) used Apple's Vision person mask (bin/person_mask_dir), which leaves a halo and a blur
box beside him. This module hands them the same thing person_mask_dir gave them: one L-mode alpha PNG per input frame, same name,
same size, in an output folder. It runs matte_hq.py --dir (BiRefNet-portrait keys + optical-flow fill) and has no fallback:
if BiRefNet cannot run, the engine stops with one line that says what is missing and how to fix it.

    import birefnet_cut as BC
    BC.check()                                   # SystemExit(one line) when the venv, onnxruntime, cv2 or the model is missing
    info = BC.masks(stretches, out_dir, tmp=TD, work=WORK, only=None)
        stretch = {"src": CAMERA, "t0": seconds, "n": frames, "fps": 30000/1001, "size": (540, 960), "look": "how the pixels were made",
                   "frames": [PNG paths, in order], "names": [output names] (default: the frames' own names)}
        writes out_dir/<name> for every frame (or only the names in `only`, a list of output names, for stills)
        returns {"method": "birefnet", "model", "frames", "computed", "cached", "seconds", "s_per_frame", "cache_root", "stretches": [...]}
    BC.find_work(plan_path, plan)                # the job's WORK folder (plan "work", env OB_WORK, or the plan's own folder), never the T7
    BC.record(work, engine, plan_path, info, looks)   # appends to WORK/qc/matte.json, which qc_assets.py build reads

CACHE  <root>/<key>/k_00000.png ... + meta.json ("complete": true is written last); <root>/keys/ holds matte_hq's per-frame BiRefNet
alphas (by the PNG's bytes), so a stopped run resumes where it stopped. root = WORK/matte-cache when the job has a WORK folder, else
~/ob-scratch/matte-cache. key = sha1 of source path, its mtime, t0, frame count, frame rate, size, the pixel pipeline ("look"),
the model and this module's method version. Never under /Volumes/T7. Nothing is ever deleted here.
"""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time

BIN = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.expanduser("~/OpenMontage/.venv/bin/python")
MODEL = os.path.expanduser("~/.ob-models/birefnet-portrait/model.onnx")
MODEL_ID = "birefnet-portrait-onnx-fp32"
METHOD = "matte_hq.dir.v1"          # bump when matte_hq's --dir method changes, so old cache entries are not reused
DEFAULT_ROOT = os.path.expanduser("~/ob-scratch/matte-cache")
FPS = 30000 / 1001
_PY = []


def _die(what, fix):
    raise SystemExit(f"BiRefNet cut-out cannot run: {what}. Fix: {fix}. No fallback to Apple's person mask (never-again rule 9).")


def check():
    """The python that runs BiRefNet (this interpreter when it has onnxruntime, else the OpenMontage venv), or SystemExit(one line)."""
    if _PY: return _PY[0]
    py = sys.executable if importlib.util.find_spec("onnxruntime") and importlib.util.find_spec("cv2") else VENV_PY
    if not os.path.exists(py): _die(f"the venv python {py} is missing", "recreate ~/OpenMontage/.venv and run its pip install onnxruntime opencv-python pillow numpy")
    if not os.path.exists(MODEL): _die(f"the model {MODEL} is missing", "download onnx-community/BiRefNet-portrait-ONNX (model.onnx, fp32) to that path")
    r = subprocess.run([py, "-I", "-c", "import onnxruntime, cv2, numpy, PIL"], capture_output=True, text=True)
    if r.returncode:
        miss = (r.stderr.strip().splitlines() or ["import failed"])[-1]
        _die(f"{py} cannot import what BiRefNet needs ({miss})", f"{os.path.dirname(py)}/pip install onnxruntime opencv-python pillow numpy")
    _PY.append(py); return py


def _not_t7(p): return p and not os.path.realpath(p).startswith("/Volumes/T7")


def find_work(plan_path=None, plan=None):
    """WORK: the plan's "work", else env OB_WORK, else the plan's folder (or its parent) when it is named WORK or holds qc/. None if not found or on the T7."""
    for c in ((plan or {}).get("work"), os.environ.get("OB_WORK")):
        if c and os.path.isdir(os.path.expanduser(c)) and _not_t7(os.path.expanduser(c)): return os.path.abspath(os.path.expanduser(c))
    if plan_path:
        d = os.path.dirname(os.path.abspath(plan_path))
        for c in (d, os.path.dirname(d)):
            if (os.path.basename(c) == "WORK" or os.path.isdir(os.path.join(c, "qc"))) and _not_t7(c): return c
    return None


def cache_root(work=None):
    r = os.path.join(work, "matte-cache") if work and _not_t7(work) else DEFAULT_ROOT
    os.makedirs(os.path.join(r, "keys"), exist_ok=True); return r


def key_of(st):
    src = os.path.abspath(st["src"]); mt = os.path.getmtime(src) if os.path.exists(src) else 0
    k = [src, f"{mt:.3f}", f"{float(st['t0']):.4f}", int(st["n"]), f"{float(st.get('fps', FPS)):.5f}", list(st.get("size") or ()), st.get("look", ""), MODEL_ID, METHOD]
    return hashlib.sha1(json.dumps(k).encode()).hexdigest()[:20], k


def _complete(d):
    try: return json.load(open(os.path.join(d, "meta.json"))).get("complete") is True
    except Exception: return False


def _copy(a, b):
    tmp = f"{b}.{os.getpid()}.part"; shutil.copyfile(a, tmp); os.replace(tmp, b)


def masks(stretches, out_dir, tmp, work=None, only=None, every=3, log=None):
    """One alpha PNG per frame of each stretch into out_dir (see the module doc). tmp: the caller's scratch folder (staging lives there)."""
    log = log or (lambda m: print(m, flush=True)); py = check(); root = cache_root(work); t = time.time()
    os.makedirs(out_dir, exist_ok=True); only = set(only) if only else None
    info = {"method": "birefnet", "model": MODEL_ID, "engine_tool": "matte_hq.py --dir", "cache_root": root, "frames": 0, "computed": 0, "cached": 0, "stretches": []}
    todo = []
    for j, st in enumerate(stretches):
        names = st.get("names") or [os.path.basename(f) for f in st["frames"]]; key, kparts = key_of(st); cd = os.path.join(root, key)
        want = [k for k, nm in enumerate(names) if only is None or nm in only]
        info["stretches"].append({"src": os.path.abspath(st["src"]), "t0": round(float(st["t0"]), 4), "n": int(st["n"]), "key": key, "frames": len(want)})
        if not want: continue
        if _complete(cd):
            for k in want: _copy(os.path.join(cd, f"k_{k:05d}.png"), os.path.join(out_dir, names[k]))
            info["cached"] += len(want); info["stretches"][-1]["from"] = "cache"; continue
        todo.append((j, st, names, want, cd, kparts)); info["stretches"][-1]["from"] = "birefnet"
    if todo:
        stage = os.path.join(tmp, f"birefnet_{os.getpid()}_{int(time.time() * 1000)}"); si, so = os.path.join(stage, "in"), os.path.join(stage, "out")
        os.makedirs(si); os.makedirs(so); sel = []
        for j, st, names, want, cd, kp in todo:
            for k, f in enumerate(st["frames"]): os.symlink(os.path.abspath(f), os.path.join(si, f"{j:04d}_{k:05d}.png"))
            if only is not None: sel += [f"{j:04d}_{k:05d}.png" for k in want]
        env = dict(os.environ, OB_MATTE_KEY_CACHE=os.path.join(root, "keys"))
        cmd = [py, "-I", os.path.join(BIN, "matte_hq.py"), "--dir", si, so, "--every", str(every)] + (["--only", ",".join(sel)] if sel else [])
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if r.returncode: raise SystemExit("BiRefNet cut-out failed (matte_hq.py): " + " | ".join(r.stderr.strip().splitlines()[-3:]))
        last = (r.stdout.strip().splitlines() or [""])[-1]
        for j, st, names, want, cd, kp in todo:
            for k in want: _copy(os.path.join(so, f"{j:04d}_{k:05d}.png"), os.path.join(out_dir, names[k]))
            if only is None:   # a whole stretch: keep it, meta.json last so a half-written entry is never read as done
                os.makedirs(cd, exist_ok=True)
                for k in want: _copy(os.path.join(so, f"{j:04d}_{k:05d}.png"), os.path.join(cd, f"k_{k:05d}.png"))
                json.dump({"key": kp, "frames": len(want), "made": time.strftime("%Y-%m-%d %H:%M:%S"), "complete": True}, open(os.path.join(cd, "meta.json"), "w"))
            info["computed"] += len(want)
        log(f"  matte: BiRefNet-portrait via matte_hq.py ({py}), {last.replace('[matte_hq] ', '')}")
    info["frames"] = info["computed"] + info["cached"]; info["seconds"] = round(time.time() - t, 1)
    info["s_per_frame"] = round(info["seconds"] / info["computed"], 2) if info["computed"] else 0.0
    log(f"  matte: BiRefNet {info['frames']} frames ({info['computed']} made, {info['cached']} from cache {root}) in {info['seconds']} s")
    return info


def record(work, engine, plan_path, info, looks):
    """Append what the engine used to WORK/qc/matte.json (qc_assets.py build stamps the matching cutout rows birefnet from it)."""
    if not work or not _not_t7(work) or not plan_path: return None
    p = os.path.join(work, "qc", "matte.json"); os.makedirs(os.path.dirname(p), exist_ok=True)
    try: d = json.load(open(p))
    except Exception: d = {"version": 1, "runs": []}
    h = hashlib.sha1(open(plan_path, "rb").read()).hexdigest()
    d["runs"].append({"engine": engine, "plan": os.path.abspath(plan_path), "plan_sha1": h, "method": info["method"], "model": info["model"],
                      "looks": sorted(set(looks)), "frames": info["frames"], "computed": info["computed"], "cached": info["cached"],
                      "cache_root": info["cache_root"], "stretches": info["stretches"], "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    tmp = p + f".{os.getpid()}.part"; json.dump(d, open(tmp, "w"), indent=1); os.replace(tmp, p); return p
