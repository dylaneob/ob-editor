# Style card: split + punch word + face bubble (OB's horizontal takes)

> **OB 10-30 ~22:35: the split itself now follows `dylan-page-split.md`** ("really really study this because this is what I meant for a the split screen style when I shoot horizontal", https://www.instagram.com/reel/DfIndnRoz80/).
> - receipts from the story on top, never stock; seam y 876;
> - him full frame on the turns;
> - her clip full frame with its own sound.
>
> The punch word, chest infographics and framework canvas below are extras for when he asks for them, not the default.

OB 10-28: "The videos I shot horizontally I want you to edit like this" with two reels from one tech-explainer creator (black cap, dark room):
- https://www.instagram.com/reel/DeZPNanOD0W/ (78 s, AI satellites)
- https://www.instagram.com/reel/Db-0516OBQM/ (about 70 s, a suite of health bots)

Decoded 10-28 from 40 + 35 frames and both transcripts (study copies in the session scratchpad only). It builds on `dylan-page-split.md` (same seam, same footage-on-top rule, same caption placement) and adds the two looks that card doesn't have.

## Three looks, switched every 1.5-3 s
1. **Split** (most of the runtime): moving footage in the top half, him chest-up in the bottom half, 1-3 caption words on the seam. The top never sits still: slow pushes and pans on photos, screen recordings scrolling, app windows tilted in 3D on a gradient, satellite map tiles. It changes every 1-2 s while he stays put below.
2. **Full him + one big word** on the turns of the script ("But", "And", "Now", "If", "that", "easiest"): a punch-in to his face and chest, full frame, one giant word on his chest, never on his face. Emphasis words are sometimes a serif italic ("Individual").
3. **Full footage + face bubble**: when the picture needs the whole frame (a vertical clip, a big map, a reveal). His talking head sits in a circle top left, and a small caption pill (white text, dark rounded box) sits mid-frame.

Opening: the split with the strongest picture on top and a headline block on the seam ("THE FUTURE OF AI SATELLITES", heavy red and white letters), or the split with the product on top and his first words.

## Measured (reference frames 768x1366, scaled to 1080x1920)
| What | Value |
|---|---|
| Seam | about half the height (same as dylan-page-split: y 960) |
| Face bubble | a circle about 26% of the width (about 280 px), left edge about 70 px. The reference puts it near the very top; OB's goes just under Instagram's top bar (top at about y 240). No border. |
| Punch word | about 150 px tall, white heavy sans with a soft shadow, centred around 0.6 of the height (his chest) |
| Seam caption | small (about 55 px), white bold with a shadow, 1-3 words; OB keeps his locked captions instead (3 words, live word yellow, centred at y 930) |
| Pill caption | about 55 px white text on a dark rounded box, mid-frame, on full-frame footage |
| Pace | a new picture on top every 1-2 s; a look change every 1.5-3 s |

## How it maps to OB
- **Which takes:** the ones shot horizontally. In the 10-28 backlog that's C4383 (1,200 calories), C4396 (Fun Food Friday reaction) and C4397 ("morbidly obese, blamed everyone" reaction). C4361, C4362, C4364, C4371 and C4380 were shot vertically and keep their own looks.
- **Reactions shot horizontally** use this instead of the three C4379 looks. Her clip is a vertical reel, so it plays full frame with his face bubble while she talks (look 3), and goes into the top half, cropped to her and the food, while he talks over it (look 1).
- **Talking heads** (C4383): the top half carries what he names (the food, the study, a chart that draws, a photo with its source logged), from the stack we have (`cards.py`, `explainer_cards.py`, real photos). The motion library §G effects are optional seasoning here.
- **The bubble is a picture-in-picture.** OB asked for this look by name, so it's allowed in this format only; elsewhere the old no-PiP rule stands.
- Zero dead space, word-safe cuts and the QC gate as always. No text on his face (the big word sits on his chest, the bubble's caption is the pill). Real footage and photos only.
- Built from what exists: the split from `ytclip_pic.py`, cutouts and mattes from `person_mask_dir`, springs from `cards.py`. A new piece goes to OB as a shot list first.

## Variant B: chest infographics (OB 10-28: "I love this style as well")
https://www.instagram.com/reel/Dek-vvcgy61/ (sanji.chien, 51 s; about how a big channel's videos get made). Same family: screens in the top half with him at the desk below, and full-frame him for the turns. What it adds:
1. **Chest infographics on full-frame him** (never on his face):
   - **Icon grid:** person icons build up row by row (a team of 50), then a share turns red with a red label bar ("3D ANIMATORS": 30 of the 50). For OB this is any real "X of Y" number with a source (clients, a study's people).
   - **Logo link:** two app icons with their names drop onto his chest, a line draws between them and a green check pops ("Claude, connected to Higgsfield"). For OB: two real things linking up (Cronometer and his coaching app, for example), never a brand mark he can't use.
   - **Big phrase:** a giant white "SUPER EASY" or "IT'S" across his chest, the same as the punch word.
2. **Screens that do something:** stats on a screenshot count up to the real number (`moves.py counter` / the COUNT spring), and red label stamps ("1 CHAT", "1 PROMPT") land on the screen as he says them.
3. **Two framings from one take:** a wide desk shot (the 4K frame cropped to 9:16 at full height, mic and desk in view) and a tight close-up, cut on the turns.
4. **Pace (`motion_score.py`):** 65.8 events a minute, a cut every 4 s, a live score of 8.7/10 with 14% idle, the first move at 0.03 s.

Variant A (the bubble) and B mix freely in one edit. B has no face bubble: full-screen shots just play without him.

## Variant C: framework canvas (OB 10-28: "love this format as well")
https://www.instagram.com/reel/Derji4txGJD/ (Kallaway, 112 s). One numbered framework diagram returns at each step and unblurs its next label. It sits on a black dot-grid canvas, he sits in a wide rounded desk card below, and close-ups take 41% of the runtime. Full card: `framework-canvas.md`. Use it when a horizontal desk take names a model (C4383: calories / macros / micros).

## OB notes (10-29)
- "Caption hers": when her clip plays full frame with his face in the bubble, her words are captioned like his (3 words, live word yellow, just under her chin). Her beat text from the plan is aligned to her clip's ASR words.
- "Make me a little bigger in the circle": his face crop in the bubble is zoomed 2.1 (was 1.6), head and shoulders. The engine constant is `brand_react_render.BUBBLE_ZOOM`.

## OB 10-30: the top half is relevant footage (ledger M40). SUPERSEDED 10-30 ~22:35 by `dylan-page-split.md`: receipts per claim (median 3.5 s), no stock
The text below is kept for the record only.
"on the horzontal ones you were suppose to have relevant split screen", "not just through the orginal reaction above me", "you were
suppose to find relevant things like you do for youtube". Every split line gets its own shots on top, cut on his cue words every
1.5-3 s: her clip's matching moment when he talks about her or her food, his own b-roll, else stock (Pexels index:
`stock_pexels.py sheet TERM`, `get ID`). brand_react_render plan: `lines.Lxx.top = [{src, in, at, nth, y}]`. Look at a still of each
shot first: stock with readable off-topic text (a news headline) gets swapped.
