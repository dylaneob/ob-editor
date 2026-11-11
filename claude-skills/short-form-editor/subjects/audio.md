# Subject: sound (his voice, music, sound effects)

Read it on every route. Every number (levels, caps, windows, counts) is printed by `ob_job.py start` and lives in `~/ob-editor/qc/formats.json`. This file is the method.

**The rule.** His voice only gets better. Music and each sound effect are chosen for this cut from scored candidates in the indexed bank, placed against the picture and his words, then measured in the finished mix. Nothing is defaulted, reused or made by us. OB 11-10: "the best everything, music, sound effects, not just doing th easiest and fastest".

## What stands in for ears
You cannot hear. A pick needs all three stand-ins:
1. **Earshot** (always the wrapper `~/ob-editor/bin/earshot`): `describe FILE` gives mood tags, `rank "a sentence" FILES` orders by fit, `compare FILE --refs TRACKS` gives distance to tracks he picked or hated, `realness FILE` tells a recording from a synthetic sound.
2. **Measurements** from the index and the stems: loudness, beats, key and mode, energy per section, energy in his speech band, each sound's peak time.
3. **One speech model on the voice stem and on the finished mix.** A word the stem has and the mix lost is masking you can prove.

Weak spots: a tag is a model's word, not his ear. A transcript proves a word is audible, not that the song suits him. So the taste anchor (Traps) is part of every score, and the delivery note says what was measured and calls the rest "not verified".

## The voice
- **Source:** the external mic file. Never camera audio or a 16 kHz copy.
- **Reels and ads:** `python3 -I ~/ob-editor/bin/voice_master.py master IN.wav OUT.wav --lines EDL.json` (`takes.py ... --voice OUT.wav --master` runs it). It levels each line, then limits gently; it never hard-clips. If the target would need hard limiting, it goes quieter.
- **Long form:** the mic through the render's loudness pass only. No compressor and no de-esser: a generic "pro chain" makes him worse. `voice_polish.py` (a clarity EQ) stays off unless he asks for it.
- **Proof:** `python3 -I ~/ob-editor/bin/voice_master.py check FILE`: no flat-topped peaks, loudness and true peak inside the master limits, loudness range 3 to 7 LU. The gate repeats it (`audio`) and measures his lips (`lipsync`). OB 10-28: "only make it sound better not worse".

## Music
The route's `music` setting says if there is a bed: `bed` = yes; `optional` = only under his own talk with no clip or song playing (else start with `--music none`); `none` = nothing baked in.

| Format | Lane, in order | Tone |
|---|---|---|
| Organic reels (talking, graphics, lists, lecture, FDOE, reaction) | his saved viral songs, then royalty-free bank tracks | upbeat, bright, major |
| Ads, and any reel he will boost | royalty-free only. Bed when the reference ad has one or there is no reference | fits the script |
| YouTube long form | `youtube-safe` only: human-made, page shows no AI label and no Content ID, credited in the description | teaching: upbeat. Documentary: may go tense |
| YouTube clips for Instagram | none: he adds his sound in the app | |

OB 11-07: "Education content should be upbeat and higher enegery"; "yt is a little different because of copyright rules so do copyright friendly". A royalty-free track that outscores his saved song by the config's margin wins over it. Never: music we make (code, synth, AI), a track that is not in the index, a track inside the no-reuse window, an engine's own default.

**1. Read the edit, then pick.** With the cut locked:
```bash
python3 -I ~/ob-editor/bin/music_pick.py WORK --route ROUTE --voice VOICE.wav
```
→ `WORK/audio/edit_profile.json` and `WORK/audio/music_candidates.json`. Correct the profile: the sections are the real ones (hook, turn, payoff, CTA; chapters in long form) and the punch lines are the script's (the line after "but", the verdict). A wrong profile scores every track against the wrong video. Run it again. `--tone "tense, investigative"` only for a documentary.

**2. The shortlist.** Each survivor is scored on beat fit, energy per section (steady under the hook, a lift at the payoff; in long form the best section for each chapter), sitting under him (little energy in his speech band, no lead vocal) and the taste anchor. The record holds every candidate with scores and a reason in words, the rejects, and previews in `WORK/audio/previews/`. Too few: the record says `bank_short: true` with what was searched, and the delivery note says the bank needs new tracks. The top score goes in; any other pick needs its reason in the record. Name the pick and two runner-ups at delivery.

**3. Place it.**
```bash
python3 -I ~/ob-editor/bin/music_pick.py apply WORK
python3 -I ~/ob-editor/bin/music_pick.py use WORK
```
→ `WORK/audio/voice.wav`, `bed.wav`, `manifest.json`. `use` logs the track against reuse.
- **Level:** the route's bed level under his voice, stem against stem, per chapter in long form. A song with vocals is a voice under a voice: it loses to an instrumental at an equal score, and sits lower if it wins. OB 11-07: "turn the background music down".
- **Duck:** held, with the config's hold and release, so the bed does not pump in word gaps. Never the quick-release duck in `music_mix.py`.
- **Punch lines:** the bed drops out under each line marked in `WORK/plan/punch_lines.json` and returns on the next sentence. Never the hook.
- **Chapter turns (long form):** music changes on chapter cards and only there. One track may carry the video. A second track joins only at a card: crossfade when the keys agree, otherwise out into the card and in after it. A heavy chapter gets a sparser section or a dip, never a sad track.

**4. Mix onto the picture.**
```bash
python3 -I ~/ob-editor/bin/music_pick.py mix WORK VIDEO [--out OUT.mp4]
```
Voice, bed and every planned sound, mastered to the route's loudness, onto VIDEO's copied picture; pieces carried over. The gate and reviewer run on OUT, never VIDEO. No hand-rolled ffmpeg.
- **Cuts in the track:** on a bar line, same bar position both sides.
- **The ending:** silent by the last frame, on the track's own ending or the config fade. Never a hard stop, never mid-swell. To land the real ending, remove whole bars from the middle; with low beat confidence keep the fade.
- **Someone else's clip** never gets music or sound effects. Her voice never plays under his (OB 11-03: "when they are talking dont play their audio when im talking").
- **One file.** The stems stay in WORK for a quick bed swap.

## Sound effects
The route's `sfx` setting: `plan` = required; `optional` = only where a moment lands hard, else write no plan (or declare `--sfx none` at `start`); `none` = none. The per-minute cap is a ceiling, not a target.

1. **Moments come from the picture.** A moment is an event with an id where something lands, moves, changes or is revealed: a card entering, a photo snapping in, an object dropping, a number landing, a scene change, a proof flash. Entrances only; skip what his voice or the music carries. Source: the engine's event file or a `WORK/plan/moments.json` (`[{"id", "t", "what"}]`) you write.
2. **Say what the object does.** One line per moment: material (paper, glass, air, plastic, camera), action (slide, drop, tap, snap, rise), weight, length. "A paper card slides in, light, under 0.4 s." "A sugar cube drops on a table, small, hard."
3. **Rank from the bank.**
```bash
python3 -I ~/ob-editor/bin/sfx_pick.py WORK --route ROUTE
python3 -I ~/ob-editor/bin/sfx_check.py files PICKS...
```
→ `WORK/story/sfx_plan.json` (each hit: `t`, `event`, `object_line`, `file`, `recording_id`, `rank_score`, `runner_ups`, `db`) and `WORK/audio/sfx_candidates.json`. Overwrite a lazy proposed line. `files` screens for clipping, hiss, a silent tail and a late start. Nothing plausible: the moment goes in the plan's `bank_misses` with the search that ran, then `python3 -I ~/ob-editor/bin/openverse_sfx.py search "soft paper slide" --out ~/ob-editor/assets/sfx_library/openverse`, `sfx_dupes.py`, index, rank again. Still nothing: the moment stays silent. Never the code-made kit (`~/ob-editor/assets/sfx`), never a banned family.
4. **Vary by recording, not by file name.** Pitched copies of one recording are one recording. Stay under the repeat cap, never the same recording twice running. A list with more rows than the bank has recordings gets fewer sounds.
5. **Place the peak on the frame.** The sound's loudest 10 ms sits on the event frame, from the indexed peak, never a hand-typed lead. Early is what people notice: stay inside the config's sync window. If the beat and his word disagree, the word wins. A riser into the payoff stops dead just before it. Layer two sounds only on the biggest moment, tails trimmed before his next line. Level inside the config band.
6. **Check it is heard:** `python3 -I ~/ob-editor/bin/sfx_check.py mix FILE WORK/story/sfx_plan.json`. A planned sound the mix does not show on its frame is raised inside the band, cleared of the bed or removed.

## What is measured
The gate (`ob_job.py gate WORK FILE`) FAILs on:

| Check | What fails |
|---|---|
| `audio` | master loudness or true peak outside the limits, any clipped peak |
| `bank` | a file not in the index by hash (`bank_index.py lookup FILE`), a lane the route forbids, a code-made sound |
| `music_pick` | no record, too few candidates without `bank_short`, a pick that is not the top score with no reason, a reused track |
| `bed_level`, `music_story` | bed outside the route's level, or no stems; a cue off its chapter card; a punch line with the bed still up |
| `sfx_link`, `sfx_repeat`, `sfx_cap`, `sfx_heard` | a hit with no event, object line or runner-ups; a recording over the cap; too many a minute; a sound not found on its frame |
| `audio_manifest` | music or sound in the mix not declared, or the reverse |

No check covers these. Do them and keep the files:
```bash
W(){ ffmpeg -nostdin -v error -y -i "$1" -vn -ac 1 -ar 16000 "$2.wav" && whisper-cli -m ~/.whisper-models/ggml-medium.en.bin -f "$2.wav" -ml 1 -sow -np 2>/dev/null | sed 's/^\[[^]]*\] *//' | tr 'A-Z' 'a-z' | tr -cd "a-z0-9' \n" | tr -s ' \n' '\n' | sed '/^$/d' > "$2.txt"; }
W WORK/audio/voice.wav WORK/qc/words_voice; W FILE WORK/qc/words_mix; diff WORK/qc/words_voice.txt WORK/qc/words_mix.txt
ffmpeg -nostdin -i FILE -af ebur128 -f null - 2>&1 | awk '/ S: /{for(i=1;i<NF;i++)if($i=="S:"){v=$(i+1)+0;if(!n++||v>m)m=v}} /^ +I: /{I=$2} END{print "loudest 3 s minus whole mix:",m-I,"LU"}'
~/ob-editor/bin/earshot describe FILE --start S --end E --out WORK/qc/mood_S.json
```
- A word missing from the mix: the bed or a sound covers it. Lower or move it, mix again.
- The loudest 3 seconds stay inside the master's short-term margin.
- Each section's top mood tags agree with the profile's target words ("tense" on a teaching section is the wrong pick).
- Pumping: in `bed.wav`, no 2 dB rise under 0.4 s while he talks.

## Traps (his words; the taste anchor)
- **He picked:** Feel Good Funk Anthem, Moon Walk, Pop Track 03, Upbeat Jazz, his saved songs The Night We Met and Nineteen.
- **He hated:** Tapis and Vastness (11-07: "Oddly depressing for an educational video"); Spice Intrigue, Lounge Soul, Pizzicato Flow, Sneaky Curious Jazzy ("You always go so depressing"); beds in his voice band.
- **Stop-start** (10-20: "doesnt flow well"): one level, held duck, changes on chapter turns.
- **Same sound over and over** (10-16: "have different sound effects and make them a little quieter"): `sfx_repeat`.
- **Obnoxious** (10-29: "dont be obxious about them"): `sfx_cap`.
- **Ticks and a glitch** (11-06: "I also hated that sound effect you used"): banned families.
- **Sounds made in code, most too quiet to hear** (11-07: "use the sound effects from the bank first"): `bank`, `sfx_heard`.
- **AI-labelled and Content ID tracks:** the index's page-check dates decide, not a file name.
- **The boom file** is mostly infrasound and reads as clipping: high-pass it at 35 Hz.
