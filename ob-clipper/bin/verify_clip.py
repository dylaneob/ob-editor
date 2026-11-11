#!/usr/bin/env python3
"""
verify_clip.py — render QA harness for finished 9:16 Reels.

Stop validating clips by eyeballing one frame. Given a finished clip mp4, this
runs a battery of automated checks and prints a readable report ending in a
single PASS / FAIL with a defect list. It mirrors what render_clip.py is
supposed to produce (1080x1920, -14 LUFS, face-centered crop, captions).

Checks:
  1. CONTAINER  — dimensions are exactly 1080x1920 and there is BOTH a video
                  and an audio stream (ffprobe).
  2. LOUDNESS   — integrated loudness near -14 LUFS (ffmpeg loudnorm
                  print_format=json analysis); reports measured LUFS + true peak.
  3. SUBJECT    — sample ~12 frames across the duration, cv2 Haar face detection;
                  reports fraction of sampled frames with a detectable face and
                  whether the face x stays roughly centered (crop quality /
                  no cut-off head).
  4. CAPTIONS   — sample frames, detect bright text-like pixels in the lower
                  third (rough proxy that karaoke captions are rendering).
  5. DURATION   — matches --expect-dur S (if passed), within tolerance.

Usage:
  python3 bin/verify_clip.py <clip.mp4> [--expect-dur S]

Pure python + cv2 + ffmpeg/ffprobe. Exit code 0 on PASS, 1 on FAIL.
"""
import os
import sys
import json
import argparse
import subprocess

import cv2
import numpy as np

# ---- expected render targets (kept in sync with render_clip.py) ------------
EXPECT_W, EXPECT_H = 1080, 1920   # vertical default; --aspect horizontal swaps to 1920x1080
TARGET_LUFS = -14.0
LUFS_TOL = 2.0            # |measured - target| must be <= this to pass
TRUE_PEAK_MAX = -0.5     # dBTP ceiling; loudnorm aims for TP=-1
N_SAMPLE_FRAMES = 12
FACE_FRAC_MIN = 0.40     # >= this fraction of sampled frames must show a face
CENTER_TOL_FRAC = 0.28   # median face-center x within +/- this*W of frame center
CAPTION_FRAC_MIN = 0.25  # >= this fraction of frames must show lower-third text
DUR_TOL = 0.75           # seconds of slack for --expect-dur


# ---- tiny helpers ----------------------------------------------------------
class C:
    """ANSI colors, auto-disabled when stdout is not a tty."""
    _on = sys.stdout.isatty()
    G = "\033[32m" if _on else ""
    R = "\033[31m" if _on else ""
    Y = "\033[33m" if _on else ""
    B = "\033[1m" if _on else ""
    X = "\033[0m" if _on else ""


def mark(ok):
    return f"{C.G}PASS{C.X}" if ok else f"{C.R}FAIL{C.X}"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


# ---- 1. container: dimensions + stream presence ----------------------------
def check_container(path, defects):
    print(f"{C.B}[1] CONTAINER{C.X}")
    r = run(["ffprobe", "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", path])
    if r.returncode != 0:
        print(f"    {mark(False)} ffprobe could not read the file")
        defects.append("container: ffprobe failed to read the file (corrupt / not a video)")
        return None
    try:
        info = json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"    {mark(False)} ffprobe returned unparseable output")
        defects.append("container: ffprobe returned unparseable JSON")
        return None

    streams = info.get("streams", [])
    vstreams = [s for s in streams if s.get("codec_type") == "video"]
    astreams = [s for s in streams if s.get("codec_type") == "audio"]

    has_v = len(vstreams) > 0
    has_a = len(astreams) > 0
    print(f"    {mark(has_v)} video stream present"
          + (f" ({vstreams[0].get('codec_name','?')})" if has_v else ""))
    print(f"    {mark(has_a)} audio stream present"
          + (f" ({astreams[0].get('codec_name','?')})" if has_a else ""))
    if not has_v:
        defects.append("container: no video stream")
    if not has_a:
        defects.append("container: no audio stream (clip is silent / mux failed)")

    w = h = None
    if has_v:
        w = int(vstreams[0].get("width", 0))
        h = int(vstreams[0].get("height", 0))
        dim_ok = (w == EXPECT_W and h == EXPECT_H)
        print(f"    {mark(dim_ok)} dimensions {w}x{h} "
              f"(expected {EXPECT_W}x{EXPECT_H})")
        if not dim_ok:
            defects.append(
                f"container: dimensions {w}x{h}, expected {EXPECT_W}x{EXPECT_H}")

    dur = None
    try:
        dur = float(info.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        pass
    if dur is not None:
        print(f"    info: duration {dur:.2f}s")
    print()
    return {"width": w, "height": h, "duration": dur,
            "has_video": has_v, "has_audio": has_a}


# ---- 2. loudness: integrated LUFS + true peak ------------------------------
def check_loudness(path, has_audio, defects):
    print(f"{C.B}[2] LOUDNESS{C.X}")
    if not has_audio:
        print(f"    {mark(False)} no audio stream to measure")
        defects.append("loudness: no audio stream to measure")
        print()
        return None

    # loudnorm in analysis mode prints a JSON blob on stderr.
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
             "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
             "-f", "null", "-"])
    blob = _extract_json(r.stderr)
    if blob is None:
        print(f"    {mark(False)} loudnorm analysis produced no JSON")
        defects.append("loudness: loudnorm analysis failed (no JSON output)")
        print()
        return None

    def _num(key):
        try:
            return float(blob.get(key))
        except (TypeError, ValueError):
            return None

    lufs = _num("input_i")
    tp = _num("input_tp")
    lra = _num("input_lra")
    thresh = _num("input_thresh")

    # A near-silent track reports a sentinel like -70/-inf; treat as a defect.
    if lufs is None or lufs <= -60.0:
        print(f"    {mark(False)} integrated loudness "
              f"{'unmeasurable' if lufs is None else f'{lufs:.1f} LUFS'} "
              f"(track is effectively silent)")
        defects.append("loudness: audio is effectively silent (<= -60 LUFS)")
        print()
        return {"lufs": lufs, "tp": tp}

    lufs_ok = abs(lufs - TARGET_LUFS) <= LUFS_TOL
    print(f"    {mark(lufs_ok)} integrated loudness {lufs:.1f} LUFS "
          f"(target {TARGET_LUFS:.0f} +/- {LUFS_TOL:.0f})")
    if not lufs_ok:
        defects.append(
            f"loudness: {lufs:.1f} LUFS, target {TARGET_LUFS:.0f} +/- {LUFS_TOL:.0f}")

    if tp is not None:
        tp_ok = tp <= TRUE_PEAK_MAX
        print(f"    {mark(tp_ok)} true peak {tp:.1f} dBTP "
              f"(ceiling {TRUE_PEAK_MAX:.1f})")
        if not tp_ok:
            defects.append(
                f"loudness: true peak {tp:.1f} dBTP exceeds {TRUE_PEAK_MAX:.1f} (clipping risk)")
    else:
        print(f"    {mark(False)} true peak unmeasurable")

    if lra is not None:
        print(f"    info: loudness range {lra:.1f} LU"
              + (f", gating threshold {thresh:.1f} LUFS" if thresh is not None else ""))
    print()
    return {"lufs": lufs, "tp": tp, "lra": lra}


def _extract_json(text):
    """Pull the last {...} JSON object out of ffmpeg stderr."""
    end = text.rfind("}")
    if end == -1:
        return None
    depth = 0
    start = None
    for i in range(end, -1, -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                start = i
                break
    if start is None:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# ---- shared frame sampler --------------------------------------------------
def sample_frames(path, n):
    """Return up to n (BGR) frames evenly spaced across the clip."""
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total <= 0:
        # fall back to sequential reads if frame count is unknown
        while len(frames) < n:
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(fr)
        cap.release()
        return frames
    # avoid the very first/last frame (often black fade)
    idxs = np.linspace(total * 0.04, total * 0.96, n).astype(int)
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, fr = cap.read()
        if ok:
            frames.append(fr)
    cap.release()
    return frames


# ---- 3. subject-in-frame: face detection + centering -----------------------
_YUNET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                           "face_detection_yunet_2023mar.onnx")


def _detect_faces(gray_or_bgr):
    """YuNet when available (handles glasses/angles/profiles that blind the
    frontal Haar cascade and caused false subject-off-frame FAILs on correctly
    framed clips); Haar fallback."""
    import cv2 as _cv2
    if os.path.exists(_YUNET_PATH):
        try:
            img = gray_or_bgr if gray_or_bgr.ndim == 3 else _cv2.cvtColor(gray_or_bgr, _cv2.COLOR_GRAY2BGR)
            h, w = img.shape[:2]
            det = _cv2.FaceDetectorYN_create(_YUNET_PATH, "", (w, h), 0.6)
            det.setInputSize((w, h))
            _, faces = det.detect(img)
            if faces is None:
                return []
            return [(int(f[0]), int(f[1]), int(f[2]), int(f[3])) for f in faces]
        except Exception:
            pass
    casc = _cv2.CascadeClassifier(_cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    g = gray_or_bgr if gray_or_bgr.ndim == 2 else _cv2.cvtColor(gray_or_bgr, _cv2.COLOR_BGR2GRAY)
    return list(casc.detectMultiScale(g, 1.1, 5, minSize=(120, 120)))


def check_subject(frames, width, defects):
    print(f"{C.B}[3] SUBJECT-IN-FRAME{C.X}")
    if not frames:
        print(f"    {mark(False)} could not read any frames")
        defects.append("subject: no frames could be read for face detection")
        print()
        return None

    w = width or (frames[0].shape[1])
    centers = []
    hits = 0
    for fr in frames:
        faces = _detect_faces(fr)
        if len(faces):
            hits += 1
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            centers.append(fx + fw / 2.0)

    frac = hits / len(frames)
    frac_ok = frac >= FACE_FRAC_MIN
    print(f"    {mark(frac_ok)} face detected in {hits}/{len(frames)} "
          f"sampled frames ({frac*100:.0f}%, need >= {FACE_FRAC_MIN*100:.0f}%)")
    if not frac_ok:
        defects.append(
            f"subject: face in only {frac*100:.0f}% of frames "
            f"(need >= {FACE_FRAC_MIN*100:.0f}%) — subject may be off-frame")

    center_ok = True
    if centers:
        med = float(np.median(centers))
        offset = med - w / 2.0
        offset_frac = abs(offset) / w
        center_ok = offset_frac <= CENTER_TOL_FRAC
        side = "left" if offset < 0 else "right"
        print(f"    {mark(center_ok)} median face-center x {med:.0f}px "
              f"({offset_frac*100:.0f}% off-center to the {side}; "
              f"tol {CENTER_TOL_FRAC*100:.0f}%)")
        if not center_ok:
            defects.append(
                f"subject: face sits {offset_frac*100:.0f}% off-center to the {side} "
                f"— head may be cropped / crop miscentered")
    else:
        print(f"    {C.Y}skip{C.X} centering (no faces to locate)")
    print()
    return {"face_frac": frac, "center_ok": center_ok}


# ---- 4. caption presence: bright text pixels in lower third ----------------
def check_captions(frames, defects):
    print(f"{C.B}[4] CAPTION PRESENCE{C.X}")
    if not frames:
        print(f"    {mark(False)} could not read any frames")
        defects.append("captions: no frames could be read")
        print()
        return None

    caption_hits = 0
    for fr in frames:
        h, w = fr.shape[:2]
        # captions render around 70% height; scan the lower third.
        band = fr[int(h * 0.60):int(h * 0.95), :]
        if _has_text_like_pixels(band):
            caption_hits += 1

    frac = caption_hits / len(frames)
    frac_ok = frac >= CAPTION_FRAC_MIN
    print(f"    {mark(frac_ok)} lower-third text detected in "
          f"{caption_hits}/{len(frames)} frames "
          f"({frac*100:.0f}%, need >= {CAPTION_FRAC_MIN*100:.0f}%)")
    if not frac_ok:
        defects.append(
            f"captions: text detected in only {frac*100:.0f}% of frames "
            f"(need >= {CAPTION_FRAC_MIN*100:.0f}%) — captions may not be rendering")
    print()
    return {"caption_frac": frac}


def _has_text_like_pixels(band):
    """Heuristic: karaoke captions are bright (white/yellow) glyphs with dark
    stroke, giving a small-but-nonzero cluster of very bright pixels plus high
    local contrast. We require both to avoid firing on a plain bright frame."""
    if band.size == 0:
        return False
    b, gch, r = band[:, :, 0].astype(np.int16), band[:, :, 1].astype(np.int16), band[:, :, 2].astype(np.int16)
    # white text: all channels high.  yellow text: R & G high, B low.
    white = (b > 200) & (gch > 200) & (r > 200)
    yellow = (r > 190) & (gch > 170) & (b < 130)
    bright = white | yellow
    frac_bright = bright.mean()
    # captions occupy a modest slice of the band: enough to matter, not a
    # fully-blown-out frame.
    if not (0.004 <= frac_bright <= 0.45):
        return False
    # require dark stroke nearby: the band should also contain dark pixels,
    # so contrast (std of luma) is high where text lives.
    luma = (0.114 * b + 0.587 * gch + 0.299 * r)
    return float(luma.std()) > 28.0


# ---- 5. duration match -----------------------------------------------------
def check_duration(dur, expect, defects):
    if expect is None:
        return None
    print(f"{C.B}[5] DURATION{C.X}")
    if dur is None:
        print(f"    {mark(False)} could not read duration")
        defects.append("duration: could not read clip duration")
        print()
        return None
    ok = abs(dur - expect) <= DUR_TOL
    print(f"    {mark(ok)} duration {dur:.2f}s "
          f"(expected {expect:.2f}s +/- {DUR_TOL:.2f})")
    if not ok:
        defects.append(
            f"duration: {dur:.2f}s, expected {expect:.2f}s +/- {DUR_TOL:.2f}")
    print()
    return ok


def check_opening_words(path, expect_open, defects):
    """TIME-DIMENSION check: whisper the first ~2.5s and fuzzy-compare against the
    words the clip is supposed to OPEN on. Catches start-bleed (the previous
    sentence's tail leaking in because auto-sub timestamps skew early) — a defect
    no still-frame or aggregate check can see. Fuzzy 4-char-stem matching survives
    base-model mishears ('Tanked' -> 'Tank to')."""
    if not expect_open:
        return None
    print(f"{C.B}[6] OPENING WORDS{C.X}")
    model = os.path.expanduser("~/.whisper-models/ggml-base.en.bin")
    import tempfile, json as _json, re as _re
    tmp = tempfile.mkdtemp(prefix="vclip_")
    wav = os.path.join(tmp, "head.wav")
    # 5s head, not 2.5: whisper-base drops abrupt first words on very short
    # snippets (a correct clip opening on 'Tanked my energy' was heard from
    # 'and hormones', a false FAIL). Longer context transcribes the true head.
    run(["ffmpeg", "-y", "-t", "5", "-i", path, "-vn", "-ar", "16000", "-ac", "1", wav])
    run(["whisper-cli", "-m", model, "-f", wav, "-nt", "-np", "-oj", "-of", wav[:-4]])
    try:
        heard_txt = " ".join(s["text"].strip() for s in
                             _json.load(open(wav[:-4] + ".json"))["transcription"]).strip()
    except Exception:
        print(f"    {mark(False)} could not transcribe clip head")
        defects.append("opening: transcription failed")
        print()
        return False

    def toks(s):
        # explode hyphens: '65-year-old' must match whisper's '65 year old'
        # (the unexploded form silently failed a correctly-cut clip)
        parts = (p for w in s.split() for p in w.split("-"))
        return [t for t in (_re.sub(r"[^a-z0-9']", "", p.lower()) for p in parts) if t]

    exp, heard = toks(expect_open)[:4], toks(heard_txt)
    if not exp:
        print(f"    {mark(True)} nothing to check")
        print()
        return True
    # the expected SEQUENCE must begin within the first 2 heard tokens — anchoring
    # only the first token is trivially fooled by common words ("I" matched the
    # bleed "...Because I just wanted..." in testing). Fuzzy per-token, 1 miss
    # allowed for sequences of >=3 tokens.
    def m(a, b):
        return a == b or (len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4])

    def seq_at(i):
        window = heard[i:i + len(exp)]
        if len(window) < len(exp):
            return False
        miss = sum(0 if m(h, e) else 1 for h, e in zip(window, exp))
        return miss <= (1 if len(exp) >= 3 else 0)
    pos = next((i for i in range(len(heard)) if seq_at(i)), None)
    ok = pos is not None and pos <= 1
    print(f"    {mark(ok)} expected open: {' '.join(exp)!r}")
    print(f"    {'   ' if ok else '   '} actually heard: {heard_txt[:70]!r}")
    if not ok:
        defects.append(f"opening: clip does not open on expected words "
                       f"(heard {heard_txt[:60]!r}) — start-bleed or wrong cut")
    print()
    return ok


# ---- driver ----------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Render QA harness for finished 9:16 clips "
                    "(dimensions, loudness, subject-in-frame, captions, duration).")
    ap.add_argument("clip", help="path to the finished clip mp4")
    ap.add_argument("--expect-dur", type=float, default=None,
                    help="expected duration in seconds; checked within "
                         f"+/- {DUR_TOL}s")
    ap.add_argument("--expect-open", default=None,
                    help="the words the clip should OPEN on; whispers the first "
                         "2.5s and fails on start-bleed (previous sentence leaking in)")
    ap.add_argument("--aspect", default="vertical", choices=["vertical", "horizontal"],
                    help="'vertical' (default) expects 1080x1920; 'horizontal' expects "
                         "1920x1080 (full-frame, no-crop render). The subject-in-frame "
                         "face check still runs (YuNet handles either orientation).")
    a = ap.parse_args()

    if not os.path.isfile(a.clip):
        print(f"{C.R}error:{C.X} no such file: {a.clip}", file=sys.stderr)
        raise SystemExit(2)

    global EXPECT_W, EXPECT_H
    if a.aspect == "horizontal":
        EXPECT_W, EXPECT_H = 1920, 1080

    print(f"{C.B}=== verify_clip: {os.path.basename(a.clip)} ==={C.X}\n")

    defects = []

    cont = check_container(a.clip, defects) or {}
    check_loudness(a.clip, cont.get("has_audio", False), defects)

    # frames are shared by the subject + caption checks (sample once).
    frames = sample_frames(a.clip, N_SAMPLE_FRAMES)
    check_subject(frames, cont.get("width"), defects)
    check_captions(frames, defects)
    check_duration(cont.get("duration"), a.expect_dur, defects)
    check_opening_words(a.clip, a.expect_open, defects)

    # ---- verdict ----
    print(f"{C.B}=== VERDICT ==={C.X}")
    if defects:
        print(f"{C.R}{C.B}FAIL{C.X} — {len(defects)} defect(s):")
        for d in defects:
            print(f"  {C.R}x{C.X} {d}")
        raise SystemExit(1)
    print(f"{C.G}{C.B}PASS{C.X} — all checks green")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
