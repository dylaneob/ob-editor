# OB Studio: design note (2026-11-07)

OB asked for "my own with you that looks like an editor so I can make changes and requests", laid out like the
editor chase_ai_ built inside Claude Code (TikTok https://www.tiktok.com/t/ZPLqesJ3j/). His final scope:
**music, sound effects, different beats and a timeline**, plus notes, requests and Send to Claude. No settings.
Instagram's Edits app is a look reference only (we never open or drive it).

## What chase's editor has (read from his frames)

Reference frames are saved in `ref/` (watch.py, balanced, 1024 px; t = time in his video).

| Frame | What it shows |
|---|---|
| `ref/chase_t00_layout.jpg` | Browser tab "Beat Review v2". Top bar: `chase_ai_  1102-1  picture 7de660a0  [UNVERIFIED]`. 9:16 video on the left, BEATS list on the right, transport + timeline strip along the bottom. |
| `ref/chase_t17_beat_list.jpg` | Header `BEATS 43 · 1:25.50`, then `5 beats changed last round: b02 b31 b32 b42 b43` (underlined links). Rows: `b01  0:00.00  You will struggle with front-end design` (mono id + time, bold spoken line). A red `Changed last round` tag under changed rows. Thin blue row rules, dark navy ground. |
| `ref/chase_t19_timeline_strip.jpg` | Bottom bar: `Whole video`, `Sound: with cues` (toggle), `Listening preview`. Under it the strip: numbered beat blocks (11, 12, 13 ...) in two blues, sound cue ticks with labels (`pop`, `pop-hero`). |
| `ref/chase_t61_tabs.jpg`, `ref/chase_sound_tab.jpg` | Right panel tabs `NOTES  CHECKS  ROUNDS  SOUND 21`. Sound tab: one cue per entry, `0:00.40 · es-pop-1 · -9.0 dB`, then one sentence on what it hits ("on 'struggle' the first tell ... lands"), and a `Note` button on every cue. |

Other things he says: every beat is a scene cut, a caption change or anything new on screen; "change beat 33"
re-renders only that beat; notes are per beat; a sound section holds the sound packs; you stay inside Claude Code.

## What OB Studio keeps, maps and adds

Side by side (left chase, right OB Studio):

- Layout: `ref/side_by_side_layout.jpg`
- Sound tab: `ref/side_by_side_sound.jpg`
- Timeline + notes with statuses after a run: `ref/side_by_side_timeline.jpg`

| chase | OB Studio |
|---|---|
| Top bar: name, picture id, UNVERIFIED tag | `OB Studio`, edit name, beat count, length, `picture <8 hex>` (changes with every new render), gate tag: `GATE PASS` / `GATE NOT PASS` / `UNVERIFIED` from `qc_gate`'s report for the exact file in the preview. Send to Claude sits at the right. |
| 9:16 video left | Same, a 720p proxy of the newest render (`beats/out/current.mp4` or the adapter's final, whichever is newer). 16:9 edits get a 16:9 stage. |
| BEATS list | Same header, same "changed last round" links, same rows (`b07  0:07.11  Ozempic did make her lose bone density. But`), her words in italics, what is on screen under the line, red `Changed last round`, a count of open notes, a `Note` button per row. Click a row: plays that beat from its start. |
| Tabs NOTES / CHECKS / ROUNDS / SOUND | Only **NOTES** and **SOUND** (OB). NOTES is the request list; SOUND is chase's cue list plus the music bed on top. |
| Transport: Play, prev/next, time · frame · beat, Note, Whole video, Sound: with cues | Play, ‹ ›, `0:16.40 · frame 491 · b12`, Note, `Whole video` / `Loop b12`, zoom − Fit +. "Sound: with cues" is dropped: the cues are baked into the mix, there is nothing to toggle. |
| Timeline strip: beat blocks + sound ticks | Three tracks only: **BEATS** (filmstrip thumbnails, beat number, a kind bar: OB on camera / her clip / board / CTA, orange top edge = changed last round, white outline = selected, blue dot = open notes), **SFX** (one tick per cue named by family, green = swapped), **MUSIC** (the bed, its drop-outs dashed, "no music" before it starts). Ruler on top; white playhead. |

Edits-app conventions used to fill gaps: the filmstrip on the video track, white selection outline, a white
playhead with a handle, tap a clip to act on it, a bottom sheet on the phone, pinch to zoom the timeline.

## The request loop (the core)

1. Tap a beat block, a sound tick or the music bar (or any `Note` button). The note sheet opens on that target,
   with its words, what is on screen and its sounds. Type the change, or tap a chip ("Make it punchier",
   "Cut this line", "Louder", "Drop the music here" ...). **Add note** puts it in NOTES as *Not sent*.
2. **Send to Claude** turns every *Not sent* note into *Queued* in `beats/requests.json` (one round number per send).
3. Claude reads them (`studio.py requests <edit>`), marks each *Claude working*, makes the change, re-renders,
   marks it *Done* with a one-line reply (`studio.py mark <edit> <id> done --reply "..."`).
4. The page polls every 2 s: statuses update, the new render is picked up, a new proxy is cut, and the preview
   reloads at the same time position. Beats from the latest finished round get the orange edge.

Mechanical requests run straight from the page, through beats.py, one job at a time:
- **Redo bNN** (beat sheet): `beats.py redo <edit> NN` (re-render only that beat's frames, encode, gate).
- **Swap to** (sound sheet, with a play button per library sound, same family first): `beats.py sfx <edit> NN swap <idx> <file>`
  (audio remix + mux, picture untouched; gate on the last swap).
Press **Render (n)** in the top bar or the NOTES tab; progress and the beats.py log show while it runs.

## Rules it keeps
- Writes only inside the edit's beats folder (`requests.json`, `studio/` cache, beats.py's own outputs). Never touches
  AirDrop, READY or any delivery folder. Delivery stays manual, after the gate.
- Localhost only (127.0.0.1:8765). No external services, fonts or scripts. No em dashes in UI text.
- Proxy builds and renders wait on `render_slots` (one heavy job at a time).

## Long-form (2026-11-08): every finished YouTube edit opens here for OB's notes before the final
`python3 studio.py serve longform:<project>` (project keys in `bin/beats_adapters/longform_projects.json`; launch entry `ob-studio-longform`, port 8767)
opens an `assemble.py` edit. Beats are every cut, graphic/card entrance and spoken-line change (a graphic leaving is not a beat), numbered across the
video and grouped by chapter: the BEATS list has a header per chapter (current one open, others collapsed, jump links under the title), the timeline
gets a CHAPTERS lane above the beat lane, the music lane names the track per chapter, and the beat list loads its stills lazily from a 540p proxy
(`/thumb/<picture>/<beat>.jpg`, cut on first request). Redo = re-render only that beat's pieces, re-encode only its chapter segment, join the segments with
stream copy, copy the audio; sound swaps remix audio only (`-c:v copy`). A project opened with `readonly: true` (the delivered edit) takes notes but not redo.
Details and the proof it leaves in the log: top docstring of `bin/beats_adapters/longform.py`.

## Files
- `studio.py` server + CLI (`serve`, `requests`, `mark`, internal `lanes`)
- `index.html` the whole UI (no build step, no libraries)
- `ref/` chase frames + side-by-sides; `shots/` headless Chrome checks (desktop 1440x900, phone 390x844)
