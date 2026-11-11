# T23 Step tracker (Alex Hormozi, @hormozi)

## ENGINE FIXES 11-07 (gap audit `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/TEMPLATE-GAPS-11-07.md`)
- **Violet board cutaways** (48-73% of his top reels): `{"type": "tb", "palette": "hz", "only": [LINE_IDS], "scenes": [...]}` over a `{"name": "plate", "cap_y": 1390}` line.
  - Same builds as T17 (heading, numbers, bars, progress, lists), white on #6D00FC.
  - The tracker, step tag, checks and captions stay on top.
  - Test `/Volumes/T7/OB-EDITS/2026-11-06-hormozi-study/test-T23/T23_tracker_boards.json`, stills `B_*.jpg`.
- **Step tag:** a 2-frame pop from 85% with no bounce (`"enter": "spring"` restores the old one); held 1.7 s by default.
- **Pill:** held 4.0 s in the plan.
- **Still open:** the countdown clock, the maroon "#n TIP" label, the persistent header, rank slots, and a score with stars.

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
- **T23 (tracker, n=1): mostly right.**
  - The panel (#7517FC) is up from 0.1 s until the CTA.
  - Step tags (#F12817, 16 measured in 3 reels) pop in 1-2 frames on the word "Step" and hold 0.9-2.3 s.
  - Full-screen summary cards cut in and out, 1.1-2.4 s.
  - His purple BOARD cutaways use a bluer violet, #6D00FC: 48-73% of the runtime, all top reels (1.67-2.55x), building item by item. The two "Comment MAP" reels got ~20x his comment rate.
  - Rank/rate reels (~1.7-1.8x): a fixed header; the icon slides to its numbered slot in 0.57 s; the score sits top-left.
  - Clock list (3.03x, n=1): a real countdown clock on the table and a maroon "#n" label swapping each tip (~3.5 s), no captions.

OB 2026-11-06 sent DfVRSAYoFPf ("5 steps to train a sales rep in 14 days"): "here are more", then "It doesn't have to be purple".
Evidence: T7 `OB-EDITS/2026-11-06-hormozi-study/reel-DfVRSAYoFPf/` (`key/`, `tracker_elements.jpg`, `words.json`); his account in `../DECODE.md` (F3).
His numbers: 69 s, 237 wpm, 457,713 plays at 2 days (0.89x his median) but 2,296 comments, the most of his Nov 3-6 batch.

## What it is
A numbered process taught to camera. A progress panel with one circle per step sits on screen the whole time, so the viewer always knows how many steps are left (future step names are blurred). Each step opens with a "STEP #n" tag. 1-3 s summary cards give the detail as a numbered list with emoji. A checklist ticks box by box ("check 3 boxes with one action"). Captions sit just above the panel, with bold accent words.

## His measured look (1080x1920) vs OB's default
| Element | Engine | His | OB default (`"theme": "brand"`) |
|---|---|---|---|
| Tracker | `tracker` | Purple #7318FC panel x 142-940, y 1376-1582, r 34; 56 px white-ring circles; done/active filled white; the line out of the active step fills over the step; future names blurred | His studio frosted under the panel, #FFD400 for done/active, Big Shoulders; y 1286-1492 (above the IG band) |
| Step tag | `steptag` | "STEP #n" white bold italic on red #F22817 (306 x 94, centre y 1195) over a purple name tag; ~2 s; no caption while up | "STEP #n" in yellow Big Shoulders Black, the name in white under it, no box; centre y 1110 |
| Summary card | `takeover` | The whole frame purple for 1-3 s: title, numbered rows (white circle, italic number), emoji at the right; tracker + captions stay on top | `"mode": "chest"`: a frosted card between his chin and the tracker, yellow number circles, so his face stays on screen (M37) |
| Checklist | `checks` | Rows at the left of the chest (box 52 px, white border on purple), each appears on its word and ticks 0.45 s later | Clear box, yellow tick, Big Shoulders |
| Title | `pill` | Red pill, Poppins Black Italic, centre y 1159, 0-4 s | `"font": "brand", "box": false` |
| Captions | `"captions": {"style": "clean", "font": "poppins", "bold": [...]}` | 2-4 words, white Poppins SemiBold, accent words ExtraBold, y ~1250 | y 1190 above OB's panel |
| CTA | `ctabar` | 'Comment "SALES"' white bold italic, no bar, y ~1528 | Brand bar, frosted, y 1420 |

`"theme": "purple"` on every element gives his exact look (test: `test-T23/T23_tracker_purple.json`).

## Test (gate PASS 11-06)
`T7/OB-EDITS/2026-11-06-hormozi-study/test-T23/T23 step tracker test.mp4`, plan `T23_tracker.json`. It runs 14 s on C4413 and shows the pill, the tracker over 3 steps, step tag #1, the chest summary card, the checklist and the comment bar. TEST ONLY.
- **Warnings:** only WARN captions (on-screen words that aren't spoken, by design).
- **Side by side:** `T23-OB-VS-PURPLE.jpg`.
- **First-run fixes:**
  - The full-screen card put text on his blurred face (gate FAIL), so OB's default became the chest card.
  - His panel sits in the IG band, so OB's is moved up.
- **Engine fixes the same day:** `apple_words` retries when the Neural Engine is busy and falls back to whisper.cpp word times. Before, it returned no words in silence, which meant no captions and no elements.

## Film for it
- Seated at a table, locked camera, chest-up.
- Say "Step one", "Step two" out loud: the tracker and the tags trigger on those words.
- One sentence per detail line, so each summary card can sit on its own sentence.
