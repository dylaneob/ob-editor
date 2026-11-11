#!/usr/bin/env python3
"""Fix a typo on the TV behind OB by re-setting the slide's own letters (no new font, no AI).

Run with ~/OpenMontage/.venv/bin/python (needs cv2).

  tv_patch.py build SPEC.json OUT.npz      # median reference, text alpha, moved/copied letter blocks
  tv_patch.py still OUT.npz SRC T OUT.png  # one full patched frame (for stills / mockups)
  tv_patch.py band  OUT.npz SRC T0 T1 OUT.mov [NFRAMES]
                                           # band-only clip (ProRes) for [T0, T1] (or exactly NFRAMES
                                           # frames from T0); overlay it at rect x,y on the source
                                           # before crop/scale/LUT, decoded with the same -ss

SPEC: {"src", "tref", "rect": [x, y, w, h], "angle": deg, "region": {"top0", "bot0"[, "gx", "gdrop"]},
       "blocks": [{"u": [u0, u1], "du": shift} | {"u": [u0, u1], "scale": k, "anchor": [u, v], "to": [u, v]}]}
"region" = the line being re-set (y between top0 + x*tan(angle) and bot0 + ..., band coords; gx/gdrop
let a descender through past x=gx). A block with its own "region" copies letters from another line.
u runs along the text line, v across it (rotated by `angle`). Blocks are cut in the gaps between letters.
Every frame is tracked against the reference (tripod shake, phase correlation); the old letters are
inpainted from that frame's own pixels and the new ones laid in with ink matched to the screen's
brightness, so nothing static or boxy shows.
"""
import json, subprocess, sys
import numpy as np, cv2

FPS = 30000 / 1001


def decode(src, ss, dur, vf, w, h, nframes=0):
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{ss:.4f}", "-t", f"{dur:.4f}", "-i", src,
           # explicit BT.709 both ways, or the band drifts ~2.4 levels darker than the frame around it
           "-vf", vf + ",scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24"] \
        + (["-frames:v", str(nframes)] if nframes else []) + ["-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n: break
            yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    finally:
        p.stdout.close(); p.wait()


def lum(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def build(spec_path, out):
    sp = json.load(open(spec_path))
    X, Y, W, H = sp["rect"]; th = np.radians(sp["angle"]); c, s = np.cos(th), np.sin(th)
    fr = list(decode(sp["src"], sp["tref"] - 0.4, 0.8, f"crop={W}:{H}:{X}:{Y}", W, H))
    ref = np.median(np.stack(fr), 0).astype(np.float32)
    L = lum(ref)
    bgL = cv2.GaussianBlur(cv2.morphologyEx(L, cv2.MORPH_CLOSE, np.ones((61, 61), np.uint8)), (0, 0), 8)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    def region(rg):
        top = rg["top0"] + np.tan(th) * xx
        bot = rg["bot0"] + np.tan(th) * xx + np.where(xx >= rg.get("gx", 1e9), rg.get("gdrop", 0), 0)
        return (yy > top) & (yy < bot)
    reg = region(sp["region"])
    d = (bgL - L) * reg
    inkL = float(np.median(L[d > 0.6 * d.max()]))
    a_all = np.clip((bgL - L) / np.maximum(bgL - inkL, 1), 0, 1)
    near = cv2.dilate((a_all > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    a_all = a_all * near; a_all[a_all < 0.05] = 0            # letters + their soft edges, not screen texture
    a_old = a_all * reg                                       # the line being re-set
    ink = np.median(ref[a_old > 0.97], 0)
    u = xx * c + yy * s
    a_new = np.zeros_like(a_old)
    for b in sp["blocks"]:
        src_a = a_all * region(b["region"]) if "region" in b else a_old   # copy letters from another line
        m = src_a * ((u >= b["u"][0]) & (u < b["u"][1]))
        if "du" in b:
            k, tx, ty = 1.0, b["du"] * c, b["du"] * s
        else:
            k = b["scale"]; (ua, va), (ub, vb) = b["anchor"], b["to"]
            du, dv = ub - k * ua, vb - k * va
            tx, ty = du * c - dv * s, du * s + dv * c
        a_new += cv2.warpAffine(m, np.float32([[k, 0, tx], [0, k, ty]]), (W, H), flags=cv2.INTER_CUBIC)
    a_new = np.clip(a_new, 0, 1); a_new[a_new < 0.02] = 0
    hole = cv2.dilate(((a_old > 0.03) * 255).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    near = cv2.dilate((((a_old > 0.02) | (a_new > 0.02)) * 255).astype(np.uint8), np.ones((31, 31), np.uint8))
    bright = (L > 205) & (near == 0)                          # screen white only, not the wall
    np.savez_compressed(out, rect=np.array([X, Y, W, H]), ref=ref, hole=hole, a_new=a_new, a_old=a_old,
                        ink=ink, bright=bright, tref=sp["tref"])
    print(f"built {out}: ink {ink.round(1)}  old px {(a_old > .5).sum()}  new px {(a_new > .5).sum()}")


class Patcher:
    def __init__(self, path):
        z = np.load(path)
        self.rect = [int(v) for v in z["rect"]]; self.ref = z["ref"]; self.hole = z["hole"]
        self.a_new = z["a_new"]; self.ink = z["ink"]; self.bright = z["bright"]
        self.refg = lum(self.ref).astype(np.float32)
        H, W = self.refg.shape
        self.win = cv2.createHanningWindow((W, H), cv2.CV_32F)

    def gain_map(self, fa):
        """Smooth per-channel frame/ref ratio over the screen white (TV backlight and camera exposure drift,
        including local dimming), in reference coordinates."""
        H, W = self.refg.shape; sw, sh_ = W // 8, H // 8
        w = (self.bright & (lum(fa) > 205)).astype(np.float32)
        ratio = fa / np.maximum(self.ref, 1)
        num = cv2.GaussianBlur(cv2.resize(ratio * w[..., None], (sw, sh_), interpolation=cv2.INTER_AREA), (0, 0), 6)
        den = cv2.GaussianBlur(cv2.resize(w, (sw, sh_), interpolation=cv2.INTER_AREA), (0, 0), 6)
        g = num / np.maximum(den, 1e-4)[..., None]
        g[den < 1e-3] = (ratio * w[..., None]).sum((0, 1)) / max(w.sum(), 1)
        return cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)

    def __call__(self, band):
        """Erase the old letters from this frame's own pixels (inpaint), then lay the new ones in,
        both riding the tracked shake; ink brightness follows the screen."""
        f = band.astype(np.float32); H, W = self.refg.shape
        (dx, dy), resp = cv2.phaseCorrelate(self.refg, lum(f).astype(np.float32), self.win)
        T = np.float32([[1, 0, dx], [0, 1, dy]]); Ti = np.float32([[1, 0, -dx], [0, 1, -dy]])
        sh = lambda a, fl=cv2.INTER_CUBIC: cv2.warpAffine(a, T, (W, H), flags=fl, borderMode=cv2.BORDER_REPLICATE)
        fa = cv2.warpAffine(f, Ti, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        G = self.gain_map(fa)
        clean = cv2.inpaint(np.ascontiguousarray(band), sh(self.hole, cv2.INTER_NEAREST), 5, cv2.INPAINT_TELEA).astype(np.float32)
        A = np.clip(sh(self.a_new), 0, 1)[..., None]
        out = clean * (1 - A) + sh(self.ink * G) * A
        return np.clip(out + 0.5, 0, 255).astype(np.uint8), (dx, dy, resp, G[self.bright].mean(0))


def still(npz, src, t, out):
    P = Patcher(npz); X, Y, W, H = P.rect
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                            "-of", "json", src], capture_output=True, text=True).stdout
    st = json.loads(probe)["streams"][0]; w, h = st["width"], st["height"]
    if any(abs(sd.get("rotation", 0)) == 90 for sd in st.get("side_data_list", [])): w, h = h, w
    fr = next(decode(src, t, 0.5, "null", w, h, 1)).copy()
    fr[Y:Y + H, X:X + W], info = P(fr[Y:Y + H, X:X + W])
    cv2.imwrite(out, cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
    print(f"still {t}s shift {info[0]:.2f},{info[1]:.2f} resp {info[2]:.2f} gain {np.round(info[3], 3)} -> {out}")


def band(npz, src, t0, t1, out, nframes=0):
    P = Patcher(npz); X, Y, W, H = P.rect
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", "30000/1001", "-i", "-",
                            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv444p10le", "-c:v", "prores_ks", "-profile:v", "4",
                            "-pix_fmt", "yuv444p10le", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-color_range", "tv", out], stdin=subprocess.PIPE)
    n, worst = 0, 9
    for fr in decode(src, t0, t1 - t0, f"crop={W}:{H}:{X}:{Y}", W, H, nframes):
        o, info = P(fr); enc.stdin.write(o.tobytes()); n += 1; worst = min(worst, info[2])
    enc.stdin.close(); enc.wait()
    print(f"band {out}: {n} frames, weakest track response {worst:.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build": build(sys.argv[2], sys.argv[3])
    elif cmd == "still": still(sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5])
    elif cmd == "band": band(sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), sys.argv[6], int(sys.argv[7]) if len(sys.argv) > 7 else 0)
