#!/usr/bin/env python3
"""Quality score for an export: Netflix's VMAF (0-100) of DIST against REF, frame-aligned, so "the render looks worse than
what I shot" becomes a number before OB ever sees the file (OB 2026-10-20 picked this upgrade after the 4K-to-shitty-render note).

  python3 vmaf_check.py REF DIST [--ref-start S] [--dist-start S] [--dur D] [--size WxH] [--phone] [--sub N] [--json OUT]

- REF is what the export should look like (the source segment, the graded master, the posted reel for an unchanged tail).
- Both are trimmed, set to the same fps, and REF is scaled to DIST's size (or --size) with bicubic before scoring.
- --phone uses VMAF's phone model (viewing on a phone: scores run higher). The default model is the stricter one.
- --sub N scores every Nth frame (default 1; use 2-5 on long videos).

Working rule (ours, not a standard): mean >= 93 and 1%-low >= 85 is a clean export; under 90 mean means the encode is
visibly losing detail. Exit code 0 = pass, 3 = fail, so other tools can gate on it.
"""
import argparse, json, os, subprocess, sys, tempfile


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                          "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out); s = d["streams"][0]; n, m = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(m), float(d["format"]["duration"])


def score(ref, dist, ref_start=0.0, dist_start=0.0, dur=None, size=None, phone=False, sub=1, threads=4):
    rw, rh, rfps, rdur = probe(ref); dw, dh, dfps, ddur = probe(dist)
    w, h = size or (dw, dh)
    dur = dur or min(rdur - ref_start, ddur - dist_start)
    log = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    model = "version=vmaf_v0.6.1" + ("\\:enable_transform=true" if phone else "")
    # start half a frame early on both sides: a start rounded up past a frame's timestamp drops that frame, and a one-frame
    # offset scored the 1230 B-GY tail 70.6 (1%-low 2.1) against the same frames that score 97 aligned (10-21)
    rs, ds = max(0.0, ref_start - 0.5 / rfps), max(0.0, dist_start - 0.5 / dfps)
    fc = (f"[0:v]trim=start={rs:.5f}:duration={dur:.4f},setpts=PTS-STARTPTS,fps={dfps},scale={w}:{h}:flags=bicubic,format=yuv420p[r];"
          f"[1:v]trim=start={ds:.5f}:duration={dur:.4f},setpts=PTS-STARTPTS,fps={dfps},scale={w}:{h}:flags=bicubic,format=yuv420p[d];"
          f"[d][r]libvmaf=model={model}:n_threads={threads}:n_subsample={sub}:log_fmt=json:log_path={log}")
    p = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", ref, "-i", dist, "-lavfi", fc, "-f", "null", "-"],
                       capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-2000:])
    d = json.load(open(log)); os.unlink(log)
    frames = [(f["frameNum"], f["metrics"]["vmaf"]) for f in d["frames"]]
    vals = sorted(v for _, v in frames)
    p1 = vals[max(0, int(len(vals) * 0.01) - 1)] if vals else 0.0
    # worst one-second windows (start time in DIST, mean score), so a bad stretch can be found and looked at
    per = {}
    for n, v in frames: per.setdefault(int(n * sub / dfps), []).append(v)
    worst = sorted(((sec + dist_start, sum(v) / len(v)) for sec, v in per.items()), key=lambda x: x[1])[:3]
    pooled = d["pooled_metrics"]["vmaf"]
    res = dict(ref=ref, dist=dist, size=f"{w}x{h}", seconds=round(dur, 2), model="phone" if phone else "default",
               mean=round(pooled["mean"], 2), harmonic=round(pooled["harmonic_mean"], 2), min=round(pooled["min"], 2), p1=round(p1, 2),
               worst_seconds=[(round(t, 1), round(v, 1)) for t, v in worst])
    res["pass"] = res["mean"] >= 93 and res["p1"] >= 85
    return res


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("ref"); a.add_argument("dist")
    a.add_argument("--ref-start", type=float, default=0.0); a.add_argument("--dist-start", type=float, default=0.0)
    a.add_argument("--dur", type=float); a.add_argument("--size"); a.add_argument("--phone", action="store_true")
    a.add_argument("--sub", type=int, default=1); a.add_argument("--threads", type=int, default=4); a.add_argument("--json")
    o = a.parse_args()
    size = tuple(int(x) for x in o.size.lower().split("x")) if o.size else None
    r = score(o.ref, o.dist, o.ref_start, o.dist_start, o.dur, size, o.phone, o.sub, o.threads)
    print(f"VMAF {r['mean']} mean | {r['p1']} 1%-low | {r['min']} min | {r['seconds']} s at {r['size']} ({r['model']} model) | "
          f"worst seconds {r['worst_seconds']} | {'PASS' if r['pass'] else 'FAIL'}")
    if o.json: json.dump(r, open(o.json, "w"), indent=1)
    sys.exit(0 if r["pass"] else 3)


if __name__ == "__main__":
    main()
