#!/usr/bin/env python3
"""First-3-seconds check for a batch of trial reels (OB, 2026-10-22).

OB's rule (2026-10-20): "in trials it needs to be a different first 3 seconds". A version whose
opening picture matches another version's is not a new trial, whatever its words say. (Same idea as
the "real variation" gate in mbfinotti/advertising-skills ad-hook-analyzer, MIT: if the opening
visual doesn't differ, the platform doesn't see a new variation.)

usage:
  first3_check.py VIDEO VIDEO [VIDEO ...]
  first3_check.py DIR                 every .mp4/.mov in it
  first3_check.py SPEC.json           a trial_variants.py spec: its rendered versions (out/prefix-*.mp4)
  options: --seconds 3   --json OUT.json

For every pair of versions it compares the first N seconds: 4 frames a second at 32x32 grey
(mean absolute difference, 0-255) and the loudness envelope (correlation, 100 ms steps).
  SAME   picture difference under 6: the openings look alike. Fails OB's rule; change one.
  CHECK  under 12, or under 20 with the same sound (correlation 0.9+): look at both openings by eye.
  OK     otherwise.
Calibration (2026-10-22): OB's delivered 0719, 1006 and 1230 batches (49 versions, 393 pairs) give
0 SAME and 0 CHECK, closest pair 14.1. Controls made from MT-B-IR: re-encode 0.6 (SAME), a new
white caption bar 10.4 (CHECK), a new headline block 16.6 with the same sound (CHECK), a 115% punch-in
29.2 (OK: if framing is the only change, decide by eye).
Exit code 1 if any pair is SAME. Standard library + ffmpeg only.
"""
import argparse
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path

FPS, SIZE = 4, 32
SAME_BELOW, CHECK_BELOW = 6.0, 12.0   # calibrated 2026-10-22 on the 0719, 1006 and 1230 trial batches
SAME_SOUND_CHECK_BELOW, SAME_SOUND = 20.0, 0.9
VIDEO_EXT = {'.mp4', '.mov', '.m4v'}


def ffmpeg_bytes(args):
    r = subprocess.run(['ffmpeg', '-v', 'error', *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed: {r.stderr.decode(errors='replace')[-300:]}")
    return r.stdout


def opening(path, seconds):
    raw = ffmpeg_bytes(['-t', str(seconds), '-i', str(path), '-vf',
                        f'fps={FPS},scale={SIZE}:{SIZE}:flags=area,format=gray', '-f', 'rawvideo', '-'])
    n = SIZE * SIZE
    frames = [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]
    pcm = ffmpeg_bytes(['-t', str(seconds), '-i', str(path), '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'])
    env = []
    step = 800 * 2  # 100 ms of 16-bit samples
    for i in range(0, len(pcm) - step + 1, step):
        chunk = memoryview(pcm[i:i + step]).cast('h')
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk)) if len(chunk) else 0.0
        env.append(20 * math.log10(rms + 1e-9) - 90.3)  # dBFS-ish
    return {'frames': frames, 'env': env}


def picture_distance(a, b):
    k = min(len(a), len(b))
    if k == 0:
        return float('nan')
    total = 0.0
    for fa, fb in zip(a[:k], b[:k]):
        total += sum(abs(x - y) for x, y in zip(fa, fb)) / len(fa)
    return total / k


def correlation(a, b):
    k = min(len(a), len(b))
    if k < 5:
        return None
    a, b = a[:k], b[:k]
    ma, mb = sum(a) / k, sum(b) / k
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va < 1e-6 or vb < 1e-6:
        return None  # silence or a flat tone: no shape to compare
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def collect(inputs):
    files = []
    for item in inputs:
        p = Path(item).expanduser()
        if p.suffix.lower() == '.json':
            spec = json.loads(p.read_text())
            out = (p.parent / spec.get('out', '.')).resolve()
            files += sorted(out.glob(f"{spec['prefix']}-*.mp4"))
        elif p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT and not f.name.startswith('.'))
        else:
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('--seconds', type=float, default=3.0)
    ap.add_argument('--json', dest='json_out')
    o = ap.parse_args()
    files = collect(o.inputs)
    if len(files) < 2:
        raise SystemExit('need at least 2 versions to compare')
    data = {}
    for f in files:
        data[f] = opening(f, o.seconds)
    rows = []
    for a, b in itertools.combinations(files, 2):
        pic = picture_distance(data[a]['frames'], data[b]['frames'])
        cor = correlation(data[a]['env'], data[b]['env'])
        same_sound = cor is not None and cor >= SAME_SOUND
        verdict = ('SAME' if pic < SAME_BELOW else
                   'CHECK' if pic < CHECK_BELOW or (same_sound and pic < SAME_SOUND_CHECK_BELOW) else 'OK')
        rows.append({'a': a.name, 'b': b.name, 'picture': round(pic, 1),
                     'sound_corr': None if cor is None else round(cor, 2), 'verdict': verdict})
    rows.sort(key=lambda r: r['picture'])
    same = [r for r in rows if r['verdict'] == 'SAME']
    check = [r for r in rows if r['verdict'] == 'CHECK']
    print(f"first {o.seconds:g} s of {len(files)} versions, {len(rows)} pairs: {len(same)} SAME, {len(check)} CHECK")
    print('picture = mean grey difference 0-255 (under 6 SAME; under 12, or under 20 with sound 0.9+, CHECK)')
    for r in rows:
        if r['verdict'] != 'OK' or len(rows) <= 12:
            snd = '  n/a' if r['sound_corr'] is None else f"{r['sound_corr']:5.2f}"
            print(f"{r['verdict']:5}  picture {r['picture']:5.1f}  sound {snd}  {r['a']}  <>  {r['b']}")
    if len(rows) > 12 and not (same or check):
        print(f"all pairs OK; closest pair: {rows[0]['a']} <> {rows[0]['b']} (picture {rows[0]['picture']})")
    if o.json_out:
        Path(o.json_out).write_text(json.dumps({'seconds': o.seconds, 'files': [str(f) for f in files], 'pairs': rows}, indent=1))
    return 1 if same else 0


if __name__ == '__main__':
    sys.exit(main())
