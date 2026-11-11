#!/usr/bin/env python3
"""Bring a finished master's true peak under the QC gate's -1 dBTP (C4398, 2026-10-30: assemble.py's loudnorm aims at -1.5 dBTP,
the AAC encode overshot that to -0.7 and the gate failed the film). Re-encodes only the sound, from the render's float mix
(WORK/render/mix.wav), with loudnorm at a lower true-peak target, copies the picture, and replaces the master only when the new
file passes the gate's audio rule (true peak -1 dBTP or lower, no flat tops, -14 +-1.5 LUFS). Measured with voice_master.check,
the gate's own meter.

  python3 -I tp_fix.py MASTER.mp4 MIX.wav
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voice_master as VM


def loudnorm(mix, tp):
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", mix, "-af", f"loudnorm=I=-14:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    s = r.stderr; ln = json.loads(s[s.rfind("{"): s.rfind("}") + 1])
    return (f"loudnorm=I=-14:TP={tp}:LRA=11:measured_I={ln['input_i']}:measured_TP={ln['input_tp']}:measured_LRA={ln['input_lra']}:"
            f"measured_thresh={ln['input_thresh']}:offset={ln['target_offset']}:linear=true")


def ok(r):
    return r["true_peak"] is not None and r["true_peak"] <= -1.0 and r["flat_tops"] == 0 and r["lufs"] is not None and -15.5 <= r["lufs"] <= -12.5


def main():
    master, mix = sys.argv[1], sys.argv[2]
    r = VM.check(master); print(f"tp_fix before: {r['lufs']} LUFS, true peak {r['true_peak']} dBTP, flat tops {r['flat_tops']}", flush=True)
    if ok(r): print("tp_fix: already passes, left as it is"); return
    tmp = master[:-4] + ".tpfix.mp4"
    for tp in (-2.0, -2.5, -3.0):
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", master, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", loudnorm(mix, tp) + ",aresample=48000", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-shortest", tmp],
                       check=True)
        q = VM.check(tmp); print(f"tp_fix target {tp} dBTP: {q['lufs']} LUFS, true peak {q['true_peak']} dBTP, flat tops {q['flat_tops']}", flush=True)
        if ok(q):
            os.replace(tmp, master); print("tp_fix: replaced", master); return
    os.remove(tmp); sys.exit("tp_fix: no target passed, master left as it was")


if __name__ == "__main__":
    main()
