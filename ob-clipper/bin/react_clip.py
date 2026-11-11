#!/usr/bin/env python3
"""
react_clip.py — REACT-MODE renderer for reaction episodes that alternate
between OB on camera ("you") and the footage he's reacting to ("content").

A blind 9:16 face-crop (render_clip.py's default path) is correct for "you"
segments but ruins "content" segments — it slices the reacted-to footage down
to a random vertical sliver. This renderer classifies the cut into "you" /
"content" runs first, then renders each run with the layout that fits it:

  "you"     -> render_clip's face-tracked 9:16 punch-in (track_center_x).
  "content" -> full 16:9 frame letterboxed into the 1080x1920 canvas (scaled
               to 1080 wide, centered at ~38% canvas height), background
               filled with a heavily blurred+darkened copy of the same frame
               (same aesthetic as cover_source_captions). Headline stays on
               top; karaoke captions still sit at ~0.70 canvas height.

Everything else — transcription, phrase grouping, boundary refinement, the
face-tracking trajectory itself, the cover-source-captions band, the caption
drawing, and the final -14 LUFS mux — is IMPORTED from render_clip.py, not
duplicated.

Pipeline (mirrors render_clip.py's 5 steps, same flags):
  1. cut the [start,end] segment from the source (with optional boundary
     refinement via --expect-first/--expect-last, same as render_clip.py)
  2. whisper-cli word-level timestamps on the segment
  3. LAYOUT CLASSIFIER: sample frames every ~0.4s, Haar face-detect, classify
     each sample "you" (face height >= 18% of frame height) or "content"
     (no qualifying face); median-smooth over a ~1.5s window; absorb any run
     shorter than 1.2s into its neighbor. Then face-track ONLY across "you"
     runs for the punch-in trajectory.
  4. per-frame: render per its run's state (face-tracked punch-in for "you",
     letterboxed full-frame + blurred backdrop for "content") -> headline ->
     karaoke caption
  5. ffmpeg: mux full-quality audio, loudnorm -14 LUFS, x264 crf18, faststart

Usage:
  python3 react_clip.py --video V.mp4 --start 1.2 --end 16.4 --out reel.mp4 \
      [--headline "ON-SCREEN HOOK"] [--model base|medium] [--no-captions] \
      [--cover-source-captions] [--expect-first "..."] [--expect-last "..."] \
      [--debug-states] [--classify-only]
"""
import os
import sys
import subprocess
import argparse
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

# reuse, don't duplicate — same directory as render_clip.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_clip import (
    W_OUT, H_OUT, MODELS, FONTS, YELLOW, WHITE, STROKE,
    sh, font, transcribe_words, group_phrases, refine_bounds, _find_seq,
    track_center_x, crop_center_x, cover_source_captions, draw_caption, _wrap,
)

# ---- layout classifier tunables ---------------------------------------------
SAMPLE_STEP_S = 0.4          # sample cadence for the you/content classifier
FACE_HEIGHT_FRAC_YOU = 0.18  # face height >= 18% of frame height -> "you"
SMOOTH_WINDOW_S = 1.5        # median-filter window over the sampled state seq
MIN_RUN_S = 1.2              # "you" runs shorter than this get absorbed into a neighbor
# "content" runs need a much longer floor: real reacted-clip cutaways hold for
# several seconds, while a 2-3s face-detection dropout (subject turns away, hand
# over face, wide shot) is almost always still the creator — proven on real
# footage where every short "content" blip was actually him. Better to miss a
# very short cutaway than to jarringly zoom out mid-sentence on a false positive.
MIN_CONTENT_RUN_S = 3.5

# ---- content-layout geometry -------------------------------------------------
CONTENT_W = 1080
CONTENT_H = int(round(CONTENT_W * 9 / 16))       # 608
CONTENT_CENTER_Y_FRAC = 0.38                      # center of the 16:9 inset, as frac of H_OUT
CONTENT_BLUR_RADIUS = 60
CONTENT_DARKEN = 0.40


def classify_states(clip_mp4, debug=False):
    """Sample the clip every ~SAMPLE_STEP_S seconds, Haar-detect the largest
    face per sample, and classify each sample 'you' (face height fraction >=
    FACE_HEIGHT_FRAC_YOU) or 'content' (no qualifying face). Returns:

      runs: list of (state, start_s, end_s) covering [0, duration] contiguously
      fps, n_frames: for converting seconds <-> frame indices at render time

    Smoothing: median-filter the per-sample state sequence over a
    ~SMOOTH_WINDOW_S window (odd-sized), then merge the smoothed sequence into
    runs and absorb any run shorter than MIN_RUN_S into its longer neighbor
    (hand-over-face reaction beats briefly lose the face — this is exactly
    what the smoothing + minimum run length is for).
    """
    cap = cv2.VideoCapture(clip_mp4)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    dur = n / fps if fps else 0.0

    step_frames = max(1, int(round(fps * SAMPLE_STEP_S)))
    sample_idx, sample_state = [], []
    for i in range(0, max(n, 1), step_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = casc.detectMultiScale(g, 1.1, 5, minSize=(80, 80))
        state = "content"
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            if h >= frame_h * FACE_HEIGHT_FRAC_YOU:
                state = "you"
        sample_idx.append(i)
        sample_state.append(state)
    cap.release()

    if not sample_idx:
        return [("you", 0.0, dur)], fps, n

    # median-filter the sampled state sequence over a ~SMOOTH_WINDOW_S window
    win = max(1, int(round(SMOOTH_WINDOW_S / SAMPLE_STEP_S)))
    if win % 2 == 0:
        win += 1
    smoothed = list(sample_state)
    half = win // 2
    if win > 1:
        codes = [1 if s == "you" else 0 for s in sample_state]
        sm = []
        for i in range(len(codes)):
            lo, hi = max(0, i - half), min(len(codes), i + half + 1)
            window = codes[lo:hi]
            sm.append(1 if sum(window) * 2 >= len(window) else 0)
        smoothed = ["you" if c else "content" for c in sm]

    # merge into contiguous runs
    sample_times = [idx / fps for idx in sample_idx]
    runs = []
    cur_state, cur_start = smoothed[0], sample_times[0]
    for i in range(1, len(smoothed)):
        if smoothed[i] != cur_state:
            runs.append([cur_state, cur_start, sample_times[i]])
            cur_state, cur_start = smoothed[i], sample_times[i]
    runs.append([cur_state, cur_start, dur])

    # absorb runs shorter than MIN_RUN_S into their neighbor (prefer the
    # longer of the two neighbors; a same-state merge just extends).
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i, (state, s, e) in enumerate(runs):
            floor = MIN_CONTENT_RUN_S if state == "content" else MIN_RUN_S
            if e - s >= floor:
                continue
            prev_len = runs[i - 1][2] - runs[i - 1][1] if i > 0 else -1
            next_len = runs[i + 1][2] - runs[i + 1][1] if i + 1 < len(runs) else -1
            if prev_len < 0 and next_len < 0:
                break  # only run left, nothing to absorb into
            if next_len >= prev_len:
                runs[i + 1][1] = s
                del runs[i]
            else:
                runs[i - 1][2] = e
                del runs[i]
            # re-merge any now-adjacent same-state runs
            merged = []
            for r in runs:
                if merged and merged[-1][0] == r[0]:
                    merged[-1][2] = r[2]
                else:
                    merged.append(list(r))
            runs = merged
            changed = True
            break

    runs = [(s, round(a, 2), round(b, 2)) for s, a, b in runs]
    if debug:
        print("[react] classified runs:", file=sys.stderr)
        for state, s, e in runs:
            print(f"[react]   {s:6.2f}s -> {e:6.2f}s  ({e - s:5.2f}s)  {state}", file=sys.stderr)
    return runs, fps, n


def _run_state_at(runs, t):
    for state, s, e in runs:
        if s <= t < e or (t >= e and (state, s, e) == runs[-1]):
            return state
    return runs[-1][0] if runs else "you"


def _draw_content_frame(fr_bgr, img_out):
    """Render a 'content' frame: full 16:9 source letterboxed into the
    1080x1920 canvas (scaled to 1080 wide -> 1080x608), centered vertically
    at CONTENT_CENTER_Y_FRAC of canvas height, background filled with a
    heavily blurred + darkened copy of the same frame (cover_source_captions'
    aesthetic). Draws directly into `img_out` (a PIL Image already sized
    W_OUT x H_OUT); caller draws headline/captions on top afterward."""
    rgb = cv2.cvtColor(fr_bgr, cv2.COLOR_BGR2RGB)
    src_img = Image.fromarray(rgb)
    src_w, src_h = src_img.size

    # background: cover-fill W_OUT x H_OUT, blur + darken
    scale_bg = max(W_OUT / src_w, H_OUT / src_h)
    bg_w, bg_h = int(round(src_w * scale_bg)), int(round(src_h * scale_bg))
    bg = src_img.resize((bg_w, bg_h), Image.LANCZOS)
    bx = (bg_w - W_OUT) // 2
    by = (bg_h - H_OUT) // 2
    bg = bg.crop((bx, by, bx + W_OUT, by + H_OUT))
    bg = bg.filter(ImageFilter.GaussianBlur(CONTENT_BLUR_RADIUS))
    bg = ImageEnhance.Brightness(bg).enhance(CONTENT_DARKEN)
    img_out.paste(bg, (0, 0))

    # foreground: fit the full frame at 1080 wide, centered at ~38% height
    fg_h = int(round(CONTENT_W * src_h / src_w))
    fg = src_img.resize((CONTENT_W, fg_h), Image.LANCZOS)
    cy = int(round(H_OUT * CONTENT_CENTER_Y_FRAC))
    fy = cy - fg_h // 2
    img_out.paste(fg, (0, fy))


def render(clip_mp4, phrases, runs, fps, silent_out, headline=None, captions=True,
           cover_captions=False):
    """Per-frame dispatch by run state:
      'you'     -> render_clip's face-tracked 9:16 punch-in (track_center_x
                   trajectory computed once over the whole clip, indexed here
                   only for frames whose state is 'you').
      'content' -> full 16:9 frame letterboxed + blurred backdrop.
    Headline and karaoke captions are drawn on top in both cases, at the same
    positions render_clip.py uses.
    """
    traj = track_center_x(clip_mp4)
    static_cx = None
    if traj is None:
        static_cx = crop_center_x(clip_mp4)

    cap = cv2.VideoCapture(clip_mp4)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    crop_w = int(round(src_h * 9 / 16))   # resolution-agnostic (720p sources exist)
    if static_cx is not None:
        x0_static = int(max(0, min(src_w - crop_w, static_cx - crop_w / 2)))

    vw = cv2.VideoWriter(silent_out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W_OUT, H_OUT))
    hl_font = font(64)
    idx = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        t = idx / fps
        state = _run_state_at(runs, t)

        if state == "you":
            if traj is not None:
                cx = traj[idx] if idx < len(traj) else traj[-1]
                x0 = int(max(0, min(src_w - crop_w, cx - crop_w / 2)))
            else:
                x0 = x0_static
            crop = fr[0:src_h, x0:x0 + crop_w]
            crop = cv2.resize(crop, (W_OUT, H_OUT), interpolation=cv2.INTER_CUBIC)
            img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            if cover_captions:
                cover_source_captions(img)
        else:
            img = Image.new("RGB", (W_OUT, H_OUT))
            _draw_content_frame(fr, img)

        if headline:
            dd = ImageDraw.Draw(img)
            lines = _wrap(dd, headline.upper(), hl_font, W_OUT - 120)
            yy = int(H_OUT * 0.11)
            for ln in lines:
                b = dd.textbbox((0, 0), ln, font=hl_font)
                dd.text(((W_OUT - (b[2] - b[0])) // 2, yy), ln, font=hl_font,
                        fill=WHITE, stroke_width=7, stroke_fill=STROKE)
                yy += int((b[3] - b[1]) * 1.5)
        if captions:
            for ph in phrases:
                if ph[0]["start"] <= t <= ph[-1]["end"]:
                    draw_caption(img, ph, t)
                    break
        vw.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        idx += 1
    cap.release()
    vw.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", type=float, default=None,
                    help="required unless --classify-only")
    ap.add_argument("--end", type=float, default=None,
                    help="required unless --classify-only")
    ap.add_argument("--out", required=False, help="required unless --classify-only")
    ap.add_argument("--headline", default=None, help="persistent on-screen hook text")
    ap.add_argument("--model", default="base", choices=list(MODELS))
    ap.add_argument("--no-captions", action="store_true",
                    help="skip karaoke captions (for source that is already captioned); keeps the headline")
    ap.add_argument("--cover-source-captions", action="store_true",
                    help="hide the source's burned-in bottom captions on 'you' runs with a "
                         "blurred+darkened lower-third band before drawing our karaoke caption")
    ap.add_argument("--expect-first", default=None,
                    help="first few words the clip should OPEN on; the cut snaps to their "
                         "spoken onset (fixes early-skewed auto-sub starts bleeding in the "
                         "previous sentence)")
    ap.add_argument("--expect-last", default=None,
                    help="last few words the clip should END on; the cut extends to their true end")
    ap.add_argument("--debug-states", action="store_true",
                    help="print the classified you/content runs")
    ap.add_argument("--classify-only", action="store_true",
                    help="run just the layout classifier on --video (treated as the clip "
                         "itself, no cut/transcribe/render) and print the runs, then exit")
    a = ap.parse_args()

    if a.classify_only:
        target = a.video
        tmp_seg = None
        if a.start is not None or a.end is not None:
            tmp_dir = tempfile.mkdtemp(prefix="obreact_classify_")
            tmp_seg = os.path.join(tmp_dir, "segment.mp4")
            start = a.start if a.start is not None else 0.0
            cut_args = ["ffmpeg", "-y", "-ss", str(start)]
            if a.end is not None:
                cut_args += ["-to", str(a.end)]
            cut_args += ["-i", a.video, "-c", "copy", tmp_seg]
            print(f"[react] classify-only: cutting [{start}, {a.end}] before scanning",
                  file=sys.stderr)
            sh(cut_args)
            target = tmp_seg
        runs, fps, n = classify_states(target, debug=True)
        dur = n / fps if fps else 0.0
        n_you = sum(1 for s, s0, e0 in runs if s == "you")
        n_content = sum(1 for s, s0, e0 in runs if s == "content")
        print(f"[react] classify-only: {len(runs)} runs over {dur:.2f}s "
              f"({n_you} you / {n_content} content)", file=sys.stderr)
        return

    if a.start is None or a.end is None:
        raise SystemExit("--start and --end are required unless --classify-only")
    if not a.out:
        raise SystemExit("--out is required unless --classify-only")

    tmp = tempfile.mkdtemp(prefix="obreact_")
    wide = os.path.join(tmp, "wide.mp4")
    clip = os.path.join(tmp, "clip.mp4")
    wav = os.path.join(tmp, "wide.wav")
    silent = os.path.join(tmp, "silent.mp4")

    if a.expect_first or a.expect_last:
        pad_pre, pad_post = 2.5, 2.5
        ws = max(0.0, a.start - pad_pre)
        print("[react] 1/5 cut wide segment + refine boundaries", file=sys.stderr)
        sh(["ffmpeg", "-y", "-ss", str(ws), "-to", str(a.end + pad_post), "-i", a.video,
            "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", wide])
        sh(["ffmpeg", "-y", "-i", wide, "-ar", "16000", "-ac", "1", wav])
        words = transcribe_words(wav, a.model)
        wide_dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", wide],
            capture_output=True, text=True).stdout.strip() or 0)
        rs, re_ = refine_bounds(words, wide_dur, a.start - ws, a.end - ws,
                                a.expect_first, a.expect_last)
        print(f"[react]     refined: start {ws + rs:.2f}s end {ws + re_:.2f}s "
              f"(was {a.start:.2f}-{a.end:.2f})", file=sys.stderr)
        sh(["ffmpeg", "-y", "-ss", str(rs), "-to", str(re_), "-i", wide,
            "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", clip])
        if a.no_captions:
            phrases = []
            print("[react] 2/5 captions skipped (--no-captions)", file=sys.stderr)
        else:
            kept = [{"w": w["w"], "start": w["start"] - rs, "end": w["end"] - rs}
                    for w in words if w["start"] >= rs - 0.05 and w["end"] <= re_ + 0.05]
            phrases = group_phrases(kept)
            print(f"[react] 2/5 captions from refine pass ({len(kept)} words)", file=sys.stderr)
    else:
        print("[react] 1/5 cut segment", file=sys.stderr)
        sh(["ffmpeg", "-y", "-ss", str(a.start), "-to", str(a.end), "-i", a.video,
            "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", clip])
        if a.no_captions:
            phrases = []
            print("[react] 2/5 captions skipped (--no-captions)", file=sys.stderr)
        else:
            print("[react] 2/5 transcribe words", file=sys.stderr)
            sh(["ffmpeg", "-y", "-i", clip, "-ar", "16000", "-ac", "1", wav])
            phrases = group_phrases(transcribe_words(wav, a.model))

    print("[react] 3/5 classify you/content runs", file=sys.stderr)
    runs, fps, n = classify_states(clip, debug=a.debug_states)
    n_you = sum(1 for s, s0, e0 in runs if s == "you")
    n_content = sum(1 for s, s0, e0 in runs if s == "content")
    print(f"[react]     {len(runs)} runs ({n_you} you / {n_content} content)", file=sys.stderr)

    print(f"[react] 4/5 render frames ({len(phrases)} caption phrases)", file=sys.stderr)
    render(clip, phrases, runs, fps, silent, headline=a.headline, captions=not a.no_captions,
           cover_captions=a.cover_source_captions)

    print("[react] 5/5 mux audio + loudnorm -14 LUFS + x264", file=sys.stderr)
    sh(["ffmpeg", "-y", "-i", silent, "-i", clip, "-map", "0:v", "-map", "1:a",
        "-af", "loudnorm=I=-14:TP=-1:LRA=11", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out])
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", a.out],
                         capture_output=True, text=True).stdout.strip()
    print(f"[react] done -> {a.out} ({dur}s)", file=sys.stderr)


if __name__ == "__main__":
    main()
