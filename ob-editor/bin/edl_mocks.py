#!/usr/bin/env python3
"""Frame-by-frame mock stills for a lecture_render EDL: the real source frame at each edit time, framed (FRAMES crop)
and graded (the EDL's LUT) exactly as the render will, with the lecture_viz graphics composited on top.

  python3 edl_mocks.py WORK NAME OUTDIR [T ...]        (no times: one still per row, late enough for its graphic to land)

Writes OUTDIR/NAME_<t>.jpg and prints one line per shot: time, row, source time, framing, caption.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lecture_render as LR   # noqa: E402

BIN = os.path.dirname(os.path.abspath(__file__))


def main():
    work, name, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    spec = json.load(open(f"{work}/{name}_edl.json")); rows = spec["rows"]
    take, lutn = (spec["take"], spec["grade"]) if spec.get("take") and spec.get("grade") else LR.TAKES[name]
    lut = f"{work}/luts/{spec.get('grade', lutn)}.png"
    src = next(p for p in (f"/Volumes/T7/{take}.MP4", f"/Volumes/T7/RAW-FOOTAGE/camera/{take}.MP4") if os.path.exists(p))
    if len(sys.argv) > 4:
        times = [float(t) for t in sys.argv[4:]]
    else:
        times = []
        for r in rows:
            d = r["edit_out"] - r["edit_in"]; fx = r.get("fx") or {}
            times.append(round(r["edit_out"] - 0.12 if fx else r["edit_in"] + 0.6 * d, 2))
    subprocess.run([sys.executable, "-I", f"{BIN}/lecture_viz.py", f"{work}/{name}_edl.json", f"{work}/hf", name, "--mock"],
                   check=True, capture_output=True)
    shots = []
    for t in times:
        i = max(k for k, r in enumerate(rows) if r["edit_in"] <= t + 1e-6)
        r = rows[i]; st = r["src_in"] + (t - r["edit_in"])
        crop = LR.FRAMES.get(r.get("framing") or "wide", "")
        bg = f"{outdir}/_bg_{t:.2f}.png"
        rlut = f"{work}/luts/{r['lut']}.png" if r.get("lut") else lut          # per-line match, as the render does
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{st:.3f}", "-i", src, "-i", rlut, "-filter_complex",
                        f"[0:v]{crop}scale=1080:1920:flags=lanczos[v];[v][1:v]haldclut=interp=tetrahedral", "-frames:v", "1", bg], check=True)
        shots.append({"t": t, "bg": bg, "out": f"{outdir}/{name}_{t:05.2f}.jpg"})
        print(f"{t:6.2f}s  row {i:2d}  src {st:7.2f}  {r.get('framing', 'wide'):9s} | {r['caption']}")
    sj = f"{outdir}/_shots_{name}.json"; json.dump(shots, open(sj, "w"))
    subprocess.run(["node", f"{BIN}/viz_shots.js", "mock", f"{work}/hf/compositions/{name}.mock.html", sj], check=True, cwd=os.path.dirname(BIN))
    for s in shots: os.remove(s["bg"])


if __name__ == "__main__":
    main()
