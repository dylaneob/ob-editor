# Muse technique library (2026-10-30): editing techniques from 38 Muse creator studies

Source: section 4 "Editing techniques" of every study in `muse-txt/bundles/EDIT-ALL.md` (38 studies; full notes per study in vault `90-References/muse-notes/<name>.notes.md`). Cross-checked against `short-form-editor/SKILL.md`, `presets/*/PRESET.md`, `presets/PROVEN-OPENERS.md`, `styles/*.md`, `brand/BRAND.md` and `bin/`. Every value below is quoted from the studies or from OB's own files. Where a study gives no number the entry says "value not given". No invented values.

## 1. How to use

This is a reference library, not a preset. Look up the area you are editing, read what the creators actually do (with their exact values), and use the "Build" line to see which existing OB tool makes it. Status tags: ALREADY HAVE (the file or tool is named, nothing to build), NEW-TEST (not in the editor yet), CONFLICTS WITH OB RULE (the rule is named and the technique is not recommended; if a safe fragment of it survives, the entry points to the entry that carries it). Anything marked NEW-TEST goes to trial reels first, one variable at a time against the same footage, judged on skip rate (reach and follows as the second read), and only a trial winner is promoted to the feed, re-cut with the fixes OB names and no new look. Every NEW-TEST build still passes `qc_gate.py`, `first3_check.py` for trial packs, `motion_score.py` and the face-clear checks (`faces`, `frame_obstacles`, `face_clear.py`, `overlay_touch.py`). OB's hard rules apply to everything here: text never covers a face (text starts about 60 px under the chin, outside Instagram's top 220 px and bottom 420 px), no black bands or flat black voids (fill the frame), his face on every post, no AI imagery, voice or music, no SFX by default, never clip a word, no em dashes in on-screen text, one brand font (Big Shoulders Display, no boxes or bubbles, OB yellow `#FFD400` on the one word that matters). Creators' serif, handwritten and boxed type are therefore copied for structure (what, when, where), never for typeface or box.

---

## 2. Techniques

### A. Openings and first frame

**A1. Claim or literal question as on-screen title on the live picture**
- What: the title is on screen at frame zero and the same promise is spoken in the first 3 seconds, so the structure is legible before sound is on.
- Values: title is the literal question ("Would you eat it?", R13); belief named in 3 seconds (OB rule quoted in the cross-niche study); 4x4 standard: on-screen title plus the same promise spoken in the first 3 seconds; Luke Hannan "names the target in the first 5 seconds"; Dr Noc "first 3 seconds carry the hook"; Brigid's big numbers "earn the next 3 seconds"; Dr Idz "bold claim thumbnail", claim in the first frame. Calleigh: bold caps title plus a laptop held up showing the same title. Holman SIX: on-screen hook title plus the spoken opener "In case no one's ever told you this" (same opener in Reel A and B). Lynch: premise in the first caption line. Font size and position: value not given.
- Creators (studies): cross-niche-format-library-v2, four-by-four-format-study, numbered-plan-reel-kyle-megann, william-holman-deep-study, nutrition-focused-fitness-creators part1 and part2.
- Build: `PROVEN-OPENERS.md` rules 3 (3+ readable words by 1.6 s) and 5 (food number in frame 1); title placed with `faces` / `frame_obstacles` (allowed on body, shirt or food for the first 3.5 s, never on a face); Big Shoulders Black; `cards.py` / `reel_cards.py` lines or `box_flash.py`.
- Status: ALREADY HAVE (`presets/PROVEN-OPENERS.md`, `presets/short-form/PRESET.md` step 6). Gabby's boxed black-on-white title is not copied (no boxes).

**A2. Full-screen title or question card as frame zero**
- What: a card with only text opens the video before the speaker (Jayyang walk-and-talk Reels 1 and 2: frame zero is a title card carrying the claim, income and age or "top 1 percent"; Dr Noc "large question-card hook before the speaker talks"; Tobi "large white serif title card at the start"; Kamila paper-style title card).
- Creators: jayyanginspires-deep-study, nutrition-focused part2, tobi-30day-study, master-formats-every-link.
- Build: none.
- Status: CONFLICTS WITH OB RULE: face on every post and `PROVEN-OPENERS` rule 1 (two people / his face in the first frame), `feedback_no_text_only_overlays` (no text-only card on its own), brand look (serif). A1 carries the same job on the live picture.

**A3. Comment-reply sticker or opening comment screenshot as the hook**
- What: a real comment is the first thing on screen and the video answers it.
- Values: WISDM frame zero: the "COMMENT REPLY" sticker on screen seeds the format (W1, W2). Gin Lee (about 25 to 28 s loop): "an opening comment screenshot (on-screen comment as the hook)". Sticker size and position: value not given.
- Creators: cross-niche-format-library-v2, gin-lee-core-values-study; Sky Tan's caption reel also uses a comment graphic ("who is this guy").
- Build: crop the real comment to the text only with names and photos hidden (the BRAND.md DM rule); overlay on frame 1 with a `cards.py` spring (`insert` or `photo_overlay`) so something moves by 1.5 s (`motion_score.py`); place with `head_clear.py` / `faces` so it never touches his face; label in brand font, no box. `moves.py comments` is the CTA comment wall, not this.
- Status: NEW-TEST (real comments only; mask handles).

**A4. Payoff first, then rewind**
- What: open on the finished result, then show how it was made.
- Values: Fitness Chef recipe films "open on the finished dish or payoff, then rewind"; Luke Keegan hook 0 to 3 s is a close-up of the finished golden loaf, single words flashing, the series line, then the claim, order "food first, brand second, claim third"; cross-niche: "the visual hook is the video"; Sky Tan: an "insane visual hook" timed to the beat drop.
- Creators: thefitnesschef-deep-dive, luke-keegan-deep-study, cross-niche-format-library-v2, sky-tan-advice-study.
- Build: ffmpeg cut of the best frames of the result to the top, then jump back; keep a second person or OB in the first frame (`PROVEN-OPENERS` rule 1) and the food number on screen (rule 5). Scope: recipe, 10/10 and list reels. On audits keep the proven exception (open on her own intro).
- Status: NEW-TEST.

**A5. Hook-frame text fragment with the last word highlighted**
- What: a short dangling fragment on the hook frame, last word emphasised.
- Values: Fitness Chef: potato remake hook shows "WELL", lamb shows "THIS", donut opens with "EATING THIS DOUGHNUT REPRESENTS" with the last word highlighted. Size and position: value not given.
- Creators: thefitnesschef-deep-dive.
- Build: `box_flash.py` single chunk or `reel_cards.py` line, last word in `#FFD400`. Keep it at 3+ words so it passes `PROVEN-OPENERS` rule 3 (the one-word fragments "WELL" and "THIS" would not).
- Status: NEW-TEST.

**A6. Ten-second lived-recognition cold open**
- What: the viewer recognises their own situation before any teaching.
- Values: R6 cold open is "10 seconds of lived recognition" (proposed for OB in the study). No cut values.
- Creators: cross-niche-format-library-v2.
- Build: a script and edit choice only (`takes.py`, `zero_dead.py`); no new tool. Check it against the reach-trial rule of 9 or fewer spoken words in the first 3 seconds (`PROVEN-OPENERS` rule 6) before using.
- Status: NEW-TEST.

**A7. Seamless visual-trick transition as a frame-zero device**
- What: one in-camera or in-edit trick that morphs into the real opening. The study says OB's editor "can build once and reuse" it.
- Values: the trick itself, duration and count: value not given (R21).
- Creators: cross-niche-format-library-v2.
- Build: needs a new tool: `zoom_portal` in `moves.py` (motion-library section G #7 "Zoom portal" is listed but not built; #17 "Frame break" is the alternative).
- Status: NEW-TEST (highest build cost in section A).

**A8. 2x2 four-image opener with the talking-head cutout at the junction**
- What: four aspirational images in a 2x2 grid, creator cutout centred over the junction, title on the grid.
- Values: grid 1 to 3 seconds in the 4x4 study; the four images show "outcome life, not stock or random photos"; cutout positions: centred (Darren, Adam SPLIT, Hayes, Josh TEST, Josh PLAN, James); slightly below centre (Jake); slightly above vertical midpoint (Nitto); lower centre, partly covering the bottom two images (Mora); small rectangular cutout straddling all four quadrants (Strauss). Josh PLAN: grid only at start and on loop, then program slides. Strauss: persistent grid. "Never returns to the grid" in the master-formats read; the same four images can open every episode (one-time asset per series). Thumb-stop is visual, but opening retention is unmeasured (slide and reel retention are not in the API data).
- Creators: four-by-four-format-study, four-by-four-deep-analysis, master-formats-every-link, ten-ten-study (Mora).
- Build: the 10/10 engine in `T7/OB-EDITS/2026-10-24-tenten/_work/` (`tenten3_c4376_edit.py`) with `person_mask_dir` cutout; OB's rule: if a format holds the grid, it holds the whole video.
- Status: ALREADY HAVE (10/10 gut, hormones, micros; on OB's data the grid open skipped 31 to 37% vs 38 to 47% for the talking-head open, `project_1010_feed`). The "same four images every episode" series asset is a NEW-TEST detail.

**A9. Source clip first with her view count badged, then the host**
- What: another creator's clip leads, with its view count shown, then the host reacts.
- Values: Amelia breakdown format: the other creator's clip plays in a small centre frame with its view count badged, she talks to camera, about 55 seconds. April stitch (DcTfuugRGJ4): frame zero is the stitched clip of a man outdoors in a white cap with his on-screen complaint, then cut to April on her couch. Sky Tan breakdown reel: split screen, viral cooking clip on the right, Sky labelled "Content Strategist" on the left.
- Creators: amelia-gonzamonte-outcome-map-study, aprilvwhitney-deep-dive, sky-tan-advice-study.
- Build: `presets/fdoe-breakdown/PRESET.md` (eye icon plus HER real view count bottom-left inside the inset) and the reaction box (632x1124 at (224,796)) in `presets/reaction/PRESET.md`; `brand_react_render.py`.
- Status: ALREADY HAVE (fdoe-breakdown is itself a TEST template; the proven default stays the full-frame source with his cutout).

---

### B. Captions and on-screen text

**B1. Word-by-word burned-in captions, muted-legible**
- What: every spoken word is also readable, so the reel works muted.
- Values (no study gives a size in px or points): Sky Tan "large white bold centered"; Luke Keegan "large bold white words with a dark outline, centered over the food, one at a time, ingredient words land as each ingredient is added"; Bitterbuilds "bold white with black outline", one style across the account; Holman "large bold white captions with black outline, fast and dense"; Kyle "bold white captions tracking rapid speech, key phrases highlighted in yellow"; Rober "large burned-in word captions"; Damian "word-by-word"; Amelia "word-pop auto-captions". Numbered-plan study: "every spoken item is also a readable item".
- Creators: most studies (see above).
- Build: OB's locked caption: Big Shoulders ExtraBold, upper case, 3 words, live word yellow (`brand/brand.json`); `ob-clipper/bin/render_clip.py`, `box_flash.py`; every spoken word captioned (`brand_react_render.lost_words`).
- Status: ALREADY HAVE.

**B2. One-word-at-a-time caption chunks**
- What: one word on screen at a time instead of a 3-word chunk.
- Values: Luke Keegan (one at a time, in sync); Kamila yellow single-word captions at chest level; Megann bold outlined word-by-word captions on two reels; Jayyang word-by-word; Damian word-by-word; Amelia word-pop.
- Creators: luke-keegan, numbered-plan-reel-kyle-megann, jayyanginspires, damian-appice, amelia-gonzamonte.
- Build: `box_flash.py ... --max-words 1` or ob-clipper karaoke at one word, same font and position, one variable against the 3-word live-yellow caption on the same footage.
- Status: NEW-TEST.

**B3. Serif caption and title families**
- What: white serif word captions and serif title cards (Megann, Kamila, Gin Lee "large white serif captions centered", Tobi white serif with dark outline in the lower third, WISDM serif country title cards, Holman serif title cards).
- Creators: numbered-plan-reel-kyle-megann, gin-lee-core-values, tobi-30day, cross-niche, ten-ten.
- Build: none.
- Status: CONFLICTS WITH OB RULE: captions in one brand font (Big Shoulders). The principle ("two caption families, one function: every spoken item is readable") is carried by B1.

**B4. Screen-centred large captions over a talking head**
- What: captions centred on the screen (Gin Lee, Sky Tan "large white bold centered").
- Creators: gin-lee-core-values, sky-tan-advice.
- Build: none. The OB equivalents already place captions at the seam (y 930 in splits), on the shirt top (845 in lecture reels) or chest height.
- Status: CONFLICTS WITH OB RULE: text never covers a face (dead centre on a talking head sits on the face). Centred placement over food-only footage (Luke Keegan) has no face and is fine.

**B5. Two-tier text: persistent topic label on top, single live word at chest**
- What: a label holds the topic while a one-word caption runs at chest level.
- Values: Kamila: white serif label at the top plus yellow single-word captions at chest level; brief collage b-roll at the opening only; voice only, no music track identified. Label size and exact y: value not given.
- Creators: numbered-plan-reel-kyle-megann, master-formats-every-link.
- Build: label in Big Shoulders Black above the cap (checked with `head_clear.py` / `faces`, below Instagram's top 220 px), chest caption from `box_flash.py` or ob-clipper; no pill behind the label (the framework-canvas pill is a box, so drop it).
- Status: NEW-TEST.

**B6. Lip-sync text essay: numbered steps at the top, words pop in sync, beat counters**
- What: one continuous take, close-up selfie, the first numbered step already on screen at frame zero, single words of the audio pop on screen in sync.
- Values: Megann B1 (morning routine, Aug 8) and B2 (Great Lock In, Sep 12); "1. get up on time (no pressing snooze!)" on screen at frame zero; handwritten-style numbered text at top of frame; popped words "said", "up", "ounces", "daily"; Lock In has beat counters ("3/4") and a "hold here for 2x" note borrowed from workout language. Her morning routine uses small numbered labels at the top of frame. Trend audio supplies rhythm. Length: not stated.
- Creators: fitnessbymegann-deep-dive, numbered-plan-reel-kyle-megann.
- Build: `reel_cards.py` lines landing on word times from `speech_words`; numerals in Big Shoulders (not handwritten); `face_clear.py` to keep the top block off his head; trend audio added in the app, file delivered without music.
- Status: NEW-TEST.

**B7. News-chyron reframe lines**
- What: text overlays build a reframe line by line like a news chyron ("They renamed PCOS today."), over gym footage.
- Values: Megann B3 (May 12); save and send instructions in the caption. Bar styling: value not given.
- Creators: fitnessbymegann-deep-dive.
- Build: `reel_cards.py` `lines` that land on his words, text on picture with shadow and no bar behind it.
- Status: NEW-TEST (the lower-third bar itself would be a box; the staged reframe is what carries).

**B8. Section label that lands as each bucket, level or step starts**
- What: a short label appears when each section begins; optional timeline labels with open-loop markers.
- Values: Amelia white lower-third label per bucket plus a small panel of example post thumbnails; Gabby ladder: white lower-third level labels, "fast, energetic, continuous pacing, no pauses between levels except brief emphasis", about 2:20; Sky Tan structure reel: on-screen timeline labels (Hook, Lead, Body 1, Body 2, Body 3, CTA) with open-loop markers between sections (marker form: value not given); Holman: day-numbered series label.
- Creators: amelia-gonzamonte, ten-ten-study, sky-tan-advice, william-holman.
- Build: `reel_cards.py` lines or `cards.py` label event placed by `head_clear.py`; brand text with shadow, no box; for ladders `explainer_cards.py dose` (see C11).
- Status: NEW-TEST.

**B9. Second-colour key phrase and the hand-drawn circle**
- What: key phrases in a second colour; a circle drawn around the line that matters.
- Values: Kyle yellow highlights on key phrases; Hayes clean white and red captions; Megann red-circled grid column.
- Creators: numbered-plan-reel-kyle-megann, four-by-four-deep-analysis.
- Build: OB yellow on the live word (`brand.json`); the red circle is `explainer_cards.py` `select` / annot.
- Status: ALREADY HAVE.

**B10. Caption the source clip's speech so the argument survives muted**
- What: the other speaker's words are captioned on screen too.
- Values: Mitch Little floor compilation, 90 to 105 s: "women's voice clips captioned on screen so the argument survives muted viewing"; host reacts (laughing in a car in the closing frame); title plus a sarcastic opening voice line. Watches in the FDOE 500 bank were muted, so text carried the check.
- Creators: mitch-little-deep-study, fdoe-500-viral-bank.
- Build: transcribe the source clip with whisper medium, caption it in a second treatment (white, no yellow) away from her face and his; his lines stay in the locked caption look; `brand_react_render.py` handles clip beats.
- Status: NEW-TEST (reaction reels and FDOE).

**B11. Fixed 1-to-10 verdict numeral on the chest**
- What: one verdict graphic that never changes design.
- Values: Dozer.wl: "a large yellow 1 to 10 numeral superimposed on the chest, with an inset trend clip and its name" and "a fixed 1-10 verdict graphic". Size: value not given.
- Creators: nutrition-focused part1.
- Build: `cards.py` stamp / number card in `#FFD400`, placed in the chest zone below the chin; the inset trend clip is the reaction box (C12).
- Status: NEW-TEST (verdict stamps exist in the reaction preset; the chest numeral is new).

**B12. Fixed comparison design system with badges and pills**
- What: layout never changes, only the words.
- Values: Fitness Chef: bold white uppercase type on rounded badges; dark green for product names; white pills with black text for calorie counts; yellow pills for the emotional tagline; red versus green when one side is the warning; readable in under two seconds at thumbnail size, muted.
- Creators: thefitnesschef-deep-dive.
- Build: none for the pills. The principle (one fixed layout, only the numbers change, red/green warning colour) is carried by C1.
- Status: CONFLICTS WITH OB RULE: brand look (no boxes, cards, pills or bubbles; `feedback_no_bubble_cards_brand_font`).

**B13. Credit line for the stitched creator and the graphics source**
- What: the original creator and any graphics source are credited on screen.
- Values: Dozer.wl: "Stitch + credit the original creator and the graphics source." Position and size: value not given.
- Creators: nutrition-focused part1.
- Build: small handle line in Big Shoulders via `ffmpeg-full` drawtext or a `reel_cards.py` line, outside the bottom 420 px, clear of both faces.
- Status: NEW-TEST (low priority).

**B14. Label and sticker vocabulary**
- What: a small fixed set of on-screen tags.
- Values: "POV" label (Mitch trigger skit); "POV, we made the news" (Today Show reel); "COMMENT REPLY" sticker; small "GROUP A" corner bug throughout (WISDM W2); role label "Content Strategist" on the host side (Sky Tan breakdown); eye icon plus view count badge (Amelia, Artzen card). Sizes and corner: value not given.
- Creators: mitch-little, cross-niche, sky-tan, amelia-gonzamonte.
- Build: `ffmpeg-full` overlay or `cards.py` label; brand font, no box; corner bug stays out of the top 220 px.
- Status: NEW-TEST.

---

### C. Layouts: split, inset, cutout, grid, strip

**C1. Calorie-matched split screen**
- What: two foods, one number, split in two.
- Values: split screen with 2,000 calories on both sides (count hook H3); 476 versus 106 calories split screen (Fitness Chef). Orientation (left/right or top/bottom) and seam position: value not given.
- Creators: cross-niche-format-library-v2, thefitnesschef-deep-dive.
- Build: top/bottom with the footage-top seam at y 960 from `styles/dylan-page-split.md`, or `ffmpeg` hstack; real food footage (her clip, his own, or logged `stock_pexels.py`); numbers count up with `moves.py counter` / `cards.py num` in Big Shoulders, no pills; his cutout (`person_mask_dir`) or face on the seam side for face-on-every-post.
- Status: NEW-TEST (FDOE frame-zero candidate).

**C2. Evidence on top, him below (split screen), plus the left/right variant**
- What: moving evidence in one half, the speaker in the other.
- Values: Plant Slant bean-salad reel opening: source creator holding a bowl on top, reactor below; abbeyskitchen WIEIAD split-screen reaction; Adam SPLIT: split screen of statue, office and training images, then training b-roll; Holman SIX: split and inset for the workout demos; Sky Tan: left/right with a role label. OB's measured split: seam y 960, evidence swaps every 1 to 4 s.
- Creators: nutrition-focused part1 and part2, four-by-four-deep-analysis, william-holman, sky-tan-advice.
- Build: `styles/dylan-page-split.md`, `styles/split-punch-bubble.md`, `ytclip_pic.py`, `brand_react_render.py`.
- Status: ALREADY HAVE (top/bottom). Left/right orientation is a NEW-TEST (not in OB's styles; each panel is 540 px wide, so check the face crop).

**C3. Cutout over a full-frame source (green-screen layout)**
- What: him cut out over her footage or a document.
- Values: "20 of 20 audit breakouts"; cross-niche: green-screen reaction layout (study says it "cannot do by itself" what Gillam does with a drawn mechanism, see E5).
- Creators: cross-niche, nutrition-focused part1.
- Build: `presets/fdoe-audit/PRESET.md`, `person_mask_dir`, `person_mask`.
- Status: ALREADY HAVE.

**C4. Cutout over full-screen working visuals (grid never returns)**
- What: after the opener the speaker stays small or centred over full-screen b-roll, images, cards, documents or a notebook.
- Values: Darren: full-screen training b-roll and graphic illustrations, brisk cuts between lifts, sprints, carries, running, about 1:40 looped; Josh TEST: full-screen document and list pages (nutrition table), speaker cut out at the bottom, very fast page flips, about 1:05 to 1:10; Hayes: black numbered habit cards ("HABIT 03 / 06") with the speaker in a small cutout, large text "6 HABITS / 6 MONTHS", clean white and red captions, about 1:00, a screenshot ask; Adam PLAN: see C10. Study range 1:00 to 1:40.
- Creators: four-by-four-format-study, four-by-four-deep-analysis, master-formats-every-link.
- Build: 10/10 engine (A8) with `reel_cards.py reel`; Hayes's counter "03 / 06" rides footage as a number (a plain black text card is not allowed alone, `feedback_no_text_only_overlays`).
- Status: ALREADY HAVE (micros ran the cutout the whole way with a 2x2 of four photos per item).

**C5. Item-per-slide list body with a talking-head inset (Omar AMOUNTS)**
- What: one slide per item showing the item, its amount and two short reasons, plus item photos, speaker in an inset.
- Values: Omar AMOUNTS: about one minute, loops at roughly 57 seconds; inset usually lower or right; ten slides, about 45 seconds; hook 0 to 3 s is an on-screen title naming ten foods with exactly how much to eat over a food, gym and physique collage; close is a spoken keyword ask and a follow ask in the caption, no link, no end card described. Other Omar reels: BALANCE (inset over photo collage, then full frame, closing "Comment BALANCE" card), WEEK, MATH (black "THE MATH" slide with the formula), CRAVE (black slides, each craving and its swap). One room, one caption style, one slide template.
- Creators: omar-bendjahene-format-study, master-formats-every-link.
- Build: `reel_cards.py` / `cards.py` item cards with the photo filling the frame (no flat black void, `feedback_fill_the_frame_graphics`), `person_mask_dir` cutout at lower right, amounts from USDA/PubMed loaded first (`evidence-check`, fabricated-stats rule).
- Status: NEW-TEST (black text slides and the black "Comment BALANCE" card are not copied).

**C6. Static one-frame numbered plan, one cut per item or block**
- What: one locked talking head in one room, cut only per item or block.
- Values: Kyle 49 s to 2:30; Megann 25 s to 2:00 (bulk 1:30 to 2:00); Kamila about 60 s; Calleigh about 30 s (30 s at 95,539 likes; Kyle number 1 at 2:30 at 76,277 likes); "fast but not frantic"; one cut per item or block, not per sentence; "length follows the plan's completeness". Setting: couch, kitchen or desk, handheld mic, a coffee cup or laptop as prop; no walking, no room changes; one take, one room, one caption style. Kyle's reference motion: 39 to 52 events a minute, idle 1 to 7%.
- Creators: numbered-plan-reel-kyle-megann, master-formats-every-link.
- Build: the 10/10 "GUT Kyle look" and "GUT Megann look" (`T7/OB-EDITS/2026-10-24-tenten/_work/`), `takes.py` + `zero_dead.py`, `motion_score.py` against the Kyle (9.3 to 9.9) and Megann (8.6 to 9.5) references.
- Status: ALREADY HAVE.

**C7. B-roll strip above or below the talking head**
- What: a small strip changes with each topic while he holds one frame.
- Values: Kyle lecture reel: "small horizontal b-roll strip across the top of the frame that changes with each topic" (track sprinting, a bed, gym work, blue-light glasses and a red-lit room, an athlete photo); plain white bold captions centred low; about 80 seconds, loop-ready; dramatic music bed under the voice (credited track). Kyle numbered plans: meme, product or posture strip above or below him.
- Creators: master-formats-every-link, numbered-plan-reel-kyle-megann.
- Build: "GUT Kyle look" in the 10/10 engine; strip must not touch his face (`faces`).
- Status: ALREADY HAVE.

**C8. Two-panel card: short label left, related photo right**
- What: one card per schedule block or item.
- Values: Calleigh: laptop two-panel cards (short label left, related photo right), one cut per schedule block, about 30 s, bold white captions at the bottom matching spoken words, no prominent background music. Card size: value not given.
- Creators: numbered-plan-reel-kyle-megann.
- Build: `explainer_cards.py` side-image / `versus` card or a `cards.py` `beside` panel with a real photo that moves (no static tile).
- Status: NEW-TEST.

**C9. Floating cutout images above the speaker, one per point**
- What: photo cutouts and small graphics pop above her head on each point.
- Values: Tobi: "floating cutout images and emojis appear above her to illustrate each point" (food, product images, a kiwi/magnesium/tea graphic on the sleep beat); static talking head on a couch, holds a small mic and counts on her fingers; "fast and direct-to-camera"; white serif-style text with a dark outline in the lower third. Size and height: value not given.
- Creators: tobi-30day-study.
- Build: real product photos cut out (`fg_cutout`), pop and drift with `cards.py` springs placed by `head_clear.py` (above the cap, never on the face); no emoji (brand look is real photos). OB rule: overlays move, no static stills (`reel_cards.py` note).
- Status: NEW-TEST.

**C10. Handwritten notebook list followed by the camera**
- What: the camera follows a handwritten list while the speaker explains the math.
- Values: Adam PLAN: full-screen talking head plus a handwritten notebook list the camera follows, slower "explain the math" pacing, about 1:35, white captions.
- Creators: four-by-four-deep-analysis, four-by-four-format-study.
- Build: shoot-side (a second notebook angle); edit with `ffmpeg` crop and pan keyframes; not a graphic.
- Status: NEW-TEST (production request, low cost to try once).

**C11. Ladder or level device**
- What: levels or rungs revealed in order.
- Values: Gabby ladder (about 2:20, boxed black-on-white title at the top, white lower-third level labels); Sam Gaudet target reel: static tripod, mid shot, home office, one printed ladder-graphic prop, on-screen captions labelling each rung as he reaches it, full-screen framework, "zero cuts needed", CTA at about 1:45; Rober "3 Levels of Elephant Toothpaste" escalation ladder (study maps it to a dose ladder).
- Creators: ten-ten-study, sam-gaudet-cult-brand-study, mark-rober-visceral-doctrine-study.
- Build: `explainer_cards.py dose`, `tier_cards.py` tier board, `styles/framework-canvas.md`. The printed prop on set is a shoot request.
- Status: ALREADY HAVE (digital). The boxed title is not copied.

**C12. Face bubble and reaction PiP over footage**
- What: his face in a small frame over the source footage.
- Values: R10 picture-in-picture reactor verdict layout; Syatt PiP narration over another creator's footage; Tony's PIP reactions are his two biggest posts (Twinkie diet 915K, fitness tracker 638K); Bitterbuilds PiP at bottom centre (persona thesis, Apr 23). OB's: face circle about 26% of width (about 280 px), top near y 240, no border.
- Creators: cross-niche, nutrition-focused part2, bitterbuilds-deep-dive.
- Build: `styles/split-punch-bubble.md` look 3, reaction box in `presets/reaction/PRESET.md`.
- Status: ALREADY HAVE (allowed for reaction and horizontal-take formats only).

**C13. Resting inset clip over his own talking head**
- What: a small clip held in a corner or bottom centre over the speaker's frame.
- Values: Bitterbuilds PiP at the bottom centre; Mitch cellulite debunk inset clip of the device treatment (about 75 s); Amelia inset "wrong example" clips, one labelled WEALTH; Damian screen recordings of the Edits app intercut.
- Creators: bitterbuilds, mitch-little, amelia-gonzamonte, damian-appice.
- Build: none. OB's alternatives are the side panel (`beside_split.py`) or a split (C2).
- Status: CONFLICTS WITH OB RULE: no resting picture-in-picture for graphics (motion-library "Not taken"; PiP is allowed only in the reaction and horizontal-take formats).

**C14. Two-chair layout, second person's reactions as the laugh track**
- What: a second person reacts beside the host and the reactions carry the humour.
- Values: R20 Wolf: two-chair layout, the second person's reactions are the laugh track. Positions: value not given.
- Creators: cross-niche-format-library-v2.
- Build: two-camera sync with `sync_av.py`, then `brand_react_render.py` horizontal looks; needs a team member on set.
- Status: NEW-TEST (production cost; low priority).

**C15. Walk-and-talk toward a tracking camera**
- What: speaker walks toward the camera on a path while talking.
- Values: Jayyang Reels 1 and 2: autumn path, tracking camera, word-by-word captions (the frame-zero title card is A2, not copied).
- Creators: jayyanginspires-deep-study.
- Build: gimbal footage cropped with `ob-clipper` face tracking; captions per B1.
- Status: NEW-TEST (shoot request).

**C16. Short street interview, trigger skit and lip-sync skit (Mitch Little set)**
- What: three low-production formats.
- Values: street interview: outdoor sunny footpath, small mic, 15 to 30 s, one clip looping, no on-screen text, CTA in caption only; trigger skit: at home, 30 to 45 s, mostly non-speech sound (the sound is the content), looping, on-screen "POV" label; Dec 17 skit: 15 to 30 s, solo, lip-sync, on-screen text. Length overall 15 to 105 s.
- Creators: mitch-little-deep-study.
- Build: `ob-clipper` for the crop, B14 for the POV label, trend audio added in the app (H2).
- Status: NEW-TEST (low priority for OB's formats).

---

### D. Cut pace, length and loops

**D1. Loop-engineered close (no end card)**
- What: the last line flows back into the first frame so the reel loops.
- Values: Amelia 28 s seamless loop of a five-sentence script; Gin Lee 25 to 28 s per loop, "short, fast, punchy, looping"; Luke Keegan about 26 s, looping; Omar loops at roughly 57 s; Sky Tan about one minute, loops back to the hook; Holman EASY loops to the title card; Darren about 1:40 looped; Rober about 2 minutes looping; Megann: "looping edits with no end card"; Jayyang typographic reel: "the loop turns a 20 second idea into 40 seconds of watch time" (the study's own claim).
- Creators: amelia-gonzamonte, gin-lee, luke-keegan, omar-bendjahene, sky-tan, william-holman, four-by-four, mark-rober, fitnessbymegann, jayyanginspires.
- Build: needs a new tool: `loop_check.py` (compares the last 0.5 s of picture and audio level against the first 0.5 s and flags a hard seam). Otherwise `ffmpeg` and a rewritten last line; as a trial arm against OB's locked closer ("anyways, bs silenced - follow if you want actual logic") and the follow card.
- Status: NEW-TEST.

**D2. Bookend close: the closer mirrors the opener**
- What: the last seconds repeat the opening asset.
- Values: Omar: client-photo collage opens and closes the reel (proof first, proof last, instruction in the middle); WISDM W3 bookend returns to the first set; W6 closer mirrors the opener (cheese pull); Holman EASY loops to the title card.
- Creators: omar-bendjahene, master-formats-every-link, cross-niche.
- Build: reuse the A8 grid or the E2 proof collage as the last 1 to 3 s with `ffmpeg` concat; face stays in the cutout.
- Status: NEW-TEST.

**D3. Jump cuts and zero dead space**
- What: tight cuts with no pauses.
- Values: Amelia jump cuts between four buckets; Sky Tan "fast, continuous, direct-to-camera"; Gabby "no pauses between levels except brief emphasis"; Kyle "fast cuts"; Holman "fast and dense".
- Creators: amelia-gonzamonte, sky-tan, ten-ten-study, numbered-plan, william-holman.
- Build: `takes.py`, `zero_dead.py`, `voice_master.py`; `motion_score.py` to confirm live 8.6 or more.
- Status: ALREADY HAVE.

**D4. One-second slide montage and very fast page flips**
- What: a rapid run of full-frame slides, about a second each.
- Values: Strauss MEALS: montage of body-part slides flashing about one second each, plus a "Save this" banner; Holman FINISHER: rapid final montage, each body-part slide about one second; Josh TEST: very fast page flips (the fastest in the 4x4 set); Adam PLAN is the slow end (see C10).
- Creators: four-by-four-deep-analysis, ten-ten-study.
- Build: `reel_cards.py reel` shots or `ffmpeg` concat of stills, 1.0 s each, each with a slow push; real photos only; `motion_score.py` for one-frame flashes; `pace_check.py` flicker limits still apply around his face.
- Status: NEW-TEST.

**D5. One unbroken take with large burned-in word captions**
- What: a single continuous shot with no b-roll.
- Values: Rober classroom capture, single continuous medium shot, about 2 minutes, looping, gray t-shirt, backwards navy cap, lavalier mic ("the unscripted version of his system"); Bitterbuilds car rants, one take under a minute, auto captions mid-video; numbered plans "one take, one room, one caption style, near-zero production cost".
- Creators: mark-rober-visceral-doctrine, bitterbuilds-deep-dive, numbered-plan-reel-kyle-megann.
- Build: lecture-at-TV pipeline (`lecture_render.py`) for his version; `takes.py` for bad takes.
- Status: ALREADY HAVE.

---

### E. B-roll, proof and plan inserts

**E1. Full-screen training or food b-roll under the cutout**
- What: footage as wallpaper for a list.
- Values: April list reels use gym b-roll as wallpaper; Darren (see C4); Adam SPLIT; Mitch.
- Creators: aprilvwhitney-deep-dive, four-by-four-deep-analysis.
- Build: `reel_cards.py reel` (hard cut about every 2 s, lines landing on words), `stock_pexels.py` (source logged), `broll_edges.py`, Frame.io b-roll library.
- Status: ALREADY HAVE.

**E2. Client-photo collage bookends**
- What: transformation collages open and close the reel.
- Values: Omar: client-photo collage opens and closes (D2); Bethany carousel: 2x2 collages of befores and afters, a question on each collage. Photo count: value not given.
- Creators: omar-bendjahene, steal-brief-bethany-dobson.
- Build: `proof_screen.py` consent screen, clearance ledger `WORK/qc/clearance.csv`, ad eligibility (men 10+ lb, women 6+), 2x2 builder from A8.
- Status: NEW-TEST.

**E3. Panel of example post thumbnails**
- What: a small panel of thumbnails under each bucket.
- Values: Amelia: "a small panel of example post thumbnails" per bucket. Size: value not given.
- Creators: amelia-gonzamonte-outcome-map-study.
- Build: `cards.py` `photo_overlay` with real screenshots of his own posts, moving, placed by `head_clear.py`.
- Status: NEW-TEST.

**E4. Study screenshots, hand-drawn graph with research abstracts**
- What: the paper or graph on screen while he talks.
- Values: bdccarpenter: hand-drawn food-versus-metabolic-rate graph with on-screen research abstracts; Lugavere: static study screenshots and image carousels; Dr Noc: data inserts with animated statistics.
- Creators: nutrition-focused part1 and part2.
- Build: the Studies card in `presets/youtube-longform/PRESET.md`, `explainer_cards.py` `num` / `slider`, PMID and DOI logged.
- Status: ALREADY HAVE.

**E5. Live-drawn mechanism sketch with a stylus**
- What: the explanation is drawn as he speaks.
- Values: Gillam: lab coat, stylus and a visual mechanism explainer on a tablet, "an on-screen title that frames the claim". The cross-niche note says OB's green-screen layout "cannot do by itself" this. OB dropped his own lab-coat framing on Oct 1, so no lab coat.
- Creators: nutrition-focused part1 and part2.
- Build: needs a new tool: a `sketch` card type in `motion_cards.py` that draws SVG strokes on word times (stroke-dashoffset in HyperFrames), same family as `belly` and `tape`.
- Status: NEW-TEST (YouTube long-form and lecture reels).

**E6. Demo footage of the movements in the top half**
- What: inset or split clips of someone performing the movements while he teaches.
- Values: Holman SIX (about 50 s): talking head seated against a plain wall, large on-screen text, inset clips of a woman performing the movements in gym and home settings (not a creator demo), title card and day-numbered series label; Holman day 14 and 15: graphics (2 to 3 hard sets vs 5 easy sets; a hip-thrust graphic listing barbell and machine versions for the gym and dumbbell and single-leg bridges at home). Layout values: value not given.
- Creators: william-holman-deep-study, ten-ten-study.
- Build: C2 split with consent-screened client clips or logged Pexels footage in the top half; graphics via `explainer_cards.py` (`checklist` / `versus`).
- Status: NEW-TEST.

**E7. Prop-model demonstration**
- What: a hand-made prop explains a mechanism.
- Values: Mitch cellulite debunk (about 75 s): prop model of chopsticks and rubber bands, solo talking head.
- Creators: mitch-little-deep-study.
- Build: shoot-side prop; edit as a normal talking head with `kick` on the demonstrating word (`moves.py kick`).
- Status: NEW-TEST (low priority).

**E8. Meme and reaction inserts that punctuate disbelief**
- What: a one-beat meme or clip insert.
- Values: Gin Lee brief meme insert of a child; Shiv Wilson reaction-meme inserts (bee saga); Dr Noc split-screen misinformation clips. Duration: value not given.
- Creators: gin-lee, nutrition-focused part2.
- Build: reaction preset "meme pops"; log the source in the clearance ledger.
- Status: ALREADY HAVE (`presets/reaction/PRESET.md`).

**E9. Diagram slide with arrows to three labelled outcomes**
- What: one diagram with three positions and arrows pointing down to three labels.
- Values: Gin Lee: black diagram slide, three positions, red arrows pointing down to "Different formats," "Different hooks," "Different visuals."
- Creators: gin-lee-core-values-study.
- Build: `styles/framework-canvas.md` (graphics on a dark dot-grid canvas, he stays in a card below).
- Status: ALREADY HAVE.

**E10. Screen recordings intercut**
- What: app or dashboard recordings between talking-head shots.
- Values: Damian tutorial: 86 s, selfie outdoors in a beanie, word-by-word captions, intercut with screen recordings of the Edits app and his own reel insights. The title card ("October 2026 update") is not copied (A2).
- Creators: damian-appice-trial-reels-study.
- Build: `presets/fdoe-breakdown/PRESET.md` screen plus rounded box layout, `moves.py counter` riding the Cronometer card.
- Status: ALREADY HAVE.

**E11. Screenshot hold plus a pointing gesture**
- What: the plan stays on screen long enough to photograph, and he points at it.
- Values: Tobi: "a specific on-screen beat where the plan is shown long enough to screenshot before the CTA"; Megann 9 by 12: she points down inviting a screenshot, "a deliberate save mechanic in the video"; Hayes and James GUIDE: screenshot ask and a grocery list to screenshot; Jake SYSTEM: 4-day split slide with exact sets held long enough to read; Nitto PLAN: Workout Split slide with exact sets and reps, Formula slide held for the rule; Strauss "Save this" banner; Holman FREE 6 Pattern "Hit Save" graphic on the close. Hold duration in seconds: value not given in any study.
- Creators: tobi-30day, fitnessbymegann, four-by-four-deep-analysis, william-holman.
- Build: a plan card held after the last item (`cards.py` card kept static only for this beat; every other moment moves), "SAVE THIS" as brand text on the picture, not a banner; gesture is a shoot cue, so the card lands on the point. Judge on saves and shares, not skip rate (PROVEN-OPENERS note).
- Status: NEW-TEST.

**E12. Black-on-white plan sheets**
- What: workout sheets, set-and-rep tables and hand-drawn Monday-to-Friday diagrams as slides.
- Values: Holman EASY: serif title cards, black pills, black-on-white workout sheets, hand-drawn Monday-to-Friday diagrams, large black "Comment EASY" card, two still photos above him; three-month plan slides with sets and reps (Month 1 and Month 3 tables). Viewers screenshot the slides.
- Creators: ten-ten-study, william-holman-deep-study.
- Build: none. The save mechanic is carried by E11 with an animated data card (`dotgrid`, bars).
- Status: CONFLICTS WITH OB RULE: text-only slides and flat white/black cards (`feedback_no_text_only_overlays`, `feedback_fill_the_frame_graphics`), pills (brand look).

**E13. Cross-section money shot plus a face tasting beat**
- What: the sliced result is the proof shot; a face-to-camera tasting beat carries emotion.
- Values: Luke Keegan names Ep. 1's two-layer slice, Ep. 5's sliced loaf and Ep. 8's sliced swirl as the money shot; Ep. 5 is "the only watched episode where Luke's face carries a beat" (a face-to-camera tasting moment); Weeknight Wins Ep. 1: Luke tasting from the pan at the end; Ep. 6 close shows him eating from a bowl.
- Creators: luke-keegan-deep-study.
- Build: shot-list items for recipe or taste content; his tasting beat to camera at the end; `thumb_frames.py` to pick the face frame.
- Status: NEW-TEST.

---

### F. Series devices

**F1. Episode or day number plus a fixed spoken opener**
- What: numbered episodes under one series name with a repeated opening line.
- Values: Luke Keegan voiceover "Episode 8 of Cut The Junk" inside the first 3 s, then the series promise; Nate Gaffney: Episode 1 onward under one name ("Interesting People for Curious Humans"), fixed opener "Send this to [archetype]"; Holman day-numbered series label; Alex Falcone series title "Is It a Scam? Yep."; Megann "THE 10/10 LIST // no gatekeeping"; Matt West "F*CK or SUCK"; WISDM serif title cards.
- Creators: luke-keegan, nate-gaffney, william-holman, nutrition-focused part2, cross-niche.
- Build: `presets/fdoe-breakdown/PRESET.md` already puts the episode number in the first frame and the caption ("LEGIT Ep 1"); the LEGIT or SH*T title grammar is OB's own. A fixed spoken opener for talking-head series is text in the script plus a `reel_cards.py` label.
- Status: NEW-TEST (the FDOE episode number is templated but itself under TEST).

**F2. Challenge package: rules overlay, timer, topic screen**
- What: one reusable overlay set per episode plus a visible clock.
- Values: Bitterbuilds challenge package: rules overlay, timer, topic screen, reused across episodes, about 1 minute spoken; R8: a 1-minute unscripted performance with a visible timer and 60 seconds of verdict. Timer size and position: value not given.
- Creators: bitterbuilds-deep-dive, cross-niche-format-library-v2.
- Build: needs a new tool: a `timer` card in `cards.py` / `moves.py` (count-down digits in Big Shoulders, below Instagram's top 220 px, no ring or pill) plus a rules line; `moves.py counter` is the model.
- Status: NEW-TEST.

**F3. Running counter**
- What: a number that climbs through the video.
- Values: count hook H3 (2,000 calories on both sides); OB's: 0 to 615 at BREAKFAST then +225 to 840 at SNACK on C4378.
- Creators: cross-niche-format-library-v2.
- Build: `moves.py counter`.
- Status: ALREADY HAVE.

**F4. Recurring physical signature**
- What: one prop or look that appears in every video.
- Values: Amelia oversized teal translucent glasses and a small fuzzy handheld mic; April small handheld mic and red nails; Megann mini handheld mic; Tobi small black-and-white mic; Bitterbuilds small mic, sometimes a glass of iced coffee; Rober lavalier.
- Creators: amelia-gonzamonte, aprilvwhitney, fitnessbymegann, tobi-30day, bitterbuilds, mark-rober.
- Build: shoot-side; OB already has the cap and the handheld mic.
- Status: ALREADY HAVE.

**F5. Part N sequel label**
- What: a second part is labelled on screen.
- Values: Megann Oct 28 watch 2 is "part two of the Oct 24 reel"; Kyle "Part 2: Automating Your Environment" overlaid "Big Boy Maxxing"; Nate YouTube breakdown Part 1 trial reels, Part 2 signature series, Part 3 infrastructure, then a recap.
- Creators: numbered-plan-reel-kyle-megann, nate-gaffney.
- Build: `reel_cards.py` label for 1 to 2 s on frame 1; the YouTube version is a chapter card (`cards.py` chapter v4).
- Status: NEW-TEST.

**F6. Trial re-edit rules (change one variable)**
- What: re-edit the raw footage like the original, then change only one thing per trial.
- Values: Damian: change only music or instrumental, on-screen text font, text placement, caption, and colour grade; winner edits use white bold captions (series format) with credited audio (C418, Minecraft; C418, Wet Hands).
- Creators: damian-appice-trial-reels-study.
- Build: `trial_variants.py`, `first3_check.py`, `styles/trial-reupload.notes.md`.
- Status: ALREADY HAVE.

**F7. Execution variants of one script**
- What: the same hook with different delivery.
- Values: Nate Five Method: camera fixed, creator in front with a microphone, each execution slightly different, 3 to 10 minutes per video, never 20; execution variants: text on screen instead of voice, text plus audio, a long written description; hook scripted word for word (one or two words changed can be the difference), body from bullet points; "FaceTime-with-a-friend" tone.
- Creators: nate-gaffney-deep-dive.
- Build: three trial arms off one take: normal, text-on-screen with his face visible and no voice (B1 captions, track added in the app), text plus voice; `trial_variants.py`.
- Status: NEW-TEST.

**F8. Keyword CTA placed in the reel versus caption only**
- What: where the CTA keyword lives.
- Values: April: in 4 of 5 reels the keyword CTA appears only in the caption; on-screen text carries the thesis, the caption carries doctrine and funnel. Master-formats: "keyword spoken in the reel, not caption-only, for conversion". Omar: spoken keyword ask, caption follow ask, no end card; Megann: keyword in the caption in every case ("the video earns the attention; the caption runs the funnel").
- Creators: aprilvwhitney, master-formats-every-link, omar-bendjahene, fitnessbymegann.
- Build: trial arm with a spoken CTA line versus none; `moves.py comments` is the on-screen form. No keyword funnel on FDOE (fdoe-breakdown note).
- Status: NEW-TEST.

**F9. Black banner and black end-card CTAs**
- What: a black banner or card with the keyword.
- Values: Holman FINISHER black banners ("Save this", FINISHER); Holman EASY large black "Comment EASY" card; Omar BALANCE closing "Comment BALANCE" card.
- Creators: ten-ten-study, omar-bendjahene.
- Build: none. The save cue is E11 as brand text on the picture.
- Status: CONFLICTS WITH OB RULE: no black bands or boxes, fill the frame.

**F10. Faceless or text-only formats**
- What: formats without the creator's face.
- Values: Luke Keegan Ep. 8: hands, bowls and a loaf pan, no talking head, voiceover carries the whole recipe, about 26 s; Jayyang F1: black screen, minimal white line art, deep cinematic voiceover, no face, captions 80 characters or less, seamless loop; Jayyang F2: one black image, serif font, about 120 words; Jayyang F3: six slides, one line each, attribution frame per slide; W5: faceless 3D animation with branded props; W4: no voiceover, a music track carries it.
- Creators: luke-keegan-deep-study, jayyanginspires-deep-study, cross-niche-format-library-v2.
- Build: none. Usable fragments live elsewhere: words landing as ingredients are added (B1), cross-section shot plus a face tasting beat (E13), loops (D1).
- Status: CONFLICTS WITH OB RULE: his face on every post (`feedback_face_on_every_post`); black screen / text-only (no black bands, no text-only); a "deep cinematic voiceover" produced like a trailer would also need to be his own voice, never AI.

---

### G. Carousels

**G1. Same photo in colour on top and black-and-white below**
- What: two stacked panels per slide, the grade is the only change.
- Values: thesis study winner: same photo, colour on top and B&W below, slides 1 to 6, "no new photos, just a grade change between panels"; 6 to 8 slides (winner 7; Oct 20 chain 8; Oct 24 8 slides; Oct 26 7 slides); canvas 4:5; Tyler benchmark: colour top, B&W bottom for slides 1 to 6 (sent post 8 slides); Jeff and Jun reframe carousels: B&W on top (problem half), colour below (reframe half), white bold text over each half; "device cost is near zero (one photo per slide, duplicated and desaturated on top)"; text "large and plain".
- Creators: thesis-carousel-complete-study-v3, you-are-not-behind-carousel-study, master-formats-every-link, steal-brief-you-are-not-behind.
- Build: `~/ob-carousel/tools/split_render.py` (1080x1350, modes `bw_color`, `pair`, `card`).
- Status: ALREADY HAVE.

**G2. Dim top, bright bottom**
- What: stacked panels with a brightness split instead of a colour split.
- Values: Martell: vertical split screen per slide, dim top and bright bottom, key words bolded, final black card with a small logo; Port B: seven split screens (dim top, bright bottom); 7 slides. Dim/bright amounts: value not given.
- Creators: you-are-not-behind-carousel-study, steal-brief-you-are-not-behind.
- Build: add a `dim_bright` mode to `split_render.py` (a brightness curve on the top half); end on a full-frame photo card, not a black card with a logo.
- Status: NEW-TEST.

**G3. Pattern-breaking full-bleed final slide**
- What: the last slide drops the split and runs one full-bleed photo with the thesis or CTA.
- Values: winner slide 7 (sent post slide 8) is a single full-colour photo; Oct 24 slide 8 and Oct 26 slide 7 full-bleed thesis; Chloe 3-slide deviation (full-bleed mirror photo with the thesis line on slide 3); Jun Yuh 13-slide story arc with a full-bleed CTA on slide 13; Jun reframe: 10 slides with a question-close on slide 10; Jeff: 5 slides, no CTA slide; Tyler sequel 8 slides, full colour (B&W dropped); Audrey 6.
- Creators: thesis-carousel-complete-study-v3, you-are-not-behind-carousel-study, nutrition-focused part2, master-formats-every-link.
- Build: `split_render.py` `card` mode over a darkened full-bleed photo.
- Status: ALREADY HAVE.

**G4. Creator in every photo, photos and plain text only**
- What: real photos of OB with plain text, no graphics package.
- Values: "photos of Ob plus text, no filming"; thesis study: creator in every photo; Port A: OB photo on every slide; Sam Gaudet: 8 slides (hooks) with a footer brand on every slide.
- Creators: steal-brief-you-are-not-behind, thesis-carousel-complete-study-v3, sam-gaudet-cult-brand.
- Build: `~/ob-carousel/tools/overlay_render.py` (text or tweet-card look); the per-slide footer handle is a NEW-TEST detail (G5).
- Status: ALREADY HAVE.

**G5. Brand footer on every slide**
- What: a small brand line repeated on each slide.
- Values: Sam Gaudet footer "topicfinder.ai" on every one of 8 slides. Size and position: value not given.
- Creators: sam-gaudet-cult-brand-study.
- Build: `split_render.py` has `foot` only on card mode; add it to the other modes, `@ob_health.fit` in Big Shoulders.
- Status: NEW-TEST.

**G6. Client-results carousel structure**
- What: before/after splits and collages with payoff lines.
- Values: Bethany steal brief: before/after split (cover, slides 4 to 7 per client, bridge); 2x2 collages (befores, afters); back-view before/after split for Jenn; single photo slides; challenge quote on the cover; "1 rule" hook on slide 2; rule statement with quoted hype instruction on slide 3; payoff lines per client slide; a question on each collage; smiling CTA photo. Mitch Natasha carousel (10 slides) adds day-of-eating slides with weighed ingredients and macros.
- Creators: steal-brief-bethany-dobson, mitch-little-deep-study.
- Build: `ob-carousel` `client_library.py`, `overlay_render.py`, `quadcut.py`; `proof_screen.py`; meal slides from the meal planner / diet analyzer.
- Status: ALREADY HAVE.

**G7. Emoji-covered faces on before/after selfies**
- What: Natasha carousel: before and after split mirror selfies with faces covered by emoji.
- Creators: mitch-little-deep-study.
- Build: none.
- Status: CONFLICTS WITH OB RULE: OB's proof uses consent-screened visible faces (`reference_ob_curated_proof_library`) and `feedback_carousel_client_results_slides` ("less blur"); no template-looking stickers on proof.

**G8. Cheat-sheet, infographic and haul carousels**
- What: save-first reference slides.
- Values: evidencebased_training daily infographic cheat-sheet carousels; Pathradecha numbers carousel; Lugavere static study screenshots; Mamavation lab-results image carousels (EPA-certified lab results, caption text only, not measured); lifeuntox 11-slide photo and text carousel with the follow prompt last; organicmindedmom 15-slide haul (cover, fourteen product slides, a store shot of the creator); April Cornell witness-statement carousel, nine slides, no CTA.
- Creators: nutrition-focused part1 and part2, misinformation-grocery-fear-creators-v3, aprilvwhitney-deep-dive.
- Build: `~/ob-carousel/build.js` and `audit.js` (layouts `grid`, `tiers`, `ladder`, `vs`, `photo`), `mega_costco_guide.py`.
- Status: ALREADY HAVE (the nine-slide first-person statement is a text carousel; only build it in the photo look, G4).

---

### H. Sound

**H1. Voice-led, music optional and never the message**
- What: the voice carries the message; music is a per-reel choice.
- Values: 4x4 rule: music is credited per reel where present but never carries the message (Josh: electronic track credited on the page; Adam SPLIT: none prominent); numbered plans: Megann named tracks (instrumental, piano, pop), Kyle credited tracks per reel (one repeats across two energy reels), Kamila voice only, Calleigh speech-driven; "music is not required for outlier performance"; study recommends one trial with music and one without.
- Creators: four-by-four-format-study, numbered-plan-reel-kyle-megann, master-formats-every-link.
- Build: `music_variants.py`, `tier_music.py`, `MUSIC-LIBRARY.md` Lane A (21 to 27 dB under the voice) plus a voice-only copy; feed posts ship voice-only.
- Status: ALREADY HAVE.

**H2. Trending or original audio added in the app**
- What: the trend sound or the creator's own audio supplies the rhythm.
- Values: Megann lip-sync posts on trend audio; Yogasini trending-audio react and a 10-second trend-react format; Damian winner edits credit C418 tracks; Tobi credits an Ayra Starr track; Druski and Golden Balance use original audio; abbeyskitchen theatrical lip-sync satire; Kyle lecture reel dramatic music bed (credited).
- Creators: fitnessbymegann, nutrition-focused part1, damian-appice, tobi-30day, cross-niche.
- Build: Lane B: deliver the file without the commercial song, add it in the Instagram app; never bake it in (music-bed rules in `SKILL.md`).
- Status: ALREADY HAVE.

**H3. Visuals locked to the beat**
- What: entrances and hook land on the beat drop.
- Values: Sky Tan breakdown reel: trending audio with a beat drop, visuals timed to the music, an "insane visual hook" timed to the beat drop.
- Creators: sky-tan-advice-study.
- Build: `assemble.py` beat lock for Lane A beds; SKILL "lock graphic entrances to the beat".
- Status: ALREADY HAVE (Lane A tracks only; a Lane B in-app song cannot be locked at export).

**H4. Sound effects timed to visuals by default**
- What: Sky Tan breakdown reel: "sound effects timed to visuals".
- Creators: sky-tan-advice-study.
- Build: none (when OB asks for an SFX beat, `sfx.py` and the SKILL rule 3 govern: a handful, planned per edit).
- Status: CONFLICTS WITH OB RULE: no SFX by default (only where a beat needs one, OB 10-29).

**H5. Wordless persistent-text thesis over trending audio**
- What: one scene, one line of text that stays on screen, no speech.
- Values: April DFHOI: one scene, April at a table eating eggs and greens, white tank top, pointing at the camera, trending sped-up audio, no on-camera speech; persistent text "if you have to eat 1,000 cals to keep that body, then that is not your body, read that again."; Fitness Chef wordless myth bust: licensed music (Taylor Dayne, "Tell It to My Heart"), on-screen text cards, deadpan footage, no speech; Gabby tag clip: a woman at a table eating a salad, looking to camera, no spoken narration, message carried by on-screen text. Length: not stated.
- Creators: aprilvwhitney-deep-dive, thefitnesschef-deep-dive, ten-ten-study.
- Build: his face in one locked shot; text in Big Shoulders placed off the face by `faces` / `face_clear.py`, held for the whole shot (a rare static text beat; the shot itself moves); trend audio added in the app, file delivered without music; the claim passes `evidence-check` first. Text sits on the picture, not on cards.
- Status: NEW-TEST.

---

## 3. Top 10 to build or test first (OB's formats: FDOE audits, reaction reels, talking head, lecture-at-TV, YouTube long-form)

1. **C1 Calorie-matched split screen** (FDOE frame zero): two creators' hooks (2,000 on both sides, 476 versus 106) and it puts the food number in frame 1 (`PROVEN-OPENERS` rule 5, best follows lift 1.18x) with tools OB already owns.
2. **A3 Comment-reply sticker or comment screenshot as the hook**: real comments are free, give text on screen from frame 1 (rule 3, best saves/shares lift) and work on talking heads and reactions alike.
3. **B10 Captioned source-clip speech on reactions and FDOE**: the one idea in the set built for the muted viewer, and every reaction reel has a source speaker to caption.
4. **D1 Loop-engineered close (no end card)**: ten studies run looping reels from 25 s to about 2 minutes; cheap (a rewritten last line plus `loop_check.py`); tests against OB's locked closer as a trial arm.
5. **A5 Hook-frame fragment with the last word highlighted**: a text-only change to frame 1, one variable, no new tool.
6. **B2 One-word caption chunks**: six creators run single words; `box_flash.py --max-words 1` already exists, so it is a one-variable trial on the same footage.
7. **C9 Floating product and food cutouts above the speaker**: gives talking heads and FDOE "moving overlays on his words" (OB's C4395 rule) with real photos; uses `head_clear.py` placement.
8. **E11 Screenshot hold plus a pointing gesture**: five creators build a deliberate save mechanic, and OB's plan reels (reta plan, meal plans) already have a plan worth saving; judged on saves and shares.
9. **H5 Wordless persistent-text thesis**: April and Fitness Chef run it, it is the cheapest build in the set (one locked shot, one line, audio added in the app), and it tests a no-speech reach format.
10. **E5 Live-drawn mechanism sketch**: the only technique that fills a stated gap in OB's YouTube and lecture layouts (the study says his green-screen layout cannot do it); highest build cost of the ten, so run it on one long-form chapter.

Next in line: D2 bookend close, C5 item-per-slide list body for the 10/10 lists, A4 payoff-first open for recipe reels, F2 timer package, G2 dim-top/bright-bottom carousel.

---

## Appendix A. Tools the NEW-TEST entries still need built

| Tool | Used by | One line |
|---|---|---|
| `loop_check.py` | D1, D2 | Compare the last 0.5 s of picture and audio level to the first 0.5 s and flag a hard seam. |
| timer card (in `cards.py` / `moves.py`) | F2 | Count-down digits in Big Shoulders below Instagram's top 220 px, no pill or ring. |
| `sketch` card (in `motion_cards.py`) | E5 | SVG strokes drawn on word times, same family as `belly` and `tape`. |
| `zoom_portal` (in `moves.py`) | A7 | Spring zoom into a point with a growing circle mask into the next shot (motion-library section G #7). |
| `dim_bright` mode and `foot` on all modes (in `~/ob-carousel/tools/split_render.py`) | G2, G5 | Brightness split on the top half; brand footer on every slide. |

## Appendix B. Reference values quoted in the studies (no build)

- Lengths: Amelia sent reel 28 s, breakdowns about 55 s; Damian tutorial 86 s; Gin Lee 25 to 28 s per loop; Luke Keegan Ep. 8 about 26 s; Holman SIX about 50 s, GUIDE about 50 s, FREE 6 Pattern about 90 s; Omar about 57 to 60 s; Gabby ladder about 2:20; Sky Tan sent reel about one minute; Rober about 2 minutes; Mitch: street 15 to 30 s, trigger skit 30 to 45 s, floor compilation 90 to 105 s, cellulite debunk about 75 s, Dec 17 skit 15 to 30 s; Nate Gaffney trial format 3 to 10 minutes, never 20; Alex Falcone explainers about two minutes; 4x4 grid reels 1:00 to 1:40; numbered plans 25 s to 2:30 (bulk 1:30 to 2:00).
- Hook timings: first 3 seconds carry the promise (4x4, master-formats, Dr Noc); target named in 5 s (Luke Hannan); a verdict "in under 60 seconds" (theguthealthdoctor); "save the winner for the final second" (ilanamuhlsteinrd); a 4-second meme (yogasini top post).
- Slide counts: thesis 6 to 8 (winner 7); Martell 7; Tyler 7 (sequel 8); Audrey 6; Jeff 5; Jun 10; Jun Yuh story arc 13; Chloe 3; Sam Gaudet 8; Sky Tan 8 and 9; Omar ten-slide body; Natasha 10; lifeuntox 11; organicmindedmom 15; April Cornell 9.
- Post-caption lengths (not burned-in): Mallory 24 to 196 characters, lowercase, zero CTAs; No Food Rules median 98 characters; a near-captionless recipe video still pulled about 2K likes (dietitiancass); full recipes in the caption as the saveable element (j.newtrition, mattwest_roadtoaesthetics).
- Not measured anywhere in the 38 studies: caption size in px or points, shot length in seconds (beyond OB-measured numbers), exact zoom values, transition types, grid-to-body retention.

## Appendix C. Studies with no editing content in section 4

bethany-proof-stack-candidate-roster, fdoe-300-audit-memo, fdoe-300-review-bank, fdoe-400-new-bank, fdoe-500-viral-bank (only: watches were muted), fdoe-saved-bank-plus-100, saved-videos-master-harvest-v2 (parts 1 and 2), misinformation-grocery-fear-creators-v3 (three specimen formats only, in G8). Section 4 of these says "none" or lists captions and ranking only.
