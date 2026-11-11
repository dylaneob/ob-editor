> SUPERSEDED 2026-11-10: the rules for this format now live in `~/.claude/skills/short-form-editor/routes/fdoe.md`.
> Where this file disagrees, the route file and `~/ob-editor/qc/formats.json` win. Kept for history only.

# Preset: FDOE breakdown, Artzen "Breaking Reels" layout (TEMPLATE, TEST STATUS)
OB 2026-10-29: "the new pdf ... i wanna do for FDOE reviews, like exactly the same ... his hat and face are over the reaction but his hand and arm are behind it ...
i love that his head is popping out on the bottom on the second half ... save that as a template".
Source: @artzenmedia reel DfE7jMLTLSx (Breaking Reels), study PDF T7 `artzen-box-flash-effect-study-2026-10-29.pdf`,
full measured style card `~/ob-editor/styles/artzen-breaking-reels.md` (read it: every position and timing below comes from it).
Reference frames in this folder: ref_t0.3 (opening depth), ref_t9.0 (title card), ref_t13.2 (keyword overlay), ref_p24.0 (screen + PiP head pop-out), ref_t50.0 (follow card).

## ⚠️ Status: TEST variant, not the default
`presets/fdoe-audit/PRESET.md` (his proven layout: cutout over the FULL-FRAME source, 20 of 20 audit breakouts; the boxed "Fact or Hype" layout flopped, ledger B8.18)
stays the default. This template boxes the source in the opening and puts a screen on top later, so it ships as a trial A/B against the proven layout first
(the trial engine's 2 test slots), judged on skip rate, reach and follows. OB's call to promote it.
Note: from the meals on, her footage is full frame like the proven layout (step 4a); only the 0-7 s opening boxes it.

## Structure (FDOE mapping of the measured beats)
1. **0-7 s, demo first.** Her FDOE clip in a rounded inset LEFT (x 3-55%, y 39-91%, radius ~2% W), HER real view count (eye icon + number) bottom-left inside it,
   handwritten 2-line caps label above it ("HOW MANY CALORIES / IS THIS..."). OB seated RIGHT, leaning in. **Depth:** OB's hat + face composited ABOVE the inset
   (cap brim and face overlap its top-right corner); shoulders, arms and hands stay BEHIND it.
   Build: Apple Vision person mask (`~/ob-editor/bin/person_mask`) ∩ head region (face box from `frame_obstacles`, grown up for the hat and down to the chin/neck line),
   feathered 2-3 px, composited over the inset. Per-frame mask, smoothed over 3 frames so the edge doesn't shimmer.
2. **7.3-7.9 s, flash-cut burst** (1-3 frame cuts) into the **title card, ~2.1 s**: chalkboard texture, LEGIT logo (his series name, never "Breaking reels")
   enters oversized and slams down (spring), eye counter climbs to a REAL number of his (e.g. total LEGIT views; sourced, never invented), chalk line draws up-right.
   Spoken over it: his series line ("This is LEGIT, the series where I ...", his words).
3. **~3.5 s full-screen OB** for the one-line verdict tease; one keyword overlay above his head (red italic serif on a white rectangle).
4. **Meals: her clip, then the breakdown, for EVERY meal (OB 2026-10-29: "we have to show the original creator like we always do in between each meal so i can breakdown each meal").**
   a. **Her meal clip, the way he always does it** (`presets/fdoe-audit/PRESET.md` "Meal beats"): her footage of that meal FULL FRAME, OB cutout bottom-left,
      single-word captions, her own audio/music under him. Never boxed here.
   b. **Then his breakdown of that meal: screen + PiP** (below), Cronometer showing that meal.
   Order per meal: a -> b, then the next meal's clip. Breakdown layout:
   **Screen + PiP.** Near-black background; Cronometer screen (the meal's diary/card) across the top ~0-48%; OB in a rounded box x 9.6-90.4%,
   top at 59.3% H, running off the bottom, radius ~40 px @1080, ~4 px glow border sampled from his footage colours.
   **Head pop-out:** his hat + head composited above the box top and border, rising ~9.4% of H (~180 px @1080). Alternate with full-screen OB for spoken beats;
   one keyword overlay per meal (the meal name or the kcal).
5. **Close ~4 s:** his locked closer ("anyways, bs silenced - follow if you want actual logic"), then a follow card (avatar circle + "OB" + Follow button tapped by a cursor).
   NO comment-keyword asset funnel (Artzen's BOX gate is a do-not-transfer).

## Tunde Alao additions (OB 2026-10-29, style card `~/ob-editor/styles/tunde-rebuilding.md`, frames ref_tunde_*.png)
- **Episode number** in the first frame and the caption ("LEGIT Ep 1").
- **Running counter with a progress bar** at the close, same design every episode (his "$359 / $5,000" gold label + bar). Unit is OB's call
  (e.g. days counted, creators checked); only real numbers.
- **Phone-to-lens proof** at the verdict: OB holds his phone with the Cronometer day total up to the camera (filmed, not built).
- **Floating proof cards** as the alternative to the screen-on-top layout: the meal's Cronometer card pops in over the lower half beside him, never on his face.
- **From the full Muse study (Parts 5-6, read 2026-10-29), the craft rules that apply to every LEGIT episode:**
  - Camera locked off, eye level, medium to medium-close; no moves. The still frame is a trust device: the viewer trusts the screen wasn't faked.
  - Eye-line grammar: lens for the claim, down at the screen/phone for the proof, lens for the verdict.
  - Face anchors, screen proves: talking head vs evidence about half and half, INTERCUT (not blocked), the evidence never fully replaces his face
    except in full-frame evidence beats (her meal clips).
  - Hard jump cuts only, no dissolves; rhythm from content (fast routine meals, slower held payoff).
  - Graphics are labels or series trackers only (episode number, counter, meal name, kcal); nothing purely decorative.
  - Same spot, same framing, black hat every episode = the series tableau, recognisable in one frame.
  - Two framing breaks per episode: the phone-to-lens proof, and one reset shot near the close in a different spot of the same room.
  - Loop: the last line flows back into the first so a rewatch feels natural.
  - Episode skeleton (REBUILDING): grievance/claim hook -> title card with episode number -> her original shown -> fast breakdown -> payoff -> counter -> closer.
  - Held last item (Wait-for): tease the biggest meal or the verdict early, pay it off slower and longer at the end.
  - Not ported: keyword gates (B23.1: comments up, follows flat), his "comment yes" prompt (OB's closer stays locked), his rooms/wardrobe/mic.
- **Tests from the full Tunde read** (vault `90-References/muse-2026-09/_TUNDE-ALAO-REVIEW-2026-10-29.md`): (1) "guess her calories" on screen
  mid-video with the day total held to the end (his puzzle + held-last-item takeoff); never as the opening (question openings bought nothing, B8).
  (2) Instagram collab invite to the source creator on a defend episode (his spikes came from borrowed audiences). Both untested on OB.
- Captions alternative: his single words sit ABOVE the head (y ~23%) vs Artzen's at y ~72%; pick per shot so they never cover a face or a card.

## Eric Berg additions (2026-10-29, test status; review `90-References/muse-2026-09/_ERIC-BERG-REVIEW-2026-10-29.md`)
- **Hidden-calorie elimination (one beat, before the totals):** OB rules out the two meals the viewer suspects, then reveals the real one from Cronometer. Spoken to the lens, e.g. "It's not the dessert. It's not the latte. It's the two tablespoons of oil in the 'healthy' bowl." Only when the Cronometer numbers say so; the eliminated meals must be the obvious guesses, never straw men. Never a superlative ("the most fattening..."): the math is the claim.
- **Guess hold, Berg's two-label build:** during her last meal clip, one persistent label on screen ("GUESS HER TOTAL") held for at least two beats, then the reveal on the phone-to-lens Cronometer total. Never the opening line and never a caption comment game (B8.5 question openings 0.80x follows; B31.1 his one guess prompt 0.00x follows; C150).
- **First line rule:** no "NOT what you think" and no "the most / the best" opener. On his talk-lane hooks a contrarian word in line 1 sits in the bottom quarter for follows (B41.2); Berg's winners with it are superlative stacks.
- **Never faceless:** Berg's footage-only reels are out (face rule). The port of his footage-first opening is her clip full frame with OB's cutout, both people visible at 0.4 s (PROVEN-OPENERS #1, B8.18).
- Judge both beats as trials on skip rate, average watch and follows; they become defaults only after a trial pack wins.
- Peter Visuals extension of Tunde test (1) (landed 2026-10-31): (1) "guess her calories" on screen mid-video with the day total held to the end. Same hold-then-reveal can be tried once on a defense episode (claim on screen, hold two beats, reveal); judge on skip, average watch and follows, never likes. Still never as the opening and never a caption game (B8.5, B31.1, C150). Peter Visuals adds no new evidence: his post's engagement is gate-driven.

## Captions
Single word, white handwritten font, ~70 px cap height @1080, centred x 50%, y ~72% (on the chest in full-screen shots). Optional A/B: Artzen box flash, built: `~/ob-editor/bin/box_flash.py`
(2 frames solid white box per word, then plain white text; tested 2026-10-29) vs his current style, one variable, judged on skip rate.

## Filming spec (tell OB before he films)
Vertical (phone) or Sony 4K horizontal (crop to 9:16). One take, one spot: seated right of centre, head upper middle, hands low in front of the chest,
black hat on, plain wall behind the head, and **headroom: about a tenth of the frame clear above the hat** (needed for the pop-out). Phone ~4 ft back, chest height.

## Gates (as every preset)
Shot list / frame-1 mock approved by OB before any full render; never-clip-words diff; QC gate; text never on a face; no black bands.

## Built 10-30 (C4400 Alex, C4401 Dominique): `T7/OB-EDITS/2026-10-28-backlog/_work/fdoe_artzen.py TAKE OUT [--plan|--geo|--frames t,t|--dry|--segs]`
OB's notes on the first build (10-30 night) are now the rules:
- **Opening = his reaction, "like he did":** 4-5 s of him watching her video on his phone, her video in the inset with her own sound, then his
  hook over it with her sound ducked 18 dB. **Find the reaction by frames, never by silence (ledger M34, OB 10-30: "c4400 1:31 is where im
  reacting to the person", "after i react i say my thing and the reaction can move to make it fit because i ... filmed it wrong"):** the first
  build took the silent stretch before his first line and got him leaning in, sitting back and looking at the lens. Make a 2 fps sheet of
  the take, take the stretch where he sits still with his eyes on the phone (C4400 1:31, C4401 1:06; it may come after his lines), check
  the window's own sheet, and move it to the start. His timestamp wins. Gaze can't check this (eye openness reads the same on phone and lens).
- **Order, "just like the other reviews":** reaction, his line, the LEGIT card, then per meal her clip full screen with her own sound (no OB,
  no card) and then his breakdown in this template. Trim her clips before her own end cards ("READ THE CAPTION") and empty-counter tails. The inset sits on the side away from his face
  (Artzen's left when he sits right of centre; mirrored when he is centred, since he holds the mic in his right hand and its head floated over a
  left inset). Only his head goes in front: person matte x an ellipse from his cap top (that frame's matte) to his chin (that frame's Vision face
  box, 5-frame median); never the neck or shoulder.
- **"Move it when I'm saying I'm gonna review":** on his series/review line the inset springs off (0.5 s), then the 0.6 s flash burst, then
  **"a big overlay, make it a series"**: the chalkboard LEGIT card, logo slam, chalk line.
- **"Show calories then show the foods and add stuff and movement ... the food or info about the food items":** each meal's first PiP line shows
  the real Cronometer card; the next PiP lines show her plated-meal footage (ping-pong 0.75x, slow push) with a yellow kcal badge and food chips
  that pop in on the word he names them (white pill, red sub-line; numbers only from the audited sheet).
- **Cronometer, "direct photos like you did before":** log her day on an empty past date in his diary, tune one main food's grams per meal so
  each meal's kcal matches what he says on camera exactly, select a meal by clicking its group header, `zoom` (save_to_disk) the Energy
  Summary + Targets panel and the Highlighted Nutrients panel; `_work/make_cards_fdoe.py` crops them anchored on the orange Energy bar and the
  panel title. Prefer NCCDB/USDA entries that carry the 8 highlighted micros.
- Horizontal (letterboxed) sources: never black bands; full-frame clips get the strip at 1.8x over a blurred, darkened copy of itself.
- Cut: pieces with no word in them are dropped (a click in a 9 s pause made a 3-frame flash); a join with no pause is cut in the dip itself,
  nudged on the 10 ms grid until `qc_gate.valley_cut` accepts it; `--dry` gates both mixes before any picture render.

## v3 rules (OB 10-30 ~12:50, on the 11:0x C4400/C4401 cut; ledger M36-M39)
- **Lip sync, measured per window (M36):** "my lips arent synced ... on the male review ones". C4400's MOTIV file skips 2.64 s between
  "coach" and "241" and about a frame near 116 s; the one offset (79.00) put his opening lines 2.6 s off. CFG `sync` = runs of
  (mic from, offset[, drift]) matched against the camera's own sound in 3 s windows every 2 s (scratchpad `sync/fine.py`); `cam(t)` maps
  every piece. Re-run `--geo` after any sync change (head boxes are per line).
- **Never off screen while he talks (M37):** "while im talking never not show me, you did full screen overlays while im speaking about the
  food, never do that". No full-frame covers. A look-down on a full-frame line switches that stretch to the screen + PiP (the meal's food,
  the day card on review lines, her intro on hook lines), at least 1 s. The series line is the PiP too: the chalkboard LEGIT slide is
  the top card (burst of 2-3 frame cuts with her opener inside the card, logo slam, chalk line), him in the box.
- **No black (M38):** "i dont like the black background ... make it more engaging and not black". Every box layout sits on his own studio,
  blurred and warm from the same frame, moving with him, with the faint dot grid (C4383's look, his 10-29 pick); `studio_bg`, gain 0.8.
- **Her intro plays (M39):** "make sure you are showing her intro video again at the top not just a photo". Hook lines: her opener from its
  first frame at 0.75x, forward then back; a letterboxed strip goes whole into the top card, a full-frame portrait fills the top.
- **Captions in the box layouts sit under his chin** (y = chin + 75, 1400-1455, over the IG strip). The 11:0x cut had "823" on his mouth.
- He loves the screen template itself ("i love the template of the screen i sent"): the Cronometer card on top, him in the glow box,
  his head over its edge. Keep it.
