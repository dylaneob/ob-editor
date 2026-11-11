# Style card: numbered steps with proof cutaways (Mekhi Carter handoff)

Source: OB's PDF on T7, `mekhi-carter-editing-handoff-for-claude-2026-11-02.pdf` (@themekhicarter, reel DczQnxhhLk9, about 2:55, a phone-content tutorial framed as a series episode). Read in full 2026-11-04. It is an editor handoff, not a creator study: settings and cut rules to apply to OB's talking videos. It is NOT a 2x2.

## Beat sheet
**Signature moves:**
1. **Numbered step headers with a short checklist** at the top centre (pale yellow / cream bold, checklist under it). Each new header is a mini re-hook: the viewer always knows which step they are on.
2. **A cut between every sentence,** often every few words; no breath left.
3. **Proof cutaways, never b-roll:** every cutaway is a screen recording or close-up of the exact thing he is explaining (the settings screen, the slider values, the mic in hand). If it doesn't show the thing, it's cut.
4. **Word-pop captions:** large bold white sans, one or a few words, lower third, dark shadow; emphasis words pop bigger.
5. **Loop-back ending:** the close runs straight into the opening hook on replay.

**Transitions:** hard jump cuts, punch-ins and small scale-ups as he leans in; hard cuts into and out of screen recordings. No whips or match cuts.
**Graphics:** minimal: captions, step headers, a hand-drawn white scribble circle/underline on the opening title, the screens themselves.
**Sound:** clean close-mic voice, no music or SFX that stand out.
**Look:** bright, warm, punchy: CapCut Adjust contrast +1/+2, saturation +1/+2, sharpness 23-24.

## Collisions with OB's rules (decided here, not in the edit)
- **The 1.2x speed-up is out.** OB 10-27: "no i didnt want a literaly speed up, i meant with cuts". The pace comes from `zero_dead.cut_words` (every 70 ms+ pause out, never a tempo change). Same feel, no chipmunk.
- **The Adjust recipe is a grade option, not the default.** His grade is picked from 3-4 options on his real frames (warm tan default; grade A rejected as "albino"). Offer "punchy" (contrast +, saturation +, light sharpen) as one of the options when this template is used. Never lift highlights on his face.
- **Length:** don't port 3 minutes. Teaching reels convert at 90-119 s (B30.1); over 120 s runs follows 0.84x.
- **Locked assets stay:** black hat + grey shirt, his locked closer verbatim as the last beat, one CTA.

## Mapping to OB (the template)
Use it wherever a video teaches steps: how to count a meal, how to read a label, a recipe, a debunk with a list, an audit's method.
| Part | OB's template |
|---|---|
| Step header | "STEP 2: WEIGH IT RAW" style, Big Shoulders Black, white with #FFD400 on the step number, top centre at y 270-380 (under IG's bar), lands on the word "two" with a spring (`cards.py` POP), stays for the whole step |
| Checklist | 2-3 short lines under the header (Big Shoulders ExtraBold, 50-60 px), each line ticks on (#FFD400 check) as he says it |
| Proof cutaways | his own screen recordings (Cronometer, a label close-up, the scale reading), full frame or in the top half with him below (`dylan-page-split.md` seam); held long enough to read every number |
| Captions | his locked captions, or one-word pops with emphasis words 1.3x and #FFD400 |
| Title accent | the scribble circle/underline: `explainer_cards.py` `annot` (an ellipse that draws on as he says it; `"hand": true` adds a handwritten label that writes on), restyled white or #FFD400 |
| Open | the result first (the finished meal, the counted total), then step 1 (motion library §E how-to rule, same idea) |
| End | the last step's result loops into the opening shot |

## Status
- **Buildable now:** zero-dead cut, captions, step headers and checklist ticks (`cards.py` springs / HyperFrames), the drawn circle (`explainer_cards.py` `annot`), proof screens as video layers, the grade options (`make_grade.py`).
- **Needs building:** a reusable "step header + checklist" card type in `cards.py` (today it would be hand-built in HyperFrames per edit), and a screen-recording intake (iPhone screen recordings of Cronometer cropped and scaled to the panel).

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** tmpl_fx `step` (header + checklist ticking on words) over `cut` or `full`. Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T14_steps.json`: gate PASS.
