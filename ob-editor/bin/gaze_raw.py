#!/usr/bin/env python3
"""Eye-line scan of a whole raw take, before any cut exists (C4367, 2026-10-19).
OB: "if i look away cut it". He reads each line off a screen below the lens, head down, then says it to camera,
so the take alternates between reading and delivering. This samples every STEP-th source frame (exact frame
numbers), crops to the face area, runs `gaze` (Apple Vision: head pitch/yaw, pupil position, eye openness) and
writes one row per sample. With the cap on, a bowed head often hides the face entirely: that row has open = None.

  python3 -I gaze_raw.py CAMERA.MP4 OUT.json [--step 2] [--crop 1600:1300:1100:350] [--width 800] [--chunk 120]

Chunks of CHUNK s are decoded, scanned and deleted one at a time, so the frames never pile up on disk.
Resumable: chunks already in OUT.json are skipped.
"""
import argparse, glob, json, os, shutil, subprocess, tempfile, time

GAZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gaze")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--step", type=int, default=2); ap.add_argument("--crop", default="1600:1300:1100:350")
    ap.add_argument("--width", type=int, default=800); ap.add_argument("--chunk", type=float, default=120.0)
    a = ap.parse_args()
    pr = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,nb_frames",
                                  "-of", "csv=p=0", a.video], text=True).strip().split(",")
    num, den = map(int, pr[0].split("/")); fps = num / den; nfr = int(pr[1])
    done = json.load(open(a.out)) if os.path.exists(a.out) else {"fps": fps, "step": a.step, "crop": a.crop, "chunks": {}, "rows": []}
    per = int(round(a.chunk * fps / a.step)) * a.step        # frames per chunk, a multiple of STEP
    tmp = tempfile.mkdtemp(prefix="gaze_raw_", dir=os.path.dirname(os.path.abspath(a.out)))
    try:
        for k0 in range(0, nfr, per):
            if str(k0) in done["chunks"]: continue
            t_start = time.time()
            for f in glob.glob(f"{tmp}/*.jpg"): os.remove(f)
            ss = (k0 - 0.5) / fps if k0 else 0.0                # half a frame early: the first decoded frame is exactly k0
            n = min(per, nfr - k0)
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{ss:.6f}", "-i", a.video,
                            "-frames:v", str(-(-n // a.step)), "-vf", f"select='not(mod(n\\,{a.step}))',crop={a.crop},scale={a.width}:-2",
                            "-fps_mode", "passthrough", "-q:v", "4", f"{tmp}/%06d.jpg"], check=True)
            files = sorted(glob.glob(f"{tmp}/*.jpg"))
            if len(files) != -(-n // a.step):                    # a dropped frame would shift every time after it
                raise SystemExit(f"chunk at frame {k0}: {len(files)} frames decoded, expected {-(-n // a.step)}")
            lines = []
            for b in range(0, len(files), 400):
                lines += subprocess.run([GAZE, *files[b:b + 400]], capture_output=True, text=True).stdout.strip().split("\n")
            rows = []
            for line in lines:
                p = line.split()
                if not p: continue
                j = int(os.path.basename(p[0])[:6]) - 1; fr = k0 + j * a.step
                num_ = lambda s: None if s in ("nan", "-") else float(s)
                if len(p) < 6: rows.append([fr, round(fr / fps, 3), None, None, None, None, None]); continue
                rows.append([fr, round(fr / fps, 3), num_(p[1]), num_(p[2]), num_(p[3]), num_(p[4]), num_(p[5])])
            done["rows"] += rows; done["chunks"][str(k0)] = len(rows)
            json.dump(done, open(a.out + ".tmp", "w")); os.replace(a.out + ".tmp", a.out)
            face = sum(r[6] is not None for r in rows)
            print(f"chunk {k0 / fps / 60:5.1f} min: {len(rows)} samples, eyes found in {face}, {time.time() - t_start:.0f} s", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    done["rows"].sort(key=lambda r: r[0]); json.dump(done, open(a.out, "w"))
    print(f"done: {len(done['rows'])} samples")


if __name__ == "__main__":
    main()
