#!/usr/bin/env python3
"""Free stock video from Pexels for long-form overlays (OB 10-29, C4395: "you can find better videos to overlays, it doesnt have to
be just me"). Pexels license: free for commercial use and YouTube, no attribution required. Pexels blocks scripted page loads, so
the search runs inside the built-in browser (on a pexels.com tab) and posts its results to a receiver on this Mac; the video files
themselves come straight off the videos.pexels.com CDN.

  python3 -I stock_pexels.py js "term 1" "term 2" [--per 12]   print the search JS: run it in a pexels.com tab (javascript_tool),
                                                    save what it returns (lines "#term" then "id|dur|file|slug") to a text file
  python3 -I stock_pexels.py import FILE           add those results to the index + a 3-frame strip per clip (frames off the CDN)
  python3 -I stock_pexels.py sheet TERM [--out F]  contact sheet: id, description, length, three frames per clip
  python3 -I stock_pexels.py get ID [ID ...] [--dir DIR]   download the 1080p (or best landscape <= 1920) file of each pick

Cache: ~/ob-editor/stock/pexels/ (index.json, prev/, thumb/). Downloads default to OB-ARCHIVE/OB-EDITS/stock/pexels/.
Skip anything that looks AI-made, and log every clip used in the edit's clearance ledger with its page URL.
"""
import json, os, re, subprocess, sys, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

C = os.path.expanduser("~/ob-editor/stock/pexels"); IDX = f"{C}/index.json"; PORT = 8765
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
DL = "/Volumes/OB-ARCHIVE/OB-EDITS/stock/pexels"
slugify = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def load():
    return json.load(open(IDX)) if os.path.exists(IDX) else {"clips": {}, "terms": {}}


def save(ix):
    open(IDX + ".tmp", "w").write(json.dumps(ix, indent=1)); os.replace(IDX + ".tmp", IDX)


class H(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Headers", "*"); self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204); self.cors(); self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        ix = load(); term = slugify(body.get("term", "")); ids = ix["terms"].setdefault(term, [])
        for c in body.get("items", []):
            if not c.get("hd"): continue
            ix["clips"].setdefault(c["id"], c)
            if c["id"] not in ids: ids.append(c["id"])
        save(ix); self.send_response(200); self.cors(); self.end_headers(); self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


JS = r"""(async () => {
  const terms = %s, pages = %d, out = [];
  for (const term of terms) for (let p = 1; p <= pages; p++) {
    const h = await (await fetch(`/search/videos/${encodeURIComponent(term)}/?orientation=landscape&page=${p}`)).text();
    const m = h.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
    if (!m) { out.push(term + ': no data'); break; }
    const items = JSON.parse(m[1]).props.pageProps.initialData.data.filter(x => x.type === 'video').map(x => {
      const a = x.attributes, f = (a.video && a.video.video_files) || [], land = f.filter(v => v.width >= v.height);
      const hd = land.filter(v => v.width <= 1920).sort((u, v) => v.width - u.width)[0];
      const sd = land.filter(v => v.width <= 960).sort((u, v) => v.width - u.width)[0] || hd;
      return {id: String(a.id), slug: a.slug, desc: a.description || a.title || '', w: a.width, h: a.height, dur: a.duration,
              user: a.user && a.user.username, tags: (a.tags || []).slice(0, 8), hd: hd && hd.link, sd: sd && sd.link,
              page: `https://www.pexels.com/video/${a.slug}-${a.id}/`};
    });
    await fetch('http://127.0.0.1:%d/add', {method: 'POST', body: JSON.stringify({term, items})});
    out.push(`${term} p${p}: ${items.length}`);
    await new Promise(r => setTimeout(r, 600));
  }
  return out.join('; ');
})()"""


JSC = r"""(async () => {
  const terms = %s, out = [];
  for (const term of terms) {
    const h = await (await fetch(`/search/videos/${encodeURIComponent(term)}/?orientation=landscape`)).text();
    const m = h.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
    if (!m) { out.push('#' + term + ' nodata'); continue; }
    out.push('#' + term);
    JSON.parse(m[1]).props.pageProps.initialData.data.filter(x => x.type === 'video').slice(0, %d).forEach(x => {
      const a = x.attributes, f = (a.video && a.video.video_files) || [], land = f.filter(v => v.width >= v.height);
      const hd = land.filter(v => v.width <= 1920).sort((u, v) => v.width - u.width)[0];
      if (hd) out.push([a.id, a.duration, hd.link.split('/').pop(), a.slug.slice(0, 60)].join('|'));
    });
    await new Promise(r => setTimeout(r, 500));
  }
  return out.join('\n');
})()"""


def imp(path):
    """Import compact results (#term lines, then id|dur|file|slug) and make a 3-frame strip per new clip straight off the CDN."""
    ix = load(); os.makedirs(f"{C}/thumb", exist_ok=True); term = None; raw = open(path).read().replace("\\n", "\n")
    for ln in raw.splitlines():
        ln = ln.strip().strip('"')
        if not ln: continue
        if ln.startswith("#"): term = slugify(ln[1:].replace(" nodata", "")); ix["terms"].setdefault(term, []); continue
        i, d, f, slug = ln.split("|", 3)
        ix["clips"].setdefault(i, {"id": i, "dur": int(float(d)), "hd": f"https://videos.pexels.com/video-files/{i}/{f}", "desc": slug.replace("-", " "),
                                   "page": f"https://www.pexels.com/video/{slug}-{i}/"})
        if term is not None and i not in ix["terms"][term]: ix["terms"][term].append(i)
    save(ix); n = 0
    for i, c in ix["clips"].items():
        if os.path.exists(f"{C}/thumb/{i}.jpg"): continue
        d = max(c.get("dur", 10), 2); fr = []
        for k, f in enumerate((0.2, 0.5, 0.8)):
            o = f"{C}/thumb/{i}_{k}.jpg"
            subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d * f:.2f}", "-i", c["hd"], "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4", "-y", o], timeout=90)
            if os.path.exists(o): fr.append(o)
        if len(fr) == 3:
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", fr[0], "-i", fr[1], "-i", fr[2], "-filter_complex", "[0][1][2]hstack=3", "-q:v", "4", "-y", f"{C}/thumb/{i}.jpg"]); n += 1
        for f in fr: os.remove(f)
    print(f"imported; {n} new thumbnails; {len(ix['clips'])} clips in the index")


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r: data = r.read()
    open(path + ".part", "wb").write(data); os.replace(path + ".part", path)


def thumbs(cid):
    p, t = f"{C}/prev/{cid}.mp4", f"{C}/thumb/{cid}.jpg"
    if os.path.exists(t): return t
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout or 0)
    if d <= 0: return None
    fr = []
    for k, f in enumerate((0.2, 0.5, 0.8)):
        o = f"{C}/thumb/{cid}_{k}.jpg"; fr.append(o)
        subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d * f:.2f}", "-i", p, "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4", "-y", o])
    subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-v", "error"] + sum([["-i", f] for f in fr], []) + ["-filter_complex", "[0][1][2]hstack=3", "-q:v", "4", "-y", t])
    for f in fr:
        if os.path.exists(f): os.remove(f)
    return t


def prev(terms):
    ix = load(); os.makedirs(f"{C}/prev", exist_ok=True); os.makedirs(f"{C}/thumb", exist_ok=True)
    ids = [i for t in (terms or ix["terms"]) for i in ix["terms"].get(slugify(t), [])]
    got = 0
    for i in dict.fromkeys(ids):
        c = ix["clips"][i]; p = f"{C}/prev/{i}.mp4"
        if not os.path.exists(p):
            try: fetch(c["sd"], p); got += 1; time.sleep(0.2)
            except Exception as ex: print(f"  {i}: {ex}"); continue
        thumbs(i)
    print(f"previews: {got} new, {len(set(ids))} clips")


def sheet(term, out):
    from PIL import Image, ImageDraw, ImageFont
    ix = load(); ids = [i for i in ix["terms"].get(slugify(term), []) if os.path.exists(f"{C}/thumb/{i}.jpg")]
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20); rows = []
    for i in ids:
        c = ix["clips"][i]; im = Image.open(f"{C}/thumb/{i}.jpg").convert("RGB"); im = im.resize((960, int(960 * im.height / im.width)))
        row = Image.new("RGB", (960, im.height + 30), "black"); row.paste(im, (0, 30))
        ImageDraw.Draw(row).text((6, 4), f"P{i} {c.get('dur', '?')}s  {c['desc'][:80]}", fill="yellow", font=font); rows.append(row)
    if not rows: sys.exit(f"nothing cached for {term}: harvest and run prev first")
    for k in range(0, len(rows), 10):
        part = rows[k:k + 10]; per = -(-len(part) // 2)
        sh = Image.new("RGB", (1920, max(sum(r.height for r in part[c * per:(c + 1) * per]) for c in range(2))), "black")
        for c in range(2):
            y = 0
            for r in part[c * per:(c + 1) * per]: sh.paste(r, (960 * c, y)); y += r.height
        o = (out or f"{C}/sheet_{slugify(term)}") + f"_{k // 10 + 1}.jpg"; sh.save(o, quality=80); print(o)


def get(ids, dest):
    os.makedirs(dest, exist_ok=True); ix = load()
    for i in ids:
        i = i.lstrip("P"); c = ix["clips"].get(i); o = f"{dest}/{i}.mp4"
        if not c: print(f"{i}: not in the index"); continue
        if os.path.exists(o): print(f"{i}: have it"); continue
        try: fetch(c["hd"], o); print(f"{i}: {os.path.getsize(o) // 1_000_000} MB  {c['page']}")
        except Exception as ex: print(f"{i}: FAILED {ex}")
        time.sleep(0.3)


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    pos = [x for j, x in enumerate(a[1:], 1) if not x.startswith("--") and not a[j - 1].startswith("--")]
    if a[0] == "serve": os.makedirs(C, exist_ok=True); HTTPServer(("127.0.0.1", PORT), H).serve_forever()
    elif a[0] == "js": print(JSC % (json.dumps(pos), int(opt("--per", 12))))   # run in a pexels.com tab; save its output to a file
    elif a[0] == "import": imp(pos[0])
    elif a[0] == "prev": prev(pos)
    elif a[0] == "sheet": sheet(pos[0], opt("--out"))
    elif a[0] == "get": get(pos, opt("--dir", DL))
    else: print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
