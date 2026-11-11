# Changelog

## 2026-11-02 (replaces the 2026-10-21/22 kit)

Everything OB's editor learned between Oct 22 and Nov 1. Re-run `bash INSTALL.sh ~/EditorWork` over the old kit: your old
`ob-editor`, `ob-clipper`, `ob-moments` and skill folders are renamed with a timestamp, never deleted, so copy any presets
you locked yourself back in from the renamed folder.

### New: the QC gate (every render passes it before anyone sees it)
- `qc_gate.py`: one gate run at the end of every render. It checks every scripted word is heard, silence and dead space,
  "cut that" retakes left in, cuts on a look-away, text over the face, loudness and true peak, quality (VMAF), 9:16 format,
  one-frame flashes, the hook on frame 1, dashes or "free" on screen, IG safe zones, and cut edges inside a word.
- `qc/mistakes.json`: the never-again ledger, 41 rules, each written from a real note OB gave on a real edit, with the check
  that catches it. `qc_gate.py --rules` prints it. When you give a new note, Claude adds a rule and a check.
- `deliver.py`: the only way a file reaches your delivery folder. It copies only on a PASS and makes a 720p phone copy over
  30 MB.
- `--selftest` runs the gate's logic tests. OB's planted-mistake clips are his footage (about 100 MB) and are not shipped;
  plant your own in `ob-editor/qc/regress/` (the list is in `fixtures.json`) and the self-test runs them too.

### New: clean cuts and a clean voice
- `takes.py`: keeps the last clean take of every script line and drops the "cut that" tries, restarts and short tries.
- `zero_dead.py`: word-safe cut edges with zero dead space (silence 3% or less, no gap over 0.2 s) and the eyes-off check at
  every cut. `breaths.py` (with `vad_probs.py`) cuts audible breaths like pauses.
- `voice_master.py`: masters the mic to about -14 LUFS without ever hard-clipping; `tp_fix.py` fixes a true peak that
  overshoots after encoding.
- `sync_pieces.py`, `lag_steps.py`, `cutqc_chain.sh`: sync a long external-mic take piece by piece, and check a long cut for
  lost words and bad joins.
- `words_at.py`, `roughcut.py`: words between two times, and a 540p rough cut of a long-form cut list.

### New: graphics that move and never cover a face
- `overlay_touch.py`, `face_clear.py`, `card_faces.py`, `fq_fit.js`: no title, caption or card ever touches a face, his or
  anyone's on stock footage; quote cards shrink to fit instead of rewrapping badly.
- `kinetic_cards.py` + `kinetic_sides.py`: bigger kinetic words placed on the free side of the subject.
- `reel_cards.py`: every overlay moves (no static images, no text-only overlays).
- `box_flash.py`: box-flash word captions (each word flashes as a white box for 2 frames, then the text).
- `moves.py`: the zoom kick on a stressed word, a running calorie counter, the comment-section CTA.
- `motion_score.py`: how alive a finished video is, measured from its pixels (events a minute, idle time, first move,
  one-frame flashes); calibration in the skill's `references/motion-library.md`.
- `beside_split.py`, `jh_cards.py`: the chart-beside-you layout and paper cards from the Johnny Harris study.
- `overlay_freq.py`: overlay frequency of any talking-head video, frame by frame, to copy a reference's density.

### New: the long-form to reels clipper
- `ytclip.py` (+ `ytclip_pic.py`, `ytclip_yt.py`): turns a long-form edit into finished 9:16 reels from its own cut decisions.
  Stages: cut, lookoff, mock, page, render, qa, deliver, review. Preset `presets/yt-clips/PRESET.md`.
- Rules built in: every reel under 1:30; a clip is made only when a part stands alone as a complete, good clip (picks are a
  ceiling, not a quota); his face on screen while he talks; horizontal footage goes in a 50/50 split (style card
  `styles/dylan-page-split.md`); long-form graphics are rebuilt for 9:16, never cropped.
- Render clips with `ytclip.py render WORK --yield` so they wait for the machine to be free.
- The Monday `review` stage reads YouTube views from Instagram with your own YouTube API sign-in; it is optional.

### New: reactions and formats
- Reaction shots are your real playback: `react_window_audit.py` finds the moment your phone played that clip by its sound
  and fails any other window (no "reacting" while scratching your leg).
- `brand_react_render.py`: reactions in a clean brand look, with the clip cut at sentence edges.
- `presets/fdoe-breakdown/PRESET.md`: a day-of-eating breakdown layout (TEMPLATE, test it against `fdoe-audit`).
- `presets/PROVEN-OPENERS.md`: which reel openings held viewers, measured on OB's skip rate over 6,130 reels.
- New style cards in `ob-editor/styles/`: Artzen "Breaking Reels", Dylan Page split, split punch bubble, Johnny Harris,
  Tunde Alao rebuilding, Rico appetizer clips, framework canvas, and a technique library from 38 creator studies.
- `breakdown_page.py`: the shot-by-shot approval page for long-form, before any full render.

### New: YouTube thumbnails (method from 2026-11-01)
- `claude-skills/short-form-editor/references/youtube-thumbnails.md`:
  - mirror a proven mega-outlier thumbnail's layout (any niche) and theme it with your own frames and props
  - always keep the A/B test winner in slot 1 of the next round, plus 2 new challengers
- `clean_skin.py`: acne spot removal on your face in thumbnails. Small red spots only; eyes, lips and nose untouched; run it on
  the 4K frame and check the compare image.
- The long-form preset's upload steps point at it.

### New: sound
- `openverse_sfx.py`: search and download real recorded sound effects from Openverse (CC0 first, every source logged).
- The Kenney CC0 sound kit (`assets/sfx_real/`) now ships.
- The two sound tools OB installed on 11-01, as an optional install: `zsh ~/ob-editor/bin/install_sfx_tools.sh` pulls earshot 0.4.0
  (pick a sound by ear from a folder, via the guarded `bin/earshot` wrapper) and Clipwing's Real SFX skill (places recorded sounds
  on exact frames, with OB's rules on top) straight from their GitHub releases, checked by sha256. About 1.5 GB of models, once.
- Sound-effect rule changed: use them only where a beat needs one, about 3 to 4 a minute at most in a reel, none in the first
  0.5 s, quiet and varied. (Was: off unless asked.)
- `stock_pexels.py`, `stock_mixkit.py`: free stock video for long-form overlays (Pexels needs a pexels.com tab open in
  Claude's browser).

### Changed
- `short-form-editor` skill: the new hard rules (zero dead space, bad takes out, the QC gate, one heavy job at a time), the
  toolbox rows for every tool above, and the skill's `references/` folder (motion library, thumbnail method) now ships.
- Presets updated: short-form, youtube-longform, reaction, fdoe-audit.
- Updated tools: `assemble.py`, `cards.py`, `gate_lib.py`, `final_deliver.py`, `lookaway_check.py`, `pace_check.py`,
  `coverage_check.py`, `trial_variants.py`, `react_render.py`, `react_prep.py`, `tier_render.py`, `resolve_events.py`,
  `stage.py`, `sync_av.py`, `sync_steps.py`, `render_review.py`, `lecture_render.py`, `explainer_cards.py`, `bleep_pin.py`,
  `build_breakdown.py`, `react_breakdown.py`, `mock_shots.js`, `commons_fetch.py`, and ob-clipper's `render_clip.py`.
- `INSTALL.sh` adds `faster-whisper` to the editor venv (the breath and speech detector needs it).

### One heavy job at a time
The kit was built on an 8 GB MacBook Air, which crashed on 11-01 with three heavy jobs running at once. Run one render,
4K frame job or thumbnail build at a time; the queue scripts and `--yield` wait for the machine to be free.

### Not included
OB's footage, client photos and names, his notes and account data, OB's planted-mistake test clips, the Anderson Tai SFX pack
(no licence for sharing).
