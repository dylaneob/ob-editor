#!/usr/bin/env python3
"""Prepare reaction graphics for mockups/render: tag each event with its base layout, resolve montage
items, build the HyperFrames project assets, and grab the base still under every event.

  python3 react_prep.py WORK_DIR SOURCE.MP4
"""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from react_geom import OB_X, OB_W, OB_SRC_X, CLIP_X, CLIP_W
from PIL import Image, ImageOps

W, SRC = sys.argv[1], sys.argv[2]
H = f"{W}/hf"
for d in ("compositions", "mocks", "assets/stills", "assets/photos", "assets/proof", "assets/shots", "assets/montage", "assets/base", "assets/fonts"):
    os.makedirs(f"{H}/{d}", exist_ok=True)
ED = os.path.expanduser("~/ob-editor")
for f in os.listdir(f"{ED}/fonts"):
    if os.path.isfile(f"{ED}/fonts/{f}"): shutil.copy(f"{ED}/fonts/{f}", f"{H}/assets/fonts/{f}")
shutil.copy(f"{ED}/fonts/BigShoulders/BigShouldersDisplay[wght].ttf", f"{H}/assets/fonts/BigShouldersDisplay.ttf")   # brand font (10-28): flat name for CSS
shutil.copy(f"{ED}/vendor/gsap.min.js", f"{H}/assets/gsap.min.js"); shutil.copy(f"{ED}/assets/topo_bg.png", f"{H}/assets/topo_bg.png")
if not os.path.exists(f"{H}/meta.json"):
    json.dump({"id": os.path.basename(W.rstrip("/")).lower(), "name": os.path.basename(W.rstrip("/")).lower()}, open(f"{H}/meta.json", "w"))
    open(f"{H}/index.html", "w").write('<!doctype html><html><head><script src="assets/gsap.min.js"></script></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="1" data-width="3840" data-height="2160"></div><script>window.__timelines=window.__timelines||{};window.__timelines["main"]=gsap.timeline({paused:true});</script></body></html>')

# assets: OB's own photos (viewed + chosen 2026-10-16), Client M, screenshots
ST = os.path.expanduser("~/Desktop/OB-TODDLER-DIET-STORY/RAW STILLS (no captions, full res)")
pick = {"japan.jpg": f"{ST}/02 Japan (Nov 16-18)/02-01 IMG_8301 Nov 16 Japan 0m01.0s.jpg",
        "before218.jpg": f"{ST}/01 Hook - 218 (before, Nov 27)/01-03 C3002 Nov 27 0m06.0s.jpg",
        "after185.jpg": f"{ST}/01 Hook - 185 (after, day 30, Jan 15)/01-03 C3279 Jan 15 0m07.0s.jpg"}
for dst, src in pick.items():
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB"); im.thumbnail((1600, 2200)); im.save(f"{H}/assets/photos/{dst}", quality=92)
shutil.copy("/Volumes/T7/OB-EDITS/C4352-edit/hf/assets/proof/client_m4.jpg", f"{H}/assets/proof/client_m4.jpg")
for f in (os.listdir(f"{W}/shots") if os.path.isdir(f"{W}/shots") else []):
    if f.lower().endswith(".png") and not f.startswith("._"): Image.open(f"{W}/shots/{f}").convert("RGB").save(f"{H}/assets/shots/{f}", quality=92)

shots = json.load(open(f"{W}/react_cutlist.json"))["shots"]
evs = json.load(open(f"{W}/resolve/events_resolved.json"))["events"]

# proof assets for on-frame overlays, from your own consented proof folders (run proof_screen.py first;
# excluded IDs are never listed in the spec)
OBV = os.path.expanduser("~/EditorWork/ARCHIVE/proof")
SRCS = {"f_": f"{OBV}/before-after/ba-{{}}.jpg",        # f_<ID>: finished before/after composites
        "n_": f"{OBV}/new/{{}}.jpg",                    # n_<ID>: new photos
        "c_": f"{OBV}/clean/{{}}.jpg"}                  # c_<name>: clean chats / charts
for e in evs:
    if e["type"] != "overlay" or e.get("folder", "proof") != "proof": continue
    for it in e["items"]:
        key = it[0]; dst = f"{H}/assets/proof/{key}.jpg"
        if key[:2] in SRCS and not os.path.exists(dst):
            im = ImageOps.exif_transpose(Image.open(SRCS[key[:2]].format(key[2:]))).convert("RGB"); im.thumbnail((1800, 1800)); im.save(dst, quality=90)


def r2e(t):
    for s_ in shots:
        if s_["src_in"] <= t < s_["src_out"]: return s_["edit_in"] + t - s_["src_in"]
        if t < s_["src_in"]: return s_["edit_in"]
    return shots[-1]["edit_out"]


def item_times(e):   # when each overlay image lands, relative to the event start
    n = len(e["items"])
    if e.get("items_at_src"): return [round(max(0.0, r2e(t) - e["edit_in"]), 3) for t in e["items_at_src"]]
    if e.get("even"): return [round(i * (e["dur"] - 0.3) / n, 3) for i in range(n)]
    return e.get("items_at", [0.0] * n)


CASC = [cv2.CascadeClassifier(cv2.data.haarcascades + f) for f in
        ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml", "haarcascade_profileface.xml")]


def face_cx(path, default=1840):
    """OB's face centre on the 4K canvas, so overlays and the side layout never cover it."""
    if any(c.empty() for c in CASC):   # this OpenCV ships no cascade files (11-03): Apple Vision via bin/faces
        out = subprocess.run([f"{ED}/bin/faces", path], capture_output=True, text=True).stdout.strip()
        v = out[len(path):].split("|")[0].split() if out.startswith(path) else []
        if len(v) == 4:
            x0, _, x1, _ = map(float, v); w = cv2.imread(path).shape[1]
            return int(round((x0 + x1) / 2 / w * 3840))
        return default
    g = cv2.equalizeHist(cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)); h, w = g.shape; best = None
    for c in CASC:
        for flip in (False, True):
            gg = cv2.flip(g, 1) if flip else g
            for x, y, fw, fh in c.detectMultiScale(gg, scaleFactor=1.08, minNeighbors=3, minSize=(int(h * .18), int(h * .18))):
                if flip: x = w - x - fw
                if y < h * .55 and (best is None or fw * fh > best[2] * best[3]): best = (x, y, fw, fh)
    if best is None: return default
    r = (best[0] + best[2] / 2) / w
    return int(r * 3840) if 0.35 <= r <= 0.65 else default
clips = {}
for line in open(f"{W}/clips_index.txt"):
    k, name, _ = line.rstrip("\n").split("\t"); clips[int(k[1:])] = f"{W}/clips/{name}"
LUT = f"{W}/lut.png" if os.path.exists(f"{W}/lut.png") else f"{ED}/luts/ob_grade_warmtan_hald.png"; TOPO = f"{ED}/assets/topo_bg_preview.jpg"


def shot_at(e):
    for s in shots:
        if s["edit_in"] <= e < s["edit_out"]: return s
    return shots[-1]


def grab_ob(t, framing, path, w):
    vf = ("crop=3200:1800:320:120," if framing == "punch" else "") + f"scale={w}:-2"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", SRC, "-i", LUT, "-filter_complex",
                    f"[0:v]{vf}[v];[v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", "-q:v", "2", path], check=True)


def split_still(t, clip_k, clip_t, path, empty=False):
    ob = path + ".ob.jpg"; grab_ob(t, "wide", ob, 1920)
    canvas = Image.open(TOPO).convert("RGB").resize((1920, 1080)); sx = 0.5
    canvas.paste(Image.open(ob).convert("RGB").crop((int(OB_SRC_X * sx), 0, int((OB_SRC_X + OB_W) * sx), 1080)), (int(OB_X * sx), 0))
    if not empty:
        cl = path + ".cl.jpg"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{max(0, clip_t):.3f}", "-i", clips[clip_k], "-frames:v", "1", "-q:v", "2", cl], check=True)
        c = Image.open(cl).convert("RGB"); ch = 1080; cw = int(c.width * ch / c.height)
        if cw > int(CLIP_W * sx): cw = int(CLIP_W * sx); ch = int(c.height * cw / c.width)
        canvas.paste(c.resize((cw, ch)), (int(CLIP_X * sx) + (int(CLIP_W * sx) - cw) // 2, (1080 - ch) // 2)); os.remove(cl)
    canvas.save(path, quality=90); os.remove(ob)


# no overlay may cross a switch between OB-full and split screen: pull it earlier instead
bounds = [s0["edit_in"] for a, s0 in zip(shots, shots[1:]) if a["layout"] != s0["layout"]]
into_ob = {s0["edit_in"] for a, s0 in zip(shots, shots[1:]) if a["layout"] != s0["layout"] and s0["layout"] == "ob"}
for e in evs:
    if e["type"] in ("montage", "end"): continue
    nxt = next((b for b in bounds if e["edit_in"] < b < e["edit_out"]), None)
    if nxt is not None and nxt - e["edit_in"] < 0.6 and nxt in into_ob:   # it starts just before a clip ends (a graphic on his first word after
        d = e["dur"]; e["edit_in"] = round(nxt + 0.05, 3); e["edit_out"] = round(e["edit_in"] + d, 3)   # a clip, C4407 11-03: the claim labels
        nxt = next((b for b in bounds if e["edit_in"] < b < e["edit_out"]), None)                        # flashed one frame over it): past the switch
    if nxt is not None:   # stamps/pops slide earlier to keep a readable length; everything else keeps its start and ends early
        want = max(1.8, min(e["dur"], 2.4)) if e["type"] in ("stamp", "pop", "title") else 1.5
        if nxt - e["edit_in"] < want: e["edit_in"] = round(max(0, nxt - want), 3)
        e["edit_out"] = round(nxt - 0.05, 3); e["dur"] = round(e["edit_out"] - e["edit_in"], 3)
evs.sort(key=lambda e: e["edit_in"])
for a, b in zip(evs, evs[1:]):
    if a["edit_out"] > b["edit_in"] - 0.05 and a["type"] != "end":
        a["edit_out"] = round(max(a["edit_in"] + 1.2, b["edit_in"] - 0.05), 3); a["dur"] = round(a["edit_out"] - a["edit_in"], 3)
SPAN_DIR = os.path.expanduser(f"~/ob-scratch/{os.path.basename(W.rstrip('/'))}/facespan")


def face_span(e, every=0.25):
    """His face over the whole event on the 4K canvas, (x0, y0, x1, y1): the union of his face box in a frame every 0.25 s of
    each full-frame piece the event covers, in that piece's framing. One still at 1 s missed him leaning into the tags
    (C4407 3:59 and 8:51, 11-03: the icons sat on his ear while he leaned right). None if no frame shows his face."""
    td = f"{SPAN_DIR}/{e['id']}"; shutil.rmtree(td, ignore_errors=True); os.makedirs(td)
    for s_ in shots:
        a, b = max(e["edit_in"], s_["edit_in"]), min(e["edit_out"], s_["edit_out"])
        if b - a < 0.04 or s_["layout"] != "ob": continue
        crop = "crop=3200:1800:320:120," if s_.get("framing") == "punch" else ""
        if b - a >= 0.3:   # a frame every 0.25 s; a sliver of a piece (0.05 s before a cut) gets its middle frame
            cmd = ["-ss", f"{s_['src_in'] + a - s_['edit_in']:.3f}", "-t", f"{b - a:.3f}", "-i", SRC, "-vf", f"{crop}fps={1 / every},scale=960:-2"]
        else: cmd = ["-ss", f"{s_['src_in'] + (a + b) / 2 - s_['edit_in']:.3f}", "-i", SRC, "-vf", f"{crop}scale=960:-2", "-frames:v", "1"]
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + cmd + ["-q:v", "4", "-start_number", str(len(os.listdir(td))), f"{td}/f%04d.jpg"], check=True)
    fs = sorted(os.listdir(td))
    if not fs: return None
    r = subprocess.run([f"{ED}/bin/faces"] + [f"{td}/{f}" for f in fs], capture_output=True, text=True)
    if r.returncode == 3: sys.exit(f"faces: Vision failed on {e['id']} (another job holding the Neural Engine?): {r.stderr[-400:]}")
    boxes = []
    for line in r.stdout.splitlines():
        v = line.split(" ", 1)[1].split("|")[0].split() if " " in line else []
        if len(v) != 4: continue
        x0, y0, x1, y1 = (float(z) * 4 for z in v)   # 960 px frame -> 3840 canvas
        if 0.2 * 3840 < (x0 + x1) / 2 < 0.8 * 3840 and x1 - x0 > 160: boxes.append((x0, y0, x1, y1))
    if not boxes: return None
    return [int(min(b[0] for b in boxes)), int(min(b[1] for b in boxes)), int(max(b[2] for b in boxes)), int(max(b[3] for b in boxes)), len(boxes), len(fs)]


for e in evs:
    rep = e["edit_in"] + min(1.0, e["dur"] / 2)
    s = shot_at(rep); t = s["src_in"] + (rep - s["edit_in"])
    e["on"] = "split" if (s["layout"] == "split" or e["type"] == "montage") else "ob"
    out = f"{H}/assets/stills/{e['id']}.jpg"
    if e["type"] == "montage":
        split_still(t, None, 0, out, empty=True)
        e["items_r"] = []
        for i, it in enumerate(e["items"]):
            if it[0] == "shot":
                e["items_r"].append({"kind": "shot", "file": it[1].replace(".PNG", ".PNG"), "mode": it[2]})
            else:
                k, start = it[1], it[2]; e["items_r"].append({"kind": "clip", "k": k, "start": start})
                subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{start + 0.5:.2f}", "-i", clips[k], "-frames:v", "1", "-q:v", "2",
                                f"{H}/assets/stills/{e['id']}_m{i}.jpg"], check=True)
    elif s["layout"] == "split":
        split_still(t, s["k"], t - s["offset"], out)
    else:
        grab_ob(t, s.get("framing", "wide"), out, 1920)
    if e["on"] == "ob": e["face_cx"] = face_cx(out)
    if e["type"] == "overlay":
        e["items_t"] = item_times(e)
        if e["on"] != "ob": print("! overlay on a split shot:", e["id"])
with ThreadPoolExecutor(6) as ex:
    spans = list(ex.map(face_span, [e for e in evs if e["on"] == "ob" and e["type"] != "montage"]))
for e, sp in zip([e for e in evs if e["on"] == "ob" and e["type"] != "montage"], spans):
    if sp: e["face_x0"], e["face_y0"], e["face_x1"], e["face_y1"], e["face_n"] = sp[:5]
    else: print("! no face found across", e["id"])
json.dump({"events": evs}, open(f"{W}/react_events.json", "w"), indent=1)
print(len(evs), "events prepared; on split:", sum(1 for e in evs if e["on"] == "split"))
