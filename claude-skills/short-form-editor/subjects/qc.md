# Subject: the gate, the reviewer and OB's notes

Read with every route. OB 10-28: "have quality control and a loop of upgrades so you dont make the same mistake twice". OB 11-10: "I want this to make no more mistakes short form and long form". He is never the verifier: the gate and a fresh reviewer pass the exact file before he sees it.

## How the gate decides

- **The verdict belongs to one exact file**, named by its SHA-256. Every run is kept in the QC folder's `runs/` directory. For each check the verdict is the latest run in which that check really ran, so a later run with fewer inputs cannot erase a FAIL. A re-render is a new file and starts from nothing.
- **Required checks.** The route in `~/ob-editor/qc/formats.json` lists them. A required check that did not run is a FAIL that says what to pass. It is N/A only where the route says so, or where the job declared it at `start` with a reason (no script, no separate mic, music none quoting OB, no sound effects).
- **WARN means look.** Open the frame or the stretch of sound it points to, then answer in `WORK/qc/warn_answers.json`: `{"check name": "what I looked at and why it is fine for this file"}`. An answer older than the run is stale. "Known" or "same as last time" is not an answer.
- **FAIL means fix the cause**, render again, gate again. An override lives in `WORK/qc/gate_overrides.json` as `{"CHECK": {"why": ..., "ob_words" or "proof": ..., "date": ...}}`: `ob_words` is his exact words, `proof` the frame or time that shows the check is wrong on this file. Nothing else overrides, and every use is logged.
- **Records.** The route also requires decision files (music candidates, sound plan, assets manifest, breakdown, format check, reaction windows). A missing record blocks delivery like a FAIL: it is how the gate knows a choice was made and not defaulted.

## Commands

```bash
python3 -I ~/ob-editor/bin/ob_job.py status WORK
python3 -I ~/ob-editor/bin/ob_job.py gate WORK FILE
python3 -I ~/ob-editor/bin/qc_route.py verdict FILE
python3 -I ~/ob-editor/bin/qc_route.py problems FILE --work WORK
```

- `status`: every required check and record as done, missing or stale, with the next command.
- `gate`: runs every check with every input it finds in `WORK/job.json` and WORK. Use it in place of a bare `qc_gate.py FILE`.
- `verdict`: the per-check verdict for that file across all its runs.
- `problems`: everything that still blocks delivery, one line each with the fix. Empty output means `finish` will deliver.

## The reviewer

1. When the gate has no FAIL, call the `video-reviewer` agent. Its brief is the file path and the WORK path, nothing else. Do not say who made it, what you fixed, or what to look at: a reviewer who is told the story checks the story.
2. It looks at contact sheets, the transcript, the levels, the records and the approved exemplar for the format, against `~/ob-editor/qc/REVIEW-CHECKLIST.md` (lines R01 to R30). It answers `VERDICT`, `FILE`, `SHA256` and one line per problem.
3. The app records that verdict for that file hash in the QC folder's `reviews/` directory. `finish` reads it. A PASS for an older render does not count.
4. Fix what it flags at the cause, gate again, call a new reviewer. Three rounds at most. If it still fails, tell OB exactly what is wrong: the file, the time, the line id.
5. Never review your own render. Never argue with the reviewer in its brief. If a checklist line is wrong, change the line with OB's words and date, then review again.
6. Anything that is not a video (a script, a caption, a number, a tool change) goes to the `work-checker` agent the same way.

## When OB gives a note (the never-again loop)

His note is the most valuable thing in the job. The same day:

1. Fix it in the edit he saw.
2. Write it in the ledger in his words:
   ```bash
   python3 -I ~/ob-editor/bin/ledger.py add --said "his exact words" --date YYYY-MM-DD --rule "the rule" --check CHECK --routes ROUTE --enforcer gate:CHECK
   ```
   Enforcers: `gate:<check>`, `record:<name>`, `review:<R##>`, `hook:<name>`, `engine:<file>`, or `route:<file>` (prose only: the weakest).
3. Make the check catch the file he saw. Run the gate on that file: it must FAIL for his reason. If it passes, the check is not done.
4. Plant it: a short clip that shows the mistake in `~/ob-editor/qc/regress/`, listed in `fixtures.json` with `must_fail`. Then `python3 -I ~/ob-editor/bin/qc_gate.py --selftest`.
5. No code can check it yet: add or tighten a line in `~/ob-editor/qc/REVIEW-CHECKLIST.md` and point the ledger at it (`review:R##`). The second time he gives the same note it must become a code check, that day.
6. `python3 -I ~/ob-editor/bin/ledger.py coverage` must exit clean: no active rule without an enforcer.
7. A number changes in `~/ob-editor/qc/formats.json`, never in prose. A route or subject file changes only when the editor must act differently. Then `python3 -I ~/ob-editor/bin/skill_lint.py`.
8. When his new words replace an older rule: `python3 -I ~/ob-editor/bin/ledger.py supersede M## --by "OB <date>: his words"`. His latest words win.
9. One pointer line in memory (`_index-content-edits.md`) and the STATE file.

## When OB praises something

That render is now the bar for its format. Add it to `~/ob-editor/qc/gold.json` under `formats`: `exemplar_path`, `approved_on`, `ob_words` (exact), `grade`, and `metrics` measured from that file's gate run (`qc_route.py verdict FILE`: loudness, sound effects per minute, music under voice, events per minute). Measure, never estimate. If the bar moves a number, change it in formats.json for that route. The reviewer compares every later render of the format with it (R30).

## Mocks and previews

A mock, preview or test clip starts on the `mock` route: `python3 -I ~/ob-editor/bin/ob_job.py start mock WORK --camera CAM.MP4 --mic MIC.wav (--script F | --no-script "why")`. Build it from the raw take, never from a posted render (that inherits its cut-offs, M27). It gets the same gate and the same `video-reviewer` as an edit. It goes to OB in chat only when `python3 -I ~/ob-editor/bin/qc_route.py problems FILE --work WORK` prints nothing. It is never delivered as a final.

## Self tests

Run them after touching a check, the ledger, formats.json or any skill file:

```bash
python3 -I ~/ob-editor/bin/qc_gate.py --selftest
python3 -I ~/ob-editor/bin/qc_route.py --selftest
python3 -I ~/ob-editor/bin/ob_job.py --selftest
python3 -I ~/ob-editor/bin/qc_audio.py --selftest
python3 -I ~/ob-editor/bin/qc_assets.py --selftest
python3 -I ~/ob-editor/bin/skill_lint.py
```

Every planted mistake must still fail and the clean clips must still pass.

## Traps

- A second gate run with fewer inputs used to replace a failing report. Runs are now kept per file, but pass every input anyway: `ob_job.py gate` does it for you.
- WARNs used to ship unread on most deliveries. Each one now needs an answer about this file before `finish` will deliver.
- Long videos used to skip the cut-off-word check. `gate` now builds the pieces from the cut list; if it says the pieces are missing, that is a FAIL to fix, never one to waive.
- A brief that banned client photos made a helper override the clients check. Briefs come from `python3 -I ~/ob-editor/bin/ob_job.py brief WORK`; check a hand-edited one with `python3 -I ~/ob-editor/bin/ob_job.py lint-brief FILE`.
- `OB_QC=0` is for throwaway test renders in scratch. Anything that leaves WORK goes through the gate.
- "The check is wrong" is a claim to prove. Put the frame or time in the override and fix the check in the same session, with a fixture, so nobody needs the override twice.

## When the gate says there are no recorded pieces

The cut-off-word check and the lip-sync check need to know which piece of the source plays where in the file. Most engines record it when they render. A build script you wrote yourself, `assemble.py`, `lecture_render.py`, `tier_render.py` and `trial_variants.py` do not. Record it yourself, then gate again:

```bash
python3 -I ~/ob-editor/bin/ob_job.py pieces WORK FILE WORK/qc/segs.json --cam WORK/qc/cam.json
```

- `WORK/qc/segs.json`: one row per piece of his voice, `[source file, start s, end s, where it plays in FILE s]`, written by your build from the cut list it used, never typed from memory.
- `WORK/qc/cam.json`, when his voice comes from a separate mic: one row per piece of his picture, `[camera file, start s, end s, where it plays in FILE s]`.
- A re-render or a new mix is a new file: `music_pick.py mix` carries the record over; anything else, record again.
