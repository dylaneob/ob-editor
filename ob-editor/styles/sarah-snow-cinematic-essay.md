# Style card: Sarah Snow's cinematic essay (@iamsarahsnow) -> OB's reframe essay and long essay (T21)

OB 11-06: "here is another editing style to copy... really understand it", with C6efiYjs3oP (4.06M plays, 51.7 s, 14.9x her median of 273k).

Studied 2026-11-06 from 10 of her reels:
- C3BtI7RsR85 15.5x
- C6efiYjs3oP 14.9x
- DaIpUSlxu0W 8.9x (2026)
- C8QrbeMM-CL 7.5x
- DBZtLTpv91b 7.4x
- DczXHp5R4dK 6.5x (2026)
- CvIJAS_AAFD 5.4x (2023)
- C15VY8nOvJ3 3.0x
- C4MYkj_OGIK 2.9x
- C7iCzuhsGBy 2.3x

Full decode with every measurement, beat maps for the 3 biggest, the method and paths: `/Volumes/T7/OB-EDITS/2026-11-06-sarah-snow-study/DECODE.md`. Key frames are in its `frames/key/`; the font proof is `sheets/font_compare.png`. Her files are 720x1280; every number here is converted to 1080x1920.

**The difference from Kallaway / Trainbloom in one line:** they teach with designed graphics over a talking head; Sarah tells one idea as a short film. Her voice runs over real footage of her own life, she is small in a big landscape, and the only graphic is a glowing lower-case serif placed in the empty sky, with the argument's key words set large.


## OB's decisions (2026-11-06): keep all of her style for T21
OB: "I like all of her stuff keep it all for her style and if we use her style we can shoot the overlays and b roll". So for T21 only, his usual rules give way:
- **Her serif:** EB Garamond, lower case, glow, big italic emphasis. Not Big Shoulders.
- **Her music bed:** a soft, non-percussive bed 18 dB under the voice, no duck (plan `"music"`). He picks the track by ear.
- **Her voice over b-roll:** most of the runtime. He is in most shots, and talks to camera at the hook, the turn and the end.
- **Her breaths:** pauses up to 0.8 s stay (plan `"keep_pauses": 0.8`; the gate allows them).
- **Her ending:** a loop word or a dry tag in place of his locked closer.
- **Her framing:** a wide location A-roll with sky or wall above him, face about 130 to 220 px.
- **He shoots the b-roll and the inserts:** DECODE §12, and the shoot list at `T7/OB-EDITS/2026-11-06-sarah-snow-study/T21-SHOOT-LIST.md`.

Still his rules: no text on his face, real footage only (no AI), no barbell back squat or deadlift as advice, and the skip + share pass on the script (text hook, send line in the caption if not spoken).

## Beat sheet
**Signature moves:**
1. **Small person, big sky.**
   - A-roll is a wide, locked shot in a location. C6ef: face 130 px (12% of the width), centred at x 514, y 976, head top about y 850, so the top 44% of the frame is empty sky.
   - The caption lives there: 78% of C6ef's caption words are in the top third, and only 10% of frames with her face have text touching her head.
2. **One serif, lower case, glowing: EB Garamond.**
   - Body: Regular, about 74 px, line pitch about 98 px, centred.
   - Emphasis: SemiBold (upright) or Bold Italic at 1.7x to 4.5x (130 to 345 px), on its own line.
   - Colour: off-white #FCFEF7 with a soft white glow. On a bright sky the text turns dark in the shot's own shadow colour (olive #4F5847 in C6ef, teal #163F42 in DczX), with no glow.
   - The big words have rough, ink-bleed edges (her "glow and jitter"); no frame-to-frame motion was measurable.
3. **Short phrases, one a second, cleared by the cut.**
   - Blocks of 1 to 4 words (median 2), about 50 blocks in 52 s, landing about 0.2 s before the word is heard.
   - A picture cut clears the block: 12 of 17 cuts in C6ef, 35 of 38 in DczX.
   - Lines stack only in the hook (up to 9 words) and where a small lead-in sits over a big word.
4. **Emphasis is rationed to the argument.** About 1 word in 11 (C6ef: peace, if, even, okay., expectations, rules., then, break, free, falling apart.):
   - the promised outcome;
   - the contrast pivot ("if" against "even if");
   - the sentence-final payoff ("okay.", "rules.");
   - the payoff verb ("break free").
   It either hard-pops with its glow or blurs in over 0.25 s (6 frames). Her two ordinary cooking essays enlarge 23 and 30 words; the winners 12 and 13.
5. **Her voice over her life.**
   - VO over full-frame b-roll is 69% of C6ef and 100% of the 2026 reels.
   - She is in 95% of C6ef's runtime (A-roll 31% + b-roll of her 64%).
   - A-roll returns at the hook, the turn and the close.
   - The cooking essays run one meal from raw to plate under the whole monologue (hands and food only for 34 to 73% of the runtime) and pay it off as the metaphor in the last line.
6. **Calm, breathing delivery, cut in the breath.**
   - 126 to 146 wpm in the 2024 essays, 7 pauses of 0.5 s or more in C6ef's 52 s, a 1.06 s beat before the loop word.
   - Median shot 1.4 to 2.6 s.
   - Cuts fall in the voice gaps: level at the cut 2.5 to 14.5 dB under random moments.
   - No whooshes, no dissolves since 2024, no slow motion, no speed ramps.
7. **Filmic, natural grade.**
   - Lifted blacks (luma p1 16 to 27), soft whites (p99 186 to 242, almost nothing clipped), warm b* +2 to +18, saturation left near natural (0.20 to 0.44).
   - Each location keeps its own light; there is no single LUT.
8. **A soft bed and a loop.**
   - A non-percussive ambient bed sits 11 to 22 dB under the voice in the pauses (est.), not ducked.
   - C6ef ends on "Because." so the last word runs into the first line. The cooking essays end on one dry food joke instead. No spoken ask in any essay.

**Pace:**
- Essays: 17 to 28 cuts a minute (2026 up to 34.8).
- Tips reels: 13 to 15 cuts a minute (desk talking head).
- Caption blocks: about one a second.
- Slow digital push on the talking shots: C6ef hook 5.7%/s (13% over 2.4 s), later 1.5 to 3.5%/s; the last A-roll is static.

**First 2 s:**
- She is on frame 0 in all 10 reels, and text is up by 0.75 s in all 10 (frame 0 when measured at full rate).
- The first sentence is the whole thesis as a reframe ("true [outcome] comes when you switch from [A] to [B]", "your problem isn't [flattering self-image]...").
- Her two ordinary reels open with a softener ("this might be an unpopular opinion"); none of the winners does.

**Energy curve:** a quiet open (wide, push-in, the hook stack) -> rhythm (three examples on one sentence frame) -> the turn back to camera -> a short cost beat with literal pictures -> the payoff word big -> a breath -> loop or tag.

**Audio:**
- Close, dry voice (est. lav or re-recorded on the location shots).
- Ambient bed throughout, no SFX.
- 2024 hits mastered quiet (-24.0 and -22.6 LUFS); late 2024 and 2026 at -14.2.

**Captions:** on 89 to 98% of frames, lower case, punctuation kept, never boxed.

## States (share of runtime)
| State | What | Share |
|---|---|---|
| A | her talking to the lens in a location, wide, slow push | C6ef 31%; cooking essays 15 to 39%; 2026: 0% |
| B | b-roll with her in it, her voice over | C6ef 64%; 2026 71%; cooking essays 10 to 27% |
| I | insert: hands, food, objects, landscape, voice over | C6ef 5%; cooking essays 34 to 73%; 2026 29% |
| D (tips only) | desk talking head + overhead paper-craft inserts | C8Qr 42% + 52%; DBZt 63% + 17% |
| Text | serif caption on screen | 89 to 98% of frames |

## Mapping to OB (template T21)
Two shapes, both from her winners:
- **A. Reframe essay** (her C6ef, 14.9x), 60-89 s for OB. Thesis as a from/to reframe -> the pivot pair big -> three examples on one sentence frame -> "but we..." turn on camera -> the cost twice -> payoff verb big -> loop word or his closer.
- **B. Long essay** (her C3Bt 15.5x, DaIp 8.9x), 90-119 s. Name the viewer's self-image and flip it, or a confession with one charged word -> his history over one continuous process (a full meal prep) -> "it was a choice" -> reframe x3 -> diagnosis -> permission -> thesis restated as a pair -> dry tag or the photo callback.

Script beats: vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §T21 (text ready at the end of the DECODE; not pasted yet).

| Part | Hers | OB's template |
|---|---|---|
| A-roll | wide in a location, face 130 to 342 px, slow push 1.5 to 5.7%/s | `full` from his location take (or his studio take; OB's call), push 1.00 to 1.13 over the hook shot, 1.5 to 3%/s later, last A-roll static |
| B-roll | her life (field, road, lake, kitchen, friends, baby), mostly her in shot | his life, **him in most shots** (shot list in DECODE §12): an empty road, the gym at 6 am, meal prep from raw to containers, the food scale, the grocery aisle, the car, the scale and tape, a profile at a window |
| Inserts | hands and food, one continuous process | his meal prep as the long-form metaphor; literal inserts for concrete nouns (the scale reading, the label, the step count) |
| Captions | EB Garamond, lower case, glow, sized concept words in the empty sky | either Big Shoulders in his brand treatment or the serif for this template (OB's call). Either way: placed per shot in negative space, never on his face, 1 to 4 words, about 1 in 11 words big |
| Grade | lifted blacks, soft whites, location light, warm | `make_grade.py` per location to the target numbers in the build list |
| Audio | voice + ambient bed 11 to 22 dB under, no duck, no SFX | `voice_master` at -14 LUFS; bed only if OB allows (feed rule: no music) |
| Close | loop word or dry tag, no ask | his locked closer, or the loop (not both; OB's call) |
| Length | 52 s and 187 s winners | 60-89 s (A) or 90-119 s (B) |

## Status
- **Buildable now:**
  - his A-roll as `full` with a hald LUT (`make_grade.py` takes lift, contrast, sat, warmth and a soft highlight roll-off);
  - a music bed under the voice (`music_mix.py`, `--rel`, `--duck 0`);
  - caption groups that reset at every cut (engine rule);
  - the person matte for text behind his head (`person_mask_dir`);
  - the face check (`face_clear.py`);
  - the QC gate.
- **Needs building:**
  - the serif caption element (B1);
  - a full-frame `broll` look that keeps his voice running (B2);
  - a negative-space placer (B3);
  - a slow linear push-in on `full` (B4; `full` has only the zoom-out on a cut);
  - the loop-end option (B6);
  - the ragged hook stack (inside B1);
  - the gate checks (B8).
- **Not ported:**
  - the 2026 centred line across the face;
  - 2023's cross-dissolves;
  - hands-only cooking runs while he talks (they break his on-screen rule);
  - her sentences (shapes only).

## BUILD LIST (for `tmpl.py` / `tmpl_fx.py`)
Values are at 1080x1920. "(est.)" means inferred, not measured exactly.

**B1. `serif` caption element**
- **Font:** EB Garamond, variable woff2 already on the machine at `~/.cache/hyperframes/fonts/eb-garamond/` (upright `400-normal-*.woff2`, italic `400-italic-*.woff2`; set weight with `set_variation_by_axes([wght])`). SIL OFL.
- **Body:** weight 400 (450 est.), **74 px**, line pitch **98 px** (1.32 em), lower case, punctuation kept, curly apostrophes, centred lines, max line width 760 px (70%).
- **Emphasis:** its own line; upright **600** or italic **700**; size **1.7x to 4.5x** body (130 to 345 px); about **1 per 9 to 11 words**, never more than 1 per phrase. Picked from the plan by a mark on the word ("emph": true): the outcome, the pivot pair, the sentence-final payoff, the payoff verb, the list number.
- **Inline italic:** body size, italic 400, for softer stress and for quoted speech.
- **Colour rule:** sample the background luma under the text box (dilated 30 px).
  - Under about 185: off-white **#FCFEF7** with the glow.
  - About 185 or more: dark text in the shot's shadow hue (median of the shot's darkest 10% of pixels, lifted to luma about 85: e.g. #4F5847 olive, #163F42 teal), **no glow**.
- **Glow (white text, est. from the measured fall-off):**
  - two white Gaussian layers under the text: sigma 6 px at 55% and sigma 14 px at 30% opacity;
  - target: about +30% of the text-to-background contrast at 4.5 px from the stroke and +7% at 18 px; big words 1.3x stronger;
  - CSS equivalent: `text-shadow: 0 0 6px rgba(255,255,255,.55), 0 0 14px rgba(255,255,255,.30)`.
- **Rough edge** ("jitter", emphasis words only, est.): a static displacement of the glyph outline, amplitude about 1.5 px, noise scale about 6 px. No per-frame motion.
- **Reveal modes** (per template preset):
  - `pop` (C6ef, default): a 1 to 4 word phrase appears whole, hard, at its first word minus 0.20 s.
  - `fadeword` (C3Bt, C4MY): each word fades in over 0.25 s, starting 0.20 s before it is said.
  - `type` (C15V): letter by letter at about 28 characters a second (est.), so the word completes as it is said.
- **Emphasis entry:** `pop` (with its glow) or `blurin`: 0.25 s (6 frames at 24 fps), Gaussian blur 12 to 0 px and opacity 0 to 1, no scale.
- **Hold:** static. Text does not move with the footage push.
- **Exit:** hard off at the picture cut or when the next block replaces it; optional `blurout` 0.2 s.
- **Blocks:**
  - from the plan's phrase splits, 1 to 4 words, about one a second;
  - stack (new line under the last) only in the hook and for "lead-in + emphasis";
  - 9 words on screen at most, median 2;
  - frame 0 always has text.
- **Ragged hook stack** (C6ef 2.4 to 6.3 s): 3 lines with left offsets of 0, +140 and +50 px from the first line's start, instead of centring.

**B2. `broll` look**
- Full-frame clip, his voice continues, no PiP.
- Each b-roll shot starts on the first word of its phrase, cut in the breath between phrases.
- Median shot 2.3 to 2.6 s (range 1.1 to 7.1 s), real time, no transitions.
- The plan tags each shot `her_equiv`: literal, metaphor or mood. C6ef's mix is 3 / 5 / 7; save literal shots for concrete nouns.
- **Gate:** flag any b-roll stretch with no OB face (rule conflict, see below).

**B3. Negative-space placer**
- Per shot, pick the caption band as the 3-line-tall horizontal band with the lowest edge density that is at least 60 px from the face box (from `faces` on 2 fps frames, widest over the shot) and inside y 220 to 1500.
- C6ef's bands: y 250 to 750 (word centres 284 to 705).
- Prefer the top third when the sky or wall is empty.

**B4. Slow push on `full`**
- `"push": [start_scale, end_scale]`, linear.
- Hook A-roll 1.00 to 1.13 over about 2.4 s (5.7%/s); later A-roll 1.5 to 3%/s; last shot static.
- The text does not scale with it.

**B5. Grade**
- `make_grade.py` per location to these targets: luma p1 16 to 27, p99 about 215 to 225, clipped under 0.5%, saturation natural (x0.95 to 1.0), warm highlights b* +6 to +12.
- Outdoor overcast can sit olive (a* about -4, as C6ef); indoor golden light warm (a* +5 to +9, b* +12 to +18).
- No grain needed (none measurable in hers).

**B6. Loop end (option)**
- The last line ends on a bridge word that reads into line 1 (C6ef "Because." after a 1.06 s beat). `"tail": 0`, and the first frame matches the A-roll framing so the loop is seamless.
- Exclusive with his locked closer.

**B7. Music bed (only if OB allows)**
- `music_mix.py`: non-percussive ambient piano or pad, trimmed to the reel length, `--rel -18` (her pause floor sits 11 to 22 dB under the voice), `--duck 0` (no ducking measured), master -14 LUFS.
- Optional: the bed drops out on the hook's last word (her stated rule in DBZt, not confirmed in the files).

**B8. Gate checks for T21**
- caption box never touches the face box (`face_clear.py`, 0 frames);
- emphasis 1 word in 9 or fewer;
- every cut clears or keeps the block (no orphan words);
- frame 0 has text;
- no full-frame b-roll over his speech without his face (warn until OB rules on it).

## OB conflicts (resolved 11-06: see "OB's decisions" above)
1. **Face on every frame while he talks** (OB 10-30: b-roll never full screen over his speech). Her style is 69 to 100% voiceover over b-roll. Does b-roll of him (face visible, not talking) count? Hands-only cooking runs (34 to 73% of her cooking essays) break the rule either way.
2. **Brand font.** Big Shoulders, upper case, #FFD400, no boxes, against her EB Garamond, lower case, glow, emphasis by size and italic. **OB's call:** keep his brand font for T21, or allow the serif for this one template. No boxes either way.
3. **No text on his face.** C6ef is compatible (10% head overlap, fixable per shot). The 2026 centred line across her face is not.
4. **Zero dead space.** Her 0.5 to 1 s pauses and 126 to 146 wpm are part of the calm. His short-form rule cuts every 70 ms+ pause. Keep his rule (faster, less cinematic), or allow designed pauses for T21.
5. **No music on feed posts.** **The style depends on a soft bed** (constant, 11 to 22 dB under the voice). Feed: voice only + in-app sound per his rule, or an exception; trials can test it as one variable.
6. **Locked closer vs her loop or tag ending.** Only one can be last.
7. **Framing.** A wide location A-roll puts his face at about 130 to 220 px against his usual 330 to 400 px (60 to 67% smaller). The alternative is his studio A-roll with location b-roll.
8. **No AI imagery.** No conflict: she uses only real footage. It needs a b-roll shoot day (DECODE §12 shot list, 15 shot types).
9. **Length.** Her C6ef (52 s) is under his 60-89 s myth band: add one example beat. The long essay maps to his 90-119 s lessons (her own 120 s+ reels have her best median, 576k, but his data says avoid 120 s+).
