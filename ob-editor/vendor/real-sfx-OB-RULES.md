> **OB's local rules (read first; they override anything below).** Installed by hand 2026-11-01 from Clipwing/skills @ edbefcb
> (2026-10-21, tarball sha256 b187ed76..., kept at `~/ob-editor/vendor/`), after a line-by-line security read. OB asked:
> "download this to our editor skill long form and short" (@hugomxnning's "3 free SFX tools for Claude" reel). Licence: the
> README says scripts MIT (no LICENSE file in the repo); the bundled uisfx sounds are CC0.
> - **/short-form-editor stays the entry point.** This skill is its sound-effects mixer and moment finder: use it when that
>   skill's SFX step routes here or OB names Real SFX. It does not take over a plain "add sound effects" request on its own.
> - **OB's caps win over this skill's densities** (it drafts up to ~30 sounds a minute and has no per-minute limit):
>   reels about 3-4 a minute at most, none in the first 0.5 s, never two within 1.5 s (a list's ticks excepted),
>   entrances only, never on exits, about -24 dB under his voice, varied. Long-form between 0.6 and 2.9 a minute, only
>   where a beat needs one ("use them when needed dont be obxious about them", ledger M17). So:
>   - always feed `from_cues.py` OUR cue list (the shot list's audio plan, `OB_SFX_PLAN`) as a cues.json: never a project
>     folder (with no list it runs the project's own JS under node, and its hook is not a sandbox);
>   - `find_moments.py` / `suggest_cues.py` only to suggest candidates for the plan, never placed as they come;
>   - never `texture.py` or `bed.py` on his edits (they fill the holes with sound).
> - **Never run:** `setup.py init --uisfx` (uisfx is already bundled; it would npm-install the latest version),
>   `listen.py install` / `hear.py install` (unpinned pip + an unhashed model / a 2.75 GB model with remote code; never
>   `--trust-unreviewed`), `listen_page.py serve --lan` (stop the local page when done), `adjust_test.py` with hand-written ids.
> - **Libraries:** `~/ob-editor/assets/sfx_real` (Kenney), `assets/sfx_tai` (Anderson Tai), the Openverse downloads in
>   `/Volumes/T7/OB-EDITS/sfx-library/openverse` (`~/ob-editor/bin/openverse_sfx.py`). Pick between candidates with
>   `~/ob-editor/bin/earshot match`. No AI-generated audio, no uploads of his audio anywhere.
> - Its taste and index files live in this folder: back it up before any update. Never update it from upstream blind.
