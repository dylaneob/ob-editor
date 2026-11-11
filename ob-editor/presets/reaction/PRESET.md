> SUPERSEDED 2026-11-10: the rules for this format now live in `~/.claude/skills/short-form-editor/routes/reaction.md`.
> Where this file disagrees, the route file and `~/ob-editor/qc/formats.json` win. Kept for history only.

# Preset: OB reaction videos (long-form, Doctor Mike style, mirrored)

> **HARD RULE (OB 11-09): never touch the original clip.** Play it whole, first frame to last, full screen. The only thing allowed is OB added over it by green screen. No trims, boxes, hook text, stamps, captions, graphics, on-screen credit, music, SFX, grade, zoom, crop or speed change. The credit goes in the post caption. This overrides everything below.


Load this first for any OB reaction edit. Locked values as of 2026-10-17 (C4353 / C4354 / C4356 reactions). The detailed runbook lives in memory `reference_short_form_editor_setup` (Reaction edits section) and in the docstrings of `~/ob-editor/bin/react_*.py`. Style decode: `T7/OB-EDITS/references/drmike-T8CNeQ-cbo0/_STYLE-DECODE.md`. Thumbnails follow `feedback_reaction_thumbnail_style` (RP / Cody Ko / Doctor Mike, not Dan Go).

**Openings: read `~/ob-editor/presets/PROVEN-OPENERS.md` first** (v0 2026-10-22, from his skip rate on 6,130 reels). It sets the defaults for frame 1 and every hook or opening variant in a trial pack.

## Pipeline (lock each stage before the next)
1. **Sync the mic.** `sync_av.py --audio-only` writes the synced mic without re-rendering. Use `sync_steps.py` if the take was recorded while a render ran.
2. **Find every clip play.** `clipmatch.py`, then `react_bleedmap.py` for exact plays, pauses, replays and aborted starts at 0.1 s steps.
3. **Gate.** `react_gate.py`: while a clip plays, its clean file audio is heard and his mic stays muted until he speaks. A mic word that matches the clip transcript within ±0.9 s is bleed, not OB.
4. **Cut.** `react_cutlist.py WORK --start S --end E`. Clip playback is never trimmed. Outside playback, pauses of 0.8 s or more shrink to ~0.4 s, and loading/searching silence is dropped.
5. **Cut QC.** `react_qc.py build|compare` must report 0 clipped words. `react_listen.py` checks bleed around every play, resume and removed span. OB flags outtakes himself; remove them with a change script (dry run first), never by hand.
   - **Dead air includes silent look-downs inside a line:** C4407 24:00 kept 1.1 s of him looking down between "everything at" and "once" (breath above -48 dB, no word). The gate's lipsync check (M36) failed it as "not found within 1 s": a piece with no word has no lips to match. Cut such a piece.
   - **Scan the cut's own transcript for retake cues with two recognizers** (C4407, 11-03): whisper medium on the cut's mic, and Apple `speech_words words`. Grep for "cut that", Claude (heard as cloud, clock, clawed), "editor" and "prompt". Expect 0.
     - The DTW transcript the cut was built from had dropped "Cut that, Claude. Just put 47% on the side." and put a "Claude" 15 s from where he said it, so both stayed in the first render.
     - The live gate's Apple-only cue scan came back empty because the Neural Engine was busy.
     - Check each retake join by transcribing the joined audio, not the DTW word times.
6. **Graphics.** `react_resolve.py` → `react_prep.py` (per-event face detection for overlay slots) → `react_cards.py --mock` → `react_mock_shots.js`. Fact-check flags stay `"held"` until OB answers and never render.
7. **Breakdown → OB's OK** (HARD RULE): `react_stills.py` + `react_breakdown.py` + `html2pdf.js`.
8. **Render.** `react_render.py WORK SRC OUT [--range S E]`. Hold the mux while OB still reviews.
   - **Parallel (Mac mini, 11-03):** it renders 3 graphics at a time with 2 HyperFrames workers each and encodes 3 units at a time. Leave `OB_JOBS` and `OB_HF_WORKERS` unset; 6 workers on one graphic at a time was the slower setting. C4407 test (60 s, 10 graphics, another render running): 108 s instead of 183 s, the sound byte-identical and the picture within 49 dB.
   - **Kept units:** the units and scratch live on the internal SSD in `~/ob-scratch/<work dir name>` and stay after the render (`REACT_SCRATCH` picks another place). A re-render after notes encodes only the shots and graphics that changed: the same 60 s again took 6 s. Units are keyed on the camera file's size and date too, so a re-exported take never reuses old ones.
   - **The shared ceiling:** the 4K HEVC encoder (~55 fps) is one media engine for every render on the Mac, so two long-form renders at once each slow down while they encode units. Count running jobs with `render_slots.py list` (up to 3).
   - **See-through graphics: tested 11-03, parked.** Rendering overlay graphics as transparent layers composited in the unit's one encode gained ~1% on 60 s of C4407 (81.6 vs 82.4 s) with no visible picture difference; zoom cuts split 4 of 10 graphics across shots. Only worth it if renders become encoder-bound. Patch and numbers: `~/ob-editor/tools/parked/patch_react_alpha.py`.
9. **QC.** `react_render_qc.py`: sync within one frame (33 ms) inside full-frame OB shots, dead/black frames, loudness, frame sheet.
10. **Deliver.** The master plus trial-pack variants for any short cut-downs (`feedback_trial_variant_packs`).

## Locked values
| What | Value |
|---|---|
| Layout | Split screen mirrored from Doctor Mike: OB in the LEFT panel (x 0-2505 = source x 668-3173), the clip in the RIGHT panel (x 2565-3780). He looks down to frame-right, so he appears to watch it (OB 2026-10-16). Full-screen OB when he pauses, alternating wide / punch-in (`crop=3200:1800:320:120`) |
| Audio | Clip audio from the file, not his mic. While he talks over a clip, the clip keeps playing 8 dB down and his mic gets spectral bleed suppression |
| Grade | Per-take `WORK/lut.png` (his pick from 3 warm options), else warm tan. Golden skin, never pink-neutral |
| Graphics | Doctor Mike grammar on OB's card system: term labels, meme pops, lowercase joke subs, verdict stamps. All on OB's side, never over the clip |
| Studies | Journal, year, title, authors, finding, PMID + DOI, optional chart, on the side layout (his frame slides left, uncropped; panel x 1640-3840) |
| Proof | `overlay` straight on his frame at slots from his detected face (flash / quad / pair / pairw / one), "Individual results vary".<br>Plenty of women in the longer holds. Skip chats that show a client's face avatar.<br>Screen against your consent exclusion list |
| Encode | `hevc_videotoolbox` at 24 Mbps by default (`OB_CODEC` / `OB_VBR`) |
| Master | Two-pass loudnorm, LRA 11, plus a gentle expander, about −14.5 LUFS |
| SFX | Only where a beat needs one, never obnoxious (OB 10-29; skill motion rule 3). `OB_SFX=1` mixes every saved cue, so pick the few first and plan them in the shot list |
| Music | None on reactions unless OB asks: the clip audio carries the video |

## Vertical reaction reels (OB 2026-10-21)
OB on C4356's reel: "you last time put it in a square rather than a normal frame like my others". The clip was cropped into a 740x840 rounded panel copied from Shiv Wilson's layout.
- **The clip always keeps its whole 9:16 frame.** Never crop it to a square or to a panel's aspect.
- **Default: OB's own box.** The 1230/0719 reels put the clip in a plain box, 632x1124 at (224, 796), with its bottom on the frame edge, over him watching. His face stays in the top third (`react_watch` crop). Square corners, no outline. In code this is `lecture_viz.CX..CH` and `lecture_render.PANEL_W x PANEL_H` (cards keep their own `PX..PH` zone). Before/after still: `T7/OB-EDITS/C4356-react/REACTION-FRAMING-FIX (Oct 21).jpg`.
- **Alternative:** full-frame clip plus OB as a small cutout at the bottom (left or centre). This is his audit breakouts' geometry (a cutout over a full-frame source in 20 of 20 audit breakouts, ledger B8.18) and @thesoberbodybuilder's watching segment (DecqvGJyxiE). It needs the person-matte cutout; see the FDOE preset.
- @trainbloom holds the clip like a phone recording pinned over his torso, which is the same idea as OB's box.

## The 2 intro versions (OB 2026-10-21: "1 and 2 is the main i dropped 3"); every episode ships both as trials
They differ only in the first seconds; the rest is the same edit (memory `feedback_trial_variant_packs`). Mock: `T7/OB-EDITS/FDOE-PRESET (Oct 21) 3 intros mock.jpg`.
1. **Corner cutout:** "greenscreen and im in the corner just looking then me as the full frame". Her clip full frame, OB cut out in the bottom-left corner watching (no talking), then a hard cut to OB full frame at the desk for his first line. Cutout values as in Locked values.
2. **Trainbloom style:** "looking at the reaction video". OB full frame (the `react_watch` 1.3x framing, face in the top third) looking down at the clip, which plays in the tall 9:16 box over him: 632x1124 at (224, 796), bottom on the frame edge, never cropped (the reaction preset's box).
3. ~~**Corner clip:**~~ DROPPED (OB 10-21: "i dropped 3"). Kept for reference only: "me looking into the corner and the video playing". OB full frame, the clip small in a top corner: 380 px wide 9:16 (380x676) at (660, 140), thin white outline. He looks INTO that corner while it plays, so film this take glancing up-right (or flip the corner to wherever he looked).

## Horizontal reaction takes (OB 2026-10-28)
A reaction shot horizontally (C4396, C4397 on 10-27) uses `~/ob-editor/styles/split-punch-bubble.md` instead of the three C4379 looks: her vertical clip full frame with his face in a round bubble while she talks, cropped into the top half while he talks over it, and full-frame punch-ins with one big word on his turns.

## Long-form frame: Dr. Mike Israetel's (OB 2026-11-03, C4407)
OB: "No out the from like dr Mike isrealt for reactions". This replaces the split above for widescreen long-form.
- **The frame:** OB full frame the whole video. While a clip plays it sits in a white-bordered box in the top corner on the side he looks to: top right at the desk set (mirrored from RP's top left). Layout `pip` in `react_render.py`, values in `react_geom.PIP_*`, memory `feedback_reaction_frame_israetel`.
- **Box size** (OB 11-03: "Make them bigger, don't cover me but make the reactions bigger"): as big as it can go without touching him.
  - Then "still bigger as well": 16:9 clip 2000 px wide (52% of the frame), 9:16 clip 1960 px tall, never cropped.
  - 26 px white border, 60 px from the edges, the source credit under it.
  - His frame under the box is punched in from the left (`PIP_D` 950, x1.33), which moves him left.
  - Check every clip shot with `bin/person_extent` (Apple Vision person mask): 60 px clearance at least.
- **Under the box:** his watching footage from a still look at his spot (M34). `watch/pick_windows.py` picks the latest still window per clip; check every window frame by frame. Where he held still under the clip's length, use another watching stretch, never a pause between his lines.
- **Graphics** sit on full-frame talking shots only, never over a clip shot.
- **His mic's green LED** lights his grey shirt and his chin on the desk set, and the warm grade made it louder. Fix it in the LUT (C4407 `lut_nogreen5.png`, two passes):
  - Pass 1 works on the input colour (hue 62-190°, even faint green).
  - Pass 2 works on the graded colour (hue 75-190°).
  - Each pulls the colour to its own luminance: grey for a lit grey shirt, warmed back toward skin where the input was skin plus green.
  - Skin, wood, lamps and the plant come out unchanged.
  - Two versions failed: v1 (input only) left faint green, and v4 (protecting strong greens for the plant) let the LED glow back in.
- **Explainer graphics while he talks** (OB 11-03: "like markusfit and dr mike"): at Markus's pace, about 5.7 a minute. See memory `feedback_reaction_explainer_graphics` and `react_cards.markus` (chap, fq, tags, num).
- **Clear of his face over the whole event** (11-03, C4407 render 1: tag icons on his ear at 3:59 and 8:51 while he leaned right):
  - `react_prep` measures his face every 0.25 s across each event (`face_x0`/`face_x1`), not one still at 1 s.
  - `react_cards` places zones, proof slots, stamps and pops 230 px past that span. Long tags wrap to two lines rather than drop under 100 px.
  - Check: `react_gfx_face.py WORK OUT` reads every graphic at 4 fps (the gate reads every 2 s). It exits 1 on the graphic's own words over his face, and 2 when they sit within 140 px of it in 2+ frames. A single-frame near is listed for an eye check.
    - It only counts readings that share a word with that graphic's copy. OCR reads his ear and hair as letters ('T riA&', 'II') and glues them to the title beside him: C4407 render 3 got 1 false FAIL and 18 false NEARs, all clear by eye.

## Brand look (2026-10-28)
**Brand look (OB picked 'Athletic' 2026-10-28): `~/ob-editor/brand/BRAND.md` + `brand.json`.** Big Shoulders Display (Black headlines, ExtraBold captions), no boxes or bubble cards, a soft shadow, OB yellow on the one word that matters, DM proof as a full-screen flash. Every overlay and caption uses it; engines still on Montserrat switch on their next use.
