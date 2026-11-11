#!/usr/bin/env python3
"""qc_assets: the plan must show its work (built 2026-11-10, WP3 of the editor rebuild; checks "AI slop" BEFORE a render).

OB 11-10 "no more ai slop". His most repeated complaint (seven times, ledger M16): "Again I hate boring just text slides".
Others that came back: the banned physique clips C1797-C1802 shown as lean (11-07 "y do you always show me fat asf as toned"),
cutouts made with Vision masks (rule: BiRefNet only, 11-06/11-09), black backgrounds (M38), zooming (11-07 "zooming in and out
non stop"), fidgety springs (11-07 "Why is it so fidgety?"), stock or AI pictures as filler (M22/M28), upscaled pictures (11-06
"glitchy"). Each one FAILs from the plan, before a render. Every number and list comes from ~/ob-editor/qc/formats.json
(defaults.picture, defaults.assets, defaults.text, the route's own keys); this file holds no threshold of its own except the
three marked OPT below (read from formats.json when the key exists).

THE MANIFEST  WORK/qc/assets.json  = {"version", "built", "plan_files": [{path, sha1}], "declared_fonts": [], "rows": [ROW, ...]}
  ROW = {id, t0, t1, kind, files[], source, source_url, viewed, sheet, matte, bg, font, text, client, scale, anim,
         over, layout, person, why, damping, zoom_pct, cut_scale_pct, origin, fill_in[]}
  source: own | client | their_clip | screenshot | stock:<site> | drawn | chart | blender | code
  viewed true + sheet (an existing frame sheet or still) = a person or agent LOOKED at it before it went in
  over: what is behind a text row: aroll | blur_aroll | broll | footage | picture | board | black | flat
  scale: a number (static) or [from, to] (animated).  fill_in: the fields `build` could not know (the editor fills them in).

    python3 -I ~/ob-editor/bin/qc_assets.py build WORK [--plan FILE ...] [--out FILE]   (fills the manifest from the plan, keeps hand-filled values)
    python3 -I ~/ob-editor/bin/qc_assets.py check WORK --route ROUTE [--job JOB.json]    (every check, one line each; exit 1 on a FAIL)
    python3 -I ~/ob-editor/bin/qc_assets.py problems WORK --route ROUTE [--job JOB.json] (what qc_route.record_problems prints)
    python3 -I ~/ob-editor/bin/qc_assets.py --selftest

Plug-in interface (qc_route.py): run(ctx) -> {check: (status, detail)}; record_problems(route, work, job) -> [str].
ctx = {path, sha256, work, route, cfg, job, long, dur, segs, report}.
Checks: gfx_kind asset_source asset_viewed banned_assets matte bg zoom_plan springs fonts upscale barbell ob_in_overlay (+ assets = manifest health).
ob_in_overlay (11-11, ledger M87; widens M37 to long form): OB on C4465, r2 1:06.4 "you just put a bench, im not in the overlay". On a route where he talks to camera
(long-form, reel-talking; formats.json picture.ob_in_overlay_routes overrides), a full-frame overlay row (ffcover, reel, full photo) must show him: a row with_ob true.
`build` fills with_ob from the event (with_ob / ob_pip / pip / ob_cutout) or, when the clip or photo exists on disk, by running bin/faces on up to 4 frames of the span
(ob_frames "2/4"; half or more with his face = true). Not measurable = not shown = FAIL. Set with_ob true by hand only after looking at the frames.
Plan shapes `build` reads: long-form events_resolved.json; tmpl.py plan ({"timeline", "els"}); level-kit plan ({"elements", "camera", "cells"}).
Engine matte record (11-11): WORK/qc/matte.json, written by tmpl.py / brand_react_render.py through birefnet_cut.py after a render. A cutout
row from a plan with a run there (same plan path and sha1, method birefnet, the row's look among the run's looks) is stamped matte birefnet
by `build` itself (origin gets "+engine"). A cutout row with no engine run must still be declared, and is checked as before.
"""
import os, sys, re, json, time, hashlib, glob, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
QC = os.path.expanduser("~/ob-editor/qc")
FORMATS = os.path.join(QC, "formats.json")
ROW_KEYS = ["id", "t0", "t1", "kind", "files", "source", "source_url", "viewed", "sheet", "matte", "bg", "font", "text", "client",
            "scale", "anim", "over", "layout", "person", "why", "damping", "zoom_pct", "cut_scale_pct", "origin", "with_ob", "ob_frames"]
MEDIA_KINDS = {"photo", "clip", "image", "chart", "drawn", "blender", "cutout", "screenshot", "footage", "broll", "seq", "paper", "sticker"}
NON_OVERLAY = {"label", "caption", "lower_third", "cta", "chapter", "fx", "shot", "layout"}   # captions and lower-third labels are not overlays
SOURCE_RE = re.compile(r"^(own|client|their_clip|screenshot|stock:\S+|drawn|chart|blender|code)$")
FOOTAGE_OVER = {"aroll", "blur_aroll", "broll", "footage", "clip"}       # moving picture behind the text
KINETIC_CUES = {"kinetic", "slam", "word_slam", "brush", "mask_rise", "word_rise", "rise", "stagger", "word_pop"}   # C4398 kinetic test: words rise/slam on the spoken word
DARK_NAMES = {"black": 0, "board": 8}     # named backgrounds that are dark (tmpl "board": "dark warm, faint grid")
WEIGHTS = {"thin", "light", "regular", "medium", "semibold", "bold", "extrabold", "black", "italic", "heavy", "display"}
ZK = re.compile(r"^(zoom|punch|push|kick|kb|kenburns|ken_burns|dolly)$", re.I)
CHECKS = ["gfx_kind", "asset_source", "asset_viewed", "banned_assets", "matte", "bg", "zoom_plan", "springs", "fonts", "upscale", "barbell", "ob_in_overlay"]
COVER_KINDS = {"clip", "photo", "image", "footage", "broll", "screenshot", "seq", "paper"}   # a picture that can fill the frame
OB_ROUTES = {"long-form", "reel-talking"}      # OPT: routes where he talks to camera (formats.json picture.ob_in_overlay_routes wins)
OB_FLAGS = ("with_ob", "ob_pip", "pip", "ob_cutout")


# ---------------------------------------------------------------- config
def _merge(a, b):
    o = dict(a)
    for k, v in b.items(): o[k] = _merge(o[k], v) if isinstance(v, dict) and isinstance(o.get(k), dict) else v
    return o


def cfg_of(route):
    """qc_route.cfg(route) when it works; else formats.json defaults merged with the route (one small fallback)."""
    try:
        if HERE not in sys.path: sys.path.insert(0, HERE)
        import qc_route
        return qc_route.cfg(route)
    except Exception:
        F = json.load(open(FORMATS)); c = _merge(F["defaults"], F["routes"].get(route, {})); c["route"] = route
        c["records"] = list(F["routes"].get(route, {}).get("records", [])); return c


def _opt(c, sec, key, default):
    """OPT: a key that formats.json may add later; until then the default (listed in reports/WP3.md)."""
    v = (c.get(sec) or {}).get(key); return default if v is None else v


def _is_ugc(job):
    j = job or {}; d = j.get("declares") or {}
    return any(str(x.get("ugc", "")).lower() not in ("", "false", "0", "none") for x in (j, d)) or "ugc" in str(j.get("subject", "")).lower()


def zoom_allowed(c, job):
    if (c.get("picture") or {}).get("zoom_animated"): return True
    za = str(c.get("zoom_allowed", "")).lower()
    return bool(za) and "ugc" in za and _is_ugc(job)


# ---------------------------------------------------------------- small helpers
def _f(x):
    try: return float(x)
    except Exception: return None


def _t(cues, v, default=None):
    """A time from a number, a cue name, or {"cue": name, "off": s}."""
    if isinstance(v, bool) or v is None: return default
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str): x = (cues or {}).get(v); return _f(x[0] if isinstance(x, list) and x else x) if x is not None else default
    if isinstance(v, dict):
        b = _t(cues, v.get("cue"), None); return None if b is None else b + (_f(v.get("off")) or 0.0)
    return default


def row(id, t0, t1, kind, **kw):
    r = {k: None for k in ROW_KEYS}
    r.update(id=str(id), t0=t0, t1=t1, kind=kind, files=[], source="", source_url="", viewed=None, sheet="", matte="", bg="", font="",
            text="", client="", scale=None, anim="", over="", layout="", person=False, why="", damping=None, zoom_pct=None, cut_scale_pct=None, origin="", with_ob=None, ob_frames="")
    r.update({k: v for k, v in kw.items() if v is not None}); return r


def guess_source(s):
    s = (s or "").lower()
    for site in ("pexels", "mixkit", "pixabay", "unsplash", "shutterstock", "istock", "storyblocks", "videvo", "stockcake", "coverr", "openverse", "wikimedia", "commons"):
        if site in s: return "stock:" + site
    if re.search(r"/b roll/|/b-roll/|(^|/)(c\d{4}|dsc\d+|img_\d+)\b", s) or re.search(r"\bown\b|\bob own\b", s): return "own"
    if "/proof/" in s or "client" in s: return "client"
    return ""


def scan_motion(d):
    """Walk one plan element: (animated scale % or None, hard-cut scale step % or None, lowest spring damping or None, tokens)."""
    out = {"anim": None, "step": None, "damp": None, "tok": set()}
    def num(x): return isinstance(x, (int, float)) and not isinstance(x, bool)
    def walk(o, k=""):
        if isinstance(o, dict):
            for kk, v in o.items(): walk(v, kk)
        elif isinstance(o, list):
            if k == "spring" and len(o) == 2 and all(num(x) for x in o): out["damp"] = o[1] if out["damp"] is None else min(out["damp"], o[1]); out["tok"].add("spring")
            elif ZK.match(k) and len(o) == 2 and all(num(x) for x in o) and o[0]:
                p = abs(o[1] / o[0] - 1) * 100; out["anim"] = max(out["anim"] or 0, p); out["tok"].add("push")
            elif k == "spring" or ZK.match(k): pass
            else:
                for x in o: walk(x, k)
        elif num(o):
            kl = k.lower()
            if ZK.match(kl):
                if kl == "punch" and o > 1: out["step"] = max(out["step"] or 0, (o - 1) * 100); out["tok"].add("punch")
                elif o > 1: out["anim"] = max(out["anim"] or 0, (o - 1) * 100); out["tok"].add(kl)
                elif kl == "push" and 0 < o < 1: out["anim"] = max(out["anim"] or 0, o * 100); out["tok"].add("push")
            elif kl in ("damp", "damping"): out["damp"] = o if out["damp"] is None else min(out["damp"], o)
    walk(d); return out["anim"], out["step"], out["damp"], out["tok"]


def _apply_motion(r, el):
    a, s, dm, tok = scan_motion(el)
    r["zoom_pct"] = a; r["cut_scale_pct"] = s; r["damping"] = dm
    r["anim"] = " ".join(sorted(set(r["anim"].split()) | tok)); return r


def _set_fill(rows, F):
    """fill_in = the fields the checks need and `build` could not learn from the plan."""
    tox = set(F["defaults"]["assets"]["text_only_kinds"])
    for r in rows:
        need = []
        k = r["kind"]
        if k in MEDIA_KINDS or k == "background":
            if not r["source"]: need.append("source")
            if (r["person"] or k == "background") and r["viewed"] is not True: need.append("viewed")
            if (r["person"] or k == "background") and not r["sheet"]: need.append("sheet")
            if k == "cutout" and not r["matte"]: need.append("matte")
            if r["source"].startswith("stock") and not r["why"]: need.append("why")
        elif k not in tox and k not in NON_OVERLAY: need.append(f"kind (unknown type {k})")
        r["fill_in"] = need
    return rows


def _fbin():
    p = os.path.join(HERE, "faces"); return p if os.path.exists(p) else ""


def measure_ob(path, t_in=0.0, dur=2.0, n=4):
    """(with_ob, "k/n") by bin/faces on up to n frames of the clip span (or the photo itself); (None, "") when it cannot be measured."""
    import subprocess
    fb = _fbin()
    if not fb or not path or not os.path.isfile(path): return None, ""
    try:
        with tempfile.TemporaryDirectory() as td:
            if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")): fr = [path]
            else:
                dur = max(0.4, dur or 2.0)
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, t_in or 0.0):.3f}", "-t", f"{dur:.3f}", "-i", path, "-vf", f"fps={n / dur:.4f},scale=960:-2", "-frames:v", str(n), "-q:v", "3", f"{td}/%02d.jpg"],
                               check=True, timeout=120)
                fr = [os.path.join(td, f) for f in sorted(os.listdir(td)) if f.endswith(".jpg")][:n]
            if not fr: return None, ""
            out = subprocess.run([fb] + fr, capture_output=True, text=True, timeout=120).stdout.splitlines()
    except Exception: return None, ""
    hit = sum(1 for ln in out if len(ln.split(" ", 1)) > 1 and not ln.split(" ", 1)[1].startswith(("none", "error")))
    return (hit * 2 >= len(fr)), f"{hit}/{len(fr)}"


def _cover_ob(r, e, work, src, t_in, dur):
    """A full-frame picture row from an event: does it show him?"""
    r["layout"] = "full"
    for k in OB_FLAGS:
        if e.get(k): r["with_ob"] = True; r["ob_frames"] = f"flag:{k}"; return r
    w, fr = measure_ob(src, t_in, dur); r["with_ob"] = w; r["ob_frames"] = fr; return r


# ---------------------------------------------------------------- build: three plan shapes
def rows_from_events(d, work):
    out = []
    for e in d.get("events", []):
        i = e.get("id") or f"E{len(out)}"; t0, t1 = _f(e.get("edit_in")), _f(e.get("edit_out")); ty = e.get("type", "")
        desc = e.get("desc", "") or e.get("note", "") or ""
        kw = dict(origin=f"event:{ty}")
        if ty in ("plate", "pills", "facequote"):
            kind = {"plate": "plate", "pills": "pill", "facequote": "quote"}[ty]
            txt = " | ".join(c[0] for c in e.get("chunks", [])) if ty == "plate" else " | ".join(x[0] for x in e.get("items", [])) if ty == "pills" else e.get("text", "")
            r = row(i, t0, t1, kind, text=txt, over="aroll", layout="side" if ty == "facequote" else "on_face", anim="word_timed" if (e.get("at") or e.get("items_t")) else "", **kw)
            if ty == "plate" and e.get("kinetic") and e.get("kchunks"):   # 2026-11-11 C4465 r2: the C4398 kinetic bar (kinetic_cards.kbar) over his moving A-roll
                r.update(layout="full", anim="word_rise word_slam", over="aroll", size=min(int(c.get("size") or 0) for c in e["kchunks"]))
        elif ty == "chapter": r = row(i, t0, t1, "chapter", text=f"{e.get('kicker', '')} {e.get('title', '')}".strip(), over="aroll", **kw)
        elif ty == "label": r = row(i, t0, t1, "label", text=f"{e.get('title', '')} {e.get('sub', '')}".strip(), **kw)
        elif ty == "stat_bars": r = row(i, t0, t1, "chart", source="chart", files=[], text=e.get("title", ""), anim="bars", **kw)
        elif ty == "photo":
            names = [p[0] for p in e.get("photos", [])]
            r = row(i, t0, t1, "photo", files=names, source="own" if re.search(r"\b(his|my|ob)\b", desc, re.I) else guess_source(desc), text=e.get("title", ""), **kw)
        elif ty == "photo_overlay":
            names = [os.path.join(e.get("folder", ""), it[0]) for it in e.get("items", [])]
            cl = e.get("client_proof")
            r = row(i, t0, t1, "photo", files=names, source="client" if cl else guess_source(" ".join(names)), person=bool(cl),
                    client=", ".join(re.sub(r"^ba_", "", os.path.basename(n)) for n in names) if cl else "", **kw)
            if e.get("full") is True: _cover_ob(r, e, work, "", 0.0, 1.0)
        elif ty == "reel":
            sh = [s.get("b") for s in e.get("shots", [])]
            r = row(i, t0, t1, "clip", files=[s for s in sh if s], source=guess_source(desc) or ("stock:?" if "stock" in desc.lower() else ""), why="", text=desc, **kw)
            s0 = (e.get("shots") or [{}])[0]; bp = next(iter(glob.glob(os.path.join(work or "", "hf", "assets", "broll", str(s0.get("b", "")) + ".mp4"))), "")
            _cover_ob(r, e, work, bp, 0.0, _f(s0.get("d")) or 2.0)
        elif ty == "ffcover":
            r = row(i, t0, t1, "clip", files=[e.get("src", "")], source=guess_source(e.get("src", "") + " " + desc), person=bool(re.search(r"\b(ob|client|physique|body|him|her)\b", desc, re.I)), text=desc, **kw)
            if e.get("full") is not False: _cover_ob(r, e, work, e.get("src", ""), _f(e.get("in")) or 0.0, _f(e.get("dur")) or ((t1 or 0) - (t0 or 0)) or 1.5)
        else: r = row(i, t0, t1, ty or "?", text=desc, **kw)
        _apply_motion(r, {k: v for k, v in e.items() if k not in ("shots", "pics")}); out.append(r)
        pics = [p for p in (e.get("pics") or []) if p.get("key")]
        if pics and t0 is not None:   # 2026-11-11 (C4465): pictures layered on a card (cards.add_pics / assemble.ffcover_layers) are their own photo row
            a = t0 + min(_f(p.get("t0")) or 0.0 for p in pics); b = min(t1 if t1 is not None else a + 1.0, t0 + max(_f(p.get("t1")) if p.get("t1") is not None else (t1 - t0 if t1 is not None else 1.0) for p in pics))
            names = [os.path.join(p.get("folder", "proof"), p["key"]) for p in pics]
            cl = bool(e.get("client_proof")) and any(not os.path.basename(n).startswith("ob_") for n in names)
            out.append(row(f"{i}.pics", a, b, "photo", files=names, source="client" if cl else ("own" if all(os.path.basename(n).startswith("ob_") for n in names) else ""),
                           person=True, client=", ".join(re.sub(r"^(pa|tm)_", "", os.path.basename(n)) for n in names if not os.path.basename(n).startswith("ob_")) if cl else "",
                           origin=f"event:{ty}+pics", text=desc))
    return out


TMPL_TEXT = {"title": "title_card", "pill": "pill", "quote": "quote", "takeover": "list"}   # step and checks tick drawn boxes on each word: they count as drawn objects (TMPL_MEDIA)
TMPL_LABEL = {"igtext", "text", "lower3", "ctabar", "label", "badge", "tag", "steptag", "cta", "tint", "scan", "check", "marks", "tracker", "map", "tease"}
TMPL_MEDIA = {"image": ("photo", "screenshot"), "burst": ("photo", "own"), "seq": ("blender", "blender"), "slide": ("drawn", "drawn"), "paper": ("paper", "drawn"),
              "vcard": ("clip", "stock"), "board": ("drawn", "drawn"), "step": ("drawn", "code"), "checks": ("drawn", "code"), "sticker": ("sticker", "drawn"), "count": ("chart", "chart"), "bar": ("chart", "chart"), "line": ("chart", "chart"), "icons": ("drawn", "drawn")}


def rows_from_tmpl(d):
    out = []; t = 0.0; looks = []
    for n, s in enumerate(d.get("timeline", [])):
        L = s.get("look") or {}; dur = _f(s.get("dur")) or (abs(s["mic"][1] - s["mic"][0]) if s.get("mic") else (_f(s.get("out", 0)) or 0) - (_f(s.get("in", 0)) or 0))
        looks.append(L); nm = L.get("name", "")
        if L.get("bg"):
            b = str(L["bg"]); kind = "background"
            path = b.split(":", 1)[1].split("@")[0] if re.match(r"^(frosted|image|src):", b) else ""
            r = row(f"look{n}", t, t + dur, kind, bg=b, files=[path] if path else [], source=guess_source(path) if path else ("own" if b == "studio" else "code" if b == "board" else ""), origin=f"look:{nm}")
            if b == "studio": r["viewed"] = True; r["sheet"] = "(his own frame)"
            out.append(r)
        if nm in ("cut", "inset", "card", "grid", "box", "freeze"):
            out.append(row(f"cut{n}", t, t + dur, "cutout", matte=str(L.get("matte") or d.get("matte") or ""), source="own", origin=f"look:{nm}"))
        r = row(f"shot{n}", t, t + dur, "shot", origin=f"look:{nm}"); _apply_motion(r, {k: v for k, v in L.items() if ZK.match(k)}); out.append(r)
        t += dur
    if "lines" in d and "timeline" not in d:   # 11-11: tmpl.py word-anchored plans (times resolve at render: rows carry the line ids)
        seen = set(); cut = False
        for n, s in enumerate(d["lines"]):
            L = s.get("look") or {}; nm = L.get("name", ""); looks.append(L); lid = s.get("id", f"L{n}")
            if nm in ("cut", "inset", "card", "grid", "box", "freeze") and not cut:
                out.append(row(f"cut_{lid}", None, None, "cutout", matte=str(L.get("matte") or d.get("matte") or ""), source="own", origin=f"look:{nm}")); cut = True
            for cl in (L.get("cells") or []):
                for f in (cl if isinstance(cl, list) else [cl]):
                    if not isinstance(f, str) or f in seen: continue
                    seen.add(f); out.append(row(f"cell_{len(seen)}", None, None, "clip" if f.lower().endswith((".mp4", ".mov")) else "photo", files=[f],
                                                source=guess_source(f), text=lid, origin=f"look:{nm}:cell"))
            if nm == "full" and n == 0: r = row("shot_full", None, None, "shot", origin="look:full"); r["viewed"] = True; r["sheet"] = "(his own frame)"; out.append(r)
    only_board = bool([l for l in looks if l.get("bg")]) and all(str(l.get("bg")) == "board" for l in looks if l.get("bg")) and not any(l.get("name") == "full" for l in looks)
    over = "board" if only_board else "aroll"
    for n, el in enumerate(d.get("els", [])):
        ty = el.get("type", ""); i = el.get("id") or f"el{n}_{ty}"; t0 = _t(None, el.get("t", el.get("at")), None) if not isinstance(el.get("at"), str) else None
        t1 = (t0 + _f(el.get("dur"))) if (t0 is not None and _f(el.get("dur"))) else (_t(None, el.get("until")) if not isinstance(el.get("until"), str) else None)
        font = str(el.get("font") or ""); path = el.get("path") or el.get("image") or el.get("src") or ""
        if ty in TMPL_MEDIA:
            kind, src = TMPL_MEDIA[ty]; files = list(el.get("paths") or ([path] if path else []))
            r = row(i, t0, t1, kind, files=files, source=("screenshot" if (src == "screenshot" and not files) else guess_source(" ".join(files)) or src), font=font, origin=f"el:{ty}")
        elif ty in TMPL_TEXT:
            bgp = re.match(r"^(src|image):([^@]+)", str(el.get("bg", "")))
            r = row(i, t0, t1, TMPL_TEXT[ty], text=str(el.get("title") or el.get("text") or ""), font=font, over=over, files=[bgp.group(2)] if bgp else [],
                    anim="word_rise" if ty == "title" else "", origin=f"el:{ty}")
        else:
            r = row(i, t0, t1, "label" if ty in TMPL_LABEL else (ty or "?"), text=str(el.get("text") or el.get("title") or ""), font=font, origin=f"el:{ty}")
        if ty in ("image", "title", "paper", "pill"): r["anim"] = (r["anim"] + " spring").strip()
        _apply_motion(r, el); out.append(r)
    return out


LK_TEXT = {"title": "title_card", "depth_word": "text", "keyword": "text"}   # text_pop is a small letter-spaced tag (a label); checklist ticks drawn boxes (a drawn object)
LK_MEDIA = {"object3d": ("blender", "blender"), "blocks3d": ("blender", "blender"), "bar": ("chart", "chart"), "chips": ("drawn", "drawn"), "checklist": ("drawn", "code"), "card": ("paper", "drawn")}


def rows_from_levelkit(d):
    out = []; cues = d.get("cues") or {}
    lt = d.get("layout_track") or []; grid = []
    for n, (c, name) in enumerate(lt):
        a = _t(cues, c, None); b = _t(cues, lt[n + 1][0], None) if n + 1 < len(lt) else None
        if name == "GRID" and a is not None: grid.append((a, b if b is not None else a + 1.0))
    for key, c in (d.get("cells") or {}).items():
        if isinstance(c, dict) and c.get("src") and grid:
            for gi, (a, b) in enumerate(grid):
                out.append(row(f"cell_{key}_{gi}", a, b, "clip", files=[c["src"]], source=guess_source(c["src"]), origin="levelkit:cell", why="b-roll cascade cell" if "stock" in guess_source(c["src"]) else ""))
    for n, s in enumerate((d.get("camera") or {}).get("shots", [])):
        if isinstance(s, list) and len(s) >= 3:
            r = row(f"cam{n}", _t(cues, s[0], None), None, "shot", scale=[s[1], s[2]], origin="levelkit:camera")
            if s[1] and s[1] != s[2]: r["zoom_pct"] = abs(s[2] / s[1] - 1) * 100; r["anim"] = "push"
            out.append(r)
    sh = sorted((r for r in out if r["kind"] == "shot" and r["t0"] is not None), key=lambda r: r["t0"])
    for a, b in zip(sh, sh[1:]):
        if a["scale"] and b["scale"]: b["cut_scale_pct"] = abs(b["scale"][0] / a["scale"][1] - 1) * 100
    over = "broll" if grid else "aroll"
    for n, el in enumerate(d.get("elements", [])):
        ty = el.get("type", ""); i = el.get("id") or f"el{n}_{ty}"; t0 = _t(cues, el.get("in", el.get("stage_from")), None); t1 = _t(cues, el.get("out"), None)
        if t0 is None and el.get("rows"):
            ins = [x for x in (_t(cues, rw.get("in"), None) for rw in el["rows"] if isinstance(rw, dict)) if x is not None]; t0 = min(ins) if ins else None
        if ty in LK_MEDIA:
            kind, src = LK_MEDIA[ty]; r = row(i, t0, t1, kind, source=src, files=[el["frames"]] if el.get("frames") else [], origin=f"levelkit:{ty}", text=str(el.get("label") or el.get("title") or ""))
        elif ty in LK_TEXT:
            if ty == "title": txt = " ".join(" ".join(l.get("words", [])) for l in el.get("lines", []))
            elif ty == "checklist": txt = " | ".join(x.get("text", "") for x in el.get("rows", []))
            else: txt = str(el.get("text", ""))
            kin = any(k in el for k in ("rise", "stagger", "per")) or any(isinstance(l, dict) and ("rise" in l or "stagger" in l) for l in el.get("lines", []))
            r = row(i, t0, t1, LK_TEXT[ty], text=txt, over=over, anim="word_rise" if kin else "tick" if ty == "checklist" else "", origin=f"levelkit:{ty}")
        else: r = row(i, t0, t1, "label" if ty in ("item_label", "text_pop") else (ty or "?"), text=str(el.get("name") or el.get("text") or ""), origin=f"levelkit:{ty}")
        _apply_motion(r, el); out.append(r)
    return out


def _sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def engine_mattes(work):
    """WORK/qc/matte.json runs (birefnet_cut.record): {(plan path, sha1): set of looks the engine cut him out in with BiRefNet}."""
    try: d = json.load(open(os.path.join(work, "qc", "matte.json")))
    except Exception: return {}
    out = {}
    for r in d.get("runs", []):
        if str(r.get("method", "")).lower() == "birefnet": out.setdefault((r.get("plan"), r.get("plan_sha1")), set()).update(r.get("looks") or [])
    return out


def find_plans(work):
    c = [os.path.join(work, "events_resolved.json")] + sorted(glob.glob(os.path.join(work, "plan*.json")) + glob.glob(os.path.join(work, "*", "plan*.json")))
    return [p for p in c if os.path.isfile(p)]


def build(work, plans=None, out=None):
    F = json.load(open(FORMATS)); plans = plans or find_plans(work); rows = []; used = []; fonts = []; em = engine_mattes(work)
    for p in plans:
        d = json.load(open(p))
        if isinstance(d, dict) and "events" in d: rs = rows_from_events(d, work)
        elif isinstance(d, dict) and "els" in d and ("timeline" in d or "lines" in d): rs = rows_from_tmpl(d)   # 11-11: word-anchored "lines" plans too
        elif isinstance(d, dict) and "elements" in d: rs = rows_from_levelkit(d)
        else: continue
        pre = os.path.splitext(os.path.basename(p))[0]
        cut = em.get((os.path.abspath(p), _sha1(p)), set())
        for r in rs:   # 11-11: the engine's own record, not the editor's word
            if r["kind"] == "cutout" and (r.get("origin") or "").split(":")[-1] in cut: r["matte"] = "birefnet"; r["origin"] = (r.get("origin") or "") + "+engine"
        if len(plans) > 1:
            for r in rs: r["id"] = f"{pre}:{r['id']}"
        rows += rs; used.append({"path": os.path.abspath(p), "sha1": _sha1(p)})
        fonts += [str(x) for x in (d.get("declared_fonts") or [])] + ([str(d["creator_font"])] if d.get("creator_font") else [])
    mp = out or os.path.join(work, "qc", "assets.json"); old = {}
    if os.path.exists(mp):
        try: old = {r["id"]: r for r in json.load(open(mp)).get("rows", [])}
        except Exception: old = {}
    keep = ("source", "source_url", "viewed", "sheet", "matte", "client", "why", "font", "person", "scale", "damping", "bg", "over", "with_ob")
    for r in rows:
        o = old.get(r["id"])
        if o:
            for k in keep:
                if o.get(k) not in (None, "", [], False) and r.get(k) in (None, "", [], False): r[k] = o[k]
            if not r["files"] and o.get("files"): r["files"] = o["files"]
    for r in rows:
        if not r["sheet"]:
            g = glob.glob(os.path.join(work, "qc", "sheets", re.sub(r"[^\w.-]", "_", r["id"]) + ".*"))
            if g: r["sheet"] = g[0]
    _set_fill(rows, F)
    eng = None
    try:
        m = re.search(r"def spring\(t, freq=[\d.]+, damp=([\d.]+)\)", open(os.path.join(HERE, "tmpl_fx.py")).read()); eng = float(m.group(1)) if m else None
    except Exception: pass
    man = {"version": 1, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "plan_files": used, "declared_fonts": sorted(set(fonts) | set((old and json.load(open(mp)).get("declared_fonts", [])) or [])) if old else sorted(set(fonts)),
           "engine_spring_damp": eng, "rows": rows}
    os.makedirs(os.path.dirname(mp), exist_ok=True); json.dump(man, open(mp, "w"), indent=1)
    return man, mp


def load_manifest(work):
    p = os.path.join(work or "", "qc", "assets.json")
    if not os.path.exists(p): return None, p
    return json.load(open(p)), p


# ---------------------------------------------------------------- checks
def _ids(rs, n=6):
    s = ", ".join(r["id"] for r in rs[:n]); return s + (f" (+{len(rs) - n} more)" if len(rs) > n else "")


def _rx(tokens):
    return re.compile("|".join(r"(?<![a-z0-9])" + re.escape(t.lower()) + r"(?![a-z0-9])" for t in tokens), re.I) if tokens else None


def _span(r):
    a = r["t0"]; b = r["t1"]
    if a is None: return None
    return (a, b if (b is not None and b > a) else a + 1.0)


def _overlap(r, others):
    s = _span(r)
    if not s: return 0.0
    tot = 0.0
    for o in others:
        q = _span(o)
        if q: tot = max(tot, max(0.0, min(s[1], q[1]) - max(s[0], q[0])))
    return tot / max(1e-6, s[1] - s[0])


def _is_media(r, real=True):
    return r["kind"] in MEDIA_KINDS and (r["files"] or r["source"] in ("chart", "drawn", "blender", "code") or r["kind"] in ("chart", "drawn", "blender"))


def c_gfx_kind(rows, c, **k):
    tox = set(c["assets"]["text_only_kinds"]); media = [r for r in rows if _is_media(r)]; bad = []; kin = 0
    for r in rows:
        if r["kind"] not in tox or r["kind"] in NON_OVERLAY: continue
        if [f for f in r["files"] if f]: continue                                    # text on a photo or clip of its own
        if _overlap(r, media) >= _opt(c, "picture", "text_cover_frac", 0.8): continue   # OPT: a photo, clip, chart, drawn or 3D asset is on screen under it
        toks = set(re.split(r"[\s,;|]+", (r["anim"] or "").lower()))
        if toks & KINETIC_CUES and r["over"] in FOOTAGE_OVER and r["layout"] in ("", "full", None):   # C4398 kinetic test: full-frame words rising/slamming on the spoken word over moving A-roll
            mn = _opt(c, "text", "kinetic_min_px", None)
            if mn is None or (r.get("size") or mn) >= mn: kin += 1; continue
        bad.append(r)
    if bad: return "FAIL", f"text-only graphic (OB: 'Again I hate boring just text slides'): {_ids(bad)}. Give each a real photo, clip, chart, drawn or 3D asset, or make it full-frame kinetic type (anim word_slam/word_rise) over his moving A-roll"
    return "PASS", f"no text-only overlay ({kin} kinetic full-frame text over moving A-roll allowed, {sum(1 for r in rows if r['kind'] in tox)} text rows checked)"


def _ai_in_file(p, rx):
    try:
        with open(p, "rb") as f: head = f.read(262144)
    except Exception: return ""
    for m in (b"trainedAlgorithmicMedia", b"c2pa", b"Adobe Firefly", b"made with AI"):
        if m.lower() in head.lower(): return m.decode()
    a = head.find(b"<x:xmpmeta"); seg = head[a:head.find(b"</x:xmpmeta>", a) + 12] if a >= 0 else b""
    if seg and rx:
        m = rx.search(seg.decode("latin-1")); return m.group(0) if m else ""
    for m in re.finditer(rb"(?:Software|Generator|Creator)\x00?([ -~]{3,60})", head):
        s = rx.search(m.group(1).decode("latin-1")) if rx else None
        if s: return s.group(0)
    return ""


def c_asset_source(rows, c, job=None, work=None, **k):
    rx = _rx(c["assets"]["ai_sources"]); thumb = str((job or {}).get("kind", "")).lower() == "thumbnail" or c.get("route") == "thumbnail"
    bad = []; ai = []; filler = []
    for r in rows:
        if not (r["kind"] in MEDIA_KINDS or r["kind"] == "background"): continue
        if not SOURCE_RE.match(r["source"] or ""): bad.append(r); continue
        if r["source"].startswith("stock") and not r["why"]: filler.append(r)
        if thumb: continue
        hay = " ".join([r["source"], r["source_url"] or "", r["why"] or ""] + list(r["files"]))
        hit = rx.search(hay) if rx else None
        if not hit:
            for fp in r["files"]:
                q = fp if os.path.isabs(fp) else os.path.join(work or "", fp)
                if os.path.isfile(q):
                    h = _ai_in_file(q, rx)
                    if h: hit = re.match(r"(.*)", h); break
        if hit: ai.append((r, hit.group(0)))
    m = []
    if ai: m.append("AI-made picture (rule: no AI imagery in videos; thumbnails only): " + "; ".join(f"{r['id']} ({h})" for r, h in ai[:5]) + ". Replace it with a real photo or his footage")
    if bad: m.append(f"no valid source on {_ids(bad)}: set source to own | client | their_clip | screenshot | stock:<site> | drawn | chart | blender | code")
    if filler: m.append(f"stock with no 'why' (filler): {_ids(filler)}: say what it shows that his own footage cannot, or use his footage")
    if m: return "FAIL", " ; ".join(m)
    return "PASS", f"every media file has a source, none matches the AI list or carries AI metadata{' (thumbnail job: AI check skipped)' if thumb else ''}"


def c_asset_viewed(rows, c, work=None, **k):
    bad = []
    for r in rows:
        if not ((r["person"] and (r["kind"] in MEDIA_KINDS)) or r["kind"] == "background"): continue
        sh = r["sheet"] or ""; q = sh if os.path.isabs(sh) else os.path.join(work or "", sh)
        if r["viewed"] is not True or not sh or not (os.path.exists(q) or sh.startswith("(")): bad.append(r)
    if bad: return "FAIL", f"never looked at: {_ids(bad)}. Make a frame sheet (frame_sheet.py), look at it, then set viewed true and sheet to its path"
    return "PASS", "every photo or clip of a person and every background was viewed (sheet exists)"


def _banned_rx(c):
    ids = c["assets"]["banned_files"]
    return re.compile("|".join(r"(?<![0-9A-Za-z])" + re.escape(x) + r"(?![0-9])" for x in ids), re.I) if ids else None


def _name_rx(names):
    return re.compile("|".join(r"(?<![a-z0-9])" + r"[\s_\-.]*".join(map(re.escape, n.lower().split())) + r"(?![a-z0-9])" for n in names), re.I) if names else None


def c_banned_assets(rows, c, man=None, segs=None, ctx=None, **k):
    rx = _banned_rx(c); nx = _name_rx(c["assets"]["consent_excluded"]); hits = []; names = []
    texts = [("manifest " + r["id"], " ".join(list(r["files"]) + [r["source_url"] or "", r["client"] or "", r["text"] or ""])) for r in rows]
    for s in (segs or []): texts.append(("recorded piece", str(s[0] if isinstance(s, (list, tuple)) else s)))
    try:
        if ctx and ctx.get("path"):
            if HERE not in sys.path: sys.path.insert(0, HERE)
            import qc_gate
            pp = qc_gate.pieces_path(ctx["path"])
            if os.path.exists(pp): texts.append(("recorded pieces file", open(pp).read()))
    except Exception: pass
    for pf in (man or {}).get("plan_files", []):
        try: texts.append(("plan " + os.path.basename(pf["path"]), open(pf["path"]).read()))
        except Exception: pass
    for where, t in texts:
        m = rx.search(t) if rx else None
        if m: hits.append(f"{m.group(0).upper()} in {where}")
        n = nx.search(t) if nx else None
        if n: names.append(f"{n.group(0)} in {where}")
    if hits or names:
        return "FAIL", "banned: " + "; ".join((hits + names)[:6]) + ". Remove it (C1797-C1802 are his fat clips, never shown as lean: use " + c["assets"]["lean_photo"] + "; a consent-excluded client is never shown)"
    return "PASS", f"no banned file ({', '.join(c['assets']['banned_files'][:2])}...) or excluded client in {len(rows)} rows, {len(segs or [])} recorded pieces, {len((man or {}).get('plan_files', []))} plan files"


def c_matte(rows, c, **k):
    want = (c["picture"]["matte"] or "birefnet").lower(); bad = [r for r in rows if (r["kind"] == "cutout" or r["matte"]) and (r["matte"] or "").lower() != want]
    if bad: return "FAIL", f"cutout not made with {want}: " + "; ".join(f"{r['id']} ({r['matte'] or 'method not declared'})" for r in bad[:6]) + ". Re-cut with BiRefNet (never Vision, GrabCut or a drawn mask) and set matte birefnet"
    return "PASS", f"{sum(1 for r in rows if r['kind'] == 'cutout')} cutouts, all {want}"


def luma_of(bg):
    s = str(bg or "").strip().lower()
    if s in DARK_NAMES: return DARK_NAMES[s]
    m = re.match(r"^#([0-9a-f]{3}|[0-9a-f]{6})$", s)
    if m:
        h = m.group(1); h = "".join(ch * 2 for ch in h) if len(h) == 3 else h; r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b
    m = re.match(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s)
    if m: r, g, b = map(int, m.groups()); return 0.2126 * r + 0.7152 * g + 0.0722 * b
    return None


def c_bg(rows, c, **k):
    lim = c["picture"]["black_luma_max"]; media = [r for r in rows if _is_media(r)]; bad = []
    for r in rows:
        if not r["bg"]: continue
        l = luma_of(r["bg"])
        if l is not None and l <= lim and _overlap(r, media) < _opt(c, "picture", "bg_cover_frac", 0.5): bad.append((r, l))   # OPT: share of the background that a picture must cover
    if bad: return "FAIL", "black or near-black background with nothing over it (M38 'not black, looks boring'): " + "; ".join(f"{r['id']} {r['bg']} luma {l:.0f}" for r, l in bad[:6]) + f" (limit {lim}). Use his blurred warm frame, a picture's own blur or a lit set"
    return "PASS", f"{sum(1 for r in rows if r['bg'])} declared backgrounds, none black (luma limit {lim}) without a picture over it"


def c_zoom_plan(rows, c, job=None, **k):
    ok = zoom_allowed(c, job); floor = _opt(c, "picture", "zoom_anim_min_pct", 0.0); mx = c["picture"]["zoom_hard_cut_max_pct"]; m = []
    an = [r for r in rows if (r["zoom_pct"] or 0) > floor]
    st = [r for r in rows if (r["cut_scale_pct"] or 0) > mx]
    if an and not ok: m.append("animated scale (punch-in, push, zoom kick, ken-burns; OB 11-07 'zooming in and out non stop'): " + "; ".join(f"{r['id']} {r['zoom_pct']:.1f}%" for r in an[:6]) + " . Remove it; the cutout or picture holds still")
    if st and not ok: m.append(f"hard-cut scale step over {mx}%: " + "; ".join(f"{r['id']} {r['cut_scale_pct']:.0f}%" for r in st[:6]) + ". Keep consecutive shots within the limit")
    if m: return "FAIL", " ; ".join(m)
    return "PASS", ("zoom allowed for this job (UGC)" if ok else f"no animated scale above {floor}%, no hard-cut step above {mx}%")


def c_springs(rows, c, man=None, **k):
    mn = c["picture"]["spring_damping_min"]; bad = [r for r in rows if r["damping"] is not None and r["damping"] < mn]
    if bad: return "FAIL", f"fidgety spring (OB 11-07 'Why is it so fidgety?'), damping under {mn}: " + "; ".join(f"{r['id']} {r['damping']}" for r in bad[:6]) + f". Set damping {mn} to 0.95 and drop kick pulses"
    und = [r for r in rows if "spring" in (r["anim"] or "").split() and r["damping"] is None]; eng = (man or {}).get("engine_spring_damp")
    if und and eng is not None and eng < mn: return "WARN", f"{len(und)} spring elements declare no damping and the engine default is {eng} (under {mn}): {_ids(und)}. Declare damp {mn} or more on each, or patch tmpl_fx.spring"
    return "PASS", f"{sum(1 for r in rows if r['damping'] is not None)} declared springs, all damping {mn} or more"


def _fam(f):
    t = [w for w in re.split(r"[\s_\-]+", str(f).lower()) if w and w not in WEIGHTS]; return " ".join(t)


def c_fonts(rows, c, man=None, **k):
    ok = {_fam(c["text"]["font_headline"]), _fam(c["text"]["font_caption"]), "brand", ""} | {_fam(x) for x in (man or {}).get("declared_fonts", [])}
    bad = [r for r in rows if r["font"] and not any(_fam(r["font"]) == o or (o and (_fam(r["font"]).startswith(o) or o.startswith(_fam(r["font"])))) for o in ok)]
    if bad: return "FAIL", "font outside the brand pair: " + "; ".join(f"{r['id']} {r['font']}" for r in bad[:6]) + f". Use {c['text']['font_headline']}, or list the creator's font in assets.json declared_fonts when the template declares it"
    return "PASS", f"fonts on {sum(1 for r in rows if r['font'])} rows are the brand pair or declared"


def c_upscale(rows, c, **k):
    mx = c["picture"]["upscale_max"]; bad = []
    for r in rows:
        if r["kind"] in NON_OVERLAY or r["scale"] is None or r["kind"] not in MEDIA_KINDS | {"background"}: continue
        s = max(r["scale"]) if isinstance(r["scale"], (list, tuple)) else r["scale"]
        if s > mx: bad.append((r, s))
    if bad: return "FAIL", f"picture upscaled past {mx}x (OB 11-06 'glitchy', 'pixel photos'): " + "; ".join(f"{r['id']} {s:.2f}x" for r, s in bad[:6]) + ". Use a larger source or a smaller box"
    return "PASS", f"no picture scaled past {mx}x"


def c_barbell(rows, c, man=None, **k):
    rx = _rx(c["assets"]["barbell_terms"]); hits = [r for r in rows if rx and rx.search(" ".join(list(r["files"]) + [r["source_url"] or "", r["text"] or "", r["why"] or ""]))]
    if hits: return "WARN", f"barbell squat/deadlift shown or searched: {_ids(hits)}. Pick RDL, hack squat, leg press or machine work (rule: no barbell squat or deadlift)"
    return "PASS", "no barbell squat or deadlift in the plan"


def _tc(t):
    return "?" if t is None else f"{int(t // 60)}:{t % 60:04.1f}"


def c_ob_in_overlay(rows, c, job=None, **k):
    """OB 11-11 on C4465 (M87, widening M37): 'you just put a bench, im not in the overlay'. He is on screen in every overlay while he talks."""
    routes = set(_opt(c, "picture", "ob_in_overlay_routes", None) or OB_ROUTES)
    if c.get("route") not in routes: return "SKIP", f"route {c.get('route')} is not one where he talks to camera ({', '.join(sorted(routes))})"
    cov = [r for r in rows if r["layout"] == "full" and r["kind"] in COVER_KINDS]
    bad = [r for r in cov if r.get("with_ob") is not True]
    if not bad: return "PASS", f"{len(cov)} full-frame overlays, every one shows him"
    fq = [x for x in rows if x["kind"] == "quote"]
    bad.sort(key=lambda r: (0 if any(_overlap(r, [x]) > 0 for x in fq) else 1, r["t0"] or 0))   # covers that sit on his facequote first
    def desc(r):
        f = next((x["id"] for x in fq if _overlap(r, [x]) > 0), ""); n = os.path.basename((r["files"] or [""])[0])
        return f"{r['id']} {_tc(r['t0'])}-{_tc(r['t1'])} {n}".strip() + (f" ({'no face in frames ' + r['ob_frames'] if r.get('ob_frames') and ':' not in r['ob_frames'] and r['with_ob'] is False else 'could not be measured'})") + (f" over facequote {f}" if f else "")
    return "FAIL", (f"{len(bad)} of {len(cov)} full-frame overlays do not show him (OB 11-11: 'you just put a bench, im not in the overlay'; 10-30 'never not show me'): "
                    + "; ".join(desc(r) for r in bad[:6]) + (f" (+{len(bad) - 6} more)" if len(bad) > 6 else "")
                    + ". Make each one show him: his own footage with him in it, him cut out over it (BiRefNet), or him in a box on it; if it already shows him set with_ob true after looking at the frames")


FN = {"gfx_kind": c_gfx_kind, "asset_source": c_asset_source, "asset_viewed": c_asset_viewed, "banned_assets": c_banned_assets, "matte": c_matte,
      "bg": c_bg, "zoom_plan": c_zoom_plan, "springs": c_springs, "fonts": c_fonts, "upscale": c_upscale, "barbell": c_barbell, "ob_in_overlay": c_ob_in_overlay}


def check_all(man, c, job=None, work=None, segs=None, ctx=None):
    rows = man.get("rows", []); R = {}
    for n in CHECKS:
        try: R[n] = FN[n](rows, c, man=man, job=job, work=work, segs=segs, ctx=ctx)
        except Exception as e: R[n] = ("FAIL", f"{n} crashed: {e!r} (fix qc_assets.py or the manifest, then re-gate)")
    return R


def manifest_problems(man, p):
    out = []
    if not man.get("rows") and not man.get("plan_files"): out.append(f"{p} has no rows and no plan file: `qc_assets.py build WORK --plan PLAN.json` (nothing to check is a FAIL, not a pass)")
    for pf in man.get("plan_files", []):
        if not os.path.exists(pf["path"]): out.append(f"plan {pf['path']} is gone: rebuild the manifest")
        elif _sha1(pf["path"]) != pf["sha1"]: out.append(f"plan {os.path.basename(pf['path'])} changed after the manifest was built: `qc_assets.py build WORK`")
    need = [r for r in man.get("rows", []) if r.get("fill_in")]
    if need:
        by = {}
        for r in need:
            for f in r["fill_in"]: by.setdefault(f, []).append(r["id"])
        out.append(f"{len(need)} manifest rows have fields to fill in: " + "; ".join(f"{f}: {', '.join(v[:5])}{' ...' if len(v) > 5 else ''}" for f, v in by.items()) + f" (edit {p}; build keeps what you fill in)")
    return out


# ---------------------------------------------------------------- plug-in interface
def run(ctx):
    work = ctx.get("work"); c = ctx.get("cfg") or cfg_of(ctx.get("route")); route = ctx.get("route")
    need = "assets" in (c.get("records") or [])
    man, p = load_manifest(work)
    if man is None:
        if not need: return {"assets": ("SKIP", f"route {route} keeps no assets record")}
        return {"assets": ("FAIL", f"no asset manifest {p}: `python3 -I ~/ob-editor/bin/qc_assets.py build {work or 'WORK'}` then fill in the listed fields")}
    R = check_all(man, c, ctx.get("job"), work, ctx.get("segs"), ctx)
    mp = manifest_problems(man, p)
    R["assets"] = ("FAIL", mp[0] + (f" (+{len(mp) - 1} more)" if len(mp) > 1 else "")) if mp else ("PASS", f"{len(man.get('rows', []))} rows from {len(man.get('plan_files', []))} plan files")
    return R


def record_problems(route, work, job=None):
    c = cfg_of(route)
    if not work or not os.path.isdir(work): return [f"no WORK folder for the asset record: pass --work WORK"]
    man, p = load_manifest(work)
    if man is None: return [f"manifest {p} missing: `python3 -I ~/ob-editor/bin/qc_assets.py build {work}`"]
    out = manifest_problems(man, p)
    for n, (s, d) in check_all(man, c, job, work).items():
        if s == "FAIL": out.append(f"{n}: {d}")
    return out


# ---------------------------------------------------------------- selftest
def _selftest():
    base = os.path.expanduser("~/ob-scratch/skill-rebuild/wp3/selftest"); os.makedirs(base, exist_ok=True)
    fx = os.path.expanduser("~/ob-editor/qc/regress/look"); os.makedirs(fx, exist_ok=True)
    c = cfg_of("reel-graphics"); ad = cfg_of("ad"); fails = []; n = [0]
    jpg = os.path.join(base, "photo.jpg"); open(jpg, "wb").write(b"\xff\xd8\xff\xe0" + b"\0" * 200 + b"\xff\xd9")
    sheet = os.path.join(base, "sheet.jpg"); open(sheet, "wb").write(b"\xff\xd8\xff\xd9")
    aijpg = os.path.join(base, "gen.jpg"); open(aijpg, "wb").write(b"\xff\xd8\xff\xe1<x:xmpmeta><Iptc4xmpExt:DigitalSourceType>http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia</Iptc4xmpExt:DigitalSourceType></x:xmpmeta>\xff\xd9")

    def base_rows():
        return [row("P1", 0, 4, "photo", files=[jpg], source="own", person=True, viewed=True, sheet=sheet, anim="spring", damping=0.92, scale=1.0),
                row("C1", 4, 8, "clip", files=["/x/pexels/9.mp4"], source="stock:pexels", why="a pharmacy aisle he cannot film", scale=1.05),
                row("B1", 0, 8, "background", bg="#3a2f25", source="own", viewed=True, sheet="(his own frame)", files=[]),
                row("K1", 8, 12, "text", text="IT WORKS", over="blur_aroll", anim="word_slam brush", layout="full"),
                row("T1", 12, 14, "quote", text="a line", files=[jpg], source="own"),
                row("L1", 14, 16, "label", text="EDUCATION"),
                row("U1", 0, 8, "cutout", matte="birefnet", source="own", font="Big Shoulders Black")]

    def case(name, mut, check, want, cfg=None, job=None, segs=None, base_extra=None):
        rows = base_rows()
        if mut:
            res = mut(rows); rows = res if isinstance(res, list) else rows
        man = {"rows": rows, "plan_files": [], "declared_fonts": (base_extra or {}).get("declared_fonts", []), "engine_spring_damp": None}
        s, d = check_all(man, cfg or c, job, base, segs)[check]; n[0] += 1
        ok = (s == want); print(f"  {'ok  ' if ok else 'MISS'} {check:13s} {want:5s} <- {name:42s} got {s}: {d[:110]}")
        if not ok: fails.append(f"{name}: wanted {check} {want}, got {s} ({d})")

    print("clean manifest, every check PASS:")
    for ck in CHECKS: case("clean base", None, ck, "SKIP" if ck == "ob_in_overlay" else "PASS")   # ob_in_overlay applies on talking routes only (long-form below)
    print("planted mistakes, each must FAIL:")
    case("plate over his face, word-timed only", lambda r: r.append(row("X", 20, 24, "plate", text="NO DESIRE", over="aroll", anim="word_timed", layout="on_face")), "gfx_kind", "FAIL")
    case("quote card over a dark board", lambda r: r.append(row("X", 20, 24, "quote", text="q", over="board", anim="fade")), "gfx_kind", "FAIL")
    case("kinetic words over black (not footage)", lambda r: r.append(row("X", 20, 24, "text", text="q", over="black", anim="word_slam", layout="full")), "gfx_kind", "FAIL")
    case("kinetic words in a side panel", lambda r: r.append(row("X", 20, 24, "text", text="q", over="aroll", anim="word_slam", layout="side")), "gfx_kind", "FAIL")
    case("kinetic bar over his A-roll (C4465 r2)", lambda r: r.append(row("X", 20, 24, "plate", text="PEOPLE ARE STUFFED", over="aroll", anim="word_rise word_slam", layout="full")), "gfx_kind", "PASS")
    case("bullet list beside nothing", lambda r: r.append(row("X", 20, 24, "bullet", text="a|b", over="aroll", anim="fade")), "gfx_kind", "FAIL")
    case("text row with a chart under it passes", lambda r: (r.append(row("Y", 20, 24, "chart", source="chart", anim="bars")), r.append(row("X", 20, 24, "list", text="a|b", anim="tick"))), "gfx_kind", "PASS")
    case("no source", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="")), "asset_source", "FAIL")
    case("stockcake in the path", lambda r: r.append(row("X", 20, 22, "photo", files=["/dl/stockcake_gym.jpg"], source="stock:stockcake", why="x")), "asset_source", "FAIL")
    case("AI metadata in the file (trainedAlgorithmicMedia)", lambda r: r.append(row("X", 20, 22, "photo", files=[aijpg], source="own")), "asset_source", "FAIL")
    case("stock as filler, no why", lambda r: r.append(row("X", 20, 22, "clip", files=["/x/pexels/1.mp4"], source="stock:pexels")), "asset_source", "FAIL")
    case("AI file in a thumbnail job is exempt", lambda r: r.append(row("X", 20, 22, "photo", files=[aijpg], source="own")), "asset_source", "PASS", job={"kind": "thumbnail"})
    case("'studio' word is not 'udio'", lambda r: r.append(row("X", 20, 22, "photo", files=["/x/studio_wall.jpg"], source="own")), "asset_source", "PASS")
    case("person photo not viewed", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="client", person=True, viewed=False, sheet="")), "asset_viewed", "FAIL")
    case("viewed but the sheet does not exist", lambda r: r.append(row("X", 20, 22, "clip", files=[jpg], source="own", person=True, viewed=True, sheet="/nope/sheet.jpg")), "asset_viewed", "FAIL")
    case("background never viewed", lambda r: r.append(row("X", 20, 22, "background", bg="#334455", source="own", viewed=None)), "asset_viewed", "FAIL")
    case("banned clip C1799 in a file", lambda r: r.append(row("X", 20, 22, "clip", files=["/Volumes/T7/C1799.MP4"], source="own")), "banned_assets", "FAIL")
    case("banned clip in the recorded pieces", None, "banned_assets", "FAIL", segs=[("/Volumes/T7/C1801.MP4", 0, 3, 0)])
    case("C17990 is not C1799", lambda r: r.append(row("X", 20, 22, "clip", files=["/x/C17990.MP4"], source="own")), "banned_assets", "PASS")
    case("excluded client Client P", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="client", client="Client_P", person=True, viewed=True, sheet=sheet)), "banned_assets", "FAIL")
    case("Vision mask cutout", lambda r: r.append(row("X", 20, 22, "cutout", matte="vision", source="own")), "matte", "FAIL")
    case("cutout method not declared", lambda r: r.append(row("X", 20, 22, "cutout", matte="", source="own")), "matte", "FAIL")
    case("black background, nothing over it", lambda r: r.append(row("X", 30, 34, "background", bg="#000", source="code", viewed=True, sheet="(x)")), "bg", "FAIL")
    case("near-black #0c0c0c", lambda r: r.append(row("X", 30, 34, "background", bg="#0c0c0c", source="code", viewed=True, sheet="(x)")), "bg", "FAIL")
    case("named board with only text", lambda r: r.append(row("X", 30, 34, "background", bg="board", source="code", viewed=True, sheet="(x)")), "bg", "FAIL")
    case("black background with a photo over it", lambda r: (r.append(row("X", 30, 34, "background", bg="black", source="code", viewed=True, sheet="(x)")), r.append(row("Y", 30, 34, "photo", files=[jpg], source="own"))), "bg", "PASS")
    case("punch-in 15%", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="own", zoom_pct=15.0, anim="punch")), "zoom_plan", "FAIL")
    case("hard-cut scale step 25%", lambda r: r.append(row("X", 20, 22, "shot", cut_scale_pct=25.0)), "zoom_plan", "FAIL")
    case("hard-cut step 8% is fine", lambda r: r.append(row("X", 20, 22, "shot", cut_scale_pct=8.0)), "zoom_plan", "PASS")
    case("punch-in on a UGC ad is allowed", lambda r: r.append(row("X", 20, 22, "shot", zoom_pct=15.0)), "zoom_plan", "PASS", cfg=ad, job={"declares": {"ugc": True}})
    case("punch-in on a non-UGC ad", lambda r: r.append(row("X", 20, 22, "shot", zoom_pct=15.0)), "zoom_plan", "FAIL", cfg=ad, job={"declares": {}})
    case("spring damped 0.55", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="own", damping=0.55)), "springs", "FAIL")
    case("spring with no damping declared (engine default low)", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="own", anim="spring")), "springs", "PASS")
    case("font outside the brand pair", lambda r: r.append(row("X", 20, 22, "text", text="q", font="Comic Sans", over="aroll")), "fonts", "FAIL")
    case("creator font declared by the template", lambda r: r.append(row("X", 20, 22, "text", text="q", font="Poppins Bold", over="aroll")), "fonts", "PASS", base_extra={"declared_fonts": ["poppins"]})
    case("picture scaled 1.4x", lambda r: r.append(row("X", 20, 22, "photo", files=[jpg], source="own", scale=1.4)), "upscale", "FAIL")
    case("barbell deadlift clip", lambda r: r.append(row("X", 20, 22, "clip", files=["/x/barbell deadlift.mp4"], source="own")), "barbell", "WARN")

    print("OB in every overlay while he talks (OB 11-11 C4465 'you just put a bench, im not in the overlay'; ledger M87):")
    cl = cfg_of("long-form")
    case("long-form clean manifest", None, "ob_in_overlay", "PASS", cfg=cl)
    case("long-form: full-frame b-roll, no face in 4 frames (a bench)", lambda r: r.append(row("GL05", 68.5, 70.1, "clip", files=["/b roll/C2308.MP4"], source="own", layout="full", with_ob=False, ob_frames="0/4")), "ob_in_overlay", "FAIL", cfg=cl)
    case("long-form: full-frame b-roll that could not be measured", lambda r: r.append(row("GL07", 80, 81.6, "clip", files=["/b roll/C9.MP4"], source="own", layout="full", with_ob=None)), "ob_in_overlay", "FAIL", cfg=cl)
    case("long-form: same cover with him in it (with_ob true)", lambda r: r.append(row("GL04", 54.5, 56.1, "clip", files=["/b roll/C2310.MP4"], source="own", layout="full", with_ob=True, ob_frames="3/4")), "ob_in_overlay", "PASS", cfg=cl)
    case("long-form: facequote on his own shot is fine", lambda r: r.append(row("F01", 63.8, 69.6, "quote", text="q", over="aroll", layout="side")), "ob_in_overlay", "PASS", cfg=cl)
    case("reel-graphics: the check does not apply (SKIP)", lambda r: r.append(row("X", 68.5, 70.1, "clip", files=["/x.mp4"], source="own", layout="full", with_ob=False)), "ob_in_overlay", "SKIP")
    bw = os.path.join(base, "WORK_BENCH"); os.makedirs(bw, exist_ok=True); bp = os.path.join(fx, "plan_longform_bench.events_resolved.json")
    json.dump({"events": [
        {"id": "F01", "type": "facequote", "side": "L", "w": 720, "text": "Why would I take a GLP?\nDream body for years.", "at": {"l0": 0.05}, "edit_in": 63.801, "edit_out": 69.601, "dur": 5.8, "desc": "His question beside him"},
        {"id": "GL04", "type": "ffcover", "full": True, "edit_in": 54.489, "edit_out": 56.089, "dur": 1.6, "src": os.path.join(fx, "ob_at_laptop.jpg"), "in": 0.0, "note": "C2310: OB at his laptop"},
        {"id": "GL05", "type": "ffcover", "full": True, "inlay": True, "edit_in": 68.536, "edit_out": 70.136, "dur": 1.6, "src": os.path.join(fx, "bench_no_ob.jpg"), "in": 2.0, "note": "C2308: an empty bench"}]}, open(bp, "w"), indent=1)
    man, mp = build(bw, plans=[bp], out=os.path.join(base, "bench.assets.json")); R = check_all(man, cl, None, bw); n[0] += 1
    s_, d_ = R["ob_in_overlay"]; ok = s_ == "FAIL" and "GL05" in d_ and "F01" in d_ and "GL04" not in d_ and "1:08.5" in d_
    print(f"  {'ok  ' if ok else 'MISS'} C4465-shaped plan (facequote F01 63.8-69.6, laptop cover GL04, empty-bench cover GL05) built with the real face measure: {s_}: {d_[:150]}"); ok or fails.append(f"bench plan {s_} {d_}")
    n[0] += 1; ok = {r["id"]: r["with_ob"] for r in man["rows"]} == {"F01": None, "GL04": True, "GL05": False}
    print(f"  {'ok  ' if ok else 'MISS'} build stamps with_ob from bin/faces: {[(r['id'], r['with_ob'], r['ob_frames']) for r in man['rows']]}"); ok or fails.append("with_ob stamps")

    print("build on the three plan shapes (synthetic JSON plans, also saved as fixtures):")
    # long-form events: slop (plates, pills, quote beside him, stock reel with no why) + one good photo
    ev = {"events": [
        {"id": "H01", "type": "plate", "chunks": [["THE STRONGEST THING", "c0", "S"]], "at": {"c0": 0.05}, "at_t": {"c0": 0.05}, "edit_in": 0, "edit_out": 16, "dur": 16, "desc": "Hook on his face"},
        {"id": "P01", "type": "pills", "items": [["No GLPs to sell you", "g", "x"]], "items_t": [7.0], "edit_in": 22, "edit_out": 34},
        {"id": "F01", "type": "facequote", "side": "L", "text": "Why would I take a GLP?", "at": {"l0": 0.05}, "edit_in": 63, "edit_out": 69},
        {"id": "R01", "type": "reel", "shots": [{"b": "R01_0", "t": 0, "d": 2, "z": 1.0}], "desc": "FOOTAGE arm scratching stock", "edit_in": 114, "edit_out": 123},
        {"id": "CH1", "type": "chapter", "kicker": "CON #1", "title": "My skin", "edit_in": 86, "edit_out": 88},
        {"id": "L1", "type": "label", "title": "EDUCATION", "sub": "Not medical advice", "edit_in": 177, "edit_out": 180},
        {"id": "V01", "type": "photo", "photos": [["nov1_reta_video", "x"]], "desc": "Callback: his Nov 1 video", "edit_in": 43, "edit_out": 48},
        {"id": "CG1", "type": "photo_overlay", "folder": "proof", "client_proof": True, "items": [["ba_salvatore", 0, "w"]], "edit_in": 894, "edit_out": 912}]}
    tp = {"cam": "C1.MP4", "mic": "m.wav", "timeline": [{"mic": [0, 4], "look": {"name": "cut", "bg": "studio", "matte": "birefnet", "face_w": 300}}, {"mic": [4, 9], "look": {"name": "full", "zoom": 1.22}},
                                                      {"mic": [9, 13], "look": {"name": "card", "bg": "board", "box": [0, 0, 1, 1]}}],
          "els": [{"type": "image", "path": jpg, "t": 1.0, "dur": 3.0, "box": [540, 900, 800]}, {"type": "title", "title": ["IRAN", "WAR"], "t": 5.0, "dur": 2.0, "font": "Poppins"},
                  {"type": "pill", "text": "STEP 1", "t": 10.0, "dur": 2.0, "spring": [3.0, 0.55]}, {"type": "text", "text": "label", "t": 2.0}]}
    lk = {"cues": {"T_GRID": 4.0, "T_STAGE": 12.0, "T_A": 1.0, "T_B": 9.0}, "layout_track": [[0, "COLD"], ["T_GRID", "GRID"], ["T_STAGE", "STAGE"]],
          "cells": {"B_TL": {"src": "/Volumes/T7/b roll/C1424.MP4", "in": 27.0, "dur": 7.4}}, "camera": {"shots": [[0, 1.0, 1.0, "face"], ["T_GRID", 1.0, 1.0]]},
          "elements": [{"type": "title", "id": "title", "lines": [{"words": ["WHAT", "THE"], "size": 140, "rise": 46, "spring": [3.0, 0.9]}], "in": "T_A", "out": "T_B"},
                       {"type": "object3d", "id": "pen", "frames": "/x/pen", "stage_from": "T_A", "out": "T_B"}, {"type": "bar", "label": "HUNGER", "in": "T_GRID", "out": "T_STAGE"},
                       {"type": "keyword", "text": "GLP", "size": 300, "in": "T_GRID", "per": 0.09, "out": "T_STAGE"}]}
    for nm, dd in (("plan_longform_slop.events_resolved.json", ev), ("plan_tmpl_mixed.json", tp), ("plan_levelkit_clean.json", lk)):
        json.dump(dd, open(os.path.join(fx, nm), "w"), indent=1)
    wk = os.path.join(base, "WORK"); os.makedirs(wk, exist_ok=True)
    def b(name, want):
        man, mp = build(wk, plans=[os.path.join(fx, name)], out=os.path.join(base, name + ".assets.json"))
        R = check_all(man, c, None, wk); return man, R
    man, R = b("plan_longform_slop.events_resolved.json", None); n[0] += 1
    ok = R["gfx_kind"][0] == "FAIL" and all(x in R["gfx_kind"][1] for x in ("H01", "P01", "F01")) and "CH1" not in R["gfx_kind"][1] and "L1" not in R["gfx_kind"][1]
    print(f"  {'ok  ' if ok else 'MISS'} long-form slop plan: gfx_kind FAIL names H01 P01 F01, spares chapter + lower third: {R['gfx_kind'][1][:100]}")
    if not ok: fails.append("long-form slop gfx_kind")
    n[0] += 1; ok = R["asset_source"][0] == "FAIL" and "R01" in R["asset_source"][1]
    print(f"  {'ok  ' if ok else 'MISS'} long-form: unsourced stock reel R01 -> asset_source FAIL"); ok or fails.append("longform asset_source")
    n[0] += 1; ok = R["asset_viewed"][0] == "FAIL" and "CG1" in R["asset_viewed"][1]
    print(f"  {'ok  ' if ok else 'MISS'} long-form: client photos CG1 never viewed -> asset_viewed FAIL"); ok or fails.append("longform asset_viewed")
    man, R = b("plan_tmpl_mixed.json", None); n[0] += 1
    ok = R["zoom_plan"][0] == "FAIL" and R["bg"][0] == "FAIL" and R["fonts"][0] == "FAIL" and R["springs"][0] == "FAIL" and R["gfx_kind"][0] == "FAIL"
    print(f"  {'ok  ' if ok else 'MISS'} tmpl plan (zoom 1.22, bare board, Poppins, spring 0.55, title over board): " + " ".join(f"{k}={R[k][0]}" for k in ("zoom_plan", "bg", "fonts", "springs", "gfx_kind"))); ok or fails.append("tmpl plan")
    man, R = b("plan_levelkit_clean.json", None); n[0] += 1
    ok = all(R[k][0] == "PASS" for k in ("gfx_kind", "zoom_plan", "springs", "bg", "matte", "banned_assets"))
    print(f"  {'ok  ' if ok else 'MISS'} level-kit plan (kinetic title+keyword over b-roll grid, 3D, chart): " + " ".join(f"{k}={R[k][0]}" for k in ("gfx_kind", "zoom_plan", "springs", "bg", "matte"))); ok or fails.append(f"levelkit clean: {R}")

    print("engine matte record (WORK/qc/matte.json, birefnet_cut.record):")
    we = os.path.join(base, "WORK_ENGINE"); os.makedirs(os.path.join(we, "qc"), exist_ok=True); pe = os.path.join(we, "plan_engine.json")
    json.dump({"cam": "C1.MP4", "mic": "m.wav", "timeline": [{"mic": [0, 4], "look": {"name": "grid", "cells": [], "face_w": 211}}, {"mic": [4, 8], "look": {"name": "inset", "bg": "studio", "box": [0, 0, 1, 1]}}], "els": []}, open(pe, "w"))
    mj = os.path.join(we, "qc", "matte.json")
    def eb(runs):
        json.dump({"version": 1, "runs": runs}, open(mj, "w")); man, _ = build(we, plans=[pe], out=os.path.join(we, "qc", "assets.json")); return man, check_all(man, c, None, we)["matte"]
    good = {"engine": "tmpl.py", "plan": os.path.abspath(pe), "plan_sha1": _sha1(pe), "method": "birefnet", "looks": ["grid", "inset"]}
    for nm, runs, want in (("no engine run, nothing declared", [], "FAIL"), ("engine ran BiRefNet on this plan", [good], "PASS"),
                           ("engine run for an older version of the plan", [dict(good, plan_sha1="0" * 40)], "FAIL"),
                           ("engine run covers grid only, inset undeclared", [dict(good, looks=["grid"])], "FAIL"),
                           ("engine run says vision", [dict(good, method="vision")], "FAIL")):
        os.path.exists(os.path.join(we, "qc", "assets.json")) and json.dump({"rows": []}, open(os.path.join(we, "qc", "assets.json"), "w"))   # no hand-filled values carried over
        man, (s_, d_) = eb(runs); n[0] += 1; ok = s_ == want
        print(f"  {'ok  ' if ok else 'MISS'} matte         {want:5s} <- {nm:42s} got {s_}: {d_[:90]}"); ok or fails.append(f"engine record {nm}: {s_} {d_}")

    print("run / record_problems:")
    wb = os.path.join(base, "WORK3"); os.makedirs(wb, exist_ok=True); build(wb, plans=[os.path.join(fx, "plan_longform_slop.events_resolved.json")]); n[0] += 1
    rp = record_problems("reel-graphics", wb, {}); ok = any("fields to fill in" in x for x in rp) and any(x.startswith("gfx_kind") for x in rp)
    print(f"  {'ok  ' if ok else 'MISS'} manifest with blanks + a text-only card -> record_problems lists fields and the FAIL: {rp[0][:110] if rp else rp}"); ok or fails.append("record_problems fill-in")
    build(wk, plans=[os.path.join(fx, "plan_levelkit_clean.json")]); n[0] += 1
    rp = record_problems("reel-graphics", wk, {}); ok = rp == []
    print(f"  {'ok  ' if ok else 'MISS'} clean level-kit manifest -> record_problems empty: {rp[:2]}"); ok or fails.append(f"levelkit record {rp}")
    os.makedirs(os.path.join(base, "WORK2"), exist_ok=True); n[0] += 1
    rp = record_problems("reel-graphics", os.path.join(base, "WORK2"), {}); ok = len(rp) == 1 and "build" in rp[0]
    print(f"  {'ok  ' if ok else 'MISS'} no manifest -> says how to build: {rp}"); ok or fails.append("record_problems missing")
    n[0] += 1; r2 = run({"work": os.path.join(base, "WORK2"), "route": "reel-graphics", "cfg": c, "job": {}}); ok = r2["assets"][0] == "FAIL"
    print(f"  {'ok  ' if ok else 'MISS'} run() with no manifest on a route that needs one -> FAIL"); ok or fails.append("run missing")
    n[0] += 1; r3 = run({"work": wk, "route": "reel-graphics", "cfg": c, "job": {}}); ok = set(CHECKS) <= set(r3) and "assets" in r3
    print(f"  {'ok  ' if ok else 'MISS'} run() returns every check row: {sorted(r3)[:4]}..."); ok or fails.append("run rows")
    n[0] += 1; p0 = json.load(open(os.path.join(fx, "plan_levelkit_clean.json"))); p0["elements"].append({"type": "title", "lines": []}); json.dump(p0, open(os.path.join(fx, "plan_levelkit_clean.json"), "w"), indent=1)
    rp = record_problems("reel-graphics", wk, {}); ok = any("changed after the manifest" in x for x in rp)
    print(f"  {'ok  ' if ok else 'MISS'} plan edited after build -> stale manifest reported"); ok or fails.append("stale")
    p0["elements"].pop(); json.dump(p0, open(os.path.join(fx, "plan_levelkit_clean.json"), "w"), indent=1)
    if fails:
        print(f"\nSELFTEST FAILED ({len(fails)} of {n[0]}):"); [print("  -", x) for x in fails]; return 1
    print(f"\nSELFTEST PASSED ({n[0]} cases)"); return 0


def main(argv):
    if "--selftest" in argv: return _selftest()
    if len(argv) < 2 or argv[0] not in ("build", "check", "problems"): print(__doc__); return 2
    cmd, work = argv[0], os.path.expanduser(argv[1]); a = argv[2:]
    def opt(f, many=False):
        v = [a[i + 1] for i, x in enumerate(a) if x == f and i + 1 < len(a)]; return (v if many else (v[0] if v else None))
    route = opt("--route"); job = json.load(open(opt("--job"))) if opt("--job") else {}
    if cmd == "build":
        man, mp = build(work, [os.path.expanduser(p) for p in opt("--plan", True)] or None, opt("--out")); need = [r for r in man["rows"] if r["fill_in"]]
        print(f"manifest {mp}: {len(man['rows'])} rows from {len(man['plan_files'])} plan files; {len(need)} rows have fields to fill in")
        for p in manifest_problems(man, mp): print("  fill in:", p)
        return 0 if man["plan_files"] else 1
    if not route: print("--route ROUTE is required"); return 2
    if cmd == "problems":
        ps = record_problems(route, work, job); [print(p) for p in ps]; print("no problems" if not ps else ""); return 1 if ps else 0
    man, p = load_manifest(work)
    if man is None: print(f"FAIL no manifest {p}: qc_assets.py build {work}"); return 1
    R = run({"work": work, "route": route, "cfg": cfg_of(route), "job": job}); bad = 0
    for k, (s, d) in R.items(): print(f"{s:5s} {k}: {d}"); bad += s == "FAIL"
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
