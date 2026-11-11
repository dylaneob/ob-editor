> SUPERSEDED 2026-11-10: the rules for this format now live in `~/.claude/skills/short-form-editor/routes/short-form.md`.
> Where this file disagrees, the route file and `~/ob-editor/qc/formats.json` win. Kept for history only.

# Preset: OB short-form (9:16 Reels / TikTok / Shorts)

Load this first for any OB reel. Locked values as of 2026-10-17. The runbook with commands is `~/.claude/skills/short-form-editor/SKILL.md`; the rules come from OB's notes in memory (`reference_short_form_editor_setup`, `feedback_trial_variant_packs`, `reference_viral_background_music_2026_10`, `feedback_list_video_hook_order`). This file is the checklist and values, not a second copy of the rules.

**Openings: read `~/ob-editor/presets/PROVEN-OPENERS.md` first** (v0 2026-10-22, from his skip rate on 6,130 reels). It sets the defaults for frame 1 and every hook or opening variant in a trial pack.

## Pipeline (lock each stage before the next)
0. **The brief first** (OB 2026-10-18; full text at the top of the editor skill):
   - Evidence: skip rate and average watch time for his last 20 reels (`brain.py skip`), lined up against what was on screen. Decode the reference by behavior, not its look.
   - Promise: the hook locked before cutting.
   - Story edit: cut slack, not just outtakes.
   - Clearance ledger for any proof or song.
   - Step 5 after posting: log the Retention card and write the lesson here.
1. **Intake.** RAW, uncaptioned footage only; old captions bleed through otherwise. Ask: where it's going (organic, trial, ad), which part, and any reference reel.
2. **Sync.** `sync_av.py --audio-only`. Any take recorded while a render ran: `sync_steps.py` (MOTIV drops buffers, so the offset is a staircase).
3. **Grade.** Warm, golden skin, never pink-neutral. Show 3 options on his real frames (`make_grade.py` W1-W3) and render only after he picks. Default LUT `luts/ob_grade_warmtan_hald.png`; grade A is rejected ("albino").
4. **Bad takes out, zero dead space, clean voice (HARD RULE, OB 2026-10-27/28).** OB 10-28: "find the bad takes and get rid of them and deadspace so it flows really well and its fast pace", "not speed it up but just cut absoleultely all deadspac", "immediately after i stop talking i need you to cut". The tools:
   - **Takes.** `takes.py WORDS.json SCRIPT`. It keeps the LAST clean take of every script line and drops the tries that "cut that, Claude" follows, the ones that stop short, and the restarts. Read its drop list.
   - **Cut.** `takes.py ... --audio MIC.wav --fps 29.97 --edl EDL.json`. Each kept take goes through `zero_dead.cut_words`:
     - edges at the first word's onset and the last word's end ("immediately after the sound goes down")
     - every pause of 70 ms or more between words cut
     - nothing inside a word ever cut
     - never a tempo change
   - **Voice.** `--voice OUT.wav --master` (`voice_master.py`):
     - from the MOTIV 48 kHz mic, never camera audio or a 16 kHz analysis copy
     - each line levelled to the median line
     - a 3:1 compressor on the loudest syllables only (6 dB at most)
     - -14 LUFS with a light 4x limiter at -2 dBFS
     - never a hard clip; it goes quieter (down to -16) before it limits hard
   - Long-form keeps its own join rule.
   - Old method (before 2026-10-28): 0.18 s pause chunks with 0.08/0.03 s gaps, and the 10/10 `word_spans` with about 0.25 s joins. The delivered 10/10s measured 16-19% dead space.
5. **Cut QC** (ship only at all four):
   - `takes.py ... --voice OUT.wav --verify` (or `verify_cut.py`): word-level whisper medium (`-ml 1 -sow`; plain mode drops short words in fast speech) against the script, 0 missing or clipped words. Diff against the delivered cut's transcript when there is one, so ASR spelling isn't mistaken for damage.
   - `zero_dead.py measure OUT.mp4`: silence (under p90 - 32 dB) 3% or less and no silence over 0.2 s; dead % (under p90 - 20 dB) reported against the references.
   - `voice_master.py check OUT.mp4`: 0 flat-topped peaks, true peak -1 dBTP or lower.
   - Every word he says gets a caption. An engine that times caption words with ASR word times must place a word whose midpoint falls in a cut by its end time, then its start, never drop it. Apple starts words early over the cut pause. On 10-29, 13 words across 5 backlog reactions were never captioned (`brand_react_render.lost_words` now stops such a render). The gate only checks that each caption word was heard, not the reverse.
   - `zero_dead.py lookoff VIDEO PIECES.json`: no piece opening or closing on him looking down or off. It reads 3 frames per edge, so a blink isn't a flag. Fix a flag with another clean take, else a cut-away over that edge, else list it for OB; never by cutting into a word. Outtakes OB flags himself are removed by script, never by hand.
6. **Graphics.** Hook text on frame 1, built only from his own words. Lists: most controversial item 1st, then 2nd. Formats: talking-head list overlays (`/talking-head-recut`), lecture cards (`lecture_*`), tier board / this-or-that (`tier_*`). Anything on frame 1 must be visible by its own CSS (a `tl.set` at 0 doesn't render frame 0).
7. **Mockups → OB's OK** (HARD RULE): a shot-by-shot page with real graded stills. Write his decisions in the chat itself.
8. **Render.** One 4K render at a time across all sessions (`*_queue_when_free.sh` / `render_when_free.sh`).
   - A queue's wait-for-free check skips its own process tree, each of its ancestors (not their other children), and `sh -c` wrapper shells, whose children carry the real work (`brand_react_render.busy_renders`).
   - Its waiting line is flushed with the time and the blocker's pid, and any pipe between an engine and its log is line-buffered (`grep --line-buffered`).
   - Before leaving a queue overnight, check what it is waiting on.
   - 10-29: the backlog reaction queue sat from 01:28 to 08:25 behind its own launcher, whose command named `feed_render.py`. Its waiting line was stuck in a pipe buffer.
9. **QC.** `verify_clip.py` plus a frame audit (`tier_render_qc.py` / `lecture_render_qc.py` sheets): face in frame, captions off his face and mouth, IG safe zones, loudness about −14 LUFS.
10. **Deliver a trial pack, never one file.** Master, music variants (`music_variants.py`) and a no-music copy. Hook and opening-frame variants go through the mock rule first. Phone copies stay under 15 MB each for the artifact page.

## Locked values
| What | Value |
|---|---|
| Canvas | 1080x1920 (9:16), 30000/1001 fps |
| Captions | 3 words, live word yellow; on the black shirt below his face (lecture: top 845); never over his mouth. Option (2026-10-20): ob-clipper `--style plate`, 3-word Anton chunks on a black plate with a thin white outline and ONE yellow keyword (the decoded tutorial-reel look) |
| How-to reels | Open on the result (the finished thing plus an overview of the steps), then numbered steps with a short label each, walked across one canvas, ending back on the result (motion library §E) |
| Safe zones | Keep text out of the top ~220 px and bottom ~420 px (IG UI) |
| Pacing | Zero dead space (OB 2026-10-27/28; pipeline step 4): cut on the first word's onset and the last word's end, every 70 ms+ pause between words out, never a speed-up. GUT 10/10 test: silence 2.9% (longest 0.16 s) against the delivered 8.8% (0.43 s), 0 words lost |
| Jump cuts | Alternate 100% / ~108-115% punch-in per shot |
| Voice | External mic through `voice_master.py`: each line levelled, gentle 3:1 on the loudest syllables, -14 LUFS, light 4x limiter at -2 dBFS, never a hard clip (the 10/10 engine hard-clipped 447 peaks on GUT H5 before 2026-10-28; fixed). AAC 256k 48 kHz (`aac_at`). Lectures (camera audio): 80 Hz high-pass + 2.5:1 levelling to −20 LUFS, then −14 LUFS with a −3 dBFS limiter |
| Music, organic/trial reels | Real music, the viral songs in the bank first (OB 11-07, M58: "use real music first for short form and the viral ones that are in the bank before ever making it yourself"), then the other bank tracks; never music we make. Match the video's tone. Give 2-3 options plus a no-music copy. ~16 dB under the voice (19 for songs with vocals), ducked 5 dB. Previews via `tier_music.py`. These reels can't be boosted |
| Music, ads/boosted | Royalty-free or licensed only, 20-24 dB under the voice, ducked. Never bake a commercial song into an ad |
| SFX | Only where a beat needs one, never obnoxious (OB 10-29: "use them when needed dont be obxious about them"): about 3-4 a minute at most, none in the first 0.5 s, varied and quiet, planned in the shot list (skill motion rule 3). From the bank first, always (OB 11-07, M59): `sfx_ob_drive`, `sfx_tai`, `sfx_real`, the T7 `sfx-library`, then Openverse. The code-made `assets/sfx/` kit and `earshot forge` only with `bank_miss` in the plan |
| Proof | On his frame, "Individual results vary", consent-screened (`proof_screen.py`). Front/side/back views; skip thong back views. Plenty of women in the longer holds |
| Brand gates | His face on screen; no AI people, voice or music; no em dashes; no "free"; first person, never "team"; no barbell squat/deadlift advice |


## Learned on EkkoVision UGC (2026-10-27): zero dead space (now pipeline step 4 for all short form)
OB approved the v4 cut method: edges from each line's own speech level (p90 - 20 dB), max 50 ms tail, dead runs of 70 ms+ inside lines cut, edges rounded to the nearest frame, every line levelled. Never speed up the audio to fix pace. Measure dead % against the reference ads before sending. Method + numbers: vault `90-References/ZERO-DEAD-SPACE-CUTS-2026-10-27.md`; code `/Volumes/OB-ARCHIVE/ekko ads/_work/scripts/ekko.py`.

2026-10-28: the v4 inner cuts (any 70 ms run under p90 - 20 dB) deleted soft words on his everyday takes ("on", "of", "it", "Not for you" heard as "no"; 22 word differences on the GUT 10/10). `zero_dead.cut_words` is the word-safe version and is the default: the same cuts between words, never inside one. `cut_line` (v4 exactly) stays for punchy UGC lines like the ekko ads.

## Optional effects menu (2026-10-28)
The editor skill's `references/motion-library.md` §G lists 20 code-built effects OB sent ("don't need to use them all the time just good to have"): one or two per reel where a beat earns it, never stacked, never over his face, built on first use after OB sees the breakdown.

## Horizontal takes (OB 2026-10-28)
"The videos I shot horizontally I want you to edit like this" (two reels: DeZPNanOD0W, Db-0516OBQM). Use `~/ob-editor/styles/split-punch-bubble.md`: the split (footage on top, him below, captions on the seam), full-frame punch-ins with one big word on the turns, and full-frame footage with his face in a round bubble. Check the camera file's orientation first (`ffprobe` width > height); vertical takes keep their usual look.
Also "love this format" (OB 10-28): **framework canvas**, `~/ob-editor/styles/framework-canvas.md` (Kallaway's Derji4txGJD). When a horizontal desk take teaches one named model with steps or tiers, that diagram carries the reel: it comes back at each step and unblurs the next label, on a black dot-grid canvas above his wide desk card, with close-ups on the turns, 1-2 caption words and 90-119 s. Brand font and yellow instead of his red.

## Brand look (2026-10-28)
**Brand look (OB picked 'Athletic' 2026-10-28): `~/ob-editor/brand/BRAND.md` + `brand.json`.** Big Shoulders Display (Black headlines, ExtraBold captions), no boxes or bubble cards, a soft shadow, OB yellow on the one word that matters, DM proof as a full-screen flash. Every overlay and caption uses it; engines still on Montserrat switch on their next use.
