# Style card: screen on top, him in a card below, on a frosted background (Nick Saraev, @nick_saraev, reel DfUtovOvQ8U)

OB 11-04 sent it as "another one" for the templates. Watched 2026-11-04: frames at 1 fps, key frames, transcript, motion and loudness. The topic (a Claude Code website skill) is not OB's lane; the layout is the reference. The download is 360x640, so positions below are that frame x3 (good to about +-6 px at 1080x1920). Evidence: `/Volumes/T7/OB-EDITS/2026-11-04-creator-templates-study/extra-DfUtovOvQ8U/` (`sheet_1fps.jpg`, `keyframes.png`, `motion.json`, the watch folder with the transcript).

It belongs to the family OB already likes: the FDOE breakdown's Cronometer screen with him in the glow box (T02, "i love the template of the screen i sent") and Kallaway's canvas + card (T06). What it adds is the light, frosted look and a few screen moves.

## Beat sheet
**Signature moves:**
1. **Screen card on top, him in a wide rounded card below.** The proof (a page, a repo, a prompt, a phone mockup) sits in a rounded card with a thin blue glow border; he talks in his own card at the bottom; one or two caption words sit between them.
2. **The background is a blurred copy of the screen itself:** light and frosted when the page is light, dark when it's dark. Never flat black.
3. **Numbers become glass cards:** a frosted dark rounded card pops over the screenshot with the number big ("42.5k GitHub stars", "50 themes") while he says it; the caption shows the number in blue.
4. **He circles the words he's reading:** a red rounded outline lands on the exact phrase in the screenshot.
5. **Mixed-type captions:** 1-3 words, bold sans, the key word recoloured (blue) or switched to an italic serif ("vibe", "fresh eyes").
6. **Full-frame close-up only for the name and the ask** ("it's called [name]", the comment CTA).

**Pace (motion_score):** 67.7 events a minute, 14 cuts a minute (scene detector; about 19 including card swaps), median gap 0.87 s, idle 3%, live score 9.7, first move at 0.03 s, 0 flash frames.
**First 2 s:** a 2-line title at the top (dark sans line + a white italic serif line on a blue highlight), a screen card under it, him in the bottom card mid-sentence, a caption word between.
**Energy:** flat and fast: claim, name, proof stack (stars, themes, how it works), CTA.
**Audio:** dry voice, no music bed heard, -14.3 LUFS, LRA 3.0.
**Length:** 36 s of script. **The 72.6 s file holds that script twice** (the second pass is a fresh take, re-edited with small changes), so a viewer who keeps watching hears the hook again as if the reel had looped.

## Layout (1080x1920)
| Part | Value |
|---|---|
| Title | y about 250-440, centred: line 1 dark bold sans; line 2 white italic serif on a blue highlight box; pixel mascots at the sides (the topic's brand, not his) |
| Screen card (split state) | x about 120-960, y about 495-957, rounded about 12 px, thin blue glow border; content: real screenshots, a typed prompt bar, phone mockups fanning out |
| Caption (split) | y about 1000-1080, between the cards, dark text on the light background |
| His card | x 51-1041, top at y 1092, running off the bottom, radius about 40 px, no border; face centre about y 1440 |
| Screen only | the card grows to about y 252-1272, centred, on a dark blurred copy; caption about y 1400 |
| Glass stat card | about 660 x 370, frosted dark, centred over the screenshot's lower half; number about 150 px, label under it |
| Close-up | full frame, caption on his chest about y 1380-1500 |

Share of runtime per 36 s pass, by eye: split about 45%, screen only about 40% (no face), close-up about 15%.

## Mapping to OB (template T19, a variant of the screen + card family)
Use it for anything he reads off a screen: a Cronometer day, a nutrition label, a study's abstract, a news headline, an app's claim, a client's check-in (consented).
| Part | His | OB's |
|---|---|---|
| Background | blurred copy of the screen | the same (it satisfies M38, "i dont like the black background"); light when the screen is light |
| Screen card | blue glow border | thin #FFD400 or white glow border, his real screen captures only (Cronometer via its own pages, never redrawn) |
| His card | bottom card, no border | as T02's PiP box (x 9.6-90.4%, top about 59% H) or this card (x 51-1041, top y 1092), his head may pop over its top edge (T02) |
| Screen-only stretches | 40% with no face | **out** (M37: never off screen while he talks). Every stretch stays split; the screen card can grow up to y 1060 above his card instead |
| Numbers | glass card + blue caption number | a count-up number card (`canvas_card.py` `count`, or a frosted-card variant) in Big Shoulders, #FFD400 number |
| Phrase outline | red rounded box | red rounded outline on the phrase (fault) or #FFD400 (the line he's quoting), drawing on as he reads |
| Captions | 1-3 words, blue / italic serif emphasis | his locked captions or one-word brand captions, #FFD400 on the key word; no serif swap and no box behind words (brand rule) |
| Title | dark sans + serif on a blue box | Big Shoulders Black, #FFD400 on one word, no box (brand rule: no boxes) |
| Close-up | for the name and the ask | for the verdict and his closer |
| CTA | comment keyword | his locked closer; a keyword only on a comments job |

**The doubled script is an untested trick, not a default.** It may raise watch time or replays, or it may read as a repost (OB's data: the same footage reposted skips 3.6 points more). If OB wants it, run it as one trial variable against the single pass, and never on the grid first.

## Status
- **Buildable now:** the split with his card (T02's `fdoe_artzen.py` layout and `studio_bg`, `canvas_card.py`'s card), real screen captures, the count-up number, captions, the gate.
- **Needs building:** the frosted background from the screen itself (a heavy blur + light lift of the top card's own pixels), the glass number card, the phrase outline that draws on (the `annot` ellipse is the nearest piece; this is a rounded rectangle), the typed prompt or search bar, the phone-mockup fan.

**Built in the template engine (11-04, `~/ob-editor/bin/tmpl.py` + `tmpl_fx.py`):** `card` on `frosted:` (the screen's own blur), the screenshot as an image element with drawn outlines on his words, captions between. Test plan `T7/OB-EDITS/2026-11-04-creator-templates-study/tmpl-tests/plans/T19_saraev.json`: gate PASS.
