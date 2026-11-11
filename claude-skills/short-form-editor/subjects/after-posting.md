# Subject: after posting (reading how an edit held viewers)

Use it when: OB says a video is posted, asks "how is it doing" or "how is it holding", or a job's STATE entry says a read is due 48 hours or 7 days after posting. Also read the route file of the format being read (`routes/long-form.md`, `routes/short-form.md`, ...), because the lesson is written back into it.

## The rule and why
The editor's job is that viewers stay and the right ones book a call; the audience's curve is the judge, not the editor and not OB (OB 10-18, the brief: edit "for retention and booked calls, not just a clean cut"). So every posted edit is read twice: **48 hours** after posting (a first look) and **7 days** after (the read that counts). YouTube finishes a day's detail 2 to 3 days late, so the 48-hour read is partial and says so; the day-7 read is the one that changes rules.

The read produces three lines for OB: where it held, where it dropped and why, and the one rule that changes (or "no change, one video is a clue"). It never changes a published video. Titles, thumbnails, A/B tests and anything on his channel are his word only.

## What to pull

**YouTube long form** (read only; the sign-in is `~/.config/ob-youtube`, never print it):
```bash
PY=~/ob-youtube/.venv-google/bin/python
$PY ~/ob-youtube/yt_analytics.py check                      # sign-in ok? channel and last 28 days
$PY ~/ob-youtube/yt_analytics.py pull --only VIDEO_ID       # writes ~/ob-youtube/data/retention/VIDEO_ID.json
$PY ~/ob-youtube/yt_report_card.py card VIDEO_ID            # opening card, from day 3 (words said at the biggest drop)
python3 -I ~/ob-youtube/retention_study.py video VIDEO_ID --events WORK/events_resolved.json
```
If `check` says the sign-in expired, stop the read and tell OB in one line to run `yt_analytics.py auth` (a browser sign-in only he can do). The curve file holds about 100 points (on a 9-minute video one point is about 5.5 s), the relative-retention curve, and the key numbers. `retention_study.py video` lines the curve up against the events that were on screen (`WORK/events_resolved.json` of that edit) and lists dips with the loss rate before and after each event. For several videos at once: `retention_study.py types EVENTS_MAP.json` (its docstring gives the map format) pools "holds / loses viewers" by event type.

**Reels** (Instagram gives a skip rate and an average watch time, no curve):
- The pull: `~/ob-ig-insights/data/latest.csv` (columns `reels_skip_rate`, `ig_reels_avg_watch_time`, `age_days`, `views`, `is_shared_to_feed`, `kind`). A row marked "too new to tell" is not read yet.
- Log the read: append one row to `~/ob-brain/feed/skip_rates.csv` (columns `date,shortcode,series,opening,skip_rate,avg_watch_s,length_s,views,trial,note,camera,background,outfit,music`; `opening` is the first-seconds version in words; `trial` is `yes` or `no`), then `python3 ~/ob-brain/build_brain.py`, then `python3 ~/ob-brain/brain.py skip` to see the table by opening version.
- Feed reels and trials are never mixed in one comparison (OB's standing split). Compare a reel only with reels of the same series and the same `trial` value from the last 30 days; the baseline for hooks is `~/ob-editor/presets/PROVEN-OPENERS.md` (6,130 reels: associations, not causes).

## How to read it

1. **Line the curve up with the edit.** For each dip and spike name what was on screen in the 8 seconds around it (a card, a clip, a flash, a long face-only stretch, a look-down, a music change) and the words he was saying. The report card gives the words at the biggest drop; `events_resolved.json` gives the picture. A dip with nothing on screen to explain it is a content dip (the sentence), not an edit dip; say so.
2. **Compare with the right yardstick.** The leak is the first 20 seconds: on his 124 readable curves the biggest drop starts before 0:30 (median 0:09, about 20 points) and 58% of everyone who leaves is gone by 1:00. Judge the opening at day 7 by relative retention at 0:15, 0:30 and 1:00 against the median for the video's Browse share:

| Browse share | 0:15 | 0:30 | 1:00 |
|---|---|---|---|
| under 40% | 0.43 | 0.48 | 0.55 |
| 40 to 60% | 0.43 | 0.46 | 0.52 |
| 60 to 80% | 0.38 | 0.41 | 0.46 |
| 80% and up | 0.34 | 0.35 | 0.41 |

Above the band at 1:00 means the opening did its job. Do not use "lose under 25% by 0:30": 110 of 124 videos miss it. Also give the 30-second and midpoint numbers against his last 10 long-form videos (`retention_study.py summary`). After 2:00 the typical cliff is 2.3 points and the slide 1.8 points a minute, so pacing changes there can only move a small part of the loss.
3. **Check the packaging before blaming the cut.** A low start with a weak thumbnail click-through is a packaging problem. Thumbnail CTR comes from `~/ob-youtube/yt_reach.py` and the Studio A/B test result about two weeks after publishing (`python3 ~/ob-youtube/yt_demand.py test-result` records it; its docstring has the arguments). Packaging is the `/youtube` skill's job; report it, do not fix it here.
4. **Booked calls.** `~/ob-youtube/yt_weekly.py` groups Calendly invitees from the last 28 days whose link carried `utm_source=youtube` by video. Say how many calls came from this video when the week's page shows it.
5. **What is noise.** Many of his videos have 150 to 900 views and the spread after Browse share is 0.09 at 1:00. A gap under 0.08 at 1:00 between two openings is noise at his n.

## When a lesson becomes a rule
- **One video is a clue.** Write it as a dated block in `~/ob-editor/STATE-youtube.md` (video id, the dip or hold, the event, the line said, the numbers). Do not touch the route file.
- **Two videos showing the same thing** (same event type, same direction, from `retention_study.py types` or two day-7 reads) make an editing rule. Add it to the route file's Decisions or Traps as one line with both video ids as evidence, backing up the file first (`cp routes/long-form.md routes/long-form.md.bak-YYYY-MM-DD`) and then `python3 -I ~/ob-editor/bin/skill_lint.py`.
- **An opening rule** (the first minute) is locked only with at least 10 uploads on each side in the same Browse band and a gap of 0.08 or more at 1:00. Until then log one change per upload: the BRIEF.md of that edit names the opening type, the second the title's subject is named, the second of the first payoff and the change tested; the day-7 read adds Browse share and relative retention at 0:15, 0:30 and 1:00. The one measured edge so far: saying what the video gives the viewer, in concrete words, inside the first minute (+0.04 at 1:00, below 70% Browse). When the first payoff lands (0:20 or 0:40) showed no difference.
- **A number** (a cap, a level, a limit) changes only in `~/ob-editor/qc/formats.json`, with OB's words and the date in its `_why`. A retention result alone is not OB's word: log it and tell him; the file changes when he says so.
- **The ledger** (`ledger.py add`) holds what OB said. A retention lesson is not his note, so it does not go there. When he reacts to the finding, his words go in the ledger as in `subjects/qc.md`.
- **The gold set** (`~/ob-editor/qc/gold.json`) records what OB approved. A video that held well but that he did not praise is not an exemplar. If it already is one, add the posted numbers (day-7 relative retention at 0:30 and 1:00, average view percentage) beside its entry, so the bar says what the audience did.

## Reading the read back
At the start of every long-form job the route's step 3 uses the saved curves and the clue list in `STATE-youtube.md`. At the end of every read, log it in `STATE-youtube.md` (video id, date read, day 2 or day 7, the three lines given to OB, any rule written) so the next edit can find it.

## Traps
- Reading at 48 hours as if final: the numbers are partial; mark the block `partial` and read again at day 7.
- Blaming the edit for a packaging miss, or the reverse: step 3 first.
- Calling one video a rule: the write-back rules above.
- Mixing feed reels with trials, or reels of different series: compare like with like.
- Telling OB the cut "worked" from loudness, scopes or a clean gate: those prove the technical side only. The curve judges.
- Pulling anything with a stale sign-in and reporting an empty curve as a result: `check` first.
