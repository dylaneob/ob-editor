# Route: Trial reposts of a posted winner  (`repost-trials` in formats.json)

Use it when: OB says to re-run a posted winner as trials, "make trials of this one", or sends a posted reaction reel (a reaction box, then his line) to be re-posted with a different opening. Trials are reposts of proven winners only (OB 10-30); a new reel never gets a trial pack. Also read: `subjects/audio.md`, `subjects/qc.md`, `subjects/delivery.md`.

## The bar
- **No approved repost set exists.** OB's words that define it: "in trials it needs to be a different first 3 seconds" and "make sure they make sense to what im saying after the reaction" (10-20). The posted winner is the bar: everything after the opening stays what the audience already watched.
- **What the data says to expect:** a repost of the same footage skips about 3.6 points more than its first posting (`~/ob-editor/presets/PROVEN-OPENERS.md`); that is expected, not a defect. Reposting a non-breakout breaks out at 0.33x the normal rate, so the route is for winners.
- **Reference for verification:** re-rendering delivered versions from their specs gave identical video frames on all 5 versions tried (10-21). Your versions must differ from the posted reel only where the spec says.

## Inputs
- The posted reel as a file (`POSTED.mp4`), and proof it is a posted winner: its post link or the performance line OB gave. Posting status first: if the source is not posted, or he said "I already posted it" about the versions, stop and report; nothing is cut.
- The working spec of the closest earlier job, read from the T7 (project copies, read only: copy into WORK to change): `/Volumes/T7/OB-EDITS/0719-BROOKIE-TRIALS/_work/spec.json` (box layout: the box until the cut to him) or `/Volumes/T7/OB-EDITS/1230-MODEL-TRIALS/_work/spec.json` (the box, then the clips full screen, then him). Pick the one whose layout matches the posted reel.
- The creator's original clips. Use the original upload, never a repost (OB 11-02: "make sure im not reacting ot myself reacting"). The files the posted reel used are in the earlier job's `sources`; if an original must be downloaded, the harness asks for permission to download: answer it as the harness asks, then continue.
- For a version that needs new spoken lines: raw takes of him, edited with the talking route's cut (`routes/short-form.md` steps 2 to 4: `takes.py`, zero dead space, `voice_master`).

## Steps
Start: `python3 -I ~/ob-editor/bin/ob_job.py start repost-trials WORK --camera POSTED.mp4` (the posted file stands in for the camera; add `--mic` and `--script` when a version has new spoken lines).

1. **Probe the posted reel.** `python3 -I ~/ob-editor/bin/trial_variants.py probe POSTED.mp4 --out WORK/_work`. It finds the box and `new_box` (4 px bigger each side so the old clip never shows), the box phase (`box_frames`; "all" is the brookie layout), `bg_start` and the `join` frame, and writes `probe.jpg`. Look at `probe.jpg` and write what it shows in `WORK/notes.md` (the box matches the posted frame; the join frame is the cut to him). → `WORK/_work/probe.jpg`.
2. **Read the clips.** Copy the closer spec to `WORK/_work/spec.json`, fill `posted`, `sources`, the probe numbers, and set its output folder to WORK (`out`; no `icloud`, no AirDrop key). Run `python3 -I ~/ob-editor/bin/trial_variants.py clips WORK/_work/spec.json`. It reports for each clip its speaker segments (read from the on-screen name labels), the follow card (a segment is cut before it, on a pause), digital silence and songs, the transcript, and a sheet per clip. Read every transcript against OB's line after the join. A clip that does not set that line up is dropped from the rotation; the delivery note says which and why. → `WORK/_work/clips_report` and the sheets, listed in `BREAKDOWN.md`.
3. **Decide the versions,** by the rule in the next section, and write `segments` and `variants` in the spec. Write `WORK/BREAKDOWN.md`: per version, the first 3 seconds (clips in order, speaker first, hook line), what is identical to the posted reel, and the mock stills for each opening (`trial_variants.py render ... ids` on one id for a still check, or `tmpl.py still`). A fresh `work-checker` agent reads it with the spec and the transcripts and must say PASS before the batch render (three rounds).
4. **Render.** After `render_slots.py list` shows a free slot: `python3 -I ~/ob-editor/bin/trial_variants.py render WORK/_work/spec.json` (about 30 s a version; it waits for other renders). Audio defaults the tool applies: every speaker normalised to one level (`seg_lufs`), boost capped at +6 dB, near-silent clips take `silent_fill` (the posted reel's own opening sound), a 4x limiter at -2 dBFS (a plain -1 dBFS limiter hit +1.1 dBTP after AAC). Leave them.
5. **QC.** `python3 -I ~/ob-editor/bin/trial_variants.py qc WORK/_work/spec.json` gives frames at every cut and at the join, loudness and true peak, quiet runs, black or frozen frames, the VMAF of the unchanged tail against the posted reel (it must match: the tail is untouched), and Whisper's text across each cut. Read the sheets and the cut text. → the tool's `qc` outputs under `WORK/_work/`.
6. **First 3 seconds differ.** `python3 -I ~/ob-editor/bin/first3_check.py WORK/out/V1.mp4 WORK/out/V2.mp4 WORK/out/V3.mp4 --json WORK/qc/first3.json` compares picture and sound of every pair. SAME fails the rule: change one opening and re-render. CHECK means look at both openings on a contact sheet (`frame_sheet.py VIDEO WORK/qc/open_V1.jpg 0.2 0.8 1.4 2.0 2.6`) and decide; write the decision in `warn_answers.json`.
7. **Music.** The posted reel's own audio plan carries over: if the posted reel had a bed, each version keeps that same track and level (the stem in WORK); if it had none, none is added. `music` for this route is optional. Someone else's clip never gets music or effects, and her voice never plays under his.
8. **Each version goes through the gate and the reviewer separately,** then `finish` once per version (Finish).

## Decisions that are yours
- **How many versions:** the number OB named; if he named none, three, each with a different first 3 seconds.
- **What varies:** only the opening: which speaker or clip comes first (rotations with each speaker first), the first line he says, and the first-frame picture. Everything else stays as the posted reel: the layout (box or full-screen), the clip trims the posted reel used (clips are not trimmed further; OB 11-09: "on videos, never touch the original clip ... only thing you can do to it is add me in the green screen"), no zoom, no speed change, no music or text on the clip.
- **Which clips:** those that set up his line after the join; a clip that does not is dropped and named.
- **Spoken-line versions** (new lines from raw takes): cut by the talking route; the earlier `make_variants.py` for the 1006 apple pie job (`/Volumes/T7/OB-EDITS/1006-TRIALS/_work/make_variants.py`, project copy, read only) shows the pattern but is not run.
- **Hook text on frame 1:** none over a creator's clip (11-09 original-clip rule). Text appears only on his own footage, in his words.
- **Follow cards and shots of the creator herself:** they stay out only where the posted reel already cut them.

## Traps
- **Same first 3 seconds** across trials (OB 10-20). Step 6.
- **Lines that do not follow the clip** (OB 10-20: "make sure they make sense to what im saying after the reaction"). Step 2 reads every transcript against his line.
- **Reacting to a repost** (OB 11-02). Originals only.
- **A clip played back and forth, slowed, boxed or zoomed.** The 11-09 rule forbids it; the old layouts with "zoom" versions are not used.
- **Peak overshoot after AAC.** The 4x limiter at -2 dBFS stays.
- **Trial pack for a new reel.** Not this route (OB 10-30).
- **Delivering to a phone folder, an AirDrop folder or the T7.** Never; `finish` only (OB 10-28: "no iCloud").
- **Notes on a video he already posted** (OB 10-30: "Stop I already posted it"). Check posting status first.

## Finish
Gate inputs for this route: the version file, the pieces its render recorded (`edges`), `warn_answers.json` (including the first-3-seconds answer). No recorded pieces? `subjects/qc.md`, "When the gate says there are no recorded pieces". The match of the unchanged tail against the posted reel is `trial_variants.py qc` (step 5), not a gate input. For each version: `python3 -I ~/ob-editor/bin/ob_job.py gate WORK WORK/out/Vn.mp4`; give the `video-reviewer` the file, the posted reel, `BREAKDOWN.md` and the first3 result; fix what it flags (three rounds at most); then `python3 -I ~/ob-editor/bin/ob_job.py finish WORK WORK/out/Vn.mp4 --to "trial n of <slug>, opening: <what differs>"`. Never `trial_variants.py page` or `deliver`. The delivery note lists each version's opening in one line, the clips dropped and why, and any one-clause factual conflict.
