#!/usr/bin/env python3
"""A 3D insert rendered in Blender, headless: an extruded word or number in the brand font that springs in, as RGBA PNG frames to
composite over the canvas (OB 11-04: "here is the blender skill save it please to the editor skill and templates").

  python3 -I ~/ob-editor/bin/blender_insert.py OUT_DIR --text "14%" [--look paper|dark] [--seconds 1.0] [--px 1080] [--spin 70]

  look paper  ink face, brand-yellow sides (reads on the crumpled-paper canvas; yellow on cream does not)
       dark   brand-yellow face with a soft self-glow, ink sides (dark canvases; add the bloom when compositing)
Frames: OUT_DIR/f_0001.png ... at 29.97 fps, square px x px, transparent background, the word centred and filling about 70% of the
width at rest. Motion: the editor's closed-form damped spring (canvas_card.spring), never stock easing. Blender 5.2 at
/Applications/Blender.app, run with --factory-startup (no add-ons, no network). Waits for a render slot (render_slots).
The Blender Skills pack (~/ob-editor/blender-skills, MIT) has the deeper recipes: lighting, rendering, camera-cinematography,
materials, animation. Never its AI generators (Hyper3D, Hunyuan3D, Sketchfab AI): no AI imagery, ever (M22, M28).
"""
import argparse, os, subprocess, sys, tempfile

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
FONT = os.path.expanduser("~/ob-editor/fonts/BigShoulders/static/BigShouldersDisplay-Black.ttf")   # static instance of the brand font
BLENDER_SIDE = r'''
import bpy, math, sys, os
a = sys.argv[sys.argv.index("--") + 1:]
out, text, look, secs, px, spin, font = a[0], a[1], a[2], float(a[3]), int(a[4]), float(a[5]), a[6]
ACCENT = (1.0, 0.831, 0.0); INK = (0.102, 0.094, 0.086)
lin = lambda c: tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def spring(t, freq=3.2, damp=0.55):
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; wd = w * math.sqrt(1 - damp * damp)
    return 1 - math.exp(-damp * w * t) * (math.cos(wd * t) + damp * w / wd * math.sin(wd * t))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try: sc.render.engine = eng; break
    except TypeError: continue
sc.render.resolution_x = sc.render.resolution_y = px; sc.render.resolution_percentage = 100
sc.render.fps, sc.render.fps_base = 30000, 1001; sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"
n = max(2, round(secs * 30000 / 1001)); sc.frame_start, sc.frame_end = 1, n
cu = bpy.data.curves.new("w", "FONT"); cu.body = text; cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.font = bpy.data.fonts.load(font)
cu.extrude = 0.10; cu.bevel_depth = 0.010; cu.bevel_resolution = 3
ob = bpy.data.objects.new("w", cu); sc.collection.objects.link(ob)
def mat(name, col, rough, glow=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(col), 1); b.inputs["Roughness"].default_value = rough
    if glow:
        b.inputs["Emission Color"].default_value = (*lin(col), 1); b.inputs["Emission Strength"].default_value = glow
    return m
face, side = (mat("face", INK, 0.45), mat("side", ACCENT, 0.35)) if look == "paper" else (mat("face", ACCENT, 0.3, 0.6), mat("side", INK, 0.5))
# a text curve shares one material between its faces and its extrusion: make it a mesh, then the sides get their own colour
bpy.context.view_layer.objects.active = ob; ob.select_set(True); bpy.ops.object.convert(target="MESH")
ob = bpy.context.view_layer.objects.active; me = ob.data; me.materials.clear(); me.materials.append(face); me.materials.append(side)
for poly in me.polygons: poly.material_index = 0 if abs(poly.normal.z) > 0.95 else 1
bpy.context.view_layer.update()
dims = ob.dimensions; ob.rotation_euler = (math.radians(90), 0, 0)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "PERSP"; cam.data.lens = 60; cam.data.sensor_width = 36
dist = max(dims.x, dims.y) / 0.70 * cam.data.lens / cam.data.sensor_width   # the word fills ~70% of the frame at rest
cam.location = (0, -dist, 0); cam.rotation_euler = (math.radians(90), 0, 0)
for nm, loc, rot, e, s in (("key", (-0.6 * dist, -0.7 * dist, 0.6 * dist), (55, 0, -35), 900, 4), ("rim", (0.5 * dist, 0.5 * dist, 0.4 * dist), (-60, 0, 140), 450, 3)):
    L = bpy.data.objects.new(nm, bpy.data.lights.new(nm, "AREA")); L.data.energy = e * (dist / 6.2) ** 2; L.data.size = s
    L.location = loc; L.rotation_euler = tuple(math.radians(x) for x in rot); sc.collection.objects.link(L)
wd = bpy.data.worlds.new("w"); wd.use_nodes = True; sc.world = wd; wd.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
for f in range(1, n + 1):
    p = spring((f - 1) * 1001 / 30000)
    ob.rotation_euler = (math.radians(90), 0, math.radians(spin * (1 - p))); s = 0.6 + 0.4 * p; ob.scale = (s, s, s)
    ob.keyframe_insert("rotation_euler", frame=f); ob.keyframe_insert("scale", frame=f)
sc.render.filepath = os.path.join(out, "f_"); bpy.ops.render.render(animation=True)
print("BLENDER_INSERT_OK", n, sc.render.engine)
'''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--text", required=True)
    ap.add_argument("--look", choices=("paper", "dark"), default="paper"); ap.add_argument("--seconds", type=float, default=1.0)
    ap.add_argument("--px", type=int, default=1080); ap.add_argument("--spin", type=float, default=70.0); a = ap.parse_args()
    if not os.path.exists(BLENDER): sys.exit("Blender not found at " + BLENDER)
    if not os.path.exists(FONT): sys.exit("static brand font missing: " + FONT + " (make it: ~/ob-editor/.venv-fonts/bin/python -m fontTools.varLib.instancer)")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import render_slots as RS; RS.wait_free(max_jobs=3)
    except Exception: pass
    os.makedirs(a.out, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f: f.write(BLENDER_SIDE); side = f.name
    try:
        r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", side, "--", os.path.abspath(a.out), a.text, a.look, str(a.seconds), str(a.px),
                            str(a.spin), FONT], capture_output=True, text=True)
    finally: os.unlink(side)
    ok = "BLENDER_INSERT_OK" in r.stdout
    print(("wrote " + a.out) if ok else ("FAILED\n" + (r.stdout + r.stderr)[-3000:])); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
