# OB editor templates: one catalog of every format (2026-11-04)

OB 11-04: "make a skill or template for the editor for different creators and formats, like the 2x2 format, the megan style format", "obviously the kallaway one as well", "turn the other formats we have been using like the fdoe review one that we have as well and can even make some upgrades".

How to use it: pick the template from what he filmed and what the post's job is (table 1). Then load, in order: the template's **preset** (if it has one), its **style card**, PROVEN-OPENERS, and the hard rules in the editor skill (zero dead space, never cut him off, QC gate, shot list before render, one file per edit). The style card holds the measured look; this catalog holds what to pick, what exists in code, what is missing and the upgrades.

Status words: **LOCKED** (his proven layout, ships to the grid), **BUILDABLE** (engine exists, OB has approved the look or it's ready for a first trial), **PARTIAL** (some pieces exist, a shot list can be made, gaps listed), **NEEDS BUILDING** (style decoded, engine not built), **TEST** (trial A/B only until he promotes it).

Every upgrade below is a trial variable: change one thing per trial pack, judge on skip rate against a bar set before posting (trials never pooled with the grid).

## Format fidelity (OB 11-06, after H was built against Trainbloom's format: "Refine the skills and templates because clearly you are messing up")
1. **Copy the creator's layout first.** When OB picks a creator's format, that creator's signature layout is the template. Measure the share of runtime each layout takes on 3+ of their reels (face, overlay, split, card, source) and match it within about 10 points.
2. **House rules apply inside that layout:** captions, palette, no AI, cutout quality, sound.
3. **Conflicts go to OB, never to a silent fix.** House layout rules (M37 face on while he talks, M38 no black or white backgrounds) never quietly replace a creator's signature move. If one conflicts, ask OB once, before building.
   - T17 Trainbloom: full-screen overlays win (OB 11-06).
   - T19 Saraev (40% screen-only), T20 Nate Herk (14-43% faceless) and T21 Sarah Snow (69-100% voiceover over b-roll) were all adapted to keep his face on: pending OB.
4. **Every BREAKDOWN carries a "Format check vs <creator>" table:** each signature move, its measured share, ours, and done or can't.
5. **Before any agent builds:** read the creator's frame sheets in the decode folder, not just the card. A card can be wrong. T17's was.

## 0. The template engine (built 11-04 after OB's "doesnt matter just do all of them")
- **Code:** `~/ob-editor/bin/tmpl.py` (one plan-driven compositor) + `~/ob-editor/bin/tmpl_fx.py` (the shared brand elements). Read the docstrings: the plan format is there.
- **A plan** lists his lines from a word to a word (cut by `zero_dead.cut_words`: never cut off, every 70 ms+ pause out), source clips with their own sound, one look per line, elements that land on words, captions and a sound plan. Looks: `full`, `cut` (his matte over a background: his blurred studio, a frosted picture, a still, or her footage playing), `inset` (Karan), `card` (Kallaway / Saraev / T02 PiP, head over the edge), `split` (receipt on top, seam variable, drop-in), `grid` (2x2 with the clockwise cascade), `source` (her clip, his corner cut-out or Karan's peek), `freeze` (her frame punched in, him as an inset), `box` (his reaction box). A look can switch on a word inside one breath, without an audio cut.
- **Elements:** title, text (type-on, letter-spacing), count (odometer), bar, icons (n in 100), line chart, image (receipt card with the highlighter sweeping as he reads and a drawn outline), marks (arrow, curve, circle, X, dashed line), step header + checklist, burst, seq (Blender RGBA frames), map (Kallaway's returning map), slide (Megann's item device). Added for T20 (11-04): tease (blurred numbered tiles that open the reel, return on each step and close the loop), badge (#n + name), cta (comment / dm / follow device), scan (glowing sweep line), tint (colour wash), check (pop + tick). Caption groups reset at every cut. Self-test sheet: `python3 -I tmpl_fx.py selftest DIR`.
- **Sound:** his mic pieces + her clips, mastered by `voice_master` (-14 LUFS, never a hard clip), sound effects placed on words.
- **Mattes:** Apple's person matte (`person_mask_dir`) for his edges, filled inside his silhouette by the foreground matte (`fg_mask_dir`, built 11-04), so a mic or scale in his hand stays solid over her footage.
> 2026-11-11: no longer true. The template engine now cuts him out with BiRefNet through `~/ob-editor/bin/birefnet_cut.py` (OB: BiRefNet only). Apple's person matte is not used for cutouts.
- **Use:** `python3 -I tmpl.py still PLAN.json OUT.jpg T T ...` makes the shot-list stills (the shot list goes to OB before any full render); `python3 -I tmpl.py render PLAN.json OUT.mp4` renders, records the pieces and camera map, and runs the QC gate.
- **Tests (11-04, C4413 with Hally's day, no delivery):** plans and renders in `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/` (`plans/`, `out/`, `run_tests*.log`). Gate PASS on all 11: T01 audit with the 2x2 open, T03 box, T04 split, T09 grid, T13 follow pitch, T14 steps, T15 Karan, T16 marks over her footage, T17 Blender top stage, T18 news flash, T19 Saraev card. One still of each: `tmpl-tests/out/TEMPLATE-TESTS-11-04.jpg`.
- **What the tests taught (now in the code):** check a mic file's offset with `lipsync_check.py scan` before trusting a sync file (C4413's mic48k was already on the camera clock); lines that run straight into the next words are one line (switch the look on a word); a single-line edit ends at a real pause; fix Apple's mishears in the plan's `fix` ("salmon" heard as "Zen"); an element whose word isn't heard stays hidden; captions come up 0.1 s early so frame 0 has one; under a split his face sits 290 px below the seam so his cap clears it; receipt cards clear IG's top bar; the edit's last line takes `"tail": 0.15` so its last word decays before the file ends (T20).

**11-10 timing fix (gap G1 from the 11-07 audit):** every `on`-word element now starts ON its word (`tmpl_fx.trigger` default lead 0.0, was 0.15 s early). Karan, Squat U and Hormozi land on the word or up to 0.18 s after. Set `"lead"` on an element to go early on purpose (Drew's big counts use `"lead": 1.0`). Checked with stills on T15 v4: the 2467 count now appears ~0.15-0.2 s later, on the word.

**Before a shoot:** vault `40-Scripts/_SHOOT-GUIDE-TEMPLATES-2026-11-04.md` says how to film for each template (framing, takes, props, the receipts to capture).

**Creator reference library (11-07):** `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/REFERENCE-LIBRARY.md`. It has the measured grammar plus 3-6 real clips of every move for Karan (T15), Squat U (T16), Trainbloom (T17), Hormozi (T22-T24), Michael Read (T25) and Drew (T26). Watch the clips of a move before building it.

## 1. Pick the template

| He filmed | The post's job | Template |
|---|---|---|
| A day of eating to review | audit / LEGIT episode | T01 (default), T02 as the A/B |
| Vertical, reacting to a clip | myth react / debunk | T03 (vertical reaction), T15 (doctor react) when he explains a mechanism |
| Horizontal, reacting or telling a story | react, news, story | T04 (Dylan Page split; also works with no source clip) |
| A one-take reaction to today's news (a study, an FDA or GLP-1 headline, a viral claim) | reach | T18 (selfie flash with receipts) |
| Horizontal desk talk naming one model with steps or tiers | teaching (90-119 s) | T06 (framework canvas) |
| A numbered list to camera | 10/10, habits, plan | T07 Kyle panel, T08 Megann device, T09 2x2 grid |
| A short list of 3-4 things to get (swaps, apps, products, tools) with a keyword to send them | comments / DMs + reach | T20 (split list, tease grid, keyword CTA that loops) |
| A reframe or life essay: his voice over his own life on film (gym, walks, meal prep), a wide talking shot at the hook, the turn and the end | reach + shares | T21 (cinematic essay, Sarah Snow) |
| Teaching his own framework with a count ("my 4-part...") at a table: the parts on paper cards, the deepest part in numbered steps | teaching, saves, lead magnet | T22 (whiteboard framework, Hormozi) |
| A numbered process ("5 steps to...") with a progress bar on screen the whole time | teaching, comments | T23 (step tracker, Hormozi) |
| A problem split two ways ("2 reasons why...") with drawn stickers for each thing he names | teaching, comments | T24 (stickers + labelled frames, Hormozi) |
| At his desk, reacting live to a clip that plays in a card beside his head, then a verdict and "3 reasons" | react / debunk | T25 (desk reaction, Michael Read) |
| A health claim explained with receipts: one-sentence split hook + headline banner, then him, b-roll, boards and study pages full frame | reach + saves | T26 (split-hook explainer, Drew Canole) |
| At the TV with slides | lecture | T10 |
| Ranking things | tier / this-or-that | T11 |
| A long-form YouTube video exists | reels from it | T12 |
| One take pitching the account | follows from strangers (trials) | T13 |
| Teaching steps (count a meal, read a label, a recipe) | how-to | T14 |
| A "why does X happen" science answer | reach + saves | T17 (OB's why-explainer) |
| An exercise fix (wrong vs right), or a client case | saves | T16 |
| Him reading something off a screen (label, study, headline, app, Cronometer) | reach + saves | T19 (screen + card, frosted), T02's screen + PiP for audits |

Long-form keeps its own presets: `presets/youtube-longform/PRESET.md` (Dan Go teaching), `presets/reaction/PRESET.md` "Long-form frame" (Israetel PiP), `styles/johnny-harris.md` (documentary).

## 2. The templates

### T01 FDOE audit, the LEGIT series: LOCKED
- **Files:** `presets/fdoe-audit/PRESET.md` (his edits measured: cutout over the full-frame source, 20 of 20 audit breakouts), PROVEN-OPENERS rule 5 (the counted total on frame 1), `/fdoe-review` skill for the intake.
- **Code:** per-episode builders (`c4363_edit.py`, `C4370-legit10/_work/c4370_edit.py`, `make_cards.py`), `person_mask_dir`, `react_window_audit.py` (his reaction is his real playback, M34), the gate.
- **Shape:** her intro full frame with his corner cutout and the counted total, his hook inside 3 s; per meal: her clip clean, then his review (green screen and main frame alternating, Cronometer card top centre); totals card at 75-80%; one fix; closer. 127-175 s.
- **Upgrades (11-04):**
  1. **2x2 audit open** (from the 11-02 4x4 study, Oliver Niga's food grid): frame 1 is four of her meals in a 2x2 with OB's cutout across the centre seam and "I counted it: [total] kcal" on top. It stacks PROVEN-OPENERS rules 1, 3 and 5 in one frame. Builds from the 10/10 engine's grid (`tenten2.four_layers` / `tenten3_c4376_edit.grid2x2`) + the audit cutout. Trial against her-intro-first (rule 6 says her intro first is the follows winner, so this is a real test, not a sure thing).
  2. **Her real view count on her clip** (Artzen's eye pill, Adam Kelada's view pills): eye icon + her real number, bottom left inside her frame, 0-5 s. Social proof that the source is big. Real numbers only.
  3. **A meal header as the re-hook** (Mekhi's step headers): "MEAL 3: DINNER" lands on his first word of each review with the 1-2 nutrients he names ticking on under it. Replaces nothing; sits at the card's label tab.
  4. **Box-flash captions** (`box_flash.py`) against his one-word captions, one variable.
  5. **Karan's receipts on one meal** (T15): for the meal he explains, freeze her clip on its last word, punch in, and show the claim's proof on a card (a highlighted study line, the dose in a household unit) while he talks as the inset. One meal per episode, so the meal flow OB likes stays intact.

### T02 FDOE breakdown, Artzen layout + Tunde additions: TEST
- **Files:** `presets/fdoe-breakdown/PRESET.md`, `styles/artzen-breaking-reels.md`, `styles/tunde-rebuilding.md`.
- **Code:** `T7/OB-EDITS/2026-10-28-backlog/_work/fdoe_artzen.py` (built 10-30, v3 rules M36-M39), `box_flash.py`.
- **Shape:** demo first (her clip inset, his hat and face in front of it), LEGIT chalkboard title card, per meal her clip then the screen + PiP breakdown with his head popping out of the box, counter, closer.
- **Upgrades (11-04):** the step-header re-hook (T01 #3) on the screen card; the follow-pitch end card (T13 option 5) pointing at a past audit; Tunde's running counter (built as a preset idea, not in code yet).

### T03 Vertical reaction reel: BUILDABLE (also tmpl `box`)
- **Files:** `presets/reaction/PRESET.md` "Vertical reaction reels" and "The 2 intro versions"; PROVEN-OPENERS rule 1 (two people in frame 1).
- **Code:** `brand_react_render.py` (C4379's three looks, brand font, her beats cut between her words, his lines through `takes.py`), `react_window_audit.py`, `trial_variants.py` for trial packs.
- **Looks:** OB's box (her 9:16 clip 632x1124 at (224, 796) over him watching), the corner cutout over her full frame, the Trainbloom look-down intro.
- **Upgrades (11-04):** from Karan (T15): his real watching footage as a peek in by 0.4 s instead of a later reveal, her clip running to the end of her claim sentence before he talks, and a closing callback to her frozen frame so the loop is seamless; receipts for his claims in the top band (Dylan Page's rule: the picture is the proof of the sentence); her real view count pill.

### T04 Horizontal split, Dylan Page receipts: BUILDABLE (tmpl `split`, tested 11-04)
- **Files:** `styles/dylan-page-split.md` (10-30 deep study: seam y 876, one receipt per claim, three states), `styles/split-punch-bubble.md` (the older looks, extras only).
- **Code:** `brand_react_render.py` (split exists at y 960, video-only top shots), `ytclip_pic.py` (split for clips).
- **Built in tmpl (11-04):** seam 876, still cards on their own blur with a slow push, the highlighter and marks (`image`, `marks`), the label (`text`), full-frame turn lines, the slide-up, and (pass 3) the measured drop-in (a wipe that pushes him down), **the zoom-out on every hard cut to him full** (`{"name": "full", "zoom": 1.22}`), per-item title cards (`top: {"title": [...]}`) and the list counter (`itemno`).
- **Still missing:** the whip, glitch and blur moves between receipts, the audio-only waveform card, the odometer card, the 0.6 s photo burst timer in the top panel.
- **Upgrades (11-04, from DfQDZtxMo50, card section "11-04 pass"):** the split works for a story with no source clip at all (85% split); the round-trip breath for a turn or verdict line (panel slides up 0.30 s, him full frame one line, drops back in over 0.5 s); 0.6 s photo bursts for time-span lines (2 a reel at most); an odometer count-up card; a typed name lower third; quote cards with the #FFD400 highlighter following his voice. Missing in code: all of these plus the card's earlier engine gaps.

- **List mode (11-04 pass 3, DfVXmUnBInZ, OB: "the zoom in and out the 50/50 everything"):** a numbered news list ("the N changes coming after X"). Hook in the split with the label; per item the ordinal line, a title card naming it, receipts per claim, the counter bottom left; one clip with its own sound for the strongest item; him full frame (zoom-out) on an item's number, after a clip, and to close. Test `tmpl-tests/plans/T04_list_zoom.json`: gate PASS. Card section "11-04 pass 3".

### T05 Split + punch word + face bubble + chest infographics: BUILDABLE (extras)
- **Files:** `styles/split-punch-bubble.md` (Variants A and B). Use only when OB asks; T04 is the default split.
- **Code:** `brand_react_render.py` (split, punch word, bubble with `BUBBLE_ZOOM` 2.1).

### T06 Framework canvas, Kallaway: PARTIAL (the returning map is now `tmpl_fx` `map`)
- **Files:** `styles/framework-canvas.md` (Derji4txGJD decoded 10-28; DfUhxJqxLxP 11-04).
- **Code:** `canvas_card.py` (built 11-04: black dot-grid canvas, him in the wide rounded card at y 1240-1720, `title`, `count`, `rows`; records the camera map so lip sync is measured). Not wired into an engine.
- **Missing:** the returning diagram that unblurs its next label per step (the signature move), the step pill, thumbnail grid with views badges, phone mockup, document stack, VS cards, the full-frame close-up cut on the step turns.
- **Expanded 11-04 to 8 reels** (his outliers up to 33.6x; card section "Expanded study 2026-11-04"): a 21-element library with boxes and timings, a ranked build list (1 returning map v2, 2 phone + view-badge grid, 3 line chart, 4 doc + highlight + checklist, 5 VS cards), and three fixes to the built look (no card glow; a fainter 15-16 px dot grid; the blink in 2-frame states so the gate passes it). The short-form editor tab owns `canvas_card.py` and is extending it on 11-04; it has the build list.
- **Upgrades (11-04):** Megann's pyramid is the same device (a layer fills per item), so T08 can borrow it; Mekhi's step header doubles as the step pill; 70% canvas + card, 30% full frame on the telling lines.

### T07 10/10 list, Kyle panel: BUILDABLE
- **Files:** `T7/OB-EDITS/2026-10-24-tenten/REFERENCE-EDIT-SPEC.md` "Template K", `ref-study/kyle/KYLE-EDIT-SPEC.md`; vault `40-Scripts/_10-10-SCRIPTING-RULES-2026-10-24.md`.
- **Code:** `tenten2.py` / `tenten3_c4376_edit.py` look K (`k_layers`), in the 10/10 project.
- **Shape:** locked-off camera, a 2.23:1 panel (~920x412) at the top the whole video, a new picture every ~3.6 s landing 270 ms before its word, lowercase captions, no music.

### T08 Megann numbered plan: BUILDABLE (look MX; plan-driven with tmpl + `slide`)
- **Files:** `styles/megann-numbered-plan.md` (index + upgrades), the measured spec on T7.
- **Code:** look MX in `tenten3_c4376_edit.py`.
- **Upgrades:** in the card (real prop with screen replacement or his notebook, pyramid via `canvas_card.py`, typewriter cards, box-flash test, held proof on the teased item).

### T09 2x2 grid ("4x4"): BUILDABLE (look 4X4; the upgrade in tmpl `grid`, tested 11-04)
- **Files:** `styles/two-by-two-grid.md` (index + 12 upgrades from Eugene Healey's DcKfX0ijg_g + 4 variants: list, plan with keyword, food grid, essay with background swaps), `ref-study/fourx4/4X4-EDIT-SPEC.md`, T7 `four-by-four-format-study-upgraded-2026-11-02.pdf`.
- **Top upgrades:** the grid cascades to its contrast set when the hook pivots (fixes the GUT 4x4's still first 3 s); the grid photos argue the hook (the topic's objects, then their cost); a cut-out twice the size holding the hero prop, paid off in the last 5 s; for essays, the body runs on his talking head with background swaps on concrete nouns.
- **Missing:** the cascade, the big live cut-out, background swaps on a talking-head body, the image card behind his head, the keyword type-on, a plan-driven engine.
- **Code:** look 4X4 in `T7/OB-EDITS/2026-10-24-tenten/_work/tenten2.py` (`four_plan`, `four_layers`, `render`) with the feed wrapper `tenten3_c4376_edit.py` (`grid2x2` for the 2x2-per-item micros version); his three 10/10 feed posts use it (OB 10-29 on two of them: "wow so much better").

### T10 Lecture at the TV: BUILDABLE
- **Files:** editor skill "Lecture reels"; tools `chunks.py` .. `lecture_render.py`.
- **Upgrades (11-04):** the Kallaway returning map (put the lecture's model on the TV slide once, then return to it per point) and Mekhi's step header for numbered points.

### T11 Tier list / this-or-that: BUILDABLE
- **Files:** editor skill "Tier-list and this-or-that reels"; `T7/OB-EDITS/C4079-C4080/TIER-NOTES.md`.
- **Upgrades (11-04):** the ranking hook shape ("Rating [X] so you don't waste your [Y]", hook bank) and a held last item (the most controversial goes first per OB's list rule; the S-tier reveal is held to the end).

### T12 YouTube to Instagram clips: BUILDABLE
- **Files:** `presets/yt-clips/PRESET.md`, `styles/rico-appetizer-clips.md`. Under 1:30 always (M33).
- **Code:** `ytclip.py`, `ytclip_pic.py`, `ytclip_yt.py`.

### T13 15-second follow pitch: BUILDABLE (end card tested 11-04)
- **Files:** `styles/follow-pitch.md` (from OB's two 11-02 PDFs). Trials only.

### T14 Steps with proof cutaways (Mekhi Carter handoff): BUILDABLE (tmpl `step`, tested 11-04)
- **Files:** `styles/step-tutorial-mekhi.md`. The 1.2x speed-up is replaced by zero-dead cuts (OB's rule).
- **Missing:** a reusable step header + checklist card type; a screen-recording intake.

### T26 Split-hook explainer (Drew Canole): BUILDABLE (tmpl `split` ob_push + `banner` + `leak` + `full` drift + `plate` + `bcard` + box captions; test 11-07)
- `styles/drew-canole-split-hook.md`, decode `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/drew/DECODE-V2.md` (30 reels). Dylan Page's split used for the hook sentence only, a red 2-line banner on the seam, a light leak + riser into sentence 2, then full-frame alternation with slow drift, box karaoke captions, receipts (10 of his 11 tops), a music bed at -11 dB and a follow pill.

### T25 Desk reaction (Michael Read, DfRw4sMtL7P): BUILDABLE (tmpl `source` peek mode `card` + `title` + `full` push; stills 11-07)
- `styles/michael-read-desk-reaction.md`. His setup is OB's (desk, arm mic, studio wall): the other creator's clip plays with its sound in a rounded 9:16 card on the wall beside his head while he reacts live full frame under a 2-line "TOPIC / WARNING" title; hard cut with a 1.3x punch-in to his verdict, then one take with jump cuts alternating 1.0x / 1.13x, floating receipt cards beside his head. One breakout reel (19.9x his median), thin sample.

### T15 React and explain (Dr Karan Rajan): BUILDABLE (tmpl `source` + `freeze` + `inset`, tested 11-04)
- **11-07: the 11-04 build does NOT match Karan (OB: "horrific at finding their editing styles").** Measured at 10 fps: head peek from the bottom-right edge that stays; a small freeze box placed off their face; him small (face ~176 px) as a cut-out on a dark board, moved to one of 4 spots beside each picture of the sentence; the PubMed page full screen; normal full-frame shots; the shrink-reveal. Card section "MEASURED 11-07", evidence `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/HOW-THEY-EDIT.md`. Rebuild before the next T15 edit.
- **Backgrounds (OB 11-06 night):** Karan's board is clean, and what sits on it is the receipt (the real paper with the highlight), a crisp product cut-out or a photo that is the sentence. Never random stock. Same floor as T16: no upscale over 1.1x, no 24 fps without a 1:1 conform.
- **Files:** `styles/karan-rajan-doctor-react.md` (10 edits decoded 11-04), T7 decode `.../karan-rajan/DECODE.md`; scripts in vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T15 (pick the stance first).
- **Shape:** her clip with its own sound to the end of her claim (8 s or less on a follows job), his real watching footage as a peek from 0.4 s, freeze + punch-in + mute on his first word, then mostly a graphic board with him as an inset (cards on the word: bars, icon arrays, paper highlights, step cards), full frame on the turns, a callback to the frozen source, closer.
- **Code that exists:** `react_window_audit.py` (his real playback, M34), `her_mute`, `person_mask_dir`, `react_cards.py` (studies), `canvas_card.py` `count`, captions, the gate. The short-form editor tab is adding clip, card, chart and verdict elements to `canvas_card.py` and building `react_gfx.py` (11-04, C4416): reuse those.
- **Missing:** the freeze-frame handoff with punch-in, the peek slide-in, the inset-over-board layout (non-black board), growing bar, icon array, scale bar, the paper highlight synced to his words, the callback freeze.
- **Difference from T03:** T03 keeps her clip playing in his box; T15 freezes it and moves to a board of receipts. T03 is a react, T15 is a react that teaches.
### T16 Client case / reply-to-a-clip fix (Squat University): BUILDABLE (tmpl `cut` over her footage + `marks`)
- **11-07:** in 6 of 8 reels his cut-out is big (face 258-410 px) and fixed low in a bottom corner (in the other 2 he talks over the case footage, no cut-out); only the background moves, and it is always the exact anatomy, the exact exercise or his real patient. Never stock. Card section "MEASURED 11-07", evidence `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/HOW-THEY-EDIT.md`.
- **Files:** `styles/squat-university-fix-demo.md` (8 reels decoded 11-04), T7 decode `.../squat-university/DECODE.md`; scripts in vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T16.
- **Shape:** the source's intro with OB's cut-out silent in the corner, a reply hook, then OB as a cut-out over real footage (his client screens, his demo of the fix) for the rest; red fault / green fix / yellow force marks; a fix with an exact dose; a re-measure on camera as the payoff. Never a full-frame talking head in his version, so it reads as a different format from T03.
- **Code that exists:** the FDOE audit cut-out builders + `person_mask_dir`, `explainer_cards.py` `annot` (circle), zero-dead cut, the gate.
- **Missing:** a mark layer for moving footage (arrows, X, dashed line, red/green border lines), the two-band split at y 782 (anatomy or proof on top, demo below), an anatomy source for exercise reels (licence or Blender), the notepad diagnosis card.
- **Rules:** never a barbell back squat or conventional deadlift as his advice (they can be the clip he reacts to); client faces and names only with consent (Client Y: no photos; Client P: never name or face); no stock doctor photos.
- **Backgrounds (OB 11-06 night, after B and D: "They use really good background for their greenscreens. Not just random ass pixel photos"):**
  - What's behind him is the inside-the-body picture or the exact object or move, at full quality: Blender 3D (anatomy from BodyParts3D once OB OKs the download; objects modelled in code, as in `D/_work/level/bl3d/dset.py`), his own demo b-roll, or the real study page.
  - Random stock filler is out, and so is any source upscaled over 1.1x or 24 fps without a 1:1 conform. B and D v1 failed both.
### T17 OB's why-explainer, Trainbloom format (full-screen overlays + Blender, OB's own look): REBUILT 11-06 after OB's correction
- **ENGINE 11-07 (read first):** Trainbloom's board grammar is built: `tmpl_board.py` (element `tb`: his enter presets, scene changes, word timing, OB's warm light board) plus `board3d.py` (Blender clay bars and glass tubes with real shadows, label positions in `meta.json`). Card section "ENGINE 11-07"; test `T7/OB-EDITS/2026-11-07-style-truth/t17-test/`. This replaces "Missing" below. The 11-06 "never an off-white board" line is superseded by the 11-07 plan (brand palette on a light board); his exact pink/cyan look is `"palette": "tb"`, used only if OB asks.
- **11-07 deep pass (39 reels):** board time median 64% in ~3 stretches, his face on 0 board frames, all flat 2D, a new element every ~1.2 s; earlier 11-07 figure (34-65%) superseded; one diagram builds on one canvas, a new element every 1-1.5 s. Card section "MEASURED 11-07", evidence `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/HOW-THEY-EDIT.md`.
- **Files:** `styles/why-explainer-trainbloom-upgrade.md` (9 reels decoded 11-04, with a measured hit log of his sound effects), T7 decode `.../trainbloom/DECODE.md`; script skeleton in vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T17.
- **Shape:** someone's belief (a DM, a clip, the object in his hand) -> question -> fear stated fairly with the number -> an everyday comparison -> re-hook -> one mechanism -> the real study, two groups one difference -> OB's own proof -> re-hook -> a permission payoff on all-or-nothing -> closer. 214 wpm, no pauses, pictures a beat before the word.
- **Layout (OB 11-06: "That isn't train bloom style, train bloom style has full overlay not green screen of me"):**
  - About 50-55% of the runtime is full-screen overlays with his voice running over them, one idea built element by element about once a second.
  - About 11% is the source open; the rest is his face full frame on the telling lines. It always ends on his face.
  - His takes join under the overlays.
  - **Never** green-screen him over the overlays or under a top stage: H v1 did, and OB rejected it.
  - M37 (face on screen while he talks) does NOT apply to T17.
- **Overlay look is ours, not his:** full-bleed real footage and Blender scenes, #FFD400 + ink type, never a flat black or off-white board.
- **Never like his:** off-white boards in pink/cyan, pixel art or a bitmap font, the white cube or plinth, people icons, a music-box bed, the clip over the torso with a phone (stays a reaction intro only), his phrases and topics.
- **Proved 11-04:** the Blender headless pipeline (calorie cubes, 84 frames at 1080x1920 in 38 s, live 9.6, 0 flash frames), with the count in Big Shoulders and a sound per landing.
- **Missing:** the camera-matched desk composite with a shadow pass, the other 3D assets (exploded object, clay figures, safety tower, time ribbon), the music drop-out.
- **OB decides:** the sound density. Trainbloom runs 28-40 effects a minute; the plan for OB is 10-14 in job families, about 3x the 3-4 house rule (M17).
- **Calibration:** `motion_score` calls his reels 40-65% idle while they average 1.75M plays; judge this template on its own reference, not the live score.
### T18 Same-day news reaction, Dylan Page's selfie flash: BUILDABLE (tmpl `full` + `split`, tested 11-04)
- **Files:** `styles/dylan-page-selfie-flash.md` (DfPiAtDIaxv + the style's 3 outliers, 11-04).
- **Shape:** one take, frame 0 mid-reaction, a 2-5 word title for the first 7-9 s, one "how it happened" block of 3-6 real receipts as top panels at their own aspect with him dropped under, then a face-only twist and verdict, closer. 55-75 s. His winners carry receipts for 24-31% of the runtime; the receipt-free one OB sent sits under his median, so OB's version always has them.
- **OB decides:** iPhone at arm's length (the raw look) or the Sony (then it's his normal talking head with this structure).
- **Code that exists:** the cut, captions, the gate; top panels in `ytclip_pic.py` / `brand_react_render.py`.
- **Missing:** native-aspect receipt panels with a variable seam and still screenshots (shared with T04), the brand title on the picture.

### T19 Screen + card on a frosted background (Nick Saraev): BUILDABLE (tmpl `card` on `frosted:`, tested 11-04)
- **Files:** `styles/screen-card-saraev.md` (DfUtovOvQ8U, OB 11-04 "another one").
- **Shape:** his real screen in a glowing card on top, OB in a wide rounded card below, 1-3 caption words between; the background is a blur of the screen itself; numbers pop as count-up cards; the phrase he reads gets outlined; close-up only for the verdict and the closer. His version has 40% screen-only with no face. OB's version kept his face on (M37), the same adaptation OB rejected for T17 on 11-06: ask OB whether T19 goes back to the creator's 40% screen-only.
- **Code that exists:** T02's screen + PiP layout and `studio_bg` (`fdoe_artzen.py`), `canvas_card.py` card + `count`, captions, the gate.
- **Missing:** the frosted background from the screen's own pixels, the glass number card, the rounded phrase outline that draws on, a typed search/prompt bar, the phone-mockup fan.
- **Not ported:** the doubled script (the 72 s file holds the 36 s script twice) unless OB wants it as one trial variable.

### T20 Split list with a tease grid and a keyword CTA (Nate Herk): BUILDABLE (tmpl `split` + `tease`, `badge`, `cta`, tested 11-04, gate PASS: `tmpl-tests/out/T20_split_list_test.mp4`)
- **Files:** `styles/split-list-nate-herk.md` (DfVEGmvgIm_, OB 11-04 "another kallaway type of edit", plus 4 of his reels against his median). Evidence: `T7/.../2026-11-04-creator-templates-study/kallaway/extra-DfVEGmvgIm_/DECODE.md`.
- **Shape:**
  - 3-4 item list, 27-46 s, about 7-8 s per item.
  - Frame one: the items as blurred tiles #1-#n under a 2-word title, an arrow from the caption up to them.
  - Split body (seam 45.7%, the same as tmpl's 876). Each item's step turn on the ordinal word: a hard cut + a "#n" badge with the name.
  - Receipts are the real thing in use (counters, check pops, a scan line, a red wash on the pain).
  - CTA: the keyword types into a comment/DM box, a cursor clicks send, his reply drops in, over the rebuilt opener, so the reel loops.
- **Evidence for the shape:**
  - His 34x, 4.4x and 3.1x reels share the system.
  - The 0.6x one leaned on AI product renders, where the outliers show the real tool.
  - The faceless share (14-43%) doesn't separate them. M37 kept OB's face on, the same adaptation OB rejected for T17 on 11-06: ask OB before building T20 faceless or not.
- **OB's version:**
  - His receipts blurred in the tiles.
  - #FFD400 badge and arrow; locked captions under the seam.
  - Never faceless; no caption boxes; no AI scenes.
  - The CTA device in brand: comment, dm or follow.
  - Upgrade (Kallaway): the grid returns for 0.75 s on each step word, the tile unblurs. Items need at least 4 s for it.
- **Code that exists:**
  - tmpl `split` (+ `top: {"board": true}`).
  - tmpl_fx `tease`, `badge`, `cta`, `scan`, `tint`, `check`, plus `count`, `image` outline/highlight.
  - sfx `delay`.
- **Missing:** the product-UI carousel and hub-and-spoke logo burst (bespoke); a PiP look (his face framed above a typed prompt, Nate's Dem0B) for showing an app in use with his face on.
- **Not ported:** his 26 SFX a minute (M17); the serif-italic caption line; the pixel title.


### T21 Cinematic essay (Sarah Snow, @iamsarahsnow): BUILDABLE (tmpl `broll` + `full` push + serif captions, tested 11-06)
- **Files:** `styles/sarah-snow-cinematic-essay.md` (10 reels decoded 11-06, build list B1-B8, OB conflicts), T7 `OB-EDITS/2026-11-06-sarah-snow-study/DECODE.md` (measurements, beat maps, the 15-shot b-roll list), script structure in vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T21.
- **Shape:** his wide talking shot with a slow push at the hook, then his voice over his own b-roll (69% of her winner), back to camera on the turn and the end; one glowing serif phrase (1-3 words) at a time in the empty part of each picture, landing 0.2 s before the word; emphasis words (about 1 in 10) big italic; a picture cut clears the text; calm pace.
- **Built 11-06:**
  - look `broll` (his clip full frame, landscape cropped 9:16 at `cx`, graded with the plan LUT, his voice running; the gate counts it as not-his-lips);
  - `full` + `"push": [1.0, 1.13]` (linear, text stays still);
  - captions `{"style": "serif", "y", "emph", "stack_until", "max_words"}` -> `FX.serif_captions`: EB Garamond (`~/ob-editor/fonts/EBGaramond`, OFL) 74 px, off-white with a two-layer glow, dark shadow-hue text on bright backgrounds, emphasis blur-in, the ragged hook stack, kept off his head (face box grown to his cap);
  - `"cap_y": "auto"` per shot -> `FX.quiet_band` (the band with the fewest edges);
  - b-roll cuts on words with a line's `"switch"`.
- **OB 11-06: keep all of her style** (serif, music bed, voice over b-roll, breaths, loop ending, wide framing; he shoots the b-roll). Built the same day: `"keep_pauses": 0.8` (her breaths stay; the gate's pause limit follows it) and `"music": {file, start, rel: -18, duck: 0}` (her bed through `music_mix.bed`). Test v2 (pauses + piano bed): gate PASS. Not built: the T21-only gate checks (B8); the loop ending needs no code (plan the last line).
- **Test (11-06, gate PASS):** `T7/OB-EDITS/2026-11-06-sarah-snow-study/test/T21 cinematic essay test.mp4` (plan `T21_essay.json`, one line with 5 word switches on C4413 + Frame.io b-roll). WARN hook is a false alarm: the gate's text reader misses the thin serif, frame 0 has text. Engine fixes from the test: switches take `near` for a repeated word; `fix` takes `=Word` for an exact spelling.
- **Film for it:** wide with headroom (his face about 130-220 px wide, sky, wall or ceiling above him) so the text has empty space; on his usual chest-up framing it falls under his chin. B-roll list: DECODE §12.

### T22 Whiteboard framework (Alex Hormozi, @hormozi): BUILDABLE (tmpl `pill`, `board`, `paper`, `label`, `quote`, `lower3`, `ctabar` + clean captions, tested 11-06)
- **Files:** `styles/hormozi-whiteboard-framework.md` (locked numbers, plan sketch, OB's calls), T7 `OB-EDITS/2026-11-06-hormozi-study/reel-DfaGTlsoI7m/MEASURE.md` (the reel OB sent, measured), `DECODE.md` there (his account, more reels, his formats).
- **Shape:** one locked camera at a table, few cuts (his longest take 16 s), framing alternating wide and ~1.12x tight. A red title pill names the framework over the hook; the whole framework whips in on one board behind it; each part rises on a paper card over his chest with a yellow highlighter on each item as he says it; the deepest part gets #n step labels; example lines pop as bubbles; the name card shows at the first re-hook (~10 s); a separate CTA tag runs a comment bar. No music.
- **Built 11-06:** tmpl_fx `pill`, `board` (`"top": "auto"` = under his chin), `paper` (`"hl"` highlighter in spoken order), `label`, `quote` (`"as": "caption"` = no bubble), `lower3`, `ctabar`; tmpl captions `{"style": "clean"}` -> `FX.clean_captions` (Inter SemiBold 76, italic and quote-mark phrases, hidden or lifted by the elements through the frame's caption block). Fonts: `fonts/PatrickHand` + `fonts/Inter` (both OFL). Backups `*.bak-2026-11-06-pre-t22`.
- **Test (11-06, gate PASS):** `T7/OB-EDITS/2026-11-06-hormozi-study/test/T22 whiteboard framework test.mp4` (plan `T22_whiteboard.json`, C4413, 5 whole sentences). WARN hook: the board puts ~24 words on screen in the first 3 s (his does the same); WARN captions: the board and pill words aren't spoken (by design). First run failed edges only because test lines started mid-sentence: T22 plans use whole sentences.
- **Film for it:** seated at a table, lav mic (hands free: he counts on his fingers), plain light wall, head in the top third with chest and table in frame (the cards need the lower 45%). One take per part; the CTA tag separately.

### T23 Step tracker (Hormozi, DfVRSAYoFPf): BUILDABLE (tmpl `tracker`, `steptag`, `takeover`, `checks`; tested 11-06, gate PASS)
- `styles/hormozi-step-tracker.md`. OB 11-06 "It doesn't have to be purple": every element defaults to `"theme": "brand"` (frosted studio, #FFD400, Big Shoulders, no boxes, the summary card on his chest so his face stays on screen); `"theme": "purple"` is Hormozi's exact look. Test `T7/OB-EDITS/2026-11-06-hormozi-study/test-T23/`.

### T24 Stickers + labelled frames (Hormozi, DfXyDVPopFX): BUILDABLE (tmpl `sticker`, `tag`, `minis`, `framein`, caption `prefix`; tested 11-06)
- `styles/hormozi-stickers.md`. Drawn sticker library in code (money, runner, calendar, doc with highlighter, video, dumbbell, plate, scale, steps, clock, emoji via Noto Color Emoji OFL). Test `T7/OB-EDITS/2026-11-06-hormozi-study/test-T24/`.

## 3. Caption layers (pick one per edit; any template)
| Layer | Look | Tool |
|---|---|---|
| Locked (default) | 3 words, live word #FFD400, Big Shoulders ExtraBold, on the shirt | ob-clipper / engines |
| One word (Megann, audits) | one word at a time, key nouns #FFD400 1.3x | engines' caption step |
| Box flash (Artzen) | each word lands as a 2-frame white box, stacked blocks | `box_flash.py` |
| Seam (splits) | his locked captions at the seam | `brand_react_render.py`, `ytclip_pic.py` |

## Elements usable in any template
- **Blender 3D insert** (`styles/blender-3d-insert.md`, `bin/blender_insert.py`, pack docs `~/ob-editor/blender-skills/`): a 3D word, number or object springing in, as RGBA frames. The paper look is ink with yellow sides; the dark look is yellow with a glow. Proved 11-04.
