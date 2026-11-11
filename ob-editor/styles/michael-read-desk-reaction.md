# Style card: T25 desk reaction (Michael Read, @michaelreadart.official)

**Why it's here.** OB sent DfRw4sMtL7P on 11-07: "this could be another reaction style, he has almost the exact same setup as well me".
- **Measurement:** 4 of his reels tracked at 10 fps (DfRw4sMtL7P, DfMz_tvtMkR, DfFnC6QtmjH, DfAC66EtmlB), dense grids at the handoff and every cut, word times by whisper.
- **Files:** T7 `OB-EDITS/2026-11-07-style-truth/reel-DfRw4sMtL7P/`: grids `overview.jpg`, `d_intro.jpg`, `d_cuts.jpg`, `o2.jpg`, `o3.jpg`; the reel list `reels_p1-3.json`.
- **Numbers:**
  - DfRw4sMtL7P did 64,369 plays: 19.9x his median of 3,230, 3,273 likes, 404 comments, posted 11-03.
  - He has only 6 recent reels (the rest are 2019 gym posts), so that median is thin. Treat this as one breakout, not a proven pattern.

## ENGINE FIXES 11-07 (gap audit `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/TEMPLATE-GAPS-11-07.md`)
- **Title** is on from frame 0 (`"enter": "hard"`), with per-line sizes and colours. Line 2 is "WARNING", bigger and pink.
- `"y_mode": "center"` puts the block at y ~1070-1290; `"box": true` draws his thin pink outline.
- **Card position:**
  - The C4413 test frame has OB's head RIGHT of centre, so the card moved to the free left wall [56, 236, 416, 876] at full size.
  - The old box covered his eye.
  - Rule: the card goes on whichever side of his head has open wall.
- **Arrow:** a pink `marks` curve (`"color": "pink"`) when wanted.

## His setup (the same as OB's)
- Seated at a desk.
- A dynamic mic on an arm, held near his mouth.
- A poster wall and a warm lamp behind him; a drink can on the desk.
- One locked vertical camera, framed wide: his face is 150-190 px wide while reacting and 230-290 px while talking.
- The lower ~30% of the frame is the dark desk front.

## The reaction runway (0 to 7.8 s)
- **He is full frame, reacting live and silently** (eye roll, yawn, "no cap" mouthed) while the other creator's clip plays with its own sound.
- **The clip sits in a 9:16 rounded card over the wall beside his head:**
  - x 576-944, y 260-912 (368x652), radius ~16;
  - a thin light-pink border (~3 px);
  - on from frame 0, with no entrance animation;
  - it never covers his face.
- **Title over the desk, under his chin (y 1070-1290):**
  - line 1: the topic ("AI EDITING VIDEOS"), white heavy condensed caps with a dark stroke;
  - line 2: "WARNING", bigger, in light pink (~#F0BDB6);
  - both inside a thin rounded outline box.
  - A thin pink hand-drawn arrow curves from the title box up into the card.
  - On from frame 0, gone on the handoff.
- **Captions** of the source's words: small white bold sentence case, 1-2 words, y ~1036, just above the title.

## The handoff and the body
- **The handoff (7.8 s) is a hard cut.** The card, title and arrow go. He punches in ~1.34x on his first word, a one-line verdict ("Yeah, no shit, Sherlock").
- **The body is one continuous take** with a jump cut every ~5-9 s at sentence starts (16.2, 21.3, 30.4, 38.4, 47.1, 56.4, 61.2). The framing alternates ~1.0x and ~1.13x. No zoom animation: every change is a cut.
- **Captions:** small white bold sentence case, 1-3 words, at chest height (~y 1030).
- **Receipts** (his other reels): phone screenshots (Instagram profiles, reel thumbnails) as floating rounded cards over the wall beside or above his head, popping in on the word that names them. In DfMz_tvtMkR there are 3 thumbnails in a row across his chest. Never on his face.
- **Ending:** on his face. No end card, no music.
- **Script shape:**
  1. the clip's claim;
  2. a one-line verdict;
  3. "Here are three reasons why...";
  4. "Number one / two / three", each with a short story or analogy;
  5. "Listen, I get it...", the concession;
  6. a well-known saying as the closer;
  7. a rhetorical question.
  - 66 s.

## OB's version (T25)
- **Film the runway as real playback (M34):** play the clip OUT LOUD on the phone or monitor and film yourself watching it.
  - Frame wide, with your head left of centre, so the card fits over the wall on the right.
  - Then deliver the lines to the lens in the same setup.
- **Edit (tmpl):**
  - **Runway:** a `src` line with `"line": "runway"` and `{"name": "source", "peek": {"mode": "card", "cam": T_OF_HIS_WATCHING, "box": [700, 250, 1036, 848], "radius": 16}}`.
  - **Title:** a `title` element with `"lines": [[TOPIC...], ["WARNING"]]`, `"accent": ["WARNING"]`, `"y": 1230`, `"at": 0`, `"only": ["runway"]`. Big Shoulders, white + #FFD400, **no box** (OB's no-boxed-text rule; his thin box and pink arrow are one switch if OB wants them).
  - **Handoff:** `{"name": "full", "push": [1.3, 1.3]}`.
  - **Body:** `full`, alternating `push` [1.0] / [1.13] per sentence block.
  - **Receipts:** `image` elements with `radius` and a white `border`, beside or above his head.
  - **Captions:** OB's locked style by default (his small white sentence case is a test variable).
- **Test (11-07, C4413 + DdJWjTsspZw):**
  - Plan: `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/t25-test/T25_deskreact.json`.
  - Stills: `out/STILLS_T25.jpg`.
- **House rules:**
  - Face on screen: OK, he is full frame throughout.
  - Two people at 0.4 s: OK, the card is on at frame 0.
  - M38: no issue, there's no board.
  - M37: his voice is never under a full-screen overlay.
