# ob-clipper

Turn OB Health long-form (YouTube episodes / podcast) into ranked, captioned,
music-ready **9:16 short-form clips** for IG Reels.

Built on tooling already on this machine — no new heavy deps:
`yt-dlp`, `ffmpeg` (Homebrew, **no drawtext → captions via PIL**), `whisper-cli`
(`~/.whisper-models/ggml-base.en.bin` + `ggml-medium.en.bin`), `cv2`, `PIL`, `numpy`.

## Pipeline

| Stage | Script | Status |
|---|---|---|
| 1. Ingest (YouTube URL *or* local file) | `bin/ingest.sh` | ✅ (auto-subs path proven) |
| 2. Transcript (auto-subs for finding; whisper word-level for captions) | `bin/clean_srt.py` | ✅ finding path done |
| 3. **Find clips** (LLM → ranked clips + hooks + captions + why) | `bin/find_clips.py` (`claude -p`) | ✅ proven in-session; wrapper next |
| 4. Reframe 16:9 → 9:16 face-centered punch-in | `bin/reframe.py` (cv2) | ⏳ next |
| 5. Burn captions (word-synced, PIL PNG overlays) | `bin/captions.py` | ⏳ next |
| 6. Music (duck approved RF track under VO + in-app trending note) | `bin/music.py` | ⏳ next |
| 7. Render (x264, −14 LUFS, faststart) | `bin/render.sh` | ⏳ next |

## Usage (current)

```bash
# 1–2: get a clean, timestamped transcript from a YouTube URL
cd ~/ob-clipper
yt-dlp --skip-download --write-auto-sub --sub-lang en --convert-subs srt \
  -o "work/%(id)s.%(ext)s" "<youtube-url>"
python3 bin/clean_srt.py work/<id>.en.srt > work/<id>.transcript.txt

# 3: find clips → work/<id>.clips.md   (see first run: work/Bm7gtO679XA.clips.md)
```

## Design decisions (from prior OB builds — see memory)

- **Captions must be PIL PNG overlays** — this Homebrew ffmpeg has no `drawtext`.
- **Music does NOT auto-guess.** OB rejected auto-picked beats twice ("too loud",
  "generic elevator music"). Music is an *approve-step*: drop tracks you like in
  `music/`, the tool ducks your pick via sidechain-compress (voice −15 LUFS).
- **Trending audio for reach must be added in-app.** Burning a licensed viral track
  into an exported MP4 gets a business account muted/throttled. The tool exports a
  clean captioned clip + a "add THIS sound in-app" note for reach plays.
- **Finding uses instant auto-subs; whisper only runs on the chosen clip windows**
  (fast, accurate word timing for captions).
- Reframe keeps footage as-shot (no exposure/color ops — OB rejected grading).

## First run
`work/Bm7gtO679XA.clips.md` — 6 ranked clips + 2 bonus from the "40 lbs" episode.
