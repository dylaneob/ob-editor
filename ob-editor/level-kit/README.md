# Level kit: OB's approved "level" edit, as parts you drive from a plan

OB approved the GLP level test on 11-06 ("That's what I'm fucking talking about let's go, way better"). This kit is that test's
code, made plan-driven, so another video gets the same level from its BREAKDOWN without re-deriving anything.
The first full build with it: `/Volumes/T7/OB-EDITS/2026-11-05-scripts/GLP-shot/_work/full/` (`build_plan.py` writes `plan.json`;
read it next to this file, it uses every piece).

**Don't change the tools in `~/ob-editor/bin`.** The kit calls them: `matte_hq.py` (BiRefNet), `voice_master.py`, `qc_gate.py`,
`render_slots.py`, `zero_dead.py`, `deliver.py`, `stock_pexels.py` / `stock_mixkit.py`.

## Files
| File | What it is |
|---|---|
| `lk.py` | the entry point: `python3 -I ~/ob-editor/level-kit/lk.py STEP PLAN [args]` |
| `levelkit/clock.py` | the plan, the edit clock (pieces), Apple's words on it, cues by word, word patches |
| `levelkit/pipeline.py` | the steps: recut, verify, aroll, matte, cells, audio, render, encode, review, gate, stills |
| `levelkit/engine.py` | the compositor: grid, OB cutout, depth layer, stage elements, camera, captions |
| `levelkit/fx.py` | springs (`spring`, `kick`), brand text sprites with the soft shadow, paste with motion blur |
| `blender/blocks.py` | count-up 3D blocks (mode `split`: one block splits into two shares; mode `fill`: a ghost that a share fills) |
| `blender/pen.py` | the code-modelled GLP-1 pen with its spring turn (the title's 3D object); copy it and re-model for another object |
| `examples/glp_build_plan.py` | the GLP full edit's plan builder: every element, cue, cell, camera move and SFX of a finished level edit |
| `examples/glp_lean_split_spec.json`, `glp_regain_spec.json` | the two Blender block specs it used (38% / 25% lean; 60% regained) |

## The order of work (one video)
1. **Plan the cut** from the BREAKDOWN's `edl.json`: put `raw_pieces` ([cam_a, cam_b, line_id], the last clean take of each
   line) in `plan.json`, then `lk.py recut PLAN`. It keeps each piece's words plus their rise and decay, butt-joins them (the
   gate's dead-air rule: silence 3% or less, none over 0.2 s) and proves every edge on the raw mic. A FAIL names the piece:
   give that edge back its EDL value. A pause over 0.2 s inside a piece: split the piece inside the pause (both sides of the
   same word boundary), then `lk.py verify PLAN`. Check any split by ear or with `whisper-cli` on the joined audio.
2. **Words:** Apple's words drive cues and captions. When Apple mis-spells or mis-times one (heard by whisper), add a
   `word_patches` entry; never invent a word.
3. `lk.py aroll PLAN`, then the matte (the long pole: about 6 s a frame on CPU, so 30 s of A-roll is about 1.5 h):
   `OB_MATTE_DEVICE=cpu ~/OpenMontage/.venv/bin/python -I lk.py matte PLAN`. One matte job at a time (it takes the
   machine lock and yields every 20 frames); use the Neural Engine only when `ps` shows it idle.
4. **Cells:** pick clips (his `/Volumes/T7/b roll/` first; for unisex, real women's footage from Mixkit or Pexels, downloaded
   into the video's `_work/stock/`, logged in its `PHOTO-CREDITS.txt`), then `lk.py cells PLAN`. Look at a mid-frame sheet.
5. **3D:** Blender renders (`render_slots.py wait` first). Pin each render's frame 1 to a cue in the plan.
6. `lk.py stills PLAN t1 t2 ...` while you build each beat (`LK_PREVIEW=1` lets a still borrow the nearest finished matte, so
   you can place graphics while the matte job runs; `render` never does: it skips frames whose own matte isn't done yet, so you
   can render and review in chunks behind the matte job); `lk.py audio PLAN`; `lk.py render PLAN`; `lk.py encode PLAN`.
7. `lk.py review PLAN`: a frame every 0.5 s on sheets. Look at every one. Rework anything static over 2 s, flat, or under 8/10.
8. `lk.py gate PLAN` (records the pieces and the camera map, so edges and lip sync are checked), then
   `python3 -I ~/ob-editor/bin/qc_gate.py FINAL --script <plan dir>/script_words.txt` until it passes, then deliver only with
   `python3 -I ~/ob-editor/bin/deliver.py FINAL --to "<AirDrop folder>" --script <plan dir>/script_words.txt`.

## The plan (`plan.json`)
Every time is a **cue**: a number (edit seconds), a cue name, `{"cue": NAME, "off": s}`, `{"line": ID}` (the line's first piece),
or `{"word": W, "line": ID, "n": 1, "at": "s"|"e", "off": s}`. Name the cues once in `cues` and use the names everywhere.

| Key | What |
|---|---|
| `cam`, `mic`, `words`, `lut`, `work`, `final` | A-roll file, his mic wav (camera clock), Apple's words json, grade, scratch dir, output |
| `raw_pieces`, `pieces`, `locked_pieces` | the cut before and after recut; locked pieces are kept as they are (an approved opening) |
| `word_patches` | `[{match, cam_s, w?, s?, e?}]`: Apple's slips, fixed by hand |
| `cues` | the named moments |
| `layouts`, `layout_track` | his cutout's named placements `[S, ox, oy]` (S = his frame width / 1080, top-left in 1080x1920) and `[[cue, NAME], ...]`: each change springs (2.1 Hz, 0.62) |
| `face` | where his eyes, chin and face box sit inside his frame (fractions); captions and punch-ins use it |
| `cold_open_until` | before this cue the background is his own full frame (cold open), after it the grid |
| `camera` | `shots [[cue, z0, z1, mode]]` (mode `face` centres the punch on his face, `land` lands a new section from 1.22x), `zoom_through [[from, to, z0, z1]]`, `kicks [[cue, px, f, d, zoom]]`, `top_guard [[from, to, y]]` (a punch never pushes that graphic into the IG top band) |
| `cells` | `NAME: {src, in, dur, speed, cx, cy, zoom, lut}`: 9:16 crops at 720x1280 |
| `grid` | `sets` (name -> 4 cells), `schedule` (when each set lands in each quadrant, `cascade` or `land`), `frame_base`, `pops`, `outlines`, `rack`, `top_grade`, `seams_from`, `wall_at` |
| `elements` | the graphics, drawn in list order inside their layer (below) |
| `captions` | `below_box`, `y_min`, `y_max` (his locked style; leave as is) |
| `sfx` | `[{file, cue, db, why, hp?}]`: files under `~/ob-editor/assets/`, each aligned on its own peak, db = its loudest 100 ms vs his speech |
| `music` | `{track, start, rel_db, duck_db, cuts, licence}`: the bed (below) |

## The pieces, and how to drive each one
**The 2x2 cascade with his cutout across the seam.** `grid.schedule`: a set lands per quadrant at its cue. `cascade` = each cell
snaps in from 1.10 with a warm flash (TL, TR, BR, BL about 0.07-0.18 s apart, a tick on each in the opening); `land` = the whole
set swaps under a camera `land` shot after a `zoom_through` (a new item). His cutout: `layout_track` `GRID` = [0.97, 33, 420]
(across the seam, body to the bottom edge); `STAGE` = [0.85, 162, 603] (lower, so a 3D beat owns the top); `BIG` = [1.10, -46, 360]
(the close). `pops` (one quadrant or `ALL` with a stagger: a ripple) and `outlines` (8 px #FFD400 on the cell he names) land on
words. `rack` defocuses and dims the grid for a stage beat (and wherever a word gag must not sit on a real person).
`top_grade` darkens the top under stage text instead of a box.

**The title with a 3D object (cold open).** Element `title` (`lines` of words with their spring, `dock` over the grid on the
pull-back, `lift` out on a cue, `sub` = the one disclaimer line) plus element `object3d` with `dock_title` = the title's `id`:
`drop` (spring in, landing on the click SFX), then it docks with the title, goes `hero` (centre stage, wobble) on a cue, and
`exit`s. `layer` `depth` + `stage_from` = it sits behind his head while it is part of the title, in front once it is the hero.
`play` maps the render's frames to the clock (1x, then `rate_after`). The pen frames: GLP test `_work/level/blender/pen.py`.

**Depth text behind his head.** Element `depth_word`, `layer: depth`: letters rise from behind his matte on `rise`, one light
`sweep`; optional `sag` (sags like a rope and greys) and `soft` (defocus) for a literal gag, `out` drops it away. Keep the word's
`top` so his cap overlaps its bottom. (The title lives in the same layer.)

**The count-up 3D blocks.** `blender/blocks.py SPEC.json` (mode `split` for "of the weight lost, X% was lean"; mode `fill` for
"they regained X% of it"), then element `blocks3d` with `in` pinned to the render's frame 1, `header`, and `sources` (the receipt
lines, small, left of his head, from `after`). The number counts with the motion and a sub hit lands with it (SFX + a camera
`kick` with zoom 0.012). Every number needs its source loaded today (abstract or registry record), named on screen.

**The bar drain.** Element `bar`: `label`, `yc`, `level0`, `levels [[cue, level, f, d]]` (drain, refill), `arrow {from, bounce,
dir, until}`, `moves [[cue, yc]]` (reorder two bars), `label_color`, `out`. Two bars that drain together, then one jumps first
and refills, is the protein beat in the GLP plan.

**The caption pops.** Automatic: Apple's words (with patches), 3 per group, restarting at each piece, the live word #FFD400,
under his face box, each word on a spring pop. Nothing to set.

**Punch-ins.** `camera.shots`: alternate 1.0 / 1.06-1.08 / 1.15 on emphasis words (hard cuts on the word), a slow linear push
(z0 -> z1) on holds, `land` into each new item, `zoom_through` the old grid into it. Keep a `top_guard` row for every stretch
that has a graphic near the top.

**Other stage elements.** `text_pop` (ONE JOB, NOT MY CALL: spring, optional stamp, rotation, underline, `pulse`; `box_after`
= "3. [  ]", an open loop's empty blinking slot), `item_label` (1. MUSCLE: lands big, pulses on a word, docks as a tag (`tag`
[x, top, scale]: use 0.22 for a long name); `reveal` + `slot` = the name types into its slot word by word, on his words), `chips` (the week
row, 1st/2nd, 12 months: tiles that light or outline on words, `item_in` per tile), `checklist` (rows that tick on words: habits,
the CTA's items), `card` (a typeset study receipt with a time track; never a screenshot), `keyword` (the one keyword of the
video, typed on in #FFD400, once), `lines` (receipt lines on their own).

**SFX placement.** `sfx` rows: a whoosh on a section change (`zoom_through`), a swipe on a cascade back, a pop on each cascade
cell or object landing, a paper tick or click on list items, a sub hit when a number lands (`hp` 35 Hz twice is automatic for
sub drops, ledger M55), one accent on the keyword. 20-26 dB under his speech, none in the first 0.5 s (the step refuses; pick a
sound whose peak sits at its start for the first hit). OB 11-06 ("change up sound effects, I also hated that sound effect you
used"): `audio` checks the rules and prints BROKEN if any file is used more than 3 times, if one family takes every hit, or if
a Kenney tick (`sfx_real/tick_*`, the sound A and E leaned on) is used. Families on disk: `assets/sfx_real` (Kenney CC0: click,
paper, pop, swipe, whoosh), `assets/sfx_ob_drive` (his Drive kit: whoosh, flick, camera-click, mouse-click, flash, riser,
sub_drop_boom), `assets/sfx` (made in code: pop, thud, whoosh). `assets/sfx_tai` is organic-only (no ads, no boosts): skip it
on anything that may become an ad. About 14 events a minute: over his 3-4 house rule, OB approved it on the level test.

**The music bed.** `music {track, start, rel_db -16, duck_db 5, cuts [[cue, cue]]}`: `music_mix.bed`'s levels (16 dB under his
voice's loudness, ducked 5 dB more while he speaks, 0.4 s fade in, 1.2 s out), then a dead cut (10 ms ramps) from the punch
line's first word to the next sentence's first word. Lane A only (`/Volumes/T7/OB-EDITS/music/MUSIC-LIBRARY.md`): royalty-free
tracks baked into the file; commercial songs are added in the IG app, never baked. **Open the track's Pixabay page first:**
on 11-06, 4 of the 6 Pixabay tracks checked were tagged "AI generated" (Lofi Soul, Sugar Maple Groove, Soul RnB, Soul Jazz
Sunny Cafe). Clean on that check: FunkAvenue "Feel Good Funk Anthem" (T7 root, OB's save) and Kulakovka "Lounge Soul".

**The mastering.** `lk.py audio`: his mic only (camera clock), each line ridden by `voice_master.py` like his renders (-14 LUFS,
0 clipped), placed with 6 ms edge fades; SFX mixed against his measured speech level; the music bed; peak trimmed to -1 dBFS and
the true peak held to -1.5 dBTP (the gate fails over -1); dual-mono voice. Never camera audio, never AI voice or music.

Exits: every stage element leaves with `out {cue, dy}` (a spring up and away); set `fade_out: true` on chips and text pops that
exit through the top band, or the gate's text_safe check reads them there (checklists always fade).

## Rules the kit doesn't enforce (you do)
- His face is never covered while he talks: graphics live above his head (stage y 230-640) or behind him (depth).
- Safe zones: nothing in the top 220 px or bottom 420 px of 1920 (`top_guard` handles punch-ins).
- No em dashes, no "free", no AI imagery, 3D, voice or music. Springs only; camera pushes are linear.
- Unisex: mix his clips with real women's footage; a gag about a body ("saggy and soft") only ever over a blur or over OB.
- Only lines on tape; never invent a line. Numbers: verified source on screen, or cut the claim.
