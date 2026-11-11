# Style card: Dylan Page's selfie flash (@dylanpage.ning) -> OB's same-day news reaction

OB 11-04: "this creator has two styles we can copy", with DfQDZtxMo50 (the split: `dylan-page-split.md`, 11-04 pass) and DfPiAtDIaxv (this one). Studied 2026-11-04 on DfPiAtDIaxv plus the style's three outliers in his last 57 reels: DfQWFLwI3qR (2.4x his median plays), De9ISDaojhK (1.8x), Dery-PrIyn- (1.7x). The style is 13 of his 57 (23%) and runs at par with his split. Decode: `/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/dylan-page-and-2x2/DECODE-DYLAN-PAGE.md` Part 2 (sheets `sf_receipts.jpg`, `sf_titles.jpg`, `first3_sheet.jpg`).

**The one thing that separates the winners (n=4, topic is a confound):** the three outliers cut in receipts for 24-31% of the runtime, all in the "how it happened" middle. DfPiAtDIaxv, the one OB sent, has none and sits under his median (0.8x plays). So OB's version always carries the receipts.

## Beat sheet
**Signature moves:**
1. **Phone at arm's length, one take.** Front camera, handheld, chest-up and close (face 38-42% of the width, centre about 80 px right of centre, y 0.49-0.52 H), the frame drifting all the time; 0-2 jump cuts a reel, uncut stretches of 30-38 s.
2. **News furniture for the first 7-9.5 s only:** a small date chip on a title box with the story in 2-5 words plus "!" or "?". Then nothing but him.
3. **Receipts only in the middle,** as a top panel at the receipt's own aspect ratio (full width, from y 0 to a seam between 728 and 1036, or his split seam 874), him dropped underneath at the same scale. Hard cut in and out, on the noun (within ±0.2 s). 2 blocks a reel, changing every 0.7-3 s inside a block.
4. **The opinion ending is pure face:** the last 23-38 s (twist, takeaway, verdict) carry no receipt and no text.
5. **Raw delivery left in:** natural pauses kept (9-23 a reel), no captions, no music, no SFX. The live score still reaches 8.5-9.4 from handheld drift, hand gestures and his cycling LED wall.

**First 3 s:** frame 0 mid-gesture, often a hand-to-head or facepalm inside the first second; the title already up; first words at 0.0-0.57 s: an interjection to the viewer, then the outcome stated as done, or a yes/no question about it.
**Length and pace:** 55-75 s, 157-184 wpm, -14 LUFS.

## Script shape (shapes only)
| Beat | Time | Shape |
|---|---|---|
| Hook | 0-5 s | "[interjection], [it actually happened]: [subject] [did the extreme thing]." The title is this in 2-5 words |
| Aside | 5-9 s | one weary line about the times (the title leaves here) |
| How it happened | 9-35 s | "[because you know those X that have been going on]..." then the mechanism in plain words. Receipts live here |
| Twist | 25-50 s | "[only to find out] [reversal]" / "[and it doesn't end there]" / "[and an hour ago] [new development]" |
| The number | inside the twist | "[figure], [compared with the threshold]" |
| Kicker | last 5-10 s | his verdict, a rhetorical question, or a history line; ends on the last word |

## Mapping to OB (template T18)
Use it for a same-day reaction to fitness or nutrition news: a new study, a GLP-1 or FDA headline, a viral claim. The kicker is where OB's verdict line goes.
| Part | His | OB's |
|---|---|---|
| Camera | phone front camera, handheld | **his call** (ask before the shoot): the iPhone at arm's length for the raw look, or the Sony on its stand (then it's his normal talking head and the "flash" is the title + receipts + face-only verdict) |
| Frame 0 | mid-gesture, title up | mid-reaction, first word by 0.3 s, medium shot so no big face close-up at 0.4 s (PROVEN-OPENERS rule 2: his framing at 38-42% W is a close-up, so OB frames wider) |
| Title | white rounded box + red date chip | Big Shoulders Black straight on the picture with a soft shadow, the key word #FFD400, the date as a small #FFD400 word above it (no boxes, brand rule); y 300-500, above his cap; off on the first receipt |
| Receipts | top panels at native aspect | 3-6 real receipts in one "how it happened" block (the abstract, the headline, the viral post, the label), panel bottom at y 820 or less so his chin stays above y 1500; he drops under at the same scale; hard cut on the noun |
| No-face posts | a 4 s burst of full-screen posts | out (face on every post); keep every receipt as a top panel |
| Captions | none | his locked captions stay (below his chin when a panel is up); "no captions" only as a trial variable |
| Pauses | kept | cut (zero dead space, OB 10-28 hard rule); a handheld take shows jump cuts more, so cut on gestures or hide joins under receipt changes |
| Ending | face-only verdict, 20-30 s | face-only verdict, then his locked closer |
| Length | 55-75 s | 55-75 s (the myth-react band is 60-89 s) |

**Not copied:** the News Daddy neon wall and LEDs, his foam mic, caps and sweaters, the red date chip as branding, his slang.

## Status
- **Buildable now:** the cut (`takes.py`, `zero_dead`, voice master), his captions, the gate. Top panels with him dropped under exist in `ytclip_pic.py` (split at y 960) and `brand_react_render.py` (video top shots only).
- **Needs building:** receipt panels at native aspect with a variable seam and still screenshots (the same gap as the split card's "Engine gaps"), and the title in brand on the picture.

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** `full` + date and title for the opening only, a `split` receipt block in the middle (seam variable, card shown whole), a face-only verdict. Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T18_flash.json`: gate PASS.
