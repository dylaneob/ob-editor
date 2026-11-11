# Style card: Megann's numbered plan (@fitnessbymegann), the 10/10 list with ONE item device

Index card, written 2026-11-04 for the template catalog. **The measured spec already exists; don't re-measure:**
- Edit spec, 9 reels measured frame by frame (10-25): `/Volumes/T7/OB-EDITS/2026-10-24-tenten/ref-study/megann/MEGANN-EDIT-SPEC.md` (sheets, boxes, per-reel stats beside it).
- Script anatomy: vault `30-Competitors/_MEGANN-SCRIPT-ANATOMY-2026-10-24.md`; OB's 10-24 scripting corrections: vault `40-Scripts/_10-10-SCRIPTING-RULES-2026-10-24.md`; memory `feedback_megann_structure_first`.
- Cross-creator study (Kyle + Megann + Kamila + Calleigh): vault `90-References/muse-notes/numbered-plan-reel-kyle-megann-2026-10-28.notes.md`.
- Built once as look `MX` in `T7/OB-EDITS/2026-10-24-tenten/_work/tenten3_c4376_edit.py` (`mx_layers`, `mx_laptop`, `mx_slide`), from her #1 reel DevKKzOR2dc.

## What OB has said about it
- 10-24: "her structure is most important though to follow because clearly its working", "she is the gold standard".
- 10-24 HARD LINE, twice: copy the FORMAT, the hook STRUCTURE and the editing, never her words.
- 10-28 23:20: "just do the megan version", "legit copy the exact frame as her for that one" (gut only).
- 10-29: the MX gut was set aside for his own trial winner (look 4X4): "based on my 3 top versions, upgrade them". Lesson (memory `feedback_feed_winner_upgrade_only`): a reference copy he asks for is for that one video only, and a feed version is the trial winner's look.

## Beat sheet
**Signature moves (from the spec):**
1. **One item device for the whole list,** on screen 71-95% of the runtime in her winners: a laptop slide on her lap (#1 reel), a pyramid that fills a layer per item, a typed card then a 3-photo strip, a "1/4" counter plus plan pages, or a running label plus a sticky note held to the lens. Her losers had a tiny label or 15-19 s blank gaps.
2. **The device changes on the spoken number word** (-100 to 0 ms) and, on the #1 reel, on a jump cut (11 of 12 swaps). The cut is the transition.
3. **One word of caption at a time,** light white serif, centred y 70-75%, key nouns and numbers tinted pale lime and 1.2-1.5x bigger on 11-16% of words (winners only).
4. **Jump cuts 11-18 a minute** (median shot 2.5-4.2 s), about half punched in ~10%; every pause cut to 0.42 s or less; 230-240 wpm; first word by 0.16 s.
5. **Images hard-cut in and out; text types on** (cards 0.4-0.7 s, labels 0.4-1.0 s). No SFX on overlays.

**First 2 s:** talking at 0.0 s; title at y 14-17% (2.9-4.8 s), white serif or bold sans + lime pill; a hook visual by 1.3-2 s (3-photo strip y 13-28%, or one body photo inset 40-46% lower left).
**Energy curve:** flat and fast; the flagged item ("the one that...") gets the longest hold (16.9 s vs a 9.85 s median).
**Audio:** -14.1 LUFS, LRA 1.4-4.8, soft piano/pad bed 21-27 dB under, no beat.
**Close:** keyword line typed on within 0.2 s of the word, then a profile chip for the last 0.7-2 s.

## Script structure (shapes only; her beat order, OB's words)
Promise (number + concrete body outcome at 0:00) -> an everyday picture of the outcome for both sexes -> credential + scale in one breath -> SAVE or reverse-save instruction -> tease on one numbered item -> [optional mid re-hook or disqualifier] -> 10 items, each: command, sourced number, one line of why, a sting naming the viewer's mistake -> #10 = the never-miss-twice close -> CTA.
- Trend frame verbatim when OB says copy her: spoken "10 out of 10 habits to [outcome]", title "10/10 HABITS TO [OUTCOME] (lowercase parenthetical)", slides 1/10 to 10/10.
- Item #1 is the most controversial or never-heard fact (OB 10-24 HARD RULE). Never attack 1,200 calories.
- Before delivering, grep the script for her distinctive phrases (list in `feedback_megann_structure_first`) and rewrite any hit in OB's words.
- Script bank entry: vault `40-Scripts/_SCRIPT-STRUCTURES-CREATOR-TEMPLATES-2026-11-04.md` §Megann.

## Mapping to OB (the template)
| Part | Her | OB's template |
|---|---|---|
| Framing | seated, face 21-33% W, face top 28-35% H | his vertical take, face top about 30% H so y 10-32% stays clear above the head (fits the device band) |
| Title | white serif, y 14-17% | Big Shoulders Black, white, y 14-17% (top edge clear of IG's 220 px bar: start at y 270), #FFD400 on the one word. Serif only in "exact copy" mode when he asks |
| Item device | one of five | default **the laptop slide** (her #1; built as MX); options below |
| Captions | 1 word, white serif, lime emphasis | 1 word, Big Shoulders ExtraBold, #FFD400 + 1.3x on 10-15% of words (the rule's nouns and numbers), y 70-75% on his chest, never on his face |
| Music | piano/pad 21-27 dB under | feed posts: none (OB 10-29, he adds sound in app); trials: Lane A bed 21-27 dB under |
| Close | keyword pill + profile chip | his locked closer, then the profile chip (no asset keyword unless he asks) |

## Upgrades (new 11-04, each a trial variable, one at a time)
1. **A real prop instead of a drawn laptop.** MX drew a silver MacBook. Upgrade: his own laptop or iPad on his lap, filmed, with the screen replaced per item (screen corners tracked; `tv_patch.py`'s tracking method), or Adam Becker's **handwritten notebook** from the 11-02 4x4 study (his handwriting, camera lingers until each number reads). A physical object reads as his plan, not a template.
2. **The pyramid as a framework canvas.** Her building graphic is the same idea as Kallaway's returning diagram (`framework-canvas.md`, `canvas_card.py`): one diagram above his head, a layer fills and its label lands on the item word. Reuse `canvas_card.py`'s spring and `rows` element.
3. **Typewriter cards in brand.** Her typed card (0.4-0.7 s) becomes a Big Shoulders line typing on at y 19-23%, then a 3-photo strip (real photos only, M28), hard cut.
4. **Box-flash captions as a tested alternative** to her one-word serif: `box_flash.py --layout stack` (Artzen). One variable per trial.
5. **The flagged item gets a held proof.** Her longest hold is the teased item; OB's version holds a real receipt there (a client, his Cronometer, a study screenshot with the source).

## Status
- **Buildable now:** look MX (laptop slide, title, 3-photo strip, one-word lime/yellow captions, profile chip) in `tenten3_c4376_edit.py`; zero-dead cut, voice master, gate.
- **Needs building:** MX is wired to the 10/10 project (fixed paths, gut/hormones/micros plans). A plan-driven version (`numbered_plan.py PLAN.json`: device, items, number-word times) is the generalisation. Also the pyramid device (via `canvas_card.py`), the typewriter card, the counter + plan pages, the sticky-note label, and screen replacement on a real laptop.

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** tmpl_fx `slide` (a drawn screen whose slide hard-swaps on each spoken number) over any tmpl look; the measured MX look stays in the 10/10 engine.
