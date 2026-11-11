#!/usr/bin/env python3
"""High-quality subject matte with BiRefNet-portrait (MIT, 1024x1024 input), built 2026-11-03 for the M5 Pro Mac mini.
Replaces hyperframes' u2net_human_seg (320x320 input) for embedded-captions when OB_MATTE=birefnet (the default since 11-03).
Weights: ~/.ob-models/birefnet-portrait/model.onnx (onnx-community/BiRefNet-portrait-ONNX, fp32, 973 MB). Runs locally on CoreML.

  python3 -I matte_hq.py IN.mp4 OUT_DIR FPS        # writes OUT_DIR/f_%04d.png (RGBA, subject opaque) at FPS
  python3 -I matte_hq.py IN.png OUT.png            # one image (tests, thumbnails)
  python3 -I matte_hq.py --dir IN_DIR OUT_DIR [--only a.png,b.png] [--every 3]   # alpha per PNG, same names: BiRefNet keys + flow fill (tmpl.py "matte": "birefnet")
Engines call it through birefnet_cut.py (cache, one-line error when BiRefNet cannot run, the WORK/qc/matte.json record).
Env: OB_MATTE_KEY_CACHE (where raw BiRefNet keys are kept); OB_MATTE_SMOOTH (default 0.35): blends each alpha with the previous frame's to calm edge flicker on video.
Runs with ~/OpenMontage/.venv/bin/python (onnxruntime, numpy, PIL)."""
import os, subprocess, sys, tempfile, time
import numpy as np
from PIL import Image
import onnxruntime as ort

MODEL = os.path.expanduser("~/.ob-models/birefnet-portrait/model.onnx")
MEAN, STD = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)


def session():
    os.environ.setdefault("OB_MATTE_DEVICE", "cpu")   # 11-11: CoreML cannot run this model (MLProgram fails to parse; NeuralNetwork ~250 s/frame; the ANE compile hangs)
    so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    prov = [p for p in ("CoreMLExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
    if os.environ.get("OB_MATTE_DEVICE") == "cpu": prov = ["CPUExecutionProvider"]
    return ort.InferenceSession(MODEL, so, providers=prov)


def alpha(sess, im):
    x = (np.asarray(im.convert("RGB").resize((1024, 1024), Image.BILINEAR), np.float32) / 255.0 - MEAN) / STD
    out = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[-1]
    a = 1.0 / (1.0 + np.exp(-out[0, 0]))                                   # logits -> 0..1
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize(im.size, Image.BILINEAR), np.float32) / 255.0


def rgba(im, a):
    o = im.convert("RGBA"); o.putalpha(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))); return o


CACHE = os.environ.get("OB_MATTE_KEY_CACHE") or os.path.expanduser("~/ob-scratch/matte_cache/birefnet-portrait")   # 11-11: birefnet_cut.py points this at the job's matte cache (resumable keys)


def _key(sess_box, path):
    """raw BiRefNet alpha of one PNG, cached by the PNG's bytes (stills and renders of the same frames share it)."""
    import hashlib
    os.makedirs(CACHE, exist_ok=True); cp = os.path.join(CACHE, hashlib.sha1(open(path, "rb").read()).hexdigest() + ".png")
    if os.path.exists(cp): return np.asarray(Image.open(cp), np.float32) / 255.0
    if sess_box[0] is None: sess_box[0] = session()
    a = alpha(sess_box[0], Image.open(path)); Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(cp, compress_level=1); return a


def main_dir(src, out, only=None, every=3):
    """--dir IN_DIR OUT_DIR [--only a.png,b.png] [--every N]: an L-mode alpha PNG per input PNG (NNN_kkkk.png), same name (tmpl.py
    "matte": "birefnet", 11-11). The 11-06 method that left no ghost on a moving head (STATE-short-form 11-06): BiRefNet on every
    Nth frame of each shot plus its last frame (CPU: CoreML can't run this model), DIS optical flow carries the two nearest keys onto
    each frame between, then motion-compensated smoothing (0.35 of the previous matte, moved onto this frame by flow). A shot is
    one NNN prefix, so nothing blends across a cut. --only mattes just those frames straight from BiRefNet (stills)."""
    import cv2
    os.makedirs(out, exist_ok=True); sb = [None]; t = time.time(); K = float(os.environ.get("OB_MATTE_SMOOTH", "0.35")); DS = 2
    save = lambda f, a: Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, f), compress_level=1)
    if only:
        for f in only: save(f, _key(sb, os.path.join(src, f)))
        print(f"[matte_hq] done: {len(only)} frames (BiRefNet each) in {time.time()-t:.0f} s", flush=True); return
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    def flow(a, b):
        h, w = a.shape; f = dis.calc(cv2.resize(a, (w // DS, h // DS), interpolation=cv2.INTER_AREA), cv2.resize(b, (w // DS, h // DS), interpolation=cv2.INTER_AREA), None)
        return cv2.resize(f, (w, h), interpolation=cv2.INTER_LINEAR) * DS
    def warp(al, f):
        h, w = al.shape; xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        return cv2.remap(al, xx + f[..., 0], yy + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    files = sorted(f for f in os.listdir(src) if f.endswith(".png")); shots = {}
    for f in files: shots.setdefault(f.split("_")[0], []).append(f)
    nk = 0; done = 0
    for sg, fs in shots.items():
        n = len(fs); keys = sorted(set(list(range(0, n, every)) + [n - 1])); A = {}
        for i in keys: A[i] = _key(sb, os.path.join(src, fs[i])); nk += 1
        G = [np.asarray(Image.open(os.path.join(src, f)).convert("L"), np.uint8) for f in fs]; prev = gprev = None
        for i in range(n):
            g = G[i]
            if i in A: a = A[i]
            else:
                k1 = max(k for k in keys if k < i); k2 = min(k for k in keys if k > i); a = 0; ws = 0
                for k in (k1, k2): wk = 1.0 / abs(i - k); a = a + wk * warp(A[k], flow(g, G[k])); ws += wk
                a = np.clip(a / ws, 0, 1)
            if prev is not None and K > 0: a = (1 - K) * a + K * warp(prev, flow(g, gprev))
            prev, gprev = a, g; save(fs[i], a); done += 1
        if done and (len(shots) < 20 or int(sg) % 10 == 0): print(f"[matte_hq] shot {sg}: {done}/{len(files)} frames, {nk} keys, {time.time()-t:.0f} s", flush=True)
    print(f"[matte_hq] done: {len(files)} frames ({nk} BiRefNet keys, every {every}, flow fill) in {time.time()-t:.0f} s", flush=True)


def main():
    if sys.argv[1] == "--dir":
        a = sys.argv[4:]; only = a[a.index("--only") + 1].split(",") if "--only" in a else None
        return main_dir(sys.argv[2], sys.argv[3], only, int(a[a.index("--every") + 1]) if "--every" in a else 3)
    src = sys.argv[1]; sess = session()
    if src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        im = Image.open(src); t = time.time(); rgba(im, alpha(sess, im)).save(sys.argv[2]); print(f"[matte_hq] {time.time()-t:.2f} s"); return
    out, fps = sys.argv[2], sys.argv[3]; os.makedirs(out, exist_ok=True)
    k = float(os.environ.get("OB_MATTE_SMOOTH", "0.35"))
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-vf", f"fps={fps}", f"{td}/f_%04d.png"], check=True)
        files = sorted(f for f in os.listdir(td) if f.endswith(".png")); prev = None; t = time.time()
        for i, f in enumerate(files, 1):
            im = Image.open(os.path.join(td, f)); a = alpha(sess, im)
            if prev is not None and k > 0: a = (1 - k) * a + k * prev                # temporal smoothing against flicker
            prev = a; rgba(im, a).save(os.path.join(out, f))
            if i % 50 == 0: print(f"[matte_hq] {i}/{len(files)} frames, {(time.time()-t)/i:.2f} s/frame", flush=True)
    print(f"[matte_hq] done: {len(files)} frames in {time.time()-t:.0f} s")


if __name__ == "__main__":
    main()
