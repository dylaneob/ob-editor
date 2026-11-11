# Element card: Blender 3D insert (any template)

OB 11-04 sent Nick Saraev's reel on "Blender Skills" (https://www.instagram.com/reel/DfUBU1tPVZn/) and the repo
(github.com/arjun988/blender-skills): "here is the blender skill save it please to the editor skill and templates".

A 3D object, word or number rendered in Blender and composited into the edit. It plays the role Kallaway's glowing objects
play (the infinity sign, the brain, the phone, the chips) and Trainbloom's boards play: one picture of the idea, a beat
before he says it. It is an element, not a whole format. Use it inside T06 (framework canvas), T15 (react and explain),
T17 (why-explainer) and T03 (reaction graphics while he talks).

## What exists (11-04)
- **`~/ob-editor/bin/blender_insert.py`** renders an extruded word or number in Big Shoulders Black with a spring-in turn,
  as RGBA PNG frames on a transparent background. Headless Blender 5.2 with `--factory-startup` (no add-ons, no network).
  It waits for a render slot. Measured: 30 frames at 540 px in about 10 s.
  - `--look paper`: ink face with yellow sides, for the crumpled-paper canvas, where yellow on cream doesn't read.
  - `--look dark`: yellow face with a self-glow and ink sides, for dark or studio canvases; add the soft glow when compositing.
  - `python3 -I ~/ob-editor/bin/blender_insert.py OUT --text "14%" --look paper --seconds 1.0 --px 1080`
  - Proved 11-04: "14%" in the paper look over the crumpled-paper canvas and "17.9" in the dark look with its glow, both
    springing in. The paper canvas is drawn in code: `T7/OB-EDITS/2026-11-04-reactions/_work/paper_gen.py`.
- **T17's calorie-cubes test** (templates study, 11-04): 84 frames at 1080x1920 in 38 s, live 9.6, 0 flash frames.
  Scripts are in that session's notes.
- **The Blender Skills pack**, saved as reference docs at `~/ob-editor/blender-skills/`; read `README-OB.md` there first.
  - `lighting/`, `rendering/`, `camera-cinematography/`, `materials/` (and `lookdev/`), `animation/` and `vfx-fx/`
    for glows and particles.
  - `geometry-nodes/` and `procedural-modeling/` for objects built from code; `prop-artist/` and `hard-surface/` for a phone,
    a bottle or a scale.
  - `neon-retrofuturism/` and `minimalist-style/` for the look.
  - The pack's `blender-director/` plans game pipelines. For a reel the editor is the director: one object per idea.

## How to place it
- **On the canvas** (T06 paper or studio): above his card, in the graphics band y 240 to 1120. It lands about 150 ms before
  the cue word (Kallaway's median lead). It holds with a slow drift or turn, never still, and leaves with the next graphic.
- **Soft shadow on paper:** the alpha blurred about 10 px, 35% black, offset 12 px down.
- **Glow on dark:** the alpha blurred about 18 px in #FFD400 at 50%, under the object.
- **Over his full frame:** only where he is silent or in the top stage (M37: a graphic never covers him while he talks).
  On his desk (T17 hero) it needs the camera match and a shadow pass, which are not built yet.

## Rules
- **No AI anything** (M22, M28). The pack documents ahujasid/blender-mcp's Hyper3D Rodin, Hunyuan3D and Sketchfab tools:
  never use them. Every object is modelled in code or by hand in Blender. Poly Haven CC0 HDRIs and textures are fine; log
  each one in `PHOTO-CREDITS.txt`.
- **Brand:** #FFD400 and ink only; Big Shoulders from `~/ob-editor/fonts/BigShoulders/static/` (static Black, ExtraBold and
  Bold made 11-04; Blender can't pick a weight from the variable font).
- **Motion:** the closed-form spring (`canvas_card.spring`) keyed per frame; no stock easing. A camera push is linear.
- **Sound:** a landing can carry one SFX within M17 (3-4 a minute, never two within 1.5 s).
- **Heavy job:** it counts toward `render_slots` (max 3 on the Mac mini, max 2 4K renders off the T7).

## Interactive Blender (when a model needs hands-on work)
Blender MCP is wired in this app (`mcp__Blender__*`: `execute_blender_code`, `get_objects_summary`,
`render_viewport_to_path`, screenshots, API docs). It needs Blender open, with its MCP add-on serving on localhost:9876.
The pack's recipes name ahujasid's tools; map them:
- `get_scene_info` -> `get_objects_summary`
- `get_viewport_screenshot` -> `get_screenshot_of_area_as_image` or `render_viewport_to_path`
- `execute_blender_code` -> the same name
- Poly Haven or Sketchfab download tools: not available here. Fetch CC0 files by hand and log them.
For edits, prefer the headless path (`blender_insert.py`, or a script run with `Blender -b --factory-startup -P`). It
needs no GUI and is repeatable.

## Upgrades to build next (each one a trial variable)
1. Objects beyond text: a phone with his real screenshot on the screen, a scale with the number, a pill bottle, a 3D bar
   chart that grows. Use the pack's `prop-artist`, `hard-surface` and `geometry-nodes`.
2. A camera move library for 1-2 s holds (push, orbit 15 degrees, drift), from `camera-cinematography/references/`.
3. A desk composite for T17: camera match and a shadow catcher.
