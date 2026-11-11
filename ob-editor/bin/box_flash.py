#!/usr/bin/env python3
"""box_flash.py - Artzen "box flash" word captions (OB 2026-10-29, from the Breaking Reels tutorial).

Every spoken word first shows as a SOLID WHITE BOX for 2 frames (the text background on, white, opacity 100),
then continues as plain white text, word by word, timed to the voice. Words build up into short chunks
(a phrase of up to --max-words), the way the demo stacks "For / anyone / of our".

  python3 box_flash.py IN.mp4 OUT.mp4 [--words words.json] [--font PATH] [--size 64] [--y 0.72]
                       [--flash 2] [--max-words 3] [--stroke 0] [--start S --dur D]

Words: --words takes [{"w","s","e"}] (seconds). Without it the audio is transcribed on-device
(bin/speech_words, Apple SpeechTranscriber), falling back to whisper.cpp medium (-ml 1).
Recipe values that are Artzen's instruction: 2 frames, white, opacity 100. Font/size are OB's house style, not his.
Style card: ~/ob-editor/styles/artzen-breaking-reels.md. Test it as one variable vs OB's current captions (skip rate).

2026-11-04 upgrade (OB: "Yes, upgrade it", after re-sending the tutorial, reel DfUmDI2Py8Z):
  --layout stack (default): Artzen's stacked block. Words fill lines of --line-chars, up to --lines lines; a pause of 0.35 s
           or a full block starts the next block. The whole block is laid out first, so nothing shifts as words land.
  --layout line: the 10-29 behaviour (one line of up to --max-words).
  Every word on a line sits on one baseline (10-29 bug: each word was centred on its own ink, so "your" rode higher than
  "for" and looked overlapped). Brand defaults: Big Shoulders ExtraBold, upper case, the brand's soft shadow (--shadow 0 off).
  The flash is 2 frames of white, not a box behind the text, so the brand's no-boxes rule still holds.
"""
import argparse, json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

BIN = os.path.dirname(os.path.abspath(__file__))
FALLBACK_FONT = '/System/Library/Fonts/HelveticaNeue.ttc'
BRAND = json.load(open(os.path.expanduser('~/ob-editor/brand/brand.json')))
BRAND_FONT = os.path.expanduser(BRAND['font'])


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=width,height,r_frame_rate,duration', '-show_entries', 'format=duration',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    j = json.loads(out); s = j['streams'][0]
    n, d = s['r_frame_rate'].split('/')
    # the video stream's own length: the container's runs on with the audio tail (11-04: 3 extra frames hit a closed pipe)
    return s['width'], s['height'], float(n) / float(d), float(s.get('duration') or j['format']['duration'])


def transcribe(video, start, dur, tmp):
    wav = os.path.join(tmp, 'a.wav')
    cmd = ['ffmpeg', '-v', 'error', '-y']
    if start: cmd += ['-ss', str(start)]
    cmd += ['-i', video]
    if dur: cmd += ['-t', str(dur)]
    subprocess.run(cmd + ['-ac', '1', '-ar', '16000', wav], check=True)
    sw = os.path.join(BIN, 'speech_words')
    if os.path.exists(sw):
        r = subprocess.run([sw, 'words', wav], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip().startswith('['):
            return json.loads(r.stdout)
    model = os.path.expanduser('~/.whisper-models/ggml-medium.en.bin')
    subprocess.run(['whisper-cli', '-m', model, '-f', wav, '-ml', '1', '-sow', '-oj', '-of',
                    os.path.join(tmp, 'w')], capture_output=True, check=True)
    j = json.load(open(os.path.join(tmp, 'w.json')))
    words = []
    for seg in j['transcription']:
        t = seg['text'].strip()
        if t:
            words.append({'w': t, 's': seg['offsets']['from'] / 1000, 'e': seg['offsets']['to'] / 1000})
    return words


def chunks(words, max_words, gap=0.35, max_len=1.6):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w['s'] - cur[-1]['e'] > gap or w['e'] - cur[0]['s'] > max_len):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out


def blocks(words, line_chars, max_lines, gap=0.35, max_len=2.6):
    """Artzen's stacked blocks: [[line words, ...], ...] per block; a pause, a full block or a long block starts the next."""
    out, cur, line = [], [], []
    def close():
        nonlocal cur, line
        if line: cur.append(line)
        if cur: out.append(cur)
        cur, line = [], []
    last = None
    for w in words:
        first = (cur or line) and (cur[0][0] if cur else line[0])
        if last and (w['s'] - last['e'] > gap or (first and w['e'] - first['s'] > max_len)): close()
        if line and len(' '.join(x['w'] for x in line + [w])) > line_chars:
            cur.append(line); line = []
            if len(cur) >= max_lines: close()
        line.append(w); last = w
    close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--words'); ap.add_argument('--font', default=BRAND_FONT if os.path.exists(BRAND_FONT) else FALLBACK_FONT)
    ap.add_argument('--weight', default=BRAND['caption']['weight'], help='variable-font weight name (brand: ExtraBold)')
    ap.add_argument('--layout', choices=['stack', 'line'], default='stack')
    ap.add_argument('--lines', type=int, default=3, help='stack: lines per block')
    ap.add_argument('--line-chars', type=int, default=10, help='stack: characters per line')
    ap.add_argument('--case', choices=['upper', 'asis'], default='upper' if BRAND['caption']['case'] == 'upper' else 'asis')
    ap.add_argument('--shadow', type=int, default=1, help='brand soft shadow under the words (0 = Artzen look)')
    ap.add_argument('--font-index', type=int, default=0)
    ap.add_argument('--size', type=int, default=96, help='px at 1080 wide; scaled to the video')
    ap.add_argument('--y', type=float, default=0.62, help='caption block centre, fraction of height (0.62 keeps a 3-line block out of the IG bottom band)')
    ap.add_argument('--flash', type=int, default=2, help='frames of solid white box per word')
    ap.add_argument('--max-words', type=int, default=3)
    ap.add_argument('--stroke', type=int, default=0, help='black outline px (0 = Artzen look)')
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--dur', type=float, default=0)
    a = ap.parse_args()

    W, H, fps, total = probe(a.inp)
    dur = a.dur or (total - a.start)
    with tempfile.TemporaryDirectory() as tmp:
        words = json.load(open(a.words)) if a.words else transcribe(a.inp, a.start, a.dur, tmp)
    words = [dict(w, w=(w['w'].strip().upper() if a.case == 'upper' else w['w'].strip())) for w in words if w['w'].strip()]
    if not words: sys.exit('no words')
    cks = [[ln] for ln in chunks(words, a.max_words)] if a.layout == 'line' else blocks(words, a.line_chars, a.lines)
    k = W / 1080
    font = ImageFont.truetype(a.font, int(a.size * k), index=a.font_index)
    try: font.set_variation_by_name(a.weight)
    except Exception: pass
    pad_x, pad_y, space = int(10 * k), int(6 * k), font.getlength(' ')
    asc, desc = font.getmetrics(); lh = int((asc + desc) * 0.92)   # tight stacked lines, as in the reel
    cy = int(a.y * H)
    shadow = (int(W * BRAND['shadow']['y_of_width']), W * BRAND['shadow']['blur_of_width'] / 2, BRAND['shadow']['alpha']) if a.shadow else None

    # block end = next block start (or last word end + 0.3 s); each word's place is fixed for its whole block
    first = lambda b: b[0][0]; lastw = lambda b: b[-1][-1]
    ends = [first(cks[i + 1])['s'] if i + 1 < len(cks) else lastw(cks[i])['e'] + 0.3 for i in range(len(cks))]
    place = []
    for b in cks:
        top = cy - (len(b) * lh) // 2; pl = []
        for li, ln in enumerate(b):
            base = top + li * lh + asc; x = (W - (sum(font.getlength(w['w']) for w in ln) + space * (len(ln) - 1))) / 2
            for w in ln: pl.append((w, int(round(x)), base)); x += font.getlength(w['w']) + space
        place.append(pl)
    flash_s = a.flash / fps
    blank = bytes(W * H * 4)
    cache = {}

    def frame(t):
        for ci, pl in enumerate(place):
            if first(cks[ci])['s'] <= t < ends[ci]:
                shown = [i for i, (w, x, b) in enumerate(pl) if w['s'] <= t]
                boxed = tuple(i for i in shown if t < pl[i][0]['s'] + flash_s)
                key = (ci, len(shown), boxed)
                if key not in cache:
                    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
                    sh = Image.new('L', (W, H), 0); ds = ImageDraw.Draw(sh)
                    for i in shown:
                        w, x, base = pl[i]
                        bx = d.textbbox((x, base), w['w'], font=font, anchor='ls')   # the word's ink on its line's baseline
                        if i in boxed:
                            d.rectangle([bx[0] - pad_x, bx[1] - pad_y, bx[2] + pad_x, bx[3] + pad_y], fill=(255, 255, 255, 255))
                        else:
                            d.text((x, base), w['w'], font=font, anchor='ls', fill=(255, 255, 255, 255),
                                   stroke_width=int(a.stroke * k), stroke_fill=(0, 0, 0, 255))
                            if shadow: ds.text((x, base + shadow[0]), w['w'], font=font, anchor='ls', fill=255)
                    if shadow:
                        from PIL import ImageFilter
                        sh = sh.filter(ImageFilter.GaussianBlur(shadow[1])).point(lambda v: int(v * shadow[2]))
                        out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.putalpha(sh); out.alpha_composite(im); im = out
                    cache[key] = im.tobytes()
                return cache[key]
        return blank

    cmd = ['ffmpeg', '-v', 'error', '-y']
    if a.start: cmd += ['-ss', str(a.start)]
    if a.dur: cmd += ['-t', str(a.dur)]          # input option on the video, BEFORE -i (after it, it would bind to the pipe)
    cmd += ['-i', a.inp]
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
            '-filter_complex', '[0:v][1:v]overlay=0:0:eof_action=pass[v]', '-map', '[v]', '-map', '0:a?',
            '-c:v', 'h264_videotoolbox', '-b:v', '10M', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(round(dur * fps))
    try:
        for i in range(n): p.stdin.write(frame(i / fps))
        p.stdin.close()
    except BrokenPipeError: pass   # ffmpeg took every frame the video has
    p.wait()
    if p.returncode: sys.exit('ffmpeg failed')
    print(f'{a.out}: {len(words)} words, {len(cks)} {"blocks" if a.layout == "stack" else "chunks"}, flash {a.flash} frames @ {fps:g} fps')


if __name__ == '__main__':
    main()
