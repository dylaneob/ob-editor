#!/usr/bin/env python3
"""Generate HyperFrames compositions (Dan Go card system) for resolved edit events.

  python3 cards.py EVENTS_RESOLVED.json PROJECT_DIR [--mock]

--mock swaps the A-roll <video> for a still <img> so Puppeteer can screenshot the
exact same layout for the shot-by-shot breakdown. Without --mock the A-roll is
a muted <video> (assets/aroll/<id>.mp4) for the real HyperFrames render.
Canvas 3840x2160. Times inside a composition are relative to the event start.
"""
import html, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bowl_anim   # noqa: E402  (the protein bowl being built: a code-drawn motion graphic)
import motion_cards   # noqa: E402  (belly cross-section, tape, cycle, meal cards; C4365)
import explainer_cards   # noqa: E402  (clip, photo_full, num, math, dose, coins, timeline, title, disclaimer; C4367)
import jh_cards   # noqa: E402  (paper cards for the Johnny-style edit: anchor chart, ledger, stamp; C4372)
import stage
import reel_cards   # noqa: E402  (moving overlays: footage montages, vertical clips beside him; C4395 10-29)
import kinetic_cards   # noqa: E402  (OB_KINETIC=1: the bigger, word-by-word style OB picked on 10-30, C4398/C4402)
KIN = os.environ.get("OB_KINETIC") == "1"
PROJ = None        # hf project dir, set in main(): screenshot cards size each image from its file

Y, R = "#F7DC3A", "#E53935"
CONTAIN = {"extinguisher"}  # tall product shots: show the whole object
W, H = 3840, 2160
# Side layout (replaces the corner PiP, OB 2026-10-16): graphic panel on the left, OB on the right, uncropped.
SIDE_W, SIDE_SHIFT, SIDE_S = 2300, 1150, 0.745
FULL_X = 370   # "full": true side cards (C4367) fill the frame: content at scale 1, centred (the .area spans 140-2960 px of #cin)
SPLIT_W, SPLIT_SHIFT = 1728, 864   # bullet ("split") cards: narrower panel, OB bigger
SIDE_TYPES = {"photo", "equation", "stat_ratio", "stat_bars", "stat_list", "stat_columns", "stat_count", "dotgrid",
              "stat_equals", "proof", "poster", "study", "chart_line", "shots", "bowl"} | set(motion_cards.HTML)
# Overlay slots on OB's own frame (he sits centre, face ~x 1600-2280): nothing drawn around the images.
SLOTS = {
    "portrait4": [(120, 511, 640, 1138), (820, 511, 640, 1138), (2380, 511, 640, 1138), (3080, 511, 640, 1138)],
    "landscape4": [(140, 40, 1180, 1020), (140, 1100, 1180, 1020), (2520, 40, 1180, 1020), (2520, 1100, 1180, 1020)],
    "pair_LR": [(140, 230, 1300, 1700), (2400, 230, 1300, 1700)],
    "pair_sm": [(380, 520, 880, 1100), (2580, 520, 880, 1100)],  # low-res sources (~360 px): about 2.4x at 4K, ~1.2x at 1080p
    "flash": [(160, 260, 1240, 1640), (2440, 260, 1240, 1640)],
    # C4353 framing (handheld mic, head wider: face + cap span about x 1180-2600 at 4K): narrower side slots
    "pair_LRn": [(80, 230, 1060, 1700), (2700, 230, 1060, 1700)],
    "flashn": [(80, 260, 1060, 1640), (2700, 260, 1060, 1640)],
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
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.4 2.7-6 6-6s6 2.6 6 6"/><circle cx="17" cy="9" r="2.6"/><path d="M15.5 14.3c3 .2 5.5 2.5 5.5 5.7"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M7.8 12.3l2.9 2.9 5.6-5.8"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8.5 7V5.2c0-.7.5-1.2 1.2-1.2h4.6c.7 0 1.2.5 1.2 1.2V7M3 12.5h18"/>',
    "leaf": '<path d="M5 19c0-8 5.5-13 15-14-.6 9.6-5.6 15-14 15"/><path d="M5 19l7-7"/>',
    "heart": '<path d="M12 20s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.3a4.3 4.3 0 0 1 7.5 2.6C19.5 15.4 12 20 12 20z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.4 2"/>',
    "bowl": '<path d="M3.5 11h17a8.5 8.5 0 0 1-17 0z"/><path d="M8 20h8M9 7.5c0-1.5 1.5-1.5 1.5-3M13.5 7.5c0-1.5 1.5-1.5 1.5-3"/>',
    "glass": '<path d="M7 3h10l-1 6a4 4 0 0 1-8 0z"/><path d="M12 13v7M8.5 20h7"/>',
    "network": '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 10.9l7.6-3.8M8.2 13.1l7.6 3.8"/>',
    "bolt": '<path d="M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>',
    "eye": '<path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "chat": '<path d="M4 5h16v11H9.5L4 20z"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "scale": '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M7.8 10.5a5.2 5.2 0 0 1 8.4 0"/><path d="M12 10.8l1.7-2.3"/>',
    "ruler": '<path d="M3 15.5L15.5 3 21 8.5 8.5 21z"/><path d="M7 11.5l2 2M9.5 9l1.5 1.5M12 6.5l2 2M14.5 4.2l1.3 1.3"/>',
    "dumbbell": '<path d="M6.5 7v10M17.5 7v10M3.5 9.5v5M20.5 9.5v5M6.5 12h11"/>',
    "fish": '<path d="M3 12c3-4.5 9-6 14-2.5L21 7v10l-4-2.5C12 18 6 16.5 3 12z"/><circle cx="7.5" cy="11" r=".8"/>',
    "note": '<path d="M5 3.5h10l4 4v13H5z"/><path d="M15 3.5V8h4M8 12h8M8 15.5h8"/>',
    "pause": '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7M14 8.5v7"/>',
    "x": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "flag": '<path d="M5.5 21.5V3.5"/><path d="M5.5 4h12.5l-2.6 4.2 2.6 4.3H5.5"/>',
}
# Floating tags around OB's head (Dan Go "Nutrient-Dense / Quick to Make" pills). Order: top-left, top-right, mid-left,
# mid-right, low-left, low-right. (side, edge x, top y): a left pill ends at edge x, a right pill starts there, so both
# keep ~100 px clear of his cap and face in either framing (face x ~1490-2300 at the 120% punch-in).
PILL_SLOTS = [("L", 1380, 290), ("R", 2470, 290), ("L", 1240, 640), ("R", 2610, 640), ("L", 1360, 990), ("R", 2490, 990)]
PILL_COLORS = ["#3B82F6", "#22C55E", "#EF4444", Y, "#A855F7", "#F97316"]

CSS = f"""
@font-face {{ font-family: 'DINC'; src: url('../assets/fonts/DINCondensed-Bold.ttf'); }}
@font-face {{ font-family: 'AvM'; src: url('../assets/fonts/AvenirNext-Medium.ttf'); }}
@font-face {{ font-family: 'AvDB'; src: url('../assets/fonts/AvenirNext-DemiBold.ttf'); }}
@font-face {{ font-family: 'Hand'; src: url('../assets/fonts/BradleyHand-Bold.ttf'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #0c0c0c; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; color: #fff; }}
.bg {{ position: absolute; inset: 0; background: #0c0c0c url('../assets/topo_bg.png') center / cover no-repeat; }}
.din {{ font-family: 'DINC'; }} .av {{ font-family: 'AvM'; }} .avb {{ font-family: 'AvDB'; }} .hand {{ font-family: 'Hand'; }}
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
.pill {{ position: absolute; display: flex; align-items: center; gap: 22px; padding: 22px 42px 22px 32px; background: #fff; color: #111;
         border: 7px solid var(--c); border-radius: 40px; font-family: 'AvDB'; font-size: 72px; line-height: 1; white-space: nowrap;
         box-shadow: 0 0 40px var(--g), 0 16px 44px rgba(0,0,0,.45); opacity: 0; }}
.pill svg {{ width: 66px; height: 66px; flex: none; }}
"""


def esc(s):
    return html.escape(s or "", quote=True)


def aroll(ev, mock, cls="layer"):
    """The A-roll layer: a still for the breakdown mockup, the edited clip for the render."""
    if mock:   # "mock_still": a frame of the A-roll at the moment being shot (C4395 v4_review.py, 10-29: one still per card misled OB)
        return f'<div class="{cls}"><img class="media" src="{ev.get("mock_still") or "../assets/stills/" + ev["id"] + ".jpg"}"/></div>'
    return (f'<div class="{cls}"><video id="aroll" class="media clip" src="../assets/aroll/{ev["id"]}.mp4" muted playsinline '
            f'data-start="0" data-duration="{ev["dur"]:.3f}" data-track-index="0"></video></div>')


def side_in(ev):
    """How a wide-panel card arrives: slides in, keeps the panel the card before left up (chain_in),
    or widens a bullet card's narrower panel into its own (chain_from "split")."""
    if not ev.get("chain_in"):
        return [f'tl.fromTo("#vid",{{x:0}},{{x:{SIDE_SHIFT},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
                f'tl.fromTo("#panel",{{x:-{SIDE_W}}},{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},0);']
    if ev.get("chain_from") == "split":
        return [f'tl.fromTo("#vid",{{x:{SPLIT_SHIFT}}},{{x:{SIDE_SHIFT},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
                f'tl.fromTo("#panel",{{width:{SPLIT_W}}},{{width:{SIDE_W},duration:SLIDE.dur,ease:SLIDE.ease}},0);']
    return [f'tl.set("#vid",{{x:{SIDE_SHIFT},immediateRender:true}},0);', 'tl.set("#panel",{x:0,immediateRender:true},0);']


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
    if KIN and t in kinetic_cards.TYPES and kinetic_cards.handles(ev):
        return kinetic_cards.body(ev, mock, aroll(ev, mock))
    if t in jh_cards.TYPES:   # the stamp sits on his own frame: it needs the A-roll under it (the paper cards cover it)
        b, jl = jh_cards.body(ev, mock)
        if t in jh_cards.COVER and ev.get("beside"):
            # Johnny's board beside his face (1955 vs 2025): the paper card in the left panel, OB slid right, his face on screen
            b = (f'<div class="bg"></div><div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll(ev, mock)}</div>'
                 f'<div id="panel" style="position:absolute;left:0;top:0;width:{SIDE_W}px;height:{H}px;overflow:hidden">{b}'
                 '<div style="position:absolute;right:0;top:0;width:14px;height:100%;background:linear-gradient(90deg,rgba(0,0,0,0),rgba(0,0,0,.35))"></div></div>')
            if ev.get("from_full"):   # the same chart was full frame a cut ago (beside_split.py): the paper pulls back and OB slides in
                jl = [f'tl.fromTo("#panel",{{width:{W}}},{{width:{SIDE_W},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
                      f'tl.fromTo("#vid",{{x:{W}}},{{x:{SIDE_SHIFT},duration:SLIDE.dur,ease:SLIDE.ease}},0);'] + jl
            else:
                jl = side_in(ev) + jl
            if not ev.get("chain_out") and not ev.get("to_full") and D > 1.6:
                jl += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});',
                       f'tl.to("#panel",{{x:-{SIDE_W},duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});']
            return b, jl
        return (b if t in jh_cards.COVER else aroll(ev, mock) + b), jl
    if t in reel_cards.TYPES:   # OB 10-29: every overlay moves (footage montages; vertical clips beside him)
        return reel_cards.body(ev, mock, aroll(ev, mock))
    if t in explainer_cards.TYPES:
        return explainer_cards.body(ev, mock)
    if t == "chapter" and ev.get("style", "v4") == "v4":
        # v4 (OB 10-20 on the breakdown: "these title sections can be improved visually as well and have more movement and animated"):
        # layered and moving. A giant outlined chapter number drifts behind (parallax); PART N slides in behind a drawn rule; the title
        # rises word by word out of a mask, then a light sweep runs across its letters; the underline draws from the centre. The
        # chapter map is a track: the progress line travels from the last part to this one, the node pops and keeps pulsing ("you are
        # here"), finished parts carry a tick. Readable by ~0.7 s; nothing stands still.
        light = stage.WASH.get(ev.get("n", 0), stage.WASH[0])[2]; n = ev.get("n", 1); nchar = len(ev["title"])
        fs = 400 if nchar <= 12 else (330 if nchar <= 20 else 260)
        words = "".join(f'<span class="cwm" style="display:inline-block;overflow:hidden;vertical-align:top;padding:0 .08em;margin:0 -.04em">'
                        f'<span class="cwi" style="display:inline-block">{esc(w)}</span></span> ' for w in ev["title"].split())
        ty = 1000 - fs // 2
        b = (f'<div class="bg"></div>'
             f'<div id="cbig" class="din" style="position:absolute;right:120px;top:{1080 - 820}px;font-size:1640px;line-height:1;color:transparent;'
             f'-webkit-text-stroke:7px {light};opacity:0;letter-spacing:-20px{";display:none" if ev.get("nobig") else ""}">{n:02d}</div>'
             f'<div id="cw" style="position:absolute;left:0;top:0;width:3840px;height:2160px;transform-origin:50% 46%">'
             f'<div id="ckw" class="center" style="top:{ty - 230}px;display:flex;justify-content:center;align-items:center;gap:40px">'
             f'<div id="ckl" style="width:170px;height:8px;border-radius:4px;background:{light};transform-origin:100% 50%"></div>'
             f'<div id="ck" class="avb" style="font-size:96px;letter-spacing:22px;color:{light}">{esc(ev.get("kicker", f"PART {n}"))}</div>'
             f'<div id="ckr" style="width:170px;height:8px;border-radius:4px;background:{light};transform-origin:0% 50%"></div></div>'
             f'<div id="title" class="center din" style="top:{ty}px;font-size:{fs}px;line-height:1.02;text-shadow:0 14px 60px rgba(0,0,0,.55)">{words}</div>'
             f'<div id="tsh" class="center din" aria-hidden="true" style="top:{ty}px;font-size:{fs}px;line-height:1.02;color:transparent;'
             f'background-image:linear-gradient(105deg,rgba(0,0,0,0) 42%,{light} 50%,rgba(0,0,0,0) 58%);background-size:300% 100%;'
             f'background-position:100% 0;-webkit-background-clip:text;background-clip:text;pointer-events:none">{esc(ev["title"])}</div>'
             f'<div id="cl" style="position:absolute;left:{W // 2 - 560}px;top:{ty + int(fs * 1.02) + 60}px;width:1120px;height:12px;border-radius:6px;background:{light}"></div>')
        js += [f'tl.fromTo("#cbig",{{opacity:0,x:260}},{{opacity:.2,x:120,duration:.7,ease:"power2.out"}},0);',
               f'tl.to("#cbig",{{x:-140,duration:{max(D - 0.7, 0.5):.3f},ease:"none"}},.7);',
               'tl.fromTo("#ck",{opacity:.35,letterSpacing:"46px"},{opacity:1,letterSpacing:"22px",duration:SOFT.dur,ease:SOFT.ease},0);',
               'tl.fromTo(["#ckl","#ckr"],{scaleX:0},{scaleX:1,duration:.5,ease:"power3.out"},.05);',
               'tl.fromTo("#title .cwi",{yPercent:62},{yPercent:0,duration:.55,ease:"power4.out",stagger:.06},0);',
               'tl.fromTo("#cl",{scaleX:0},{scaleX:1,duration:SOFT.dur,ease:SOFT.ease},.32);',
               f'tl.fromTo("#tsh",{{backgroundPosition:"100% 0"}},{{backgroundPosition:"0% 0",duration:.85,ease:"power1.inOut"}},{min(0.78, max(D - 1.0, 0.3)):.3f});']
        if ev.get("map"):
            M = ev["map"]; k_ = len(M); x0m, x1m, my = 500, W - 500, 1760; step = (x1m - x0m) / max(k_ - 1, 1)
            X = lambda i: x0m + i * step
            prev, cur = X(max(n - 2, 0)), X(n - 1)
            b += (f'<div id="cmap" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;opacity:0">'
                  f'<div style="position:absolute;left:{x0m}px;top:{my - 7}px;width:{x1m - x0m}px;height:14px;border-radius:7px;background:rgba(255,255,255,.22)"></div>'
                  f'<div id="cfill" style="position:absolute;left:{x0m}px;top:{my - 7}px;width:{cur - x0m:.0f}px;height:14px;border-radius:7px;background:{light};'
                  f'transform-origin:0 50%"></div>')
            for i, c in enumerate(M):
                done, here = i + 1 < n, i + 1 == n
                hereF = "#ffffff" if n in (1, 5) else Y   # on the amber and gold chapters a yellow node would melt into the finished ones
                fill = light if done else (hereF if here else "rgba(0,0,0,.55)")
                ring = Y if here else (light if done else "rgba(255,255,255,.55)")
                fut = '' if (done or here) else 'filter:blur(5px);opacity:.45;'
                b += (f'<div id="cn{i}" style="position:absolute;left:{X(i) - 62:.0f}px;top:{my - 62}px;width:124px;height:124px;border-radius:62px;background:{fill};'
                      f'border:8px solid {ring};box-sizing:border-box;{fut}display:flex;align-items:center;justify-content:center;'
                      f'font-family:DINC;font-size:74px;color:{"#111" if (done or here) else "#fff"}">{"✓" if done else i + 1}</div>'
                      f'<div class="avb" style="position:absolute;left:{X(i) - 360:.0f}px;width:740px;top:{my + 92}px;text-align:center;text-wrap:balance;'
                      f'font-size:{74 if here else 60}px;line-height:1.15;{fut}color:{Y if here else ("#f2f2f2" if done else "rgba(255,255,255,.62)")}">{esc(c)}</div>')
            b += (f'<div id="cring" style="position:absolute;left:{cur - 62:.0f}px;top:{my - 62}px;width:124px;height:124px;border-radius:62px;'
                  f'border:8px solid {Y};box-sizing:border-box;opacity:0"></div></div>')
            js += ['tl.fromTo("#cmap",{opacity:.3,y:40},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
                   f'tl.fromTo("#cfill",{{scaleX:{(prev - x0m) / max(cur - x0m, 1):.4f}}},{{scaleX:1,duration:.55,ease:"power2.inOut"}},.3);' if n > 1 else
                   'tl.fromTo("#cfill",{scaleX:0},{scaleX:1,duration:.4,ease:"power2.out"},.3);',
                   f'tl.fromTo("#cn{n - 1}",{{scale:.55}},{{scale:1.18,duration:.25,ease:"power2.out"}},.82);',
                   f'tl.to("#cn{n - 1}",{{scale:1,duration:.3,ease:"power2.inOut"}},1.07);',
                   f'tl.fromTo("#cring",{{scale:1,opacity:.85}},{{scale:2.3,opacity:0,duration:.85,ease:"power1.out",repeat:{max(1, int((D - 0.9) / 0.85))}}},.9);']
        b += "</div>"
    elif t == "chapter":   # v3 (OB 10-20): a chapter title that fills the frame on its chapter's colour, not a small tile on black
        light = stage.WASH.get(ev.get("n", 0), stage.WASH[0])[2]; ttl = esc(ev["title"]); nchar = len(ev["title"])
        fs = 430 if nchar <= 12 else (340 if nchar <= 20 else 270)
        b = f"""<div class="bg"></div><div id="cw" style="position:absolute;left:0;top:0;width:3840px;height:2160px;transform-origin:50% 50%">
<div id="ck" class="center avb" style="top:{1080 - fs // 2 - 230}px;font-size:96px;letter-spacing:22px;color:{light}">PART {ev['n']}</div>
<div id="title" class="center din" style="top:{1080 - fs // 2}px;font-size:{fs}px;line-height:1;text-shadow:0 14px 60px rgba(0,0,0,.55)">{ttl}</div>
<div id="cl" style="position:absolute;left:{W // 2 - 520}px;top:{1080 + fs // 2 + 70}px;width:1040px;height:12px;border-radius:6px;background:{light}"></div>"""
        if ev.get("map"):   # the chapter map from the roadmap (reshoot, OB 10-20): every part in a row, this one lit ("you are here")
            chips = "".join(f'<div id="cm{k}" style="display:flex;align-items:center;gap:24px;padding:22px 40px;border-radius:24px;white-space:nowrap;'
                            f'background:{"rgba(0,0,0,.72)" if k + 1 != ev["n"] else Y};border:4px solid {Y if k + 1 != ev["n"] else Y};'
                            f'color:{"#fff" if k + 1 != ev["n"] else "#111"};opacity:{1 if k + 1 == ev["n"] else (.82 if k + 1 < ev["n"] else .5)}">'
                            f'<span class="din" style="font-size:100px;line-height:1">{k + 1}</span><span class="avb" style="font-size:68px">{esc(c)}</span>'
                            + (f'<span class="avb" style="font-size:54px;margin-left:6px;opacity:.75">\u2713</span>' if k + 1 < ev["n"] else "") + '</div>'
                            for k, c in enumerate(ev["map"]))
            b += f'<div id="cmap" style="position:absolute;left:0;top:1770px;width:{W}px;display:flex;justify-content:center;gap:30px">{chips}</div>'
            js += [f'tl.fromTo("#cmap",{{y:60,opacity:0}},{{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease}},.12);',
                   f'tl.fromTo("#cm{ev["n"] - 1}",{{scale:.8}},{{scale:1.08,duration:POP.dur,ease:POP.ease}},.35);']
        b += "</div>"
        js += ['tl.fromTo("#ck",{opacity:0,letterSpacing:"40px"},{opacity:1,letterSpacing:"22px",duration:SOFT.dur,ease:SOFT.ease},0);',
               'tl.fromTo("#title",{y:70,opacity:0},{y:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease},.08);',
               'tl.fromTo("#cl",{scaleX:0},{scaleX:1,duration:SOFT.dur,ease:SOFT.ease},.3);']
    elif t == "quote":   # v4 (OB 10-20: "boring slides that stay there for 5 seconds"): each line lands as he says it (at l1, l2...),
        # sized by its longest line to fill the frame; lines not yet said keep their space, so nothing reflows
        lines = ev["text"].split("\n"); n = len(lines); L = max(len(x) for x in lines)
        fs = int(min(10300 / max(L, 1), 1560 / (1.1 * n), 460))
        at = ev.get("at_t") or {}; ts, last = [], -1.0
        for k in range(n):
            r = 0.0 if k == 0 else at.get(f"l{k}")
            if r is None or (k and r < last + 0.25): r = last + max(0.45, min(0.9, (D - 1.2) / n))
            ts.append(round(min(r, max(D - 0.6, 0.0)), 3)); last = ts[-1]
        rows = "".join(f'<div id="ql{k}" style="opacity:0;transform-origin:50% 60%">{underline(x, ev.get("underline"))}</div>' for k, x in enumerate(lines))
        b = f"""<div class="bg"></div><div id="cw" style="position:absolute;left:0;top:0;width:3840px;height:2160px;transform-origin:50% 50%">
<div id="qy" style="position:absolute;inset:0"><div id="q" class="din" style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:3500px;text-align:center;font-size:{fs}px;line-height:1.1;white-space:nowrap;text-shadow:0 12px 50px rgba(0,0,0,.5)">{rows}</div></div></div>"""
        js += [f'tl.fromTo("#ql{k}",{{opacity:0,y:50,scale:.94}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{tk:.3f});' for k, tk in enumerate(ts)]
        lh = fs * 1.1   # the lines said so far stay centred: the block eases up as each new line arrives
        if n > 1:
            js.append(f'tl.set("#qy",{{y:{(n - 1) / 2 * lh:.1f}}},0);')
            js += [f'tl.to("#qy",{{y:{(n - 1 - k) / 2 * lh:.1f},duration:.45,ease:"power3.inOut"}},{max(0.0, ts[k] - 0.05):.3f});' for k in range(1, n)]
        kU = next((k for k, x in enumerate(lines) if ev.get("underline") and ev["underline"] in x), None)
        if kU is not None: js.append(f'tl.fromTo("#ql{kU} .ubar",{{scaleX:0}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{ts[kU] + 0.4:.3f});')
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
        # items: [text, anchor] or [text, anchor, source]: a sourced bullet carries its study in small grey type under it
        def src_line(it):
            return f'<div class="av" style="font-size:54px;line-height:1.2;color:#9a9a9a;margin-top:12px">{esc(it[2])}</div>' if len(it) > 2 and it[2] else ""
        items = "".join(f'<li id="b{i}" style="margin-bottom:{50 if len(ev["items"]) > 5 else 62}px;list-style:none;display:flex;gap:34px"><span style="color:{"#B3261E" if ev.get("paper") else Y}">&bull;</span>'
                        f'<span>{esc(it[0])}{src_line(it)}</span></li>' for i, it in enumerate(ev["items"]))
        n = len(ev["items"]); block_h = 200 + n * 172 + 76 * sum(1 for it in ev["items"] if len(it) > 2 and it[2])
        top = max(380 if "day" not in ev else 330, 1080 - block_h // 2)
        # transforms only (no left/width): the video slides right, the text panel slides in from the left
        b = f"""<div class="bg"></div>
<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll(ev, mock)}</div>
<div id="panel" style="position:absolute;left:0;top:0;width:1728px;height:{H}px;overflow:hidden">
  {'<img src="../assets/paper.jpg" style="position:absolute;left:0;top:0;width:3840px;height:2160px;object-fit:cover"><div style="position:absolute;right:0;top:0;width:14px;height:100%;background:linear-gradient(90deg,rgba(0,0,0,0),rgba(0,0,0,.35))"></div>' if ev.get("paper") else '<div class="bg"></div>'}
  <div id="st" class="din" style="position:absolute;left:190px;top:{top}px;width:1480px;font-size:138px;{'color:#1f1b16' if ev.get('paper') else ''}">{esc(ev.get('title',''))}</div>
  <ul id="ul" class="av" style="position:absolute;left:196px;top:{top+230}px;width:1480px;font-size:92px;line-height:1.16;{'color:#1f1b16' if ev.get('paper') else ''}">{items}</ul>
  {motion_cards.day_tracker(ev["day"], SPLIT_W) if "day" in ev else ""}</div>"""
        if ev.get("chain_in"):   # the card before kept the panel up: only the content changes (a wide card's panel narrows to this one)
            js += ([f'tl.fromTo("#vid",{{x:{SIDE_SHIFT}}},{{x:{SPLIT_SHIFT},duration:SLIDE.dur,ease:SLIDE.ease}},0);',
                    f'tl.fromTo("#panel",{{width:{SIDE_W}}},{{width:{SPLIT_W},duration:SLIDE.dur,ease:SLIDE.ease}},0);']
                   if ev.get("chain_from") == "side" else
                   [f'tl.set("#vid",{{x:{SPLIT_SHIFT},immediateRender:true}},0);', 'tl.set("#panel",{x:0,immediateRender:true},0);'])
            js.append('tl.fromTo("#st",{opacity:0,x:-30},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.15);')
        else:
            js += ['tl.fromTo("#vid",{x:0},{x:864,duration:SLIDE.dur,ease:SLIDE.ease},0);',
                   'tl.fromTo("#panel",{x:-1728},{x:0,duration:SLIDE.dur,ease:SLIDE.ease},0);',
                   'tl.fromTo("#st",{opacity:0,x:-30},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.3);']
        for i, it in enumerate(ev["items_t"]):
            js.append(f'tl.fromTo("#b{i}",{{opacity:0,x:-36}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{max(it, 0.45):.3f});')
        if ev.get("chain_out"):  # next card takes over the panel: fade the bullets instead of sliding away
            js.append(f'tl.to("#st, #ul",{{opacity:0,duration:.25,ease:"none"}},{max(D-0.28, 0.5):.3f});')
        elif D > 1.6:
            js += [f'tl.to("#vid",{{x:0,duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});',
                   f'tl.to("#panel",{{x:-1728,duration:SLIDE.dur,ease:SLIDE.ease}},{D-0.52:.3f});']
    elif t == "label":
        b = f"""{aroll(ev, mock)}
<div style="position:absolute;left:0;top:{max(0, ev.get('ly', 120) - 120)}px;width:2000px;height:700px;background:radial-gradient(ellipse at 0% {'0%' if ev.get('ly', 120) < 600 else '60%'},rgba(0,0,0,.55),rgba(0,0,0,0) 70%)"></div>
<div id="lb" style="position:absolute;left:170px;top:{ev.get('ly', 120)}px">
  <div style="width:130px;height:10px;background:{Y};margin-bottom:34px"></div>
  <div class="din" style="font-size:118px;line-height:1">{esc(ev.get('title',''))}</div>
  <div class="avb" style="font-size:64px;color:#e8e8e8;margin-top:18px">{esc(ev.get('sub',''))}</div></div>"""
        js += ['tl.fromTo("#lb",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},0);',
               f'tl.to("#lb",{{opacity:0,duration:SOFT.dur,ease:SOFT.ease}},{max(D-0.3, 0.5):.3f});']
    elif t in SIDE_TYPES:
        inner, extra = card_area(ev), card_js(ev)
        if ev.get("source"):   # where a number on the card comes from, in small grey type at the foot of the panel
            inner += f'<div class="av" style="position:absolute;left:40px;top:1985px;width:2740px;font-size:52px;line-height:1.25;color:#8f8f8f">{esc(ev["source"])}</div>'
        day = motion_cards.day_tracker(ev["day"], SIDE_W) if "day" in ev else ""   # outside #cin: stays put when a chained card swaps content
        if ev.get("full") and ev.get("face"):
            # C4395 10-29 (OB: "its a little too long on the overlays when its the full screen you can come back to me a little more"):
            # full frame over his look-downs, and in each ev["face"] window (eyes on the lens) the panel pulls back to the side and he
            # slides in, then it fills the frame again before the next look-down
            b = f"""<div class="bg"></div>
<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform:translateX({SIDE_SHIFT}px)">{aroll(ev, mock)}</div>
<div id="panel" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;overflow:hidden">
  <div class="bg"></div>
  <div id="cin" style="position:absolute;left:{FULL_X}px;top:0;width:{W}px;height:{H}px;transform-origin:0 50%"><div class="area">{inner}</div></div>{day}</div>"""
            js += ([] if ev.get("chain_in") else ['tl.fromTo("#cin",{x:-70},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);']) + extra
            for t0, t1 in ev["face"]:
                back = max(t0 + 0.6, t1 - 0.55)
                js += [f'tl.to("#panel",{{width:{SIDE_W},duration:SLIDE.dur,ease:SLIDE.ease}},{t0:.3f});',
                       f'tl.to("#cin",{{left:0,scale:{SIDE_S},duration:SLIDE.dur,ease:SLIDE.ease}},{t0:.3f});']
                if t1 < D - 0.1:
                    js += [f'tl.to("#panel",{{width:{W},duration:.5,ease:SLIDE.ease}},{back:.3f});',
                           f'tl.to("#cin",{{left:{FULL_X},scale:1,duration:.5,ease:SLIDE.ease}},{back:.3f});']
            return b, js
        if ev.get("full"):   # C4367: the card fills the frame, covering a moment where OB reads off the script; no A-roll under it
            b = f"""<div class="bg"></div>
<div id="panel" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;overflow:hidden">
  <div id="cin" style="position:absolute;left:{FULL_X}px;top:0;width:{W}px;height:{H}px"><div class="area">{inner}</div></div></div>"""
            js += ([] if ev.get("chain_in") else ['tl.fromTo("#cin",{x:-70},{x:0,duration:SNAP.dur,ease:SNAP.ease},0);']) + extra
            return b, js
        b = f"""<div class="bg"></div>
<div id="vid" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px">{aroll(ev, mock)}</div>
<div id="panel" style="position:absolute;left:0;top:0;width:{SIDE_W}px;height:{H}px;overflow:hidden">
  <div class="bg"></div>
  <div id="cin" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform:scale({SIDE_S});transform-origin:0 50%"><div class="area">{inner}</div></div>{day}</div>"""
        js += side_in(ev) + extra
        if ev.get("chain_out"):  # next card takes over the panel: fade this content out instead of sliding away
            js.append(f'tl.to("#cin",{{opacity:0,duration:.25,ease:"none"}},{max(D-0.28, 0.5):.3f});')
        elif D > 1.6:
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
        js += side_in(ev)
        js.append('tl.fromTo("#eb",{opacity:0,x:-40},{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease},.3);')
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
        slots = ev.get("slots_xywh") or SLOTS[ev["layout"]]; imgs = []; last_in_slot = {}   # C4423 11-05: per-event slots fitted to his head zone
        times = ev["items_t"]
        for i, (key, si, _) in enumerate(ev["items"]):
            x, y, w, h = slots[si]
            imgs.append(f'<img class="ov" id="o{i}" src="../assets/{ev.get("folder","proof")}/{key}.jpg" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;opacity:0"/>')
            # hard cuts, no crossfades (a fade-in under the outgoing image ghosts into a double exposure):
            # the old image in this slot vanishes and the new one snaps on in the same frame, with a spring punch
            if si in last_in_slot:
                js.append(f'tl.set("#o{last_in_slot[si]}",{{opacity:0}},{times[i]:.3f});')
            js.append(f'tl.set("#o{i}",{{opacity:1}},{times[i]:.3f});')
            if os.environ.get("OB_NO_PUSH") == "1":   # 2026-11-11 C4465 (R18, OB 11-07): no scale pop on stills; a short rise instead
                if ev.get("items_enter", "slide") == "slide" and not (si in last_in_slot):
                    js.append(f'tl.fromTo("#o{i}",{{y:46}},{{y:0,duration:SOFT.dur,ease:SOFT.ease}},{times[i]:.3f});')
            else:
                js.append(f'tl.fromTo("#o{i}",{{scale:1.07}},{{scale:1,duration:SNAP.dur,ease:SNAP.ease}},{times[i]:.3f});')
            nxt = [times[j] for j in range(i + 1, len(times)) if ev["items"][j][1] == si]
            hold = (nxt[0] if nxt else D - 0.27) - times[i]
            if hold >= 3.0 and os.environ.get("OB_NO_PUSH") != "1":  # long hold: slow constant drift (off under OB_NO_PUSH: OB 11-07 no pushes on stills)
                js.append(f'tl.to("#o{i}",{{scale:1.04,duration:{hold:.3f}-SNAP.dur,ease:"none"}},{times[i]:.3f}+SNAP.dur);')
            last_in_slot[si] = i
        ar = aroll(ev, mock)
        if ev.get("full") and ev.get("ob_pip"):   # 2026-11-11 C4465 (M87): a cover over a look-down: his frame blurred behind, him sharp in the box
            ar = f'<div style="position:absolute;inset:0;filter:blur(34px) brightness(.62) saturate(1.1);transform:scale(1.06)">{ar}</div>'
        b = f'{ar}{"".join(imgs)}'
        if ev.get("foot"):  # landscape4's bottom-left slot reaches y=2120, so its footnote sits centred in the gap under OB
            pos = "left:1920px;transform:translateX(-50%)" if ev["layout"] == "landscape4" else "left:60px"
            b += f'<div class="av" style="position:absolute;{pos};top:2080px;font-size:40px;color:rgba(255,255,255,.75);text-shadow:0 2px 10px rgba(0,0,0,.8);white-space:nowrap">{esc(ev["foot"])}</div>'
        if ev.get("label"):   # 2026-11-11: the brand face (Big Shoulders Display Black) when the kinetic CSS is on the page; label_t lands it on his word
            b += (f'<div id="lb" style="position:absolute;left:{ev.get("label_x", 170)}px;top:{ev.get("label_y", 90)}px;opacity:0"><div class="{"bsd" if KIN else "din"}" style="font-size:{ev.get("label_px", 110)}px;line-height:1;'
                  f'text-shadow:0 4px 24px rgba(0,0,0,.7)">{esc(ev["label"])}</div></div>')
            js.append(f'tl.fromTo("#lb",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{float(ev.get("label_t", 0)):.3f});')
        if D > 1.0 and not ev.get("keep_end"):  # everything clears at the end (no hard pop-off); keep_end: the next card carries the same picture on
            js.append(f'tl.to(".ov:not(.pic)",{{opacity:0,duration:.25,ease:"none"}},{D-0.27:.3f});')
    elif t == "pills":
        # items: [text, anchor, icon]; each tag springs out from the side facing OB, then drifts up slowly (no frozen frames)
        slots = ev.get("slots") or PILL_SLOTS
        tags = []
        for i, it in enumerate(ev["items"]):
            side, ex, y = slots[i % len(slots)]
            c = PILL_COLORS[i % len(PILL_COLORS)]
            pos = f"right:{W - ex}px" if side == "L" else f"left:{ex}px"
            icon = ICONS.get(it[2] if len(it) > 2 else "", ICONS["check"])
            tags.append(f'<div class="pill" id="pl{i}" style="{pos};top:{y}px;--c:{c};--g:{c}66;transform-origin:{"100%" if side == "L" else "0%"} 50%">'
                        f'<svg viewBox="0 0 24 24" fill="none" stroke="#111" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{icon}</svg>'
                        f'<span>{esc(it[0])}</span></div>')
            ti = ev["items_t"][i]
            js += [f'tl.fromTo("#pl{i}",{{opacity:0,scale:.55}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{ti:.3f});',
                   f'tl.fromTo("#pl{i}",{{y:0}},{{y:-18,duration:{max(D - ti, 0.5):.3f},ease:"none"}},{ti:.3f});']
        b = f'{aroll(ev, mock)}{"".join(tags)}'
        if ev.get("photo"):   # v3 (OB 10-20: "add a photo of David in the opening next to my face"): a polaroid beside him
            ph = ev["photo"]; x, y, w = ph.get("x", 2620), ph.get("y", 470), ph.get("w", 900); tp = (ev.get("at_t") or {}).get("photo", 0.6)
            b += (f'<div id="pol" style="position:absolute;left:{x}px;top:{y}px;width:{w + 48}px;padding:24px 24px 0;background:#fbfaf7;border-radius:10px;'
                  f'box-shadow:0 40px 110px rgba(0,0,0,.55);transform-origin:50% 0%;opacity:0"><img src="../assets/{ph["src"]}" style="display:block;width:{w}px;height:{w}px;object-fit:cover"/>'
                  f'<div class="din" style="height:150px;display:flex;align-items:center;justify-content:center;font-size:96px;color:#1b1b1b">{esc(ph.get("caption", ""))}</div></div>')
            js += [f'tl.fromTo("#pol",{{opacity:0,scale:.6,rotation:12,y:60}},{{opacity:1,scale:1,rotation:ph_rot,y:0,duration:POP.dur,ease:POP.ease}},{tp:.3f});'.replace("ph_rot", str(ph.get("rot", 4))),
                   f'tl.to("#pol",{{y:-26,rotation:{ph.get("rot", 4) - 1.5},duration:{max(D - tp - 0.6, 0.6):.3f},ease:"sine.inOut"}},{tp + 0.5:.3f});']
            if D > 1.0: js.append(f'tl.to("#pol",{{opacity:0,duration:.25,ease:"none"}},{D - 0.27:.3f});')
        if D > 1.0:
            js.append(f'tl.to(".pill",{{opacity:0,duration:.25,ease:"none"}},{D-0.27:.3f});')
    elif t == "plate":
        # OB 10-20: "you can overlay text from me on screen talking sometimes as well, like johnny harris" + "learn any of the animations
        # from the upgrade we did today" (motion library §E, Payton Kaleiwahea's reel): his words as caption plates over his own shot,
        # 2-4 words a beat, condensed caps on a black plate with a thin white outline, ONE word in yellow. ev["chunks"]: [[text, at-key,
        # yellow word or ""], ...]; at-keys resolve to seconds in ev["at_t"]. Each plate holds until the next lands; the last to the end.
        at = ev.get("at_t") or {}; ch = ev["chunks"]; ts, last = [], -1.0
        for k, c in enumerate(ch):
            r = at.get(c[1], 0.05 if k == 0 else last + 0.7)
            if k == 0: r = min(r, 0.05)
            if k and r < last + 0.3: r = last + 0.3
            ts.append(round(min(r, max(D - 0.35, 0.0)), 3)); last = ts[-1]
        def plate_html(txt, yw):
            out = []
            for w_ in txt.split():
                core = w_.strip(".,!?;:\u201c\u201d\"'").lower()
                out.append(f'<span style="color:{Y}">{esc(w_)}</span>' if yw and core == yw.lower() else esc(w_))
            return " ".join(out)
        b = aroll(ev, mock)
        for k, (txt, key, yw) in enumerate(ch):
            b += (f'<div id="pl{k}" style="position:absolute;left:0;top:{ev.get("y", 1640)}px;width:{W}px;text-align:center;opacity:0">'
                  f'<span class="din" style="display:inline-block;font-size:{ev.get("size", 176)}px;line-height:1;text-transform:uppercase;letter-spacing:2px;'
                  f'background:#000;color:#fff;padding:24px 50px 16px;border:6px solid #fff;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.55)">'
                  f'{plate_html(txt, yw)}</span></div>')
        for k, tk in enumerate(ts):
            js.append(f'tl.fromTo("#pl{k}",{{opacity:0,scale:.9,y:24}},{{opacity:1,scale:1,y:0,duration:.22,ease:"back.out(2)"}},{tk:.3f});')
            if k + 1 < len(ts): js.append(f'tl.set("#pl{k}",{{opacity:0}},{ts[k + 1]:.3f});')
            elif D - tk > 0.6: js.append(f'tl.to("#pl{k}",{{opacity:0,duration:.18,ease:"none"}},{D - 0.2:.3f});')
    elif t == "selfquote":
        # OB's own line as a title on his frame, on the side away from his face (Johnny Harris's "I HAVE CHILDREN"), signed OB.
        side = ev.get("side", "L"); n = len(ev["text"]); fs = 300 if n <= 14 else (240 if n <= 30 else 200)   # v4: bigger (OB: "nothing small")
        shade = "90deg" if side == "L" else "270deg"
        tq = (ev.get("at_t") or {}).get("q", 0.1)
        b = (f'{aroll(ev, mock)}<div style="position:absolute;{"left" if side == "L" else "right"}:0;top:0;width:1800px;height:{H}px;'
             f'background:linear-gradient({shade},rgba(0,0,0,.62),rgba(0,0,0,.3) 62%,rgba(0,0,0,0))"></div>'
             f'<div id="sq" style="position:absolute;{"left" if side == "L" else "right"}:150px;top:{ev.get("y", 700)}px;width:1280px;text-align:{"left" if side == "L" else "right"}">'
             + (f'<div class="din" style="font-size:{fs}px;line-height:.98;text-wrap:balance;text-shadow:0 8px 40px rgba(0,0,0,.7)">\u201c{esc(ev["text"])}\u201d</div>'
                f'<div style="display:flex;align-items:center;gap:22px;margin-top:34px;{"justify-content:flex-end" if side == "R" else ""}">'
                f'<div style="width:90px;height:10px;background:{Y}"></div><div class="avb" style="font-size:60px;color:{Y};letter-spacing:5px">OB</div></div></div>'
                if not ev.get("plain") else   # "plain": a title on his shot (a name, a term), no quote marks, no signature (C4367 reshoot)
                (f'<div class="avb" style="font-size:70px;color:{Y};letter-spacing:6px;margin-bottom:26px">{esc(ev.get("kicker", ""))}</div>' if ev.get("kicker") else "")
                + "".join(f'<div class="din" style="font-size:{ev.get("size", 230)}px;line-height:1;text-shadow:0 8px 40px rgba(0,0,0,.7)">{esc(x)}</div>' for x in ev["text"].split("\n"))
                + '</div>'))
        js += [f'tl.fromTo("#sq",{{opacity:0,y:30,scale:.96}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{tq:.3f});']
        if D > 1.0: js.append(f'tl.to("#sq",{{opacity:0,duration:.25,ease:"none"}},{D-0.27:.3f});')
    elif t == "facequote":
        # OB 10-20 on the v6 previews: "show me more than these boring ass text overlay slides... showing my face more and just putting
        # text as the overlay on those shots anyways, just the text ones, i love the animations and slides that have movement". A quote
        # card's lines over his own shot, beside his face: each line lands as he says it (at l0, l1...), the key phrase gets the red
        # underline, an optional yellow kicker sits on top, and the block drifts up slowly so nothing holds still. Never over a look-down
        # (the project's make_spec puts those under footage or under the card before).
        lines = ev["text"].split("\n"); n = len(lines); side = ev.get("side", "L"); bw = ev.get("w", 1300)
        at = ev.get("at_t") or {}; ts, last = [], -1.0
        for k in range(n):
            r = at.get(f"l{k}", 0.0 if k == 0 else None)
            if r is None or (k and r < last + 0.25): r = last + max(0.4, min(0.8, (D - 0.8) / n))
            ts.append(round(min(max(r, 0.0), max(D - 0.5, 0.0)), 3)); last = ts[-1]
        L = max(len(x) for x in lines); ul = ev.get("underline") or ""
        unit = max([len(w) for x in lines for w in x.split()] + [len(ul)])   # an underlined phrase never wraps (.u is inline-block)
        CW = 0.33   # DIN Condensed Bold, average width of a character in em (mock 10-20: 28 characters at 130 px ran 1120 px)
        fs = ev.get("size") or int(min(250 if L <= 16 else 220 if L <= 26 else 195, 0.9 * bw / (CW * max(unit, 1))))   # big, like the self-quotes; an underlined phrase keeps a 10% margin so it never breaks at a hyphen
        kick = ev.get("kicker")
        vis = lambda f: sum(max(1, -(-int(len(x) * CW * f) // bw)) for x in lines)   # wrapped lines, estimated
        bh = vis(fs) * fs * 1.04 + (96 if kick else 0)
        if bh > 1480: fs = int(fs * 1480 / bh); bh = vis(fs) * fs * 1.04 + (96 if kick else 0)
        top = int(max(200, min(ev.get("y", 1000) - bh / 2, H - 240 - bh)))
        shade = "90deg" if side == "L" else "270deg"
        rows = "".join(f'<div id="fq{k}" class="din" style="font-size:{fs}px;line-height:1.04;text-wrap:balance;opacity:0;'
                       f'text-shadow:0 8px 40px rgba(0,0,0,.75),0 0 6px rgba(0,0,0,.35)">{underline(x, ul)}</div>' for k, x in enumerate(lines))
        b = (f'{aroll(ev, mock)}<div id="fqs" style="position:absolute;{"left" if side == "L" else "right"}:0;top:0;width:1900px;height:{H}px;opacity:0;'
             f'background:linear-gradient({shade},rgba(0,0,0,.66),rgba(0,0,0,.34) 58%,rgba(0,0,0,0))"></div>'
             f'<div id="fqb" style="position:absolute;{"left" if side == "L" else "right"}:150px;top:{top}px;width:{bw}px;text-align:{"left" if side == "L" else "right"}">'
             + (f'<div id="fqk" class="avb" style="font-size:68px;color:{Y};letter-spacing:6px;margin-bottom:26px;opacity:0;text-shadow:0 4px 24px rgba(0,0,0,.6)">{esc(kick)}</div>' if kick else "")
             + rows + '</div>')
        js += ['tl.fromTo("#fqs",{opacity:0},{opacity:1,duration:.22,ease:"none"},0);',
               f'tl.fromTo("#fqb",{{y:0}},{{y:-26,duration:{max(D, 0.5):.3f},ease:"none"}},0);']
        if kick: js.append(f'tl.fromTo("#fqk",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{min(0.05, ts[0]):.3f});')
        js += [f'tl.fromTo("#fq{k}",{{opacity:0,y:44,scale:.95}},{{opacity:1,y:0,scale:1,duration:POP.dur,ease:POP.ease}},{tk:.3f});' for k, tk in enumerate(ts)]
        kU = next((k for k, x in enumerate(lines) if ul and esc(ul) in esc(x)), None)
        if kU is not None: js.append(f'tl.fromTo("#fq{kU} .ubar",{{scaleX:0}},{{scaleX:1,duration:SOFT.dur,ease:SOFT.ease}},{min(ts[kU] + 0.35, max(D - 0.4, 0)):.3f});')
        if D > 1.0: js.append(f'tl.to(["#fqb","#fqs"],{{opacity:0,duration:.22,ease:"none"}},{D - 0.24:.3f});')
    elif t == "doc" and ev.get("page"):
        # C4367 v9 (OB 10-20: "any screenshots from the studies and highlights we can do as well to have more credibility"): the REAL
        # page (the court filing, the FDA-hosted notice), rendered from the PDF, large on the frame with a slight tilt; a slow push toward
        # the key line while a red marker sweeps across it line by line as he says it (research: one place to look, the rest dims).
        pg = ev["page"]; iw, ih = pg["size"]; hl = pg.get("hl", [])
        dispw = pg.get("width", 4300); s = dispw / iw; disph = ih * s   # zoomed into the paragraph: the key line reads at ~95 px (phone-size text)
        fx = pg.get("fx") or (sum(x + w / 2 for x, y, w, h in hl) / len(hl) if hl else iw / 2)   # "fx": a page x to centre on (keeps a wide paragraph's margin in frame)
        fy = sum(y + h / 2 for x, y, w, h in hl) / len(hl) if hl else ih / 2
        left, top = 1920 - fx * s, pg.get("y", 1000) - fy * s            # the highlight's centre sits at the frame's centre
        th = (ev.get("at_t") or {}).get("hl", 0.3)
        bars = "".join(f'<div id="rhl{k}" class="rhl" style="position:absolute;left:{(x - 8) * s:.0f}px;top:{(y - 4) * s:.0f}px;width:{(w + 16) * s:.0f}px;height:{(h + 8) * s:.0f}px;'
                       f'background:rgba(229,57,53,.42);mix-blend-mode:multiply;border-radius:6px;transform-origin:0 50%;transform:scaleX(0)"></div>' for k, (x, y, w, h) in enumerate(hl))
        b = (f'<div class="bg"></div>'
             f'<div id="rpg" style="position:absolute;left:{left:.0f}px;top:{top:.0f}px;width:{dispw}px;height:{disph:.0f}px;transform-origin:{fx * s:.0f}px {fy * s:.0f}px;'
             f'transform:rotate({pg.get("rot", -1.0)}deg)">'
             f'<div style="position:absolute;inset:0;background:#fff;box-shadow:0 40px 140px rgba(0,0,0,.7)"></div>'
             f'<img src="../assets/{pg["img"]}" style="position:absolute;left:0;top:0;width:{dispw}px;height:{disph:.0f}px"/>'
             f'<div id="rdim" style="position:absolute;inset:0;background:rgba(0,0,0,0);pointer-events:none"></div>{bars}</div>'
             f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:radial-gradient(ellipse at 50% 46%,rgba(0,0,0,0) 52%,rgba(0,0,0,.55) 100%);pointer-events:none"></div>')
        if ev.get("source"):
            b += (f'<div id="rsrc" style="position:absolute;left:70px;top:64px;display:flex;align-items:baseline;gap:22px;background:rgba(255,255,255,.94);color:#111;'
                  f'border-radius:18px;padding:16px 32px 18px;white-space:nowrap"><span class="avb" style="font-size:50px">{esc(ev["source"])}</span>'
                  f'<span class="av" style="font-size:40px;color:#666">{esc(ev.get("source_sub", ""))}</span></div>')
            js.append('tl.fromTo("#rsrc",{x:-40},{x:0,duration:SNAP.dur,ease:SNAP.ease},.05);')
        if ev.get("caption"):
            c = ev["caption"]; tcap = (ev.get("at_t") or {}).get("cap", c.get("at", 0.3)) if isinstance(c, dict) else 0.3
            txt = c["text"] if isinstance(c, dict) else c
            b += (f'<div id="rcap" class="center din" style="top:{1700}px;font-size:180px;line-height:1;opacity:0;text-shadow:0 10px 50px rgba(0,0,0,.9)">'
                  f'<span style="display:inline-block;background:rgba(0,0,0,.66);padding:22px 56px 12px;border-radius:22px">{esc(txt)}</span></div>')
            js.append(f'tl.fromTo("#rcap",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{tcap:.3f});')
        js += ['tl.fromTo("#rpg",{y:60},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
               f'tl.fromTo("#rpg",{{scale:{pg.get("s0", 0.94)}}},{{scale:{pg.get("s1", 1.12)},duration:{max(D, 0.5):.3f},ease:"power1.inOut"}},0);',
               f'tl.to("#rdim",{{background:"rgba(0,0,0,.10)",duration:.4,ease:"none"}},{th:.3f});']
        for k in range(len(hl)):
            js.append(f'tl.to("#rhl{k}",{{scaleX:1,duration:.45,ease:"power2.inOut"}},{th + 0.32 * k:.3f});')
    elif t == "doc":
        # A document or clipping, a red marker sweeping across the key line as he says it (Johnny Harris). ev["doc"]: {source, title,
        # text, hl}. Beside OB on his own frame (side "L"/"R"), or full frame (full: true) with a slow push toward the page.
        d = ev["doc"]; full = bool(ev.get("full")); hl = d.get("hl", "")
        txt = esc(d["text"])
        if hl and esc(hl) in txt:
            # a highlighter behind the words that sweeps along each line it covers (box-decoration-break: a phrase that wraps
            # gets one bar per line; an absolutely placed bar collapsed to a sliver on a wrapped phrase, C4367 v2.1)
            txt = txt.replace(esc(hl), f'<span class="hlbar" style="background-image:linear-gradient(rgba(229,57,53,.55),rgba(229,57,53,.55));'
                                       f'background-repeat:no-repeat;background-position:0 70%;background-size:0% 82%;padding:0 6px;margin:0 -6px;'
                                       f'-webkit-box-decoration-break:clone;box-decoration-break:clone">{esc(hl)}</span>', 1)
        pw, fs, pad = (2760, 96, "100px 120px") if full else (1520, 60, "62px 74px")
        th = (ev.get("at_t") or {}).get("hl", 0.6)
        if full:   # centred on the frame whatever its length (a one-line patent title would sit high otherwise)
            pos = f"position:relative"
        else:
            pos = f"{'left' if ev.get('side', 'L') == 'L' else 'right'}:140px;top:{ev.get('y', 360)}px"
        paper = (f'<div id="doc" style="{"" if full else "position:absolute;"}{pos};width:{pw}px;background:#f4f0e6;color:#1d1d1d;border-radius:8px;padding:{pad};'
                 f'box-shadow:0 40px 120px rgba(0,0,0,.6);transform:rotate({ev.get("rot", -1.2)}deg)">'
                 f'<div style="position:absolute;inset:0;background:url(../assets/grain.png);background-size:768px;mix-blend-mode:multiply;opacity:.12;border-radius:8px"></div>'
                 f'<div class="avb" style="position:relative;font-size:{44 if full else 32}px;letter-spacing:3px;color:#7a7a7a;text-transform:uppercase">{esc(d.get("source", ""))}</div>'
                 + (f'<div style="position:relative;font-family:Georgia,serif;font-weight:bold;font-size:{fs + 16}px;line-height:1.15;margin-top:26px">{esc(d["title"])}</div>' if d.get("title") else "")
                 + f'<div style="position:relative;font-family:Georgia,serif;font-size:{fs}px;line-height:1.42;margin-top:28px">{txt}</div></div>')
        b = (f'<div class="bg"></div><div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">{paper}</div>'
             if full else f'{aroll(ev, mock)}{paper}')
        js.append(f'tl.fromTo(".hlbar",{{backgroundSize:"0% 82%"}},{{backgroundSize:"100% 82%",duration:.55,ease:"power2.inOut"}},{th:.3f});')
        if full:
            js += ['tl.fromTo("#doc",{y:50},{y:0,duration:SNAP.dur,ease:SNAP.ease},0);',
                   f'tl.fromTo("#doc",{{scale:1}},{{scale:1.07,duration:{D:.3f},ease:"none"}},0);']
        else:
            js += [f'tl.fromTo("#doc",{{x:{-160 if ev.get("side", "L") == "L" else 160},opacity:0}},{{x:0,opacity:1,duration:SNAP.dur,ease:SNAP.ease}},0);']
            if D > 1.0: js.append(f'tl.to("#doc",{{opacity:0,duration:.25,ease:"none"}},{D-0.27:.3f});')
    else:
        raise ValueError(t)
    if t in ("chapter", "quote", "myths"):  # no dead frames: slow constant-speed push-in while the card holds
        js.append(f'tl.fromTo("#cw",{{scale:1}},{{scale:{1.07 if t == "myths" else 1.04},duration:{D:.3f},ease:"none"}},0);')
    return b, js


def shots_boxes(ev):
    """Client screenshots (chats, charts) in the side panel, as large as fits: 1 big, 2+ stacked when all are wide, else side by side."""
    from PIL import Image
    folder = ev.get("folder", "proof"); ks = [x[0] for x in ev["shots"]]
    sizes = [Image.open(f"{PROJ}/assets/{folder}/{k}.jpg").size for k in ks]
    top0 = 360 if ev.get("title") else 200; ah = 2160 - top0 - 170; n = len(ks)
    if n == 1: cells = [(80, top0, 2660, ah)]
    elif all(w / h > 1.2 for w, h in sizes):
        ch = (ah - 60 * (n - 1)) / n; cells = [(80, top0 + k * (ch + 60), 2660, ch) for k in range(n)]
    else:
        cw = (2660 - 70 * (n - 1)) / n; cells = [(80 + k * (cw + 70), top0, cw, ah) for k in range(n)]
    out = []
    for (x, y, w, h), (iw, ih) in zip(cells, sizes):
        k = min(w / iw, h / ih, 3.0); dw, dh = iw * k, ih * k
        out.append((x + (w - dw) / 2, y + (h - dh) / 2, dw, dh))
    return ks, out


def card_area(ev):
    t = ev["type"]
    if t == "bowl":
        return bowl_anim.html(ev)
    if t in motion_cards.HTML:
        return motion_cards.HTML[t](ev)
    if t == "shots":
        ks, bx = shots_boxes(ev); folder = ev.get("folder", "proof")
        tiles = "".join(f'<div class="sh" id="sh{i}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{h:.0f}px;border-radius:26px;'
                        f'overflow:hidden;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.6);opacity:0"><img src="../assets/{folder}/{k}.jpg" '
                        f'style="width:100%;height:100%;display:block"/></div>' for i, (k, (x, y, w, h)) in enumerate(zip(ks, bx)))
        title = (f'<div id="sht" class="din" style="position:absolute;left:80px;top:150px;font-size:130px">{esc(ev.get("title", ""))}'
                 f'<span class="av" style="font-size:50px;color:#9a9a9a;margin-left:36px">{esc(ev.get("foot", ""))}</span></div>') if ev.get("title") else ""
        return title + tiles
    if t == "photo":
        ph = ev["photos"]; n = len(ph)
        w, h = (1280, 990) if n == 2 else (1900, ev.get("photo_h", 1250))   # photo_h: e.g. 1069 for a 16:9 thumbnail
        has_t = bool(ev.get("title")); top0 = (2160 - ((150 if has_t else 0) + h + 170)) // 2
        tiles = "".join(f'<div class="ph" id="p{i}" style="display:flex;flex-direction:column;align-items:center;gap:40px">'
                        f'<div style="width:{w}px;height:{h}px;border-radius:30px;overflow:hidden;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.55)">'
                        f'<img src="../assets/photos/{k}.jpg" style="width:100%;height:100%;object-fit:{"contain" if k in CONTAIN else "cover"}"/></div>'
                        f'<div class="din" style="font-size:{104 if len(lbl) < 30 else 100}px;text-align:center;max-width:{w + 300}px">{esc(lbl)}</div></div>'
                        for i, (k, lbl) in enumerate((p[0], p[1]) for p in ph))  # [key, caption] or [key, caption, anchor]
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
        # bars: [label, value, shown text] or [label, value, shown text, anchor]; optional title above them
        mx = max(b[1] for b in ev["bars"]); n = len(ev["bars"])
        rows = f'<div id="sbt" class="din" style="position:absolute;left:150px;top:300px;font-size:140px">{esc(ev["title"])}</div>' if ev.get("title") else ""
        y0, dy = (520, 360) if n > 3 else ((640, 470) if n > 2 else (760, 520))   # C4398: a 4th bar ran off the frame at 470; at 560/380 its value sat on the source line
        for i, (lbl, v, txt) in enumerate(b[:3] for b in ev["bars"]):
            wpx = int(1650 * v / mx)
            rows += (f'<div style="position:absolute;left:150px;top:{y0+i*dy}px">'
                     f'<div class="avb" style="font-size:78px;color:#e6e6e6;margin-bottom:34px">{esc(lbl)}</div>'
                     f'<div style="display:flex;align-items:center;gap:50px"><div class="bar" id="bar{i}" style="width:{wpx}px;height:150px;border-radius:75px;background:{Y if i == 0 else "#f2f2f2"};transform-origin:left center"></div>'
                     f'<div class="din" id="bv{i}" style="font-size:150px;white-space:nowrap">{esc(txt)}</div></div></div>')
        return rows
    if t == "dotgrid":
        # C4398 (OB 10-30: "I hate boring just text slides make it more engaging"): Nippard's dot charts. Rows of dots that pop in,
        # then the counted ones light up in the row's colour as he says it, and the value lands. ev["rows"]: [{"label", "n", "k",
        # "color", "text", "at", optional "shape": "person"}]; a row of 100 is a 25 x 4 block. Optional ev["title"].
        rows = f'<div id="dgt" class="din" style="position:absolute;left:150px;top:{220 if len(ev["rows"]) > 2 else 330}px;font-size:132px">{esc(ev["title"])}</div>' if ev.get("title") else ""
        y = 470 if ev.get("title") else 330
        for i, r in enumerate(ev["rows"]):
            n, k = r["n"], r["k"]; cols = n if n <= 20 else 25; nr = -(-n // cols)
            size = 112 if n <= 10 else (84 if n <= 20 else 58); gap = int(size * 0.32)
            dots = ""
            f0 = r.get("from", 0)   # the lit run can start later in the row (weeks 8 to 10 of 12)
            for j in range(n):
                hi = f0 <= j < f0 + k
                shape = ("border-radius:50% 50% 46% 46%" if r.get("shape") == "person" else "border-radius:50%")
                dots += (f'<div class="dg{i}{" dh" + str(i) if hi else ""}" style="width:{size}px;height:{size}px;{shape};background:#3a3a3a;'
                         f'transform:scale(0);opacity:0"></div>')
            bw = cols * size + (cols - 1) * gap
            rows += (f'<div style="position:absolute;left:150px;top:{y}px">'
                     f'<div class="avb" style="font-size:74px;color:#e6e6e6;margin-bottom:30px">{esc(r["label"])}</div>'
                     f'<div style="display:flex;align-items:center;gap:60px"><div style="display:grid;grid-template-columns:repeat({cols},{size}px);gap:{gap}px;width:{bw}px">{dots}</div>'
                     f'<div class="din" id="dgv{i}" style="font-size:{150 if n <= 20 else 130}px;white-space:nowrap;color:{r.get("color", Y)};opacity:0">{esc(r.get("text", ""))}</div></div></div>')
            y += 74 + 30 + nr * size + (nr - 1) * gap + (90 if len(ev["rows"]) > 2 else 140)
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
        # optional header (photo-card style) so the panel isn't empty before the first row is said
        head = f'<div id="set" class="center avb" style="top:430px;font-size:96px">{esc(ev["title"])}</div>' if ev.get("title") else ""
        return head + "".join(f'<div id="se{i}" class="center din" style="top:{640+i*440}px;font-size:170px">'
                       + (f'{esc(a)} <span style="color:{Y}">= {esc(b)}</span>' if a else f'<span style="color:{Y}">{esc(b)}</span>') + '</div>'
                       for i, (a, b, _) in enumerate(ev["rows"]))  # empty left side: the row is just the yellow value
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
        return (f'<div style="position:absolute;left:40px;top:0;width:2740px;height:2160px;display:flex;flex-direction:column;justify-content:center">'
                f'<div id="skk" style="display:flex;align-items:center;gap:30px;margin-bottom:40px">'
                f'<span class="avb" style="font-size:66px;background:{Y};color:#111;padding:12px 30px;border-radius:14px;letter-spacing:2px">STUDY</span>'
                f'<span class="avb" style="font-size:74px;color:#e0e0e0">{esc(s["journal"])} &middot; {esc(s["year"])}</span></div>'
                f'<div id="spp" style="background:#fff;border-radius:30px;padding:80px 90px;box-shadow:0 30px 90px rgba(0,0,0,.55);color:#111">'
                f'<div class="avb" style="font-size:86px;line-height:1.14;color:#333">{esc(s["title"])}</div>'
                f'<div class="av" style="font-size:58px;color:#777;margin-top:24px">{esc(s["authors"])}</div>'
                f'<div style="height:5px;background:#ececec;margin:54px 0"></div>'
                f'<div class="avb" style="font-size:118px;line-height:1.26">{finding}</div>'
                f'<div class="av" style="font-size:52px;color:#8a8a8a;margin-top:48px">PubMed {esc(s["pmid"])}&emsp;&emsp;doi.org/{esc(s["doi"])}</div></div>'
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
                        f'<div><div class="avb" style="font-size:58px;line-height:1.18">{esc(txt)}</div>'
                        f'<div class="av" style="font-size:46px;color:#b8b8b8;margin-top:8px">{esc(src)}</div></div></div>'
                        for i, (txt, src, _) in enumerate(c.get("callouts", [])))
        return (f'<div id="cht" class="din" style="position:absolute;left:40px;top:150px;font-size:130px">{esc(c["title"])}</div>'
                f'<div class="av" style="position:absolute;left:44px;top:300px;font-size:54px;color:#aaa">{esc(c["source"])}</div>'
                f'<svg id="csv" style="position:absolute;left:0;top:420px" width="2820" height="1260" viewBox="0 0 2820 1260">'
                f'{grid}{xl}<polyline id="cl" points="{pts}" fill="none" stroke="{Y}" stroke-width="14" stroke-linejoin="round" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>{dots}'
                f'<text id="cv0" x="{X(xs[0]):.0f}" y="{Yp(ys[0])-50:.0f}" text-anchor="middle" font-family="DINC" font-size="110" fill="#fff">{c["points"][0][1]}{c.get("unit","")}</text>'
                f'<text id="cv1" x="{X(xs[-1])-20:.0f}" y="{Yp(ys[-1])-50:.0f}" text-anchor="end" font-family="DINC" font-size="150" fill="{Y}">{c["points"][-1][1]}{c.get("unit","")}</text></svg>'
                f'<div style="position:absolute;left:330px;top:470px;width:1150px">{calls}</div>')
    raise ValueError(t)


def card_js(ev):
    t, D, js = ev["type"], ev["dur"], []
    if t == "bowl":
        return bowl_anim.js(ev)
    if t in motion_cards.JS:
        return motion_cards.JS[t](ev)
    if t == "shots":
        if ev.get("title"): js.append('tl.fromTo("#sht",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);')
        for i, tt in enumerate(ev.get("shots_t") or [0.35 + 0.5 * k for k in range(len(ev["shots"]))]):
            js.append(f'tl.fromTo("#sh{i}",{{opacity:0,y:60}},{{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease}},{max(tt, 0.3):.3f});')
        js.append(f'tl.fromTo(".sh",{{scale:1}},{{scale:1.02,duration:{max(D - 0.6, 1):.3f},ease:"none"}},.3);')   # no frozen frames
        return js
    if t == "photo":
        if ev.get("title"):
            js.append('tl.fromTo("#pt",{opacity:0,y:20},{opacity:1,y:0,duration:SOFT.dur,ease:SOFT.ease},.05);')
        pts = ev.get("photos_t") or [0.1 + i * 0.3 for i in range(len(ev["photos"]))]   # photos_t: per-photo anchors (resolve)
        for i, _ in enumerate(ev["photos"]):
            js.append(f'tl.fromTo("#p{i}",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{pts[i]:.2f});')
    elif t == "equation":
        rt = ev.get("right_t", D * 0.45)
        js += ['tl.fromTo("#eqL",{opacity:0,scale:.9},{opacity:1,scale:1,duration:POP.dur,ease:POP.ease},.1);',
               'tl.fromTo("#eqM",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.5);',
               f'tl.fromTo("#eqR",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:POP.dur,ease:POP.ease}},{rt:.3f});']
    elif t == "stat_ratio":
        js += ['tl.fromTo("#sr",{opacity:0,y:30},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.1);',
               'tl.fromTo("#srs",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.6);']
    elif t == "stat_bars":
        if ev.get("title"):
            js.append('tl.fromTo("#sbt",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);')
        bt = ev.get("bars_t") or [0.2 + i * 0.9 for i in range(len(ev["bars"]))]   # bars_t: each bar grows as he says it
        for i, _ in enumerate(ev["bars"]):
            js += [f'tl.fromTo("#bar{i}",{{scaleX:0}},{{scaleX:1,duration:BAR.dur,ease:BAR.ease}},{max(bt[i], 0.2):.2f});',
                   f'tl.fromTo("#bv{i}",{{opacity:0}},{{opacity:1,duration:SOFT.dur,ease:SOFT.ease}},{max(bt[i], 0.2) + 0.4:.2f});']
    elif t == "dotgrid":
        if ev.get("title"):
            js.append('tl.fromTo("#dgt",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.15);')
        rt = ev.get("rows_t") or [0.3 + i * 1.0 for i in range(len(ev["rows"]))]
        for i, r in enumerate(ev["rows"]):
            t0 = max(rt[i] - 0.5, 0.2); each = min(0.035, 0.7 / max(r["n"], 1))
            js += [f'tl.to(".dg{i}",{{scale:1,opacity:1,duration:.3,ease:"back.out(2)",stagger:{each:.4f}}},{t0:.3f});',
                   f'tl.to(".dh{i}",{{backgroundColor:"{r.get("color", Y)}",scale:1.12,duration:.22,ease:"power2.out",stagger:{min(0.05, 0.6 / max(r["k"], 1)):.4f}}},{t0 + 0.35 + r["n"] * each:.3f});',
                   f'tl.to(".dh{i}",{{scale:1,duration:.3,ease:"power2.out"}},{t0 + 0.8 + r["n"] * each:.3f});',
                   f'tl.fromTo("#dgv{i}",{{opacity:0,x:-30}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{t0 + 0.5 + r["n"] * each:.3f});']
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
        if ev.get("title"):
            js.append('tl.fromTo("#set",{opacity:0,y:20},{opacity:1,y:0,duration:SOFT.dur,ease:SOFT.ease},.3);')
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
        c = ev["chart"]; draw = 2.4
        x0, x1, y0, y1 = 260, 2560, 1120, 80  # same plot box as card_area
        xy = [(x0 + (x - c["xmin"]) / (c["xmax"] - c["xmin"]) * (x1 - x0), y0 - (y - c["ymin"]) / (c["ymax"] - c["ymin"]) * (y0 - y1))
              for x, y in c["points"]]
        seg = [((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 for (ax, ay), (bx, by) in zip(xy, xy[1:])]
        cum = [0.0] + [sum(seg[:k + 1]) for k in range(len(seg))]
        js += ['tl.fromTo("#cht",{opacity:0,y:20},{opacity:1,y:0,duration:SNAP.dur,ease:SNAP.ease},.2);',
               'tl.fromTo("#cv0",{opacity:0},{opacity:1,duration:SOFT.dur,ease:SOFT.ease},.45);',
               f'tl.fromTo("#cl",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:{draw},ease:"none"}},.5);']
        for i in range(len(xy)):  # each point pops when the constant-speed line reaches it (by path length, not index)
            js.append(f'tl.fromTo("#cd{i}",{{scale:0,transformOrigin:"50% 50%"}},{{scale:1,duration:POP.dur,ease:POP.ease}},{0.5 + draw * cum[i] / max(cum[-1], 1):.3f});')
        js.append(f'tl.fromTo("#cv1",{{opacity:0,y:20}},{{opacity:1,y:0,duration:POP.dur,ease:POP.ease}},{0.5 + draw:.3f});')
        for i, tt in enumerate(ev.get("callouts_t", [])):
            js.append(f'tl.fromTo("#cc{i}",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:SNAP.dur,ease:SNAP.ease}},{tt:.3f});')
    return js


PIP_BOX = (3080, 1218, 660, 842)   # the house .pip box, bottom right (CSS above)
PIP_SRC = (1340, 0, 0.6)          # his A-roll window in the box: source x, source y, scale (head and shoulders; head_clear: head x 1300-2450)


def add_pics(ev, b, js):
    """2026-11-11 C4465 (OB r1 0:56.1 "you didnt put the tranforamtions and testimonials of clients", M56/M86): client
    before/afters, testimonials or his own photo on top of any card, beside him (never over his face). Static once landed (no
    zoom, R18): a short rise on the word, a cut or a fade out. ev["pics"] = [{key, folder, x, y, w, h, t0, t1?, enter, exit}]."""
    P = ev.get("pics") or []
    D = ev["dur"]
    for i, p in enumerate(P):
        t0 = max(0.0, min(float(p.get("t0", 0.0)), D - 0.05)); t1 = min(float(p.get("t1", D)), D)
        b += (f'<img class="ov pic" id="pc{i}" src="../assets/{p.get("folder", "proof")}/{p["key"]}.jpg" '
              f'style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px;opacity:0;filter:drop-shadow(0 16px 36px rgba(0,0,0,.55))"/>')   # inline: the page CSS stays as it was, so cards without pictures keep their cached renders
        if p.get("enter", "slide") == "slide":
            js += [f'tl.fromTo("#pc{i}",{{opacity:0}},{{opacity:1,duration:.12,ease:"none"}},{t0:.3f});',
                   f'tl.fromTo("#pc{i}",{{y:46}},{{y:0,duration:SOFT.dur,ease:SOFT.ease}},{t0:.3f});']
        else:
            js.append(f'tl.set("#pc{i}",{{opacity:1}},{t0:.3f});')
        if t1 < D - 0.02:
            js.append(f'tl.to("#pc{i}",{{opacity:0,duration:.2,ease:"none"}},{max(t0, t1 - 0.2):.3f});' if p.get("exit", "fade") == "fade"
                      else f'tl.set("#pc{i}",{{opacity:0}},{t1:.3f});')
    return b, js


def add_pip(ev, b, mock):
    """2026-11-11 C4465 (OB r2 1:06.4 "you just put a bench, im not in the overlay", M87/M37): a full-frame cover shows him in
    the box, his own frame, live and in sync (the event's A-roll). ev["ob_pip"] = true or {x, y, w, h, sx, sy, s}."""
    pp = ev.get("ob_pip")
    if not pp: return b
    pp = pp if isinstance(pp, dict) else {}
    x, y, w, h = (pp.get(k, d) for k, d in zip("xywh", PIP_BOX))
    sx, sy, s = pp.get("sx", PIP_SRC[0]), pp.get("sy", PIP_SRC[1]), pp.get("s", PIP_SRC[2])
    st = f'position:absolute;left:{-sx * s:.0f}px;top:{-sy * s:.0f}px;width:{W * s:.0f}px;height:{H * s:.0f}px;object-fit:cover'
    inner = (f'<img src="{ev.get("mock_still") or "../assets/stills/" + ev["id"] + ".jpg"}" style="{st}"/>' if mock else
             f'<video id="pipv" class="clip" src="../assets/aroll/{ev["id"]}.mp4" muted playsinline data-start="0" '
             f'data-duration="{ev["dur"]:.3f}" data-track-index="5" style="{st}"></video>')
    return b + (f'<div class="pip" id="pipb" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
                f'box-shadow:0 18px 50px rgba(0,0,0,.5)">{inner}</div>')


def page(ev, mock):
    b, js = body_for(ev, mock)
    kin = KIN and ev["type"] in kinetic_cards.TYPES and kinetic_cards.handles(ev)
    if not kin or ev["type"] == "chapter":   # a kinetic card brings its own grade and grain; a chapter keeps its wash
        b, js = stage.dress(ev, b, js, mock)   # v3: background, push-in, grain (C4367 2026-10-20)
    if KIN and not kin:
        b, pj = kinetic_cards.warm_other_panels(ev, b, mock); js = pj + js
    b, js = add_pics(ev, b, js)    # 2026-11-11 C4465: proof pictures on top (no-op without ev["pics"])
    b = add_pip(ev, b, mock)       # 2026-11-11 C4465: him in the box on a full-frame cover (no-op without ev["ob_pip"])
    D = ev["dur"]
    return f"""<!doctype html>
<html lang="en" data-resolution="landscape">
<head><meta charset="UTF-8"/><meta name="viewport" content="width={W}, height={H}"/>
<script src="../assets/gsap.min.js"></script>
<style>{CSS}{kinetic_cards.CSS if KIN else ""}</style></head>
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
    global PROJ
    proj, mock = sys.argv[2], "--mock" in sys.argv
    PROJ = proj
    os.makedirs(f"{proj}/compositions", exist_ok=True)
    stage.assign(events, proj)
    for ev in events:
        name = f'{ev["id"]}{".mock" if mock else ""}.html'
        open(f"{proj}/compositions/{name}", "w").write(page(ev, mock))
    print(len(events), "compositions ->", proj, "(mock)" if mock else "")


if __name__ == "__main__":
    main()
