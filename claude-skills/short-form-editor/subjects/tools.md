# Subject: tools and engines (look-up)

Find the tool here, then run its `--help` or read its docstring for flags; this file does not repeat them. Run Python tools as `python3 -I ~/ob-editor/bin/NAME.py ...` unless a row says otherwise. All paths exist on this Mac. Tools under `~/ob-editor/bin` have older copies beside them (`*.2026-*`, `*.bak-*`): never run those.

If a tool, model or asset a step needs is missing, stop and say so. Never swap in a cheaper stand-in (a code-made sound, a text card, a held frame, the last video's music, a Vision mask, stock filler).

## 1. The job, the gate and the notes

| Tool | Use it for | Command |
|---|---|---|
| `ob_job.py` | the one entry point: routes, start, rules, brief, status, gate, finish | `ob_job.py routes`; `start ROUTE WORK --camera F --mic F (--script F | --no-script "why") [--template T17] [--ref URL]`; `rules ROUTE [--hash]`; `brief WORK`; `lint-brief FILE`; `status WORK`; `gate WORK FILE`; `finish WORK FILE --to "what it is"`; `allow-send FILE --why "..."` |
| `qc_route.py` | the route settings from `~/ob-editor/qc/formats.json`, the verdict and the problems for a file | `qc_route.py routes`; `verdict FILE`; `problems FILE --work WORK` |
| `qc_gate.py` | the checks themselves (run through `ob_job.py gate`) | `qc_gate.py --rules [ROUTE]`; `--selftest` |
| `ledger.py` | OB's notes as rules with an enforcer | `ledger.py add --said "..." --date YYYY-MM-DD --rule "..." --check CHECK --routes R --enforcer gate:CHECK`; `list --route R --active`; `supersede M24 --by "OB 11-09 ..."`; `coverage` |
| `deliver.py` | delivery copy and log; only `ob_job.py finish` calls it | never run by hand |
| `skill_lint.py` | lint of the skill files | `skill_lint.py SKILL_DIR` |
| `doctor.py` | is every tool working (run after a macOS or brew update) | `doctor.py [--quick]` |
| `render_slots.py` | how many heavy jobs run; wait for a free slot | `render_slots.py list\|busy\|wait` |

Reviewer: the `video-reviewer` agent against `~/ob-editor/qc/REVIEW-CHECKLIST.md` (R01 to R30). Gate, WARN answers and notes: `subjects/qc.md`. Where files go: `subjects/delivery.md`.

## 2. Audio

Rules and the full picture: `subjects/audio.md`.

| Tool | Use it for | Command |
|---|---|---|
| `bank_index.py` | the music and sound bank index (hash, licence, lane, loudness, tempo) | `bank_index.py lookup FILE` |
| `music_pick.py` | at least 3 scored candidates, the pick, the mix | `music_pick.py WORK --route ROUTE --voice VOICE.wav`; `apply WORK`; `use WORK` |
| `sfx_pick.py` | a sound tied to each on-screen event, with runner-ups | `sfx_pick.py WORK --route ROUTE` |
| `qc_audio.py` | the gate's audio checks (bank, bed level, repeats, heard, linked) | called by the gate |
| `sfx_check.py` | screen a sound or a plan (rate, first 0.5 s, gaps, variety, level) | `sfx_check.py files FILE...`; `plan PLAN.json --dur S` |
| `earshot` | local audio listening: tags, similarity, ranking (a wrapper; no uploads) | `~/ob-editor/bin/earshot`; also `~/ob-editor/earshot-home` |
| `openverse_sfx.py` | fetch real openly licensed sound clips when the bank has none (log the miss) | see docstring |
| `voice_master.py` | master his mic to the loudness target, never a hard clip; `check` reads any render | `voice_master.py master IN.wav OUT.wav [--lines EDL.json]`; `check FILE` |
| `lipsync_check.py`, `av_sync_check.py` | lips against the camera's own sound | `lipsync_check.py FILE.mp4`; `scan CAMERA MIC T0 T1` |

Banks live in `~/ob-editor/assets/` (`music/`, `sfx_library/`, `sfx_ob_drive/`, `sfx_tai/`, `sfx_real/`). `~/ob-editor/assets/sfx` is the code-made kit: never used. `assemble.py` can synthesize sounds itself; its output never goes in an edit: put the bank sound in `story/sfx_plan.json`.

## 3. Cut, words and voice

| Tool | Use it for | Command |
|---|---|---|
| whisper.cpp | word timestamps (`medium.en` for final captions) | `/opt/homebrew/bin/whisper-cli`; models in `~/.whisper-models/` (`ggml-base.en`, `ggml-medium.en`, `ggml-large-v3-turbo`) |
| `speech_words` | fast first-pass transcript (Apple, on device); not for cut timing | `~/ob-editor/bin/speech_words words AUDIO.wav` |
| `chunks.py`, `hear_segments.py`, `words_at.py` | speech chunks, hear candidate takes one by one, words at a time | docstrings |
| `takes.py` | bad takes out, last clean take kept, EDL, voice build, word diff | `takes.py WORDS.json SCRIPT --audio MIC.wav --edl OUT.json --voice OUT.wav --master --verify` |
| `zero_dead.py` | cut edges safe between words; dead-space yardstick; look-off check | `zero_dead.py measure FILE`; `line AUDIO S E`; `lookoff VIDEO PIECES.json` |
| `breaths.py` | find audible breaths in a cut and cut them like pauses | docstring |
| `cut_audit.py` | is a word clipped at a cut, does every join breathe | docstring |
| `tighten_edl.py`, `cutlist.py`, `tier_edl.py` | energy-based tight cuts and cut lists for talking heads and tier lists | docstrings |
| `sync_av.py` | pair camera and MOTIV mic (offset and drift) and grade | `sync_av.py CAMERA.MP4 MainOutput_24bit.wav OUT.mov [--measure-only]` |
| `make_grade.py`, `match_grade.py` | a per-take grade as a Hald CLUT; match a take to an earlier one | docstrings; default LUT `~/ob-editor/luts/ob_grade_warmtan_hald.png` |
| `ffmpeg-full` | the ffmpeg with `subtitles`, `drawtext`, `rubberband`, `zscale`, `vidstab` | `~/ob-editor/bin/ffmpeg-full`, `ffprobe-full`; system `/opt/homebrew/bin/ffmpeg` for the rest |
| `vmaf_check.py` | quality score of an export against its reference | `vmaf_check.py REF DIST` |

## 4. Pictures: look, cutouts, sheets

Rules: `subjects/graphics.md`.

| Tool | Use it for | Command |
|---|---|---|
| `matte_hq.py` | the only cutout: BiRefNet, RGBA (needs the OpenMontage venv); engines call it through `birefnet_cut.py` (cache, `WORK/qc/matte.json`) | `~/OpenMontage/.venv/bin/python -I ~/ob-editor/bin/matte_hq.py IN.mp4 OUT_DIR FPS`; `... IN.png OUT.png` |
| `qc_assets.py` | the picture plan's proof: manifest of every overlay, source, sheet, matte | `qc_assets.py build WORK [--plan FILE]`; `check WORK --route ROUTE` |
| `frame_sheet.py` | contact sheet of a video at given times | `python3 ~/ob-editor/bin/frame_sheet.py VIDEO OUT.jpg T1 T2 ...` |
| `frames_at.js` | dense proof frames of one mock composition (run with node from `~/ob-editor`) | docstring |
| `proof_screen.py` | consent screen for client photos | `~/OpenMontage/.venv/bin/python -I ~/ob-editor/bin/proof_screen.py OUT.json --cands "GLOB"` |
| `commons_fetch.py`, `stock_pexels.py`, `stock_mixkit.py` | licensed photos and stock, only with a written reason | docstrings |
| `doc_page.py` | a real document page with the key line highlighted | docstring |
| `blender_insert.py` | 3D brand-font word or number, RGBA frames | `blender_insert.py OUT_DIR --text "14%" [--look paper\|dark]`; Blender is `/Applications/Blender.app/Contents/MacOS/Blender`; counts toward `render_slots.py` |
| `cards.py` with `kinetic_cards.py`, `motion_cards.py`, `reel_cards.py`, `explainer_cards.py`, `jh_cards.py` | the card system and its drawn graphics, springs POP/SNAP/SOFT/SLIDE/BAR/COUNT | docstrings |
| `tmpl.py` with `tmpl_fx.py`, `tmpl_board.py`, `tmpl_ig.py` | the plan-driven template compositor (catalog `~/ob-editor/styles/TEMPLATE-CATALOG.md`); `tmpl_ig.py` is Instagram-native text for ads | `tmpl.py still PLAN.json OUT.jpg T T ...`; `tmpl.py render PLAN.json OUT.mp4` |
| `canvas_card.py` | Kallaway canvas: graphics above him, him in a card at the bottom | `canvas_card.py demo PLAN.json OUT.mp4` |
| `box_flash.py` | Artzen box-flash captions | docstring |
| `moves.py` | the counter and comment-wall moves (the zoom kick in it is not used) | `moves.py counter\|comments IN OUT ...` |
| `~/ob-editor/level-kit/lk.py` | the GLP level look from a plan (3D objects, b-roll cascade, matte, captions) | `python3 -I ~/ob-editor/level-kit/lk.py STEP PLAN`; first read `~/ob-editor/level-kit/README.md` |
| `head_clear.py`, `face_clear.py`, `overlay_touch.py` | keep graphics off his head and face (long-form WORK) | `overlay_touch.py WORK`; `head_clear.py WORK [--write]` |
| `fit_check.py`, `flicker_check.py`, `coverage_check.py`, `pace_check.py` | fill the frame; no flicker; graphics share; pace (long-form WORK) | `fit_check.py WORK`; `flicker_check.py WORK` |
| `motion_score.py` | how alive a finished video is: events a minute, idle time, flashes | `motion_score.py FILE [REF ...] --png DIR` |
| `clean_skin.py` | spot removal on his face in a YouTube thumbnail | `clean_skin.py IN.png OUT.png X Y W H` |
| HyperFrames | HTML motion graphics (check the `/hyperframes` skills first) | `cd ~/ob-editor && npx --prefix ~/ob-editor hyperframes render . -o out.mp4 --workers 4`; `--format mov` for a transparent overlay |
| Puppeteer | HTML to PNG or video | node from `~/ob-editor` (`node_modules`) |

Never run `npx hyperframes skills update` or `npx skills update` bare (it removes skills the editor routes to). Never run `hyperframes publish`. Blender recipes: `~/ob-editor/blender-skills/README-OB.md`; interactive `mcp__Blender__*` when Blender is open.

## 5. Engines by route

Start each from its route file. An engine's own defaults never override the rules in the core: its sounds come from `sfx_pick.py`, its music from `music_pick.py`, its cutouts from BiRefNet (`birefnet_cut.py`), its zoom steps are off.

| Route | Engine | Notes |
|---|---|---|
| `reel-talking` | `takes.py`, `zero_dead.py`, `tighten_edl.py`, then `tmpl.py` or a plan-driven render | no template named |
| `reel-graphics`, `reel-lists` | `tmpl.py`; the GLP level look through `lk.py` | templates T07 to T09, T13, T14, T16 to T24, T26 |
| `reel-reaction` | `react_render.py`, `brand_react_render.py`, `react_window_audit.py`, `react_prep.py`, `react_gfx_face.py` | `react_window_audit.py CAMERA CLIP WORDS.json OUT_DIR name:cam_start:clip_start:dur` picks the watching window by sound |
| `reel-fdoe` | `tmpl.py` (T01, T02); the Artzen engine `fdoe_artzen.py` is a project copy on the T7 at `/Volumes/T7/OB-EDITS/2026-10-28-backlog/_work/fdoe_artzen.py` (read only: copy it into WORK to change it) | the FDOE skill `/fdoe-review` makes the review sheet |
| `reel-lecture` | `lecture_render.py`, `lecture_cards.py`, `tier_render.py`, `tier_cards.py` | its punch-in steps stay off |
| `yt-clips` | `ytclip.py cut\|lookoff\|mock\|page\|render\|qa\|deliver\|review WORK` | reads the long-form edit's own decisions |
| `repost-trials` | `trial_variants.py`, `first3_check.py SPEC.json\|DIR\|FILES` | |
| `long-form` | `assemble.py`, `stage.py`, `resolve_events.py`, `beats.py`, `roughcut.py`, `render_review.py`, `final_deliver.py` | render with one job at a time per `render_slots.py` |
| `ad` | the reel engines above; `tmpl_ig.py` for text | scripts live in `/ad-maker` and `/ugc` |

## 6. Reference, capture and other skills

| Tool | Use it for | Command |
|---|---|---|
| `rea-video` | shot-by-shot teardown of a reference (filmed, 3D, code render, captions, SFX hits, cuts); review then apply-review before trusting it | `~/ob-vendor/bin/rea-video` (skill `/rea-video`) |
| `/watch`, `yt-dlp` | pull and read a video or reference link | `/opt/homebrew/bin/yt-dlp` |
| OpenMontage | `~/OpenMontage` (read `OB-SETUP-NOTES.md`); venv Python `~/OpenMontage/.venv/bin/python` has OpenCV for the consent screen | |
| `motion_score.py` and `overlay_freq.py` | measure a reference the same way as the edit | docstrings |
| `~/ob-brain/brain.py`, `~/ob-youtube/yt_analytics.py` | OB's brain and channel analytics | docstrings |
| Skills | `/hooks`, `/youtube`, `/carousel`, `/ad-maker`, `/ugc`, `/motion-graphics`, `/talking-head-recut`, `/embedded-captions` | HyperFrames skills build only the graphics layer; the checks stay here |

The level brief for the graphics-led look: `/Volumes/T7/OB-EDITS/2026-11-05-scripts/LEVEL-UP-BRIEF.md` (read only).
