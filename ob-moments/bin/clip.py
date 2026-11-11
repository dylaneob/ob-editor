#!/usr/bin/env python3
"""
clip.py — the one command. URL or file in → finished Instagram clips out.

    python3 bin/clip.py "<youtube-url>"          # or a local .mp4/.mov path
    python3 bin/clip.py video.mp4 --n 4          # how many clips (default 3)

It ingests, transcribes, finds the best moments, and renders each as a finished
9:16 vertical clip with a locked-on hook headline + karaoke captions, then writes
a folder of ready-to-post clips + a SUMMARY.md (hook, caption, music-to-add).

Options:
  --n N            number of clips to make (default 3)
  --no-captions    skip karaoke captions (use for already-captioned footage)
  --music TRACK    burn an approved royalty-free track under the voice (else voice-first)
  --llm            force the claude/API scorer (sharper picks)
  --no-llm         force the deterministic regex scorer (no LLM call)

By default the LLM scorer is used automatically when a backend is available
(claude CLI logged in, or ANTHROPIC_API_KEY set); otherwise it falls back to the
deterministic regex picker and says so.
"""
import os, sys, re, json, subprocess, argparse, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preflight import run_preflight

OBM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(OBM, "bin")
WORK = os.path.join(OBM, "work")
RENDER = os.path.expanduser("~/ob-clipper/bin/render_clip.py")
OUTROOT = os.path.expanduser("~/ob-clipper/out")
YTDL_FMT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]"
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".webm"}
WHISPER_MODEL = os.path.expanduser("~/.whisper-models/ggml-large-v3-turbo.bin")   # 2026-11-03 M5 Pro (was base.en)


def log(msg):
    print(f"[clip] {msg}", file=sys.stderr)


def run(cmd, **kw):
    """Run a step. On failure, surface the tool's own stderr (not a generic line)
    so a broken ingest/render is actually debuggable."""
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        tail = ""
        if kw.get("capture_output") and getattr(r, "stderr", None):
            tail = "\n" + (r.stderr[-1500:] if isinstance(r.stderr, str) else "")
        sys.exit(f"step failed: {' '.join(map(str, cmd[:4]))} ...{tail}")
    return r


def has_audio(path):
    """True if the container has at least one audio stream."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", path],
        capture_output=True, text=True)
    return bool(r.stdout.strip())


def llm_backend_available():
    """Mirror score.py's _llm_call backend probe: LLM is usable when the claude
    CLI answers a trivial prompt (rc 0, non-empty, not 'Not logged in'), OR when
    ANTHROPIC_API_KEY is set. Returns (available: bool, how: str)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True, "ANTHROPIC_API_KEY"
    try:
        out = subprocess.run(["claude", "-p", "ok"], capture_output=True, text=True,
                             timeout=30)
        txt = out.stdout.strip()
        if out.returncode == 0 and txt and not txt.startswith("Not logged in"):
            return True, "claude CLI"
    except Exception:
        pass
    return False, ""


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "clip"


def ingest(src):
    """Return (video_path, srt_path, video_id). Reuses cached downloads/transcripts."""
    os.makedirs(WORK, exist_ok=True)
    if re.match(r"https?://", src):
        vid = subprocess.run(["yt-dlp", "--get-id", src], capture_output=True, text=True).stdout.strip()
        if not vid:
            # yt-dlp --get-id can fail on rate-limit/bot-check even when the video
            # is already cached — parse the 11-char id straight from the URL so we
            # can reuse the local download instead of re-fetching.
            m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|/live/)([A-Za-z0-9_-]{11})", src)
            vid = m.group(1) if m else "yt"
        video = os.path.join(WORK, f"{vid}.mp4")
        alt = os.path.expanduser(f"~/ob-clipper/work/{vid}.mp4")
        if not os.path.exists(video) and os.path.exists(alt):
            video = alt
        if not os.path.exists(video):
            log(f"downloading {vid} …")
            run(["yt-dlp", "-f", YTDL_FMT, "--merge-output-format", "mp4", "-o", video, src])
        srt = os.path.join(WORK, f"{vid}.en.srt")
        if os.path.exists(srt) and os.path.getsize(srt) > 0:
            log(f"reusing cached transcript {os.path.basename(srt)}")
        else:
            log("pulling transcript …")
            run(["yt-dlp", "--skip-download", "--write-auto-sub", "--sub-lang", "en",
                 "--convert-subs", "srt", "-o", os.path.join(WORK, "%(id)s.%(ext)s"), src])
        return video, srt, vid

    # ---- local file → whisper transcript -----------------------------------
    src = os.path.expanduser(src)
    if not os.path.exists(src):
        sys.exit(f"[clip] file not found: {src}")
    ext = os.path.splitext(src)[1].lower()
    if ext not in VIDEO_EXTS:
        sys.exit(f"[clip] unsupported file type '{ext}'. "
                 f"Give a URL or a {', '.join(sorted(VIDEO_EXTS))} file.")
    video = os.path.abspath(src)
    vid = slugify(os.path.splitext(os.path.basename(src))[0])
    log(f"local file: {video}")

    srt = os.path.join(WORK, f"{vid}.en.srt")
    if os.path.exists(srt) and os.path.getsize(srt) > 0:
        log(f"reusing cached transcript {os.path.basename(srt)}")
        return video, srt, vid

    if not shutil.which("whisper-cli"):
        sys.exit("[clip] whisper-cli not found on PATH (needed to transcribe local files).")
    if not os.path.exists(WHISPER_MODEL):
        sys.exit(f"[clip] whisper model missing: {WHISPER_MODEL}")
    if not has_audio(video):
        sys.exit(f"[clip] '{os.path.basename(video)}' has no audio track — "
                 "nothing to transcribe. Use footage with a voice track, "
                 "or supply your own <id>.en.srt in work/.")

    log("transcribing with whisper (local file) …")
    wav = os.path.join(WORK, f"{vid}.wav")
    # -of takes a path WITHOUT extension; '-osrt' then writes '<of>.srt'.
    # srt ends in '.en.srt', so srt[:-4] == '<vid>.en' -> whisper writes '<vid>.en.srt'. (verified)
    of_stem = srt[:-4]
    try:
        run(["ffmpeg", "-y", "-i", video, "-vn", "-ar", "16000", "-ac", "1", wav],
            capture_output=True, text=True)
        run(["whisper-cli", "-m", WHISPER_MODEL, "-f", wav, "-l", "en", "-np",
             "-osrt", "-of", of_stem], capture_output=True, text=True)
    finally:
        if os.path.exists(wav):
            os.remove(wav)

    # whisper writes a 0-byte SRT when the audio has no recognizable speech.
    if not os.path.exists(srt) or os.path.getsize(srt) == 0:
        sys.exit(f"[clip] whisper found no speech in '{os.path.basename(video)}' "
                 "(empty transcript) — no clips can be cut from silent/music-only footage.")
    log(f"transcript ready → {os.path.basename(srt)}")
    return video, srt, vid


def pick(moments, n):
    """Top gated moments, diversified so we don't ship 4 of the same engagement lever."""
    gated = [m for m in moments if m.get("gate_passed")]
    chosen, per_lever = [], {}
    for m in gated:
        lever = m.get("engagement_lever", "?")
        if per_lever.get(lever, 0) >= max(1, n // 2 + 1):
            continue
        chosen.append(m); per_lever[lever] = per_lever.get(lever, 0) + 1
        if len(chosen) >= n:
            break
    for m in gated:                                   # backfill if diversity left us short
        if len(chosen) >= n:
            break
        if m not in chosen:
            chosen.append(m)
    return chosen[:n]


def mmss(t):
    return f"{int(t)//60:02d}:{int(t)%60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="youtube url or local video file")
    ap.add_argument("--n", type=int, default=None,
                    help="how many clips (scorer path defaults to 5). With --picks-json, "
                         "renders ALL provided picks unless --n is explicitly set.")
    ap.add_argument("--score-only", action="store_true",
                    help="download+transcribe+score then STOP (writes moments.json, "
                         "no render) — for feeding an external viral-judge pass")
    ap.add_argument("--top", type=int, default=15,
                    help="how many scored candidate moments to keep in moments.json "
                         "(pool size for an external judge pass; default 15)")
    ap.add_argument("--picks-json", default=None,
                    help="path to a JSON list of pre-selected moment dicts "
                         "(start/end/title/onscreen_hook/hook_line/text). When set, "
                         "SKIPS scoring/picking and renders exactly these moments in "
                         "order — used to drive the render from an external viral-judge "
                         "pass (workflow/LLM) instead of the deterministic scorer.")
    ap.add_argument("--no-captions", action="store_true")
    cov = ap.add_mutually_exclusive_group()
    cov.add_argument("--cover", dest="cover", action="store_true", default=None,
                     help="blur-cover the source's burned-in bottom captions "
                          "(use for OB's edited main-channel videos)")
    cov.add_argument("--no-cover", dest="cover", action="store_false",
                     help="never cover (clean sources like guest podcasts)")
    ap.add_argument("--music", default=None)
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--llm", dest="llm", action="store_true", default=None,
                     help="force the LLM scorer (sharper picks)")
    grp.add_argument("--no-llm", dest="llm", action="store_false",
                     help="force the deterministic regex scorer")
    ap.add_argument("--force", action="store_true",
                    help="render even if the preflight quality gate fails "
                         "(defects will still be printed, just not enforced)")
    ap.add_argument("--format", default="both", choices=["vertical", "horizontal", "both"],
                    help="'vertical' (default look, 9:16 face-tracked crop), "
                         "'horizontal' (16:9 full frame, no crop), or 'both' "
                         "(default) — renders one file per orientation per clip")
    a = ap.parse_args()

    video, srt, vid = ingest(a.src)

    # Cover decision comes from per-source memory (auto-detection failed ground
    # truth 4/4 — see render_clip.py note). Explicit --cover/--no-cover overrides
    # AND is remembered for this source; unseen sources default to clean + a hint.
    cover_db_path = os.path.join(OBM, "data", "cover-sources.json")
    try:
        cover_db = json.load(open(cover_db_path))
    except Exception:
        cover_db = {}
    if a.cover is not None:
        cover = a.cover
        cover_db[vid] = cover
        os.makedirs(os.path.dirname(cover_db_path), exist_ok=True)
        json.dump(cover_db, open(cover_db_path, "w"), indent=1)
        log(f"cover band {'ON' if cover else 'OFF'} (remembered for {vid})")
    elif vid in cover_db:
        cover = cover_db[vid]
        log(f"cover band {'ON' if cover else 'OFF'} (remembered)")
    else:
        cover = False
        log("cover band OFF (new source). If this footage has burned-in captions "
            "at the bottom, re-run with --cover (remembered per source).")

    # Decide the scorer: honor an explicit --llm/--no-llm; otherwise auto-detect.
    if a.llm is None:
        use_llm, how = llm_backend_available()
        if use_llm:
            log(f"scorer: LLM ({how}) — sharper picks. Override with --no-llm.")
        else:
            log("scorer: deterministic fallback (regex baseline) — no LLM backend "
                "found. For sharper picks, log in with `claude` or set "
                "ANTHROPIC_API_KEY, or pass --llm.")
    else:
        use_llm = a.llm
        log(f"scorer: {'LLM (forced --llm)' if use_llm else 'deterministic (forced --no-llm)'}")

    mpath = os.path.join(os.path.dirname(srt), f"{vid}.moments.json")
    if a.picks_json:
        # External viral-judge pass drives the render: use these moments verbatim,
        # in order, skipping scoring/picking entirely.
        picks = json.load(open(a.picks_json))
        if isinstance(picks, dict):
            picks = picks.get("picks", picks.get("moments", []))
        picks = picks[: a.n] if a.n else picks
        # enrich with music beds if the caller didn't supply them (best-effort;
        # music.py operates on a moments.json, so stage the picks through one)
        # music beds are optional (added in-app, never burned in) — skip enrichment
        # here so a music.py hiccup can't block a picks-driven render; music.md can
        # be generated separately if wanted.
        log(f"using {len(picks)} pre-selected pick(s) from {os.path.basename(a.picks_json)} "
            "(external viral-judge pass — scorer skipped)")
        if not picks:
            sys.exit("[clip] --picks-json contained no moments.")
    else:
        log("finding the best moments …")
        # --flag=value form: YouTube ids can START WITH A DASH ('-oNRtyqu-vo'), which
        # argparse otherwise parses as a new flag ("expected one argument")
        score_cmd = ["python3", os.path.join(BIN, "score.py"), srt, f"--id={vid}",
                     "--top", str(a.top)]
        if not use_llm:
            score_cmd.append("--no-llm")
        run(score_cmd, capture_output=True, text=True)
        if a.score_only:
            data = json.load(open(mpath))
            log(f"--score-only: {len(data['moments'])} scored moment(s) -> {mpath} "
                "(no render; feed this to a viral-judge pass)")
            return
        run(["python3", os.path.join(BIN, "music.py"), mpath], capture_output=True, text=True)
        data = json.load(open(mpath))
        picks = pick(data["moments"], a.n or 5)
        if not picks:
            sys.exit(f"[clip] no clip-worthy moments cleared the gates in '{vid}'. "
                     "The footage may be too conversational/low-energy for short-form.")

    # PREFLIGHT QUALITY GATE: lint exactly the picks we're about to render
    # (not the full moments list) for the known whack-a-mole defect classes
    # (garbled/fragment openers, bad headlines, bad duration, banter leakage,
    # all-same-CTA) BEFORE any render work starts. A failure aborts here —
    # --force renders anyway but still prints the defect report.
    pf_ok, pf_report = run_preflight(picks, n=None)
    if not pf_ok:
        log(f"PREFLIGHT FAILED for {vid} — defects found in the picks below:")
        for line in pf_report:
            print(line, file=sys.stderr)
        if not a.force:
            sys.exit("[clip] aborting before render (preflight quality gate failed). "
                     "Fix the flagged picks, or re-run with --force to render anyway.")
        log("--force set: rendering anyway despite the defects above.")
    else:
        log(f"preflight: PASS — {len(picks)} pick(s) clean.")

    formats = {"vertical": ["vertical"], "horizontal": ["horizontal"],
               "both": ["vertical", "horizontal"]}[a.format]
    fmt_label = {"vertical": "9:16", "horizontal": "16:9", "both": "9:16 + 16:9"}[a.format]
    log(f"picked {len(picks)} moment(s) → rendering to {fmt_label} clips …")

    outdir = os.path.join(OUTROOT, f"{vid}-{slugify(picks[0]['title'])}")
    os.makedirs(outdir, exist_ok=True)
    summary = [f"# Clips for {vid}", f"_{len(picks)} Instagram-ready clips from `{a.src}`_\n"]

    for i, m in enumerate(picks, 1):
        headline = m.get("onscreen_hook") or m["title"]
        headline_note = " (headline rewritten from spoken open)" if m.get("headline_is_rewrite") else ""
        log(f"rendering {i}/{len(picks)}: {m['title']} ({mmss(m['start'])}–{mmss(m['end'])}) …")
        outs = {}
        for aspect in formats:
            suffix = "_h" if aspect == "horizontal" else ""
            out = os.path.join(outdir, f"clip_{i:02d}_{slugify(m['title'])}{suffix}.mp4")
            outs[aspect] = out
            # medium whisper for finals: base-model mishears get BURNED INTO the karaoke
            # ("in hormones" for "and hormones", "Tank to" for "Tanked") — worth the
            # slower transcribe on a clip that ships
            rcmd = ["python3", RENDER, f"--video={video}", "--start", str(m["start"]),
                    "--end", str(m["end"]), f"--out={out}", f"--headline={headline}",
                    "--model", "medium", "--aspect", aspect,
                    # snap the cut to true speech: auto-sub timestamps skew early, which
                    # bleeds the previous sentence into the open and can chop the ender
                    f"--expect-first={' '.join(m['hook_line'].split()[:5])}",
                    f"--expect-last={' '.join(m['text'].split()[-5:])}"]
            if a.no_captions:
                rcmd.append("--no-captions")
            if cover:
                rcmd.append("--cover-source-captions")
            if a.music:
                rcmd += ["--music", a.music]
            run(rcmd)
        mu = m.get("music", {})
        lane_b = (mu.get("lane_b") or {}).get("trend", "")
        file_lines = [f"  - {label}: {os.path.basename(outs[aspect])}"
                      for aspect, label in [("vertical", "vertical (9:16)"), ("horizontal", "horizontal (16:9)")]
                      if aspect in outs]
        summary += [
            f"## {i}. {m['title']}",
            *file_lines,
            f"- ⏱  {mmss(m['start'])}–{mmss(m['end'])} ({m['dur']}s)"
            + (f" · score {m['score']}" if m.get('score') is not None else "")
            + (f" · lever: {m['engagement_lever']}" if m.get('engagement_lever') else ""),
            f"- 🎬  On-screen hook: **{headline}**{headline_note}",
            (f"- 💬  Quote/caption seed: _{m['quotable_line']}_" if m.get("quotable_line") else ""),
            f"- 🎵  Music to add in-app ({mu.get('vibe','')}): {lane_b}" if lane_b else "",
            "",
        ]

    open(os.path.join(outdir, "SUMMARY.md"), "w").write("\n".join(x for x in summary if x is not None))
    log(f"done — {len(picks)} clip(s) rendered.")
    print(f"\n✅ {len(picks)} clips ready → {outdir}")
    print(f"   {len(picks)} .mp4 + SUMMARY.md (each hook + caption + the trending sound to add in-app).")
    print(f"   open:  open '{outdir}'")


if __name__ == "__main__":
    main()
