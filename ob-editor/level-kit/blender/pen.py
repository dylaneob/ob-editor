"""A generic GLP-1 pen, modelled in code (no brand, no AI): white body, ink cap, #FFD400 band, dose window, knurled ink dial.
Blender 5.2, Cycles on Metal, AgX, transparent film. Frames: OUT/p_0001.png ... at 29.97 fps.
Motion (pen's own rotation only; the drop is a 2D move in the comp): 0-0.6 s a spring turn about the vertical axis from -165 deg,
then a slow roll about its long axis with a small yaw drift, never still.
  Blender -b --factory-startup -P pen.py -- OUT_DIR [SECONDS] [W H]"""
import bpy, math, sys, os
argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]; SECS = float(argv[1]) if len(argv) > 1 else 6.0
W, H = (int(argv[2]), int(argv[3])) if len(argv) > 3 else (1600, 560)
FPS = 30000 / 1001; NF = int(round(SECS * FPS))
os.makedirs(OUT, exist_ok=True)

def spring(t, freq=2.0, damp=0.52):
    if t <= 0: return 0.0
    w = 2 * math.pi * freq; wd = w * math.sqrt(1 - damp ** 2)
    return 1 - math.exp(-damp * w * t) * (math.cos(wd * t) + damp * w / wd * math.sin(wd * t))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    pr = bpy.context.preferences.addons["cycles"].preferences; pr.compute_device_type = "METAL"; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception as e: print("GPU setup failed", e)
sc.cycles.samples = 72; sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.fps, sc.render.fps_base = 30000, 1001
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
sc.render.use_persistent_data = True
sc.view_settings.view_transform = "AgX"
for lk in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try: sc.view_settings.look = lk; break
    except Exception: pass
sc.view_settings.exposure = -0.1
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.20, 0.17, 0.14, 1); bg.inputs[1].default_value = 0.6

def mat(name, rgb, rough=0.35, coat=0.0, metal=0.0, ior_level=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    try: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.12
    except Exception: pass
    try: b.inputs["Specular IOR Level"].default_value = ior_level
    except Exception: pass
    return m

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

M_BODY = mat("body", srgb("ECECEA"), 0.32, coat=0.35)
M_LABEL = mat("label", srgb("D9DBDD"), 0.55)
M_INK = mat("ink", srgb("17171A"), 0.42, coat=0.2)
M_YEL = mat("yel", srgb("FFD400"), 0.30, coat=0.4)
M_WIN = mat("win", srgb("2B3036"), 0.06, coat=1.0, ior_level=0.9)
M_STRIPE = mat("stripe", srgb("8F969E"), 0.5)

pivot = bpy.data.objects.new("pivot", None); sc.collection.objects.link(pivot)

def cyl(name, r, depth, x, m, verts=128, bevel=0.0, seg=5):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=(x, 0, 0), rotation=(0, math.pi / 2, 0))
    o = bpy.context.active_object; o.name = name; o.data.materials.append(m)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL"); b.width = bevel; b.segments = seg; b.limit_method = "ANGLE"
    try: bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    except Exception: bpy.ops.object.shade_smooth()
    o.parent = pivot; return o

L = 1.62; R = 0.078
# body (x -0.42 .. 0.62), cap (x -0.81 .. -0.42), band, dial (0.62 .. 0.81)
cyl("body", R, 1.04, 0.10, M_BODY, bevel=0.012)
cyl("label", R + 0.0012, 0.70, 0.05, M_LABEL)
cyl("stripeA", R + 0.0016, 0.012, -0.28, M_STRIPE)
cyl("stripeB", R + 0.0016, 0.012, 0.38, M_STRIPE)
cyl("cap", R + 0.006, 0.40, -0.615, M_INK, bevel=0.03, seg=8)
cyl("band", R + 0.0035, 0.045, -0.40, M_YEL, bevel=0.004)
cyl("collar", R * 0.92, 0.05, 0.645, M_INK, bevel=0.006)
dial = cyl("dial", R * 0.86, 0.17, 0.75, M_INK, bevel=0.02, seg=6)
for i in range(40):                                   # knurling ribs on the dial
    a = 2 * math.pi * i / 40
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.75, math.cos(a) * R * 0.86, math.sin(a) * R * 0.86), rotation=(a, 0, 0))
    rb = bpy.context.active_object; rb.scale = (0.12, 0.010, 0.012); rb.data.materials.append(M_INK); rb.parent = pivot
# dose window: a dark glossy pane on the front face of the label, with a yellow dose tick beside it
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.43, -R - 0.002, 0.0))
win = bpy.context.active_object; win.scale = (0.16, 0.012, 0.075); win.data.materials.append(M_WIN)
b = win.modifiers.new("bev", "BEVEL"); b.width = 0.012; b.segments = 4; win.parent = pivot
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.535, -R - 0.004, 0.0))
tick = bpy.context.active_object; tick.scale = (0.012, 0.01, 0.05); tick.data.materials.append(M_YEL); tick.parent = pivot
# lights: big soft key top-left front, warm fill, cool rim from behind
def area(name, loc, rot, size, power, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.size = size; l.energy = power; l.color = color
    o = bpy.data.objects.new(name, l); o.location = loc; o.rotation_euler = rot; sc.collection.objects.link(o); return o
def aim(o, target=(0, 0, 0)):
    import mathutils
    d = mathutils.Vector(target) - o.location; o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
k = area("key", (-2.2, -3.0, 3.0), (0, 0, 0), 3.0, 700, (1.0, 0.97, 0.92)); aim(k)
f = area("fill", (3.0, -3.0, 0.4), (0, 0, 0), 4.0, 160, (1.0, 0.86, 0.70)); aim(f)
r = area("rim", (0.8, 3.2, 2.0), (0, 0, 0), 2.0, 500, (0.85, 0.92, 1.0)); aim(r)
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85; cam_d.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -4.9, 0.62); aim(cam, (0, 0, 0.0))
# per-frame keys of the pivot rotation (spring turn, then a slow roll with a small yaw drift)
sc.frame_start, sc.frame_end = 1, NF
for fr in range(1, NF + 1):
    t = (fr - 1) / FPS
    yaw = math.radians(-165) * (1 - spring(t, 1.9, 0.5)) + math.radians(5) * math.sin(2 * math.pi * 0.22 * max(0, t - 0.6))
    roll = math.radians(-30) * (1 - spring(t, 1.6, 0.6)) + math.radians(22) * max(0, t - 0.5)
    pitch = math.radians(8) * (1 - spring(t, 2.2, 0.45))
    pivot.rotation_euler = (roll, pitch, yaw); pivot.keyframe_insert("rotation_euler", frame=fr)
try:
    for fc in pivot.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
except Exception as e:
    print("interp", e)
sc.render.filepath = os.path.join(OUT, "p_")
bpy.ops.render.render(animation=True)
print("PEN DONE", NF)
