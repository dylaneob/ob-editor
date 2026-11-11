#!/usr/bin/env python3
"""Real document page for a `doc` card (C4367 v9: the court filing and the FDA notice shown as the actual page, the key line swept
with a red marker). General version of C4367's tools/pdf_hl.py + ocrfind.

  python3 -I doc_page.py PDF PAGE OUT.png OUT.json "phrase" ["phrase" ...] [--dpi 220] [--nth N] [--no-ocr]

Renders PAGE (1-based) of PDF to OUT.png with pdftoppm, then finds each phrase on the page and writes its box, one box per printed
line the phrase covers, in pixels of OUT.png (x, y, w, h; top-left origin):
  1. from `pdftotext -bbox` (the PDF's own text layer, exact);
  2. when that fails (pdftotext crashes on some court PDFs, exit 134, C4367's complaint.pdf page 4), finds no text, or does not contain
     the phrase: Apple Vision OCR on the rendered page (bin/ocrfind, built from bin/ocrfind.swift, rebuilt here if missing).
A phrase is matched on its letters and digits only (case, punctuation, spacing and line breaks ignored), whole words, in page order;
use a phrase long enough to be unique (a bare "fat" is on the page many times). The first match is used; --nth 2 takes the second.
The PDF is untrusted data: only pdfinfo, pdftoppm and pdftotext read it (no JavaScript, nothing opened or executed), each with a
timeout, the page size is checked before rendering, and it is never written to.

OUT.json (paste into the card; it matches C4367's hf/assets/docs/*.json and its `page` field):
  {"pdf", "page", "dpi", "size": [w, h], "phrases": {phrase: [[x, y, w, h], ...]},      the reference's own keys
   "img": "docs/NAME.png",   path of OUT.png under hf/assets/ (the card's page.img; the file name alone when OUT.png is elsewhere)
   "hl": [[x, y, w, h], ...],   every phrase's line boxes in the order given: the card's page.hl, swept one bar per box
   "matches": {phrase: n}, "method": {phrase: "text" | "ocr" | "none"}}
so the event is  page={"img": J["img"], "size": J["size"], "hl": J["hl"]}  (add "fx", "y", "rot", "s0", "s1", "width" by hand if needed).
Exit codes: 0 every phrase found, 1 a phrase was not found (the JSON is still written, with [] for it), 2 bad arguments or a PDF problem.
"""
import argparse, html, json, os, re, shutil, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OCR, OCR_SRC = os.path.join(HERE, "ocrfind"), os.path.join(HERE, "ocrfind.swift")


def run(cmd, timeout):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "timed out")


def norm(s): return re.sub(r"[^a-z0-9%]", "", unicodedata.normalize("NFKC", s).lower())


def text_words(pdf, page, k):
    """words from the PDF's text layer in px: [{t, x0, y0, x1, y1, line}], or ([], why) when pdftotext fails or finds nothing"""
    r = run(["pdftotext", "-f", str(page), "-l", str(page), "-bbox", pdf, "-"], 90)
    if r.returncode:
        return [], f"pdftotext exit {r.returncode}"
    ws = [{"t": html.unescape(t), "x0": float(a) * k, "y0": float(b) * k, "x1": float(c) * k, "y1": float(d) * k}
          for a, b, c, d, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', r.stdout)]
    return (ws, "") if ws else ([], "no text layer")


def ocr_words(png):
    """words from Apple Vision OCR of the page image, with their line numbers"""
    if not os.path.exists(OCR):
        if not (os.path.exists(OCR_SRC) and shutil.which("swiftc")): return [], "bin/ocrfind missing and cannot be built"
        b = run(["swiftc", "-O", "-o", OCR, OCR_SRC], 300)
        if b.returncode: return [], f"swiftc failed: {b.stderr[-300:]}"
    r = run([OCR, "--words", png], 180)
    if r.returncode or not r.stdout.strip(): return [], f"ocrfind exit {r.returncode}: {r.stderr[-200:]}"
    ws = []
    for li, L in enumerate(json.loads(r.stdout)["lines"]):
        for w in L["words"]:
            x, y, ww, hh = w["box"]
            ws.append({"t": w["t"], "x0": x, "y0": y, "x1": x + ww, "y1": y + hh, "line": li})
    return ws, ""


def find(words, phrase):
    """[(first_word_index, last_word_index)] of every whole-word match of `phrase`, in order"""
    target = "".join(norm(t) for t in phrase.split())
    if not target: return []
    joined, starts, ends = "", {}, {}
    for k, w in enumerate(words):
        n = norm(w["t"])
        if n: starts[len(joined)] = k; joined += n; ends[len(joined)] = k
    hits, i = [], joined.find(target)
    while i != -1:
        j = i + len(target)
        if i in starts and j in ends and starts[i] <= ends[j]: hits.append((starts[i], ends[j]))
        i = joined.find(target, i + 1)
    return hits


def line_boxes(ws, tol):
    """union box per printed line of the matched words: [[x, y, w, h]] rounded once at the end"""
    lines = []
    for w in ws:
        same = lines and (("line" in w and w["line"] == lines[-1]["line"]) or ("line" not in w and abs(lines[-1]["y0"] - w["y0"]) < tol))
        if same:
            L = lines[-1]; L["x0"] = min(L["x0"], w["x0"]); L["y0"] = min(L["y0"], w["y0"]); L["x1"] = max(L["x1"], w["x1"]); L["y1"] = max(L["y1"], w["y1"])
        else: lines.append(dict(w, line=w.get("line", len(lines))))
    return [[round(L["x0"]), round(L["y0"]), round(L["x1"] - L["x0"]), round(L["y1"] - L["y0"])] for L in lines]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf"); ap.add_argument("page", type=int); ap.add_argument("out_png"); ap.add_argument("out_json"); ap.add_argument("phrases", nargs="+")
    ap.add_argument("--dpi", type=int, default=220); ap.add_argument("--nth", type=int, default=1); ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()
    pdf, png, js = os.path.abspath(a.pdf), os.path.abspath(a.out_png), os.path.abspath(a.out_json)
    if not os.path.isfile(pdf) or a.page < 1 or not png.endswith(".png") or not js.endswith(".json") or not (50 <= a.dpi <= 400):
        print("usage: doc_page.py PDF PAGE OUT.png OUT.json \"phrase\" ... [--dpi 220]  (PDF must exist, PAGE >= 1, outputs end .png / .json)", file=sys.stderr); return 2
    info = run(["pdfinfo", "-f", str(a.page), "-l", str(a.page), pdf], 60)
    m = re.search(r"Page\s+%d size:\s*([\d.]+) x ([\d.]+) pts" % a.page, info.stdout)
    if info.returncode or not m:
        print(f"doc_page: pdfinfo cannot read page {a.page} of {pdf}: {info.stderr.strip()[-200:]}", file=sys.stderr); return 2
    pw, ph = float(m.group(1)), float(m.group(2))
    if pw > 3000 or ph > 3000 or pw * ph * (a.dpi / 72) ** 2 > 60e6:
        print(f"doc_page: page is {pw:.0f} x {ph:.0f} pt, too big to render at {a.dpi} dpi (60 megapixel cap)", file=sys.stderr); return 2
    os.makedirs(os.path.dirname(png), exist_ok=True); os.makedirs(os.path.dirname(js), exist_ok=True)
    r = run(["pdftoppm", "-f", str(a.page), "-l", str(a.page), "-r", str(a.dpi), "-png", "-singlefile", pdf, png[:-4]], 180)
    if r.returncode or not os.path.exists(png):
        print(f"doc_page: pdftoppm failed (exit {r.returncode}): {r.stderr.strip()[-300:]}", file=sys.stderr); return 2
    from PIL import Image
    with Image.open(png) as im: size = list(im.size)
    k = a.dpi / 72.0
    tw, why_text = text_words(pdf, a.page, k)
    ow, why_ocr = None, ""
    res, matches, method = {}, {}, {}
    for ph_ in a.phrases:
        for src, ws in (("text", tw), ("ocr", None)):
            if ws is None:
                if a.no_ocr: break
                if ow is None: ow, why_ocr = ocr_words(png)
                ws = ow
            hits = find(ws, ph_)
            if len(hits) >= a.nth:
                i, j = hits[a.nth - 1]
                res[ph_] = line_boxes(ws[i:j + 1], 6 * a.dpi / 220.0); matches[ph_] = len(hits); method[ph_] = src
                if len(hits) > 1 and a.nth == 1:
                    print(f"doc_page: warning: {len(hits)} matches for {ph_[:50]!r}; used the first (a longer phrase or --nth picks another)", file=sys.stderr)
                break
        if ph_ not in res: res[ph_] = []; matches[ph_] = 0; method[ph_] = "none"
    if why_text: print(f"doc_page: text layer not used ({why_text})" + ("; OCR " + ("failed: " + why_ocr if why_ocr else "used") if ow is not None else ""), file=sys.stderr)
    rel = png.split("/assets/", 1)[1] if "/assets/" in png else os.path.basename(png)
    out = {"pdf": pdf, "page": a.page, "dpi": a.dpi, "size": size, "phrases": res, "img": rel,
           "hl": [b for ph_ in a.phrases for b in res[ph_]], "matches": matches, "method": method}
    json.dump(out, open(js, "w"), indent=1)
    print(png, tuple(size), {p[:40]: f"{len(v)} line(s) via {method[p]}" for p, v in res.items()})
    return 0 if all(res[p] for p in a.phrases) else 1


if __name__ == "__main__":
    sys.exit(main())
