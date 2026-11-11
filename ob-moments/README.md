# ob-moments

Find the moments in an OB Health long-form video (YouTube/podcast) most likely
to pop as short-form, score **why**, rank them for the 30–45 buyer (not just
under-25 reach), advise how to improve each clip and the source video, recommend
music across two legal lanes, and hand the winners to the **ob-clipper** renderer
for finished 9:16 captioned MP4s.

Full design + research rationale: [DESIGN-BRIEF.md](DESIGN-BRIEF.md) · sources: [RESEARCH-REFERENCES.md](RESEARCH-REFERENCES.md)

## Status

| Phase | What | State |
|---|---|---|
| 1 | **Transcript virality brain** — window → 10-feature score → gates → tags → ranked shortlist | ✅ working |
| 2 | Full-production render (promote `ob-clipper`: cut → 9:16 reframe → PIL captions → music duck → −14 LUFS) | ⏳ next |
| 3 | Improvement advisor (per-clip hook/cut/overlay + per-video hook/pacing/retention) | ⏳ |
| 4 | Music engine (ranked trending-in-app + burned-in RF, license-safe) | ⏳ |
| 5 | YouTube analytics fusion (retention curve + most-replayed → F11–F13) | ⏳ |
| 6 | Calibration (re-fit weights vs the IG content×revenue archive) | ⏳ |

## The scoring model (Phase 1)

10 features, weights sum to 100: **Hook 22** (also a *multiplier* — a weak opener
gates the whole score), Curiosity 14, Arousal 14, Self-contained 12, Payoff 10,
Controversy 8, Numbers 6, List 5, You-address 5, Quotability 4. Two **hard
rejects**: needs-context, or dead-hook. Two tags per survivor: **engagement lever**
(share/save/comment) and **buyer-relevance** (0–100). Text can only *rank*
(ViralBERT ceiling F1≈0.52), so it's triage: surface ~15, ship 3–5.

Subjective features (hook, arousal, controversy, quotable) are refined by an LLM
pass; everything has a deterministic regex baseline so it runs with zero LLM.

## Usage

```bash
cd ~/ob-moments
# 1) get transcript (auto-subs; instant)
yt-dlp --skip-download --write-auto-sub --sub-lang en --convert-subs srt \
  -o "work/%(id)s.%(ext)s" "<youtube-url>"
# 2) score → work/<id>.moments.{json,md}
python3 bin/score.py work/<id>.en.srt --id <id>
```

### LLM backend for the subjective pass (pick one)
- `claude -p` — used automatically **if the CLI is logged in** (`claude` in a normal terminal). Nested/sandboxed runs report "Not logged in" and fall back.
- `ANTHROPIC_API_KEY` — set it and the tool calls the API directly (model via `OB_MOMENTS_MODEL`, default `claude-opus-4-8`).
- `--llm-json PATH` — inject precomputed scores (used for testing / offline). Get the pool with `--dump-pool PATH`.
- `--no-llm` — deterministic regex baseline only.

## Layout
```
bin/clean_srt.py   → symlink to ob-clipper (SRT de-dup)
bin/window.py      → sentence-snapped 15–60s candidate windows
bin/score.py       → 10-feature scorer + gates + tags + LLM enrichment
app/               → (Phase 1.5) self-contained review UI, fetches app/data/moments.json
music/             → owned royalty-free tracks (+ license sidecars)
work/              → gitignored: srt/json/md caches, renders
.secrets/          → gitignored: yt-oauth.json (Phase 5)
```

## Reused assets
- yt-meta cache: `~/ob-social-dashboard/data/yt-meta/{id}.json` (759 files)
- whisper models: `~/.whisper-models/ggml-{base,medium}.en.bin`
- renderer: `~/ob-clipper/` (shared, promoted in Phase 2)

## First run
`work/Bm7gtO679XA.*` — the "I Lost 40 Pounds" episode → ranked shortlist in
`Bm7gtO679XA.moments.md` (cold open #1, "eating disorder" hot take #2).
