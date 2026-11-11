#!/usr/bin/env python3
"""Generate HyperFrames compositions (Dan Go card system) for resolved edit events.

  python3 cards.py EVENTS_RESOLVED.json PROJECT_DIR [--mock]

--mock swaps the A-roll <video> for a still <img> so Puppeteer can screenshot the
exact same layout for the shot-by-shot breakdown. Without --mock the A-roll is
a muted <video> (assets/aroll/<id>.mp4) for the real HyperFrames render.
Canvas 3840x2160. Times inside a composition are relative to the event start.
"""
import html, json, os, sys

Y, R = "#F7DC3A", "#E53935"
CONTAIN = {"extinguisher"}  # tall product shots: show the whole object
W, H = 3840, 2160
# Side layout (replaces the corner PiP, OB 2026-10-16): graphic panel on the left, OB on the right, uncropped.
SIDE_W, SIDE_SHIFT, SIDE_S = 2300, 1150, 0.745
SIDE_TYPES = {"photo", "equation", "stat_ratio", "stat_bars", "stat_list", "stat_columns", "stat_count",
              "stat_equals", "proof", "poster", "study", "chart_line"}
# Overlay slots on OB's own frame (he sits centre, face ~x 1600-2280): nothing drawn around the images.
SLOTS = {
    "portrait4": [(120, 511, 640, 1138), (820, 511, 640, 1138), (2380, 511, 640, 1138), (3080, 511, 640, 1138)],
    "landscape4": [(140, 40, 1180, 1020), (140, 1100, 1180, 1020), (2520, 40, 1180, 1020), (2520, 1100, 1180, 1020)],
    "pair_LR": [(140, 230, 1300, 1700), (2400, 230, 1300, 1700)],
    "flash": [(160, 260, 1240, 1640), (2440, 260, 1240, 1640)],
}

ICONS = {  # 24x24 line icons, black on the yellow tile
    "drop": '<path d="M12 3c-3.5 4.6-6 7.7-6 10.6a6 6 0 0 0 12 0C18 10.7 15.5 7.6 12 3z"/>',
    "dollar": '<path d="M12 2v20M17 6.5c0-2-2.2-3-5-3s-5 1.3-5 3.4 2.4 3 5 3.6 5 1.4 5 3.6-2.2 3.4-5 3.4-5-1.2-5-3.2"/>',
    "link": '<path d="M10 14a4.2 4.2 0 0 0 6 0l3-3a4.2 4.2 0 0 0-6-6l-1.2 1.2M14 10a4.2 4.2 0 0 0-6 0l-3 3a4.2 4.2 0 0 0 6 6l1.2-1.2"/>',
    "steps": '<path d="M8.5 3c-1.7 0-2.8 2-2.8 4.6 0 2.3.9 3.7 1.1 5.3h3.4c.2-1.6 1.1-3 1.1-5.3C11.3 5 10.2 3 8.5 3z"/><path d="M6.9 15.1h3.3v1.4a1.65 1.65 0 0 1-3.3 0z"/><path d="M15.5 6.8c-1.7 0-2.8 2-2.8 4.6 0 2.3.9 3.7 1.1 5.3h3.4c.2-1.6 1.1-3 1.1-5.3 0-2.6-1.1-4.6-2.8-4.6z"/><path d="M13.9 18.9h3.3v1.4a1.65 1.65 0 0 1-3.3 0z"/>',
    "flame": '<path d="M12 2.5c.8 3.4 5 5.6 5 10.2a5 5 0 0 1-10 0c0-2.4 1.2-3.9 2.5-5 .1 2 .9 3.2 2 3.6-.6-3.4.5-6.4.5-8.8z"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.3"/>',
    "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2.2"/><path d="M11 18.3h2"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.4 15.4L21 21"/>',
    "sprout": '<path d="M12 21v-8.5M12 12.5c0-4.2 3-7.5 8-7.5 0 5-3 7.5-8 7.5zM12 15c0-3.2-2.2-5.5-6.5-5.5 0 3.3 2.2 5.5 6.5 5.5z"/>',
    "plate": '<circle cx="12.3" cy="12" r="5"/><path d="M3.5 3v5.5a2 2 0 0 0 2 2V21M5.5 3v4M7.5 3v5.5a2 2 0 0 1-2 2"/><path d="M20.5 3c-1.6 1-2.6 3-2.6 6.2 0 2.4 1.1 3.3 2.6 3.3V21"/>',
    "percent": '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/>',
    "tag": '<path d="M3 12.5V4.2C3 3.5 3.5 3 4.2 3h8.3l8.5 8.5-8.8 8.8z"/><circle cx="7.6" cy="7.6" r="1.6"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
}

CSS = f"""
@font-face {{ font-family: 'DINC'; src: url('../assets/fonts/DINCondensed-Bold.ttf'); }}
@font-face {{ font-family: 'AvM'; src: url('../assets/fonts/AvenirNext-Medium.ttf'); }}
@font-face {{ font-family: 'AvDB'; src: url('../assets/fonts/AvenirNext-DemiBold.ttf'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #0c0c0c; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; color: #fff; }}
.bg {{ position: absolute; inset: 0; background: #0c0c0c url('../assets/topo_bg.png') center / cover no-repeat; }}
.din {{ font-family: 'DINC'; }} .av {{ font-family: 'AvM'; }} .avb {{ font-family: 'AvDB'; }}
.media {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; display: block; }}
.layer, .endlayer {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; }}
.pip {{ position: absolute; left: 3080px; top: 1218px; width: 660px; height: 842px; border: 8px solid {Y};
        border-radius: 28px; overflow: hidden; background: #000; }}
.pip .layer {{ left: -1208px; top: -216px; transform: scale(.8); transform-origin: 0 0; }}
.area {{ position: absolute; left: 140px; top: 0; width: 2820px; height: {H}px; }}
.center {{ position: absolute; left: 0; width: 100%; text-align: center; }}
.u {{ position: relative; display: inline-block; }}
.ubar {{ position: absolute; left: 0; right: 0; bottom: 4px; height: 12px; background: {R}; transform-origin: left center; }}
.mk {{ background-image: linear-gradient({Y}, {Y}); background-repeat: no-repeat; background-position: 0 88%; background-size: 0% 46%;
       -webkit-box-decoration-break: clone; box-decoration-break: clone; padding: 0 6px; }}
.ov {{ position: absolute; object-fit: contain; display: block; }}
"""


def esc(s):
    return html.escape(s or "", quote=True)


def aroll(ev, mock, cls="layer"):
    """The A-roll layer: a still for the breakdown mockup, the edited clip for the render."""
    if mock:
        return f'<div class="{cls}"><img class="media" src="../assets/stills/{ev["id"]}.jpg"/></div>'
    return (f'<div class="{cls}"><video id="aroll" class="media clip" src="../assets/aroll/{ev["id"]}.mp4" muted playsinline '
            f'data-start="0" data-duration="{ev["dur"]:.3f}" data-track-index="0"></video></div>')


def underline(text, phrase):
    t = esc(text)
    p = esc(phrase or "")
    if p and p in t:
        return t.replace(p, f'<span class="u">{p}<span class="ubar"></span></span>', 1)
    return t


def body_for(ev, mock):
    """Returns (html_body, js_timeline_lines)."""
    t, js = ev["type"], []
    D = ev["dur"]
    if t == "chapter":
        icon = ICONS.get(ev.get("icon"), ICONS["target"])
        b = f"""<div class="bg"></div><div id="cw" style="position:absolute;left:0;top:0;width:3840px;height:2160px;transform-origin:50% 50%">
<div id="tile" style="position:absolute;left:{W//2-115}px;top:770px;width:230px;height:230px;border-radius:48px;background:{Y};display:flex;align-items:center;justify-content:center">
<svg width="140" height="140" viewBox="0 0 24 24" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{icon}</svg></div>
<div id="title" class="center din" style="top:1068px;font-size:132px;letter-spacing:1px">{ev['n']}. {esc(ev['title'])}</div></div>"""
        js += ['tl.fromTo("#tile",{scale:.55,opacity:0},{scale:1,opacity:1,duration:POP.dur,ease:POP.ease},0);',
               'tl.fromTo("#title",{y:34,opacity:0},{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease},.1);']
    elif t == "quote":
        b = f"""<div class="bg"></div><div id="cw" style="position:absolute;left:0;top:0;width:3840px;height:2160px;transform-origin:50% 50%">
<div id="q" class="din" style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:2900px;text-align:center;font-size:152px;line-height:1.17">{underline(ev['text'], ev.get('underline')).replace(chr(10), '<br/>')}</div></div>"""
        js += ['tl.fromTo("#q",{opacity:0,y:24},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
               'tl.fromTo(".ubar",{scaleX:0},{scaleX:1,duration:SOFT.dur,ease:SOFT.ease},.4);']
    elif t == "myths":
        rows = "".join(f'<div class="myth din" id="m{i}" style="position:absolute;left:0;width:100%;text-align:center;top:{790+i*300}px;font-size:250px">'
                       f'<span class="u">{esc(txt)}<span class="ubar sbar" style="bottom:auto;top:52%;height:18px"></span></span></div>'
                       for i, (txt, _) in enumerate(ev["items"]))
        b = f"""<div class="bg"></div><div id="cw" style="position:absolute;left:0;top:0;width:3840px;height:2160px;transform-origin:50% 50%">
<div id="mt" class="center avb" style="top:590px;font-size:96px;color:#bdbdbd">{esc(ev.get('title',''))}</div>{rows}</div>"""
        pass  # "It's not:" is on screen from frame 1 (no empty first frame)
        for i, it in enumerate(ev["items_t"]):
            js += [f'tl.fromTo("#m{i}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{it:.3f});',
                   f'tl.fromTo("#m{i} .sbar",{{scaleX:0}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{it+0.55:.3f});']
    elif t == "split":
        items = "".join(f'<li id="b{i}" style="margin-bottom:62px;list-style:none;display:flex;gap:34px"><span style="color:{Y}">&bull;</span><span>{esc(txt)}</span></li>'
                        for i, (txt, _) in enumerate(ev["items"]))
        n = len(ev["items"]); block_h = 200 + n * 172
        top = max(380, 1080 - block_h // 2)
        # transforms only (no left/width): the video slides right, the text panel slides in from the left
        b = f"""<div class="bg"></div>
<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll(ev, mock)}</div>
<div id="panel" style="position:absolute;left:0;top:0;width:1728px;height:{H}px;overflow:hidden">
  <div class="bg"></div>
  <div id="st" class="din" style="position:absolute;left:190px;top:{top}px;width:1480px;font-size:138px">{esc(ev.get('title',''))}</div>
  <ul id="ul" class="av" style="position:absolute;left:196px;top:{top+230}px;width:1480px;font-size:92px;line-height:1.16">{items}</ul></div>"""
        js += ['tl.fromTo("#vid",{x:0},{x:864,duration:SLIDE.dur,ease:SLIDE.ease},0);',
               'tl.fromTo("#panel",{x:-1728},{x:0,duration:SLIDE.dur,ease:SLIDE.ease},0);',
               'tl.fromTo("#st",{opacity:0,x:-30},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.3);']
        for i, it in enumerate(ev["items_t"]):
            js.append(f'tl.fromTo("#b{i}",{{opacity:0,x:-36}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(it, 0.45):.3f});')
        if D > 1.6:
            js += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});',
                   f'tl.to("#panel",{{x:-1728,duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});']
    elif t == "label":
        b = f"""{aroll(ev, mock)}
<div style="position:absolute;left:0;top:0;width:2000px;height:700px;background:radial-gradient(ellipse at 0% 0%,rgba(0,0,0,.55),rgba(0,0,0,0) 70%)"></div>
<div id="lb" style="position:absolute;left:170px;top:120px">
  <div style="width:130px;height:10px;background:{Y};margin-bottom:34px"></div>
  <div class="din" style="font-size:118px;line-height:1">{esc(ev.get('title',''))}</div>
  <div class="avb" style="font-size:64px;color:#e8e8e8;margin-top:18px">{esc(ev.get('sub',''))}</div></div>"""
        js += ['tl.fromTo("#lb",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0);',
               f'tl.to("#lb",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.3, 0.5):.3f});']
    elif t in SIDE_TYPES:
        inner, extra = card_area(ev), card_js(ev)
        b = f"""<div class="bg"></div>
<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll(ev, mock)}</div>
<div id="panel" style="position:absolute;left:0;top:0;width:{SIDE_W}px;height:{H}px;overflow:hidden">
  <div class="bg"></div>
  <div style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform:scale({SIDE_S});transform-origin:0 50%"><div class="area">{inner}</div></div></div>"""
        js += [f'tl.fromTo("#vid",{{x:0}},{{x:{SIDE_SHIFT},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
               f'tl.fromTo("#panel",{{x:-{SIDE_W}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},0);'] + extra
        if D > 1.6:
            js += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});',
                   f'tl.to("#panel",{{x:-{SIDE_W},duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});']
    elif t == "end":
        b = f"""<div class="bg"></div>
<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll(ev, mock)}</div>
<div id="panel" style="position:absolute;left:0;top:0;width:{SIDE_W}px;height:{H}px;overflow:hidden">
  <div class="bg"></div>
  <div id="eb" style="position:absolute;left:200px;top:640px;width:1950px">
    <div style="width:150px;height:12px;background:{Y};margin-bottom:46px"></div>
    <div class="din" style="font-size:250px;line-height:1">{esc(ev['title'])}</div>
    <div class="avb" style="font-size:84px;margin-top:50px;line-height:1.2">{esc(ev['line'])}</div>
    <div class="av" style="font-size:64px;margin-top:44px;color:#bdbdbd">{esc(ev.get('small',''))}</div></div></div>"""
        js += [f'tl.fromTo("#vid",{{x:0}},{{x:{SIDE_SHIFT},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
               f'tl.fromTo("#panel",{{x:-{SIDE_W}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},0);',
               'tl.fromTo("#eb",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.3);']
    elif t == "myths_overlay":
        # OB's face stays on screen from frame 1: the list sits on the dark left of his own frame
        rows = "".join(f'<div class="din" id="m{i}" style="position:absolute;left:200px;top:{760+i*290}px;font-size:220px;line-height:1">'
                       f'<span class="u">{esc(txt)}<span class="ubar sbar" style="bottom:auto;top:50%;height:18px"></span></span></div>'
                       for i, (txt, _) in enumerate(ev["items"]))
        b = f"""{aroll(ev, mock)}
<div style="position:absolute;left:0;top:0;width:1700px;height:{H}px;background:linear-gradient(90deg,rgba(0,0,0,.62),rgba(0,0,0,.35) 60%,rgba(0,0,0,0))"></div>
<div id="mt" class="avb" style="position:absolute;left:206px;top:610px;font-size:92px;color:#d8d8d8">{esc(ev.get('title',''))}</div>{rows}"""
        for i, it in enumerate(ev["items_t"]):
            js += [f'tl.fromTo("#m{i}",{{opacity:0,x:-50}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{it:.3f});',
                   f'tl.fromTo("#m{i} .sbar",{{scaleX:0}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{it+0.55:.3f});']
    elif t == "photo_overlay":
        # Images straight on OB's frame, nothing around them. Each item: [key, slot index, anchor]; a new
        # image in an occupied slot replaces the old one (rapid-fire montage = many items, 2 slots).
        slots = SLOTS[ev["layout"]]; imgs = []; last_in_slot = {}
        times = ev["items_t"]
        for i, (key, si, _) in enumerate(ev["items"]):
            x, y, w, h = slots[si]
            imgs.append(f'<img class="ov" id="o{i}" src="../assets/{ev.get("folder","proof")}/{key}.jpg" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;opacity:0"/>')
            if si in last_in_slot:
                j = last_in_slot[si]
                js.append(f'tl.to("#o{j}",{{opacity:0,duration:.12,ease:"none"}},{max(times[i]-0.02, 0):.3f});')
            js.append(f'tl.fromTo("#o{i}",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{times[i]:.3f});')
            last_in_slot[si] = i
        b = f'{aroll(ev, mock)}{"".join(imgs)}'
        if ev.get("foot"):
            b += f'<div class="av" style="position:absolute;left:60px;top:2080px;font-size:40px;color:rgba(255,255,255,.75);text-shadow:0 2px 10px rgba(0,0,0,.8)">{esc(ev["foot"])}</div>'
        if ev.get("label"):
            b += (f'<div id="lb" style="position:absolute;left:170px;top:90px"><div class="din" style="font-size:110px;line-height:1;'
                  f'text-shadow:0 4px 24px rgba(0,0,0,.7)">{esc(ev["label"])}</div></div>')
            js.append('tl.fromTo("#lb",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0);')
        if D > 1.0:  # everything clears at the end (no hard pop-off)
            js.append(f'tl.to(".ov",{{opacity:0,duration:.25,ease:"none"}},{D-0.27:.3f});')
    else:
        raise ValueError(t)
    if t in ("chapter", "quote", "myths"):  # no dead frames: slow constant-speed push-in while the card holds
        js.append(f'tl.fromTo("#cw",{{scale:1}},{{scale:{1.07 if t == "myths" else 1.04},duration:{D:.3f},ease:"none"}},0);')
    return b, js


def card_area(ev):
    t = ev["type"]
    if t == "photo":
        ph = ev["photos"]; n = len(ph)
        w, h = (1280, 990) if n == 2 else (1900, 1250)
        has_t = bool(ev.get("title")); top0 = (2160 - ((150 if has_t else 0) + h + 170)) // 2
        tiles = "".join(f'<div class="ph" id="p{i}" style="display:flex;flex-direction:column;align-items:center;gap:40px">'
                        f'<div style="width:{w}px;height:{h}px;border-radius:30px;overflow:hidden;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.55)">'
                        f'<img src="../assets/photos/{k}.jpg" style="width:100%;height:100%;object-fit:{"contain" if k in CONTAIN else "cover"}"/></div>'
                        f'<div class="din" style="font-size:{104 if len(lbl) < 30 else 100}px;text-align:center;max-width:{w + 300}px">{esc(lbl)}</div></div>'
                        for i, (k, lbl) in enumerate(ph))
        title = f'<div id="pt" class="center avb" style="top:{top0}px;font-size:96px">{esc(ev.get("title",""))}</div>' if has_t else ""
        return f'{title}<div style="position:absolute;left:0;top:{top0 + (150 if has_t else 0)}px;width:100%;display:flex;justify-content:center;gap:120px">{tiles}</div>'
    if t == "equation":
        (lk, ll), mid, (rk, rl) = ev["left"], ev["mid"], ev["right"]
        def tile(i, k, l):
            return (f'<div id="{i}" style="display:flex;flex-direction:column;align-items:center;gap:36px">'
                    f'<div style="width:920px;height:760px;border-radius:30px;overflow:hidden;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.55)">'
                    f'<img src="../assets/photos/{k}.jpg" style="width:100%;height:100%;object-fit:{"contain" if k in CONTAIN else "cover"}"/></div>'
                    f'<div class="din" style="font-size:100px">{esc(l)}</div></div>')
        return (f'<div style="position:absolute;left:0;top:600px;width:100%;display:flex;justify-content:center;align-items:flex-start;gap:60px">'
                f'{tile("eqL", lk, ll)}<div id="eqM" class="din" style="font-size:150px;margin-top:300px;white-space:nowrap">+ {esc(mid)} <span style="color:{Y}">=</span></div>'
                f'{tile("eqR", rk, rl)}</div>')
    if t == "stat_ratio":
        return (f'<div id="sr" style="position:absolute;left:0;top:560px;width:100%;display:flex;justify-content:center;gap:160px;align-items:flex-end">'
                f'<div style="text-align:center"><div class="avb" style="font-size:88px;color:#cfcfcf">{esc(ev["left"])}</div><div class="din" style="font-size:520px;line-height:1">{esc(ev["a"])}</div></div>'
                f'<div class="din" style="font-size:420px;line-height:1.1;color:{Y}">:</div>'
                f'<div style="text-align:center"><div class="avb" style="font-size:88px;color:#cfcfcf">{esc(ev["right"])}</div><div class="din" style="font-size:520px;line-height:1">{esc(ev["b"])}</div></div></div>'
                f'<div id="srs" class="center avb" style="top:1420px;font-size:80px;color:#bdbdbd">{esc(ev.get("sub",""))}</div>')
    if t == "stat_bars":
        mx = max(v for _, v, _ in ev["bars"]); rows = ""
        for i, (lbl, v, txt) in enumerate(ev["bars"]):
            wpx = int(2300 * v / mx)
            rows += (f'<div style="position:absolute;left:150px;top:{760+i*520}px">'
                     f'<div class="avb" style="font-size:78px;color:#e6e6e6;margin-bottom:34px">{esc(lbl)}</div>'
                     f'<div style="display:flex;align-items:center;gap:50px"><div class="bar" id="bar{i}" style="width:{wpx}px;height:150px;border-radius:75px;background:{Y if i == 0 else "#f2f2f2"};transform-origin:left center"></div>'
                     f'<div class="din" id="bv{i}" style="font-size:150px;white-space:nowrap">{esc(txt)}</div></div></div>')
        return rows
    if t == "stat_list":
        return "".join(f'<div id="sl{i}" class="center din" style="top:{690+i*330}px;font-size:210px">{esc(x)}</div>' for i, x in enumerate(ev["items"]))
    if t == "stat_columns":
        return (f'<div style="position:absolute;left:0;top:620px;width:100%;display:flex;justify-content:center;gap:220px">'
                + "".join(f'<div id="sc{i}" style="width:1150px;text-align:center"><div class="din" style="font-size:520px;line-height:1;color:{Y if i == 0 else "#fff"}">{esc(n)}</div>'
                          f'<div class="avb" style="font-size:84px;line-height:1.2;margin-top:40px">{esc(l)}</div></div>' for i, (n, l) in enumerate(ev["cols"]))
                + '</div>')
    if t == "stat_count":
        return (f'<style>#cnt::before{{counter-reset:n var(--n);content:counter(n)}}</style>'
                f'<div class="center avb" style="top:620px;font-size:100px;color:#dcdcdc">{esc(ev["label"])}</div>'
                f'<div class="center" style="top:820px"><span id="cnt" class="din" style="font-size:600px;line-height:1;--n:{ev["from"]}"></span>'
                f'<span class="avb" style="font-size:140px;color:{Y};margin-left:40px">{esc(ev["unit"])}</span></div>')
    if t == "stat_equals":
        return "".join(f'<div id="se{i}" class="center din" style="top:{640+i*440}px;font-size:170px">{esc(a)} <span style="color:{Y}">= {esc(b)}</span></div>'
                       for i, (a, b, _) in enumerate(ev["rows"]))
    if t == "proof":
        tiles = "".join(f'<div class="pt" id="pr{i}" style="width:1340px;height:820px;border-radius:26px;overflow:hidden;background:#050505;box-shadow:0 24px 60px rgba(0,0,0,.6)">'
                        f'<img src="../assets/proof/proof{i+1}.jpg" style="width:100%;height:100%;object-fit:contain"/></div>' for i in range(4))
        return (f'<div id="pt0" class="din" style="position:absolute;left:40px;top:120px;font-size:150px">{esc(ev["title"])}'
                f'<span class="av" style="font-size:50px;color:#9a9a9a;margin-left:40px">{esc(ev["foot"])}</span></div>'
                f'<div id="grid" style="position:absolute;left:40px;top:330px;width:2740px;display:grid;grid-template-columns:1340px 1340px;gap:60px">{tiles}</div>')
    if t == "proof_pages":
        p1, p2 = ev["page1"], ev["page2"]
        tall = "".join(f'<div class="t1" id="pa{i}" style="width:640px;height:1138px;border-radius:26px;overflow:hidden;background:#050505;box-shadow:0 24px 60px rgba(0,0,0,.6)">'
                       f'<img src="../assets/proof/{k}.jpg" style="width:100%;height:100%;object-fit:cover"/></div>' for i, k in enumerate(p1["tiles"]))
        wide = "".join(f'<div class="t2" id="pb{i}" style="position:relative;width:930px;height:800px;border-radius:26px;overflow:hidden;background:#050505;box-shadow:0 24px 60px rgba(0,0,0,.6)">'
                       f'<img src="../assets/proof/{k}.jpg" style="width:100%;height:100%;object-fit:cover"/>'
                       + (f'<div class="din" style="position:absolute;left:28px;bottom:22px;font-size:76px;color:#fff;text-shadow:0 4px 18px rgba(0,0,0,.8)">{esc(lbl)}</div>' if lbl else "")
                       + '</div>' for i, (k, lbl) in enumerate(p2["tiles"]))
        return (f'<div id="ptt" class="din" style="position:absolute;left:40px;top:200px;font-size:150px">{esc(ev["title"])}'
                f'<span class="av" style="font-size:50px;color:#9a9a9a;margin-left:40px">{esc(ev["foot"])}</span></div>'
                f'<div id="tag1" class="avb" style="position:absolute;left:44px;top:390px;font-size:64px;color:{Y}">{esc(p1["tag"])}</div>'
                f'<div id="tag2" class="avb" style="position:absolute;left:44px;top:390px;font-size:64px;color:{Y};opacity:0">{esc(p2["tag"])}</div>'
                f'<div id="row1" style="position:absolute;left:40px;top:560px;display:flex;gap:60px">{tall}</div>'
                f'<div id="grid2" style="position:absolute;left:470px;top:520px;display:grid;grid-template-columns:930px 930px;gap:44px">{wide}</div>')
    if t == "proof_quote":
        tall = "".join(f'<div id="pq{i}" style="width:640px;height:1138px;border-radius:26px;overflow:hidden;background:#050505;box-shadow:0 24px 60px rgba(0,0,0,.6)">'
                       f'<img src="../assets/proof/{k}.jpg" style="width:100%;height:100%;object-fit:cover"/></div>' for i, k in enumerate(ev["tiles"]))
        return (f'<div id="pqt" class="din" style="position:absolute;left:40px;width:2740px;text-align:center;top:300px;font-size:140px">{underline(ev["text"], ev.get("underline"))}</div>'
                f'<div style="position:absolute;left:40px;top:600px;display:flex;gap:60px">{tall}</div>')
    if t == "poster":
        return (f'<div style="position:absolute;left:{1410-700}px;top:90px;width:1400px;height:1980px;border-radius:24px;overflow:hidden;background:#fff;box-shadow:0 30px 90px rgba(0,0,0,.6)">'
                f'<img id="poster" src="../assets/photos/{ev["image"]}.jpg" style="width:100%;height:100%;object-fit:contain;transform-origin:50% 70%"/></div>'
                f'<div class="av" style="position:absolute;left:30px;top:2040px;font-size:40px;color:#8a8a8a">{esc(ev.get("credit",""))}</div>')
    if t == "study":
        s = ev["study"]
        finding = esc(s["finding"])
        if s.get("hl") and esc(s["hl"]) in finding:
            finding = finding.replace(esc(s["hl"]), f'<span class="mk">{esc(s["hl"])}</span>', 1)
        stat = ""
        if s.get("stat"):
            stat = (f'<div id="sst" style="display:flex;align-items:baseline;gap:40px;margin-top:70px;padding-left:20px">'
                    f'<div class="din" style="font-size:300px;line-height:.9;color:{Y}">{esc(s["stat"])}</div>'
                    f'<div class="avb" style="font-size:72px;line-height:1.2;color:#e6e6e6;max-width:1500px">{esc(s.get("stat_label",""))}</div></div>')
        return (f'<div style="position:absolute;left:40px;top:250px;width:2740px">'
                f'<div id="skk" style="display:flex;align-items:center;gap:30px;margin-bottom:40px">'
                f'<span class="avb" style="font-size:54px;background:{Y};color:#111;padding:10px 26px;border-radius:12px;letter-spacing:2px">STUDY</span>'
                f'<span class="avb" style="font-size:60px;color:#d6d6d6">{esc(s["journal"])} &middot; {esc(s["year"])}</span></div>'
                f'<div id="spp" style="background:#fff;border-radius:30px;padding:80px 90px;box-shadow:0 30px 90px rgba(0,0,0,.55);color:#111">'
                f'<div class="avb" style="font-size:84px;line-height:1.15">{esc(s["title"])}</div>'
                f'<div class="av" style="font-size:54px;color:#777;margin-top:26px">{esc(s["authors"])}</div>'
                f'<div style="height:4px;background:#ececec;margin:50px 0"></div>'
                f'<div class="av" style="font-size:90px;line-height:1.3">{finding}</div>'
                f'<div class="av" style="font-size:46px;color:#8a8a8a;margin-top:44px">PubMed {esc(s["pmid"])} &middot; doi.org/{esc(s["doi"])}</div></div>'
                f'{stat}</div>')
    if t == "chart_line":
        c = ev["chart"]; xs = [p[0] for p in c["points"]]; ys = [p[1] for p in c["points"]]
        x0, x1, y0, y1 = 260, 2560, 1120, 80
        X = lambda v: x0 + (v - c["xmin"]) / (c["xmax"] - c["xmin"]) * (x1 - x0)
        Yp = lambda v: y0 - (v - c["ymin"]) / (c["ymax"] - c["ymin"]) * (y0 - y1)
        grid = "".join(f'<line x1="{x0}" y1="{Yp(g):.0f}" x2="{x1}" y2="{Yp(g):.0f}" stroke="#2c2c2c" stroke-width="3"/>'
                       f'<text x="{x0-30}" y="{Yp(g)+16:.0f}" text-anchor="end" font-family="AvM" font-size="48" fill="#9a9a9a">{g}{c.get("unit","")}</text>'
                       for g in c["yticks"])
        xl = "".join(f'<text x="{X(v):.0f}" y="{y0+80}" text-anchor="middle" font-family="AvM" font-size="48" fill="#9a9a9a">{v}</text>' for v in c["xticks"])
        pts = " ".join(f"{X(x):.1f},{Yp(y):.1f}" for x, y in c["points"])
        dots = "".join(f'<circle class="cd" id="cd{i}" cx="{X(x):.1f}" cy="{Yp(y):.1f}" r="15" fill="{Y}"/>' for i, (x, y) in enumerate(c["points"]))
        calls = "".join(f'<div class="cc" id="cc{i}" style="display:flex;gap:30px;margin-bottom:34px;opacity:0">'
                        f'<div style="width:12px;background:{Y};border-radius:6px"></div>'
                        f'<div><div class="avb" style="font-size:62px;line-height:1.2">{esc(txt)}</div>'
                        f'<div class="av" style="font-size:46px;color:#b8b8b8;margin-top:8px">{esc(src)}</div></div></div>'
                        for i, (txt, src, _) in enumerate(c.get("callouts", [])))
        return (f'<div id="cht" class="din" style="position:absolute;left:40px;top:150px;font-size:130px">{esc(c["title"])}</div>'
                f'<div class="av" style="position:absolute;left:44px;top:300px;font-size:54px;color:#aaa">{esc(c["source"])}</div>'
                f'<svg id="csv" style="position:absolute;left:0;top:420px" width="2820" height="1260" viewBox="0 0 2820 1260">'
                f'{grid}{xl}<polyline id="cl" points="{pts}" fill="none" stroke="{Y}" stroke-width="14" stroke-linejoin="round" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>{dots}'
                f'<text id="cv0" x="{X(xs[0]):.0f}" y="{Yp(ys[0])-50:.0f}" text-anchor="middle" font-family="DINC" font-size="110" fill="#fff">{c["points"][0][1]}{c.get("unit","")}</text>'
                f'<text id="cv1" x="{X(xs[-1])-20:.0f}" y="{Yp(ys[-1])-50:.0f}" text-anchor="end" font-family="DINC" font-size="150" fill="{Y}">{c["points"][-1][1]}{c.get("unit","")}</text></svg>'
                f'<div style="position:absolute;left:330px;top:620px;width:1500px">{calls}</div>')
    raise ValueError(t)


def card_js(ev):
    t, D, js = ev["type"], ev["dur"], []
    if t == "photo":
        if ev.get("title"):
            js.append('tl.fromTo("#pt",{opacity:0,y:20},{opacity:1,y:0,duration:SOFT.dur,ease:SOFT.ease},.05);')
        for i, _ in enumerate(ev["photos"]):
            js.append(f'tl.fromTo("#p{i}",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{0.1+i*0.3:.2f});')
    elif t == "equation":
        rt = ev.get("right_t", D * 0.45)
        js += ['tl.fromTo("#eqL",{opacity:0,scale:.9},{opacity:1,scale:1,duration:POP.dur,ease:POP.ease},.1);',
               'tl.fromTo("#eqM",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.5);',
               f'tl.fromTo("#eqR",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{rt:.3f});']
    elif t == "stat_ratio":
        js += ['tl.fromTo("#sr",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.1);',
               'tl.fromTo("#srs",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.6);']
    elif t == "stat_bars":
        for i, _ in enumerate(ev["bars"]):
            js += [f'tl.fromTo("#bar{i}",{{scaleX:0}},{{scaleX:1,duration:BAR.dur,ease:BAR.ease}},{0.2+i*0.9:.2f});',
                   f'tl.fromTo("#bv{i}",{{opacity:0}},{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{0.6+i*0.9:.2f});']
    elif t == "stat_list":
        for i, _ in enumerate(ev["items"]):
            js.append(f'tl.fromTo("#sl{i}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{0.1+i*0.7:.2f});')
    elif t == "stat_columns":
        for i, tt in enumerate(ev.get("cols_t", [0.1, 1.2])):
            js.append(f'tl.fromTo("#sc{i}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tt:.3f});')
    elif t == "stat_count":
        tt = ev.get("to_t", D * 0.6)
        js += [f'tl.fromTo("#cnt",{{"--n":{ev["from"]}}},{{"--n":{ev["to"]},duration:COUNT.dur,ease:COUNT.ease,snap:{{"--n":1}}}},{tt:.3f});',
               'tl.fromTo("#cnt",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.1);']
    elif t == "stat_equals":
        for i, tt in enumerate(ev.get("rows_t", [0.1, D * 0.5])):
            js.append(f'tl.fromTo("#se{i}",{{opacity:0,y:30}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{tt:.3f});')
    elif t == "proof":
        js.append('tl.fromTo("#pt0",{opacity:0,y:24},{opacity:1,y:0,duration:SOFT.dur,ease:SOFT.ease},0);')
        for i in range(4):
            js.append(f'tl.fromTo("#pr{i}",{{opacity:0,y:40}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{0.35+i*0.35:.2f});')
        js.append(f'tl.fromTo("#grid",{{scale:1}},{{scale:1.04,duration:{max(D-0.5, 1):.2f},ease:"none"}},.4);')
    elif t == "proof_pages":
        p2t = ev.get("page2_t", D * 0.5)
        js.append('tl.fromTo(["#ptt","#tag1"],{opacity:0,y:24},{opacity:1,y:0,duration:SOFT.dur,ease:SOFT.ease},0);')
        for i in range(len(ev["page1"]["tiles"])):
            js.append(f'tl.fromTo("#pa{i}",{{opacity:0,y:60}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{0.3+i*0.22:.2f});')
            js.append(f'tl.to("#pa{i}",{{opacity:0,y:-40,duration:SOFT.dur,ease:SOFT.ease}},{max(p2t-0.35+i*0.05, 0.9):.2f});')
        js.append(f'tl.to("#tag1",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(p2t-0.3, 0.9):.2f});')
        js.append(f'tl.fromTo("#tag2",{{opacity:0}},{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{p2t:.2f});')
        for i in range(len(ev["page2"]["tiles"])):
            js.append(f'tl.fromTo("#pb{i}",{{opacity:0,y:60}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{p2t+0.1+i*0.2:.2f});')
    elif t == "proof_quote":
        js.append('tl.fromTo("#pqt",{opacity:0,y:24},{opacity:1,y:0,duration:SOFT.dur,ease:SOFT.ease},0);')
        js.append('tl.fromTo(".ubar",{scaleX:0},{scaleX:1,duration:SOFT.dur,ease:SOFT.ease},.35);')
        for i in range(len(ev["tiles"])):
            js.append(f'tl.fromTo("#pq{i}",{{opacity:0,y:60}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{0.15+i*0.14:.2f});')
    elif t == "poster":
        js += ['tl.fromTo("#poster",{scale:1},{scale:1.7,duration:%.2f,ease:"none"},.6);' % max(D - 1.2, 1)]
    elif t == "study":
        hl = ev.get("hl_t", 1.1)
        js += ['tl.fromTo("#skk",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.25);',
               'tl.fromTo("#spp",{opacity:0,y:70},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.35);',
               f'tl.fromTo(".mk",{{backgroundSize:"0% 46%"}},{{backgroundSize:"100% 46%",duration:SOFT.dur*1.6,ease:SOFT.ease}},{hl:.3f});']
        if ev["study"].get("stat"):
            js.append(f'tl.fromTo("#sst",{{opacity:0,y:40}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{ev.get("stat_t", hl + 0.6):.3f});')
    elif t == "chart_line":
        n = len(ev["chart"]["points"]); draw = 2.4
        js += ['tl.fromTo("#cht",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);',
               'tl.fromTo("#cv0",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.45);',
               f'tl.fromTo("#cl",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:{draw},ease:"none"}},.5);']
        for i in range(n):  # each point pops as the line reaches it (constant-speed draw)
            js.append(f'tl.fromTo("#cd{i}",{{scale:0,transformOrigin:"50% 50%"}},{{scale:1,duration:POP.dur,ease:POP.ease}},{0.5 + draw * i / max(n - 1, 1):.3f});')
        js.append(f'tl.fromTo("#cv1",{{opacity:0,y:20}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{0.5 + draw:.3f});')
        for i, tt in enumerate(ev.get("callouts_t", [])):
            js.append(f'tl.fromTo("#cc{i}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{tt:.3f});')
    return js


def page(ev, mock):
    b, js = body_for(ev, mock)
    D = ev["dur"]
    return f"""<!doctype html>
<html lang="en" data-resolution="landscape">
<head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="../assets/gsap.min.js"></script>
<style>{CSS}</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{D:.3f}" data-width="{W}" data-height="{H}">
{b}
</div>
<script>
window.__timelines = window.__timelines || {{}};
// Closed-form damped springs (no CSS/stock easing). x(t) solves m x'' + c x' + k x = k.
// Duration = physical settle time (|1-x| < 0.1%), so motion is never time-squashed.
function spring(k, c, m = 1, v0 = 0) {{
  const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m));
  let f, T;
  if (z < 1) {{
    const wd = w0 * Math.sqrt(1 - z * z);
    f = t => 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0 - v0) / wd) * Math.sin(wd * t));
    T = Math.log(1000) / (z * w0);
  }} else {{
    f = t => 1 - Math.exp(-w0 * t) * (1 + (w0 - v0) * t);
    T = 1.6 * Math.log(1000) / w0;
  }}
  return {{ dur: +T.toFixed(3), ease: p => (p >= 1 ? 1 : f(p * T)) }};
}}
const POP = spring(320, 17), SNAP = spring(260, 22), SOFT = spring(170, 26), SLIDE = spring(200, 28),
      BAR = spring(90, 17), COUNT = spring(40, 12.6);

const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body></html>"""


def main():
    events = json.load(open(sys.argv[1]))["events"]
    proj, mock = sys.argv[2], "--mock" in sys.argv
    os.makedirs(f"{proj}/compositions", exist_ok=True)
    for ev in events:
        name = f'{ev["id"]}{".mock" if mock else ""}.html'
        open(f"{proj}/compositions/{name}", "w").write(page(ev, mock))
    print(len(events), "compositions ->", proj, "(mock)" if mock else "")


if __name__ == "__main__":
    main()
