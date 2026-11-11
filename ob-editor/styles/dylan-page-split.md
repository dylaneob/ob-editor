# Style card: Dylan Page's split (News Daddy), OB's split for horizontal takes

**OB 10-30 ~22:35:** "really really study this because this is what I meant for a the split screen style when I shoot horizontal"
- Reference: https://www.instagram.com/reel/DfIndnRoz80/ by Dylan Page (IG @dylanpage.ning), posted 10-30.
- 119 s; 41k likes and 633 comments when studied.
- The story: a prank on a Red Baron pizza worker backfires, strangers raise $570k for him, and the company makes him employee of the month.

**How it was studied (10-30):**
- the whole reel at 2 fps, both split stretches at 5 fps, and every frame of all 13 transitions;
- word timings from local Whisper (medium);
- the seam and faces measured on full-size frames;
- `motion_score.py` and `overlay_freq.py`.

The study copy (video and sheets) is only in the 10-30 session scratchpad.

Reference sheet: `dylan-page-split-receipts.jpg` (next to this card). It shows all 18 moments with the words under each.

This pass is now the rule for the split. The 10-28 decode at the bottom came from 3 TikToks at one frame every 3 s; where the two disagree, this pass wins.

## The rule: the top half is the receipt for the line he is saying
While he talks, the top half shows proof of the exact claim in his sentence. All 13 shots on top come from the story itself.

**7 are moments of the clip he is about to play:**
- the worker when he names him, with a red arrow sliding onto his head;
- the angry close-up on "it ended so badly";
- the phone tap, circled in red, on "pretends to steal his money";
- the Apple Pay screen on "the viral Apple Pay prank";
- the prankster on "in the beginning".

**4 are real screenshots of the fundraiser:**
- the total, on "raised half a million dollars";
- the page with the organiser's name, on "a man named Luke Oakenshield decided to set up a GoFundMe";
- the fundraiser's own words while he reads them aloud, with a yellow highlighter following his voice across the key phrases;
- the money line, its number in a blue highlight, on "five hundred thousand dollars out of the 700k target".

**1 is the company's logo**, on "Red Baron Pizza themselves have seen it".

**1 is the company's own post**, on "in fact he is employee of the month": "Employee of the month nominations are closed. You know why."

There is no stock, no generic b-roll and no designed text card. A new receipt lands on the first word of each new claim, not on single cue words. Each stays a median 3.5 s (0.5 to 8.2 s): 13 receipts in 45 s of split.

## Three states
| State | When | What |
|---|---|---|
| Split, 38% of the reel | He sets the story up (0-18 s) and breaks it down after the clip (88-115 s) | Receipt on top, him below |
| Him full frame, 8% | The three turns: into the clip ("but what happened next nobody expected", 18.0-21.1 s), out of it ("Now after this clip went viral", 86.0-87.8 s), and the closer ("but in the end your faith is restored that good people do exist", 114.9-119.2 s) | His whole frame, 1.8-4.3 s each |
| The clip full frame, 54% | The clip plays with its own sound, unbroken, 21.1-86.0 s (65 s) | Nothing on it: no captions, no face, no graphics |

The clip's first 8 s already ran muted on top while he set it up ("This is Walter ... comes up to him recording"), so its full-frame play opens on a scene the viewer has been primed for.

## Measured (1080x1920)
| What | Value |
|---|---|
| Seam | y 876 (0.456 of the height). Hard edge: no line, no shadow. Top panel 1080x876, his panel 1080x1044 |
| Him in the split | Chest-up with his set behind him, centred. Face about 280 px wide (0.26 of the width); face top about 190 px under the seam (face 1064-1354) |
| Him full frame | The same scale as in the split, moved up (face top about y 580). The split crops his frame; it doesn't zoom it. Every hard cut into full frame lands 1.22x zoomed in and eases out in about 0.45 s (the zoom-out, measured 11-04: section "11-04 pass 3") |
| The clip full frame | Fit to the width at 1080x1470 (about 3:4), centred (y 225-1695), with its own copy blurred and darkened above and below, which keeps it clear of Instagram's top bar and caption area |
| Screenshots | Fill the top panel's width on their own copy, blurred and darkened (mean RGB about 35), with a slow push. Never on black |
| Topic label | 0.0-5.8 s only, leaving with the first screenshot. White rounded box (724x86, radius about 12), centred across the seam (y 848-933). Black medium sans, about 60 px. The story in two words plus two emoji ("Prank Backfires!🤯🚨") |
| Red arrow | Solid red, no outline, about 700 px long. Slides in from the upper right in 0.17 s and lands on the person's head 0.55 s in. Holds 2.3 s while he names him |
| Red circle | Thick red stroke. Draws on in 0.2 s around the key object and holds about 1 s |
| Highlighter | Yellow (249, 230, 10), behind the key phrases only ("that this hardworking", "person", "lose their job", "they did not create"). Sweeps letter by letter in step with his voice |
| Number highlight | A blue (44, 61, 250) box behind the number he says ("$573,719 raised") |

## Transitions (each 0.2-0.35 s)
- **Receipt to receipt:** never the same move twice in a row.
  - a hard cut on his word (3 times)
  - a motion-blur whip or push (3: sideways, sideways, upward)
  - a glitch-streak in (2)
  - a blur out and in (2)
- **Full him to split:** the top panel drops in from the top, landing on the name he says ("Luke Oakenshield"). Measured 11-04 at 30 fps: a wipe down on an exponential ease-out (12% down on its first frame, 90% by 0.3 s, settled by 0.6 s), the receipt drifting its last 54 px into place, his picture pushed down with the edge. The "about 0.2 s" was only the visible jump.
- **Split to full him:** a hard cut (18.0 s) that lands 1.22x zoomed in and eases out over about 0.45 s (the zoom-out, on every hard cut to him in 2 reels, 6 of 6), or the panel slides up and out (114.9 s, no zoom).
- **Him to the clip and back:** hard cuts.

## His delivery and sound
- No pause of 0.1 s or more in 45 s of split: every breath is cut.
- Plain jump cuts every 5-6 s in the same framing, with no punch-ins. About half land on the same frame as a receipt change, which hides them.
- No music bed under his voice (no held notes in his stretches). No whoosh stands out over his voice.
- The clip plays at his loudness (RMS -15 against his -14 dBFS).
- No title card. Frame 0 is already the split, the first receipt and the label, mid-sentence: "someone tried to prank this Red Baron pizza worker for views".

## Pace (motion_score.py and overlay_freq.py, 10-30)
| | Dylan Page DfIndnRoz80 | Our C4396 split (10-30 16:2x) |
|---|---|---|
| Visual events a minute | 26.2 | 74.8 |
| Cuts a minute | 9.6 | 13.2 |
| Median gap between events | 1.53 s | 0.62 s |
| Idle | 9% | 2% |
| Live score | 9.1 | 9.8 |

Our word captions add most of the extra events. Our top half also changed about twice as often as his: stock cut on cue words every 1.5-3 s, against one receipt per claim.

overlay_freq's CLEAN/TEXT/CUT shares are not usable on this format: Vision counts the worker's face in the full-frame clip as the presenter.

## How it maps to OB's horizontal takes
1. **Split** while he sets up and while he breaks down. Seam at y 876. The top half holds receipts only:
   - Her clip's matching moment: her when he names her, her plate when he names the food, her scale when he says the number. A red arrow or a red circle goes on the thing he names.
   - A screenshot of her caption, a comment, a label, a study line or a Cronometer screen when he reads it, with the highlighter following his voice. The number he says goes in a highlight box.
   - The brand's logo, or its own post, when he names a brand.
   - His own footage or photo when he talks about himself (DSC07329 for his physique).
   - A client result when he talks about clients, under the client-data rules.
   - No Pexels stock in this look. If a line has no receipt, the previous receipt holds, or his line goes full frame.
2. **Him full frame** on the turns: into her clip, out of it, an item's number in a list, and the closer with the CTA. His 4K frame is cropped to 9:16 at the split's scale, and every hard cut into it carries the zoom-out (tmpl `{"name": "full", "zoom": 1.22}`).
3. **Her clip full frame** with its own sound, unbroken while she talks: centred at full width, with its own blur above and below.
   - OB's standing notes stay unless he says otherwise: his face in the bubble on her clip (10-28/29, `BUBBLE_ZOOM` 2.1) and her words captioned (10-29).
   - Dylan Page uses neither.
4. **Label:** the story in 2-4 words plus emoji, on the seam for the first 5 s (white box, black text), then gone.
5. **Captions:** OB's locked captions (3 words, live word yellow) stay on his lines at the seam; Dylan Page runs none. While the label is up, it sits just above the seam, at the bottom of the top panel.
6. **Pace targets for the split:**
   - one receipt per claim, a median of about 3.5 s;
   - no still stretch over 1.5 s on top: annotations, the highlighter and slow pushes keep it moving;
   - his jump cuts land on receipt changes when the words allow.
7. **Never** her clip looping under a whole line, stock as filler, or a full-frame cover while he talks (ledger M37).

## Engine gaps (brand_react_render.py, before the next horizontal edit)
- Still screenshots as top shots, on their own blurred copy with a slow push. Today `TopReader` reads video only.
- Annotations: the arrow slide-in, the circle draw-on, the highlighter timed to his word timings, and the number highlight box.
- The seam label.
- Full-frame-him turn lines with no big word. Today's "full" look is the punch plus one big word.
- The panel drop-in and slide-out. The whip, glitch and blur moves between receipts.
- Her clip full frame, centred at full width with blurred bands (check what H does today).
- The seam at y 876 instead of 960.

## Not copied
His set is his identity, not the layout: the neon "News Daddy" sign, the UC mic and the desk sign.

## 11-04 pass: DfQDZtxMo50, the split with no source clip (adds to the rules above)
OB 11-04 sent it with DfPiAtDIaxv ("this creator has two styles we can copy"). DfPiAtDIaxv is a different style: `dylan-page-selfie-flash.md`. This one is the split; measured 2026-11-04 (seam per frame, 10 fps transition strips, word times, motion_score). Reel: 90.2 s, 3.35M plays (1.8x his median of 1.82M over 57 recent reels). Decode: `/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/dylan-page-and-2x2/DECODE-DYLAN-PAGE.md` Part 1.

Same as above: seam y 876, receipts on the first word of each claim (15 of 19 within ±0.2 s), half his jump cuts hidden on a receipt change, no captions, frame 0 already the split with the label.

What's new:
1. **A story with no clip of its own sound:** split 85%, him full frame 15%, source clip 0%. So the split works for any story OB tells, not only reactions.
2. **The round-trip breath.** For a turn line or a verdict mid-story, the top panel leaves for one line and comes back: it slides up in 0.30 s (seam 872 > 856 > 836 > 812 > 776 > 732 > 676 > 616 > gone, accelerating) or hard-cuts away; him full frame for 1.6-4.3 s; then it drops back in over 0.37-0.50 s with an ease-out (first frame already at y 652, settling 700 ... 868, 872, 876). Three round trips in 90 s, plus the closer full frame.
3. **Photo bursts:** 7-8 photos at 0.6 s each on an even beat (not on words) for a time-span or plurality line ("years ago...", "every country"). At most 2 per reel.
4. **New receipt types:**
   - a count-up card: a number rolls up like an odometer in about 1 s and lands on the spoken number, over the clip darkened to about RGB 30 (text box x 198-883, y 375-486); a small rotated add-on ("1 Day") pops on its word;
   - a name lower third: the person's name typed on letter by letter over 0.4 s, no box, white with a soft glow, x 297-800, y 778-857, 20 px above the seam, the first time the person is named;
   - quote cards: the source's words in white on the clip blurred and darkened to RGB 20-26, a highlighter box sweeping behind the phrases as he reads them (blue RGB 45, 47, 242 here; OB's is #FFD400);
   - an animated route map flying along a line (3.1 s);
   - a few illustrative b-roll shots (0.6-1.8 s) for places with no real footage. OB keeps the no-stock rule (M37, M28): his version holds the last receipt or goes full frame instead.
5. **The label** "Longest Walk Is OVER!" leaves on the first receipt change (2.5 s here), so the rule is "the label leaves on the first receipt change", not a fixed 5.8 s. OB's label is Big Shoulders on the picture, no white box (brand rule).
6. **Pace:** 57.9 events a minute, live 9.4, idle 6%, 181 wpm, one pause over 0.12 s in 90 s, no music, -14.1 LUFS. The bursts, the count-up and the highlighter sweeps double the event rate of the 10-30 reel (26.2).

Engine gaps added by this pass: the odometer count-up, the type-on lower third, the 0.6 s burst timer, the measured slide-up and drop-in curves.

---

# Earlier decode (OB 10-28, the seed oil clips)
OB 10-28: "for the horizontal clips do the 50/50 split screen formats like dylan paige". Same creator as RIG 2 THE SPLIT in the vault (`80-Performance/_THE-DAILY-FOUR-v3-2026-08-30.md`: "True 50/50. Him one half, the artefact the other").

Decoded 10-28 from his 3 biggest TikToks of that week (frames every 3 s, seams measured row by row, faces with Apple Vision):
- 7697952781142854934 (24.0M, Paris protests, 86 s)
- 7698431914985688342 (12.3M, "Is Kim Jong Un Dead?", 73 s)
- 7699872481556892950 (10.2M, Nairobi building collapse, 31 s)

Corrections from the 10-30 pass:
- The seam measures y 876, not "0.46-0.50" or 960.
- A vertical clip takes the whole frame only when it plays with its own sound. While he talks, it is cropped into the top panel.
- Receipts change per claim (median 3.5 s), not on a fixed 2-4 s beat.

## Signature moves
1. **Horizontal evidence goes in the top half, him in the bottom half.** The footage fills its half edge to edge, cropped at the sides (the watermark "@LucAuffret" is cut to "@LucAu"). No letterbox, no blur, no divider line: a hard edge.
2. **Vertical evidence takes the whole frame**, with his voice carrying on. Him alone (no evidence) is full frame too.
3. **One piece of text furniture, on the seam**: a white rounded box with black bold type plus an emoji ("This Is Insane!", "Is Kim Jong Un Dead?", "BREAKING NEWS"), a small red date chip above it. Opener only.
4. **No word captions on the split.** On full-frame vertical clips he runs single small white words in the middle ("NAIROBI", "TRAPPED").
5. **Evidence swaps every 2-4 s**; he never leaves the bottom half while the top changes.

## Measured
| What | Value |
|---|---|
| Seam | 0.46-0.50 of the frame height (11 frames: 0.460, 0.465, 0.478, 0.480, 0.483, 0.500) |
| His face (Vision box) | 33-41% of the frame width (about 360-445 px at 1080); box bottom 0.76-0.87 of the height, so his chin sits around y 1470-1550 |
| His framing | chest-up, cap top about 100 px under the seam, eyes about 0.64 down the frame |
| First 2 s | 24M: Paris footage on top, him below, "This Is Insane!" box on the seam. 12.3M: him full frame with the date chip + "Is Kim Jong Un Dead?" box near the top. 10.2M: vertical clip pillarboxed on top, "BREAKING NEWS" box on the seam |

## How it maps to OB's clips (ytclip_pic.py, 10-28)
- Seam at y 960 (his "50/50"). The footage fills 1080x960. TV lower thirds are trimmed rather than cut mid-word. A wide graphic keeps its full width over its own blur. A title too small to read is rebuilt at 76 px or more (RIG 2's rule).
- OB chest-up under it: face box 380 px wide, ending at y 1450. Instagram covers everything under y 1500.
- OB's locked captions stay (3 words, live word yellow) but move to the seam, where Dylan Page's box sits, clear of OB's head.
- One fixed side, never mirrored: footage always on top.
- Where OB's face can't show (a look-off cover, or a clip playing its own sound), his words fill the bottom half instead.
- Source tag at the top of the footage, under Instagram's top bar.
- Not copied: the neon set, the news mic and the red date chip (his identity furniture, not the layout).

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** tmpl `split` (seam variable, drop-in, card or her clip on top, his face 290 px under the seam so his cap clears it). Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T04_split.json`: gate PASS.

## 11-04 pass 3: DfVXmUnBInZ, the numbered list and the zoom-out (OB: "the zoom in and out the 50/50 everything ... get it to a tee")
Reel: "The 5 changes that could be coming after last night's election", 128 s, posted 11-04 (561k plays at 75 minutes, too new to rank). Every move measured at 30 fps: image registration for the zoom, the seam per frame, Vision faces, word times, the audio. Decode: `T7/OB-EDITS/2026-11-04-creator-templates-study/dylan-page-and-2x2/dp3-DfVXmUnBInZ/DECODE.md`.

**The zoom (what OB called the zoom in and out):**
- **The zoom-out.** Every hard cut to him full frame lands about 1.22x zoomed in (1.21-1.24 where readable), centred on the frame, and eases out. The gap shrinks to 0.80 of itself every frame, so under 1% is left by 0.45 s. The first 3-4 frames are motion-blurred.
  - Measured on 6 of 6 cuts across 2 reels: an item's number ("Number four, ..."), the line after a clip with its own sound, and the closer.
  - Nothing pushes in after it settles.
- **No zoom inside the split.** 16 jump cuts were registered across the cut: scale 1.000 on all.
- **What does grow:** the title cards (4% a second) and the stills on top (a slow push of 0.7-2.7% a second).

**The 50/50:**
- Seam y 876. His frame sits at the same scale, moved down 462 px: the bottom panel shows from just above the cap to mid-chest, hands at chest height in view.
- **Drop-in** (full him to split): a wipe down with the same exponential ease (the gap shrinks to 0.78 a frame). The receipt drifts its last 54 px into place and his picture is pushed down with the edge.
- **Split to full him:** always a hard cut with the zoom-out. A clip with its own sound is a hard cut with no zoom.

**The list layer (new for a numbered list):**
- **Title card per item**, on its name right after the ordinal: IRAN WAR, Possible Impeachment, NO BIG NEW TRUMP LAWS, VETO.
  - White heavy condensed text, as big as fits (block 460-1030 x 380-630 px), centred a little under the panel's middle, over the previous receipt blurred and darkened.
  - It rises the last 28% of its height into place from behind its own bottom edge (about 0.4 s), then grows 4% a second. It holds 1.7-3.7 s.
- **Counter:** the item number, quiet grey-white, bottom left of the top panel (x 105-188, y 732-840). On from the item's first beat to the next item, and over a full-frame clip too.
- **Label:** "5 Changes Coming😳🚨" across the seam for the hook only (0-7.1 s). It leaves on the first title card.

**Receipts:**
- people on their names;
- a quote card with a highlighter following his reading;
- results cards (a second added under the first);
- a headline card with **his own note typed under it in grey**;
- a typed label on a photo, typed on then off;
- the subject's own post;
- one clip full frame with its own sound (8 s);
- one audio-only clip: his portrait still, a waveform and "In a call with [outlet]" (9.5 s).

**States:** split 76%, clips with their own sound 14%, him full frame 10%.

**Sound and pace:** voice only (no music, no SFX), -14.1 LUFS, no captions, 188 wpm, 23 jump cuts (10.8 a minute). He counts on his fingers at chest height on the item intros.

**Script shape** (his beat order, OB's words; skeleton in vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T04 list):
1. "[Who / your X] may look completely different after [event]. These are the reasons why." (The number goes in the label.)
2. "The first is [name]." + one consequence.
3. "The second is [name]." + "In fact, [the person] said it himself." + their clip with its own sound.
4. "Number three, don't expect [X]. Remember [the past example]..."
5. Repeat for each item, then one line to the lens to close.

**OB's version, built 11-04 (`tmpl.py` + `tmpl_fx.py`):**
- `{"name": "full", "zoom": 1.22}`: the zoom-out with zoom blur.
- `split` + `"drop": true`: the measured wipe and push (`"push": false` keeps him still).
- `top: {"title": [...], "bg": "src:PATH@T"}`: the title card, in Big Shoulders Black.
- element `itemno`: the counter, in Big Shoulders Black, white at 78%.
- The label stays Big Shoulders on the picture (no white box, brand rule). His captions stay at y 925.
- Not built: the audio-only waveform card.
- **Test:** plan `tmpl-tests/plans/T04_list_zoom.json` on C4413 (Hally's day as a list), output `tmpl-tests/out/T04_list_zoom_test.mp4`.
