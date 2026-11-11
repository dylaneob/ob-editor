#!/usr/bin/env python3
"""Free stock video from Mixkit for long-form overlays (OB 10-29, C4395: "you can find better videos to overlays, it doesnt have to
be just me", "really search for overlays and everything"). Mixkit's license: free for commercial use and YouTube, no attribution,
real footage (no AI). Pexels blocks scripted downloads; use the built-in browser for it.

  python3 -I stock_mixkit.py search TERM [TERM ...] [--pages 2]   list clips for a tag (mixkit.co/free-stock-video/TERM/), cache
                                                                  360p previews + a thumbnail strip (3 frames) per clip
  python3 -I stock_mixkit.py sheet TERM [--out FILE]              contact sheet of a term's clips: id, title, three frames each
  python3 -I stock_mixkit.py get ID [ID ...] [--dir DIR]          download the 1080p file of each pick (720p if no 1080p)
  python3 -I stock_mixkit.py info ID                              title, page URL, size and length

Cache: ~/ob-editor/stock/mixkit/ (index.json, prev/ID.mp4, thumb/ID.jpg). Downloads default to OB-ARCHIVE/OB-EDITS/stock/mixkit/.
Every clip used goes in the edit's clearance ledger with its page URL (Mixkit Stock Video Free License).
"""
import json, os, re, subprocess, sys, time, urllib.request

C = os.path.expanduser("~/ob-editor/stock/mixkit"); IDX = f"{C}/index.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
DL = "/Volumes/OB-ARCHIVE/OB-EDITS/stock/mixkit"


def fetch(url, path=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if path: open(path + ".part", "wb").write(data); os.replace(path + ".part", path)
    return data


def load():
    return json.load(open(IDX)) if os.path.exists(IDX) else {"clips": {}, "terms": {}}


def save(ix):
    open(IDX + ".tmp", "w").write(json.dumps(ix, indent=1)); os.replace(IDX + ".tmp", IDX)


def thumbs(cid):
    """Three frames (20/50/80%) of the 360p preview side by side: enough to judge motion and framing from a sheet."""
    p, t = f"{C}/prev/{cid}.mp4", f"{C}/thumb/{cid}.jpg"
    if os.path.exists(t): return t
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout or 0)
    if d <= 0: return None
    fr = []
    for k, f in enumerate((0.2, 0.5, 0.8)):
        o = f"{C}/thumb/{cid}_{k}.jpg"
        subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d * f:.2f}", "-i", p, "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4", "-y", o])
        fr.append(o)
    subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-v", "error"] + sum([["-i", f] for f in fr], []) +
                   ["-filter_complex", "[0][1][2]hstack=3", "-q:v", "4", "-y", t])
    for f in fr: os.remove(f)
    return t


def search(terms, pages):
    ix = load(); os.makedirs(f"{C}/prev", exist_ok=True); os.makedirs(f"{C}/thumb", exist_ok=True)
    for term in terms:
        slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-"); ids = []
        for pg in range(1, pages + 1):
            try: html = fetch(f"https://mixkit.co/free-stock-video/{slug}/" + (f"?page={pg}" if pg > 1 else "")).decode("utf-8", "ignore")
            except Exception as ex: print(f"  {term} page {pg}: {ex}"); break
            found = re.findall(r'href="/free-stock-video/([a-z0-9-]+)-(\d+)/"', html)
            new = [(s, i) for s, i in dict.fromkeys(found) if i not in ids]
            if not new: break
            for s, i in new:
                ids.append(i); ix["clips"].setdefault(i, {"id": i, "title": s.replace("-", " "), "page": f"https://mixkit.co/free-stock-video/{s}-{i}/"})
            time.sleep(1.0)
        ix["terms"][slug] = ids; save(ix)
        got = 0
        for i in ids:
            p = f"{C}/prev/{i}.mp4"
            if not os.path.exists(p):
                try: fetch(f"https://assets.mixkit.co/videos/{i}/{i}-360.mp4", p); got += 1; time.sleep(0.3)
                except Exception as ex: print(f"  preview {i}: {ex}"); continue
            thumbs(i)
        print(f"{term}: {len(ids)} clips ({got} new previews)")


def sheet(term, out):
    from PIL import Image, ImageDraw, ImageFont
    ix = load(); slug = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-"); ids = [i for i in ix["terms"].get(slug, []) if os.path.exists(f"{C}/thumb/{i}.jpg")]
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20); rows = []
    for i in ids:
        im = Image.open(f"{C}/thumb/{i}.jpg").convert("RGB"); im = im.resize((960, int(960 * im.height / im.width)))
        row = Image.new("RGB", (960, im.height + 30), "black"); row.paste(im, (0, 30)); d = ImageDraw.Draw(row)
        d.text((6, 4), f"{i}  {ix['clips'][i]['title'][:90]}", fill="yellow", font=font); rows.append(row)
    if not rows: sys.exit(f"nothing cached for {term}: run search first")
    for k in range(0, len(rows), 8):
        part = rows[k:k + 8]; h = sum(r.height for r in part); cols = 2; per = -(-len(part) // cols)
        sh = Image.new("RGB", (960 * cols, max(sum(r.height for r in part[c * per:(c + 1) * per]) for c in range(cols))), "black")
        for c in range(cols):
            y = 0
            for r in part[c * per:(c + 1) * per]: sh.paste(r, (960 * c, y)); y += r.height
        o = (out or f"{C}/sheet_{slug}") + f"_{k // 8 + 1}.jpg"; sh.save(o, quality=80); print(o)


def get(ids, dest):
    os.makedirs(dest, exist_ok=True); ix = load()
    for i in ids:
        o = f"{dest}/{i}.mp4"
        if os.path.exists(o): print(f"{i}: have it"); continue
        for r in ("1080", "720"):
            try: fetch(f"https://assets.mixkit.co/videos/{i}/{i}-{r}.mp4", o); print(f"{i}: {r}p, {os.path.getsize(o) // 1_000_000} MB  {ix['clips'].get(i, {}).get('page', '')}"); break
            except Exception as ex: last = ex
        else: print(f"{i}: FAILED {last}")
        time.sleep(0.5)


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    pos = [x for j, x in enumerate(a[1:], 1) if not x.startswith("--") and not (j > 1 and a[j - 1].startswith("--"))]
    if a[0] == "search": search(pos, int(opt("--pages", 2)))
    elif a[0] == "sheet": sheet(pos[0], opt("--out"))
    elif a[0] == "get": get(pos, opt("--dir", DL))
    elif a[0] == "info":
        c = load()["clips"].get(pos[0]); print(json.dumps(c, indent=1) if c else "not in the index")
    else: print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
