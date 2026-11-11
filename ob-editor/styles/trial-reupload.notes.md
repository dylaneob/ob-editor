# Trial re-upload edits: OB's notes (2026-10-18)
- No black box, no blur. The original stays fully visible ("the original got views").
- Hook text: white, heavy, black outline, no box. Never on a person (Vision masks + 22 px) or on the original's words. 3.5 s. No clear spot = no text.
- v1: 1.1x (atempo) + 1.05x center zoom + text. v2: his filmed hook, cut out, over his old cutout on the held first frame, then the original.
- v2 body starts at the FIRST MEAL, not at 0 (OB 10-18: "i repeat myself... cut straight to the first meal being shown"). Cut on the original's own scene cut into the first meal; prove 0 clipped words (frame pair, 5 ms levels, voicing of any sound right before the cut, Whisper on the result). QC: `scripts/qc_v2.py RANK` (hook word-for-word + first words after the join + join frames), then `scripts/qc_batch.py`. The held frame under his hook must not show a karaoke caption word (rank 5's "WHAT" dangled; frame 0 was clean, `V2_HELD_T`).
- Grade for iPhone takes: W2 default (make_grade warm set) until he picks.
- Master: two-pass linear loudnorm -14 LUFS (TP -2) + alimiter 0.708 + aac_at 192k (`render_final.master`). Plain loudnorm + native aac overshot to +0.2 dBTP; the sped originals clipped at +2.3 dBFS before mastering.
- Selfie hooks don't match seated old cutouts: ask for desk-framed hooks (phone back, arms in frame).
- Home: T7 `OB-EDITS/TOP100-TRIAL-REUPLOADS/` (BATCH folders + `_work`). Batch runs: `_work/scripts/batch2_run.py` (resumable, titles in `_work/batch2/v1_titles.json`, HOLD list for money claims / crude openers / mocking a professional / unconfirmed client results). Encoder: `render_final.ENC_VT` (h264_videotoolbox 12M) when the Mac is loaded.
