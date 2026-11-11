> SUPERSEDED 2026-11-10: the rules for this format now live in `~/.claude/skills/short-form-editor/routes/yt-clips.md`.
> Where this file disagrees, the route file and `~/ob-editor/qc/formats.json` win. Kept for history only.

# Preset: YouTube long-form -> Instagram reels (the clipper)

Built 2026-10-28 for OB ("way better than ob-moments ... an automatic flow"). Tool: `~/ob-editor/bin/ytclip.py` (+ `ytclip_pic.py`, `ytclip_yt.py`). First batch: C4372 "How America Got Fat", work folder T7 `OB-EDITS/2026-10-28-yt-clipper/` (`STUDY.md` has the evidence, `picks.json` the reels). The short-form PRESET and the editor skill's rules all apply; this file holds only what is specific to clips.

## 11-04 rebuild (Mac mini, OB: "Rebuild it"). These rows win over the 10-28 ones below where they differ
The look lives in `ytclip_look.py`; `ytclip.py` calls it for mock, render and qa. Backup of the old tool: `ytclip.py.bak-2026-11-04-prelook`; old preset: `PRESET.pre-1104.md`.

| What | Value (11-04) |
|---|---|
| Split (M40, `styles/dylan-page-split.md`) | Seam at y 876: the top panel is 1080x876, and he sits under it, chest-up, from a 2234x2160 4K crop centred on his face. A receipt goes up for each claim he makes, with no stock footage. Captions sit at y 836, label at y 742, credit at y 236 (it moves off any face in the footage). |
| Receipts | Kinds: video, photo, doc, count, bars, versus, study, quote. Doc receipts are the page's own pixels: only the highlighted lines, each cut to its text line, split at word gaps, scaled to about 56 px glyphs, with a yellow marker sweep. Never retype a page with OCR (on 11-04 it misread "weapon" and "a drink"). A receipt holds 2.5-6 s and stops at a clip, a turn line or the closer. A gap under 1.2 s holds the receipt, and a blip under 0.5 s is absorbed. Moves rotate drop, slide, push/blur and cut. |
| On screen (M37) | He is on screen every frame he talks. A look-off edge is covered by the split (the previous receipt), never by a cutaway or a text-only card. |
| Backgrounds (M38) | Never black: his own studio, frosted and warm, with a dot grid. |
| Full frame | 9:16 face crop with 108% alternation. The label sits at chin + 100 (clamped 1180-1380), captions at chin + 92 (1250-1460), or under the label while it is up. |
| Horizontal clips | 3:4 over their own blur, captions at y 1350. |
| Joins (M44) | At most 0.15 s at a join (`tighten_joins` after `breathe`). The line ends 40 ms after the last word. M26 still wins: never cut a word. |
| One file (M45) | One finished file per reel (`versions` = [F]), with no trial packs and no phone copies. Delivered as `{n} {Short}.mp4` through `deliver`. |
| Lip sync (M36) | `qc_gate.after_render(..., cam=look.cam_map(K))` measures every piece. |
| Transcribe | whisper large-v3-turbo, always `-l en`. |
| Render | Parallel chunks: 6 workers (`ytclip_look.py chunk`, x264 crf 16, 4 threads each), joined with `-c copy`, AAC 256k. Scratch goes in `~/ob-scratch/ytclip/`. The whole render counts as one slot in `render_slots.py`, and `--yield` waits for 9 quiet polls (3 min). |
| Source audio | The C4372 voice master and mic16 moved to OB-ARCHIVE `OB-EDITS-WORKING/C4372-seed-oils-source/voice-synced/` (11-04). `clipper.json` points there. |

## The rule (rico.incarnati's "appetizer rule", OB's reference)
Every clip stands on its own (one whole takeaway) AND leaves them hungry: it ends on one of his own open-loop lines, and the post caption names the YouTube video. OB 10-28: no on-screen YouTube chip (call 2B). Always under 1:30 and never forced (OB 10-29: "make the reel clip from youtube alwasy under 1:30 mins, if it doesnt go well no need to clip, dont force it if its not good or a complete stand alone clip"): a video with no part that stands alone and is good gets no clip, and 5 picks is a ceiling, not a quota. `ytclip.py cut` stops any reel at 90 s or more (M33).

## The flow (one command per stage, all re-runnable)
1. **Source**: the long-form edit's own decisions: the 4K camera concat, the 48 kHz voice master, the cut list (only takes it kept, so no "cut that, Claude"), events_resolved.json (its graphics), hf/assets. Archive the raw camera + MOTIV to OB-ARCHIVE first.
2. **Pick** (Claude writes `picks.json`):
   - Each reel is lines in play order (`text` = what he said, `near` = the source second).
   - The data gates: read the Content Lab RULEBOOK + NEXT-TESTS, `brain.py drivers`, `engines` and a `dossier` per topic, and the video's retention curve (`yt_analytics.py pull --only ID`).
   - Prefer DEFENSE/AUDIT moments (reach 1.26/1.29x), steps (1.18x), GLP-1/supplements (shares), and a number in the first line (likely +109% reach).
   - Skip lines that need the video ("from the start of this video") and claims he misstated.
   - Only moments that stand alone as one complete, good clip. If none do, pick none (OB 10-29, M33).
3. **cut**: Apple words per stretch, then the long-form's kept takes, then zero dead space (`zero_dead.cut_words`), then `refine_edges`:
   - soft onsets above the room are kept: the "s" of "steroids", the "A" of "And"
   - trailing room noise goes
   - a 0.45 s silent prop beat comes before the first word
   - the voice is mastered with `voice_master`
   - never cut him off (M26, OB 10-28 twice: "stop cutting me off when im saying a word"): the reel's first and last edges go to whole sentences inside a real breath (`moves.snap`). Every other splice edge with his sound right outside it moves out to the nearest real pause, by the gate's own test, at most 0.2 s (`breathe`). Two lines that meet in the source play as one stretch, with no fade and no check. When a line's sentence really starts earlier (he ran straight on), the line's `text` gets those words: R1 "Soon,", R2 "Then there was", R5 "And here's my hot take."
   - checks: the word diff against `text` (every CUT-RISK word heard again on its own), silence of 3% or less with no gap over 0.2 s, and the gate's edges check on the cut voice with every piece (`cut.json` "segs"), so a chopped edge fails before any render. The render passes the same segs to `qc_gate.after_render`.
4. **lookoff**: his eyes at every cut edge. Each flagged edge gets a 0.5-0.7 s cover: the chest card going full screen, his words big, or, near a horizontal clip, that clip in the split with his words under it. A split B-roll doesn't hide him, since he's under it, so only full cards and vertical B-roll count as covering an edge. The same card again within 1.5 s holds through instead of flashing.
5. **mock** + **page**: a still per shot and frame 1 of every version, from the same compositor as the render. OB OKs it before any render (HARD RULE).
6. **render**: the body renders once, frame 1 per version, they're joined and the voice is muxed. It waits for other sessions' renders. Clips are lower priority than his YouTube videos and short-form edits (OB 10-28: "this is the lowest priority so queue it behind the more important ones"), so run `ytclip.py render WORK --yield`. That sets nice 19 for it and its ffmpeg, and it waits for 3 minutes with no other render before every step, so it never slips into the gap between another session's steps.
7. **qa** (ship only on PASS):
   - the words (0 CUT-RISK), silence, -15 to -13 LUFS, true peak -1 dBTP or lower, 0 flat tops
   - motion: live 8.6 or more, the first move by 1.5 s, 0 flashes
   - frame-1 face under 8%, the first 0.5 s under -15 dBFS
   - no text near his face, every 0.5 s (in the split: his head, cap included, under the seam captions)
8. **deliver**:
   - into the T7 `AIRDROP ...` folder, with 720p previews over 30 MB
   - `POST-NOTES.txt` (captions)
   - `manifest.json` (the loop's record)
   - a `_PREDICTIONS.csv` row per feed post
9. **review** (Mondays):
   - finds the posted clips in the Content Lab by transcript
   - shows each against its month (trials and grid apart), against its prediction, and which opening won in each pack
   - counts YouTube views from Instagram
   - proposes rule changes and changes nothing by itself

## Locked values (2026-10-28)
| What | Value |
|---|---|
| Canvas | 1080x1920, 30000/1001. A 4K crop of 1215x2160 around his face. Every other cut is 108% zoomed about his eyes, so the cap stays in. |
| Captions | 3 words with the live word yellow, centred at y 1428. A quote plate stands in for them while it shows. |
| Cards | Chest cards (facequote, stamp, pills, checklist, split) sit between chin + 36 and the captions. Full-frame cards (num, versus, stat_bars, study, doc, photo_full) last 2.5 s at most. A vertical video in side bars fills the frame. |
| Split (OB 10-28: "for the horizontal clips do the 50/50 split screen formats like dylan paige"; `styles/dylan-page-split.md`) | Horizontal B-roll and clips go in the top half (1080x960). They fill it edge to edge with no divider: TV lower thirds are trimmed, not cut mid-word; a wide graphic keeps its full width over its own blur; a title too small to read is rebuilt at 76 px or more (`clipper.json` "split" per file). He sits chest-up under it: face box 332 px, cap top at y 1025; the full frame's 108% shots go to 93%. Captions are centred at y 930, just above the seam. The source credit sits top left at y 236, or bottom left when a face in the footage is there. Footage is always on top, never mirrored. Where his face can't show (a look-off cover, or a clip playing its own sound), his words fill the bottom half instead. Each new appearance of a B-roll picks up where it last stopped. |
| Frame 1 | Never the big-face crop. It shows no face, his 16:9 frame small, or him + the source, under a 2-line title from his words, until the first cut after 1.8 s. |
| Trial pack | Feed master + T1-T4. The pack changes ONE lever (half with it, half without), and every version has a different first 3 s. Post at most 3 per burst, 10+ min apart. |
| Length | 40-60 s (20-39 s drags follows 0.76x and saves 0.77x); never 1:30 or more (OB 10-29, M33). |
| Audio | No music baked in (he adds sound in the app). -14 LUFS, never a hard clip. |
| Brand | Titles and captions from his own words, first person, no "free", no em dashes, no YouTube-only wording on Instagram ("link in the description"). |

## Learned (each rule needs 2+ videos before it locks; 1 is a clue)
- (empty: the first packs post after 2026-10-28)
