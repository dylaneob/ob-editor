# Style card: T26 split-hook explainer (Drew Canole, @drewcanole)

**Why it's here.** OB, 11-07: "this is very similar to Dylan Paige but he is in my niche so it's better and he uses better graphics and animations it seems, we can copy again, make sure to really understand".
- **Measurement:** 30 reels, 28 in his own style.
  - Tracked at 10 fps, with every native frame at transitions.
  - Word times by whisper, on-screen text read at 1 fps, sound measured.
- **Full decode:** `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/drew/DECODE-V2.md`. Per-reel numbers are in `data/per_reel.csv` and the grids in `grids/`; start with `openings_all30_at1.0s.jpg`.
- **It replaces** the July decode (`30-Competitors/_DREW-CANOLE-GRAPHICS-PRODUCTION-DECODE-2026-07-05.md`), which missed the split hook, the leaks, the drift, the boards, the music bed and the AI imagery.

## ENGINE FIXES 11-07 (gap audit `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/TEMPLATE-GAPS-11-07.md`)
- **Riser:** `sfx` takes `"start"` now; the riser is his last 0.8 s swell (`"start": 0.9, "len": 0.8, "delay": -0.8`), ending on the cut.
- **Leak:** `lead` 0.10.
- **Box captions:** solid, in the banner red [232, 20, 27].
- **Closing pull:** -5%/s.
- **Count-ups:** `"mode": "linear"` runs big numbers evenly over 2.0 s with no pop (start ~1 s before the word with `"lead": 1.0`); percents keep the ease-out.
- **B-roll** keeps playing across pause cuts (`bcard`, the split's top half).
- **Still open:** his half framed at ~0.7x, the top-half split variant, and his ghost-then-sharp board build.

## BULK PASS 11-07 (59 reels, Mar 24 to Nov 6; library of 27 moves / 152 clips): these figures replace the counts below where they differ
Decode `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/drew/DECODE-V3.md` (animation spec v3 in section 6). Clips `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/drew/reference/REFERENCE.md`.
- **Held across all 59:**
  - The split + 2-line banner opens every reel and lasts the first sentence (~4.5 s).
  - The exit lands 0.08-0.11 s before sentence 2. His half never cuts, and there are no captions in the split.
  - Box-karaoke captions at y ~1075 (51/59).
  - Drift with no snap; -14.3 LUFS; ~195 wpm.
  - Black b-roll cards (26/59), the follow pill (48/59), AI-looking images in ~1 in 4 (14/59).
- **Eras:**
  - He sat in the TOP half Mar-Jul (26/26). The **bottom half is the default since Aug 4** (17/23 Sep-Nov).
  - The exit is a warm leak in Sep-Nov; a white flash of 8-14 frames was common Mar-Aug.
  - Boards were coloured gradients Mar-May, then cream paper with serif numbers from mid-June. Receipt quarter-circle corners only appear Sep-Oct.
  - Older habits that faded: count-ups, icon rows, a big kinetic word on the chest, a CAPS threat word in the banner, a 0.4 s blur dip.
- **Banner colours:** red #F81010 / #E00000 / #B00800 (37/59); amber #F8B000 with near-black text (11/59); green or blue rarely. One CAPS threat word is allowed.
- **Drift:** push +2.0-2.4%/s (25%), hold (42%), pull -1.6%/s (33%), and pull -5%/s on the CTA line.
- **Count-ups:** big numbers run linear over 2.0 s; percents ease out over 0.7-1.1 s; both land ~1 s after the spoken number.
- **List hooks are allowed** but rare: one list reel was a top at 11.1x. Open on a claim, not "5 things".
- **Receipts still separate his tops** (16 of 25 tops vs 10 of 34 others), less sharply than 10 of 11.
- **He re-uploads his winners as re-edits** (13 of 48 in the Aug-Nov window look like re-uploads, 3 confirmed). Same voice, his half flipped, the banner recoloured, the b-roll swapped. The re-cuts got fewer plays than the originals (with less time live). This is a recipe for OB's own winners.

## His grammar (counts out of 28)
1. **The split is ONLY the hook (28/28):**
   - It lasts the first spoken sentence: median 4.6 s, range 2.8-7.4.
   - Seam at y 960, 50/50, in 19 reels. B-roll is on top; he's usually in the bottom half.
   - His half never cuts and pushes in ~2%/s, framed wider than his full-frame shot (face ~0.74x).
   - The other half cuts every ~1.0-1.6 s.
   - No captions during the split.
2. **The hook banner (28/28):**
   - A 2-line title-case headline, each line in its own rounded box (radius 14, ~48 px geometric bold), centred on the seam.
   - Red #E8141B with white text in 19; amber #F4B207 in 4.
   - It says something different from the spoken hook. The common shapes are "The Secret Behind Why..." and "...Here's Why/How".
3. **The hook exit (21/28):**
   - A light leak or white flash over 9 frames, brightest on the cut, which lands ~0.1 s before sentence 2.
   - A riser ends on the cut (22/28).
4. **The body alternates full-frame states,** changing every ~4 s:
   - him 45%, b-roll 25%, boards and full-screen receipt pages 15%, black pages with a rounded b-roll card 2% (9% in his top reels);
   - 82% plain cuts, ~4 leaks per reel.
5. **His shots drift; they don't snap.** The scale on a cut is 1.00. Within a shot: push +2.4%/s (29-40%), hold (35-41%), pull -1.6%/s (25-30%). Dylan Page's 1.22x zoom-out appears on ~3% of cuts.
6. **Captions (22/28): box karaoke.**
   - The whole ~3-word page sits in one solid box: centre (540, 1074), height 95, ~56 px geometric bold.
   - Spoken words are full contrast, upcoming words ~45%.
   - The box colour is fixed per reel. Mostly off on boards.
7. **Receipts (15/28; 10 of his 11 top reels):**
   - A full-frame study page with a highlighter sweeping left to right, or a card on his chest.
   - The card's entrance: fade-up over 0.40 s easing out, rising 70 px, blur 8 to 0.
8. **Boards:**
   - Light paper #F8F8F8 or cream #F2EBE3.
   - Build one element per 1.0-1.2 s, timed to the word.
   - Count-ups run linear over 2 s.
9. **Other graphics:**
   - The black inset b-roll card (905x1020, radius 54, soft glow).
   - Chest overlays: photo cards, "#N" labels that wipe in over 0.2 s, icon rows.
   - Graphics land 0.4 s before to 0.2 s after their word.
10. **End:** a follow pill with an animated cursor tap in the last 2.5 s (24/28).
11. **Sound:** -14.2 to -14.6 LUFS, a music bed ~11 dB under the voice, no SFX on cuts, a riser into the hook exit.
12. **AI-looking images in 7/28.** OB swaps these for real footage (no AI imagery on IG).
13. **Tops vs the rest:**
    - Receipts in 10 of 11 tops vs 5 of 17.
    - No numbered-list hooks in the tops (0 of 11) vs 6 of 17.
    - More board time (19% vs 12%) and more black b-roll cards (9% vs 0%).
    - More push-ins (39% vs 23%).
    - A news-style opening line naming an authority.

## Drew vs Dylan Page (T04)
| | Dylan Page T04 | Drew T26 |
|---|---|---|
| Split | 38-85% of the reel, seam 876, him always below | Hook sentence only, seam 960, him in either half (usually below) |
| Label | Short white label with emoji | 2-line coloured headline banner on the seam |
| Cut into his shot | 1.22x zoom-out snap | Slow drift (push, hold or pull), no snap |
| Hook exit | Hard cut | Light leak + riser |
| Body | Split receipts | Full-frame alternation: him, b-roll, boards, pages, black cards, chest cards |
| Captions | None | Box karaoke |
| Music | None | Bed at ~-11 dB |
| End | Line to the lens | Follow pill + cursor |

## OB's version (T26): engine switches (tmpl, 11-07)
- **Hook:** `split` with `"seam": 960`, `"ob_push": 0.02`, `"face_top": 1330` (his cap clears the seam), `"caps": false`, and a `top` of `burst` or `src`.
- **Banner:** a `banner` element with `"lines": [L1, L2]`, `"y": 960`, `"at": 0`, `"only": ["hook"]`.
  - Default: Drew's red boxes.
  - `"alt": true` = amber.
  - `"style": "brand"` = OB's no-box Big Shoulders. **OB chose Drew's boxes on 11-07**, so this is used only if he asks.
- **Hook exit:** a `leak` element `{"on": FIRST_WORD_OF_SENTENCE_2, "after": ~hook_end - 1, "lead": 0.03}`, plus `sfx` `riser.mp3` with `"delay": -1.73`, `"len": 1.7`.
- **His shots:** `{"name": "full", "drift": 0.024}`, or `-0.016` to pull on the close, or no drift to hold.
- **Captions:** `{"style": "box", "y": 1074, "n": 3, "box": [0, 0, 0], "box_a": 0.65}` (the box colour can be set per reel). Per look: `"caps": false`, `"cap_y"`.
- **Receipt page:** `{"name": "plate", "bg": "paper"}` + an `image` element with `highlight`.
- **Chest card:** `image` with `"enter": "rise"`, top under the caption.
- **Black b-roll card:** `{"name": "bcard", "src": CLIP, "t": T}`.
- **Board:** `plate` with `paper` or `cream` + elements (count, text, days, ...).
- **End:** `{"type": "cta", "mode": "follow", "avatar": FACE_CROP}` (brand pill).
- **Music:** `"music": {"file": Lane A track, "rel": -11}`. Drew's level; Megann's is -21 to -27. **This is OB's call.**
- **Test:**
  - Plan: `/Volumes/T7/OB-EDITS/2026-11-07-style-truth/t26-test/T26_drew.json` (C4413 + DdJWjTsspZw b-roll).
  - Stills: `out/STILLS_T26*.jpg`.

## House-rule clashes (OB decides; the creator's look is the default per format fidelity)
- **DECIDED 11-07, OB: "Keep Drew's look".** T26 uses Drew's red 2-line banner boxes and box-karaoke captions. His no-boxed-text rule does not apply to T26. `"style": "brand"` stays only as an option he must ask for.
- **M37 (on screen while talking):** Drew is off screen ~40% (b-roll, boards, pages).
- **M38 (no black backgrounds):** his black b-roll card page.
- **No boxed text:** his banner and box captions.
- **No AI imagery:** always swap his AI-looking shots for real ones.
- **Film for it:**
  - Sentence 1 is the hook, said in one breath.
  - Film it wider than your normal framing (his split half is ~0.74x).
  - Get b-roll of the topic for the top half (4-6 clips of 1-1.5 s).
  - Get one real study page per claim.
