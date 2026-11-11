# T22 Whiteboard framework (Alex Hormozi, @hormozi)

## MEASURED 11-07, BULK PASS (32 of his reels at 10 fps, 243 screened; library of 32 moves / 114 clips): this section beats the measurements below
OB 11-07: "bulk up reference so you really understand all of these". Decode: `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/hormozi/DECODE-V2.md`, clips: `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/hormozi/reference/REFERENCE.md`.
- **His produced overlay reels are rare:** 22 of 243 since Aug 2. Several formats rest on ONE reel (paper cards, tracker, clock): n=1 is marked.
- The Nov 3-6 table reels were 1-4 days old: re-pull plays ~Nov 10.
- **What his best reels share:** one device on screen the whole time showing how far through you are (tracker, clock, progress bar, rank slots, score, finger count) and the detail on big full-frame boards, not small stickers. Keyword CTAs raise comments, not plays.
- **Shared spine:**
  - **Title pill:** red #FC0000 on frame 0 (17/17), gone in one frame on the first cut (16/16). It holds 1.6-6.2 s on the table set (median 4.0). It moves with the set: top of frame on a pool selfie, lower at a desk.
  - **Captions:** 3-4 words, white, mostly lowercase, y 1024-1090 on the table set (y 1250 on office and podcast sets).
  - **Cuts:** 3.5-9 camera cuts a minute; the longest take is 16-31 s.
  - **Sound and pace:** -14.1 to -14.9 LUFS, 213-294 wpm. **No music, no SFX** in any talking format.
  - **CTA:** 5 of 7 table reels end on a separately filmed tag in a different shirt, 3-8 s.
- **T22 corrections (paper cards, n=1):**
  - **Pill:** holds ~4 s, not 2.3.
  - **Cards in:** fade in over 0.4-0.7 s while rising 100-300 px, starting 0.15-0.4 s BEFORE the word. Not 0.3 s after it.
  - **Cards out:** sink and fade over 0.5-0.6 s. Not a hard exit.
  - **Highlighter:** #FDFD6C pops on in one frame, 0.08-0.18 s after the word. Variants: a left-to-right wipe, and a box fill.
  - **Name card:** fades in over ~0.15 s.
  - **Framing:** only 31% of cuts change it. The rest are plain jump cuts, not a wide/tight alternation.
- **Engine TODO:**
  - `paper` enter = fade + rise 100-300 px from -0.3 s, exit = sink + fade 0.55 s;
  - highlighter `mode` pop | wipe | box;
  - the pill's `until` defaults to ~4 s or the first cut.

OB 2026-11-06 sent DfaGTlsoI7m (his 5-part VSL framework, posted that day): "Make this a template and really study Alex hormozi even more".
Evidence: T7 `OB-EDITS/2026-11-06-hormozi-study/` (`reel-DfaGTlsoI7m/MEASURE.md` = this reel measured; `DECODE.md` = his account and more reels).

## What it is
He sits at a table and teaches a framework with a count ("my 5-part..."). No b-roll, few cuts. The pace comes from hand-made paper:
1. A red title pill names the framework over the hook (frame 0 to the first cut, ~2.3 s).
2. The whole framework whips in on one board behind the pill (0.9-2.4 s), so the viewer sees the map first.
3. Each part rises on its own paper card over his chest. The items get a yellow highlighter as he says them.
4. The part he spends longest on is circled on the board, gets the most time, and gets numbered step labels (#1-#4).
5. Example lines a person would say pop as bubbles.
6. His name card shows mid-video at the first re-hook, not at the start.
7. A separately filmed CTA tag offers a lead magnet behind a comment keyword, with the bar on screen the whole time.

## Locked numbers (1080x1920, measured on DfaGTlsoI7m)
| Element | Engine | Value |
|---|---|---|
| Title pill | `pill` | Red #FC0000, white heavy italic caps (Inter Black Italic), 1-2 lines, each line its own rounded bar, stepped; centre y 1072; max 81% wide; frame 0 to the first cut |
| Board | `board` | One ruled sheet, a column per part, the deepest part circled green; in from the right ~0.18 s, out to the left at the cut |
| Paper card | `paper` | #FDFDFD sheet, soft shadow, ink #201916, Patrick Hand SC; cx 51%, 36-46% wide, top 52-70%; rises over 0.3 s just after its word; hard exit |
| Highlighter | `paper` "hl" | #FDFD6C bar behind each item ON its word, in spoken order |
| Step label | `label` | "#n" white bold at the caption spot + white strip 694 x 150 (centre y 1206) with the step in marker caps; hard swap on each step word |
| Bubble | `quote` | White comic bubble, black outline, tail; ~56% wide; centre y 1140, cx 59%; from its first word to its last |
| Name card | `lower3` | Near-black bar (85%), name in white heavy caps, grey line under; his y 1380-1545, OB's 1320-1485 (above the IG band at 1500); ~4 s at the first re-hook |
| Comment bar | `ctabar` | 'COMMENT "WORD"' white caps ~88 px on a near-black bar, centre y 1420 (his ~1440), the whole CTA tag |
| Captions | `"captions": {"style": "clean"}` | 1-3 words, white mixed case, Inter SemiBold 76, soft shadow, y 1040; italic for lines voiced as someone else ("italic"), quote marks on named terms ("quote"); none over the pill, board, labels or bubbles; over a card only if it fits just above it |
| Picture | `full` + `push` | One locked camera, long takes (his longest 16 s), alternating wide and ~1.12x tighter at each cut (`"push": [1.12, 1.12]`); no music |

## A plan, in short (see the test plan for a full one)
```json
"els": [
  {"type": "board", "at": 0.45, "until": 1.9, "top": "auto", "title": "...", "cols": [["Part 1", "item", "item"], ...], "circle": 2},
  {"type": "pill", "lines": ["MY 4-PART", "..."], "at": 0.0, "until": 1.9},
  {"type": "paper", "title": "Part 1", "items": ["...", "..."], "hl": [[0, "word"], [1, "word"]], "on": "word", "until_on": "word"},
  {"type": "label", "steps": [[1, "...", "word"], [2, "...", "word"]]},
  {"type": "quote", "text": "...", "on": "first", "off": "last"},
  {"type": "lower3", "name": "OB", "sub": "...", "on": "word", "dur": 4.0},
  {"type": "ctabar", "keyword": "...", "on": "word"}
],
"captions": {"style": "clean", "y": 1040, "italic": ["..."], "quote": ["..."]}
```
Order matters: the board goes before the pill (the pill sits on top). Cards and labels hide or lift the captions by themselves.

## Changes for OB's frame (his chest-up framing, the mic in hand)
- **The board never covers his face.** `"top": "auto"` puts it just under his chin. Hormozi's covers his face for 1.5 s; OB's rule says no.
- **Move the pill lower when the board is up** (`"y": 1330` in the test) so the two don't stack on his mic.
- **Cards sit over the mic and chest** (top ~1000). That's fine: no text reaches his face.

## OB's calls (rules this template bends, faithful by default the way T21 kept Sarah Snow's look)
1. **Bubbles.** His 10-28 rule says no rounded bubble cards ("scream AI editing"). Hormozi's example lines are comic bubbles. `"as": "caption"` swaps each one for an italic line in quotes.
2. **Fonts.** Hormozi's look is Inter + hand lettering; OB's brand is Big Shoulders. `"font": "brand"` on the pill, name card and comment bar switches them; the paper keeps the hand lettering (that's the format). The red pill is itself a rounded box (his 10-28 rule): `"box": false` on the pill drops the red bar and sets the title straight on the picture (`test/pill_compare.jpg`).
3. **The CTA.** Hormozi ends on a comment keyword for a lead magnet. OB's data says keywords buy comments, not sends; his locked closer and send line are the default. Use the bar only on a lead-magnet video.
4. **The hook.** Hormozi's spoken hook is 10 words. OB's spec is 9 or fewer, no number in the spoken line; the count goes in the pill.
5. **The name card line.** It must be a fact OB signs off on (no invented numbers).
6. **Dark bars.** The editor's M38 says no near-black behind cards. His name card and comment bar are near-black. `"bar": "frosted"` swaps in the picture under the bar, blurred and darkened to about half.

## Test (gate PASS 11-06)
`T7/OB-EDITS/2026-11-06-hormozi-study/test/T22 whiteboard framework test.mp4`, plan `T22_whiteboard.json`. It runs 14 s on C4413 in 5 whole sentences: pill + board, a paper card with the highlighter, a bubble, labels + the name card, and the comment bar. TEST ONLY, not for posting.
- **Warnings:**
  - WARN hook: about 24 words on screen in the first 3 s, from the board (his does the same).
  - WARN captions: the board and pill words aren't spoken (by design).
- **Side by side:** `test/HORMOZI-VS-OB-T22.jpg`.
- **Lessons:**
  - Plans need whole sentences. The first run failed the edges check on lines that started mid-sentence.
  - The name card and comment bar sit above the IG bottom band (1500).
  - The hand lettering gets a 2 px stroke so it reads as marker.

## His other formats (study 11-06, `DECODE.md` §0; 132 reels, median 511,992 plays at 3+ days)
His Nov 3-6 "SALES" campaign ran 4 overlay systems on the same table set: the clock (F1), the paper cards (F2, this template), the purple tracker (F3) and the stickers (F4, OB's second reel DfXyDVPopFX). The cheapest formats win plays: F11 phone-selfie rules list 3.13x, F1 table + countdown clock 2.64x. The produced ones (F3-F5) sit at or under his median on plays but get 10-25x his comment rate. Most formats are n=1 reel, so read them as leads, not proof. Next templates recommended by the study: F11, F1, F4 stickers (an add-on to F1/F2), F6 (face top, whiteboard bottom).
Script shapes (DECODE §4): A numbered rapid list in a time box; B bare numbered rules, selfie, the first rule is the hook; C this framework walk-through; D one claim, one tiny example, one action.
