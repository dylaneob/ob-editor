#!/usr/bin/env python3
"""Mock frames for a reaction reel before anything is rendered: for each time, OB's graded frame with that row's
framing (straight from the camera file) plus the clip frame the panel would show, then viz_shots.js draws the graphics.

  python3 react_mocks.py WORK NAME OUTDIR T1 T2 ...
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lecture_render as L   # noqa: E402

work, name, out = sys.argv[1:4]; times = [float(t) for t in sys.argv[4:]]
spec = json.load(open(f"{work}/{name}_edl.json")); rows = spec["rows"]
take, lutn = L.TAKES[name]
src = next(p for p in (f"/Volumes/T7/{take}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{take}.MP4") if os.path.exists(p))
lut = f"{work}/luts/{lutn}.png"; os.makedirs(f"{out}/src", exist_ok=True)
cw = 1080; ch = round(cw * L.PANEL_H / L.PANEL_W / 2) * 2
shots = []
for t in times:
    i = max(k for k, r in enumerate(rows) if r["edit_in"] <= t + 1e-6); r = rows[i]
    st = r["src_in"] + (t - r["edit_in"]); fr = r.get("framing") or ("punch" if i % 2 else "wide")
    bg = f"{out}/src/bg_{t:05.2f}.jpg"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{st:.3f}", "-i", src, "-i", lut, "-filter_complex",
                    f"[0:v]{L.FRAMES.get(fr, '')}scale=1080:1920:flags=lanczos[v];[v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", "-q:v", "3", bg], check=True)
    shot = {"t": t, "bg": bg, "out": f"{out}/{name}_{t:05.2f}.jpg", "row": i}
    if r.get("panel_in") is not None:
        pt = r["panel_in"] + (t - r["edit_in"]); dy = r.get("panel_dy", 0.0)
        pp = f"{out}/src/panel_{t:05.2f}.jpg"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{pt:.3f}", "-i", spec["clip"]["video"], "-vf",
                        f"crop={cw}:{ch}:0:(ih-{ch})/2+({dy})*(ih-{ch})/2,scale={L.PANEL_W}:{L.PANEL_H}:flags=lanczos", "-frames:v", "1", "-q:v", "3", pp], check=True)
        shot["panel"] = pp
    shots.append(shot)
json.dump(shots, open(f"{out}/shots.json", "w"), indent=1)
r = subprocess.run(["node", os.path.expanduser("~/ob-editor/bin/viz_shots.js"), "mock", f"{work}/hf/compositions/{name}.mock.html", f"{out}/shots.json"],
                   capture_output=True, text=True, cwd=os.path.expanduser("~/ob-editor"))
print(r.stdout.strip() or r.stderr[-800:])
