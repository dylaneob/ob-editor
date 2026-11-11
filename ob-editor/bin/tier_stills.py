#!/usr/bin/env python3
"""Tier-reel framing + graded stills: per shot, find OB's face (YuNet, eyes + box), set the crop so his eyes sit
at y 548 of 1920 with his face centred in X, and write the shot's still at its mock time.

  ~/OpenMontage/.venv/bin/python tier_stills.py EDL.json PROJECT_DIR NAME LUT.png

Framing (TIER-NOTES 2026-10-16): even shots zoom 1.15 (crop 1878x3340 of the 2160x3840 frame), odd shots punch
to 1.30 (1662x2954). The face is sampled at 25/50/75% of each shot and the median is used, so a head turn on
one frame can't throw the crop. Crops are clamped to the frame and written back into the EDL rows
("zoom", "crop": [w, h, x, y], "face"), so the render cuts the same frame the stills show.
Every still is graded with the LUT and blurred below the board (y 1510+, like the reference); this-or-that has no board, so no blur.
Stills: PROJECT_DIR/assets/stills/NAME_###.jpg at the mock times in PROJECT_DIR/NAME_layout.json
(tier_cards.py --mock writes it), plus NAME_f1.jpg = frame 1 of the reel.
"""
import json, os, subprocess, sys
import numpy as np
import cv2

YUNET = os.path.expanduser("~/ob-clipper/models/face_detection_yunet_2023mar.onnx")
SW, SH = 2160, 3840                      # the camera frame after its -90 rotation
EYE_Y, ZOOM = 548, {"wide": 1.15, "punch": 1.30}
BLUR_TOP = 1510
FPS = 30000 / 1001


def even(v): return int(round(v / 2)) * 2


def source(take):
    """The camera file: T7 root, or RAW-FOOTAGE/camera/ where the T7 tidy-up of 2026-10-16 moved the older takes."""
    for p in (f"/Volumes/T7/{take}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{take}.MP4"):
        if os.path.exists(p): return p
    sys.exit(f"{take}.MP4 not found on the T7")


def frame(src, t, w=1080, h=1920):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def face(det, img):
    ok, f = det.detect(img)
    if f is None or not len(f): return None
    f = [r for r in f if r[14] >= 0.75 and (r[5] + r[7]) / 2 < 0.52 * img.shape[0]]
    if not f: return None
    f = min(f, key=lambda r: (r[5] + r[7]) / 2)             # the topmost face: OB's head is always above the dog on his lap
    return {"cx": float(f[0] + f[2] / 2) * 2, "eye_y": float((f[5] + f[7]) / 2) * 2, "score": float(f[14])}


def crop_for(fc, zoom):
    cw, ch = even(SW / zoom), even(SH / zoom)
    x = min(max(0, fc["cx"] - cw / 2), SW - cw); y = min(max(0, fc["eye_y"] - EYE_Y * ch / 1920), SH - ch)
    return [cw, ch, even(x), even(y)]


def still(src, t, crop, lut, out, blur=True):
    cw, ch, x, y = crop
    g = (f"[0:v]crop={cw}:{ch}:{x}:{y},scale=1080:1920:flags=lanczos[s];[s][1:v]haldclut=interp=tetrahedral"
         + (f",split=2[a][b];[b]crop=1080:{1920 - BLUR_TOP}:0:{BLUR_TOP},gblur=sigma=26[bl];[a][bl]overlay=0:{BLUR_TOP}" if blur else ""))
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", src, "-i", lut, "-filter_complex", g,
                    "-frames:v", "1", "-q:v", "2", out], check=True)


def main():
    edl, proj, name, lut = sys.argv[1:5]
    spec = json.load(open(edl)); rows = spec["rows"]
    lay = json.load(open(f"{proj}/{name}_layout.json"))
    src = source(spec["take"]); spec["source"] = src
    det = cv2.FaceDetectorYN.create(YUNET, "", (1080, 1920), 0.7)
    os.makedirs(f"{proj}/assets/stills", exist_ok=True)
    last = None; blur = spec["board"]["kind"] != "thisorthat"      # the blur sits under a board; this-or-that has none
    for i, r in enumerate(rows):
        a, b = r["src_in"], r["src_out"]
        fs = [f for f in (face(det, frame(src, a + (b - a) * p)) for p in (0.25, 0.5, 0.75)) if f]
        if fs:
            fc = {k: float(np.median([f[k] for f in fs])) for k in ("cx", "eye_y")}; fc["n"] = len(fs)
        else:
            fc = dict(last or {"cx": SW / 2, "eye_y": 1440.0}, n=0); print(f"  shot {i}: no face found, using the previous framing")
        last = fc
        r["zoom"] = ZOOM[r["framing"]]; r["crop"] = crop_for(fc, r["zoom"]); r["face"] = {k: round(v, 1) for k, v in fc.items()}
        t = a + (lay["mock_times"][i] - r["edit_in"])
        still(src, t, r["crop"], lut, f"{proj}/assets/stills/{name}_{i:03d}.jpg", blur)
        print(f"  shot {i:2d} {r['framing']:5s} face x {fc['cx']:6.0f} eyes {fc['eye_y']:6.0f} -> crop {r['crop']} | still @ src {t:.2f}", flush=True)
    still(src, rows[0]["src_in"] + 0.5 / FPS, rows[0]["crop"], lut, f"{proj}/assets/stills/{name}_f1.jpg", blur)
    json.dump(spec, open(edl, "w"), indent=1)
    print(f"{name}: {len(rows)} stills + frame 1 -> {proj}/assets/stills; crops written to {edl}")


if __name__ == "__main__":
    main()
