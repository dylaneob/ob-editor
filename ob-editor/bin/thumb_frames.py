#!/opt/homebrew/bin/python3
"""Rank the frames of long 4K footage by how good they are as a thumbnail face shot.

  thumb_frames.py SOURCE.mp4 OUTDIR [--start S --end E] [--fps 2] [--top 24]
                  [--gaze RAW.json --gaze-offset SECONDS] [--min-gap 2] [--threads 2]

Writes OUTDIR/candidates.json (every scored sample, with its signals, score and reject reason) and OUTDIR/sheet.jpg (the top frames in
a grid, face-centred crops, each labelled rank, HH:MM:SS.ss and score). Then prints the ffmpeg command that grabs a chosen timestamp
from the 4K source as a full-res PNG. Timestamps are floored to 0.01 s, so pasting one into `-ss` lands on exactly that frame.
Times are in the source file's own timeline (for C4367_C4368.MP4 that is the combined time).

HOW IT SAMPLES
  Frames are decoded scaled down to 960 px wide (-threads 2, raw RGB over a pipe, nothing is written to disk while scanning).
  --mode auto (default): when the camera's keyframes are about as close as 1/fps (this camera: an I frame every 15 frames = 0.5 s),
  only keyframes are decoded (-skip_frame nokey). That is the same 2 fps but roughly 10x cheaper than decoding every frame, and I frames
  are the best-quality frame of each GOP. Otherwise every frame is decoded and one per 1/fps is kept. --mode key / fps forces either.

SIGNALS PER SAMPLE
  q      Apple Vision VNDetectFaceCaptureQualityRequest, revision 2 pinned (face_quality.swift; largest face only).
  eyes   pupil_y and eye openness. With --gaze they come from the nearest rows of the existing gaze file (the two rows either side of
         the sample, worst case of the pair, so a blink between two rows is still caught). Without it, or where the file has no usable
         row, they come from Vision landmarks on the same frame (same maths as gaze.swift). Landmarks of the frame itself are also
         used as a cross-check against a blink that fell between two gaze rows.
  pose   head pitch and yaw from Vision on the frame itself (pitch about 0.15 head up and talking, 0.35+ head bowed over the script;
         |yaw| about 0.1 facing the camera, 0.8 turned away). A bowed or turned head can still read as "pupils on the lens" because
         the lids and pupils sit the same way inside the eye, so pose is scored too.
  sharp  Laplacian variance of the face crop, divided by the 90th percentile of the same signal among frames that could be picked
         (not rejected for pose or eyes) within +-150 s, so a dim room and a bright room are each judged against themselves and a
         frontal face is not compared with profile frames.
  size   face height as a fraction of frame height.
  tags   "mouth" (mouth clearly open) and "brows" (brows raised vs this run's median). Shown on the sheet, not scored.

HARD REJECTS (score is null, reason is in candidates.json): no_face, small_face (< 10% of frame height), cropped (face touches the
frame edge), no_eyes (no pupils anywhere), eyes_shut (open < 0.13, or the frame's own landmarks say so), eyes_down (pupil_y >= 0.45),
head_down (pitch >= 0.40), turned (|yaw| >= 0.55), blur (sharp < 0.5 of the local reference: motion blur or missed focus).

SCORE (0-100) = 30 * quality + 30 * eyes + 25 * sharpness + 15 * size, each part 0..1
  quality   (q - 0.40) / (0.70 - 0.40)
  eyes      0.5 * on_lens + 0.3 * open + 0.2 * pose
              on_lens = 1 for pupil_y 0.26-0.37, falling to 0 at 0.45 (down) and 0.12 (up)
              open    = (open - 0.13) / (0.26 - 0.13)
              pose    = the lower of (0.40 - pitch) / (0.40 - 0.26) and (0.55 - |yaw|) / (0.55 - 0.25), each held to 0..1
  sharpness (sharp / local reference - 0.5) / (0.9 - 0.5)
  size      (face height - 0.10) / (0.25 - 0.10)   (full credit from a face 25% of the frame tall: plenty of pixels at 4K)
Calibrated by eye on C4367 (desk 300-360 s and the C4368 living-room pickups, 2900-2960 s): frames that looked right score 70 and up,
frames that looked wrong but got past the hard rejects (head bowed, lids half down) fall below 70.
FULL RUN of C4367 (two runs, because the desk gaze file is on combined time and the C4368 one is on C4368's own clock; measured at
8 to 10 s of wall time per footage minute with 2 threads on a busy machine, so roughly 10 minutes for the whole 63-minute file):
  nice -n 10 /opt/homebrew/bin/python3 thumb_frames.py /Volumes/OB-ARCHIVE/OB-EDITS-WORKING/C4367_C4368.MP4 OUT/desk --end 2773.2705 \\
      --gaze /Volumes/T7/OB-EDITS/C4367-edit/gaze/raw.json --min-gap 8
  nice -n 10 /opt/homebrew/bin/python3 thumb_frames.py /Volumes/OB-ARCHIVE/OB-EDITS-WORKING/C4367_C4368.MP4 OUT/c4368 --start 2773.2705 \\
      --gaze /Volumes/T7/OB-EDITS/C4367-edit/c4368/gaze_raw.json --gaze-offset 2773.2705 --min-gap 8
PICKS: best first; none within --min-gap seconds (default 2) of a better pick; nothing under --min-score (default 70), so a short
span can return fewer than --top rather than padding the sheet with weak frames. If the top 24 bunch up in a few moments, re-run
with a bigger --min-gap (10 spreads them over the video).
"""
import argparse, bisect, json, math, os, re, resource, subprocess, sys, threading, time
from collections import Counter

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG, FFPROBE = "/opt/homebrew/bin/ffmpeg", "/opt/homebrew/bin/ffprobe"
HELPER = os.path.join(HERE, "face_quality")
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

WEIGHTS = {"quality": 30, "eyes": 30, "sharp": 25, "size": 15}
Q_LO, Q_HI = 0.40, 0.70                  # Vision capture quality that maps to 0 and to 1
PY_DOWN, PY_UP = 0.45, 0.12              # pupil_y at/above PY_DOWN = looking down (reject); score reaches 0 at PY_UP (looking up)
PY_LENS_LO, PY_LENS_HI = 0.26, 0.37      # pupil_y band with full on-lens credit
OPEN_SHUT, OPEN_FULL = 0.13, 0.26        # eye height/width: below SHUT = blink (reject), FULL and up = full credit
EYE_W = (0.5, 0.3, 0.2)                  # inside the eyes part: on_lens, open, pose
PITCH_OK, PITCH_DOWN = 0.26, 0.40        # head pitch: full pose credit up to OK, none (and a reject) at DOWN
YAW_OK, YAW_TURNED = 0.25, 0.55          # head turn (|yaw|): full credit up to OK, none (and a reject) at TURNED = not facing the lens
SHARP_LO, SHARP_HI = 0.5, 0.9            # sharp / local reference that maps to 0 and to 1
MIN_SCORE = 70.0                         # default floor for picks
LIVE_OMIN_SHUT = 0.10                    # the frame's own landmarks: either eye below this = shut (reject)
OPEN_GLITCH = 0.60                       # open above this is a failed eye contour, not an eye
MIN_FACE_H, FACE_H_LO, FACE_H_HI = 0.10, 0.10, 0.25
BLUR_MIN = 0.50                          # sharp / local reference below this = blur (reject)
REF_WINDOW, REF_PCT = 150.0, 90          # sharpness reference: this percentile of the face samples within +- this many seconds
MOUTH_TAG, BROW_TAG = 0.18, 0.012        # mouth open ratio; brow gap above the run's median (fraction of face height)
GAZE_HOLE = 0.5                          # seconds; gaze rows further apart than this are treated as missing


def parse_time(s):
    parts = [float(p) for p in str(s).split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def hms(t):
    """HH:MM:SS.ss floored to 0.01 s (a label never lies after its frame, so `-ss label` finds this very frame)."""
    cs = max(0, int(math.floor(t * 100 - 1e-6)))
    h, r = divmod(cs, 360000)
    m, r = divmod(r, 6000)
    s, c = divmod(r, 100)
    return f"{h:02d}:{m:02d}:{s:02d}.{c:02d}"


def secs(t):
    return f"{max(0, int(math.floor(t * 100 - 1e-6))) / 100:.2f}"


def clip01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else float(x)


def probe(src):
    out = subprocess.check_output([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate,duration:format=duration", "-of", "json", src], text=True)
    j = json.loads(out)
    st = j["streams"][0]
    n, d = map(int, st["r_frame_rate"].split("/"))
    dur = float(st.get("duration") or j["format"]["duration"])
    return {"w": int(st["width"]), "h": int(st["height"]), "fps": n / d, "fps_frac": (n, d), "dur": dur}


def keyframe_gap(src, start):
    """Median spacing of keyframes in 20 s of the source (None if it cannot be read)."""
    try:
        out = subprocess.check_output([FFPROBE, "-v", "error", "-select_streams", "v:0", "-read_intervals", f"{start:.3f}%+20",
                                       "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", src], text=True, timeout=60)
    except Exception:
        return None
    ks = [float(l.split(",")[0]) for l in out.splitlines() if "," in l and "K" in l.split(",")[1] and l.split(",")[0] != "N/A"]
    return float(np.median(np.diff(ks))) if len(ks) >= 3 else None


class Gaze:
    """Rows [frame, t, pitch, yaw, pupil_y, pupil_x, open]; t is the gaze file's own timeline = source time - offset."""

    def __init__(self, path, offset):
        d = json.load(open(path))
        rows = sorted(d["rows"] if isinstance(d, dict) else d, key=lambda r: r[1])
        self.rows, self.offset = rows, float(offset)
        self.t = [r[1] for r in rows]

    def eyes(self, t):
        """(pupil_y, open) worst case over the two rows around source time t, or None (outside the file, a hole, or no eyes found)."""
        g = t - self.offset
        i = bisect.bisect_right(self.t, g)
        if i == 0 or i >= len(self.t):
            return None
        lo, hi = self.rows[i - 1], self.rows[i]
        if hi[1] - lo[1] > GAZE_HOLE:
            return None
        for r in (lo, hi):
            if r[4] is None or r[6] is None or not (0.03 <= r[6] <= OPEN_GLITCH):
                return None
        return max(lo[4], hi[4]), min(lo[6], hi[6])


def face_sharpness(rgb, box):
    x, y, w, h = box
    H, W = rgb.shape[:2]
    x0, x1 = int(max(0, x + 0.12 * w)), int(min(W, x + 0.88 * w))
    y0, y1 = int(max(0, y + 0.10 * h)), int(min(H, y + 0.95 * h))
    if x1 - x0 < 16 or y1 - y0 < 16:
        return None
    g = cv2.cvtColor(rgb[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_32F).var())


def make_tile(rgb, box, tw, th, mode):
    """JPEG bytes of the sheet tile: a face-centred 16:9 crop (cap to shoulders, face = 43% of the tile height), or the whole frame."""
    H, W = rgb.shape[:2]
    if mode == "frame":
        crop = rgb
    else:
        x, y, w, h = box
        ch = min(H, 2.3 * h)
        cw = ch * tw / th
        if cw > W:
            cw, ch = W, W * th / tw
        cx, cy = x + w / 2, y + h / 2 - 0.02 * ch
        x0 = min(max(0, cx - cw / 2), W - cw)
        y0 = min(max(0, cy - ch / 2), H - ch)
        crop = rgb[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
    tile = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA if crop.shape[1] >= tw else cv2.INTER_CUBIC)
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(tile, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


SHOWINFO = re.compile(r"pts_time:\s*(-?[\d.]+|nan).*?iskey:(\d)")


def scan(a, src_info, key_mode, W, H, gaze):
    """Decode, run the Vision helper, measure sharpness. Returns (samples, tiles, timing)."""
    gap = 1.0 / a.fps - 0.25 / src_info["fps"]          # a quarter frame of slack so a 0.5 s GOP is not skipped by rounding
    dur = a.end - a.start
    vf = f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{gap:.5f})',scale={W}:{H},showinfo"
    cmd = [FFMPEG, "-nostdin", "-hide_banner", "-nostats", "-loglevel", "info", "-threads", str(a.threads)]
    if key_mode:
        cmd += ["-skip_frame", "nokey"]
    cmd += ["-ss", f"{a.start:.3f}", "-t", f"{dur:.3f}", "-i", a.source, "-an", "-sn", "-dn", "-filter_threads", str(a.threads),
            "-vf", vf, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    ff = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
    fq = subprocess.Popen([HELPER, str(W), str(H)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    times, tail = [], []

    def drain():
        for raw in ff.stderr:
            line = raw.decode("utf-8", "replace")
            m = SHOWINFO.search(line)
            if m and "showinfo" in line:
                times.append((float(m.group(1)), m.group(2) == "1"))
            else:
                tail.append(line.rstrip())
                del tail[:-25]

    th = threading.Thread(target=drain, daemon=True)
    th.start()
    nbytes = W * H * 3
    samples, tiles = [], []
    t_read = t_vis = t_other = 0.0
    t_begin = last_report = time.perf_counter()
    expect = max(1, int(dur * a.fps))
    while True:
        t0 = time.perf_counter()
        buf = ff.stdout.read(nbytes)
        t1 = time.perf_counter()
        t_read += t1 - t0
        if len(buf) < nbytes:
            break
        fq.stdin.write(buf)
        fq.stdin.flush()
        line = fq.stdout.readline()
        t2 = time.perf_counter()
        t_vis += t2 - t1
        if not line:
            raise SystemExit("face_quality helper died")
        info = json.loads(line)
        rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        s = {"i": len(samples), "face": info.get("nf", 0) > 0, "nfaces": info.get("nf", 0)}
        tile = None
        if s["face"]:
            box = (info["x"], info["y"], info["w"], info["h"])
            s.update(box=[round(v, 1) for v in box], face_h=round(info["h"] / H, 4), q=info.get("q"),
                     yaw=info.get("yaw"), pitch=info.get("pitch"), live_py=info.get("py"), live_open=info.get("open"),
                     live_omin=info.get("omin"), mouth=info.get("mouth"), brow=info.get("brow"))
            sh = face_sharpness(rgb, box)
            s["sharp"] = None if sh is None else round(sh, 2)
            tile = make_tile(rgb, box, a.tile, int(round(a.tile * 9 / 16)), a.tile_mode)
        samples.append(s)
        tiles.append(tile)
        t_other += time.perf_counter() - t2
        now = time.perf_counter()
        if now - last_report > 15:
            last_report = now
            print(f"  scanned {len(samples)}/~{expect} samples, {now - t_begin:.0f} s", file=sys.stderr, flush=True)
    fq.stdin.close()
    fq.wait()
    ff.wait()
    th.join(timeout=10)
    if ff.returncode not in (0, None):
        raise SystemExit("ffmpeg failed:\n" + "\n".join(tail))
    if len(times) < len(samples):
        raise SystemExit(f"ffmpeg reported {len(times)} frame times for {len(samples)} frames")
    for s, (pt, key) in zip(samples, times):
        s["t"] = round(a.start + pt, 4)
        s["key"] = key
        s["frame"] = int(round((a.start + pt) * src_info["fps"]))
        s["ts"] = hms(s["t"])
    cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
    me = resource.getrusage(resource.RUSAGE_SELF)
    return samples, tiles, {"decode_wait_s": t_read, "vision_s": t_vis, "other_s": t_other, "wall_s": time.perf_counter() - t_begin,
                            "cpu_ffmpeg_and_vision_s": cpu.ru_utime + cpu.ru_stime, "cpu_python_s": me.ru_utime + me.ru_stime}


def eye_reading(s, gaze):
    """Decide which eye numbers to trust: gaze file first, the frame's own landmarks otherwise. Sets s['py'], s['open'], s['eyes_src']."""
    s["eyes_src"] = None
    s["py"] = s["open"] = None
    g = gaze.eyes(s["t"]) if gaze else None
    if g is not None:
        s["gz_py"], s["gz_open"] = round(g[0], 4), round(g[1], 4)
        s["py"], s["open"], s["eyes_src"] = g[0], g[1], "gaze"
    lo, lp = s.get("live_open"), s.get("live_py")
    if g is None and lo is not None and lp is not None and lo <= OPEN_GLITCH:
        s["py"], s["open"], s["eyes_src"] = lp, lo, "live"


def reject_reason(s):
    if not s["face"]:
        return "no_face"
    if s["face_h"] < MIN_FACE_H:
        return "small_face"
    x, y, w, h = s["box"]
    if x < 4 or y < 4 or x + w > s["W"] - 4 or y + h > s["H"] - 4:
        return "cropped"
    if s.get("yaw") is not None and abs(s["yaw"]) >= YAW_TURNED:
        return "turned"
    if s["py"] is None:
        return "no_eyes"
    live_shut = s.get("live_omin") is not None and s["live_omin"] < LIVE_OMIN_SHUT
    if s["open"] < OPEN_SHUT or live_shut:
        return "eyes_shut"
    if s["py"] >= PY_DOWN:
        return "eyes_down"
    if s.get("pitch") is not None and s["pitch"] >= PITCH_DOWN:
        return "head_down"
    return None


def on_lens(py):
    if py >= PY_LENS_HI:
        return clip01((PY_DOWN - py) / (PY_DOWN - PY_LENS_HI))
    if py <= PY_LENS_LO:
        return clip01((py - PY_UP) / (PY_LENS_LO - PY_UP))
    return 1.0


def score_all(samples, gaze, W, H):
    for s in samples:
        s["W"], s["H"] = W, H
        if s["face"]:
            eye_reading(s, gaze)
        s["reject"] = reject_reason(s)
    # Local sharpness reference: percentile of the sharpness of frames that could be picked (facing the lens, eyes open and on it)
    # within +- REF_WINDOW seconds. Judging a frontal face against profile frames or bowed ones would not be like for like.
    pool = [s for s in samples if s["face"] and s.get("sharp") and s["reject"] is None]
    if len(pool) < 8:
        pool = [s for s in samples if s["face"] and s.get("sharp") and s["face_h"] >= MIN_FACE_H]
    ts = np.array([s["t"] for s in pool]) if pool else np.zeros(0)
    sh = np.array([s["sharp"] for s in pool]) if pool else np.zeros(0)
    glob = float(np.percentile(sh, REF_PCT)) if len(sh) else 1.0
    for s in samples:
        s["score"] = s["sharp_rel"] = None
        if not s["face"]:
            continue
        lo, hi = np.searchsorted(ts, s["t"] - REF_WINDOW), np.searchsorted(ts, s["t"] + REF_WINDOW, "right")
        ref = float(np.percentile(sh[lo:hi], REF_PCT)) if hi - lo >= 8 else glob
        s["sharp_rel"] = round((s.get("sharp") or 0.0) / ref, 3) if ref > 0 else None
        if s["reject"] is None and (s["sharp_rel"] is None or s["sharp_rel"] < BLUR_MIN):
            s["reject"] = "blur"
        if s["py"] is None or s.get("q") is None or s["sharp_rel"] is None:
            s["reject"] = s["reject"] or "no_signal"
            continue
        pose = min(clip01((PITCH_DOWN - s["pitch"]) / (PITCH_DOWN - PITCH_OK)) if s.get("pitch") is not None else 0.5,
                   clip01((YAW_TURNED - abs(s["yaw"])) / (YAW_TURNED - YAW_OK)) if s.get("yaw") is not None else 0.5)
        parts = {"quality": clip01((s["q"] - Q_LO) / (Q_HI - Q_LO)),
                 "eyes": EYE_W[0] * on_lens(s["py"]) + EYE_W[1] * clip01((s["open"] - OPEN_SHUT) / (OPEN_FULL - OPEN_SHUT))
                         + EYE_W[2] * pose,
                 "sharp": clip01((s["sharp_rel"] - SHARP_LO) / (SHARP_HI - SHARP_LO)),
                 "size": clip01((s["face_h"] - FACE_H_LO) / (FACE_H_HI - FACE_H_LO))}
        s["parts"] = {k: round(v, 3) for k, v in parts.items()}
        raw = sum(WEIGHTS[k] * v for k, v in parts.items())
        s["raw_score"] = round(raw, 2)
        if s["reject"] is None:
            s["score"] = round(raw, 2)
    for s in samples:
        s.pop("W", None)
        s.pop("H", None)
    # tags (informational)
    ok = [s for s in samples if s["reject"] is None and s.get("brow") is not None]
    base = float(np.median([s["brow"] for s in ok])) if ok else None
    for s in samples:
        s["tags"] = []
        if s["face"] and s.get("mouth") is not None and s["mouth"] >= MOUTH_TAG:
            s["tags"].append("mouth")
        if s["face"] and base is not None and s.get("brow") is not None and s["brow"] - base >= BROW_TAG:
            s["tags"].append("brows")
    return Counter(s["reject"] for s in samples if s["reject"])


def pick(samples, top, min_gap, min_score):
    ranked = sorted((s for s in samples if s["score"] is not None and s["score"] >= min_score), key=lambda s: -s["score"])
    chosen = []
    for s in ranked:
        if all(abs(s["t"] - c["t"]) >= min_gap for c in chosen):
            chosen.append(s)
            if len(chosen) == top:
                break
    for r, s in enumerate(chosen, 1):
        s["picked"] = r
    return chosen


def make_sheet(chosen, tiles, path, cols, tile_w):
    tile_h = int(round(tile_w * 9 / 16))
    lab, pad = 46, 6
    try:
        f1, f2 = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 14)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    rows = (len(chosen) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tile_w + pad) + pad, rows * (tile_h + lab + pad) + pad), (18, 18, 16))
    d = ImageDraw.Draw(sheet)
    for k, s in enumerate(chosen):
        x, y = pad + (k % cols) * (tile_w + pad), pad + (k // cols) * (tile_h + lab + pad)
        d.text((x + 2, y + 1), f"#{s['picked']}  {s['ts']}  {s['score']:.1f}", fill=(247, 220, 58), font=f1)
        sub = f"q {s['q']:.2f}  py {s['py']:.2f}  open {s['open']:.2f}  sharp {min(s['sharp_rel'], 9.99):.2f}"
        if s["tags"]:
            sub += "  [" + " ".join(s["tags"]) + "]"
        d.text((x + 2, y + 27), sub, fill=(200, 200, 190), font=f2)
        img = cv2.imdecode(np.frombuffer(s["_tile"], np.uint8), cv2.IMREAD_COLOR)
        sheet.paste(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), (x, y + lab))
    sheet.save(path, quality=90)


def main():
    ap = argparse.ArgumentParser(description="Rank footage frames as thumbnail face shots (see the docstring at the top of this file).")
    ap.add_argument("source")
    ap.add_argument("outdir")
    ap.add_argument("--start", type=parse_time, default=0.0, help="seconds or H:MM:SS (default 0)")
    ap.add_argument("--end", type=parse_time, default=None, help="seconds or H:MM:SS (default end of file)")
    ap.add_argument("--fps", type=float, default=2.0, help="samples per second (default 2)")
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--gaze", help="gaze RAW.json (rows [frame,t,pitch,yaw,pupil_y,pupil_x,open])")
    ap.add_argument("--gaze-offset", type=float, default=0.0, help="gaze file time = source time - OFFSET (C4368 pickups: 2773.2705)")
    ap.add_argument("--min-gap", type=float, default=2.0, help="no two picks closer than this many seconds")
    ap.add_argument("--min-score", type=float, default=MIN_SCORE, help="never pick a frame scoring below this (default 70)")
    ap.add_argument("--mode", choices=["auto", "key", "fps"], default="auto")
    ap.add_argument("--width", type=int, default=960, help="decode width for scoring")
    ap.add_argument("--threads", type=int, default=0, help="ffmpeg decode threads (0 = all cores; was 2 on the 8 GB Air)")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile", type=int, default=480, help="sheet tile width in px")
    ap.add_argument("--tile-mode", choices=["face", "frame"], default="face", help="face-centred crop or the whole frame")
    a = ap.parse_args()

    if not os.path.exists(HELPER):
        sys.exit(f"missing {HELPER}; build it: swiftc -O {HERE}/face_quality.swift -o {HELPER}")
    if not os.path.exists(a.source):
        sys.exit(f"no such file: {a.source}")
    info = probe(a.source)
    a.end = min(a.end if a.end is not None else info["dur"], info["dur"])
    if a.end <= a.start:
        sys.exit("--end must be after --start")
    W = a.width - a.width % 2
    H = int(round(info["h"] * W / info["w"] / 2)) * 2
    os.makedirs(a.outdir, exist_ok=True)
    gaze = Gaze(a.gaze, a.gaze_offset) if a.gaze else None

    gop = keyframe_gap(a.source, a.start)
    key_mode = a.mode == "key" or (a.mode == "auto" and gop is not None and 0.2 <= gop <= 1.15 / a.fps)
    mode_name = "key" if key_mode else "fps"
    print(f"{os.path.basename(a.source)} {a.start:.1f}-{a.end:.1f} s | {info['w']}x{info['h']} {info['fps']:.3f} fps, keyframe gap "
          f"{gop if gop is None else round(gop, 4)} | mode {mode_name} at ~{a.fps} fps, decode {W}x{H}, threads {a.threads}"
          + (f" | gaze {os.path.basename(a.gaze)} offset {a.gaze_offset}" if gaze else " | no gaze file, using Vision landmarks"), flush=True)

    samples, tiles, tm = scan(a, info, key_mode, W, H, gaze)
    rej = score_all(samples, gaze, W, H)
    chosen = pick(samples, a.top, a.min_gap, a.min_score)
    for s in chosen:
        s["_tile"] = tiles[s["i"]]
    if chosen:
        make_sheet(chosen, tiles, os.path.join(a.outdir, "sheet.jpg"), a.cols, a.tile)
    for s in chosen:
        del s["_tile"]

    footage = a.end - a.start
    grab = f'{FFMPEG} -ss {{T}} -i "{a.source}" -frames:v 1 -an -sn -pix_fmt rgb24 "{os.path.abspath(a.outdir)}/frame_{{T}}.png"'
    meta = {"tool": "thumb_frames.py", "source": os.path.abspath(a.source), "start": a.start, "end": a.end, "fps_requested": a.fps,
            "mode": mode_name, "keyframe_gap": gop, "decode": [W, H], "gaze": a.gaze, "gaze_offset": a.gaze_offset if gaze else None,
            "min_gap": a.min_gap, "min_score": a.min_score, "weights": WEIGHTS, "eye_weights": EYE_W,
            "thresholds": {"q": [Q_LO, Q_HI], "py_down": PY_DOWN, "py_lens": [PY_LENS_LO, PY_LENS_HI], "open": [OPEN_SHUT, OPEN_FULL],
                           "pitch": [PITCH_OK, PITCH_DOWN], "sharp": [SHARP_LO, SHARP_HI],
                           "live_omin_shut": LIVE_OMIN_SHUT, "blur_min": BLUR_MIN, "min_face_h": MIN_FACE_H},
            "vision_revisions": {"capture_quality": 2, "face_rectangles": 3, "face_landmarks": 3},
            "samples": len(samples), "faces": sum(s["face"] for s in samples), "rejected": dict(rej),
            "scored": sum(s["score"] is not None for s in samples),
            "timing_s": {k: round(v, 2) for k, v in tm.items()}, "seconds_per_footage_minute": round(tm["wall_s"] / footage * 60, 2),
            "grab_command_template": grab}
    picks = [{"rank": s["picked"], "t": s["t"], "ts": s["ts"], "score": s["score"], "grab": grab.replace("{T}", secs(s["t"]))} for s in chosen]
    body = ",\n".join(json.dumps(s, separators=(",", ":")) for s in samples)
    with open(os.path.join(a.outdir, "candidates.json"), "w") as f:
        f.write('{\n"meta": ' + json.dumps(meta, indent=1) + ',\n"picks": ' + json.dumps(picks, indent=1) + ',\n"samples": [\n' + body + "\n]\n}\n")

    print(f"\n{len(samples)} samples, {meta['faces']} with a face, {meta['scored']} scored. Rejected: "
          + (", ".join(f"{k} {v}" for k, v in rej.most_common()) or "none"))
    print(f"time: {tm['wall_s']:.1f} s for {footage:.0f} s of footage = {tm['wall_s'] / footage * 60:.1f} s per footage minute "
          f"(waiting on ffmpeg {tm['decode_wait_s']:.1f} s, Vision {tm['vision_s']:.1f} s, python {tm['other_s']:.1f} s); "
          f"CPU used {tm['cpu_ffmpeg_and_vision_s'] + tm['cpu_python_s']:.1f} s = "
          f"{(tm['cpu_ffmpeg_and_vision_s'] + tm['cpu_python_s']) / footage * 60:.1f} CPU-s per footage minute")
    print(f"\ntop {len(chosen)} (min gap {a.min_gap:g} s):")
    for s in chosen:
        print(f"  #{s['picked']:<2} {s['ts']}  score {s['score']:5.1f}  q {s['q']:.2f}  pupil_y {s['py']:.2f}  open {s['open']:.2f}  "
              f"sharp {s['sharp_rel']:.2f}  face {s['face_h']:.2f}  eyes:{s['eyes_src']}" + (f"  [{' '.join(s['tags'])}]" if s["tags"] else ""))
    print(f"\nwrote {os.path.join(a.outdir, 'candidates.json')}" + (f" and {os.path.join(a.outdir, 'sheet.jpg')}" if chosen else ""))
    ex = secs(chosen[0]["t"]) if chosen else "T"
    print("\nGrab a chosen timestamp as a full-res PNG from the 4K source (T = the label, in seconds, e.g. 00:05:12.45 -> 312.45):")
    print("  " + grab.replace("{T}", ex))


if __name__ == "__main__":
    main()
