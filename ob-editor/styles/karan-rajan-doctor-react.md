# Style card: Dr Karan Rajan's doctor reaction (@drkaranrajan) -> OB's react-and-explain reels

OB 11-04: he loves "this format when he does reactions, and how he scripts". Studied 2026-11-04: the 5 reels OB sent plus 6 extras (his #1 of 102, cellulite DcjZ7bZNOfU at 20.5x his median of 6,019 likes; beans 8.8x; processed meat 8.1x; GLP-1 3.7x; a fake call-out 3.9x; and DVWa_ncjYHj, which is the same file he reposted as DezqxN2tNhP), so 10 unique edits. Full decode with every measurement, beat map and path: `/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/karan-rajan/DECODE.md`. Start with its `sheets/KEY_states_reference.jpg`.

## ENGINE FIXES 11-07 (from the bulk numbers; gap audit `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/TEMPLATE-GAPS-11-07.md`)
- **Engine defaults now match the bulk pass:** small-him spot face 168, the peek comes in at 1.30 s, the navy bottom is #44536A.
- **Test plan `t15-test/T15_karan_v3.json`:** spots moved to [720, 855] / [495, 855], and the last line ends 0.1 s after the last word.
- **His cards can now be built with the board engine** (`tmpl_board.py`, `"fill": false`, `"palette": "dark"`, over his navy look):
  - a ruler with a moving marker (`scale` + `marks`);
  - a repeated-object array (`waffle` with `glyph`);
  - X = Y (two `text`/`icon` items and a `line` arrow);
  - numbered lists (`tiles`).
- **T15 v4 test (11-07 evening, OB "Yes, rebuild T15"):** `t15-test/build_v4.py` writes `T15_karan_v4.json` (C4413 + DdJWjTsspZw, ~44 s).
  - Nine card changes while he is small, a jump of him on each (right, left, right ... and the high-right spot once, for a ruler card below him).
  - Pictures are her real plates cut out of her own video (`assets/cut_20.0/38.0/47.0.png`, `fg_cutout`).
  - Cards are `tb` items with `"fill": false, "palette": "dark", "z": "behind"`, landing on the word with his 1-3 frame `"enter": "snap"`. Nothing animates out; each card leaves on the next card cut.
  - Cards: her day's three plates + "every day?"; a camera with a red cross; the week boxes; "fastest metabolism?" struck through to "eats less off camera"; the Cronometer targets page with its highlight; 85 g vs 130 g bars; less fat / more carbs / more fiber; a fiber ruler with "enough" at 30 g and "me" at 80 g; 80 g = 85 g.
  - Two normal shots. It ends on a callback freeze, with his box below her burned-in caption.
  - Pace: 9 card cuts in 28 s of small time (19 a minute, his 17.9) and ~46 events a minute counted (his median ~40). The first try ran 58 a minute: too many pops between cuts.
  - **Every card opens WITH its picture on the cut frame.** The first item is `"at": 0`. Only the extra beats wait for their word. v4b had an empty camera card for 1.5 s; fixed in v4c.
- **Still open:** the blue selection highlight and a live box are not built.

## BULK PASS 11-07 (70 reels, 56 reaction-explainers; library of 39 moves / 175 clips): these figures replace the deep pass below where they differ
Decode `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/karan/DECODE-V3.md`. Clips `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/karan/reference/REFERENCE.md`.
- **Held:**
  - Peek in at 1.3 s with a 0.58 s slide, a 6.4 s hold, out in ~0.27 s. Takeover at a median 8.3 s.
  - Freeze + box handoff in 48/56 (the source frozen under the box in 38/39). Box face ~170 px, held ~4.4 s.
  - 98% hard cuts to and from the normal shot. All 458 position jumps land on a picture change; no glides.
  - ~40 graphic events a minute.
  - The study strip on top (47/56). Captions at y 1210 (50/56).
  - -14 LUFS, no music, no SFX, ~221 wpm. The file ends 0.1 s after his last word.
  - "If you..." first line (23/33).
- **Shifted:**
  - **Two mid spots, not three:** face centre x ~495 (35% of small time) or x ~720 (46%), at y ~855. Use `"spot": [495, 855]` / `[720, 855]`.
  - **Board colour:** black until 14 Aug; navy since (26/34), with black back in 5 reels since 2 Oct. Either is his.
  - **Ending:** callback 25 vs normal shot 23. Since mid-August the callback leads.
  - First normal shot at ~22 s. Small blocks ~7 s. Normal shots 3.6 a minute. Callbacks in 79% of reels.
  - **No edit variable separates his top reels from his low ones** at n=56. "Shorter source = more plays" did not hold. What matters is the format itself: half his low reels drop this grammar.
- **New moves (all with clips):**
  - **His position:** top-right corner of a wide photo, with captions dropping to y ~1300 (7 reels); the 4 Nov reel's main look.
  - **Handoffs:** without the box, straight to a board, picture or normal shot (8/56). The source playing under his box instead of freezing (3/56).
  - **Drawn on pictures:** a scale or ruler with a moving marker; circles, red boxes and arrows.
  - **Cards:**
    - numbered list cards;
    - cards shrinking to the top to make room for the next one;
    - a fast 0.6 s push into a card detail;
    - "X = Y" equivalence cards.
  - **Picture types:**
    - moving b-roll on the board;
    - quantity drawn as repeated objects (160 peaches, cans of diet soda);
    - a cascading stack of study pages.
  - **The March look:** him low on a black board, full-page PubMed views.
- His two October reposts of earlier winners were identical files: counted once.

## MEASURED 11-07, DEEP PASS (41 reels at 10 fps, key moments at his native 30 fps): this section beats everything below it
OB 11-07: "dr karan, slowly brings himself in when reacting with green screen, then keeps himself small and moves around screen and either shows studies, bring him to a normal shot of no green screens or overlay, then he shows relevant photos or videos" + "do another pass that is extremely in depth". Full decode: `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/karan/DECODE-V2.md` (30 new reels: 12 top, 12 median, 6 low; 23 use this grammar), grids `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/karan/grids/`. The first 11-07 pass (11 reels) got the peek speed, the study-page layout and the low spots wrong; this section replaces it.
1. **Source alone, full frame, its own sound (23/23).** He takes over at 5.8-19.3 s (median 8.3; top reels 6.9, median reels 9.5). The source sound cuts dead on the cut.
2. **The peek (22/23):**
   - **In:** from the right edge, starting at 1.1-1.6 s, over ~0.6 s (0.5-0.83), easing out, shoulder first.
   - **Rest:** face centre ~(1000, 1380), face ~250 px, ~18% off the edge.
   - **Hold:** silent, median 6.4 s.
   - **Out:** whips out in ~0.27 s, easing in, with motion blur, ending exactly on the cut.
3. **Freeze + box (21/23):**
   - A hard cut to a frozen source frame, punched in 1.2-1.9x.
   - His box lands on the same frame with no animation: a keyed head-and-chest cut-out clipped to a straight-edged rectangle, face ~168 px.
   - Placed beside or below their face, never over eyes or mouth. Holds ~3.9 s.
4. **Next he goes SMALL, not to a normal shot:** board 10, picture 5, study 4, normal shot 4. His first normal shot comes at a median 25 s.
5. **The body is two states joined by hard cuts (220 of 226 switches are single-frame cuts):**
   - **Small:** blocks ~5.7 s, 63% of the runtime including the box.
   - **Normal full-frame shot:** blocks ~3.3 s, 23% of the runtime, ~4 a minute, face ~462 px, continuous takes, no zooms.
6. **Small him never changes size (face 148-188 px).**
   - 77% of the time his face centre sits in one band, y 800-960, at x ~490 or ~720.
   - The rest is high, y 160-480. He is never in the bottom third.
7. **He moves only by jumping on a card cut:** ~9 a minute, 97% on the same frame as the picture change. Zero glides or scale animations outside the peek. The shrink-reveal (DeUQXhMtwNs) appeared in 0 of 23 reels: a one-off, not the template.
8. **Background:** navy gradient #0F142D (top) to #44536A (bottom) in 14 reels, pure black in 9. Black is older: 9 of his 10 reels since 13 Sep are navy.
9. **Graphics while he's small: ~43 events a minute.**
   - Card cuts 18.9 a minute.
   - Pops under 0.3 s: 14.2.
   - 0.4-1 s moves (slides, scale-ups, 0.4 s fades, line draws): 6.7.
   - Over 1 s (slow push-ins, dot arrays, count-ups, building text): 3.0.
10. **Study pages (17/23):**
    - The page fills only the top 35-40% of the frame, with him small below it.
    - A yellow highlighter wipes word by word as he reads, or a blue selection is already on.
11. **Ending:** 13/23 cut back to a frozen source frame with his box for ~3.2 s, then stop on his last word.
12. **Captions:** centred at y 1210 (20/23), one line, mostly 2-4 words, white bold. Yellow keywords in only 1 reel.
13. **Sound:** -14 LUFS, no music under him, no measurable SFX.

**Engine (tmpl v3, test `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/t15-test/T15_karan_v3.json`):**
- **Peek:** `{"mode": "slide", "in": 1.2, "dur": 0.6, "out": 0.27, "face_cx": 1000, "face_w": 250}`. The source runway is at least 6 s.
- **Freeze box:** `freeze` with `box` beside or below the subject, `face_w` 168.
- **Small:** `{"name": "cut", "bg": "navy", "spot": [490 or 720, 878], "face_w": 168}`, or a high spot (y 300-480). Jump spots only when the picture changes.
- **Study:** the real page as an `image` strip across the top (y 0-750), highlighter rows on his words, him at a mid spot.
- **Pictures:** `image` (photo card, or `"cutout": true` for a clean cut-out), `count`, `days`, and charts.
- **Normal shot:** `full`, about 23% of the runtime.
- **Callback ending:** `freeze` + box on the last line.
- **Captions:** `{"y": 1210}`.
- **House-rule flags (OB's call):**
  - PROVEN-OPENERS rule 1 (two people at 0.4 s): Karan's peek lands at 1.2 s.
  - M37: the source runs 6-8 s with only the peek.
  - M38: Karan's navy board stays, per OB's "never just generic bs".

## Beat sheet
**Signature moves:**
1. **Borrowed first beat, then a freeze handoff.** The source plays first, full frame, native 9:16, with its own sound and text, untouched for 5.8-20 s (median 9.6), until its claim sentence ends. Then it freezes on a still (often punched in, 1.47x measured), its sound cuts, and his first word lands on the cut (within 0.1 s). 16 of 17 talk-over segments are a frozen source.
2. **The peek.** At 1.2-1.9 s a cut-out of him slides in from the bottom-right edge with a skeptical look, silent, and whips out at the handoff. That one element makes a repost read as a reaction.
3. **"If you..." first line** (8 of 10): it turns the source's claim into the viewer's own situation, stance in the same breath.
4. **Receipts, not authority.** He never says "as a doctor" (0 of 10). The paper's key sentence is highlighted as he reads it. Doses become household units ("about a bowl"), relative risk becomes "n in 100" on an icon array.
5. **One card per idea, on the word** (0-0.2 s, never early). Cards change 22-36 times per minute of board time; the picture changes about every 1.2 s although hard cuts run only about 12 a minute.
6. **Wall-to-wall voice, hard out.** About 214 wpm with breaths cut, no music under him, -14 LUFS, no spoken CTA; the file ends 0.1-0.2 s after the last word, and 7 of 10 return to the frozen source for the last 2.5-6 s so the loop is seamless.

**Looks (median share of runtime):** S source + peek 11%, F frozen source + his inset 7.5%, **G graphic board + his inset 56.5%**, H him full frame 19%. Order: S, F (3-7 s), then G and H alternating, ending on F (callback) or H.
**Pace:** 12.4 cuts a minute, median shot 3.4 s, 51 motion events a minute, live 8.7, idle 13%. The two weakest reels had the most idle picture (18-20%); the 20.5x reel had the least (6%) and the most events (70.6/min).
**Stance:** the top 4 all agree with or validate the source, then go bigger (an industry enemy, an evidence stack, a rescaled fear, a personal fix). His one straight "this person is wrong" reel did 1.8x.

## Measured layout (1080x1920)
| Part | Value |
|---|---|
| Him full frame (H) | selfie at eye level, face 462 px wide (43% W), face centre y 926, chin about y 1163; jump cuts with scale changes of 10% or less, no zooms |
| Peek (S) | matted cut-out, face about x 885-1120 (a quarter off-frame), y 1210-1470; slides in from the right, whips out with motion blur. Sits under IG's right action rail |
| Inset (F, G) | matted head and chest in a hard rectangle, about 377x530 at x 318-695, y 665-1195; face 172 px (16% W); centred or right of centre, away from the graphic; jumps on cuts, never slides; its bottom edge sits on the caption line |
| Board (G) | pure black or a navy gradient #0E122B to #4A5B6F; the visual in about y 200-750, the inset in the middle, the bottom zone empty in half the board frames |
| Captions | white Helvetica-Bold feel, thin outline + soft shadow, no box, sentence case, 3 words (1-4), centre y 1203-1212, just under his chin; he re-captions a source that has none |
| Colours | red bar #FC0004, yellow dots #F8E800, yellow marker #FCE000, iOS selection blue #2858C8 |

## Mapping to OB (template T15)
OB's reaction rules already fit most of this: his clip plays first (FDOE meal flow), her voice never runs under his (M42), his reaction shot is his real playback (M34).
| Part | Karan | OB's template |
|---|---|---|
| Source runway | 5.8-20 s | her clip from its first frame to the end of her claim sentence, **8 s or less on a follows job** (OB's voice inside 8 s, B41.5); longer only on a reach job |
| The peek | a stock cut-out asset, in at 1.2-1.9 s, under IG's rail | **his real watching footage of that clip** (`react_window_audit.py`, M34), cut out (`person_mask_dir`), in by 0.4 s (PROVEN-OPENERS rule 1: two people at 0.4 s), bottom LEFT or above y 1100 so IG's right rail never covers his face |
| Handoff | freeze, punch-in 1.47x, mute, first word on the cut | the same: freeze on a still that isn't unflattering for a private person, punch in 1.3-1.5x, mute on his first word (`her_mute`), first word on the cut |
| Inset | hard-cut rectangle, 172 px face, bottom on the caption line | his cut-out in a rectangle (FDOE green-screen cut-out geometry), face about 170-200 px, bottom edge on his caption line, the side away from the card |
| Board | black or navy gradient | **not black** (M38): his blurred warm studio (`studio_bg`) or the frosted blur of the card's own picture (T19). Never Karan's navy |
| Cards | bars, icon arrays, scale bars, step cards, paper + highlight, maps, line charts | the same vocabulary in brand: Big Shoulders, #FFD400 for the number and the highlight, red only for the fault; papers are real pages with PMID/DOI logged (reaction preset "Studies") |
| Paper highlight | yellow marker or iOS blue selection | an #FFD400 marker sweep in step with his voice (the iOS blue is Karan's identity) |
| Numbers | household units, "n in 100" | the same (OB already thinks in units: grams, cups, Costco portions); every number from the paper on screen |
| Captions | 3 words white under the chin | his locked captions (3 words, live word #FFD400), top at least 20 px under his chin line, measured per take |
| Audio | no bed, no SFX, -14 LUFS | the same; the source's song plays only in the runway (organic/trial; never in an ad or a boosted post) |
| Close | principle line over the frozen source, hard out | his principle line over the frozen source, then his locked closer, then a hard out |
| Length | 74-102 s | 60-89 s for a myth react (B30), up to 119 s when it teaches |

**Stance test worth running:** OB's lane is "bs silenced". Karan's data says agree-and-go-bigger beats the straight dunk. A trial pair on one source (debunk version vs validate-then-rescale version, same edit look) would answer it on OB's account.

## Status
- **Buildable now:** the source runway with its own sound, his real watching window (`react_window_audit.py`), the mute on his first word, the cut-out (`person_mask_dir`), study cards (`react_cards.py`), captions, `canvas_card.py` `count` for numbers, the gate. The short-form editor tab is extending `canvas_card.py` (clip, card, chart, verdict elements) and building `react_gfx.py` for C4416 on 11-04: check those before building any card below.
- **Needs building:** the freeze-frame handoff with punch-in; the peek slide-in from his watching footage; the inset-on-a-board layout (his rectangle cut-out mid-frame over a non-black board); a bar that grows on its number word; an icon array (n in 100); a scale bar with a moving marker; the paper highlight that sweeps with his word timings; the callback freeze at the end.
- **Not copied:** his peek asset and outfit, the navy gradient + pure-red-bar look, the iOS blue selection, his study set, his British phrasing and puns, the hyphen-run profanity mask (a dash line on screen breaks OB's no-dash rule: bleep and asterisks, or cut it), and any b-roll that might be AI.

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** source (her clip + his corner cut-out from his real watching footage), freeze (punch-in), inset on his studio board, image receipts with the highlighter, count, full-frame verdict via a look switch inside one breath. Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T15_karan.json`: gate PASS (8 edges, lips within 5 ms, -14.2 LUFS).
