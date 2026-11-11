# Route: reaction reel  (`reel-reaction` in formats.json)

Use it when: OB sends someone else's clip (a link or a file) and his own take, "react to this", a myth react, a debunk of a clip. He filmed himself watching the clip on his phone and then talking. Also read: `subjects/audio.md`, `subjects/graphics.md`, `subjects/qc.md`, `subjects/delivery.md`; `subjects/proof-clients.md` when he mentions clients or results.

Long-form reactions (a YouTube video that reacts to clips) are not this route: they use `routes/long-form.md`. The same two rules apply there (clip untouched, found by sound).

## The bar
- OB 11-09: "on videos, never touch the original clip save that as a rule, only thing you can do to it is add me in the green screen". The clip plays whole, first frame to last, full screen, with its own picture and sound. Added to it: OB, green-screened over it, and nothing else.
- OB 11-09, on a reel that hid the clip: "y is there no reaction or playing the clip at the start this is so odd". So frame 1 is the clip.
- OB 10-30: "you did very good on these" (C4380, three looks: green screen, reacting, sober), and "next time add image overlays". That is the only approved reaction. Its measured shape: 87.6 s, about 222 words per runtime minute, first move inside 1 s, loudness -14.1 LUFS. Gold record: `~/ob-editor/qc/gold.json` (entry for this format). The reviewer compares against it.
- Creator reference for pace and graphics: Karan Rajan, `~/ob-editor/styles/karan-rajan-doctor-react.md` (about 40 graphic events a minute, no music under him, both people in frame at 0.4 s). Copy his pace and graphic grammar. His freeze and punch moves are not allowed here (the clip is never frozen or zoomed).
- Openers: `~/ob-editor/presets/PROVEN-OPENERS.md` rule 1 (both people in frame at 0.4 s) is met by the clip plus the cutout from frame 1.

## Inputs
- The clip: the creator's own original upload, a file or a link OB gave. Not a re-post and not a screen recording of it (OB 11-02: "make sure im not reacting ot myself reacting"). A link is downloaded with `yt-dlp` into `WORK/clip/`.
- His camera file and his mic file for the take (he watched the clip on his phone in that take, then talked). Camera audio is only for matching; his voice is always the mic.
- Optional script. With none, run `ob_job.py start` with `--no-script "why"`.
- References: the creator's format if he named one (T15 Karan, T25 Michael Read): decode it first (see Decisions).

## Steps
Run the loop in the core. Each step ends in the file named.

1. **Start.** `python3 -I ~/ob-editor/bin/ob_job.py start reel-reaction WORK --camera CAM.MP4 --mic MIC.wav --script SCRIPT --ref CLIP_LINK`. Read the rules it prints.
2. **Fix the clip.** Copy the original to `WORK/clip/original.mp4` (never re-encode it). Run `ffprobe` for duration, fps and size. Transcribe it: `~/ob-editor/bin/speech_words words CLIP.wav`. Write `WORK/clip/ORIGINAL.json` `{file, sha256, duration, fps, w, h, has_speech, source_url}`. `has_speech` is true when the clip has any spoken word. → `WORK/clip/ORIGINAL.json`
3. **Sync and transcribe his take.** `python3 -I ~/ob-editor/bin/sync_av.py CAM.MP4 MIC.wav --audio-only WORK/audio/mic_synced.wav` (the mic on the camera timeline). Words from the synced mic with `speech_words words`, saved as `WORK/story/words.json`. → `WORK/story/words.json`
4. **Find the moment he watched it, by sound.** `python3 -I ~/ob-editor/bin/react_window_audit.py CAM.MP4 WORK/clip/original.mp4 WORK/story/words.json WORK/qc/react NAME:CAM_START:0:CLIP_DURATION`. CAM_START comes from the playback offset it finds. The window must cover the clip's full length.
   - The tool matches the clip's sound inside his camera audio and writes a frame sheet per window. Open every sheet and look: he is facing the phone, his eyes are on it, he shows a reaction, he is not scratching, reaching or looking at the lens.
   - If his phone played the clip in pieces (he paused), use one sound-matched window per piece, each piece in clip order. The clip drives time; his footage follows it.
   - If the audit hears no playback, or a stretch of the clip has none, stop. Say in one sentence that the camera file does not hold him watching that part, and that the watch has to be filmed again with the clip audible. Do not pick a still stretch by eye and do not use a pause between his lines.
   - Write `WORK/qc/react_windows.json`: `{"windows": [{"name", "cam_start", "clip_start", "dur", "method": "sound_match", "frame_sheet": <the sheet's path, absolute or from WORK>, "reacts": true}]}`. `reacts` is true only after you looked at that sheet. → `WORK/qc/react_windows.json`
5. **Cut him out with BiRefNet.** `~/OpenMontage/.venv/bin/python -I ~/ob-editor/bin/matte_hq.py WATCH_PIECE.mp4 WORK/matte/watch FPS` writes RGBA frames. Make a sheet of 8 frames over a bright colour with `frame_sheet.py` and look at every edge (hair, shoulders, phone, hands). A ragged edge, a hole or flicker: re-run with `OB_MATTE_SMOOTH` higher and look again. Never use another matte method. → `WORK/qc/matte_sheet.jpg`
6. **Cut his lines.** If there is a script: `python3 -I ~/ob-editor/bin/takes.py WORDS.json SCRIPT --audio MIC.wav --fps FPS --edl WORK/story/edl.json --voice WORK/audio/voice.wav --master`. With no script, cut with `zero_dead.cut_words` over `words.json` and master with `voice_master.py`. Every edge lands between words on a real pause (core rule 1), lines he shot stay in, he is looking at the lens at every cut in and out (core rule 3). → `WORK/story/edl.json`, `WORK/audio/voice.wav`
7. **Plan the picture.** Write `WORK/BREAKDOWN.md`: the clip's duration; part A (clip with the cutout); part B (his lines, with a table of every graphic: time, the sentence, the real photo, chart or footage that shows it, where it sits beside him). Every graphic is footage, a real photo, a chart or a drawn object with a source file that you looked at (contact sheet in WORK, listed in the breakdown). Text-only cards are not allowed. Alongside it, `WORK/plan/moments.json` `[{id, t, what}]` for the sound effects. List the graphics in `WORK/plan/plan_graphics.json`. Then `python3 -I ~/ob-editor/bin/qc_assets.py build WORK` and fill every row it lists (`subjects/graphics.md` section 8: which plan it reads, which fields); `viewed: true` only after you opened the sheet, saved as `WORK/qc/sheets/<row id>.jpg`. `qc_assets.py check WORK --route reel-reaction` shows no FAIL. → `WORK/BREAKDOWN.md`, `WORK/qc/assets.json`
8. **Music and sound effects, part B only.** `python3 -I ~/ob-editor/bin/music_pick.py WORK --route reel-reaction --voice WORK/audio/voice.wav --tone "upbeat, bright"` writes `WORK/audio/music_candidates.json` (three or more tracks scored against this cut, the winner and why). Read the record and the previews it writes. Then `music_pick.py apply WORK`. Then `python3 -I ~/ob-editor/bin/sfx_pick.py WORK --route reel-reaction`: it reads `plan/moments.json` and writes `WORK/story/sfx_plan.json`. Details: `subjects/audio.md`. → `WORK/audio/manifest.json`, `WORK/story/sfx_plan.json`
9. **Build.** Compose in a script kept in WORK (`WORK/build.py`, ffmpeg): see Layout. Render to `WORK/out/reaction.mp4`. → the file.
10. **Prove the clip is untouched.** Make a sheet of the clip span in the output and the same times in the original (`frame_sheet.py` on each, at 10 evenly spaced times): same frames, same framing, no crop, no tint, no text. The span's duration in the output equals the clip's duration within one frame. Play the output's audio across the span against the original's audio (same loudness, no music, no effects). → `WORK/qc/clip_span_out.jpg`, `WORK/qc/clip_span_orig.jpg`, listed in `WORK/BREAKDOWN.md`
11. **Gate, review, finish** as in the core: `ob_job.py gate WORK FILE`, answer every WARN in `WORK/qc/warn_answers.json`, hand the file to `video-reviewer`, then `ob_job.py finish`.

## Layout (the decision, not a menu)
- **Part A, the clip.** The clip fills the 9:16 frame at its own aspect, centred, never cropped, stretched or boxed. A horizontal clip sits at full width with the rest of the frame filled by a blurred copy of the same clip (never black, core rule 7); the clip itself is not altered. OB's cutout (step 5) sits bottom left, face width about 0.17 of the frame width, face top at 0.66 to 0.74 of the height, body running off the bottom edge, no box, no border, a feather of about 1 px. He is silent and watching.
- **Part B, his take.** Starts the frame after the clip ends. OB full frame at the desk, warm grade from his usual LUT, on screen every frame he talks. Graphics go beside him or on his chest, clear of his face over the whole event, inside the safe bands.
- **A clip with no speech** (`has_speech` false: music, ambience, a silent demo): he may talk during it. His cutout stays over the clip, the clip's sound stays, his voice sits over it, and there is no bed and no sound effect until the clip ends. A clip with speech: he never talks during it (a creator's voice never plays under his, OB 11-03: "when they are talking dont play their audio when im talking").
- The clip never returns in part B, not as a still, a replay or a cut-in. He refers back to it in words.
- Credit: in the post caption, never on screen.

## Decisions that are yours
- **Which look (box, corner cutout, Trainbloom look-down, Karan board, Israetel box).** The only look is the one above (clip full screen, cutout over it). If OB names a creator's format by name, decode that creator at 10 fps over 25 to 30 of their reels, measure the layout shares, and keep every part of it that does not touch the clip. Record the comparison in `WORK/qc/format_check.json` (rows with `ours`, `reference`, `ok`). A creator move that boxes, freezes, crops or zooms the clip is dropped and the row says why.
- **A long clip.** It plays whole, however long. One clause at delivery gives the runtime. Never trim it to fit.
- **Several clips in one reel.** Each clip plays whole in turn, each with its own sound-matched watch window and cutout, his lines between them. Each gets its row in `react_windows.json`.
- **Music.** Chosen by `music_pick.py` from three or more candidates, upbeat and bright, under part B only. Runner-ups are named in the delivery note.
- **Sound effects.** From the bank, tied to a graphic's event, never over the clip. The route's cap applies to the whole reel.
- **Fact conflict in the clip** (the creator is wrong, or right). That is the point of the reel. A factual conflict between his line and the evidence is one clause at delivery. Numbers on screen only when he says them; look up claims with `/evidence-check` before a number goes on a graphic.
- **Hook text, captions, credit on the clip.** None on the clip. Captions on his lines in part B follow the brand look in `subjects/graphics.md`.

## Traps
- Picking his reaction by silence or by a pause between lines. OB 10-31: "that wasn't me reacting it that was me scratching my leg"; "you can see me looking away and not playing the vids, I played the Gary vid you can hear it"; 11-01 "you didnt get me reacting, 33 seconds in is me reacting". Stopped by step 4: the match is by sound and every sheet is looked at.
- The clip hidden, shown in a small box or shown for seconds. OB 10-30 "there isnt the reaction on this one at all"; 11-04 "the frozen ice cream video of me reacting isnt showing the reaction"; 11-09 the "no reaction or playing the clip" note above; 10-21 "you last time put it in a square rather than a normal frame". Stopped by steps 7 and 10.
- A creator's voice under his. OB 11-03: "when they are talking dont play their audio when im talking". Stopped by the `has_speech` rule.
- Cutout with a rough or Apple-made edge. OB 11-06 and 11-09 set BiRefNet only. Stopped by step 5.
- Text-only slides in part B. OB: "Again I hate boring just text slides". Stopped by step 7 (every graphic has a source file).
- Zooming in and out. OB 11-07: "its zooming in and out non stop". No zoom anywhere in the reel.
- Cutting him off, dead space, a held frame to fill time. Core rules 1 to 3; a decoder that comes up short is a FAIL to fix, never a held frame.
- Sending several versions. OB 11-04: "when you render dont render 4 versions each and send me 4, only 1 is needed". One file.

## Finish
- Gate inputs this route needs (from `ob_job.py start`): the script or its `--no-script` reason, the pieces and camera map from the render, `story/sfx_plan.json`, `audio/manifest.json`. No recorded pieces? `subjects/qc.md`, "When the gate says there are no recorded pieces". Records: `qc/react_windows.json`, the assets record (every graphic and photo with `viewed: true` and matte method `birefnet`), `qc/warn_answers.json`.
- The hook check is N/A on this route (the clip plays untouched from frame 1) and silence is N/A over the clip; the reviewer still checks his lines for dead air.
- Give the reviewer: the file, the clip (`WORK/clip/original.mp4`), `WORK/BREAKDOWN.md`, `WORK/qc/react_windows.json` with its sheets, the two clip-span sheets, and `~/ob-editor/qc/REVIEW-CHECKLIST.md` (the reaction and original-clip rows).
- Delivery note (`ob_job.py finish --to "reaction: <creator>"`): the file, the clip's runtime, the music pick with runner-ups, any factual conflict as one clause, the credit line for the caption.
