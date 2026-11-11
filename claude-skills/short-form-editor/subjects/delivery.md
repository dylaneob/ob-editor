# Subject: where files go and how a job ends

Read with every route. One file per edit reaches OB, through one command, only when the gate and a fresh reviewer have passed that exact file.

## Where work lives

- `ob_job.py start` creates WORK and checks the drive. Work goes in `~/ob-work/<job>` or `/Volumes/OB-ARCHIVE/OB-EDITS/<job>/WORK`. Scratch goes in `~/ob-scratch/`. `start` refuses a folder on the T7 and a drive without the free space the config asks for: the T7 ran out of space mid-job on 11-10. Reading footage and banks from the T7 is fine.
- WORK holds `job.json`, `STATE.md`, `BREAKDOWN.md` and the folders `audio/`, `story/`, `qc/`, `plan/`. Every step of a route leaves its proof there.
- Save each finished piece as it lands. Write two lines to `WORK/STATE.md` after each step (done, next) so a restart or a compaction loses nothing.
- Before each render: `python3 -I ~/ob-editor/bin/render_slots.py list`. At most three heavy jobs run at once across every tab (renders, frame scans, matting, transcription). Wait for a slot; do not start a fourth.
- WORK is never deleted. Clearing space is OB's call.

## Finish

```bash
python3 -I ~/ob-editor/bin/ob_job.py finish WORK FILE --to "what it is"
```

- It runs a fresh strict gate if the file changed, then lists everything that still blocks delivery: FAILs, required checks that did not run, WARNs without an answer, missing records, no reviewer PASS for this file. Each line says the fix. Fix them and run it again.
- When nothing blocks, it copies the one file, byte-checked, into the first delivery root with room, in a folder named by the route (`AIRDROP <what> (<date>)` for short form, `UPLOAD <what> (<date>)` for long form), logs it in `~/ob-editor/qc/deliveries.log`, prints the delivered path and writes `WORK/DELIVERY.md`.
- **One file.** No second copy for the phone, no voice-only copy, no variant pack, unless OB asked for one by name. Stems stay in WORK.
- **Never by hand.** The app blocks `cp`, `mv`, `ditto` and `rsync` of a video into a delivery folder, and blocks sending a video in chat while it has open problems. Do not look for a way round it: the block is the rule working.
- A mock or preview goes to OB in chat with SendUserFile once `python3 -I ~/ob-editor/bin/qc_route.py problems FILE --work WORK` prints nothing. Mocks run the `mock` route and the same gate and reviewer.
- A raw take or a reference video he asked to see is not an edit. Allow that one file first: `python3 -I ~/ob-editor/bin/ob_job.py allow-send FILE --why "OB asked to see the raw take"`.
- The old command (`deliver.py FILE --to FOLDER`) still works for jobs started before this loop, until the date in formats.json (`enforce.legacy_until`), and prints a LEGACY notice with the open problems. New jobs use `finish`.

## What you tell OB

Short, in this order:

1. The file, as a link he can click, and what it is in one line.
2. What was checked: the gate result and the reviewer's PASS, with the round it passed on.
3. Music: the pick and the runner-ups by name, in one line.
4. One clause for a real factual conflict in something he said on camera, if there is one. It never held the edit.
5. Anything not verified, said plainly. `WORK/DELIVERY.md` lists it.

No option menus, no approval questions, no compliance notes, no list of concerns. OB 11-09: "just do what i tell you". If the reviewer still fails the file after three rounds, say exactly what is wrong (file, time, checklist line) and what you tried; do not dress it up as done.

## After delivery

- Log the delivery in the running notes: `~/ob-editor/STATE-short-form.md` for reels and ads, `~/ob-editor/STATE-youtube.md` for YouTube. One entry: date, file, WORK path, route, music used, open items.
- Posting, uploading, going public and deleting are OB's word only. A YouTube upload stays private or unlisted until he says public. Title, thumbnail, description and pinned comment come from `/youtube` and `references/youtube-thumbnails.md`.
- 48 hours and 7 days after he posts, read how it held viewers: `subjects/after-posting.md`.
- A note from him on the delivered file starts the loop in `subjects/qc.md` (fix, ledger, check, fixture) and a new render through `gate`, the reviewer and `finish`. Never patch a delivered file in place.

## Traps

- A long-form file once reached its UPLOAD folder by a hand copy with a failing gate and no log line. Only `finish` delivers.
- Extra copies (a phone copy, a voice-only copy) gave him more files to sort than edits. One file.
- A delivery folder picked by hand landed on a full drive. `finish` picks the root; do not pass a path on the T7 as WORK or as output.
- A mock sent to chat before the gate carried a cut-off word. Mocks are edits: same gate, same reviewer.
- A re-export "with one small fix" was sent without a new review. A new file has a new hash: gate it and review it again.
