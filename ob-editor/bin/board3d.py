#!/usr/bin/env python3
"""board3d: OB's Blender upgrade of Trainbloom's flat boards (T17; OB 11-07 "we wanna upgrade trainblooms style with blender").
Code-built clay objects (no AI imagery, no downloaded models) rendered in Cycles with a shadow catcher, so they sit on the
2D board (tmpl_board "tb", item kind "seq3d") with a real soft contact shadow. Full 1080x1920 frames, transparent outside the
object, so the 2D labels line up 1:1 with the numbers board3d writes to OUT/meta.json (projected pixel positions).

  python3 -I ~/ob-editor/bin/board3d.py bars  OUT --values 2467 1500 1850 --colors a b b [--max 2600] [--level 1874]
                                               [--stagger 0.12] [--dur 0.9] [--hold 0.4] [--cy 1000] [--width 760] [--height 560]
  python3 -I ~/ob-editor/bin/board3d.py tubes OUT --levels 0.80 0.85 --colors a b [--dur 1.0] [--stagger 0.25] [--hold 0.4]

bars : rounded clay columns grow from the board (his bar grow: 0.9 s ease-in-out, staggered 0.12 s), camera 12 deg above;
       meta: each bar's top centre, the base line, and the y of --level (a horizontal line in the image).
tubes: frosted glass capsules whose liquid rises to each level (his gauge fill: 1.0 s ease-in-out), on the board;
       meta: each tube's top, bottom and liquid top.
Palette names: a = brand yellow #FFD400, b = charcoal #2C2C2C, grey #C9C6BF, red #E5484D, green #22B455, or #RRGGBB.
Blender 5.2 (/Applications/Blender.app), --factory-startup, Cycles on Metal, 48 samples + denoise, only the object's region
is rendered (render border), Standard view transform so the brand colours stay exact. Waits for a render slot.
"""
import argparse, json, os, subprocess, sys, tempfile

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
PALETTE = {"a": "#FFD400", "b": "#2C2C2C", "grey": "#C9C6BF", "red": "#E5484D", "green": "#22B455", "ink": "#121212", "white": "#FFFFFF"}

SIDE = r'''
import bpy, math, sys, os, json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
A = json.loads(sys.argv[sys.argv.index("--") + 1])
FPS = 30000 / 1001
lin = lambda c: tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
hexc = lambda h: tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
def inout(u):
    u = max(0.0, min(1.0, u)); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "CYCLES"
try:
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "METAL"; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception as e: print("GPU setup:", e)
sc.cycles.samples = A.get("samples", 48); sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 100
sc.render.fps, sc.render.fps_base = 30000, 1001; sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
board = hexc(A.get("board", "#F3F1EC"))
wd = bpy.data.worlds.new("w"); wd.use_nodes = True; sc.world = wd
bg = wd.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (*lin(board), 1); bg.inputs["Strength"].default_value = A.get("world", 0.3)

def mat(name, col, rough=0.55, glass=False, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(hexc(col)), 1); b.inputs["Roughness"].default_value = rough
    if glass:
        b.inputs["Transmission Weight"].default_value = 1.0; b.inputs["IOR"].default_value = 1.35
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.25
    return m

def link(ob): sc.collection.objects.link(ob); return ob

def rounded_box(name, w, d, h, r, m):
    bpy.ops.mesh.primitive_cube_add(size=1); ob = bpy.context.active_object; ob.name = name
    ob.scale = (w, d, h); bpy.ops.object.transform_apply(scale=True)
    for v in ob.data.vertices: v.co.z += h / 2   # origin at the base: scale z grows it from the board
    bv = ob.modifiers.new("bv", "BEVEL"); bv.width = r; bv.segments = 6; bv.limit_method = "NONE"
    ob.data.materials.append(m); bpy.ops.object.shade_smooth(); return ob

def capsule(name, rad, h, m, seg=48):
    bpy.ops.mesh.primitive_cylinder_add(radius=rad, depth=h, vertices=seg); ob = bpy.context.active_object; ob.name = name
    for v in ob.data.vertices: v.co.z += h / 2   # origin at the base
    bv = ob.modifiers.new("bv", "BEVEL"); bv.width = rad * 0.98; bv.segments = 10; bv.limit_method = "ANGLE"
    ob.data.materials.append(m); bpy.ops.object.shade_smooth(); return ob

# the board: a shadow catcher, so only the shadow reaches the frame
bpy.ops.mesh.primitive_plane_add(size=60); fl = bpy.context.active_object; fl.is_shadow_catcher = True

cam = link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))); sc.camera = cam; cam.data.lens = A.get("lens", 70); cam.data.sensor_width = 36
cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 36 * 1920 / 1080
pitch = math.radians(A.get("pitch", 12)); dist = A.get("dist", 14.0); tz = A.get("target_z", 1.1)
cam.location = (0, -dist * math.cos(pitch), tz + dist * math.sin(pitch)); cam.rotation_euler = (math.pi / 2 - pitch, 0, 0)
cam.data.shift_y = A.get("shift_y", 0.0)
for nm, loc, e, s in (("key", (-7, -6, 10), 2600, 3.5), ("fill", (8, -7, 4), 300, 10), ("top", (0, 3, 12), 350, 10)):
    L = link(bpy.data.objects.new(nm, bpy.data.lights.new(nm, "AREA"))); L.data.energy = e; L.data.size = s; L.location = loc
    L.rotation_euler = (Vector((0, 0, tz)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

px = lambda co: (lambda v: (round(v.x * 1080, 1), round((1 - v.y) * 1920, 1)))(world_to_camera_view(sc, cam, Vector(co)))
meta = {"kind": A["kind"], "fps": FPS, "frames": 0}
objs = []
if A["kind"] == "bars":
    vals, cols = A["values"], A["colors"]; n = len(vals); mx = A.get("max") or max(vals); W3 = A.get("width_u", 7.4); H3 = A.get("height_u", 6.2)
    gap = 0.38; bw = W3 / (n + (n - 1) * gap); x0 = -W3 / 2 + bw / 2
    st, du, hold = A.get("stagger", 0.12), A.get("dur", 0.9), A.get("hold", 0.4)
    nf = int(round(((n - 1) * st + du + hold) * FPS)) + 1; meta["frames"] = nf; meta["bars"] = []
    for i, (v, c) in enumerate(zip(vals, cols)):
        x = x0 + i * bw * (1 + gap); h = H3 * v / mx
        ob = rounded_box(f"bar{i}", bw, bw * 0.9, h, min(0.12, bw * 0.18), mat(f"m{i}", c, 0.5, coat=0.15)); ob.location = (x, 0, 0); objs.append(ob)
        for f in range(1, nf + 1):
            u = inout(((f - 1) / FPS - i * st) / du); ob.scale = (1, 1, max(0.002, u)); ob.keyframe_insert("scale", frame=f)
        meta["bars"].append({"top": px((x, -bw * 0.45, h)), "base": px((x, -bw * 0.45, 0)), "x": px((x, -bw * 0.45, 0))[0]})
    if A.get("level") is not None:
        hl = H3 * A["level"] / mx; meta["level_y"] = px((0, -bw * 0.45, hl))[1]
        meta["level_x"] = [px((-W3 / 2 - 0.25, -bw * 0.45, hl))[0], px((W3 / 2 + 0.25, -bw * 0.45, hl))[0]]
    corners = [(sx * (W3 / 2 + 0.6), sy * 1.2, z) for sx in (-1, 1) for sy in (-1, 1) for z in (0, H3 + 0.3)]
elif A["kind"] == "tubes":
    lv, cols = A["levels"], A["colors"]; n = len(lv); rad = A.get("rad", 0.62); H3 = A.get("height_u", 4.4); sp = A.get("spacing", 2.3)
    st, du, hold = A.get("stagger", 0.25), A.get("dur", 1.0), A.get("hold", 0.4)
    nf = int(round(((n - 1) * st + du + hold) * FPS)) + 1; meta["frames"] = nf; meta["tubes"] = []
    glass = mat("glass", "#FFFFFF", 0.08, glass=True)
    for i, (l, c) in enumerate(zip(lv, cols)):
        x = (i - (n - 1) / 2) * sp
        g = capsule(f"tube{i}", rad, H3, glass); g.location = (x, 0, 0); objs.append(g)
        liq = capsule(f"liq{i}", rad * 0.86, H3 - rad * 0.14 * 2, mat(f"l{i}", c, 0.35, coat=0.3)); liq.location = (x, 0, rad * 0.14); objs.append(liq)
        for f in range(1, nf + 1):
            u = inout(((f - 1) / FPS - i * st) / du); liq.scale = (1, 1, max(0.03, l * u)); liq.keyframe_insert("scale", frame=f)
        meta["tubes"].append({"top": px((x, -rad, H3)), "bottom": px((x, -rad, 0)), "liquid_top": px((x, -rad, rad * 0.14 + (H3 - rad * 0.28) * l)), "x": px((x, 0, 0))[0]})
    corners = [(sx * ((n - 1) / 2 * sp + rad + 0.7), sy * 1.4, z) for sx in (-1, 1) for sy in (-1, 1) for z in (0, H3 + 0.3)]
# render only the object's region (plus its shadow), output stays full frame so the meta pixels are exact
pts = [px(c) for c in corners]; xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
sc.render.use_border = True; sc.render.use_crop_to_border = False
sc.render.border_min_x = max(0, min(xs) / 1080 - 0.04); sc.render.border_max_x = min(1, max(xs) / 1080 + 0.12)   # the key is front-left: shadows fall right
sc.render.border_min_y = max(0, 1 - (max(ys) + 60) / 1920); sc.render.border_max_y = min(1, 1 - (min(ys) - 40) / 1920)
meta["region"] = [min(xs), min(ys), max(xs), max(ys)]
sc.frame_start, sc.frame_end = 1, meta["frames"]
sc.render.filepath = os.path.join(A["out"], "f_")
json.dump(meta, open(os.path.join(A["out"], "meta.json"), "w"), indent=1)
if A.get("still"):
    sc.frame_set(meta["frames"]); sc.render.filepath = os.path.join(A["out"], "still.png"); bpy.ops.render.render(write_still=True)
else: bpy.ops.render.render(animation=True)
print("BOARD3D_OK", meta["frames"])
'''


def colour(c): return PALETTE.get(c, c if c.startswith("#") else "#C9C6BF")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("kind", choices=("bars", "tubes")); ap.add_argument("out")
    ap.add_argument("--values", type=float, nargs="*"); ap.add_argument("--levels", type=float, nargs="*"); ap.add_argument("--colors", nargs="*")
    ap.add_argument("--max", type=float); ap.add_argument("--level", type=float); ap.add_argument("--stagger", type=float)
    ap.add_argument("--dur", type=float); ap.add_argument("--hold", type=float); ap.add_argument("--pitch", type=float, default=12)
    ap.add_argument("--dist", type=float, default=23.5); ap.add_argument("--target_z", type=float); ap.add_argument("--shift_y", type=float, default=0.0)
    ap.add_argument("--samples", type=int, default=48); ap.add_argument("--board", default="#F3F1EC")
    ap.add_argument("--still", action="store_true", help="render only the last frame to OUT/still.png (a look check)"); a = ap.parse_args()
    A = {"kind": a.kind, "out": os.path.abspath(a.out), "pitch": a.pitch, "dist": a.dist, "shift_y": a.shift_y, "samples": a.samples, "board": a.board, "still": a.still}
    n = len(a.values or a.levels or [])
    A["colors"] = [colour(c) for c in (a.colors or ["a"] * n)]
    if a.kind == "bars": A.update(values=a.values, max=a.max, level=a.level, target_z=a.target_z or 3.0)
    else: A.update(levels=a.levels, target_z=a.target_z or 2.2)
    for k in ("stagger", "dur", "hold"):
        if getattr(a, k) is not None: A[k] = getattr(a, k)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import render_slots as RS; RS.wait_free(max_jobs=3)
    except Exception: pass
    os.makedirs(a.out, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f: f.write(SIDE); side = f.name
    try:
        r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", side, "--", json.dumps(A)], capture_output=True, text=True)
    finally: os.unlink(side)
    ok = "BOARD3D_OK" in r.stdout
    print(("wrote " + a.out) if ok else ("FAILED\n" + (r.stdout + r.stderr)[-3000:])); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
