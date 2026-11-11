# Style card: OB's why-explainer, built from Trainbloom's scripting (@trainbloom), with OB's own look and Blender 3D

OB 11-04: Trainbloom has "some of the best scripting ive ever seen"; copies of his style get called out, so OB wants "our OWN upgraded version", similar but better, with our own twist, using Blender; and "trainbloom uses a lot of sound effects as well ... make sure you dont miss that and study hard".

Studied 2026-11-04 on 9 reels: the 4 OB sent (DeuNHETuzzX 5.7x his median, DTdVpZljqZh 9.8x, DfAO2hkuuXa 1.5x, DGOMHsnPQk- 8.3x pinned), 4 from OB's bank (DaA8UMROH27 2.6x, DVgo20eDnH8 2.0x, DYPpNoJOgq5 1.0x = his median, DRNKK1QjYOs 0.8x = below it) and DV_daSMjtbj (the original of the energy-drink reel, so the remake's changes are visible). His 12-month median: 79.1k likes, 1.75M plays, 79.8 s. Full decode, with a measured hit log of his sound effects: `/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/trainbloom/DECODE.md`.

## Beat sheet
**Signature moves:**
1. **The stitched skeptic open (7 of 9):** someone else's confident claim plays in a box over his torso while his face reacts above it (often holding a lime phone), 5.3-16.2 s, then a hard cut to his answer.
2. **The object on a white cube** at chest height; objects swap or pile up as the comparisons land (the can, then a coffee cup, a yogurt, an orange).
3. **The white-board cutaway:** 46-65% of every reel (median 55%) is a full-screen off-white board, one idea built element by element about once a second, his voice running over it.
4. **Two groups, one difference:** every study shown as two coloured groups, "same X", one variable changed, then a chart.
5. **The referee script** at 206-231 wpm with **zero pauses over 0.35 s** and only about 5 hard cuts a minute: his takes are joined under the boards, so no jump cut ever shows on his face.
6. **Dense, cute sound:** a music-box / glockenspiel lo-fi bed under all of his speech (about 21 dB under), **28-40 sound effects a minute** (12-24 confirmed), about 80% of graphic entrances sounded, a sub thump under each number, and the music cut out under the punch line.

**Looks (median):** source open 11%, him + cube 34%, full-screen board 55%; 9 of 9 end on his face.
**Pictures lead the words:** median 0.3 s before the word; objects 1.4-2.5 s early (at the start of the clause that names them); labels within ±0.2 s.
**A calibration warning for our tools:** `motion_score.py` reads his reels as 40-65% idle (live 3.5-6.0) because a 40 px icon landing on a calm board changes under 1.2% of the frame. With 1.75M median plays, small meaningful changes on a calm field clearly hold attention. Don't judge this template's renders on the live score alone.

## Why the scripting works (mechanics; decode §10.3)
1. **The open makes him the referee:** someone else makes the claim, the viewer picks a side in a second and stays to see who wins. He never has to attack.
2. **Every claim is paid within one breath, and every payment opens the next question:** number, "until you see" comparison, question, answer. The longest stretch without new information is about 3 s.
3. **The picture arrives a beat before the word,** so 214 wpm doesn't feel fast and a mechanism fits in 20 s.
4. **Fear first, then a mundane villain:** the scary version stated fairly, then released by an ordinary comparison. Relief is what people forward (his comments: "Sent it to my mum").
5. **The study shrinks to one variable** (two groups, one difference), so the viewer can retell it.
6. **The payoff is a permission or a rule, not a summary.** His biggest reel ends on "you don't have to be perfect to be healthy": OB's locked enemy (all-or-nothing).
7. **Remakes keep the body and sharpen the hook** (18 of his last 93 reels re-shoot a topic; 7 of 18 beat the original).
Watch-out from his comments: the hook must be paid literally ("never answered the question posed in the opening").

**The spine:** cold open (someone's belief) -> question -> verdict tease -> frame / who tested it -> steelman with the number people quote -> consequence -> re-hook #1 (about 44% in, viewer's voice, music drops) -> one mechanism, one named term -> the study (two groups) -> result + "meaning [your number]" -> re-hook #2 (65-85%) -> nuance / guardrail -> rule or permission payoff -> optional CTA. Script skeleton: vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T17.

## What would read as a Trainbloom copy (never take)
The clip in a box over the torso with a phone held up (OB keeps that look for reactions only, T03, where it already lives as intro 2); a white cube or plinth with products piling up; off-white boards in pink vs cyan (the full-screen cutaway itself is IN, it's the format; his board LOOK is out), pixel art, a bitmap font, people-icon groups, a cursor arrow; a real headshot on a cartoon body; the purple wordmark backdrop; one-word heavy rounded captions and pixel labels with a marker; a music-box / glockenspiel / 8-bit sound; his phrases (the "lucky for us, researchers" pivot, the results-shocked-the-researchers line, "the exact same X, one difference" as a catchphrase, "I'll leave it in the caption", "calculator in my bio", "until you realize", the would-be-banned-pill analogy); his caption-title format; his topics with his comparison sets (coffee cup vs can, yogurt/orange/tuna, the Twinkie professor, the safety-margin grid). No "copy" accusations turned up in the 135 comments read, so OB's warning stands on his word, not this sample.

## ENGINE 11-07: Trainbloom's board grammar + Blender (OB 11-07: "2d or 3d plz", "we wanna upgrade trainblooms style with blender")
Built from DECODE-V3 §4 (69 reels). This section beats the older plans below where they differ.
- **2D board engine:** `~/ob-editor/bin/tmpl_board.py`, plan element `{"type": "tb", "only": [BOARD_LINE_IDS], "palette": "ob", "scenes": [...]}` over a `{"name": "plate", "caps": false}` line.
  - Every measured preset: pop from a dot (0.06 → 1.10 at 0.20 s → 1.00 at 0.27 s), mask rise 0.22 s, type-on 14 chars/s, fade 0.3 s, number fill bottom-up 0.4 s (optional 2% ghost), dim to grey 0.3 s, axis draw 0.75 s, check 0.2 s, bars 0.9 s ease-in-out staggered, slide-in 0.7 s, header grow 0.6 s, gauge fill 1.0 s, waffle rows 0.3 s, scale markers 0.4 s, strike 0.2 s.
  - Scene changes: `clear` (fade 0.33 s + 3 blank frames), `promote` (one item shrinks into the title row, 1.0 s), `dock` (the scene parks on the left as a rail, 1.1 s); a hard cut when the line ends.
  - Items time to their word (onset -0.1 s); titles and placeholders 0-0.2 s after the scene opens; popped items drift ±2 px between beats.
  - Kinds: text, hero, icon/image, seq3d, axis, bars, line, gauge, waffle, scale, strike, header, tiles, progress, row.
- **Look:** `"palette": "ob"` = a warm light board #F3F1EC, ink, brand yellow fills, a yellow highlighter band behind the accent word, charcoal as the second group, Big Shoulders numbers, Inter labels. `"palette": "tb"` is his exact look (#F5F5F5, cyan/pink) and is one switch away; it reads as a copy (11-04), so only if OB asks.
- **Blender upgrade:** `~/ob-editor/bin/board3d.py`, code-built clay with real soft contact shadows (Cycles shadow catcher), on the board as item kind `seq3d`.
  - `bars`: rounded clay columns growing with his bar timing.
  - `tubes`: frosted glass capsules whose liquid fills to a level.
  - It writes `meta.json` with the projected pixel positions, so the 2D labels, day initials and level lines sit exactly on the 3D objects.
  - About 10-20 s a frame on a busy Mac (only the object's region is rendered); render once per reel, before the edit.
- **Same engine, other templates:** `"palette": "hz"` = Hormozi's violet board cutaways (T23); `"fill": false` + `"palette": "dark"` = items only, as cards over another look (Karan's navy board, T15).
- **Test 11-07:** `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/t17-test/`. `build_plan.py` writes `T17_boards.json` (C4413, 181-246 s, 3 board stretches = 58%, two with Blender), 3D clips in `3d/`, stills in `out/`.

## OB's version (template T17)
### Correction, OB 11-06 (read first)
OB on H's first full edit: "That isn't train bloom style, train bloom style has full overlay not green screen of me".
This card had applied M37 (his face on while he talks) and cut Trainbloom's signature move, the full-screen board cutaway (46-65% of every reel, median 55%), into a cutout of OB over b-roll and a top stage. That was wrong.

### The layouts (Trainbloom's shares; our look)
1. **Source open, about 11%:** someone's claim, played as uploaded (a DM or a clip), then a hard cut.
2. **Full-screen overlay, 50-55% of the runtime:** one idea per overlay, built element by element about once a second, pictures 0.3 s before their word, his voice running over it.
   - His takes join under the overlays, so no jump cut shows on his face.
   - Our overlays: full-bleed real footage (his b-roll, licensed clips) and Blender scenes (the hero: exploded object, glass, cubes, time ribbon), #FFD400 numbers that count up, ink and white type.
   - **Never** a flat black board (M38) or his off-white pink/cyan board.
3. **His face full frame, about 34%:** the telling lines, the re-hooks and the payoff.
   - Optionally a Blender object on his desk in front of his chest (our answer to his white cube).
   - It always ends on his face.
- **Never in T17:** a green-screen cutout of OB over the overlays, or a top stage with him below.
- **M37 doesn't apply to T17** (OB's word 11-06). Captions (3 words, live word #FFD400) stay on through the overlays while he talks, in a band that never covers a number or a citation.

### House rules that still apply
- No boxes or bubbles, no em dashes, no "free".
- No AI imagery: Blender models are code-built, which is fine; no 3D-emoji characters.
- Every number goes through `/evidence-check`, with the real source on screen.
- A disclaimer once at the start near meds or peptides.

### Blender 3D that beats his boards (ranked by the decode)
1. **Exploded object:** the real object on his desk opens in 3D and its contents float out as layers sized by the real dose or calories.
2. **Calorie cubes:** 1 cube = 100 kcal; stacks build on the desk as numbers land (in vs out, the deficit, the weekend that undid the week). **Tested 11-04, below.**
3. **Two clay figures** on turntables whose fat (soft, translucent) and muscle (solid) layers change as the study result lands: "same weight lost, different kind" in one shot.
4. **Safety tower:** the tested-safe dose as a tall glass column, the official limit 100x lower as a thin slice, a real day's dose as a grain at the base.
5. **Time ribbon:** a curve extruded around a 12-hour clock dial (protein, caffeine half-life), a yellow marker riding it.
6. **Warehouse shelf** (stubborn fat: front rows empty first) or a fuel gauge.
Code-drawn 2D stays for counts, labels, underlines, checks and captions. 3D carries one or two "how it works" overlays (15-25 s a reel), full frame.
### Look
OB's studio, black hat + grey shirt, Sony 4K; real objects he owns on his desk (his food scale, the actual drink, his phone on Cronometer, a consented client screenshot); his locked captions (3 words, live word #FFD400) under the chin; numbers in Big Shoulders Black #FFD400 with a small letter-spaced label above; palette #FFD400 + white + his studio.
### Proof Trainbloom doesn't have
A DM question as the cold open (no names) instead of a stitched creator; his own Cronometer days; consented client data (men 10+ lb, women 6+ lb, consent rules); OB's own story; "here's what I do with clients who [situation]", the coach's "so what" that bridges to a booked call.
### Sound (needs OB's OK: it is about 3x the current house rule of 3-4 a minute)
OB said Trainbloom "uses a lot of sound effects" and not to miss it. His density is 8-10x OB's rule; the decode's plan for OB is about **10-14 a minute** on average, 2-4 a minute in talking stretches, up to 1 a second during a 3-6 s graphic build, with one sound family per job so it reads as a system:
| Job | Sound (OB's kits) | Level under his voice |
|---|---|---|
| A number lands | `sfx_ob_drive/sub_drop_boom.mp3`, first 150-350 ms | -18 to -20 dB |
| An object or prop appears | `sfx_real/tick_*` or `music_box_chime.wav` pitched down | about -18 dB |
| A graphic element arrives | `sfx_real/pop_*` / `click_*` | -26 to -28 dB (today's rule) |
| Into a re-hook question | `sfx_tai/riser_*` or `sfx_ob_drive/riser.mp3`, cut dead on the question's last word | about -24 dB |
| Graphic to full face | `sfx_real/whoosh_*` / `swipe_*` | about -26 dB |
| Text typing | `sfx_ob_drive/mouse-click.mp3`, 4 clicks at most | about -30 dB |
Plus one music drop-out (0.5-1.5 s) on the punch line instead of ducking. Avoid his sound: music-box or chiptune beds, `arcade_game_bleep`, `hi_tech_data`, triple tings. Match each pick with `earshot rank` against the decode's snippets (`measure/sfx_hits/*.wav`). If OB says yes, the ledger rule M17 gets a T17 exception (planned per shot list, still none in the first 0.5 s).

## Blender test (11-04, no OB footage)
`/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/trainbloom/blender-test/`: `calorie_cubes_test.mp4` (2.8 s), `comp_strip.jpg`, scripts in the session scratchpad (`calorie_cubes.py` for Blender, `overlay.py` for the 2D count and sound).
- Eight #FFD400 cubes (bevelled, code-built) drop onto a dark desk with a spring landing (squash, rebound, settle), a slow linear camera push; the count (Big Shoulders Black #FFD400, "CALORIES" label letter-spaced above) lands with each cube; "1 CUBE = 100 KCAL" under them; a soft tick per landing and a short sub thump under the final number.
- Blender 5.2 Eevee headless: 84 frames at 1080x1920 in 38 s (0.45 s a frame). `motion_score`: live 9.6, idle 4%, 0 flash frames.
- The QC gate fails it on silence because it has no voice (a graphic layer, not a reel), so the video is not sent to OB; the still strip is.
- Next step for real use: render with a transparent background and composite onto his locked-off desk shot (one camera match), with shadows from a shadow-catcher pass (Cycles for that one pass, or a baked contact shadow).

## Status
- **Buildable now:** his talking head with real objects on the desk (filmed), the zero-dead cut and voice, captions, 2D numbers (`canvas_card.py` `count` or the overlay above), the top-stage layout (T02's screen + PiP), the SFX kits and `earshot`, the Blender headless pipeline (proved 11-04).
- **Needs building:** the camera-matched desk composite (and its shadow pass), the other Blender assets (exploded object, clay figures, safety tower, time ribbon, shelf), the music drop-out on the punch line, the job-family SFX plan in the shot list (after OB's OK).

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** top stage: `card` (his box, head over the edge) + a Blender RGBA sequence (`seq`, 24 2/3 calorie cubes = 2,467 kcal) + the count on its word. Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T17_blender.json`: gate PASS. Still open: the on-desk composite and OB's call on sound density.

## BULK PASS 11-07 (69 reels, 63 board reels; library of 44 moves / 186 clips): these figures replace the deep pass below where they differ
Decode `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/trainbloom/DECODE-V3.md`. Clips `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/trainbloom/reference/REFERENCE.md`.
- **Held at 69 reels:**
  - Board 64%, 3 stretches, first board ~11.6 s, 68/69 end on his face.
  - Hard cuts 374/374. Scenes 6.5 s, a new beat every ~1.2 s, text 0.35 s before its word.
  - Face ~284 px; centred column x 196-858; #F5F5F5 / #23ACFA; -14.3 LUFS.
  - Pixel type since mid-April 2026; **0 3D in 69**.
- **Corrections:**
  - Cuts land on a sentence start ~6 in 10 times, not every time.
  - Typed-on text (12-16 chars/s) runs in both type eras.
  - The faint number placeholder is Inter-era only.
  - Small motion between beats is normal (58/63).
  - Pops start from a dot.
  - Axes take 0.6-0.9 s.
  - **Photos do appear on boards** (9/69: cut-out products, real label scans, logos, photo heads), but never his live face.
  - **Captions have 3 eras:** white serif phrases (to Dec 2025), sans phrases (to Aug 2026), then big one-word captions.
- **New moves:**
  - **Face shots:** big yellow or white words across his chest (12/69), a phone notification pill (8), props multiplying, a dark cube.
  - **Boards:**
    - an element growing from a dot;
    - fill gauges (tube, battery, body outline);
    - icon grids filling row by row;
    - a spine with branches;
    - labelled bubbles around an icon;
    - a pointer on a scale;
    - strike-through then replace;
    - toggles;
    - scrolling lists and word clouds;
    - progress bars;
    - one option lighting up.
  - **Scene changes:** a diagram parks on the edge as a side strip; a scale jump (a chart shrinks and one cell grows into the next grid).
- **Remakes:** 16/69 re-shoot an older script 5-9 months later with the same board plan; the remake won only 4 of 16.
- **Hits vs flops** (test ideas, confounded with his 2026 reach drop): flops sit on boards longer (75% vs 63%), reach them sooner (7.9 s vs 13.2 s) and have a louder bed. Board pace is the same.

## MEASURED 11-07, DEEP PASS (39 reels, 30 new at 10 fps with word timings, dense grids at 10-30 fps): this section beats everything above it
OB 11-07: "trainbloom does and overlay and have amazing graphics and animations to show, he isnt on screen with the iverlays" + "do another pass that is extremely in depth". Full decode: `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/trainbloom/DECODE-V2.md`, grids `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/trainbloom/grids/` (start with `board_styles_30.jpg`). 26 of 30 are board reels; numbers below are out of those 26.
1. **Two states only:** his face full frame, or a full-screen board. **His face is on 0 board frames.** No PiP, no cut-out.
2. **Hard one-frame cuts** (154/154), each on the first word of a sentence. He leaves a board only once it is fully built.
3. **Board share median 64%** (51-81%), in ~3 stretches of ~16.5 s. First board at ~11.7 s. 29/30 end on his face.
4. **A stretch is several scenes** (~6.5 s, ~4.5 elements each). Ideas change by:
   - fade-all-out in 0.3 s and rebuild;
   - one element shrinking up to become the next title (1.0-1.3 s, ease-in-out, ~380 px travel);
   - existing elements sliding aside (0.3-0.8 s);
   - the main icon shrinking into a corner or onto a chart axis.
   - No camera pans or zooms.
5. **Pace:** a new element every 1.15-1.2 s (44 per board-minute). Something moves within 0.2 s of a board opening (64/77).
6. **Entry animations:**
   - **Pop:** to 109% in 0.17 s, settled at 100% by 0.23 s. Neighbours 0.25-0.3 s apart.
   - **Big numbers:** a ~1.5%-opacity placeholder first, then a bottom-up fill in 0.27-0.37 s; the previous number dims to #94979A.
   - **Text:** rises through a mask or fades in, 0.2-0.33 s.
   - **Lines:** axes draw from the corner in 0.65 s; checks in 0.2 s.
   - **Bars:** grow from the baseline in 0.8-1.0 s, ease-in-out.
   - **Edge slides:** 0.8 s, ~800 px/s, easing out.
   - **Second group:** splits out from behind the first in 0.5 s.
   - **Header bar:** grows from a line to full width in 0.6 s.
   - **Colour sweep:** 0.4 s, then values cascade over 1.5 s.
   - **Numbered cover tiles (12/30):** dark tiles slide off to reveal each point when he says it.
7. **Timing:** elements land a median 0.1 s before the word; titles go up 1-2 s early; numbers land on their word or +0.05 s.
8. **Layout and palette:**
   - Centred column, x ~200-850, inside y 250-1550.
   - Board #F5F5F5, cyan #23ACFA, pink #F6ADDE, red #DD5856, green #27DE44, tiles #3C3C3C, dimmed #94979A.
9. **Type and style:**
   - Inter-like sans until 14 Apr 2026; a chunky pixel font and dot-matrix numbers since 16 Apr (18/18).
   - **All flat 2D (0/30 use 3D).** Products are redrawn as illustrations or pixel art, never raw photos on a board.
10. **Face shots:**
    - Locked medium shot, face ~284 px. The product cube is in 16/30.
    - Punch-in only twice (1.5 s, on the warning line).
    - Captions only on face shots, y ~960, one word at a time since 17 Sep 2026.
11. **Sound:** ~-14.3 LUFS. A plucky music bed (louder in his recent weak reels). Whooshes and chimes on big moves (~82% of entries by the earlier hand count).
**For OB (T17):**
- Board ~64% in 3 stretches.
- Hard cuts on sentence starts.
- Several scenes per stretch, using the four scene changes above.
- The entry specs above, in our look: brand palette on a light board, Big Shoulders or a pixel font to test.
- **2D first:** Blender only where an object must turn. This revises the 11-06 "3D for 15-25 s" plan; Trainbloom himself uses 0 3D.
- Face shots locked with one-word captions.
- A quiet bed and SFX on big moves.
