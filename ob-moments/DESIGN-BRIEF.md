Key paths confirmed: `ob-clipper` is a skeleton (only `clean_srt.py` + empty `music/`), the yt-meta cache has 759 JSON files (not 88), whisper models present, meal-planner has the `app/` + `data-build/` split. Now the brief.

# BRIEF: OB-Moments — Viral Moment Finder + Improvement Advisor + Music Matcher

**For:** OB Health short-form production (YouTube/podcast long-form → IG Reels)
**Status:** Design-ready. Builds on the just-started `ob-clipper`, reuses the `yt-meta` cache and whisper/ffmpeg stack already on the machine.

---

## 1. TL;DR Recommendation

Build **`/Users/YOU/ob-moments/`** as a staged pipeline + local review app that matches the existing OB tool pattern (Python `bin/` data-build → JSON artifact → self-contained `app/` UI). It ends in **finished, ready-to-post 9:16 captioned MP4s with music**, rendered by promoting `ob-clipper` from a skeleton into the shared **renderer** both tools call.

Four decisions drive the whole design:

1. **Phased brain.** Phase 1 scores moments from the **transcript only** (works day one, no OAuth). Phase 2 fuses in the creator's **real YouTube retention + most-replayed** data to sharpen and validate. The scorer is built as a pluggable feature stack so analytics slot in as *additional weighted features*, not a rewrite.
2. **Two-headed advisor.** The improvement advisor critiques both the **clips it picked** (hook framing, cut points, overlay text) **and the source video itself** (hook rewrite, pacing, retention dips, next-time changes). Title/thumbnail/metadata are stubbed for later.
3. **Full production, human-gated at two points.** The tool never auto-ships. It stops for (a) **moment/clip approval** and (b) **music approval** — because OB rejected auto-picked beats twice. Everything else is automated through to the final MP4.
4. **Music is ranked, never guessed.** Per clip the engine returns a *ranked shortlist across all lanes*: a business-safe **trending in-app sound** (for reach) + a **burned-in royalty-free mood-matched** track (safe fallback), each labeled with its lane and legal status. The licensed library is **pluggable** — the tool works with zero paid library (Meta Sound Collection + owned `music/` folder) and gets better if OB adds Epidemic/Artlist.

Do **not** rebuild commodity capability (auto-reframe, 97–99% captions, transcript moment-detection are solved). The defensible edge is the **closed-loop, OB-account-specific score** trained on the 6,408-post IG content×revenue archive, weighted for **conversion and the 30–40+ buyer demo**, not vanity reach.

---

## 2. The Virality Scoring Model

### 2.1 Design principle
Text scoring can only **rank a candidate pool**, not certify hits (ViralBERT topped out at F1 ~0.52 *with* follower features). So the model's job is triage: extract 10–20 candidates per episode, score+rank, surface the top 10–15 for human approval, ship 3–5. Volume strategy, human gate.

### 2.2 Candidate windowing (before scoring)
- Chunk the cleaned transcript into **15–60s windows** using sentence boundaries + speaker turns.
- **Snap window starts to sentence beginnings** so hooks are never cut mid-thought.
- Slide the window; each candidate = `{start, end, text, first_sentence}`.

### 2.3 Phase-1 feature stack (transcript-only) — 10 features, weights sum to 100

| # | Feature | Wt | How computed | Method |
|---|---------|----|--------------|--------|
| 1 | **Hook strength** (gates distribution) | 22 | Score first 1–2 sentences only. `min(100, 40 × distinct hook triggers)`. Triggers: `?` in sentence 1; contrarian markers (`everyone thinks`, `the truth is`, `nobody tells you`, `myth`, `wrong`); number/`%`/`lbs`/timeframe in sentence 1; warning imperative (`stop`, `never`, `the mistake`); `you/your` in sentence 1. Penalize openings starting with pronoun/`and so`/`but yeah` (context leak). | regex + light LLM classify |
| 2 | **Curiosity gap / open loop** | 14 | Forward-reference phrases early (`here's why`, `what most people don't realize`, `the crazy part`) that pay off later in-window. High if gap opened early AND closed before end. | regex + LLM |
| 3 | **Emotional arousal (peak, not avg)** | 14 | Lexicon/valence pass; score **peak** arousal. High-arousal +ve (`insane`, `blew my mind`, `shocking`) and −ve (`terrified`, `disgusting`, `fed up`) both score high; low-arousal (calm/sad) low. Bonus for **valence swing** within clip. | LLM rate 0–100 |
| 4 | **Self-contained arc / context independence** | 12 | Subtract for unresolved back-refs (`like I said`, `that thing`, dangling `he/she/they` with no in-clip antecedent). Add for stated-premise→conclusion. **Podcast make-or-break.** | regex + LLM |
| 5 | **Payoff / resolution clarity** | 10 | Resolution markers near end (`so the answer is`, `that's why`, `do this instead`, punchline). Opens loop but never closes = 0 here. | regex + LLM |
| 6 | **Controversy / hot-take** (drives comments+shares) | 8 | Polarizing/stance language (`unpopular opinion`, `the industry lies`, callouts). **Flag for human review, never auto-ship** (brand guardrail). | LLM |
| 7 | **Numbers / stats / specificity** (drives saves) | 6 | Count figures, %, timeframes, lb/$ amounts, named protocols. | regex |
| 8 | **List / utility structure** (drives saves) | 5 | Enumeration (`3 things`, `first… second…`) + actionable imperatives. | regex |
| 9 | **Direct "you"-address** (drives shares) | 5 | Second-person density + identity/pain statements (`if you've ever…`, `you're not lazy, you're…`). | regex |
| 10 | **Quotability / soundbite** | 4 | Crisp standalone line <~15 words, parallelism/contrast (`X, not Y`), metaphor. This becomes the **on-screen text candidate**. | LLM extract |

**Final score = weighted sum.** Two **hard gates override the raw score:**
- **HARD REJECT** if Feature 4 (context) ≈ 0 → unintelligible cold.
- **HARD REJECT** if Feature 1 (hook) ≈ 0 → dies in 3s. No strong body rescues a dead hook.

**Two extra tags** attached to every surviving candidate:
- **Primary engagement lever** (share / save / comment) — from which features dominated, so the team balances the mix.
- **Buyer-relevance flag** — a clip can score viral yet pull the wrong (non-buying, under-25) audience. Tag against the 3 brand pillars (Identity>Diet, Systems>Motivation, Support>Willpower) and BOF painpoint specificity. High-virality + low-buyer-relevance is surfaced but demoted.

**Brand-safety pass (mandatory before display):** the auto-proposed soundbite/caption runs through OB's existing no-em-dash / no-AI-tells / buyer-voice checks. A high Feature-6 score raises a human-review flag rather than auto-shipping.

### 2.4 Phase-2 features (analytics-powered) — added, not swapped
When real YouTube data is wired, the same window gets three more signals that **multiply/adjust** the transcript score:

- **F11 — Retention-anchored (weight ~15, redistributed).** Map the window's time-range to the `audienceWatchRatio` curve. A window overlapping a **local maximum / spike >1.0** (rewatch moment) gets a strong boost; a window sitting in a retention **dip** gets penalized. This is ground truth vs. the transcript's *prediction*.
- **F12 — Most-replayed overlap.** yt-dlp `heatmap` value (0–1) averaged over the window. Cross-check with F11.
- **F13 — Whole-video punch-above-length.** `relativeRetentionPerformance` (0–1, 0.5=median) scales confidence for the *whole* source — a video that over-retains for its length class makes all its candidates more trustworthy.

Implementation: features are a registry of `(name, weight, compute_fn)`. Phase 2 activates F11–F13 and **re-normalizes weights**; nothing in Phase 1 is thrown away. Transcript score and analytics score are both stored so the UI can show "predicted vs. actual retention" side by side — which is exactly the disagreement signal used to **re-fit the weights** (see §7).

### 2.5 Calibration (the moat)
The literature-derived weights above are **priors, not fitted to OB.** Back-test: score past clips with this rubric, correlate scores against actual IG views/saves/shares (and, when available, downstream DM/lead volume) from the 6,408-post archive, then re-fit — even a simple logistic regression on the 10–13 features against a "went viral for OB" label beats hand-set weights. The outcome label to fit against is an **open question** (§8) — raw views vs. saves vs. DMs may differ, and the revenue-correlated one wins.

---

## 3. Analytics Integration Plan

### 3.1 What data, from where

| Surface | Signal | Availability | Use |
|---------|--------|--------------|-----|
| **YouTube Analytics API v2** | Per-video **audience retention curve** (`dimensions=elapsedVideoTimeRatio`, `metrics=audienceWatchRatio,relativeRetentionPerformance`, `filters=video==ID`) | Owner-only, precise, ~100 points/video. `audienceWatchRatio>1.0` = rewatch spike = candidate viral moment. | **Primary Phase-2 signal.** The only programmatic true per-moment data. |
| **yt-dlp `heatmap`** ("most replayed") | `[{start_time, end_time, value 0–1}]`, ~100 entries | Public for any ~50k+ view video; **no API**, scraped from watch page. Fragile — pin yt-dlp, null-guard. | Cross-check on own videos; **only** moment signal for **competitors** (where Analytics is inaccessible). |
| **YouTube Data API v3** | `videos.list` (views/likes/comments/duration, batch 50, 1 unit); `commentThreads.list` (topic/hook mining) | 10k units/day is ample for one creator. Avoid `search.list` (100 units). | Cheap catalog/stats layer + "what viewers quote back" = caption fuel. Already partly cached in `yt-meta/`. |
| **Instagram Graph API** | Per-Reel **aggregates only**: `reach, saved, shares, views, ig_reels_avg_watch_time (ms), ig_reels_video_view_total_time, skip rate` | IG Professional/Business + linked FB Page required. **No within-Reel retention curve, no per-audio analytics.** | Whole-clip **outcome labels** for calibration (§2.5). Cannot find the moment inside a Reel. |
| **TikTok** | View/like/comment/share counts only (Display API) | Retention needs Business API approval (app review). | Out of scope; coarse winners only. |

### 3.2 OAuth + setup (low-friction, zero-review)
- **One Google Cloud project**, OAuth **"Desktop app"** client (system browser + loopback redirect).
- **Scopes:** `yt-analytics.readonly` (retention) + `youtube.readonly` (data/comments). Add `yt-analytics-monetary.readonly` only if revenue metrics wanted.
- **Consent screen = External + Testing**, add OB's own Google account as a **test user** → avoids Google's app-verification review entirely for personal use. Re-consent periodically.
- Store refresh token locally at `~/ob-moments/.secrets/yt-oauth.json` (gitignored).
- IG: long-lived token with `instagram_manage_insights` on the Professional account (this is an **open question** — does the account run Professional/Business, given the "Sophia Prince" burner setup?).

### 3.3 Phasing & feasibility
- **Phase 1 (now):** No OAuth. Transcript brain only. Fully functional.
- **Phase 2a:** YouTube Analytics retention curve for own videos (highest ROI, lowest friction). Wire F11/F13.
- **Phase 2b:** yt-dlp heatmap as cross-check + competitor moment-mining. Wire F12.
- **Phase 2c:** IG Graph aggregates as calibration labels → close the loop and re-fit weights.
- **Fragility guards:** pin + auto-update yt-dlp; null-guard `heatmap`; code IG against current field names (`views`, not deprecated `plays`); version-pin Graph API.

---

## 4. The Improvement Advisor

Two subjects, one LLM-driven critique stage (`bin/advise.py`) that consumes transcript + scores + (Phase 2) retention curve, and writes a structured `.advice.md` alongside the moments file.

### 4.1 Critique of the CLIPS it picked (per moment)
- **Hook framing** — is the clip *starting at the hook*, or is there rambling lead-up to trim? Propose an exact new start timestamp. Rate the opening line against the 6 hook archetypes; if weak, propose a rewrite/re-cut using a stronger in-clip line.
- **Cut points** — does it start on a sentence boundary and end on the payoff? Flag if it opens a loop it never closes (Feature 5 = 0) → suggest extending to include the resolution or moving the out-point.
- **Overlay text** — is the auto-extracted soundbite (Feature 10) the strongest available line? Propose the on-screen caption, run it through anti-AI-tell/buyer-voice checks, offer 2–3 alternatives.
- **Loop potential** — does the last line echo/answer the first so a rewatch feels seamless? If not, suggest an end-trim that creates the loop.

### 4.2 Critique of the SOURCE VIDEO itself
- **Hook rewrite** — the video's opening: does it survive the first 1.7s / 3s? Propose a stronger cold open (for next-time filming, and to guide where the best clip-hooks live).
- **Pacing** — words-per-minute + pause-gap histogram from `silencedetect`; flag dead-air stretches and monotone runs; recommend tightening.
- **Retention dips (Phase 2)** — map `audienceWatchRatio` valleys back to timestamps → "viewers dropped at 4:12 where you went on a tangent about X; cut or restructure this next time." Map spikes → "3:30 over-retained — this topic/framing works, do more of it."
- **Next-time changes** — a short prioritized list: what to change in the *next* recording (open with the payoff, kill the 90-second setup, etc.).

**Lower priority / stubbed:** title/thumbnail suggestions and post metadata (captions/hashtags) — scaffold the section, fill later.

**How it's generated:** transcript-derived features + regex metrics feed an LLM pass (`claude -p` / anthropic SDK) with an OB-brand-loaded prompt (pillars, anti-AI-tells, buyer voice, 30–40+ demo). Phase 2 injects the retention curve as additional context so dip/spike critique becomes data-grounded rather than inferred.

---

## 5. The Music-Matching Engine

Never auto-applies. Returns a **ranked, lane-labeled shortlist per clip**; the user approves. Library is **pluggable** — degrades gracefully to zero paid sources.

### 5.1 Pipeline (`bin/music.py`)
**Stage 1 — Characterize the clip → target vector.** Run Essentia (or librosa) on the clip audio for voice energy, pitch/loudness variance; parse transcript for speaking rate, pause density, sentiment (valence proxy), topic; estimate cut pace. Collapse to `{target_energy 0–1, target_valence 0–1, target_bpm range, vibe_tags: [motivational|calm|high-intensity|emotional], instrumental_preferred: true}` (talking-head ⇒ low/no-vocal beds rank higher).

**Stage 2 — Retrieve candidates** from a **unified local index** built from whatever sources are plugged in:
- Always-on: **owned `music/` folder** (auto-tagged once with Essentia: bpm/mood/genre/hasVocals + license sidecar) and **Meta Sound Collection** (business-safe, ~14k tracks).
- Optional (pluggable): **Epidemic Sound Partner API** (bpm/`moods[]`/`genres[]`/`hasVocals`, MCP beta for LLM query) as licensed spine; **Artlist** secondary; **Uppbeat** as manual bucket (no API).

**Stage 3 — Score each track** by weighted distance on `(bpm-match, energy/valence via mood-tag map, vocals-penalty, genre-fit)`.

**Stage 4 — Rank + label lanes.** Return **top 3 mixed across lanes** (see below).

### 5.2 The two legitimate lanes (engine must respect the boundary)
- **Lane A — Burned-in royalty-free** (safe, exportable into the MP4, never muted): from owned folder / Epidemic / Artlist / Uppbeat Premium. This is the **default primary** for a talking-head bed. Always available.
- **Lane B — In-app trending** (for reach, added natively in the IG app at low mix under the voice, **not** burned in): only sounds that are **business-safe** — present in Meta Sound Collection or the Professional Dashboard > Trending Audio list. The render exports a **clean audio track + a note "add THIS trending sound in-app"** rather than embedding it.

Every clip surfaces **≥1 Lane A and ≥1 Lane B** option, each badged with lane + license status.

### 5.3 Trending signal (Phase 3)
- **TikTok Creative Center > Trends > Songs** (free, **leads IG by 3–7 days** — early-mover window). Poll weekly.
- **Chartmetric API** (paid, clean, TikTok+IG velocity) if OB wants structured IG-specific trend data.
- **Filter every trending candidate against business-safe availability** (Meta Sound Collection / TikTok CML) before ever recommending it — a trend you can't legally use is noise.

### 5.4 Legal guardrails (encoded as hard engine rules)
1. **Never** recommend burning a non-royalty-free / label / viral chart track into the exported MP4. IG's 2026 AI fingerprinting analyzes the **final posted file** — burning in gives **zero** protection; on a monetizing business account it mutes/throttles + **disables revenue**.
2. Trending viral sounds are **only** ever Lane B (in-app) **and only** when business-licensed.
3. **No YouTube Audio Library** for IG Reels (clears on YT, flags on IG/FB).
4. Any burned-in track must carry a commercial/business-social license; **store per-track license proof** (matters for Meta ad review).
5. Treat OB as a **business account** (it monetizes): business-account rules are mandatory.

---

## 6. Recommended Architecture & File Layout

Matches the OB pattern exactly: Python `bin/` stages → cached JSON/`.md` artifacts → self-contained `app/` review UI. Reuses the whisper/ffmpeg/cv2/PIL stack (all verified present) and the `yt-meta` cache.

```
/Users/YOU/ob-moments/
├── README.md                 ← pipeline + design decisions
├── bin/
│   ├── ingest.sh             ← YT URL → local mp4 + auto-subs (checks yt-meta cache FIRST)
│   ├── transcribe.py         ← whisper-cli -ml 1 -sow -ojf → word-level JSON (ms offsets)
│   ├── clean_srt.py          ← SYMLINK/import from ob-clipper (proven dedup)
│   ├── window.py             ← chunk into 15–60s sentence-snapped candidates
│   ├── score.py              ← 10-feature transcript scorer + gates + tags (feature registry)
│   ├── analytics.py          ← (Phase 2) YT Analytics retention + heatmap → F11–F13
│   ├── advise.py             ← improvement advisor (clips + source video) → .advice.md
│   ├── music.py              ← characterize clip + rank music across lanes
│   └── calibrate.py          ← back-test scores vs IG archive outcomes, re-fit weights
├── app/                      ← self-contained review UI (meal-planner pattern)
│   ├── index.html
│   ├── styles.css
│   ├── js/app.js
│   └── data/moments.json     ← fetch()'d (large/dynamic, unlike meal-planner's embedded data)
├── music/                    ← owned royalty-free tracks + YAML license/bpm/mood sidecars
├── work/                     ← gitignored: mp4/srt/json caches, .moments.md, .advice.md, renders
├── .secrets/                 ← gitignored: yt-oauth.json, ig-token.json
└── data-build/               ← (optional) only if a trend dashboard is later wanted
```

**The renderer = promote `ob-clipper`.** `ob-clipper` is currently a skeleton (only `clean_srt.py`, empty `music/`). Rather than duplicate rendering, build the **final-production stages inside `ob-clipper`** and have `ob-moments` call it. Contract: `ob-moments` writes an approved-clip spec (`{video, start, end, caption_words[], music_choice, lane}`), `ob-clipper` consumes it and renders. This keeps one renderer, matching the research recommendation that clipper emit/consume a shareable spec.

**Renderer stages (in `ob-clipper/bin/`), all with the verified local toolkit:**
1. Cut A/V together via concat demuxer (silence/filler EDL from `silencedetect` + filler tokens in whisper JSON) — never audio-only (desync).
2. **9:16 auto-reframe** in cv2+numpy: YuNet (`FaceDetectorYN`, one-time 340KB ONNX) primary, Haar fallback; **two-pass trajectory smoothing** (collect detections → smooth whole center-x array via forward-backward EMA / boxcar) + dead-zone + per-frame clamp = no jitter. Crop width 607px @1080p.
3. **PIL karaoke captions** from whisper ms offsets (ffmpeg has **no drawtext** — hard rule). Active word bright, line dim.
4. **Music duck**: `sidechaincompress` (voice triggers, music ducks) `threshold≈0.03:ratio=8:attack=20:release=300`, then `amix`.
5. **Two-pass `loudnorm` to −14 LUFS / −1 dBTP**, run **last** (after duck+mix).
6. Mux H.264/AAC 1080×1920 + faststart → ready-to-post MP4.

**Reuse paths (reference in code):**
- yt-meta cache: `/Users/YOU/ob-social-dashboard/data/yt-meta/{video_id}.json` (759 files present)
- whisper models: `~/.whisper-models/ggml-base.en.bin` (fast preview) / `ggml-medium.en.bin` (final caption pass)
- `clean_srt.py`: `/Users/YOU/ob-clipper/bin/clean_srt.py`
- music: `/Users/YOU/ob-moments/music/`

**Deps (all installed or one pip away):** yt-dlp, ffmpeg (loudnorm/sidechaincompress/silencedetect/scdet all compiled in — verified), whisper-cli, cv2 4.13 (`FaceDetectorYN` + Haar present), PIL, numpy, `anthropic` SDK. One-time adds: `pip install scenedetect` (AdaptiveDetector), download `face_detection_yunet_2023mar.onnx`. Optional: `essentia` (mood/bpm models) or lighter `librosa` for music matching.

---

## 7. Phased Build Plan (smallest-valuable-first)

**Phase 0 — Scaffold (0.5 day).** Create `ob-moments/` tree; symlink `clean_srt.py`; wire `ingest.sh` to check `yt-meta` cache before yt-dlp. **Delivers:** URL → cleaned word-level transcript.

**Phase 1 — Transcript brain + shortlist UI (MVP).** `window.py` + `score.py` (10 features + 2 gates + engagement/buyer tags) + minimal `app/` that lists ranked moments with sub-scores, auto-hook line, suggested soundbite, and an **Approve** toggle. **Delivers:** *"Give me a URL, get a ranked, approvable shortlist of clip candidates."* Works with zero OAuth, zero paid library. This is the first thing OB can actually use.

**Phase 2 — Full production render.** Promote `ob-clipper` into the shared renderer (cut → reframe → PIL captions → duck → −14 LUFS → mux). Approved moment → finished 9:16 captioned MP4 with a **safe burned-in Lane A** track from the owned `music/` folder. **Delivers:** *end-to-end ready-to-post clip.* (Music approval step is present but Lane A only.)

**Phase 3 — Improvement advisor.** `advise.py`: clip critique (hook/cuts/overlay/loop) + source-video critique (hook rewrite, pacing, dead-air). **Delivers:** the `.advice.md` per video + per clip.

**Phase 4 — Music engine full.** Add clip characterization + ranked shortlist across lanes; plug Meta Sound Collection (Lane B business-safe) and optional Epidemic/Artlist; TikTok Creative Center trending poll + business-safe filter. **Delivers:** ranked Lane A + Lane B music choices per clip, license-badged.

**Phase 5 — Analytics fusion (YouTube).** OAuth desktop app; `analytics.py` pulls retention curve + `relativeRetentionPerformance`; add yt-dlp heatmap cross-check; wire F11–F13, re-normalize weights. Advisor's retention-dip critique becomes data-grounded. **Delivers:** analytics-powered scoring + validation of the transcript brain.

**Phase 6 — Closed loop / calibration.** IG Graph aggregates as outcome labels; `calibrate.py` back-tests rubric scores vs. the 6,408-post archive and re-fits weights (logistic regression). **Delivers:** the OB-specific moat — a score fitted to what actually goes viral *and converts* for OB, not generic population views.

---

## 8. Open Questions to Confirm

1. **Calibration outcome label:** what does "viral" map to for back-testing — raw views, views/follower, saves, shares, or **downstream DM/lead volume**? The revenue-correlated one should drive the weight re-fit, and it may not be "views." Which per-post fields actually exist in the T7 IG content×revenue archive (watch-time? DMs-per-post? attributed revenue?) — this determines whether a *conversion*-weighted score is trainable now or starts as a reach proxy.
2. **IG account type:** Professional/Business or Creator, and is it linked to a FB Page? The Graph insights endpoint + `instagram_manage_insights` require it; a personal account can't use the API at all. Worth confirming against the "Sophia Prince" burner setup. Creator accounts also get a wider in-app music library than Business.
3. **Licensed music library:** does OB want to pursue an **Epidemic Sound partnership** (portal credentials + MCP beta), or run Lane A entirely off the **owned `music/` folder + Meta Sound Collection** for now? (Engine works either way; this just sets Lane A depth.) Should the engine auto-tag the **existing owned** Epidemic/Canva/CapCut tracks with Essentia so it recommends from owned assets before hitting any API?
4. **Trending data spend:** free **TikTok Creative Center** (gray-zone if scraped) vs. paid **Chartmetric API** — depends on tolerance for ToS gray-zone and how much IG-specific trend data is needed.
5. **Filler-word cuts:** fully automated `um/uh/like` removal, or generate a **human-review EDL** first? (Auto-cutting risks clipping real words — recommend review EDL.)
6. **Controversy weighting:** should the rubric **down-rank** clips whose virality driver is controversy/out-group animosity even when they'd score high, given OB's anti-AI/authentic positioning? Tool can flag it; this is a values call for the team.
7. **Source cadence:** YouTube podcast long-form only (transcript-sufficient), or also visual-heavy inputs that would need scene-based (not just transcript) analysis?

---

**Key paths:** new tool at `/Users/YOU/ob-moments/`; renderer promoted in `/Users/YOU/ob-clipper/` (currently skeleton: only `bin/clean_srt.py` + empty `music/`); yt-meta cache `/Users/YOU/ob-social-dashboard/data/yt-meta/` (759 files); whisper models `~/.whisper-models/`; pattern references `/Users/YOU/ob-meal-planner/` (`app/`+`data-build/` split) and `/Users/YOU/ob-social-dashboard/` (`build_data.py`→JSON→self-contained HTML).