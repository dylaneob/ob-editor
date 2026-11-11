# Style card: framework canvas (Kallaway "story pyramid")

OB 2026-10-28: "love this format as well", https://www.instagram.com/reel/Derji4txGJD/ (Kallaway, @kallawaymarketing, posted 10-19, 112 s, "the ultimate storytelling framework for boring businesses"). Decoded 10-28 from 17 scene frames, three contact sheets (54 frames) and the transcript. The study copy (360x640) is in the session scratchpad only.

Same family as `split-punch-bubble.md`: a horizontal desk take, cut into a wide shot and a close-up, under graphics. The difference is that one framework diagram carries the whole video. It is a teaching reel built around one named model with numbered steps.

## Beat sheet
**Signature moves:**
1. **The map comes back.** One framework diagram (his red pyramid, tiers 1-4) is shown up front with every label blurred. It returns at each "Step N" and the next label unblurs. At the end all four are clear for the recap.
2. **Canvas plus desk card.** Graphics sit on a black dot-grid canvas in the top 70%. He sits below in a wide rounded card (his desk shot), so he never leaves the frame while the picture changes.
3. **A step's name stays up.** It sits in a pill at the top for the whole step ("Pick The Right Topic In The First Place").
4. **Each sentence draws one thing.** An icon crowd fills red for "the ideal topic", numbered cards "1" and "2" open into sentences, "New Way VS Old Way" cards meet at a VS circle, a retention line draws. Nothing is decoration.
5. **One or two words of caption at a time,** white bold sans just above his card. Key phrases switch to a serif italic ("The Story Pyramid.", "Content Growth Challenge,").

**Pace (motion_score.py, 360p copy):**
- about 48 events a minute; median gap 1.08 s, p90 2.4 s, longest 6.8 s
- 8.6 hard cuts a minute
- idle 13%, live score 8.7/10, first move at 0.04 s

**Looks:**
- canvas + desk card 59% of the runtime, full-frame close-up 41%
- 40 look changes, one every 2.8 s on average
- the cut anchor is the sentence: a new element on the word that names it

**First 2 s:**
- frame 1 is already the canvas + card
- six phone thumbnails (examples of the topic) burst out of the centre into a ring by 0.8 s, with a red badge in the middle ("Storytelling Framework")
- the two-line title writes itself in word by word at the top: serif italic for the idea, bold sans for the rest
- the caption follows his words underneath

**Energy curve:**
- fast first 2 s
- full-frame close-ups on the step turns ("Now step two is...")
- long canvas stretches (9-11 s) inside each step, carried by the elements building
- the recap pulls the whole pyramid back
- the CTA (his course site, tilted screenshots, "Comment 'Launch' To Get The Link") runs the last 12 s

## Layout (measured on 360x640, scaled to 1080x1920)
| Part | Value |
|---|---|
| Canvas | near-black (#050505) with a faint dot grid, about 20 px pitch |
| Desk card | full width minus about 72 px a side; top edge at about y 1410, running off the bottom; rounded top corners (about 36 px) with a faint cool edge glow; his wide desk shot, cropped about 2:1 |
| Caption | 1-2 words, white bold sans, about 55 px, centred just above the card (about y 1284) |
| Full-frame look | a 9:16 punch-in from the same take (face and chest), caption at the same height on his chest |
| Step pill | red-filled or red-outlined rounded pill with white title-case text, top centre (about y 144) |
| Diagram | centred about y 990, about 510 px wide; red with a soft glow; numbered tiers; label boxes with thin outlines on leader lines |
| Accent | one red with glow; everything else white, grey and black |

## Graphic vocabulary (all seen in the reel)
- **The framework diagram** returns with labels unblurring one step at a time.
- **An icon crowd in a dashed circle** (the audience); a share turns red with a label ("Ideal Topic").
- **"Don't X:" with stacked outline pills** for the two don'ts.
- **Number cards** "1" and "2" that open into their sentence, then one outline pill for the key term ("State Change").
- **A phone mockup** playing an example reel, with a stat badge under it (a views count).
- **"New Way VS Old Way"**: two labelled cards meeting at a VS circle, then a big translucent red circle around the winner and its "Outcome".
- **A line chart that draws** (retention), in red.
- **A white glowing silhouette** of a person on a phone (one beat).
- **A list card with small icons** ("Boring Topics": spreadsheet, accounting, water bottle, corporate meeting).
- **The CTA:** the offer's wordmark, tilted website screenshots with a glow, and the comment keyword line.

## Mapping to OB
- **Which takes:** horizontal desk takes with a framework he names out loud. The 4K frame gives both the wide card (cropped about 2:1) and the 9:16 close-up, like Variant B's two framings.
- **Length:** a teaching reel, so 90-119 s (B30), but always under 1:30 when it is cut from one of his YouTube talks (OB 10-29, M33). This reel runs 112 s.
- **Backlog fit, C4383:** he says "calories is weight, macros is how you look, micronutrients is how you feel" (about 5:47). That is a three-tier diagram that can come back at each tier. Fact-check the take's claims before it's scripted: Minnesota "1,200 a day", hip fracture "70%", "up to 60% lean tissue", "keto has no protein".
- **His brand over Kallaway's:**
  - Big Shoulders replaces the bold sans and the serif italic.
  - #FFD400 replaces the red as the accent, unless OB wants red kept.
  - The canvas stays black.
  - Captions: his locked brand captions, cut to 1-2 words for this format, live word yellow.
  - The diagram's label boxes are thin outlines on black, part of the drawing. They are not the white rounded caption cards he called AI-looking (`feedback-no-bubble-cards-brand-font`), and captions never get boxes.
- **IG safe zones:**
  - Kallaway's step pill sits in IG's top bar and his face low in the card. For OB, the pill goes at about y 250.
  - The card moves up to about y 1240-1720, so his face clears the bottom band (420 px).
  - Nothing goes on his face; in the full-frame look the caption sits on his chest.
- **Proof:** a diagram tier that claims a result shows a real client or a sourced study (the trust ladder in `reference_kallaway_study`), never a stock person. The silhouette beat is a drawn shape, not AI imagery (M28).
- **Build on first use:**
  - A canvas + card compositor is needed, for the card crop and the 9:16 crop of one take.
  - The diagram and elements: HyperFrames (vector, blur to sharp, line draws) or `cards.py` springs, POP for entries and SOFT for label reveals.
  - Captions from the brand layer.
  - As always: zero dead space, word-safe cuts, the QC gate, and a shot list with real stills before any render.

## Built 2026-11-04
OB on another Kallaway reel (DfUhxJqxLxP, viral storytelling framework): "for this format we have the me in the bottom down but you never make animations like this above me for this format". That reel's bottom-card moments: a light grid with a 3x3 thumbnail grid popping in (label above, green views badge below) while the title writes "Viral Storytelling Types" with a red underline; a black canvas with "Viral storytelling framework" (sans + serif italic) and 01-04 rows sliding in with a red accent on the live one. Built as `~/ob-editor/bin/canvas_card.py` (title, count, rows; brand font and yellow). Still to add: the thumbnail grid with badges, phone mockup, document stack, VS cards.

## Expanded study 2026-11-04 (8 reels; corrections + element library)
OB 11-04: "obviously the kallaway one as well", and more references per creator. Measured on the 1080x1920 masters: the two reels above plus his 6 biggest outliers of his last 60 (median 37.7k plays): DaiCxAkOpNb 33.6x (pinned), De_5mQ0R8PE 15.8x, Dewd5EDO-16 4.2x, DeaG6ajs8Mf 3.7x, DeMSNPixWZm 3.4x, DdjPoBjuPBD 1.75x. Decode: `/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/kallaway/DECODE.md` (element gallery `sheets/ELEMENT_GALLERY.jpg`, frame-by-frame entrance strips in `strips/`). It maps every box into OB's layout with `x_ob = 540 + 0.78*(x - 540)`, `y_ob = 240 + 0.78*(y - 120)`.

**Corrections to the values above:**
- The card has **no glow**: a hard edge, top corners about 38 px radius, x 72-1008, y 1408 to the bottom (OB's stays at y 1240-1720 for the IG band). His cap and raised hands are matted over the card edge 60-90 px (identity; OB's head pop-out from T02 is his own version).
- The dot grid is a **15-16 px pitch at only 2-5 levels over the base**, with a vignette; some outliers are pure black. `canvas_card.py` draws 22 px and brighter.
- A light canvas (#E4E4E4 with 17 px graph lines) marks "real examples and proof"; dark is for concepts. #FFD400 on that light grey is about 1.2:1 contrast, so OB stays dark or uses a paper surface with black Big Shoulders and yellow only as a highlighter.
- The split is about **70% canvas + card, 30% full-frame him** (7 of 8 within 68-77%). Full frame carries the telling lines (the promise, the stakes, rules, step-turn re-hooks, the close); the canvas carries the showing lines (definitions, parts, examples, data). Full-frame inserts run a median 2.1-4.4 s.
- Pace: 47.8 events a minute, a new canvas state about every 6 s with 4-6 builds inside it, live 8.85, idle 11.5%, first move 0.04 s. Elements land a median **150 ms before** their word; map returns land 0 to +150 ms after the step-turn word. No SFX layer and no music: the motion carries it. Wall-to-wall voice, -14.1 to -14.5 LUFS.

**Two habits under every element:**
- **The blink** ("this one"): 3 flashes on alternating frames, about 0.24 s, then a hold. Single-frame states fail OB's QC gate as flash frames, so OB's blink uses 2-frame states.
- **The canvas camera:** holds are never still (1-3% scale a second, slow drift); big diagrams get real pans and zooms node to node (ease-out 0.8-1.2 s) while the card stays fixed.

**Element library** (IN = in `canvas_card.py`, PARTIAL, NEW): E1 title (PARTIAL: his is centred, words blur in over 3-4 frames or type on at about 100 characters a second) · E2 **returning framework map** (PARTIAL: future steps blurred, the next one 1.15-1.2x, active row blinks then unblurs in 0.2 s, done rows dim with a tick; back as a full state on every step word, 3-6 times a reel, in 7 of 8) · E3 phone mockup playing a real clip (NEW, 8/8) · E4 thumbnail grids, rings and pairs with real view badges (NEW, 7/8) · E5 document with highlight bars (NEW) · E6 checklist with ticks (NEW) · E7 line chart that draws (NEW, 6/8) · E8 icon crowd that fills · E9 number tiles that open into sentences · E10 outline pill stack · E11 VS cards · E12 flow/tree diagram · E13 stat card with a count over a whole sentence (PARTIAL) · E14 gauge · E15 glowing icon sets · E16 analogy scene · E17 timeline bar · E18 CTA screen showing the real deliverable · E19 canvas camera · E20 annotations on media · E21 step header pill. Each one's box, entrance timing and OB brand version: decode §3 and §7.

**Ranked build list for `canvas_card.py`** (decode §8; the short-form editor tab owns the module and is extending it on 11-04): 1 E2 returning map v2 (medium) · 2 E3 phone + E4 grid with real view badges (large for video, medium for stills) · 3 E7 line chart (medium) · 4 E5 doc + highlight with E6 checklist (small-medium) · 5 E11 VS cards (small) · 6 E9 number tiles (small-medium) · 7 E13 stat card (small) · 8 transitions: blink, drift, whip, defocus-slide (small). Not yet: gauge, analogy scenes, icon sets, the head-over-card matte.

**Script shape across the 8** (vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T06): hook in 3-4 s -> the framework named by 3.5-5.5 s (the map appears with the name) -> an amplifier line by 10 s -> 3-4 steps (or 6 items), each: rule, reason, parts (one/two/three), example or analogy, test or consequence -> every step turn is a re-hook and a map return -> a one-sentence recap naming every part at 82-90% -> CTA. His two biggest outliers are the only ones stacking an impossibility hook + a named method + an extreme-mechanism line (n=2: a pattern to test, not a law).

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** tmpl_fx `map` (build-list item 1: future steps blurred, the next one 1.15x, the active one blinks in 2-frame states and unblurs, done steps dim with a tick). The canvas + card module itself is canvas_card.py.

**A Kallaway-type relative (11-04): Nate Herk's split list = T20** (`styles/split-list-nate-herk.md`). OB sent DfVEGmvgIm_ as "another kallaway type of edit". Same grammar (map visible from frame one, step turn on the ordinal word, keyword CTA), different body: a hard top/bottom split instead of the card, the map as a grid of blurred numbered tiles, and a comment-box CTA that rebuilds the opener so the reel loops. Built: tmpl_fx `tease` (with this card's returning-map behaviour as `returns`), `badge`, `cta`, `scan`, `tint`, `check`.
