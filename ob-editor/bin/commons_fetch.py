"""Search Wikimedia Commons for free-licensed photos; download 1280px thumbs + write credits.json."""
import json, os, sys, urllib.parse, urllib.request, re
OUT = sys.argv[1]; queries = json.loads(sys.argv[2]); N = int(sys.argv[3]) if len(sys.argv) > 3 else 5
UA = {"User-Agent": "OB-editor/1.0 (personal video editing)"}   # 10-23: no personal email in request headers
OK = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]?[0-9.]*|public domain|pd.*)$", re.I)
if os.environ.get("NO_ATTRIBUTION"):      # ads: CC0 / public domain only, so no credit line is owed on screen
    OK = re.compile(r"^(cc0.*|public domain.*|pd.*)$", re.I)
credits = {}
for key, q in queries.items():
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": q + " filetype:bitmap", "gsrlimit": int(os.environ.get("LIMIT", 20)), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1280})
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    os.makedirs(f"{OUT}/{key}", exist_ok=True); n = 0
    for p in pages:
        ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not OK.match(lic.strip()) or ii.get("mime") not in ("image/jpeg", "image/png") or ii["width"] < 800:
            continue
        fn = f"{OUT}/{key}/{n+1}.jpg"
        urllib.request.urlretrieve(ii["thumburl"], fn) if False else open(fn, "wb").write(
            urllib.request.urlopen(urllib.request.Request(ii["thumburl"], headers=UA), timeout=60).read())
        artist = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        credits[f"{key}/{n+1}"] = {"title": p["title"], "license": lic, "artist": artist, "page": ii.get("descriptionurl")}
        n += 1
        if n >= N: break
    print(key, n)
json.dump(credits, open(f"{OUT}/credits.json", "w"), indent=1)
