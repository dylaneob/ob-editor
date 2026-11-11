#!/usr/bin/env python3
"""The v3 stage for full-frame cards (C4367, OB 2026-10-20): "so much black space", "it's just a flat screen", "switch up the
background when doing overlay, rather than black every time... make it prettier", "some of your overlays are just boring slides
that stay there for 5 seconds doing nothing".

Every full-frame card gets:
  1. a background that is never flat black, chosen per card so neighbours differ:
       media  the card's own clip (playing, blurred) or photo (blurred): the phone-video blurred fill, for clips and photo cards
       aroll  OB's own frame at that moment, blurred warm (keeps him present behind text cards)
       wash   a colour wash for the chapter (amber, crimson, teal, indigo, gold) with a drifting light
  2. motion that never stops: the background drifts (parallax) and the content pushes in slowly for the whole card
  3. film grain and a soft vignette over everything (texture, not a flat screen)
Pre-blurred assets come from story/prep_blur.py (hf/assets/blur). cards.py calls assign() once and dress() per card.
"""
import os, re
SRC_RE = re.compile(r'<div class="av" style="position:absolute;left:\d+px;top:20\d\dpx;font-size:\d+px;color:#8f8f8f">[^<]*</div>')

W, H = 3840, 2160
FULLT = {"chapter", "quote", "myths", "clip", "photo_full", "num", "math", "dose", "coins", "timeline", "title", "disclaimer",
         "wall", "versus", "checklist", "scissors", "detector", "find", "slider", "doc", "anchor", "ledger", "ribbon", "jtitle", "jchapter"}
OWN_MOTION = {"chapter", "quote", "myths", "photo_full", "doc", "anchor", "ledger", "ribbon", "jtitle", "jchapter"}   # already push in on their own
NO_STAGE = {"insert"}                                              # full-bleed footage: nothing to dress
EXPLAIN = {"scissors", "detector", "coins", "dose", "slider", "timeline", "find"}   # drawn explainers read best on a clean wash
WASH = {   # chapter -> (deep, mid, light)
    0: ("#140b04", "#4d2c0c", "#f7b733"),   # intro: amber
    1: ("#140b04", "#4d2c0c", "#f7b733"),   # the impossible bar: amber
    2: ("#170506", "#561317", "#ff5a4f"),   # fat bars?: crimson (the lawsuit)
    3: ("#04141a", "#0e4650", "#3fd0c9"),   # the fat your body can't use: teal (the 90s, olestra)
    4: ("#060a1a", "#1a2a66", "#6f8cff"),   # is it safe?: indigo (the science)
    5: ("#110c03", "#574210", "#ffd166"),   # my verdict: gold
    6: ("#03140a", "#0f4a2a", "#3ddc84"),   # creatine myth 6 (2026-10-25): green
    7: ("#170a03", "#5e2c0a", "#ff9a3d"),   # creatine myth 7: orange (OB 10-25: "i dont like the purple")
}


def _media_of(ev, assets):
    """(kind, name) of the card's own blurred media, or None."""
    t = ev["type"]
    if t == "clip": return ("vid", f"clip_{ev['clip']}")
    img = ev.get("image")
    if img and not str(img).startswith("ph:"):
        p = img if "/" in str(img) else f"photos/{img}.jpg"
        return ("img", "img_" + p.replace("/", "_").rsplit(".", 1)[0])
    if t in ("versus", "wall"):
        for it in ev.get("items") or []:
            p = it[0]
            if isinstance(p, str) and p.lower().endswith((".jpg", ".jpeg", ".png")):
                return ("img", "img_" + p.replace("/", "_").rsplit(".", 1)[0])
    return None


def assign(events, proj):
    """Chapter index and background style per event, in time order, so two full-frame cards in a row never share a style."""
    assets = f"{proj}/assets"
    try:
        from PIL import Image
        for e in events:
            img = e.get("image")
            if img and not str(img).startswith("ph:"):
                p_ = f"{assets}/{img if '/' in str(img) else f'photos/{img}.jpg'}"
                if os.path.exists(p_):
                    with Image.open(p_) as im: e["_img_aspect"] = round(im.width / im.height, 4)
    except ImportError: pass
    import json as _json
    fitp = os.path.join(os.path.dirname(proj.rstrip("/")), "story", "fit.json")   # WORK/story/fit.json (story/fit_cards.py)
    fits = _json.load(open(fitp)) if os.path.exists(fitp) else {}
    for e in events:
        f = fits.get(e["id"])
        if f and f.get("s", 1) > 1.0: e["_fit"] = f
    kids = {}
    for e in events:
        if e.get("inlay"): kids.setdefault(e.get("parent"), []).append((e["edit_in"], e["edit_out"]))
    for e in events:   # v3 (OB 10-20: "boring slides that stay there for 5 seconds doing nothing"): camera beats
        if e.get("inlay") or e["type"] in NO_STAGE | {"clip"} or not (e["type"] in FULLT or e.get("full")): continue
        D = e["dur"]; b0 = e["edit_in"]
        beats = [0.0] + [v for v in (e.get("at_t") or {}).values() if isinstance(v, (int, float))]
        beats += [e[k] for k in ("hl_t", "stat_t") if isinstance(e.get(k), (int, float))] + list(e.get("items_t") or [])
        for h0, h1 in e.get("holes", []): beats += [h0 - b0, h1 - b0]
        for a, b in kids.get(e["id"], []): beats += [a - b0, b - b0]
        beats = sorted({round(x, 2) for x in beats if 0 <= x <= D}) + [D]
        cam = []
        for x, y in zip(beats, beats[1:]):
            if y - x >= 3.0:   # a quiet stretch: ease in toward the content, and once more if it runs long
                cam.append(round(x + min(1.6, (y - x) / 2), 2))
                if y - x >= 6.0: cam.append(round(x + (y - x) * 0.72, 2))
        if cam: e["_cam"] = [t for t in cam if t < D - 0.8]
    # a test range (assemble.py --range) passes only its own events: read the whole edit too, so the chapter colour and the
    # background rotation match the full render
    allp = os.path.join(os.path.dirname(proj.rstrip("/")), "events_resolved.json")
    pool = {e["id"]: e for e in (_json.load(open(allp))["events"] if os.path.exists(allp) else [])}
    pool.update({e["id"]: e for e in events})
    seq = sorted(pool.values(), key=lambda e: e["edit_in"])
    chap = sorted(((e["edit_in"], e.get("n", 0)) for e in seq if e["type"] == "chapter"))
    last = None
    for e in seq:
        e["_chap"] = max([n for t, n in chap if t <= e["edit_in"] + 0.01], default=0)
        if e["type"] in NO_STAGE or not (e["type"] in FULLT or e.get("full")): continue
        m = _media_of(e, assets)
        ok = lambda kind, name: os.path.exists(f"{assets}/blur/{name}.{'mp4' if kind == 'vid' else 'jpg'}")
        if e["type"] == "photo_full" and e.get("layout") != "split": style = "none"   # the photo is the frame
        elif m and ok(*m): style = "media"
        elif e["type"] in EXPLAIN or e["type"] in ("chapter", "doc", "title"): style = "wash"
        elif os.path.exists(f"{assets}/blur/still_{e['id']}.jpg"): style = "wash" if last == "aroll" else "aroll"
        else: style = "wash"
        if style == last == "media" and e["type"] != "clip": style = "wash"   # two blurred photos in a row read as one
        e["_bg"] = style; e["_media"] = m
        if style != "none": last = style


def _background(ev, mock):
    D, style = ev["dur"], ev.get("_bg", "wash")
    deep, mid, light = WASH.get(ev.get("_chap", 0), WASH[0])
    js = []
    if style == "media" and ev.get("_media"):
        kind, name = ev["_media"]
        if kind == "vid" and not mock:
            inner = (f'<video class="media clip" src="../assets/blur/{name}.mp4" muted playsinline data-start="0" data-duration="{D:.3f}" '
                     f'data-track-index="1" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover"></video>')
        else:
            inner = f'<img src="../assets/blur/{name}.jpg" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover"/>'
        html = (f'<div class="bg" style="background:{deep}"></div><div id="bgm" style="position:absolute;left:-4%;top:-4%;width:108%;height:108%">{inner}</div>'
                f'<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.30),rgba(0,0,0,.42))"></div>')
        js.append(f'tl.fromTo("#bgm",{{scale:1.06,x:-50}},{{scale:1.13,x:50,duration:{D:.3f},ease:"none"}},0);')
    elif style == "aroll":
        html = (f'<div class="bg" style="background:{deep}"></div><div id="bgm" style="position:absolute;left:-4%;top:-4%;width:108%;height:108%">'
                f'<img src="../assets/blur/still_{ev["id"]}.jpg" style="position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover"/></div>'
                f'<div style="position:absolute;inset:0;background:radial-gradient(120% 100% at 50% 45%,rgba(20,10,4,.38),rgba(10,5,2,.70))"></div>')
        js.append(f'tl.fromTo("#bgm",{{scale:1.05,x:40,y:-20}},{{scale:1.12,x:-40,y:20,duration:{D:.3f},ease:"none"}},0);')
    else:   # wash: a deep chapter colour, a soft light that drifts across, the topographic lines tinted in
        html = (f'<div class="bg" style="background:radial-gradient(130% 110% at 30% 30%,{mid} 0%,{deep} 62%,#050403 100%)"></div>'
                f'<div id="bgl" style="position:absolute;left:-30%;top:-40%;width:110%;height:150%;'
                f'background:radial-gradient(closest-side,{light}33,{light}12 45%,transparent 70%)"></div>'
                f'<div style="position:absolute;inset:0;background:url(../assets/topo_bg.png) center/cover no-repeat;mix-blend-mode:screen;opacity:.35"></div>')
        js.append(f'tl.fromTo("#bgl",{{x:-200,y:-60}},{{x:1500,y:180,duration:{max(D, 3):.3f},ease:"sine.inOut"}},0);')
    return html, js


def _grain(D):
    """Film grain that changes every other frame, and a soft vignette."""
    html = ('<div id="sgr" style="position:absolute;inset:0;background:url(../assets/grain.png);background-size:768px 768px;'
            'mix-blend-mode:overlay;opacity:.16;pointer-events:none"></div>'
            '<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(0,0,0,0) 58%,rgba(0,0,0,.5) 100%);pointer-events:none"></div>')
    js, k, t = [], 0, 0.0
    while t < D:
        js.append(f'tl.set("#sgr",{{backgroundPosition:"{(k * 397) % 768}px {(k * 211) % 768}px"}},{t:.3f});'); k += 1; t += 2 / 29.97
    return html, js


def dress(ev, b, js, mock):
    """Swap the flat .bg for the chosen background, push the content in for the whole card, lay grain on top."""
    if ev["type"] in NO_STAGE or not (ev["type"] in FULLT or ev.get("full")) or ev.get("_bg") in (None, "none"):
        return b, js
    D = ev["dur"]
    bg_html, bg_js = _background(ev, mock)
    flat = '<div class="bg"></div>'
    rest = b[len(flat):] if b.startswith(flat) else b
    # source lines stay where they are (small, at the foot), outside the fit scale
    srcs = SRC_RE.findall(rest); rest = SRC_RE.sub("", rest)
    f = ev.get("_fit")
    if f:   # measured by story/fit_cards.py: scale the content up to fill the safe area, centred
        rest = (f'<div id="fit" style="position:absolute;inset:0;transform-origin:0 0;'
                f'transform:translate({f["tx"]:.1f}px,{f["ty"]:.1f}px) scale({f["s"]:.4f})">{rest}</div>')
    cam = ev.get("_cam") or []
    if cam:   # a camera that breathes: in 6 %, back to 2 %, in again..., centred on the content
        f_ = ev.get("_fit"); bx = f_ and f_.get("box")
        ox, oy = ((f_["s"] * (bx[0] + bx[2]) / 2 + f_["tx"], f_["s"] * (bx[1] + bx[3]) / 2 + f_["ty"]) if bx else (W / 2, H / 2))
        rest = f'<div id="cam" style="position:absolute;inset:0;transform-origin:{ox:.0f}px {oy:.0f}px">{rest}</div>'
        cam_js = [f'tl.to("#cam",{{scale:{1.03 if k % 2 == 0 else 1.01},duration:1.1,ease:"power2.inOut"}},{t:.2f});' for k, t in enumerate(cam)]
    else: cam_js = []
    if ev["type"] in OWN_MOTION:
        content = rest
        push = []
    else:
        content = f'<div id="stg" style="position:absolute;inset:0;transform-origin:50% 50%">{rest}</div>'
        # Johnny measured: graphics push in about 1.5 % a second (capped so a long card's content stays inside the frame)
        push = [f'tl.fromTo("#stg",{{scale:1}},{{scale:{1 + min(0.012 * D, 0.08):.4f},duration:{D:.3f},ease:"none"}},0);']
    content += "".join(srcs)
    gr_html, gr_js = _grain(D)
    return bg_html + content + gr_html, bg_js + push + js + cam_js + gr_js
