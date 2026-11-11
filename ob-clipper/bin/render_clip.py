#!/usr/bin/env python3
"""
render_clip.py — turn one approved moment into a finished, post-ready 9:16 Reel.

Pipeline (all with the local toolkit; ffmpeg has NO drawtext so captions are PIL):
  1. cut the [start,end] segment from the source (accurate re-encode)
  2. whisper-cli word-level timestamps on the segment
  3. cv2 Haar face-TRACKING -> smoothed per-frame 9:16 punch-in crop (dead-zone, no jitter)
  4. per-frame: crop -> 1080x1920 -> [optional cover-band over source captions] -> PIL karaoke caption
  5. ffmpeg: mux full-quality audio, loudnorm -14 LUFS, x264 crf18, faststart

Usage:
  python3 render_clip.py --video V.mp4 --start 1.2 --end 16.4 --out reel.mp4 \
      [--title "..."] [--model base|medium] [--headline "ON-SCREEN HOOK"]
"""
import os, sys, re, json, subprocess, argparse, tempfile
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W_OUT, H_OUT = 1080, 1920

# ---- cover-band geometry (hides OB's burned-in source captions) -------------
# The published long-form has captions near the bottom; the 9:16 crop slices
# their edges. This band covers y in [0.80*H, 0.97*H] of the 1080x1920 output
# with a blurred+darkened copy of that same region (intentional lower-third),
# while our karaoke caption sits at ~0.70*H and stays on top / legible.
COVER_BAND_TOP = int(H_OUT * 0.80)          # 1536
COVER_BAND_BOTTOM = int(H_OUT * 0.97)       # 1862
COVER_BLUR_RADIUS = 45                       # heavy gaussian blur (px)
COVER_DARKEN = 0.45                          # multiply brightness (0=black, 1=none)

ASPECT = "vertical"   # set from --aspect at startup; drives set_aspect() below

MODELS = {"base": os.path.expanduser("~/.whisper-models/ggml-base.en.bin"),
          "medium": os.path.expanduser("~/.whisper-models/ggml-medium.en.bin")}

# ---- classic (legacy) font stack — kept so --style classic is pixel-identical
# to the pre-style-engine renderer. Do not add to this list; add to
# STYLE_FONTS_BOLD2026 instead.
FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]
YELLOW, WHITE, STROKE = (255, 214, 10), (255, 255, 255), (0, 0, 0)

# =============================================================================
# VISUAL STYLE ENGINE — implements /Users/YOU/ob-moments/data/style-spec.json
# =============================================================================
# "classic" reproduces the pre-existing look exactly (FONTS list, YELLOW/WHITE,
# draw_caption's old geometry). "bold2026" implements the spec: 1-3 word ALL_CAPS
# caption chunks, alternating base color per chunk, keyword/number emphasis
# color, heavier stroke+shadow, bigger restyled headline with optional pill,
# safe-zone-aware placement.
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

# Font resolution order per spec.font_resolution_order: a locally-downloaded
# free font first (Anton — verified present, single static weight, reads well
# large per the spec's own note), then macOS system fallbacks, then the legacy
# FONTS stack as a final safety net so a caption is NEVER left un-rendered.
STYLE_FONTS_BOLD2026 = [
    os.path.join(_FONT_DIR, "Anton-Regular.ttf"),
    os.path.join(_FONT_DIR, "Montserrat-ExtraBold.ttf"),   # optional, not bundled by default
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
] + FONTS

STYLE_FONTS_CLASSIC = FONTS

# --- caption chunking (spec.caption.chunk_words) ----------------------------
CHUNK_WORDS_BOLD2026 = 2          # spec default; range 1-3, never exceed 3
CHUNK_WORDS_CLASSIC = 3           # legacy group_phrases default, unchanged
CHUNK_WORDS_PLATE = 3             # "plate": 2-3 words, changes about every 0.7 s like the decoded reel

# --- PLATE style (decoded 2026-10-20 from Payton Kaleiwahea's motion-graphics reel, BBM Media) ----------
# the chunk sits on a black plate with a thin white outline; ONE emphasis word in yellow (a number, then a
# power/pain word, else the longest content word). Reads on any footage without a stroke on every letter.
CAPTION_SIZE_PLATE = 80
PLATE_FILL, PLATE_OUTLINE, PLATE_EMPH = (12, 12, 12), (255, 255, 255), (255, 214, 10)
PLATE_OUTLINE_W, PLATE_RADIUS, PLATE_PAD_X, PLATE_PAD_Y = 3, 6, 22, 14

# --- caption sizing / stroke / shadow (spec.caption) ------------------------
CAPTION_SIZE_PX_BOLD2026 = 84                 # spec.caption.size_px_at_1080.value
CAPTION_SIZE_MIN_BOLD2026 = 56                # shrink floor before auto-shrink gives up
CAPTION_STROKE_W_BOLD2026 = 8                 # spec.caption.stroke.width_px
CAPTION_SHADOW_BOLD2026 = dict(color=(0, 0, 0), opacity=0.55, offset=(0, 4), blur=6)
CAPTION_Y_BOLD2026 = 1250                     # spec.caption.position.y_px_at_1080x1920
CAPTION_MAX_WIDTH_PCT_BOLD2026 = 0.82         # spec.caption.position.max_width_pct_of_canvas
# horizontal-mode overrides for the two above (set_aspect() swaps these in)
CAPTION_Y_BOLD2026_H = int(1080 * 0.80)       # 864 — 16:9 canvas is only 1080 tall
CAPTION_MAX_WIDTH_PCT_BOLD2026_H = 0.70        # narrower pct so lines don't span the full 1920 width

# --- active-word + base alternating color (spec.caption.active_word) -------
CAPTION_COLOR_PRIMARY = (143, 184, 232)       # #8FB8E8 light blue/lavender
CAPTION_COLOR_SECONDARY = (232, 67, 61)       # #E8433D red
CAPTION_SCALE_POP = 1.12                      # spec scale_pop.scale_factor
CAPTION_SCALE_POP_ENABLED = False             # spec ships this OFF by default (color-alt only,
                                               # matches the verified reference); flip for A/B test

# --- keyword / number emphasis (spec.caption.emphasis_words) ---------------
EMPHASIS_COLOR_NUMBERS = (255, 212, 0)        # #FFD400 numbers_and_stats + action_verbs
EMPHASIS_COLOR_PAIN = (232, 67, 61)           # #E8433D pain_words
_PAIN_WORDS = {"hungry", "cravings", "craving", "stuck", "failing", "fail",
               "exhausted", "willpower", "tired", "starving", "bloated",
               "ashamed", "embarrassed", "frustrated", "hopeless"}
_POWER_WORDS = {"stop", "control", "build", "fix", "master", "finally",
                "proof", "guaranteed", "results", "transform", "win"}
_NUMBER_RE = re.compile(r"^[\$]?\d+([.,]\d+)?(%|x|lb|lbs|k|kg)?$", re.IGNORECASE)


def _classify_emphasis(word_upper):
    """Return an emphasis color for a single caption word, or None if it should
    just follow the chunk's base alternating color. Implements
    spec.caption.emphasis_words (numbers_and_stats + action_verbs -> yellow,
    pain_words -> red), independent of whether the word is the 'active' word."""
    w = word_upper.strip(".,!?:;\"'").lower()
    if not w:
        return None
    if _NUMBER_RE.match(w) or any(ch.isdigit() for ch in w):
        return EMPHASIS_COLOR_NUMBERS
    if w in _PAIN_WORDS:
        return EMPHASIS_COLOR_PAIN
    if w in _POWER_WORDS:
        return EMPHASIS_COLOR_NUMBERS
    return None


# --- EXPLAINER style (Drew-Canole documentary look) -------------------------
# red hook banner for the first N seconds only, then removed so it never covers
# captions; highlight-word captions get a solid box behind the ONE emphasis word
# (yellow normally, red for pain/biggest-beat words); soft end-card overlay.
EXPLAINER_BANNER_SECONDS = 3.0
EXPLAINER_BANNER_BG = (208, 32, 32)           # solid red block
EXPLAINER_BANNER_TEXT = (255, 255, 255)       # white heavy sans
EXPLAINER_BANNER_EMPH = (255, 212, 0)         # one key word swapped to yellow
EXPLAINER_BANNER_TOP = 72                      # inside the reserved top-18% (346px @1920)
EXPLAINER_BANNER_SIZE = 62                     # vertical; horizontal override below
EXPLAINER_BANNER_SIZE_H = 46
EXPLAINER_BANNER_PAD = 24                       # padding inside the red block
EXPLAINER_BOX_YELLOW = (255, 212, 0)           # emphasis-word box (normal)
EXPLAINER_BOX_RED = (208, 32, 32)              # emphasis-word box (pain / biggest beat)
EXPLAINER_BOX_TEXT_ON = (17, 17, 17)           # dark text sits on the yellow box for contrast
EXPLAINER_ENDCARD_SECONDS = 2.0
EXPLAINER_HANDLE = "@ob_health.fit"

# --- headline restyle (spec.headline) ---------------------------------------
HEADLINE_SIZE_PX_BOLD2026 = 78                # OB 2026-07-04: smaller title (was 108)
HEADLINE_STROKE_W_BOLD2026 = 6                # lighter with the smaller size
HEADLINE_SHADOW_BOLD2026 = dict(color=(0, 0, 0), opacity=0.35, offset=(0, 3), blur=5)
HEADLINE_COLOR_BOLD2026 = (255, 255, 255)     # spec.headline.color.default
HEADLINE_Y_HOOK_BOLD2026 = 240               # top of safe zone; 450 sat ON the subject's eyes (frame-audit catch)
HEADLINE_MAX_WIDTH_PCT_BOLD2026 = 0.88        # spec.headline.position.max_width_pct_of_canvas
# OB (2026-07-04): the pill box was blocking his face on tall-framed clips.
# Disabled; the headline's heavy stroke + shadow keeps it legible on any background.
HEADLINE_PILL_BOLD2026 = dict(enabled=False, color=(0, 0, 0), opacity=0.55,
                              padding=24, radius=12)
# horizontal-mode overrides (set_aspect() swaps these in)
HEADLINE_SIZE_PX_BOLD2026_H = 58               # OB 2026-07-04: smaller title (was 88)
HEADLINE_Y_HOOK_BOLD2026_H = int(1080 * 0.06)  # 64 — top of the 1080-tall canvas

# --- safe zones (spec.safe_zones.usable_safe_rect_px) -----------------------
SAFE_X_MIN, SAFE_X_MAX = 60, 996
SAFE_Y_MIN, SAFE_Y_MAX = 210, 1610
# horizontal-mode safe zone (set_aspect() swaps these in): x 60..1860, y 60..1010
SAFE_X_MIN_H, SAFE_X_MAX_H = 60, 1860
SAFE_Y_MIN_H, SAFE_Y_MAX_H = 60, 1010

# ---- vertical (default) values stashed so set_aspect('vertical') can restore
# them exactly after a prior 'horizontal' call mutated the module globals.
_VERTICAL_DEFAULTS = dict(
    W_OUT=1080, H_OUT=1920,
    CAPTION_Y_BOLD2026=1250, CAPTION_MAX_WIDTH_PCT_BOLD2026=0.82,
    HEADLINE_SIZE_PX_BOLD2026=78, HEADLINE_Y_HOOK_BOLD2026=240,   # 78 not 108: stale default was silently reverting the module-level "smaller title" edit on every set_aspect('vertical')
    SAFE_X_MIN=60, SAFE_X_MAX=996, SAFE_Y_MIN=210, SAFE_Y_MAX=1610,
    COVER_BAND_TOP=int(1920 * 0.80), COVER_BAND_BOTTOM=int(1920 * 0.97),
)


def set_aspect(aspect):
    """Reassign the module-level output-geometry globals for 'vertical'
    (1080x1920, the original layout) or 'horizontal' (1920x1080, full-frame
    no-crop). Must be called BEFORE any drawing (draw_caption/draw_headline/
    fit_wide/cover_source_captions all read these globals at call time).
    Idempotent — calling with the same aspect twice is a no-op-equivalent."""
    global ASPECT, W_OUT, H_OUT
    global CAPTION_Y_BOLD2026, CAPTION_MAX_WIDTH_PCT_BOLD2026
    global HEADLINE_SIZE_PX_BOLD2026, HEADLINE_Y_HOOK_BOLD2026
    global SAFE_X_MIN, SAFE_X_MAX, SAFE_Y_MIN, SAFE_Y_MAX
    global COVER_BAND_TOP, COVER_BAND_BOTTOM
    global _cover_mask

    ASPECT = aspect
    if aspect == "horizontal":
        W_OUT, H_OUT = 1920, 1080
        CAPTION_Y_BOLD2026 = CAPTION_Y_BOLD2026_H
        CAPTION_MAX_WIDTH_PCT_BOLD2026 = CAPTION_MAX_WIDTH_PCT_BOLD2026_H
        HEADLINE_SIZE_PX_BOLD2026 = HEADLINE_SIZE_PX_BOLD2026_H
        HEADLINE_Y_HOOK_BOLD2026 = HEADLINE_Y_HOOK_BOLD2026_H
        SAFE_X_MIN, SAFE_X_MAX = SAFE_X_MIN_H, SAFE_X_MAX_H
        SAFE_Y_MIN, SAFE_Y_MAX = SAFE_Y_MIN_H, SAFE_Y_MAX_H
        COVER_BAND_TOP = int(H_OUT * 0.80)
        COVER_BAND_BOTTOM = int(H_OUT * 0.97)
    else:
        d = _VERTICAL_DEFAULTS
        W_OUT, H_OUT = d["W_OUT"], d["H_OUT"]
        CAPTION_Y_BOLD2026 = d["CAPTION_Y_BOLD2026"]
        CAPTION_MAX_WIDTH_PCT_BOLD2026 = d["CAPTION_MAX_WIDTH_PCT_BOLD2026"]
        HEADLINE_SIZE_PX_BOLD2026 = d["HEADLINE_SIZE_PX_BOLD2026"]
        HEADLINE_Y_HOOK_BOLD2026 = d["HEADLINE_Y_HOOK_BOLD2026"]
        SAFE_X_MIN, SAFE_X_MAX = d["SAFE_X_MIN"], d["SAFE_X_MAX"]
        SAFE_Y_MIN, SAFE_Y_MAX = d["SAFE_Y_MIN"], d["SAFE_Y_MAX"]
        COVER_BAND_TOP = d["COVER_BAND_TOP"]
        COVER_BAND_BOTTOM = d["COVER_BAND_BOTTOM"]
    _cover_mask = None   # geometry changed; force cover_source_captions() to rebuild it

STYLE = "classic"    # set from --style at startup; module-level so shared
                      # helpers (font/draw_caption/_wrap) stay drop-in compatible
                      # with react_clip.py's `from render_clip import ...`


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f"command failed: {' '.join(cmd[:3])}...")
    return r


_font_cache = {}


def font(size, style=None):
    """Resolve a font at `size` for the given style ('classic'/'bold2026',
    defaults to the module-level STYLE set by --style). Signature stays
    backward-compatible: font(size) alone still works everywhere it's already
    called (react_clip.py, draw_caption, headline block)."""
    style = style or STYLE
    stack = STYLE_FONTS_BOLD2026 if style in ("bold2026", "plate") else STYLE_FONTS_CLASSIC
    key = (style, size)
    if key in _font_cache:
        return _font_cache[key]
    for p in stack:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            _font_cache[key] = f
            return f
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


def resolved_font_path(style=None):
    """Which font file `font()` will actually pick for this style — used by
    the verification script to report exact fonts resolved."""
    style = style or STYLE
    stack = STYLE_FONTS_BOLD2026 if style in ("bold2026", "plate") else STYLE_FONTS_CLASSIC
    for p in stack:
        if os.path.exists(p):
            return p
    return "<PIL default>"


# ---- 2. word-level transcript on the clip ----------------------------------
def transcribe_words(wav, model):
    pre = wav[:-4]
    sh(["whisper-cli", "-m", MODELS[model], "-f", wav, "-ml", "1", "-sow",
        "-oj", "-of", pre])
    data = json.load(open(pre + ".json"))
    words = []
    for seg in data.get("transcription", []):
        t = seg.get("text", "").strip()
        off = seg.get("offsets", {})
        if t and "from" in off:
            words.append({"w": t, "start": off["from"] / 1000.0, "end": off["to"] / 1000.0})
    return words


def _norm_tok(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def _find_seq(words, expect, from_end=False):
    """Find a fuzzy consecutive match of `expect` (a string of a few words) in the
    whisper word list. Matching is 4-char-stem based (survives base-model mishears
    like 'Tanked'->'Tank to') and tolerates one mismatched token. Hyphenated words
    are EXPLODED on both sides ('65-year-old' vs '65 year old' must match — an
    unexploded mismatch silently skipped boundary refinement and left start-bleed).
    Returns (start_idx, end_idx) into the original word list, or None."""
    toks = [_norm_tok(p) for t in expect.split() for p in t.split("-") if _norm_tok(p)]
    if not toks:
        return None
    wt, owner = [], []                      # exploded tokens + owning word index
    for wi, w in enumerate(words):
        for p in w["w"].split("-"):
            p = _norm_tok(p)
            if p:
                wt.append(p)
                owner.append(wi)

    def tok_match(a, b):
        return a == b or (len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4])

    hits = []
    for i in range(len(wt) - len(toks) + 1):
        misses = [j for j, tok in enumerate(toks) if not tok_match(wt[i + j], tok)]
        if len(misses) <= (0 if len(toks) < 3 else 1):
            # If the FIRST expected token is the one that missed, the anchor has
            # likely slid one word late over a mishear ("Tanked my" heard as
            # "Tank to my" anchored on "to" and chopped "Tanked"). Step back one
            # word: opening ~0.3s early is harmless, chopping the first word is fatal.
            si = i - 1 if (misses and misses[0] == 0 and i > 0) else i
            hits.append((owner[si], owner[i + len(toks) - 1]))
    if not hits:
        return None
    return hits[-1] if from_end else hits[0]


def refine_bounds(words, wide_dur, orig_start_in_wide, orig_end_in_wide,
                  expect_first=None, expect_last=None):
    """Snap the cut to true speech: YouTube rolling auto-subs timestamp words
    EARLY (they show on screen before they're spoken), so sentence-derived clip
    starts bleed the tail of the PREVIOUS sentence in, and ends can chop the
    final word. Given whisper words on a padded 'wide' cut, find the onset of
    the expected first words and the end of the expected last words."""
    rs, re_ = orig_start_in_wide, orig_end_in_wide
    if expect_first:
        m = _find_seq(words, expect_first)
        if m:
            rs = max(0.0, words[m[0]]["start"] - 0.18)
    if expect_last:
        m = _find_seq(words, expect_last, from_end=True)
        if m:
            re_ = min(wide_dur, words[m[1]]["end"] + 0.30)
    if re_ - rs < 3.0:                       # refuse a nonsense refinement
        return orig_start_in_wide, orig_end_in_wide
    return rs, re_


def group_phrases(words, max_words=None):
    """chunk words into <=max_words caption lines, breaking on sentence punctuation.
    max_words defaults per the active STYLE: bold2026 -> 2 (spec.caption.chunk_words,
    1-3 word karaoke chunks), classic -> 3 (legacy default, unchanged behavior)."""
    if max_words is None:
        max_words = (CHUNK_WORDS_BOLD2026 if STYLE == "bold2026" else
                     CHUNK_WORDS_PLATE if STYLE == "plate" else CHUNK_WORDS_CLASSIC)
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.!?]$", w["w"]):
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)
    return phrases


# ---- 3. face-centered crop -------------------------------------------------
def crop_center_x(clip_mp4):
    """STATIC fallback: single median face-center-x over a sparse sample."""
    cap = cv2.VideoCapture(clip_mp4)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    xs = []
    for i in range(0, n, max(1, n // 40)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = casc.detectMultiScale(g, 1.1, 5, minSize=(120, 120))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            xs.append(x + w / 2)
    cap.release()
    return float(np.median(xs)) if xs else 960.0


def track_center_x(clip_mp4):
    """Two-pass FACE-TRACKING crop trajectory (robust for moving subjects/B-roll).

    Pass 1: detect face center-x on a DENSE sample of frames (Haar); when no
            face, fall back to last-known, then frame-center 960.
    Pass 2: interpolate to a per-frame center-x over ALL frames, SMOOTH with a
            ~0.5s moving-average window, then apply a dead-zone so tiny moves
            don't cause jitter. Clamping to a valid crop window is done at
            render time against the real crop width.

    Returns a numpy array of length n (one center-x per frame), or None if
    cv2/Haar is unavailable so the caller can use the static fallback.
    """
    try:
        cap = cv2.VideoCapture(clip_mp4)
        casc_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        casc = cv2.CascadeClassifier(casc_path)
        if casc.empty():
            cap.release()
            return None
    except Exception:
        return None

    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    if n <= 0:
        cap.release()
        return None

    # Pass 1: dense sample (~every 0.1s, at least every 3rd frame) ----------
    step = max(1, min(3, int(round(fps * 0.1)) or 1))
    sample_idx, sample_x = [], []
    last_known = None
    for i in range(0, n, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = casc.detectMultiScale(g, 1.1, 5, minSize=(120, 120))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            cx = x + w / 2.0
            last_known = cx
        elif last_known is not None:
            cx = last_known                       # fall back to last-known face
        else:
            cx = src_w / 2.0 if src_w else 960.0  # then frame-center
        sample_idx.append(i)
        sample_x.append(cx)
    cap.release()

    if not sample_x:
        return None

    # Pass 2a: interpolate the sparse samples to a per-frame trajectory ------
    all_idx = np.arange(n)
    traj = np.interp(all_idx, np.array(sample_idx), np.array(sample_x))

    # Pass 2b: smooth with a ~0.5s moving-average window ---------------------
    win = max(1, int(round(fps * 0.5)))
    if win > 1:
        kernel = np.ones(win) / win
        traj = np.convolve(traj, kernel, mode="same")
        # convolve tapers the edges; restore ends toward the raw trajectory
        half = win // 2
        if n > half:
            traj[:half] = traj[half]
            traj[-half:] = traj[-half - 1]

    # Pass 2c: dead-zone — hold position until movement exceeds a threshold --
    dead = max(6.0, src_w * 0.01)                 # ~1% of source width
    out = np.empty(n)
    held = traj[0]
    for i in range(n):
        if abs(traj[i] - held) > dead:
            held = traj[i]
        out[i] = held
    return out


def _skin_fraction(bgr_box):
    """Fraction of skin-tone pixels (classic YCrCb range) in a candidate face box.
    Discriminates real faces from Haar's texture false-positives (blinds, walls)."""
    if bgr_box is None or bgr_box.size == 0:
        return 0.0
    ycrcb = cv2.cvtColor(bgr_box, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycrcb[:, :, 1], ycrcb[:, :, 2]
    skin = (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)
    return float(skin.mean())


def shot_locked_center_x(clip_mp4):
    """SHOT-LOCKED crop trajectory — the multi-guest / multicam fix.

    track_center_x follows the largest face continuously, which fails on podcast
    footage two ways: with several guests the 'largest face' oscillates between
    people, and the EMA smooths source camera-cuts into visible swooshy PANS.
    Real cameras in a podcast are static, so what reads as 'smooth' is:
      * detect the source's own shot cuts (frame-difference on thumbnails),
      * within each shot HOLD ONE static crop on that shot's dominant face
        (the position cluster with the most face-area — the featured speaker),
      * hard-SNAP at cuts, never interpolate across them.
    Returns a per-frame numpy trajectory (piecewise-constant), or None on failure.
    """
    try:
        cap = cv2.VideoCapture(clip_mp4)
        casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if casc.empty():
            cap.release()
            return None
        _profile_casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
        if _profile_casc.empty():
            _profile_casc = None
    except Exception:
        return None
    # YuNet (DNN) is the primary detector when its model is present — handles the
    # caps/glasses/side-profiles that defeat Haar. Haar chain stays as fallback.
    yunet = None
    _ypath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models",
                          "face_detection_yunet_2023mar.onnx")
    if os.path.exists(_ypath):
        try:
            yunet = cv2.FaceDetectorYN_create(_ypath, "", (320, 320), 0.6)
        except Exception:
            yunet = None
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    # RESOLUTION-AGNOSTIC detection scale: sources are NOT always 1920 wide — a
    # 720p podcast with a hardcoded x2.0 map put every crop 300px right of the
    # face (the great 'undetectable face' hunt was actually this one line).
    det_w = 960
    det_h = max(2, int(round(src_h * det_w / src_w)))
    x_scale = src_w / det_w
    if n <= 0:
        cap.release()
        return None

    thumb_every = max(1, int(round(fps * 0.13)))     # cut detection cadence
    face_every = max(1, int(round(fps * 0.27)))      # detection cadence
    thumbs, faces = [], []                           # (idx, small-gray), (idx, x, area)
    idx = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if idx % thumb_every == 0:
            g = cv2.cvtColor(cv2.resize(fr, (48, 27)), cv2.COLOR_BGR2GRAY)
            thumbs.append((idx, g.astype(np.int16)))
        if idx % face_every == 0:
            small = cv2.resize(fr, (det_w, det_h))
            dets = []
            if yunet is not None:
                yunet.setInputSize((det_w, det_h))
                _, yf = yunet.detect(small)
                if yf is not None:
                    dets = [(int(f[0]), int(f[1]), int(f[2]), int(f[3])) for f in yf]
            if not dets:
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                dets = list(casc.detectMultiScale(gray, 1.1, 5, minSize=(50, 50)))
                if not dets and _profile_casc is not None:
                    # side profiles the frontal cascade misses entirely
                    dets = list(_profile_casc.detectMultiScale(gray, 1.1, 5, minSize=(50, 50)))
                    if not dets:
                        flipped = cv2.flip(gray, 1)
                        for x, y, w, h in _profile_casc.detectMultiScale(flipped, 1.1, 5, minSize=(50, 50)):
                            dets.append((gray.shape[1] - x - w, y, w, h))
            for x, y, w, h in dets:
                # SANITY vs Haar texture hallucinations: plausible size + real skin
                if w > small.shape[1] * 0.36:
                    continue
                if _skin_fraction(small[max(0, y):y + h, max(0, x):x + w]) < 0.22:
                    continue
                faces.append((idx, (x + w / 2) * x_scale, float(w * h)))  # -> source px
        idx += 1
    cap.release()
    if not thumbs:
        return None

    # shot boundaries: normalized mean-abs-diff spike between consecutive thumbs
    cuts = [0]
    for (i1, t1), (i2, t2) in zip(thumbs, thumbs[1:]):
        if np.abs(t2 - t1).mean() > 22:
            cuts.append(i2)
    cuts.append(n)
    # merge shots shorter than 0.5s into the previous one
    min_shot = int(fps * 0.5)
    merged = [cuts[0]]
    for c in cuts[1:-1]:
        if c - merged[-1] >= min_shot:
            merged.append(c)
    merged.append(n)

    traj = np.full(n, src_w / 2.0)
    for s, e in zip(merged, merged[1:]):
        shot_faces = [(x, a) for i, x, a in faces if s <= i < e]
        if shot_faces:
            # dominant face cluster: split sorted xs at gaps > 15% width,
            # pick the cluster with the most total face area
            shot_faces.sort()
            clusters, cur = [], [shot_faces[0]]
            for f in shot_faces[1:]:
                if f[0] - cur[-1][0] > src_w * 0.15:
                    clusters.append(cur); cur = [f]
                else:
                    cur.append(f)
            clusters.append(cur)
            best = max(clusters, key=lambda c: sum(a for _, a in c))
            traj[s:e] = float(np.median([x for x, _ in best]))
        else:
            # No detectable face in this shot (capped/glasses side profiles beat
            # both cascades; wide two-shots put subjects at the edges where ANY
            # punch-in slices someone). Don't gamble: NaN = render this shot as
            # the FITTED-WIDE frame (full 16:9 over blur fill) — everyone stays
            # visible and it always looks intentional.
            traj[s:e] = np.nan
    return traj


# ---- 4. render frames with captions ---------------------------------------
_COVER_FEATHER_PX = 70          # gradient fade at the band's top edge (no hard 'box' line)
_cover_mask = None


def cover_source_captions(img):
    """Hide the source's burned-in bottom captions by covering the band
    [COVER_BAND_TOP, COVER_BAND_BOTTOM] with a heavily gaussian-blurred +
    darkened copy of that same region. The band's top edge is FEATHERED with an
    alpha gradient so it blends into the picture instead of reading as a hard
    'black box'. Mutates `img` (a full 1080x1920 PIL image)."""
    global _cover_mask
    top, bot = COVER_BAND_TOP, COVER_BAND_BOTTOM
    if bot <= top:
        return
    band = img.crop((0, top, W_OUT, bot))
    band = band.filter(ImageFilter.GaussianBlur(COVER_BLUR_RADIUS))
    band = ImageEnhance.Brightness(band).enhance(COVER_DARKEN)
    if _cover_mask is None:
        h = bot - top
        col = np.full(h, 255, dtype=np.uint8)
        f = min(_COVER_FEATHER_PX, h)
        col[:f] = np.linspace(0, 255, f).astype(np.uint8)
        _cover_mask = Image.fromarray(np.tile(col[:, None], (1, W_OUT)), "L")
    img.paste(band, (0, top), _cover_mask)


# NOTE: automatic caption-presence detection was attempted (brightness/edges,
# temporal variance, letter-component analysis) and FAILED validation against
# ground-truth segments 4/4 times: the huge glowing serif captions merge into
# un-letter-like blobs, and white clothing fakes text rows. Covering is therefore
# controlled per-source by clip.py's cover-sources memory, not a detector.


def _draw_text_with_shadow(d, xy, text, f, fill, stroke_width, stroke_fill, shadow=None):
    """d.text() with an optional soft drop-shadow pass underneath (spec's
    stroke.drop_shadow: offset + blur, drawn on a separate layer then composited
    so the blur doesn't bleed onto the crisp stroked glyph)."""
    if shadow:
        img = d._image
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ox, oy = shadow["offset"]
        a = int(255 * shadow["opacity"])
        ld.text((xy[0] + ox, xy[1] + oy), text, font=f,
                 fill=shadow["color"] + (a,), stroke_width=stroke_width,
                 stroke_fill=shadow["color"] + (a,))
        if shadow.get("blur"):
            layer = layer.filter(ImageFilter.GaussianBlur(shadow["blur"]))
        img.paste(layer, (0, 0), layer)
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def draw_caption(img, phrase, t, chunk_idx=0):
    """draw the caption chunk. Behavior branches on the module-level STYLE:

    classic    -> byte-identical to the original renderer: centered ~70% height,
                  active word (covering t) yellow, others white, 7px stroke.
    bold2026   -> spec-driven: ALL_CAPS (already applied by caller upstream, but
                  enforced here too), base color alternates primary/secondary per
                  CHUNK (chunk_idx, not per word — matches the decoded reference),
                  numbers/pain/power-word KEYWORD EMPHASIS overrides the base
                  color even when the word isn't active, heavier stroke + soft
                  drop shadow, positioned at spec.caption.position.y (clamped to
                  the safe-zone rect), auto-shrunk to max_width_pct_of_canvas.
    """
    d = ImageDraw.Draw(img)

    if STYLE == "classic":
        gap, size = 20, 88
        while size > 46:
            f = font(size)
            widths = [d.textlength(w["w"].upper(), font=f) for w in phrase]
            total = sum(widths) + gap * (len(phrase) - 1)
            if total <= W_OUT * 0.92:
                break
            size -= 4
        x = (W_OUT - total) / 2
        y = int(H_OUT * 0.70)
        for w, wid in zip(phrase, widths):
            active = w["start"] <= t <= w["end"]
            d.text((x, y), w["w"].upper(), font=f, fill=YELLOW if active else WHITE,
                   stroke_width=7, stroke_fill=STROKE)
            x += wid + gap
        return

    if STYLE == "plate":
        gap, size = 18, CAPTION_SIZE_PLATE
        max_w = min(W_OUT * CAPTION_MAX_WIDTH_PCT_BOLD2026, SAFE_X_MAX - SAFE_X_MIN) - 2 * PLATE_PAD_X
        while True:
            f = font(size)
            widths = [d.textlength(w["w"].upper(), font=f) for w in phrase]
            total = sum(widths) + gap * (len(phrase) - 1)
            if total <= max_w or size <= CAPTION_SIZE_MIN_BOLD2026:
                break
            size -= 4
        ups = [w["w"].upper() for w in phrase]
        emph = _pick_plate_emph(ups)
        x = (W_OUT - total) / 2
        y = max(SAFE_Y_MIN, min(SAFE_Y_MAX - size, CAPTION_Y_BOLD2026))
        tb = d.textbbox((0, 0), "AY", font=f)
        bd = ImageDraw.Draw(img, "RGBA")
        bd.rounded_rectangle([x - PLATE_PAD_X, y + tb[1] - PLATE_PAD_Y, x + total + PLATE_PAD_X, y + tb[3] + PLATE_PAD_Y],
                             radius=PLATE_RADIUS, fill=PLATE_FILL + (255,), outline=PLATE_OUTLINE + (255,), width=PLATE_OUTLINE_W)
        done = False
        for up, wid in zip(ups, widths):
            hot = (not done) and up == emph
            done = done or hot
            bd.text((x, y), up, font=f, fill=(PLATE_EMPH if hot else WHITE) + (255,))
            x += wid + gap
        return

    # ---- bold2026 + explainer (shared spec layout) -------------------------
    gap = 22
    size = CAPTION_SIZE_PX_BOLD2026
    max_w = W_OUT * CAPTION_MAX_WIDTH_PCT_BOLD2026
    max_w = min(max_w, SAFE_X_MAX - SAFE_X_MIN)          # clamp to safe-zone rect
    while size > CAPTION_SIZE_MIN_BOLD2026:
        f = font(size)
        widths = [d.textlength(w["w"].upper(), font=f) for w in phrase]
        total = sum(widths) + gap * (len(phrase) - 1)
        if total <= max_w:
            break
        size -= 4

    is_explainer = (STYLE == "explainer")
    # base fill: explainer = plain white (the BOX carries emphasis); bold2026 =
    # per-chunk alternating primary/secondary (spec.caption.active_word.color_alternate)
    base_color = WHITE if is_explainer else (
        CAPTION_COLOR_PRIMARY if chunk_idx % 2 == 0 else CAPTION_COLOR_SECONDARY)
    # cap 1 emphasized word per chunk (spec.emphasis_words.max_emphasized_words_per_chunk)
    emphasized_done = False
    x = (W_OUT - total) / 2
    x = max(SAFE_X_MIN, min(SAFE_X_MAX - total, x))
    y = CAPTION_Y_BOLD2026
    y = max(SAFE_Y_MIN, min(SAFE_Y_MAX - size, y))
    for w, wid in zip(phrase, widths):
        active = w["start"] <= t <= w["end"]
        up = w["w"].upper()
        emph_color = None if emphasized_done else _classify_emphasis(up)
        if emph_color is not None:
            emphasized_done = True
        if is_explainer:
            if emph_color is not None:
                # solid box behind the ONE emphasis word: red for pain/biggest-beat,
                # yellow otherwise; text color flips for contrast on the fill
                box = EXPLAINER_BOX_RED if emph_color == EMPHASIS_COLOR_PAIN else EXPLAINER_BOX_YELLOW
                txt = (255, 255, 255) if box == EXPLAINER_BOX_RED else EXPLAINER_BOX_TEXT_ON
                bd = ImageDraw.Draw(img, "RGBA")
                bb = bd.textbbox((x, y), up, font=f)
                bd.rounded_rectangle([bb[0] - 10, bb[1] - 6, bb[2] + 10, bb[3] + 8],
                                     radius=8, fill=box + (255,))
                bd.text((x, y), up, font=f, fill=txt)
            else:
                _draw_text_with_shadow(d, (x, y), up, f, base_color,
                                       CAPTION_STROKE_W_BOLD2026, STROKE,
                                       shadow=CAPTION_SHADOW_BOLD2026)
            x += wid + gap
            continue
        fill = emph_color if emph_color is not None else base_color
        # OPTIONAL scale-pop on the active word (spec: OFF by default, ship as a
        # flag-able enhancement) — CAPTION_SCALE_POP_ENABLED toggles it.
        draw_f, draw_wid = f, wid
        draw_x = x
        if active and CAPTION_SCALE_POP_ENABLED:
            pop_size = int(round(size * CAPTION_SCALE_POP))
            draw_f = font(pop_size)
            draw_wid = d.textlength(up, font=draw_f)
            draw_x = x - (draw_wid - wid) / 2   # keep visually centered on its slot
        _draw_text_with_shadow(d, (draw_x, y), up, draw_f, fill, CAPTION_STROKE_W_BOLD2026,
                                STROKE, shadow=CAPTION_SHADOW_BOLD2026)
        x += wid + gap


def draw_headline(img, headline, hl_font):
    """draw the persistent on-screen hook/headline. Branches on module-level STYLE:

    classic  -> byte-identical to the original: top third (~11% down), white,
                7px stroke, no background.
    bold2026 -> spec-driven: bigger (caller passes a font sized per
                HEADLINE_SIZE_PX_BOLD2026), positioned at the hook y (450px,
                clamped inside the safe-zone rect), heavier stroke + soft
                shadow, optional semi-opaque background pill for legibility
                over unpredictable footage, width capped at
                HEADLINE_MAX_WIDTH_PCT_BOLD2026 of canvas (safe-zone clamped).
    """
    dd = ImageDraw.Draw(img)

    if STYLE != "bold2026":
        lines = _wrap(dd, headline.upper(), hl_font, W_OUT - 120)
        yy = int(H_OUT * 0.11)
        for ln in lines:
            b = dd.textbbox((0, 0), ln, font=hl_font)
            dd.text(((W_OUT - (b[2] - b[0])) // 2, yy), ln, font=hl_font,
                    fill=WHITE, stroke_width=7, stroke_fill=STROKE)
            yy += int((b[3] - b[1]) * 1.5)
        return

    # ---- bold2026 ----------------------------------------------------------
    max_w = min(W_OUT * HEADLINE_MAX_WIDTH_PCT_BOLD2026, SAFE_X_MAX - SAFE_X_MIN)
    lines = _wrap(dd, headline.upper(), hl_font, int(max_w))
    line_h = int((dd.textbbox((0, 0), "AY", font=hl_font)[3]) * 1.35)
    block_h = line_h * len(lines)
    yy = HEADLINE_Y_HOOK_BOLD2026
    yy = max(SAFE_Y_MIN, min(SAFE_Y_MAX - block_h, yy))

    if HEADLINE_PILL_BOLD2026["enabled"]:
        widths = [dd.textbbox((0, 0), ln, font=hl_font)[2] for ln in lines]
        pad = HEADLINE_PILL_BOLD2026["padding"]
        pill_w = max(widths) + pad * 2
        pill_x0 = max(SAFE_X_MIN, (W_OUT - pill_w) / 2)
        pill_x1 = min(SAFE_X_MAX, pill_x0 + pill_w)
        pill_y0 = yy - pad
        pill_y1 = yy + block_h - (line_h - int(dd.textbbox((0, 0), 'AY', font=hl_font)[3])) + pad
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        a = int(255 * HEADLINE_PILL_BOLD2026["opacity"])
        od.rounded_rectangle([pill_x0, pill_y0, pill_x1, pill_y1],
                              radius=HEADLINE_PILL_BOLD2026["radius"],
                              fill=HEADLINE_PILL_BOLD2026["color"] + (a,))
        img.paste(overlay, (0, 0), overlay)
        dd = ImageDraw.Draw(img)

    for ln in lines:
        b = dd.textbbox((0, 0), ln, font=hl_font)
        x = (W_OUT - (b[2] - b[0])) // 2
        x = max(SAFE_X_MIN, min(SAFE_X_MAX - (b[2] - b[0]), x))
        _draw_text_with_shadow(dd, (x, yy), ln, hl_font, HEADLINE_COLOR_BOLD2026,
                                HEADLINE_STROKE_W_BOLD2026, STROKE,
                                shadow=HEADLINE_SHADOW_BOLD2026)
        yy += line_h


_PLATE_SKIP = {"you're", "you", "your", "going", "that's", "that", "this", "these", "those", "with", "from", "they",
               "they're", "we're", "i'm", "it's", "just", "really", "have", "been", "what", "when", "where", "which",
               "there", "their", "about", "would", "could", "should", "gonna", "wanna", "into", "then", "also", "here's"}


def _pick_plate_emph(words):
    """PLATE: the ONE yellow word. A number/stat or power/pain word first, then the longest real word (4+ letters,
    not a pronoun or helper verb), then none: an all-filler chunk ("YOU'RE GOING TO") stays white."""
    for w in words:
        if _classify_emphasis(w) is not None:
            return w
    content = [w for w in words if len(w.strip(".,!?:;\"'")) >= 4 and w.strip(".,!?:;\"'").lower() not in _PLATE_SKIP]
    if content:
        return max(content, key=len)
    short = [w for w in words if w.strip(".,!?:;\"'").lower() not in _PLATE_SKIP | {"a", "an", "the", "to", "of", "and", "or", "is", "it", "in", "on", "at", "i"}]
    return short[-1] if short else ""


def _pick_banner_emph(words):
    """Choose the ONE banner word to swap to yellow: prefer a number/stat, then a
    pain/power word, else the longest content word."""
    for w in words:
        if _classify_emphasis(w) is not None:
            return w
    content = [w for w in words if len(w.strip(".,!?:;\"'")) >= 4]
    return max(content, key=len) if content else (words[-1] if words else "")


def draw_red_banner(img, text, banner_font):
    """EXPLAINER: pin a bold white-on-red hook banner across the top (inside the
    reserved top-18% band), one key word swapped to yellow, <=2 lines. Meant to be
    drawn only for the first EXPLAINER_BANNER_SECONDS, then removed."""
    d = ImageDraw.Draw(img, "RGBA")
    words = text.upper().split()
    emph = _pick_banner_emph(words)
    max_w = int(W_OUT * 0.90)
    lines = _wrap(d, text.upper(), banner_font, max_w)[:2]
    lh = int(d.textbbox((0, 0), "AY", font=banner_font)[3] * 1.28)
    pad = EXPLAINER_BANNER_PAD
    block_w = min(W_OUT - 40, max(d.textbbox((0, 0), ln, font=banner_font)[2] for ln in lines) + pad * 2)
    block_h = lh * len(lines) + pad * 2
    x0 = (W_OUT - block_w) // 2
    y0 = EXPLAINER_BANNER_TOP
    d.rounded_rectangle([x0, y0, x0 + block_w, y0 + block_h], radius=14,
                        fill=EXPLAINER_BANNER_BG + (255,))
    yy = y0 + pad
    for ln in lines:
        toks = ln.split()
        widths = [d.textlength(tok + " ", font=banner_font) for tok in toks]
        total = sum(widths)
        x = (W_OUT - total) / 2
        for tok, wdt in zip(toks, widths):
            fill = EXPLAINER_BANNER_EMPH if tok.strip(".,!?:;\"'") == emph.strip(".,!?:;\"'") else EXPLAINER_BANNER_TEXT
            d.text((x, yy), tok, font=banner_font, fill=fill)
            x += wdt
        yy += lh


def draw_end_card(img, handle=EXPLAINER_HANDLE):
    """EXPLAINER: soft end-card overlay for the last seconds — dim the frame and
    center the handle + FOLLOW. (A full animated end card is a manual-asset upgrade;
    this burns in the tie-in cleanly without changing clip duration/audio sync.)"""
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W_OUT, H_OUT], fill=(0, 0, 0, 150))
    hf = font(96)
    ff = font(64)
    hb = d.textbbox((0, 0), handle, font=hf)
    cy = H_OUT // 2 - 80
    d.text(((W_OUT - (hb[2] - hb[0])) // 2, cy), handle, font=hf,
           fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    pill = "FOLLOW"
    pb = d.textbbox((0, 0), pill, font=ff)
    pw, ph = pb[2] - pb[0], pb[3] - pb[1]
    px0 = (W_OUT - pw) // 2 - 34
    py0 = cy + 150
    d.rounded_rectangle([px0, py0, px0 + pw + 68, py0 + ph + 40], radius=44,
                        fill=EXPLAINER_BANNER_BG + (255,))
    d.text(((W_OUT - pw) // 2, py0 + 14), pill, font=ff, fill=(255, 255, 255))


def fit_wide(fr):
    """Fit the FULL 16:9 frame into the 9:16 canvas: scaled to 1080 wide, centered
    at ~40% height, over a blurred+darkened cover-fill of the same frame. Used for
    shots where no face is detectable (wide two-shots, capped side profiles) —
    a punch-in there gambles with slicing someone off-frame."""
    src_h, src_w = fr.shape[:2]
    # cover-fill background: scale to fill 1080x1920 (center-crop), blur, darken
    scale = max(W_OUT / src_w, H_OUT / src_h)
    big = cv2.resize(fr, (int(src_w * scale) + 1, int(src_h * scale) + 1))
    y0 = (big.shape[0] - H_OUT) // 2
    x0 = (big.shape[1] - W_OUT) // 2
    bg = big[y0:y0 + H_OUT, x0:x0 + W_OUT]
    bg = cv2.GaussianBlur(bg, (0, 0), 30)
    bg = (bg * 0.42).astype(np.uint8)
    # foreground: full frame at 1080 wide
    fg_h = int(round(src_h * (W_OUT / src_w)))
    fg = cv2.resize(fr, (W_OUT, fg_h))
    top = int(H_OUT * 0.40) - fg_h // 2
    top = max(0, min(H_OUT - fg_h, top))
    bg[top:top + fg_h, :] = fg
    return bg


def render(clip_mp4, phrases, crop_x, silent_out, headline=None, captions=True,
           cover_captions=False):
    """crop_x may be a scalar (static crop) or a per-frame numpy trajectory
    (face-tracking; NaN entries mean 'render this frame fitted-wide'). The 608px
    crop window is clamped to stay inside [0, src_w - crop_w]."""
    cap = cv2.VideoCapture(clip_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    # 9:16 crop width from the REAL source height — hardcoding 608 (correct only
    # for 1080p) vertically stretched every 720p source by 1.5x
    crop_w = int(round(src_h * 9 / 16))
    per_frame = hasattr(crop_x, "__len__")                   # numpy trajectory vs scalar
    if not per_frame:
        x0_static = int(max(0, min(src_w - crop_w, crop_x - crop_w / 2)))
    vw = cv2.VideoWriter(silent_out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W_OUT, H_OUT))
    hl_font = font(HEADLINE_SIZE_PX_BOLD2026 if STYLE == "bold2026" else 64)
    banner_font = font(EXPLAINER_BANNER_SIZE)                 # explainer red-banner font
    dur_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps if fps else 0
    idx = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        t = idx / fps
        fitted = False
        if per_frame:                                        # smoothed face-tracking center
            cx = crop_x[idx] if idx < len(crop_x) else crop_x[-1]
            fitted = bool(np.isnan(cx))
        if fitted:                                           # no-face shot -> fitted wide
            crop = fit_wide(fr)
        else:
            x0 = (int(max(0, min(src_w - crop_w, cx - crop_w / 2)))
                  if per_frame else x0_static)
            crop = fr[0:src_h, x0:x0 + crop_w]
            crop = cv2.resize(crop, (W_OUT, H_OUT), interpolation=cv2.INTER_CUBIC)
        img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        if cover_captions:                                   # hide source's burned-in captions first
            cover_source_captions(img)
        if STYLE == "explainer":                             # red hook banner, first 3s only
            if headline and t < EXPLAINER_BANNER_SECONDS:
                draw_red_banner(img, headline, banner_font)
        elif headline:                                       # persistent on-screen hook, top third
            draw_headline(img, headline, hl_font)
        if captions:
            for ci, ph in enumerate(phrases):
                if ph[0]["start"] <= t <= ph[-1]["end"]:
                    draw_caption(img, ph, t, chunk_idx=ci)
                    break
        if STYLE == "explainer" and dur_total and t >= dur_total - EXPLAINER_ENDCARD_SECONDS:
            draw_end_card(img)                               # soft end card, last 2s
        vw.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        idx += 1
    cap.release(); vw.release()


def render_horizontal(clip_mp4, phrases, silent_out, headline=None, captions=True,
                       cover_captions=False):
    """Horizontal (16:9, 1920x1080) render path: NO CROP, NO face tracking.
    Full source frame -> scale to 1920x1080 (letterbox-pad with black bars only
    if the source isn't already 16:9; normal 16:9 sources get a plain resize) ->
    cover band (if enabled) -> headline -> captions. Everything downstream
    (cut+boundary-refine, whisper captions, loudnorm mux) is identical to the
    vertical path — only this frame pipeline differs."""
    print("[render] horizontal: full frame, no crop", file=sys.stderr)
    cap = cv2.VideoCapture(clip_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or W_OUT
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or H_OUT
    vw = cv2.VideoWriter(silent_out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W_OUT, H_OUT))
    hl_font = font(HEADLINE_SIZE_PX_BOLD2026 if STYLE == "bold2026" else 64)
    banner_font = font(EXPLAINER_BANNER_SIZE_H)              # explainer red-banner font (16:9)
    dur_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps if fps else 0

    src_aspect = src_w / src_h if src_h else (16 / 9)
    out_aspect = W_OUT / H_OUT
    is_169 = abs(src_aspect - out_aspect) < 0.01

    idx = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        t = idx / fps
        if is_169:
            frame = cv2.resize(fr, (W_OUT, H_OUT), interpolation=cv2.INTER_CUBIC)
        else:
            # letterbox-pad: fit the full frame inside 1920x1080 with black bars
            # (never crop content in horizontal mode)
            scale = min(W_OUT / src_w, H_OUT / src_h)
            fw, fh = int(round(src_w * scale)), int(round(src_h * scale))
            fitted = cv2.resize(fr, (fw, fh), interpolation=cv2.INTER_CUBIC)
            frame = np.zeros((H_OUT, W_OUT, 3), dtype=np.uint8)
            x0, y0 = (W_OUT - fw) // 2, (H_OUT - fh) // 2
            frame[y0:y0 + fh, x0:x0 + fw] = fitted
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if cover_captions:                                   # hide source's burned-in captions first
            cover_source_captions(img)
        if STYLE == "explainer":                             # red hook banner, first 3s only
            if headline and t < EXPLAINER_BANNER_SECONDS:
                draw_red_banner(img, headline, banner_font)
        elif headline:                                       # persistent on-screen hook, top of frame
            draw_headline(img, headline, hl_font)
        if captions:
            for ci, ph in enumerate(phrases):
                if ph[0]["start"] <= t <= ph[-1]["end"]:
                    draw_caption(img, ph, t, chunk_idx=ci)
                    break
        if STYLE == "explainer" and dur_total and t >= dur_total - EXPLAINER_ENDCARD_SECONDS:
            draw_end_card(img)                               # soft end card, last 2s
        vw.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        idx += 1
    cap.release(); vw.release()


def _wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=f)[2] <= maxw:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--headline", default=None, help="persistent on-screen hook text")
    ap.add_argument("--model", default="base", choices=list(MODELS))
    ap.add_argument("--no-captions", action="store_true",
                    help="skip karaoke captions (for source that is already captioned); keeps the headline")
    ap.add_argument("--cover-source-captions", action="store_true",
                    help="hide the source's burned-in bottom captions with a blurred+darkened "
                         "lower-third band before drawing our karaoke caption")
    ap.add_argument("--music", default=None, help="path to an approved royalty-free track to duck under the voice")
    ap.add_argument("--music-vol", type=float, default=0.18, help="music bed level before ducking (0-1)")
    ap.add_argument("--expect-first", default=None,
                    help="first few words the clip should OPEN on; the cut snaps to their "
                         "spoken onset (fixes early-skewed auto-sub starts bleeding in the "
                         "previous sentence)")
    ap.add_argument("--expect-last", default=None,
                    help="last few words the clip should END on; the cut extends to their true end")
    ap.add_argument("--style", default="classic", choices=["bold2026", "classic", "explainer", "plate"],
                    help="visual style: 'classic' (default) = clean white ALL-CAPS headline "
                         "at top, thin stroke, no box, no shadow (the -oNRtyqu 'HigherUp' look "
                         "OB approved); 'bold2026' = spec-driven Anton karaoke captions + "
                         "big restyled headline per ob-moments/data/style-spec.json; "
                         "'plate' = 2-3 word Anton chunks on a black plate with a thin white "
                         "outline, one emphasis word yellow (decoded 2026-10-20)")
    ap.add_argument("--aspect", default="vertical", choices=["vertical", "horizontal"],
                    help="'vertical' (default) = 1080x1920 face-tracked punch-in crop "
                         "(the original Reel look); 'horizontal' = 1920x1080 full frame, "
                         "NO crop and NO face tracking")
    a = ap.parse_args()

    global STYLE
    STYLE = a.style
    # geometry MUST be set before any drawing (draw_caption/draw_headline/fit_wide/
    # cover_source_captions all read the module globals set_aspect() reassigns)
    set_aspect(a.aspect)

    tmp = tempfile.mkdtemp(prefix="obclip_")
    wide = os.path.join(tmp, "wide.mp4")
    clip = os.path.join(tmp, "clip.mp4")
    wav = os.path.join(tmp, "wide.wav")
    silent = os.path.join(tmp, "silent.mp4")

    if a.expect_first or a.expect_last:
        # boundary-refined path: pad the cut, whisper it, snap to true word onsets,
        # then cut the real clip. The whisper pass is reused for the captions.
        pad_pre, pad_post = 2.5, 2.5
        ws = max(0.0, a.start - pad_pre)
        print("[render] 1/5 cut wide segment + refine boundaries", file=sys.stderr)
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
        print(f"[render]     refined: start {ws + rs:.2f}s end {ws + re_:.2f}s "
              f"(was {a.start:.2f}-{a.end:.2f})", file=sys.stderr)
        sh(["ffmpeg", "-y", "-ss", str(rs), "-to", str(re_), "-i", wide,
            "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", clip])
        if a.no_captions:
            phrases = []
            print("[render] 2/5 captions skipped (--no-captions)", file=sys.stderr)
        else:
            kept = [{"w": w["w"], "start": w["start"] - rs, "end": w["end"] - rs}
                    for w in words if w["start"] >= rs - 0.05 and w["end"] <= re_ + 0.05]
            phrases = group_phrases(kept)
            print(f"[render] 2/5 captions from refine pass ({len(kept)} words)", file=sys.stderr)
    else:
        print("[render] 1/5 cut segment", file=sys.stderr)
        sh(["ffmpeg", "-y", "-ss", str(a.start), "-to", str(a.end), "-i", a.video,
            "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", clip])
        if a.no_captions:
            phrases = []
            print("[render] 2/5 captions skipped (--no-captions)", file=sys.stderr)
        else:
            print("[render] 2/5 transcribe words", file=sys.stderr)
            sh(["ffmpeg", "-y", "-i", clip, "-ar", "16000", "-ac", "1", wav])
            phrases = group_phrases(transcribe_words(wav, a.model))
    if a.aspect == "horizontal":
        # NO CROP, NO face tracking: full source frame, scaled/letterboxed to
        # 1920x1080. Skip shot_locked/track/fit_wide entirely.
        print("[render] 3/5 horizontal: skipping crop + face tracking", file=sys.stderr)
        render_horizontal(clip, phrases, silent, headline=a.headline,
                           captions=not a.no_captions,
                           cover_captions=a.cover_source_captions)
    else:
        print(f"[render] 3/5 shot-locked crop ({len(phrases)} caption phrases)", file=sys.stderr)
        # shot-locked is the default: static within each source shot, hard snap at
        # cuts — what actually reads 'smooth' (continuous tracking oscillated between
        # guests on multicam podcasts and turned source cuts into swooshy pans)
        traj = shot_locked_center_x(clip)
        if traj is None:
            traj = track_center_x(clip)                          # legacy continuous tracking
        if traj is not None:
            cx = traj
            d = np.diff(traj)
            n_shots = int(np.count_nonzero(np.abs(d[~np.isnan(d)]) > 1)) + 1
            n_wide = int(np.isnan(traj).sum())
            span = (f"crop_x {np.nanmin(traj):.0f}->{np.nanmax(traj):.0f}"
                    if not np.all(np.isnan(traj)) else "all fitted-wide")
            print(f"[render] 4/5 render frames (shot-locked, {n_shots} shot(s), "
                  f"{n_wide} fitted-wide frame(s), {span})", file=sys.stderr)
        else:                                                    # cv2/Haar unavailable -> static fallback
            cx = crop_center_x(clip)
            print(f"[render] 4/5 render frames (static crop_x={cx:.0f})", file=sys.stderr)
        render(clip, phrases, cx, silent, headline=a.headline, captions=not a.no_captions,
               cover_captions=a.cover_source_captions)
    if a.music:
        print("[render] 5/5 mux + duck music under voice + loudnorm -14 LUFS + x264", file=sys.stderr)
        # music ducks whenever the voice speaks (sidechaincompress), then mix, then normalize
        fc = (f"[2:a]volume={a.music_vol}[mus];"
              f"[mus][1:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck];"
              f"[1:a][duck]amix=inputs=2:duration=first:dropout_transition=0[mix];"
              f"[mix]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
        sh(["ffmpeg", "-y", "-i", silent, "-i", clip, "-stream_loop", "-1", "-i", a.music,
            "-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-shortest",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out])
    else:
        print("[render] 5/5 mux audio + loudnorm -14 LUFS + x264", file=sys.stderr)
        sh(["ffmpeg", "-y", "-i", silent, "-i", clip, "-map", "0:v", "-map", "1:a",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out])
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", a.out],
                         capture_output=True, text=True).stdout.strip()
    print(f"[render] done -> {a.out} ({dur}s)", file=sys.stderr)
    try:   # 2026-10-28: the QC gate runs on every render (OB: "wire it in"); deliver.py keeps a FAIL out of his AirDrop folders
        sys.path.insert(0, os.path.expanduser("~/ob-editor/bin")); import qc_gate; qc_gate.after_render(a.out)
    except Exception as e: print("qc_gate not run:", e, flush=True)


if __name__ == "__main__":
    main()
