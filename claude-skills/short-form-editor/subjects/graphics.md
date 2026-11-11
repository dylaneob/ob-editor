# Subject: what goes on screen, and what never does

Read it with every route. OB 11-10: "no more ai slop". His most repeated complaint, seven times: "Again I hate boring just text slides" (10-30). The reviewer holds every frame against `~/ob-editor/qc/REVIEW-CHECKLIST.md` (R05, R06, R10, R11, R16, R18, R21 are this file). Picture numbers (black limits, flash rate, damping, upscale limit) are in `~/ob-editor/qc/formats.json`; `ob_job.py rules ROUTE` prints them.

## 1. Every overlay is a picture of the thing he is saying

An overlay is one of: **footage** (his own, a clip with its own sound), a **real photo** (his, a client's through the consent screen, a screenshot of the paper or app), a **chart** that counts or draws, a **drawn object** made for this line, or **3D** (Blender). It lands on or just before his word, moves while it is on screen, and leaves when the line ends.

A text-only card is never an overlay. Words on screen are captions, a one-word label on a picture, or the big kinetic word OB approved over blurred A-roll (10-30: "i like the bigger text an effects so much better": Big Shoulders Black, 470 to 640 px, word slam, brush stroke).

Before building, write in the plan what the viewer sees for every overlay (object, photo, chart, clip). A line with nothing to show gets his face, not a card.

## 2. The slop table

What OB called AI-looking, boring or cheap, what was on screen, what he approved. The reviewer compares against it. Quotes are exact.

| Date | OB's words | What was on screen | What he approved |
|---|---|---|---|
| 10-20 | "why is it just a photo here and not an animation or a cool overlay... it's just a flat screen"; "so much black space" | Photo tile beside text; half-empty cards | Full-frame cards, blurred warm fill, motion on every photo |
| 10-28 | "these bubble text scream ai editing" | White rounded bubble cards, black text | Words on the picture, soft shadow, Big Shoulders Display, yellow key word |
| 10-30 | "Again I hate boring just text slides"; "your graphics and animations are boring asf" | 103 cards, mostly plates, pills, quote cards; one fade-and-slide | Kinetic words, charts counting, a blurred warm A-roll panel |
| 11-06 | "weak and boring, the GLP one is gonna flop" | Flat stills, 2D pictogram people, dark navy boards, black cells | 3D title object, his b-roll cascading, a draining bar, counting 3D blocks, word-pop captions: "That's what I'm fucking talking about let's go" |
| 11-06 | "Not just random ass pixel photos", "glitchy" | His cutout over grapes, a jacket, a pool; upscaled sources; 24 fps on 29.97 | Blender 3D set, real paper excerpts, his footage |
| 11-07 | "its zooming in and out non stop and looks retarded" | Punch-ins on every emphasis word, pushes on stills | No zooms; the cutout holds a corner |
| 11-07 | "Why is it so fidgety?" | Springs with 15% overshoot, kick pulses | Damping at the route's minimum or above, no kicks, one render frame per output frame |
| 11-09 | "I hate your color grading honestly, no color at all", "You put blur next to me" | Flat grade, a blur box over his whiteboard, Vision-mask rims | Grade measured against reference ads; board left as shot; BiRefNet mattes |
| 11-10 | "never not show me, do overlays on screen instead" | Full-screen photo cutaways while he talked, a dark board behind the study card | His full frame, cards on his chest |

## 3. Rules that follow

1. **He is on screen every frame he talks** in reels and ads. Graphics go beside him or on his chest. A format that is full-overlay by design (named in its route file) is the only exception.
2. **Nothing over his face.** Text starts below his chin; `head_clear.py`, `face_clear.py` and `overlay_touch.py` measure it (section 7). Clear of Instagram's top and bottom bands (the route's safe bands in `formats.json`; `text_safe` checks).
3. **Type.** No dashes (long or short) in any on-screen word, and never "free" or "team". A text block stays up long enough to read; word-pop captions are exempt.
4. **No black.** No black or near-black background, panel or bar (OB 10-30: "i dont like the black background ... make it more engaging and not black"). Fill the frame: blurred warm A-roll, a paper background (OB 11-04: "can you do the paper background"), a real photo, a 3D set.
5. **No zooming.** No punch-ins, pushes, slow zooms or zoom kicks on him, stills or source clips. A scale change is a rare hard cut. UGC ads are the one exception (route `ad`). If a creator's signature move is a zoom, copy the layout and leave the zoom out.
6. **Smooth, not fidgety.** Springs damped at or above the `formats.json` value, no `kick()` pulses, one render frame per output frame for any 3D move, the cutout holds one corner at the small scale (0.85 or less) and never slides. Nothing on a panel sits still; frame one of a card is already a finished picture.
7. **One lead move with smaller ones around it.** Something meaningful moves every 1 to 1.5 s in a graphics-led reel.
8. **Frequency is the reference's, not more** (OB 10-29: "way too many overlays"). Count its overlays a minute from the decode, match it, write the number in `WORK/BREAKDOWN.md`.
9. **Footage is mixed:** men and women (OB 11-06: "make it unisex"). No pictogram or stick-figure people.

## 4. Brand look

Locked in `~/ob-editor/brand/BRAND.md` and `brand.json` (same folder): read them. Big Shoulders Display (`~/ob-editor/fonts/BigShoulders`), no boxes or bubbles, soft shadow, OB yellow on the one word that matters. HyperFrames ignores system fonts: load the brand font through its font system and look at a frame. For ads use `tmpl_ig.py` (OB 11-10: "dont put the bubble text like you also do, make it instagram").

## 5. Cutouts and backgrounds (the green-screen look)

- **BiRefNet only:** `~/OpenMontage/.venv/bin/python -I ~/ob-editor/bin/matte_hq.py IN.mp4 OUT_DIR FPS` (video, RGBA frames) or `matte_hq.py IN.png OUT.png` (one image). CPU only, one matte job at a time. Never Apple Vision (`person_mask_dir`, `person_mask`, `fg_cutout`), GrabCut, drawn masks or chroma key (Vision mattes left rims, 11-09). Never shift a matte with `ImageChops.offset`. `tmpl.py` and `brand_react_render.py` cut OB out with BiRefNet themselves (`birefnet_cut.py`, cached; `routes/templates.md` step 7). The level kit (`~/ob-editor/level-kit/lk.py`) already calls `matte_hq.py`.
- **The background is the picture of that exact sentence** (OB 11-06: "They use really good background for their greenscreens. Not just random ass pixel photos"). In this order: a Blender 3D scene of the thing (food, pack, the inside of the body); the real study page highlighted on a clean board; his own b-roll; a 4K clip of the exact move. Stock only for a reason written in the manifest (`why`), never as filler, never where his own footage fits.
- No source upscaled past the `formats.json` limit after the crop. Conform 24 fps sources 1:1 to 29.97 or 30; frame doubling reads as "glitchy".

## 6. Nothing AI-made in a video

No AI images, people, voice, music or textures; no Hyper3D, Hunyuan3D or Sketchfab AI models; HyperFrames Kokoro, MusicGen and avatar paths stay off; `media-use` only for transcription, cuts, ducking and background removal. Poly Haven CC0 for 3D assets, with a credit line. The one exception is the YouTube thumbnail (OB 11-06: "You can use ai images", "Thumbnails i dont care do anything to get views"): see `~/.claude/skills/short-form-editor/references/youtube-thumbnails.md`. A reel cover or a video frame is not a thumbnail. Doubt about a picture (glossy skin, repeating texture, malformed hands, text off a baseline) means do not use it.

## 7. Where real pictures come from (in this order)

1. **His own footage and photos** (b-roll, camera files, vault photos). His lean photo is DSC07329. C1797 to C1802 are banned (fat shown as lean).
2. **Client photos,** only after the consent screen: `~/OpenMontage/.venv/bin/python -I ~/ob-editor/bin/proof_screen.py OUT.json --cands "GLOB"` flags images that hold an excluded client. It finds the same photo only; a different photo of an excluded client needs a look against their folder. No barbell squats or deadlifts in client visuals. A number is on screen only when he says it. The proof rules are in `subjects/proof-clients.md`.
3. **Screenshots** of the paper, the app, the label, the article or the DM, with the key line highlighted (`doc_page.py` makes a real document page). Real papers over drawn ones.
4. **Wikimedia Commons** (`commons_fetch.py`, licence logged in `PHOTO-CREDITS.txt`); Pexels and Mixkit (`stock_pexels.py`, `stock_mixkit.py`) only with a `why` in the manifest.
5. **Drawn or 3D made for the line:** `blender_insert.py` for a brand-font word or number; a Blender script for an object (`~/ob-editor/styles/blender-3d-insert.md`, `~/ob-editor/blender-skills/README-OB.md`); `motion_cards.py`, `tmpl_fx.py`, `kinetic_cards.py` for charts, counters, kinetic words. Load `~/.claude/skills/short-form-editor/references/motion-library.md` at every graphics pass.

A creator's format is copied from a real decode (10 fps over 25 to 30 of their reels; `/rea-video` for a shot-by-shot teardown) before the first graphic is built; match each signature move's share of runtime.

## 8. Proof that pictures were looked at

No picture goes in unseen (OB 11-07: C1797 to C1802 shown as lean). For every photo, clip, background and cutout:

1. Make a contact sheet: `python3 ~/ob-editor/bin/frame_sheet.py VIDEO OUT.jpg T1 T2 ...` for clips, or a sheet of the stills. Save it as `WORK/qc/sheets/<row id>.jpg` (the row id is the overlay's id in the plan).
2. Look at it. Reject any frame that breaks a rule here (AI tell, black, client not consented, face cut, upscaled, fat shown as lean).
3. Build the manifest: `python3 -I ~/ob-editor/bin/qc_assets.py build WORK`. It reads `WORK/events_resolved.json` (long form), a `tmpl.py` plan (`WORK/plan.json` or `WORK/plan/plan.json`, `timeline` + `els`) or a level-kit plan, writes `WORK/qc/assets.json` (`{version, built, plan_files, declared_fonts, rows}`) and lists the rows with fields to fill in. A route that builds with its own script (reaction, FDOE, `ytclip.py`) first lists each overlay in `WORK/plan/plan_graphics.json`: `{"timeline": [], "els": [{"id": "g1", "type": "image", "t": 4.2, "dur": 2.5, "path": FILE}]}` (`type` as in `tmpl.py --help`), and `build WORK` finds it. Edit the rows by hand; `build` keeps what you fill in (a plan changed after `build` needs a new `build`): `source` is `own`, `client`, `their_clip`, `screenshot`, `stock:<site>` (with `why`), `drawn`, `chart`, `blender` or `code`; `matte` is `birefnet` wherever he is cut out; `viewed` is `true` only after step 2; `sheet` is the file from step 1 (a sheet named `WORK/qc/sheets/<row id>.*` is picked up by itself). Then `python3 -I ~/ob-editor/bin/qc_assets.py check WORK --route ROUTE`: one line per check; fix every FAIL. The gate reads the same manifest.
4. List the sheets in `WORK/BREAKDOWN.md` under "Pictures looked at", with what each overlay shows.
5. After the render, make a sheet of the finished file at every overlay (on his word and mid-move) and look again before the gate.

## 9. Checks

Machine: `text_face`, `text_lint`, `text_safe`, `captions`, the motion checks and the `qc_assets.py` checks of section 8, all in the gate (`ob_job.py gate`); `overlay_touch.py WORK`, `fit_check.py WORK`, `flicker_check.py WORK` (long-form WORK folders) and `motion_score.py FILE` (events a minute, idle time). Reviewer, by eye: R05, R06, R10, R11, R16, R18, R21 against the slop table and the approved exemplar (`~/ob-editor/qc/gold.json`, `subjects/qc.md`).

## 10. Traps

- A text card dressed up (a coloured plate, a pill, a quote card) is still a text card.
- A cutout row with no engine run in `WORK/qc/matte.json`: declare `matte` yourself and check it.
