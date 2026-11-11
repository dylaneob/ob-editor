# OB Editor

OB's video editing setup for Claude Code: the editor skills, a format for every kind of edit, OB Studio, and the sound and music banks.
Public since 2026-11-11. Some music and sound effects have licence limits: check THIRD-PARTY.md before reusing them anywhere else.

## What's here

| Folder | What it is |
|---|---|
| `claude-skills/` | short-form-editor (a route per format, subjects), rea-video, Real SFX, watch, captions, motion graphics and the HyperFrames skills |
| `claude-agents/`, `claude-hooks/`, `VERIFICATION-LOOP.md` | The verification loop: a fresh read-only video reviewer and work checker, and a Stop hook that blocks "done" on a video until a reviewer passes it |
| `ob-editor/qc/` | The QC gate ledger, the review checklist, every number per format (`formats.json`) and the approved exemplars (`gold.json`) |
| `ob-editor/presets/` | The locked format for reels, YouTube, reactions, FDOE edits and clips |
| `ob-editor/styles/` | Templates and style cards (start with `TEMPLATE-CATALOG.md`) |
| `ob-editor/bin/` | The editing tools, overlay and card engines, quality gate, beat tools |
| `ob-editor/studio/` | OB Studio: beats, sound effects, music and a timeline, for leaving notes on an edit |
| `ob-editor/level-kit/`, `ob-editor/blender-skills/` | Graphics engine and Blender docs |
| `ob-editor/assets/`, `banks/` | Sound effects and the music bank (`banks/music/MUSIC-LIBRARY.md`) |
| `ob-editor/luts/`, `ob-editor/fonts/` | Colour grades and open-licence fonts |

## Set up

macOS on Apple Silicon: `./INSTALL.sh`. Read `HOUSE-STYLE.md` first, then `KIT-GUIDE.md` for the full walkthrough (written for the earlier kit, so this README wins where they differ).

OB Studio: `python3 ~/ob-editor/studio/studio.py serve <edit>`. See `ob-editor/studio/DESIGN.md`.

## Not in this repo

Client names, photos and proof, footage, renders, keys, OB's notes and business data, stock video, Apple fonts. Client names in the rules are replaced by labels such as "Client Y": ask OB for the consent list before showing any client.
