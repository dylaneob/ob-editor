#!/usr/bin/env python3
"""Graded stills per reaction shot (for the breakdown). Split shots are composed in the
Doctor Mike layout mirrored for OB: OB in the left panel, the vertical clip in the right panel, on OB's topo card.

  python3 react_stills.py WORK_DIR SOURCE.MP4
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from react_geom import OB_X, OB_W, OB_SRC_X, CLIP_X, CLIP_W
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

W, SRC = sys.argv[1], sys.argv[2]
LUT = f"{W}/lut.png" if os.path.exists(f"{W}/lut.png") else os.path.expanduser("~/ob-editor/luts/ob_grade_warmtan_hald.png")
TOPO = os.path.expanduser("~/ob-editor/assets/topo_bg_preview.jpg")
OUT = f"{W}/stills"; os.makedirs(OUT, exist_ok=True)
shots = json.load(open(f"{W}/react_cutlist.json"))["shots"]
clips = {}
for line in open(f"{W}/clips_index.txt"):
    k, name, _ = line.rstrip("\n").split("\t"); clips[int(k[1:])] = f"{W}/clips/{name}"
PUNCH = "crop=3200:1800:320:120,"
# Split geometry at 4K from react_geom.py, scaled /4 for 960x540 stills
SX = 0.25


def grab_ob(t, framing, path, w=1920):
    vf = (PUNCH if framing == "punch" else "") + f"scale={w}:-2"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", SRC, "-i", LUT, "-filter_complex",
                    f"[0:v]{vf}[v];[v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", "-q:v", "3", path], check=True)


def grab_clip(k, t, path):
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{max(0, t):.3f}", "-i", clips[k], "-frames:v", "1", "-q:v", "3", path], check=True)


def make(i_s):
    i, s = i_s
    mid = (s["src_in"] + s["src_out"]) / 2
    dst = f"{OUT}/shot_{i:03d}.jpg"
    if s["layout"] == "insert":   # first soundbite: clip sharp in the centre over a blurred fill of itself
        k, a0 = s["bites"][0][0], s["bites"][0][1]; cl = f"{OUT}/_cl_{i:03d}.jpg"; grab_clip(k, a0 + 0.6, cl)
        c = Image.open(cl).convert("RGB"); bg = ImageEnhance.Brightness(ImageOps.fit(c, (960, 540)).filter(ImageFilter.GaussianBlur(16))).enhance(0.72)
        fg = c.resize((int(c.width * 540 / c.height), 540)); bg.paste(fg, ((960 - fg.width) // 2, 0)); bg.save(dst, quality=85); os.remove(cl); return
    if s["layout"] == "ob":
        grab_ob(mid, s["framing"], dst, 960); return
    ob = f"{OUT}/_ob_{i:03d}.jpg"; cl = f"{OUT}/_cl_{i:03d}.jpg"
    grab_ob(mid, "wide", ob, 960); grab_clip(s["k"], mid - s["offset"], cl)
    canvas = Image.open(TOPO).convert("RGB").resize((960, 540))
    obi = Image.open(ob).convert("RGB")                      # 960x540 = full 3840 frame /4
    canvas.paste(obi.crop((int(OB_SRC_X * SX), 0, int((OB_SRC_X + OB_W) * SX), 540)), (int(OB_X * SX), 0))
    c = Image.open(cl).convert("RGB"); ch = 540; cw = int(c.width * ch / c.height)
    if cw > int(CLIP_W * SX): cw = int(CLIP_W * SX); ch = int(c.height * cw / c.width)
    c = c.resize((cw, ch)); canvas.paste(c, (int(CLIP_X * SX) + (int(CLIP_W * SX) - cw) // 2, (540 - ch) // 2))
    canvas.save(dst, quality=85); os.remove(ob); os.remove(cl)


with ThreadPoolExecutor(int(os.environ.get("REACT_STILLS_WORKERS", "3"))) as ex:
    list(ex.map(make, enumerate(shots)))
print(len(shots), "stills ->", OUT)
