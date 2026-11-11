"""List (and optionally download) an iCloud shared album via the public web-stream API (no login, no key).
  python3 -I icloud_album.py TOKEN OUT_JSON            -> metadata only (count, captions, contributors, dates)
  SINCE=2026-07-02 python3 -I icloud_album.py TOKEN OUT_JSON DEST_DIR -> download photos added after SINCE (largest JPEG)
"""
import json, sys, urllib.request, os

tok, out = sys.argv[1], sys.argv[2]
dest = sys.argv[3] if len(sys.argv) > 3 else None
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
def b62(s):
    n = 0
    for c in s: n = n * 62 + B62.index(c)
    return n
part = b62(tok[1]) if tok[0] == "A" else b62(tok[1:3]) if tok[0] == "B" else 1
host = f"p{part:02d}-sharedstreams.icloud.com"

def post(path, body):
    global host
    for _ in range(3):
        req = urllib.request.Request(f"https://{host}/{tok}/sharedstreams/{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "text/plain", "Origin": "https://www.icloud.com", "User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 330:
                host = json.load(e)["X-Apple-MMe-Host"]; continue
            raise
    raise SystemExit("redirect loop")

ws = post("webstream", {"streamCtag": None})
photos = ws.get("photos", [])
print("album:", ws.get("streamName"), "| owner:", ws.get("userFirstName"), ws.get("userLastName"), "| items:", len(photos))
rows = []
for p in photos:
    ders = p.get("derivatives", {})
    best = max(ders.values(), key=lambda d: int(d.get("width", 0)) * int(d.get("height", 0))) if ders else {}
    rows.append({"guid": p["photoGuid"], "created": p.get("dateCreated"), "caption": p.get("caption"),
                 "contributor": p.get("contributorFullName"), "type": p.get("mediaAssetType", "image"),
                 "w": best.get("width"), "h": best.get("height"), "bytes": int(best.get("fileSize", 0)),
                 "checksum": best.get("checksum")})
tot = sum(r["bytes"] for r in rows)
print(f"largest-derivative total: {tot/1e6:.1f} MB | videos: {sum(1 for r in rows if r['type']=='video')}")
caps = [r["caption"] for r in rows if r["caption"]]
print("captions:", len(caps), caps[:40])
print("contributors:", sorted({r['contributor'] for r in rows if r['contributor']}))
ds = sorted(r["created"] for r in rows if r["created"])
print("dates:", ds[:1], ds[-1:])
json.dump(rows, open(out, "w"), indent=1)

if dest:
    os.makedirs(dest, exist_ok=True)
    since = os.environ.get("SINCE", "")
    rows = [r for r in rows if r["type"] != "video" and (r["created"] or "") > since]
    guids = [r["guid"] for r in rows]
    urls = {}
    for i in range(0, len(guids), 25):
        res = post("webasseturls", {"photoGuids": guids[i:i + 25]})
        for ck, it in res.get("items", {}).items():
            urls[ck] = f"https://{it['url_location']}{it['url_path']}"
    n = 0
    for k, r in enumerate(rows):
        u = urls.get(r["checksum"])
        if not u: continue
        fn = os.path.join(dest, r["guid"][:8] + ".jpg")
        if os.path.exists(fn) and os.path.getsize(fn) == r["bytes"]: n += 1; continue
        urllib.request.urlretrieve(u, fn); n += 1
    print("downloaded", n, "->", dest)
