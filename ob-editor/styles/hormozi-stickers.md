# T24 Stickers + labelled frames (Alex Hormozi, @hormozi)

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
- **T24 corrections (3 reels):**
  - **Stickers:** 300-440 px wide, centred y ~1460 (bigger and lower than built). A HARD one-frame pop on the noun, 0-0.12 s early, with no spring or wobble; the next sticker replaces it on the same frame.
  - **Sparkles** appear only on DfXZyinIVtU's draw-on stickers.
  - **Labelled frames:** wider and lower than built.
  - **Push-in:** 0.17 s, not 0.3; the inset is ~72% wide, not 66%.
  - **Green tag:** darker, #245A00.
  - **White-box CTA:** in one reel only.
  - The upgrade's day-box and shrinking-bar timings are in the decode.
- **Engine TODO:** `sticker` default size ~370, y ~1460 (check the IG band; text stays above 1500), `"enter": "pop"` hard; `framein` 0.72 / 0.17 s; TAG_GREEN #245A00.

OB 2026-11-06 sent DfXyDVPopFX ("2 reasons why no one is buying"): "he has so many formats and super super high quality edits".
Evidence: T7 `OB-EDITS/2026-11-06-hormozi-study/reel-DfXyDVPopFX/` (`sheet_all.jpg`, `words.json`, `sticker_library.jpg`); `../DECODE.md` (F4).
His numbers: 41 s, 271 wpm, 187,792 plays at 1 day (not settled); a sister reel DfXZyinIVtU did 0.65x at 1 day. Re-pull around Nov 9.

## What it is
A two-way split of a problem ("two reasons"):
1. **The open:** two small grey copies of him stand on the table, each tagged with one of the two reasons.
2. **The push-in:** his frame becomes a white-bordered inset over its own blurred zoom, with a red X tag that swaps to a green tag.
3. **The stickers:** back full frame, white line-drawn stickers pop onto the table one per noun he says (money, a runner with a flag, a "90 DAYS" calendar, a document whose lines get highlighted, a video window), with red X and green check emoji on the verdict words.
4. **Numbered captions:** "#1 budget", "#4 timing".

## Engine
| Element | Engine | Notes |
|---|---|---|
| Two frames | `minis` | Two grey copies of the live frame, 300 wide, standing on the table (bottom y 1480), each with a tag |
| Push-in | look via element `framein` (list it first) | Inset 66% wide, 10 px white border, centre y 880, over the frame zoomed 1.5x and blurred 22; pushes 0.92 to 1.0 in 0.3 s |
| Tags | `tag` | Sharp dark-red (150,16,16) with a red X, or dark-green (52,128,40) with an emoji; Big Shoulders ExtraBold caps |
| Stickers | `sticker` | Drawn in code, no AI art. Kinds: money, runner, calendar, doc, video, videos, dumbbell, plate, scale, steps, clock, emoji. Size 280, centre y 1360 (his sit lower, in the IG band). Spring pop from 55% with a small wobble. The doc's lines highlight yellow one by one (`"hl": [[n, word]]`). |
| Numbered captions | `"captions": {"prefix": {"word": "#1"}}` | Puts "#1" before the word in his caption |
| Title | `pill` | OB: `"font": "brand", "box": false`. Keep it below his chin (y ~760 on his chest-up frame), never on his face |

## Test (gate PASS 11-06)
`T7/OB-EDITS/2026-11-06-hormozi-study/test-T24/T24 stickers test.mp4`, plan `T24_stickers.json`. It runs 14 s on C4413 and shows the minis opener with its tags, the push-in with the tag, the doc sticker highlighting line by line, the red X and green check, "#1 fat", and the comment bar. TEST ONLY.
- **Warnings:**
  - WARN hook: 14 words in the first 3 s (the title + the two tags).
  - WARN captions: the "fiber" tag isn't spoken.
- **First-run failures:**
  - The title at y 560, then 760, sat on his face. On his chest-up frame it goes at y ~875, under the chin.
  - The tag at 1480 sat in the IG band, so it moved to 1445.

## Film for it
- Name each thing out loud ("the money", "90 days", "a case study"): every sticker lands on a spoken noun.
- Say the two reasons in the first sentence, so the opener's tags have their words.
- Leave the table in frame: the stickers stand on it.

## Upgrade pass (OB 11-06: DfXZyinIVtU "upgrade Alex more even", his "6 sales fixes" reel, 0.65x at 1 day, 858 comments)
What it adds over DfXyDVPopFX: **live diagrams drawn on the table** that act out his numbers.
| Element | His | Engine |
|---|---|---|
| Day boxes | 7 white outlined squares on the table edge, M-S under them; the last two fill as "5 -> 7" is written above in white marker; on "72 hours" the first 3 fill yellow and the rest dim | `days` (`steps` fill on words, `notes` in marker above, `dim_rest`) |
| Slot bar | A dashed outline at the old length, a "SLOT LENGTH" tag, a "15 MIN" bar | `slot` (the bar shrinks from `from` to `to` on the `change` word, value inside, label above; OB: yellow bar, no-box label) |
| Draw-on stickers | A browser "THANK YOU!" window draws on with sparkle strokes; a black play button; a phone photo | `sticker` `"enter": "draw"`, sparkles on every sticker, kinds `browser` (`text`), `player` |
| FIX tags | A small red "FIX #n" over a purple name tag, high on the chest | `steptag` `"word": "FIX", "scale": 0.62` |
| Bold numbers | "to **7**", "**72 hours**", "it's **10 minutes**"; dialogue in quote marks | captions `"bold_numbers": true`, `"quote": [...]` |
| CTA | 'COMMENT "SALES"' black bold italic in a white rounded box | `ctabar` `"style": "pill"` (OB's no-box rule: frosted brand bar stays the default) |

**Test (gate PASS 11-06):** `T7/OB-EDITS/2026-11-06-hormozi-study/test-upgrade/Hormozi upgrade test.mp4`, plan `upgrade.json` (C4413).
- **What it shows:**
  - "his week" as day boxes filling yellow and white with "MORE / LESS" then "AVG = MAINTENANCE" in marker;
  - a FAT bar shrinking on "decrease";
  - a play button drawing on with sparkles;
  - small FIX tags.
- **Warnings:**
  - WARN hook: a false alarm. The gate's reader misses the slanted brand title on frame 0, which the stills show.
  - WARN captions: the title words aren't spoken.
- **Side by side:** `UPGRADE-HIS-VS-YOURS.jpg`.

**For OB's videos:** the day row fits his weeks:
- training days;
- step days;
- a weekend that undoes the week;
- "3 days out" before a weigh-in.

The slot bar fits a portion shrinking or a number going down: calories, fat, minutes.
