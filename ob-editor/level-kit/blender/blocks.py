"""Count-up 3D blocks, modelled in code (no AI 3D): Blender 5.x, Cycles on Metal, AgX, transparent film over a shadow catcher.
Springs are keyed per frame (closed form, never stock easing); the camera push and orbit are linear, so it is never still.

  Blender -b --factory-startup -P blocks.py -- SPEC.json [--test FRAME]
Writes SPEC.out/b_0001.png ... and SPEC.out/proj.json (per frame: screen points of each block, for the 2D layer).
Run `python3 -I ~/ob-editor/bin/render_slots.py wait` first: a Blender render is a heavy job.

SPEC (JSON; times in seconds from the render's frame 1, which the engine pins to a cue):
  out, w, h (render px, 1242x920 fills the top stage at scale 1.10), secs, samples (80), exposure (-1.1), look ("AgX - Punchy")
  mode "split": each block of 'weight lost' drops in, splits on t_split into a top part (#FFD400) and a bottom part (ink) whose
         share counts up (0 -> share) on its front face, pulse on t_pulse. Block keys: key, share, x, title, sub, top_label,
         bottom_label. (The GLP test: STEP 1 38% / SURMOUNT-1 25% lean.)
  mode "fill": each block is a ghost outline (100%) that a #FFD400 fill rises into, from t_fill0 to land at share on
         t_land, the % counting with the fill height; ghost_label on the ghost, fill_label under the number; pulse on t_pulse.
         (The GLP edit: 60% of the weight lost regained, Budini 2026.)
  ht, bw, bd (block size, metres), cam {lens, dist, dist_end, height, target_z, orbit_deg}"""
import bpy, math, sys, os, json
import mathutils
from bpy_extras.object_utils import world_to_camera_view
argv = sys.argv[sys.argv.index("--") + 1:]
SPEC = json.load(open(argv[0])); OUT = SPEC["out"]; os.makedirs(OUT, exist_ok=True)
W, H = SPEC.get("w", 1242), SPEC.get("h", 920); FPS = 30000 / 1001; SECS = SPEC["secs"]; NF = int(round(SECS * FPS))
MODE = SPEC.get("mode", "split"); HT, BW, BD = SPEC.get("ht", 1.70), SPEC.get("bw", 0.86), SPEC.get("bd", 0.86)
FONT_DIR = os.path.expanduser("~/ob-editor/fonts/BigShoulders/static/")


def spring(t, freq=2.2, damp=0.5):
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; wd = w * math.sqrt(1 - damp ** 2)
    return 1 - math.exp(-damp * w * t) * (math.cos(wd * t) + damp * w / wd * math.sin(wd * t))


def kick(t, freq=2.4, damp=0.35):
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; return math.exp(-damp * w * t) * math.sin(w * t)


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "CYCLES"
try:
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "METAL"; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception as e: print("GPU setup failed", e)
sc.cycles.samples = SPEC.get("samples", 80); sc.cycles.use_denoising = True
sc.render.film_transparent = True; sc.render.use_persistent_data = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.fps, sc.render.fps_base = 30000, 1001
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.4
sc.view_settings.view_transform = "AgX"
for lk in (SPEC.get("look", "AgX - Punchy"), "Punchy", "AgX - Medium High Contrast"):
    try: sc.view_settings.look = lk; break
    except Exception: pass
sc.view_settings.exposure = SPEC.get("exposure", -1.1)
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
bgn = world.node_tree.nodes["Background"]; bgn.inputs[0].default_value = (0.18, 0.15, 0.12, 1); bgn.inputs[1].default_value = 0.5
FONT = bpy.data.fonts.load(FONT_DIR + "BigShouldersDisplay-Black.ttf"); FONT_XB = bpy.data.fonts.load(FONT_DIR + "BigShouldersDisplay-ExtraBold.ttf")


def pmat(name, hexc, rough=0.4, alpha=1.0, emit=0.0, coat=0.25):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(hexc), 1); b.inputs["Roughness"].default_value = rough
    try: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.2
    except Exception: pass
    if alpha < 1: b.inputs["Alpha"].default_value = alpha
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(hexc), 1); b.inputs["Emission Strength"].default_value = emit
    return m


def two_tone(name, end_hex, end_rough):
    """'Weight lost' cream that crossfades to the slab's own colour (Mix Shader factor keyed per frame)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nodes = nt.nodes
    out = nodes["Material Output"]; a = nodes["Principled BSDF"]
    a.inputs["Base Color"].default_value = (*srgb("EDE6DA"), 1); a.inputs["Roughness"].default_value = 0.42
    b = nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Base Color"].default_value = (*srgb(end_hex), 1); b.inputs["Roughness"].default_value = end_rough
    for bs in (a, b):
        try: bs.inputs["Coat Weight"].default_value = 0.25; bs.inputs["Coat Roughness"].default_value = 0.2
        except Exception: pass
    mix = nodes.new("ShaderNodeMixShader")
    nt.links.new(a.outputs[0], mix.inputs[1]); nt.links.new(b.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    return m, mix


def slab(name, h, m, bw=BW, bd=BD, bevel=0.045):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); o = bpy.context.active_object; o.name = name
    o.scale = (bw, bd, h); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bv = o.modifiers.new("bev", "BEVEL"); bv.width = bevel; bv.segments = 6; bv.limit_method = "ANGLE"
    try: bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except Exception: bpy.ops.object.shade_smooth()
    o.data.materials.append(m); return o


def label(parent, body, size, z, m, font=None, ext=0.006, y=None):
    cu = bpy.data.curves.new(body[:8], "FONT"); cu.body = body; cu.font = font or FONT; cu.size = size
    cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = ext
    o = bpy.data.objects.new(body[:8], cu); sc.collection.objects.link(o); o.data.materials.append(m)
    o.parent = parent; o.location = (0, (-BD / 2 - 0.004) if y is None else y, z); o.rotation_euler = (math.radians(90), 0, 0); return o


M_TINK = pmat("tink", "141416", 0.5, coat=0); M_TWHITE = pmat("twhite", "FFFFFF", 0.5, emit=0.35, coat=0); M_TYEL = pmat("tyel", "FFD400", 0.5, emit=0.6, coat=0)
blocks = []
if MODE == "split":
    for bk in SPEC["blocks"]:
        piv = bpy.data.objects.new(bk["key"], None); sc.collection.objects.link(piv); piv.location = (bk["x"], 0, 0)
        hl, hf = HT * bk["share"], HT * (1 - bk["share"])
        ml, mixl = two_tone(bk["key"] + "_lm", "141416", 0.36); mf, mixf = two_tone(bk["key"] + "_fm", "FFD400", 0.34)
        lo = slab(bk["key"] + "_low", hl, ml); lo.parent = piv; fo = slab(bk["key"] + "_top", hf, mf); fo.parent = piv
        label(fo, bk["title"], bk.get("title_size", 0.215), 0.16, M_TINK); label(fo, bk["sub"], 0.10, -0.03, M_TINK, FONT_XB)
        tl = label(fo, bk.get("top_label", "FAT"), 0.12, -hf / 2 + 0.13, M_TINK)
        num = label(lo, "0%", bk.get("num_size", 0.30), bk.get("num_z", 0.05), M_TWHITE)
        bl = label(lo, bk.get("bottom_label", "LEAN MASS"), 0.085, bk.get("bottom_z", -hl / 2 + 0.10), M_TYEL)
        blocks.append(dict(bk, piv=piv, low=lo, top=fo, hl=hl, hf=hf, mixes=(mixl, mixf), num=num, labs=(tl, bl, num)))
else:
    for bk in SPEC["blocks"]:
        piv = bpy.data.objects.new(bk["key"], None); sc.collection.objects.link(piv); piv.location = (bk.get("x", 0), 0, 0)
        gm = pmat(bk["key"] + "_ghost", "F4F1EA", 0.3, alpha=0.10, coat=0)
        ghost = slab(bk["key"] + "_ghost", HT, gm, bevel=0.03); ghost.parent = piv; ghost.location = (0, 0, HT / 2)
        em = pmat(bk["key"] + "_edge", "F4F1EA", 0.35, emit=0.15, coat=0)
        edges = slab(bk["key"] + "_edges", HT, em, bevel=0.0); edges.parent = piv; edges.location = (0, 0, HT / 2)
        wf = edges.modifiers.new("wire", "WIREFRAME"); wf.thickness = 0.03; wf.use_even_offset = True
        fm = pmat(bk["key"] + "_fill", "FFD400", 0.32, coat=0.35)
        fill = slab(bk["key"] + "_fill", 1.0, fm, BW - 0.06, BD - 0.06); fill.parent = piv
        gl = label(ghost, bk.get("ghost_label", "WEIGHT LOST"), bk.get("ghost_label_size", 0.15), HT / 2 - 0.17, M_TWHITE, FONT, y=-BD / 2 - 0.02)
        num = label(fill, "0%", bk.get("num_size", 0.42), 0.0, M_TINK, ext=0.01, y=-(BD - 0.06) / 2 - 0.006)
        fl = label(fill, bk.get("fill_label", "REGAINED"), bk.get("fill_label_size", 0.12), 0.0, M_TINK, FONT_XB, y=-(BD - 0.06) / 2 - 0.006)
        blocks.append(dict(bk, piv=piv, ghost=ghost, edges=edges, fill=fill, num=num, flab=fl, glab=gl))

bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0)); floor = bpy.context.active_object; floor.is_shadow_catcher = True


def area(name, loc, size, power, color=(1, 1, 1), target=(0, 0, 0.8)):
    l = bpy.data.lights.new(name, "AREA"); l.size = size; l.energy = power; l.color = color
    o = bpy.data.objects.new(name, l); o.location = loc; sc.collection.objects.link(o)
    d = mathutils.Vector(target) - o.location; o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); return o


area("key", (-3.0, -3.5, 4.2), 4.0, 1300, (1.0, 0.96, 0.9)); area("fill", (3.8, -3.0, 1.6), 5.0, 380, (1.0, 0.85, 0.7)); area("rim", (1.5, 4.0, 3.2), 3.0, 900, (0.85, 0.92, 1.0))
C = SPEC.get("cam", {}); cam_d = bpy.data.cameras.new("cam"); cam_d.lens = C.get("lens", 50); cam_d.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam


def place_cam(t):
    u = t / SECS; orb = C.get("orbit_deg", 4.0); ang = math.radians(-orb / 2 + orb * u); dist = mix(C.get("dist", 6.0), C.get("dist_end", 5.65), u)
    cam.location = (math.sin(ang) * dist, -math.cos(ang) * dist, C.get("height", 1.75))
    d = mathutils.Vector((0, 0, C.get("target_z", 0.78))) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def mix(a, b, u):
    return a + (b - a) * u


T_SPLIT, T_PULSE = SPEC.get("t_split", 0.70), SPEC.get("t_pulse", 1.97)


def fill_level(bk, t):
    """mode fill: the fill height share (0..share) at t: a spring from t_fill0 that lands on share at t_land."""
    t0, t1 = SPEC["t_fill0"], SPEC["t_land"]; f = SPEC.get("fill_freq", 1.0 / max(0.2, (t1 - t0)) * 0.62)
    return bk["share"] * spring(t - t0, f, SPEC.get("fill_damp", 0.78))


def count_val(t, bk, i):
    if MODE == "fill":                                         # the % rides the fill and reads the share once it has landed
        return int(round(min(1.0, max(0.0, fill_level(bk, t)) / (bk["share"] * 0.97)) * bk["share"] * 100))
    T0, T1 = T_SPLIT + 0.12, T_SPLIT + 0.72
    u = min(1.0, max(0.0, (t - T0 - 0.09 * i) / (T1 - T0))); target = round(bk["share"] * 100)
    return target if u >= 1 else int(target * (1 - (1 - u) ** 3))


def on_frame(scene, depsgraph=None):
    t = (scene.frame_current - 1) / FPS
    for i, b in enumerate(blocks): b["num"].data.body = f"{count_val(t, b, i)}%"


bpy.app.handlers.frame_change_pre.append(on_frame)
proj = []; sc.frame_start, sc.frame_end = 1, NF


def px(o, dx=0, dy=0, dz=0):
    p = o.matrix_world @ mathutils.Vector((dx, dy, dz)); v = world_to_camera_view(sc, cam, p)
    return [round(v.x * W, 1), round((1 - v.y) * H, 1)]


for fr in range(1, NF + 1):
    t = (fr - 1) / FPS; place_cam(t); cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_euler", frame=fr); pf = {"t": round(t, 4)}
    for i, b in enumerate(blocks):
        td = t - 0.09 * i; drop = spring(td, 2.0, 0.42); yaw = math.radians(28 * (1 if i % 2 == 0 else -1)) * (1 - spring(td, 1.7, 0.55))
        b["piv"].location = (b.get("x", 0), 0, 2.9 * (1 - drop)); b["piv"].rotation_euler = (0, 0, yaw)
        b["piv"].keyframe_insert("location", frame=fr); b["piv"].keyframe_insert("rotation_euler", frame=fr)
        if MODE == "split":
            ts = t - T_SPLIT - 0.06 * i; s = spring(ts, 2.3, 0.5); gap = 0.16 * s; fwd = -0.26 * spring(ts - 0.05, 2.0, 0.5)
            pulse = 1 + 0.07 * kick(t - T_PULSE - 0.05 * i)
            b["low"].location = (0, fwd, b["hl"] / 2); b["low"].scale = (pulse, pulse, pulse); b["top"].location = (0, 0, b["hl"] + gap + b["hf"] / 2)
            for o in (b["low"], b["top"]): o.keyframe_insert("location", frame=fr); o.keyframe_insert("scale", frame=fr)
            ls = spring(ts - 0.04, 3.2, 0.6)
            for o in b["labs"]: o.scale = (ls, ls, ls); o.keyframe_insert("scale", frame=fr)
            c = min(1.0, max(0.0, (t - T_SPLIT + 0.02) / 0.22)); c = c * c * (3 - 2 * c)
            for mx in b["mixes"]: mx.inputs[0].default_value = c; mx.inputs[0].keyframe_insert("default_value", frame=fr)
            sc.frame_set(fr); bpy.context.view_layer.update()
            pf[b["key"]] = {"lean_front": px(b["low"], 0, -BD / 2 - 0.01, 0), "fat_front": px(b["top"], 0, -BD / 2 - 0.01, 0), "base": px(b["piv"], 0, -BD / 2, 0),
                            "top": px(b["top"], 0, -BD / 2, b["hf"] / 2), "lean_left": px(b["low"], -BW / 2, -BD / 2, 0), "lean_right": px(b["low"], BW / 2, -BD / 2, 0)}
        else:
            h = max(0.004, min(HT - 0.01, HT * fill_level(b, t) / 1.0)); pulse = 1 + 0.05 * kick(t - T_PULSE)
            b["fill"].scale = (1, 1, h); b["fill"].location = (0, 0, h / 2 + 0.005); b["ghost"].scale = (pulse, pulse, 1)
            for o in (b["fill"], b["ghost"]): o.keyframe_insert("location", frame=fr); o.keyframe_insert("scale", frame=fr)
            # the number and its label ride the fill's front face, never squashed by its z scale
            nz = max(h - 0.30, 0.26); inv = 1.0 / max(h, 1e-3); vis = min(1.0, max(0.0, (h - 0.30) / 0.30)); vis = vis * vis * (3 - 2 * vis)
            for o, z in ((b["num"], nz), (b["flab"], nz - 0.25)):
                o.location = (0, -(BD - 0.06) / 2 - 0.006, (z - h / 2) * inv); o.scale = (max(vis, 1e-3), max(vis, 1e-3) * inv, max(vis, 1e-3))
                o.keyframe_insert("location", frame=fr); o.keyframe_insert("scale", frame=fr)
            sc.frame_set(fr); bpy.context.view_layer.update()
            pf[b["key"]] = {"base": px(b["piv"], 0, -BD / 2, 0), "ghost_top": px(b["piv"], 0, -BD / 2, HT), "fill_top": px(b["piv"], 0, -BD / 2, h),
                            "left": px(b["piv"], -BW / 2, -BD / 2, 0), "right": px(b["piv"], BW / 2, -BD / 2, 0)}
    proj.append(pf)
for o in bpy.data.objects:
    ad = o.animation_data
    if ad and ad.action:
        try:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
        except Exception: pass
json.dump(proj, open(os.path.join(OUT, "proj.json"), "w"))
if "--test" in argv:
    fr = int(argv[argv.index("--test") + 1]); sc.frame_set(fr); sc.cycles.samples = 24
    sc.render.filepath = os.path.join(OUT, f"test_{fr:04d}.png"); bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(OUT, "b_"); bpy.ops.render.render(animation=True)
print("BLOCKS DONE", NF)
