# OB's Claude Video Editor Kit

This is the video-editing setup OB runs inside Claude Code: one editor skill, a locked preset for each format, and the tools it drives (about 150 scripts). You give Claude raw footage, and it comes back with a finished, captioned, graded and mixed edit. Before anything renders, you get a shot-by-shot review page to approve.

Shared as-is from OB's machine, updated 2026-11-02, with everything private taken out (see the last section). What changed since the October kit is in CHANGELOG.md.

## What it edits

| Format | What you get | Preset |
|---|---|---|
| Short-form reels | Tight talking-head cuts, face-tracked 9:16 crop, captions, hook text, list and graphic overlays, music under the voice, mastered for Instagram/TikTok. | `presets/short-form` |
| Long-form YouTube | Story edit from raw takes, explainer cards, photo pop-ins, sourced charts, punch-ins to hide cuts, chapter cards, end card. | `presets/youtube-longform` |
| Reaction videos | Split screen (you and the clip), clip audio from the file, term labels, quick proof overlays, chapter flow. | `presets/reaction` |
| Lecture reels | You at a TV with slides: hook block, slide cards, stamps, captions, TV typo patching. | inside the skill |
| Tier lists / this-or-that | TierMaker-style board, or two option cards with a check on the pick; items pop and spring into place. | inside the skill |
| Calorie-audit reviews | The format OB uses to review food days. | `presets/fdoe-audit` (and `fdoe-breakdown`, a template to test) |
| Long-form to reels | Turns a finished YouTube edit into stand-alone 9:16 reels, each under 1:30, only where a part stands on its own. | `presets/yt-clips` (`ytclip.py`) |
| YouTube thumbnails | Mirror a proven outlier's layout with your own frames, acne spot cleanup, A/B rounds that keep the winner in slot 1. | `references/youtube-thumbnails.md` in the skill |

## What you need

- A Mac with Apple Silicon (M1 or newer). The tools use Apple's video encoder and Apple Vision, so they won't run on Windows.
- [Claude Code](https://claude.com/claude-code) signed in.
- [Homebrew](https://brew.sh) and Xcode command line tools (`xcode-select --install`).
- About 4 GB free for the tools, and room for your footage. A separate drive for footage is best.

## Install (about 15 minutes, mostly downloads)

1. Unzip the kit anywhere.
2. In Terminal, run `bash INSTALL.sh ~/EditorWork`. The folder at the end is where your footage and edits live; use an external drive path if you have one.
   - It installs ffmpeg, whisper.cpp, yt-dlp and Node if missing, the Python and Node packages, and the Whisper models.
   - It copies `ob-editor`, `ob-clipper` and `ob-moments` into your home folder. Any existing copies are renamed, not deleted.
   - It installs the editor skill into `~/.claude/skills`, points every path at your folders, builds the Apple Vision helpers, and makes the fonts from your Mac's own system fonts.
3. Add the two free third-party skills the editor leans on, in Terminal:
   - `npx skills add heygen-com/hyperframes -g -a claude-code` (HyperFrames: the motion-graphics engine)
   - the `watch` skill from https://github.com/bradautomates/claude-video (lets Claude watch a reference reel)

## Using it

Open Claude Code in your home folder and talk to it like an editor:

- "edit this ~/EditorWork/RAW-FOOTAGE/clip.MP4, make it a reel like this: <reference link>"
- "cut this down to the best 45 seconds"
- "this is a reaction video, the clip is ~/Downloads/clip.mp4"

The skill asks you a few setup questions, loads the preset for the format and builds the edit in stages:
1. cut
2. word-level QC (0 clipped words)
3. grade options on one frame
4. graphics plan
5. a mock of every shot

You approve the review page, and only then does it render. Every render then runs the QC gate (`qc_gate.py`: clipped words, dead space, text on the face, loudness, quality, safe zones and more), and only a PASS is copied to your delivery folder (`deliver.py`). Finished files land in your work folder.

When you give Claude a note on an edit ("you cut me off mid word"), it adds the rule to the never-again ledger (`~/ob-editor/qc/mistakes.json`) with a check, so the gate catches it next time. `python3 -I ~/ob-editor/bin/qc_gate.py --rules` prints the list.

## Make it yours

- **HOUSE-STYLE.md** lists OB's rules: no sound effects unless asked, springs-only motion, his warm grade, no em dashes on screen, and so on. They are written into the skill and the presets. Tell Claude which ones to change for you, or edit `~/.claude/skills/short-form-editor/SKILL.md` and `~/ob-editor/presets/*/PRESET.md` yourself.
- **Presets are the secret.** Once an edit looks right, say "lock this into the preset" and Claude writes the values down so the next edit starts there.
- The skill mentions OB's own notes ("memory `…`"). Those files aren't included; Claude will skip them, or you can ask it to start your own.
- Folder names like `OB-EDITS` and `RAW-FOOTAGE/camera` are kept so the tools work unchanged; they now live under your work folder.
- The skill also mentions OpenMontage, an optional open-source toolkit OB had installed (silence cutting, reframing). The core pipeline doesn't need it; its OpenCV role is covered by the kit's own `~/ob-editor/.venv`.

## Good to know

- **One heavy job at a time.** On an 8 GB Mac two 4K renders, or three thumbnail builds, at once can crash everything (OB's did on Nov 1). The queue scripts (`*_when_free.sh`, `tier_render_queue.sh`, `ytclip.py render --yield`) wait for the machine to be free. Keep working files on your work drive, not /tmp.
- **Long renders run detached,** so closing Claude doesn't kill them. The skill has the exact command.
- `vmaf_check.py` (quality score) needs an ffmpeg with libvmaf. If yours lacks it: `brew tap homebrew-ffmpeg/ffmpeg && brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-libvmaf`.
- Music: OB mixes his saved tracks in for short form. Only use music you're allowed to; a reel with a copyrighted song can't be boosted.

## What's not included (on purpose)

- Client photos, testimonials, consent lists and any names. `proof_screen.py` ships with an empty exclusion list for your own.
- OB's footage, music, renders, notes, account data and logins.
- One-off scripts written for specific videos, backups, and compiled binaries (the installer rebuilds them). The skill sometimes names a per-video script (`story/...`, `_work/...`) as a worked example; Claude writes your own when needed.
- OB's planted-mistake test clips for the QC gate (his footage). Plant your own in `~/ob-editor/qc/regress/`.
- Apple's fonts. The installer makes them from your own Mac, which has them.
- Third-party skills (installed in step 3). See THIRD-PARTY.md for licences.
