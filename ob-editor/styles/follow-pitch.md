# Style card: the 15-second follow pitch (trial format)

Source: OB's two PDFs on T7, `follow-pitch-trial-format-2026-11-02.pdf` (Jay Robb, @itsmejrob, reel DdfKwxuuFzW, ~15 s) and `follow-pitch-trial-format-specimen-2-2026-11-02.pdf` (reel De-hEPcuds7, ~20 s, n = 2 for the creator). Read in full 2026-11-04. Not re-watched: the PDFs are watched decodes and the format has almost no edit.

## What it is
One take, one shot, 15-20 s, a pitch aimed only at people who don't follow yet. The product is the account, not a tip. It asks for a profile visit, not a follow, a comment or a keyword. It loops back to the hook. Trial-native: strangers are exactly who trials reach.

## Beat sheet
**Signature moves:**
1. **Proof in the frame before any claim** (specimen 1): the picture itself demonstrates the skill. For OB: him (the physique, hat and grey shirt), his kitchen, or an audit on screen.
2. **Stranger address** as its own beat ("you probably don't follow me yet", in his words): qualifies and flatters the cold viewer.
3. **One niche, one benefit, one proof line.** No list, no life story.
4. **The ask is a profile visit,** with more coming. Specimen 2 adds an end card pointing at one proof reel (arrow + thumbnail) as an optional fifth beat.
5. **Loops:** the last word runs back into the first; 15 s watched twice is 30 s of retention.

**Cut:** none needed. OB's version still gets the zero-dead cut (every 70 ms+ pause out, never a speed-up) and his locked captions; Jay Robb's no-caption continuous take is a do-not-copy.
**First 2 s:** OB in frame mid-sentence, the proof visible (medium shot, face under 8% of the frame per PROVEN-OPENERS rule 2), 3+ words of on-screen text by 1.6 s (rule 3).
**Energy:** flat, conversational, one breath per beat.

## Script (shapes; full riff cards and 4 versions are in the PDF)
1. Hook + proof in frame: "[What the viewer is looking at] is [the outcome he sells]." (9 words or fewer)
2. Stranger address: "[If you're new here], you [probably don't follow me] yet."
3. Name + niche + benefit + ONE proof line: "I'm OB. I [niche] for [who], [benefit], because [one lived-it or record line]."
4. Profile visit + locked closer: "[If that's your thing], check my profile." + "Anyways, bs silenced, follow if you want actual logic."
Optional 5 (specimen 2, separate test): a 2 s end card, "[HOW I COUNTED THIS]" + arrow to one audit reel's thumbnail.

Versions to film in one batch (PDF): A mission, B proof, C 30-plus, D audit-tease. Only beats 1 and 3 change.

## Rule checks against OB's data (do these before filming)
- **Hook order:** OB's hook spec says never "you/your" first (skip +2.25) and start with "I", a name, a brand or a place (B41.3). Specimen 1's order (proof line first, stranger address second) fits; specimen 2's ("If you're seeing this...") opens on "you". Use specimen 1's order.
- **The number:** the PDF's draft line says "over 1,200 people coached". The vault's verified figure is "over a thousand" (memory `project_1010_feed_2026_10`). Use "over a thousand" unless OB confirms a new count.
- **No keyword, no "free", no second CTA,** no em dash on screen. Closer verbatim as the last beat.
- **Judge it as a trial only:** skip rate against a bar set before posting, then follows per reach and profile visits per reach. Never the feed median. Kill rule: 3 of 4 versions miss the skip bar = format suspect on this account.

## Layout (OB)
| Part | Value |
|---|---|
| Frame | his vertical take, medium shot, face under 8% of the frame at 0.4 s, hat + grey shirt |
| Text | a one-line label from frame 1 at y 270-420, Big Shoulders Black, #FFD400 on one word, the label is his niche in 3-5 words |
| Captions | his locked captions (3 words, live word yellow, y on the shirt) |
| End card (option 5) | the proof reel's real cover frame, 340x604 (9:16), lower right above y 1500, an #FFD400 arrow that draws on (new; the nearest existing piece is the `annot` ellipse in `explainer_cards.py`), label above it |
| Length | 15-20 s; if a draft runs long, cut beat 1, never the closer |

## Status
- **Buildable now:** everything. One take through `takes.py` (bad takes out, zero dead space, voice master), ob-clipper captions, the label from the brand layer, the gate, `deliver.py`.
- **Needs building:** only the optional end card (thumbnail + hand arrow), from `moves.py`/`cards.py` pieces on first use.

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** label + end card (image with a yellow frame, label, a curved arrow drawing on). Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T13_pitch.json`: gate PASS.
