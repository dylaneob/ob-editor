# Style card: split list with a tease grid and a keyword CTA (Nate Herk, @nateherkai, reel DfVEGmvgIm_) = T20

OB 11-04 sent it as "another kallaway type of edit". It is **Nate Herk**, not Kallaway. It shares Kallaway's grammar (the list's map visible from frame one, a step turn on the ordinal word, a keyword CTA) on a different body: a hard top/bottom split (T04's) instead of Kallaway's rounded card.

- **Studied:** DfVEGmvgIm_ plus 4 of his reels, ranked on his own median (29,704 plays). The 34.1x, 4.4x and 3.1x reels share the system; a 0.6x one is the contrast.
- **Measured:** layout shares, seam, caption and badge boxes, step-turn timing, the opener and close at 10 fps, cuts, motion, loudness and SFX.
- **Evidence:** `T7/OB-EDITS/2026-11-04-creator-templates-study/kallaway/extra-DfVEGmvgIm_/DECODE.md`, with sheets, key frames, the comparison reels and `reels_table.json`.

The topic (Claude plugins) is not OB's lane; the format is the reference. Copy the format and the beat order, never his words.

## Beat sheet
**Signature moves:**
1. **Tease grid on frame one.** The list's items are shown as blurred tiles labelled #1-#4 under a 2-word title ("4 Plugins"). An arrow points from the caption up to them. Tiles pop in reading order about 0.1 s apart (all in by 0.2 s), and a sheen sweeps them. It's an open loop the viewer can see.
2. **Split body.** A real screen or product sits in a hard top panel; he sits below at the same scale. The seam is at 45.7% of the height (y 877 at 1920) on 4 of 5 reels, with captions on the seam.
3. **Step turn on the ordinal word.** A hard cut and a big "#n" badge with the item's name land on "The first one / Second / Third / Fourth", within -70 to +130 ms (Kallaway's window is 0 to +150 ms).
4. **Receipts are the tool itself**: the UI in use, a counter dropping, a check popping on a finished task, a scan line down the code, a red wash on the pain phrase. The three outliers carry real screens; the one under his median leans on AI product renders.
5. **Keyword CTA device that loops.** At the CTA the opener frame rebuilds. His avatar and a comment box appear, the keyword types letter by letter (done about 0.2 s before he says it), a cursor clicks send, and a DM notification "Here you go!" drops in. The last frame is the first frame's layout, so the reel loops. This is on 3 of his 4 outliers that end on a keyword.

**Pace:** 38.6 cuts a minute, median gap 0.48 s, idle 2%, live 9.8, 240 wpm, first move 0.07 s, 0 flash frames.
**First 2 s:** the grid and title build while he says "So these 4 [things] can [10x] your [setup]"; hard cut at 0.9 s to a full-width graphic of the promise.
**Energy:** flat and fast; each item gets about 7-8 s: name, what it does, the pain it removes.
**Audio:** -14.5 LUFS, LRA 4.0, a quiet music bed, about 26 SFX a minute (whooshes on about half the cuts, pops, a hit on the red wash). OB's rule M17 is 3-4 a minute; his density is not ported unless OB says so.
**Length:** 27-46 s across his 5.

## Script structure (shapes only; his beat order, OB's words)
1. **Hook:** "These [N things] [do the big outcome]." The number lives in the tease title. /hooks bans a number in the spoken line, so OB's first line drops it (`40-Scripts/_HOOK-SHAPES-CREATOR-BANK-2026-11-04.md` §I).
2. **Item block** (N = 3-4; for OB at least 4 s each, so the map return fits):
   - "The first one is [name]."
   - "It [does X]."
   - "So that [pain removed / gain]": "instead of...", "without...", "while... less...".
   - A receipt on screen for each claim.
3. **CTA:** "Comment / DM [KEYWORD] and I'll send you all [N]." The device plays while he says it, then the loop.

Skeleton: vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T20.

## Mapping to OB (the template)
| Part | Nate | OB's T20 |
|---|---|---|
| Body | split, seam 45.7% | tmpl `split`, seam 876, his face 290 px under the seam (cap clears it) |
| Faceless screen states | 43% of DfVEG with no face, captions in pill boxes | **never** (M37): the screen goes in the split panel, or full frame with his FDOE corner cut-out (tmpl `source` look, peek corner). No caption boxes |
| Tease grid | blurred tiles #1-#4, red arrow, product logo + "4 Plugins" | `tease`: his real receipts blurred (the meal, the label, the app), Big Shoulders Black title with the number in #FFD400, #FFD400 arrow, warm dark board under it (never black, M38) |
| Step badge | mint "#2" + mono name + icon | `badge`: "#n" in #FFD400 Big Shoulders Black + the name typing on in white letter-spaced caps, bottom of the top panel |
| Captions | 2-3 words on the seam, mint key word, serif italic payoff line | his locked captions at y 925 (just under the seam), live word #FFD400; groups now reset at every cut |
| Receipts | real UI, counters, check pops, scan line, red wash | `count`, `check`, `scan`, `tint`, `image` with `outline` / `highlight` |
| CTA | comment box + IG DM notification, purple send | `cta`: "comment" or "dm" (keyword types, cursor clicks a #FFD400 send, his reply "here you go" drops in) or "follow" (profile row, cursor clicks FOLLOW, it turns FOLLOWING). Drawn in brand, no IG logo. The keyword routes through ManyChat, as his CTAs already do |
| Loop | close rebuilds the opener | a second `tease` on the CTA line with the same tiles, blurred |
| AI scenes | a pixel-art game world, a stranger at a laptop | **banned** (no AI imagery): his own shot or a receipt |
| Retro pixel title, serif italic captions | yes | no (brand font, locked captions) |

## Upgrades (each a trial variable, one at a time)
1. **The map comes back at every step** (Kallaway, 7 of 8 reels). On each ordinal word the tease grid returns for 0.75 s: tile n blinks in 2-frame states and unblurs, earlier tiles stay sharp, then the cut to the item. This is the progress bar Nate leaves out. Built: `tease` "returns".
2. **Receipts are his**, never generated: tiles and panels are his Cronometer, the label, the client's check-in (consent), the meal.
3. **One click SFX** on the CTA send/follow, inside his 3-4 a minute. Nate's 26 a minute is a separate trial, if OB wants it.

## Status
**BUILDABLE.** The whole layout runs in tmpl.py.

Not built:
- the product-UI carousel and the hub-and-spoke logo burst (bespoke);
- his PiP-over-a-typed-prompt shot (Dem0B), the face-safe way to show an app being used (future `pip` look).

## Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`)
- **New elements:** `tease`, `badge`, `cta`, `scan`, `tint`, `check`.
- **Other changes:**
  - split `top: {"board": true}`
  - sfx `"delay"` (a click after its word)
  - caption groups that reset at every cut (a fix for every template)
- **Test:** `tmpl-tests/plans/T20_split_list.json` on C4413 (Hally's day as 3 meals). The grid opens; it returns on each meal's number; the #n badges land; the scan runs on dinner; the follow device plays over the same grid at the close.
  - Result: `tmpl-tests/out/T20_split_list_test.mp4` (11.1 s), sheet `out/T20_TEST_SHEET.jpg`. QC gate PASS.
  - WARNs answered: text_safe is OCR of his EKKOVISION shirt print (the same false positive as the 11 earlier tests); hook counts the grid's tile labels as on-screen words, so keep the title to 2-3 words.
- **What the test taught:**
  - The edit's last line needs `"tail": 0.15` (new line option) so the last word decays before the file ends; the gate failed "-tion" at -30 dB without it.
  - Apple heard "This" as "Does", so the close grid stayed hidden until the plan's `fix`.
  - A line that starts mid-sentence ("..., if you want") fails edges: start it after a real pause.
  - At 1.4-1.7 s per item the 0.75 s return takes half the item; real items need at least 4 s.
- **Selftest sheet:** `tmpl-tests/selftest-t20/new_elements.jpg`.
