# Blender Skills pack: OB's copy (reference docs, read this first)

Source: github.com/arjun988/blender-skills @ 8f778d2 (v1.3.0, MIT, LICENSE here). Installed by hand on 2026-11-04 after every file
was read. OB sent Nick Saraev's reel and the repo: "here is the blender skill save it please to the editor skill and templates".

- **Docs, not registered skills.** The 94 folders sit under the editor's toolbox, so they don't add 94 entries to every session.
  The editor loads a file when a 3D insert needs it. The element card is `~/ob-editor/styles/blender-3d-insert.md`.
- **Left out:** the root setup files. They hold a pipe-to-shell uv installer, PATH edits, an unpinned add-on, telemetry and
  agent rules. Removed from the docs: the Hyper3D/Hunyuan3D row in `references/mcp-tools.md` (no AI generation, ever: M22, M28)
  and a line in `references/reference-analysis-template.md` that told the agent to ignore the user.
- **Useful for reels:**
  - `camera-cinematography/` (camera-move-library: dolly-in, orbit, crane reveal; lens 35-50 mm product, 85-135 mm hero)
  - `lighting/references/cinematic-light-rigs.md` (product rig)
  - `compositing/` (Glare on the emission pass)
  - `realistic-style/references/pbr-values.md`
  - `hard-surface/` (Bevel 0.005-0.02 m, 2-3 segments, then Weighted Normal)
  - `stylized-style/references/npr-shaders.md` (rim glow, outlines)
  - `animation/`
  - Skip `blender-director`: it forces a game production brief.
- **Wrong for Blender 5.2** (the pack was written for 3.x-4.1):
  - EEVEE has no SSR, AO, Bloom or Contact Shadows checkboxes, and its engine id is `BLENDER_EEVEE` (no "Next").
  - Bloom is the Glare node (Bloom/Fog Glow) in `scene.compositing_node_group`; 5.x has no `node_tree` and no Composite node.
  - Principled inputs are renamed: Specular IOR Level, Transmission/Sheen/Subsurface Weight, Emission Color/Strength.
  - Auto Smooth is gone (`shade_auto_smooth`). Combine RGB is now Combine Color.
  - "Medium Contrast" is a Filmic look: use AgX, or Standard / Khronos PBR Neutral when brand colours must stay exact.
  - Never MP4 for inserts (no alpha): use `film_transparent` with PNG RGBA or ProRes 4444.
- **MCP names:** the pack assumes ahujasid/blender-mcp. Here, Blender Lab's server (`mcp__Blender__*`) maps as follows:
  - `get_scene_info` -> `get_objects_summary`
  - `get_viewport_screenshot` -> `get_screenshot_of_area_as_image` or `render_viewport_to_path`
  - `execute_blender_code` is the same.
  - Interactive use needs Blender open with its add-on on :9876. Edits use the headless path (`bin/blender_insert.py`).
