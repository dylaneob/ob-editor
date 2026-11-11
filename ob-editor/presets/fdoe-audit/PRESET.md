> SUPERSEDED 2026-11-10: the rules for this format now live in `~/.claude/skills/short-form-editor/routes/fdoe.md`.
> Where this file disagrees, the route file and `~/ob-editor/qc/formats.json` win. Kept for history only.

# Preset: OB's FDOE audit / day-of-eating review (the LEGIT or SH*T series), mirrored from his own edits

OB 2026-10-21: "for FDOE review videos, knowing how I edit would you be able to mirror that?" Decoded on 10-21 from his top audits in the IG export (his Instagram data export):
- Nov 8 2025 `17888659119386452` (175 s, #1 for follows, 3,118)
- Nov 30 `17930446605135965` (147 s)
- Nov 5 `18085222678952857` and its trial twin `17939476547961400` (127 s)
- Nov 12 `18151563109414246` (136 s)

**Openings: read `~/ob-editor/presets/PROVEN-OPENERS.md` first** (v0 2026-10-22, from his skip rate on 6,130 reels). It sets the defaults for frame 1 and every hook or opening variant in a trial pack.

Background: OB's own notes on this format (not included).

**Alternative template (OB 2026-10-29, test status):** `presets/fdoe-breakdown/PRESET.md`, the Artzen Breaking Reels layout. Ship it as a trial A/B against this layout before using it on the grid.

**Layout rule:** the cutout over a full-frame source, for the whole episode. 20 of 20 audit breakouts used it; the boxed "Fact or Hype" layout flopped (OB 10-18, ledger B8.18). Layout check: `T7/OB-EDITS/FDOE-PRESET (Oct 21) mock.jpg`.

## Structure (his edits, measured)
1. **0-10 s, the hook.**
   - Her clip full frame, with her own title and claim visible ("What I Eat In A Day", "FULL DAY OF EATING", "He eats 6,560 calories").
   - OB is a cutout at the bottom left.
   - His line comes inside 3 s: a verdict tease or paradox ("She eats almost 3,000 calories and maintains that lean figure, and I'll tell you how"). The trial twins add the claim as text in the first 5 s.
   - Her music plays under him (Nov 8 opens on 2.7 s of her music, then his voice).
2. **Meal beats.**
   - Her footage of the meal stays full frame, with the cutout and single-word captions.
   - The meal's Cronometer card sits at the top centre: the kcal ring, then "Protein (25%) - 30.2g" in green, "Carbs" in cyan and "Fat" in red, then the micronutrient bars (Fiber, Iron, Calcium, Vitamin A | Vitamin C, B12, Folate, Potassium).
   - He names one or two nutrients per meal.
3. **Desk beats.** A short cut to OB full frame at the desk (the neon sun set) for a longer point, about 10 s into Nov 8.
4. **About 75-80% in, the totals.** The Cronometer targets card (Energy, Protein, Carbs and Fat with white, green, cyan and red bars) shows first over her footage (top left), then large over his chest with OB full frame.
   Optional (test): the hidden-calorie elimination beat from `presets/fdoe-breakdown/PRESET.md` "Eric Berg additions" goes right before the totals card. Film it as its own clean take to the lens.
5. **The close (last 10-15%).** OB full frame with ONE fix: an Omega-3 : Omega-6 ratio card, or the bottle in hand. The CTA lives in the caption only.
6. **Length:** 127-175 s.

## Locked values (fractions of the 9:16 frame; 1080x1920 numbers in brackets)
| What | Value |
|---|---|
| Cutout | Apple Vision person matte of his desk take (`bin/person_mask`), feathered about 1 px. No box and no border; his body runs off the bottom edge. Face width 0.16-0.18 W (175-195 px), 0.21 in the hook; face left edge at 0.12-0.19 W; face top at 0.66-0.74 H (1270-1420). It hides on text-only ingredient beats. |
| Captions | One word at a time, every spoken word. White, heavy rounded sans (Montserrat ExtraBold 800 at about 112 px is the closest local match), thick black outline (about 11 px). Centred near his head: text top at 0.64-0.76 H. |
| Meal card | His own Cronometer screenshot (Diary, the selected foods' summary). Top centre: x 0.255-0.78 W, y 0.085-0.29 H [275-842 x 163-557]. On for the whole meal beat. |
| Totals card | Cronometer targets (Energy / Protein / Carbs / Fat bars). Over his chest when he's full frame: x 0.24-0.76 W, rows at 0.50, 0.62, 0.72, 0.83 H. |
| Desk shots | His graded camera frame (warm tan or the take's pick), wide, face about 0.30-0.36 W. |
| Audio | His voice leads at -14 LUFS; her track (music or ambience) ducked well under it. Never her voice over his. |
| Music | Her clip's own music under the hook, nothing added (LEGIT plan §2B: one cleared track per show, OB's yes pending). |

## Inputs and the Cronometer step (OB 2026-10-21: "i use cronometer nutrition analysis tab and i send the video and you build it out on chrome already and i edit what i think after")
0. **Build-the-total sources (no stated figure, e.g. every row of the Oct 28 Muse bank):** the frame-1 number (PROVEN-OPENERS rule 5) has to be OB's own counted total, so finish his Cronometer edit before the opening is cut. On-screen text from 0.0 s: her intro line plus "I counted it: [total] kcal". Spoken line 9 words or fewer, no spoken statistic (C457: stat-first trials skip +5.4). The figure is about, never exact, when grams are estimated.
1. **He sends her video** (a link: OK the download first).
2. **I build her day in his Cronometer, on Chrome.**
   - `/diet-analyzer` turns the video into per-meal entry lists: foods, grams, P/C/F, flagged guesses.
   - I log those entries in his Cronometer diary (web, his logged-in account), one meal at a time, and tell him when it's built and which numbers are soft.
3. **He edits what he thinks after**, in Cronometer itself. His numbers win over mine.
4. **The meal cards and the totals card come from Cronometer's Nutrition Analysis tab** after his edits: one capture per meal plus the day's targets view, at the card positions in Locked values. Never a redrawn copy of Cronometer's screen.
5. **His desk take:** the Sony C43xx plus the MOTIV file. Film it wide at the desk so the cutout gets his full upper body. Any background works, because the matte removes it.
6. **His intro takes (C4370, 10-21):**
   - A blank stare at the camera of about 15 s ("i stared blankly so i can react"). Both intro looks use it; pick a stretch with no blink.
   - Usually TWO spoken hooks. Each is its own version for an A/B test, never played back to back ("i did two intros ... so we can ab test the two intros").
   - So an episode ships as 2 hooks x 2 looks = 4 files with the same body.
7. **Meal cards from Cronometer web** (C4370): capture the Diary's Energy Summary + Targets panel and the Highlighted Nutrients panel with the meal's foods selected. Crop them to the Consumed ring, the 4 Targets bars and the 8 nutrient rings. The faded Expenditure / Remaining rings are dropped, never redrawn.
   - Card: white, 1000 px wide, label tab ("BREAKFAST"). The card body sits at y 216-730.
   - The day card goes over his chest on the totals line.
   - Builder: `T7/OB-EDITS/C4370-legit10/_work/make_cards.py`.
8. **Props:** when he holds something up (the Omega 3 bottle on the omega-3 line), that line stays on him full frame. No cutaway.
9. **The meal flow (OB 10-21):** "do you let the orignal play without me on it when she shows her meals and directly after then meal i review it, thats the flow normlaly".
   - For each meal, her clip plays as she posted it: her voice and music, full frame, no OB, no card, no captions.
   - Then his review of that meal, with the cutout and the meal's card.
   - Cut her clip on her own sentence and breath boundaries, so the picture shows what she is saying.
   - If her line covers two things, split it at her breath and play each part before his review of it.
   - **How much of her to play (OB 10-21, after two rounds):**
     - Too short: "you cut her off really fast each time and dont let her explain the full meal". Every clip ends on her full stop or breath, never mid-word, with a 150 ms fade.
     - Too long: "you showed too much". He wants the middle: her opening up to the line that sets up the video ("...As someone who is traveling so often,"), then each meal's core description.
     - Skip her lines that play over footage of a later beat. "i liked that you didnt show the workout til i mentioned the carbs". Her workout waited for his "improve performance" line.
   - **His clip plays before every meal, even a music-only reel (OB 10-22, after cutting the video himself: "the formula is the original video then me breaking down meal by meal after each meal is shown, its good for retention").** The reel's own clip of the meal, with its song, then his breakdown with that meal behind him on the green screen. What he called "glitch and show the food for like a second ... choppy" was the cutaways over his talking, not these clips.
   - **Music bed under his talking (OB 10-22: "you can add background music when im talking").** About 19 dB under his voice, 4 dB lower while he speaks, muted under the intro and his clips (their song plays there): `MUSIC` / `bed_env()` / `music_bed.long_bed`. Short form uses his saved tracks; every version also ships a -NOMUSIC copy, and 1A comes with the other tracks to pick from.
   - **Title box (OB's own edit 10-22):** an Instagram-style text box, black condensed type on a white rounded box (about 600x127 at y 245), "Is his diet legit or sh*t", over the intro and his first hook line (`TITLE`, `title_img()`).
   - **His cuts (same edit):** he drops the weakest lines ("Same with the potatoes", "Same with avocado", "Great protein from the beef", a stumbled "Greek") and joins lines tight: about 0.04 s after the last sound, the next line on its first sound. Check the edge against the mic: his phone trims clipped "old", "fiber", the p of "potatoes" and "spinach".
   - **He stays on screen while he talks (OB 10-22: "u dont green screen me while talking you just show the overlay and my voice").** No covers on green-screen lines, and no short food cutaways anywhere (`COVERS_ON = False` in `c4363_edit.py`). The cover rules below only apply if he asks for B-roll again.
   - **Dead air (OB 10-22: "you also keep me looking away and deadspace"):** every line starts on its first word (check the mic level, not the ASR word start: Apple stretches a word back over the silence before it, so hook1c kept 1.3 s of him reading his phone). Silences of 0.35 s or more inside a line are cut to 0.16 s (`SPLITS`), and each piece takes the other layout (green screen / main frame) to hide the jump.
   - **Reading lines go small:** where he reads off his phone most of a line, that line is the green-screen cutout; the full frame goes to lines he says to the lens and to his reactions. Fix at the shoot: phone script right under the lens, or a teleprompter, and one clean take per line looking at the lens.
   - **His eyes (OB 10-21: "make sure you dont have me looking off"):** `gaze_rows.py` scans every line. Where he looks down while talking, her footage covers him or the cutout drops out (`gaze_covers()` in the builders). This is mostly the first half-second of each line, as his eyes come up from the phone.
   - **No flashing (OB 10-21: "you glitched ... flashing back to her and me talking over and over, looked horrible"):** at most ONE cover per line, never under 0.6 s, never under 0.6 s of OB on either side of it (else it runs to the line's edge), the whole line when it would cover 70%. Hooks get NO covers. Quick glances (under 0.4 s, or under 0.3 s at the line start) stay. Reaction look-downs (laughing, head dropped) stay on him (`NO_COVER`).
   - **Cover footage always moves:** a fresh clip that starts with the cover (`cover_source()`), never a held frame. A shot too short for the cover at 0.8x loops forward-back if it's a plate shot (`PP_STARTS`), else plays slowed with blended frames (`cover_clip()`). On C4370 her breakfast line ran over the plate and then the glass. OB: "show the breakfast not the drink, after breakfast show the drink, allow her to say the meal and the drink as well". So the meal plays over the plate, his breakfast review follows, then the drink over the glass, then his juice review.
10. **Shot variety in his reviews (OB 10-21: "when im reviewing keep green screen and then change to me as the main frame and the calories and food are overlays as well, so it has more shots and im the focus in some of the frames").**
    - Within each meal review, alternate the green screen with OB as the main frame.
    - Green screen: his cutout over her food, card at the top. Main frame: OB full frame, her food in a rounded 9:16 box top right (340x604 at 716,230, white ring), the meal's card over his chest (y 986-1500), captions at y 868 between them.
    - The calorie line (the first row) is always green screen. Builder: `MAIN_ROWS` in `c4370_edit.py`.

## Pipeline (built from existing tools)
`sync_av.py` (MOTIV) → `chunks.py` / `tighten_edl.py` (his take, little dead space) → beat map (his lines to her meal timestamps) → `person_mask_dir` (the cutout's alpha, every frame) → render: her clip full frame + cutout + card PNGs + one-word captions (`ffmpeg-full`: `subtitles`/`ass` burn for the captions) → `render_review.py` / `vmaf_check.py` → trial pack (memory `feedback_trial_variant_packs`): 2-3 opening variants that differ only in the first 3 s.

## The 2 intro versions (OB 2026-10-21: "1 and 2 is the main i dropped 3"); every episode ships both as trials
They differ only in the first seconds; the rest is the same edit (memory `feedback_trial_variant_packs`). Mock: `T7/OB-EDITS/FDOE-PRESET (Oct 21) 3 intros mock.jpg`.
1. **Corner cutout:** "greenscreen and im in the corner just looking then me as the full frame". Her clip full frame, OB cut out in the bottom-left corner watching (no talking), then a hard cut to OB full frame at the desk for his first line. Cutout values as in Locked values. Size: face ~0.17 W, the same as the review cutout (OB 10-21: "make me a little smaller in the intro ... on the green screen version"; 0.21 W was too big).
2. **Trainbloom style:** "looking at the reaction video". OB full frame (the `react_watch` 1.3x framing, face in the top third) looking down at the clip, which plays in the tall 9:16 box over him: 632x1124 at (224, 796), bottom on the frame edge, never cropped (the reaction preset's box).
3. ~~**Corner clip:**~~ DROPPED (OB 10-21: "i dropped 3"). Kept for reference only: "me looking into the corner and the video playing". OB full frame, the clip small in a top corner: 380 px wide 9:16 (380x676) at (660, 140), thin white outline. He looks INTO that corner while it plays, so film this take glancing up-right (or flip the corner to wherever he looked).


## Originality A/B (trial only, 2026-10-29)
The meal flow in item 9 plays her clip clean (no OB, no captions). The Nov 2025 breakout edits (Structure item 2) and `fdoe-breakdown` step 4a kept OB's cutout and one-word captions over her meal footage. Mosseri (Colin and Samir, 51:58) says originality classification now matches copied segments, and Meta counts stitching as a light edit, not original (ledger C323). Test the one variable on one episode as a trial pair: A = item 9 as is; B = the same cut with OB's cutout bottom-left and his captions over every meal clip (her audio unchanged). 10+ pairs before a verdict. Read reach and breakouts per post vs the month's trial median, and skip at 72 h. Grid default stays item 9 until it reads (OB 10-22: the clip-then-breakdown order is good for retention; B keeps that order).

## QC gate (2026-10-28)
Run `qc_gate.py` on every FDOE render (skill: "The QC gate and the never-again loop"). On the posted C4378 1B it found one 0.49 s silence and the Cronometer cards (BREAKFAST, Fiber, Iron...) in the bottom IG band (below y 1500 of 1920), where the IG caption and buttons sit. Keep the cards above y 1500. Expect a WARN from her clip's own text ("What I eat in a day"), which is not his copy.
