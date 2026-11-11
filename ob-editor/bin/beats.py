#!/usr/bin/env python3
"""Beat sheet for an edit (chase_ai_'s "beat" workflow, built 2026-11-07).

An edit is cut into numbered BEATS: a new beat starts at every hard cut, every board/graphic entrance and every caption-line
change (beats under 0.7 s are merged into a neighbour). OB gives notes as "beat 33: ..." and only that beat is re-rendered.

  python3 -I beats.py map  <edit> [--dir D] [--no-hash]       number the beats -> D/beats.json + D/beats.html (+ frames_md5.json)
  python3 -I beats.py redo <edit> <n>... [--dir D] [--no-gate] re-render only those beats' frames, re-encode from the cache,
                                                              remix audio only if the beat's sounds changed, run the gate, print timings
  python3 -I beats.py sfx  <edit> <n> list [--all]            the beat's sounds + the sound families/files available
  python3 -I beats.py sfx  <edit> <n> swap <old> <new> [--db X] [--gate]
                                                              <old>: index in the beat's list, file name or family; <new>: a path,
                                                              a path under the sfx roots, or a unique file name.
                                                              Writes D/sfx_overrides.json, remixes audio only, muxes with -c:v copy.
  python3 -I beats.py adapters                                 the registered adapters
  python3 -I beats.py build|check <longform:project> [...]     long-form only (adapters/longform.py): build the per-chapter segment encodes; A/V sync + gate check
<edit> may also be adapter:project (longform:c4423). An adapter that defines cmd_<name>(args) owns that command (long-form owns map and redo).

<edit> = an adapter name (bin/beats_adapters/<name>.py) or a path to an adapter .py file.
D (default: the adapter's own folder, e.g. <edit dir>/beats) holds beats.json, beats.html, frames_md5.json, sfx_overrides.json,
state.json, mix.wav, out/current.mp4 (the last re-encode), aside/<stamp>/ (old frames moved aside, never deleted).
Nothing here delivers anything: outputs stay in D. Copy a finished current.mp4 to the delivery folders yourself, after the gate.

HOW TO ADD AN ADAPTER (level-kit, brand_react_render, cards, hyperframes ... any engine that renders one image per frame)
  Make bin/beats_adapters/<name>.py with   def make(beats_dir, h): return Adapter(beats_dir, h)    (h = this module: helpers).
  The class needs (all times are EDIT seconds, k = frame index, t = k / fps):
    name, fps, n_frames, beats_dir (the arg, or the default folder)
    frame_path(k)                   where frame k's PNG lives (the engine's frame cache)
    render_frame(k) -> PIL image    render ONE frame exactly as the engine's main loop would (importing must not render anything)
    state(k) -> dict                {"shot": id of the source clip/take (changes at a hard cut), "graphic": layout/board name or None,
                                     "caption": the caption LINE (phrase) on screen or None, "elements": ["short phrases", ...]}
    words() -> [{"w","s","e","who"}]  spoken words in edit time ("who": "ob" or "her"/"him" for a source clip)
    base_sfx_plan() -> the same list WITHOUT overrides (overrides are keyed on it)
    sfx_plan() -> [(file, t, dB, family)]  WITH h.apply_sfx_overrides(plan, beats_dir) applied; sfx_onset(item) if a sound starts before t
    music_on(t) -> bool
    audio(out_wav)                  remix bed + voice + sfx; must use sfx_plan() and write only out_wav and scratch inside beats_dir
    encode(out_mp4, wav)            encode the frame cache + wav exactly like the engine's own final encode
    gate(out_mp4) -> bool           the engine's QC gate call (with cam= for lip sync when there is a camera map)
    base_mix(), mix_sig(), base_mix_sig()   the engine's own mix.wav and signatures of the sound plan (so an unchanged plan is not remixed)
    final_path()                    the engine's finished file (only READ, as the video source for a first sfx swap)
    families() -> {family: [files]} ;  full_render_s() -> seconds of the last full render, or None
  Engines that do not keep PNGs per frame (a HyperFrames project, a Blender shot) can still adapt: render_frame(k) calls their
  single-frame entry (hyperframes seek + capture, blender -f k) and frame_path(k) is where the result is written.
"""
import os, sys, json, time, glob, shutil, hashlib, base64, io, subprocess, importlib.util, html
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
ADAPTERS = os.path.join(HERE, "beats_adapters")
MIN_BEAT = 0.7
LEAD = 0.12   # a sound that starts up to 0.12 s before a beat's first frame (the whoosh ahead of a cut) belongs to that beat
SFX_ROOTS = ["/Volumes/T7/OB-EDITS/sfx-library", os.path.expanduser("~/ob-editor/assets")]
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".aiff", ".flac", ".ogg")

# ------------------------------------------------------------------ helpers adapters use
def apply_sfx_overrides(plan, beats_dir):
    """plan = [(file, t, dB, fam)]; D/sfx_overrides.json = {"swaps": [{"t", "old", "new", "db"?}]} replaces the file (and dB) of the sound
    whose base file and time match."""
    p = os.path.join(beats_dir, "sfx_overrides.json")
    if not os.path.exists(p): return list(plan)
    sw = json.load(open(p)).get("swaps", []); out = []
    for f, t, db, fam in plan:
        hit = next((s for s in sw if abs(s["t"] - t) < 0.0015 and s["old"] == f), None)
        out.append((hit["new"], t, hit.get("db", db), fam) if hit else (f, t, db, fam))
    return out
def plan_sig(plan, extra=""):
    return hashlib.md5((json.dumps([[a, round(b, 3), c, d] for a, b, c, d in plan]) + extra).encode()).hexdigest()[:12]
def caption_lines(words, gap=0.30):
    """group word dicts (sorted) into caption lines: a new line after . ? ! or a pause over `gap` s -> [(first_index, last_index)]"""
    lines, st = [], 0
    for i in range(1, len(words)):
        if words[i - 1]["w"].strip().endswith((".", "?", "!")) or words[i]["s"] - words[i - 1]["e"] > gap: lines.append((st, i - 1)); st = i
    if words: lines.append((st, len(words) - 1))
    return lines

# ------------------------------------------------------------------ generic plumbing
def fmt_t(t): return f"{int(t // 60)}:{t % 60:04.1f}"
def load_adapter(edit, beats_dir=None):
    """edit = adapter name | path to an adapter .py | name:project (2026-11-08: the adapter gets the part after the colon, e.g. longform:c4423)"""
    edit, _, arg = edit.partition(":") if not edit.endswith(".py") else (edit, "", "")
    path = edit if edit.endswith(".py") else os.path.join(ADAPTERS, edit + ".py")
    if not os.path.exists(path): sys.exit(f"no adapter {path} (python3 -I beats.py adapters)")
    spec = importlib.util.spec_from_file_location("beats_adapter_" + os.path.basename(path)[:-3], path); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); A = m.make(beats_dir, sys.modules[__name__], arg) if arg else m.make(beats_dir, sys.modules[__name__])
    os.makedirs(A.beats_dir, exist_ok=True); return A
def jload(p, default=None): return json.load(open(p)) if os.path.exists(p) else default
def jsave(p, o):
    tmp = p + ".tmp"; json.dump(o, open(tmp, "w"), indent=1); os.replace(tmp, p)
def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()
def hash_frames(A):
    ks = list(range(A.n_frames))
    with ThreadPoolExecutor(8) as ex: hs = list(ex.map(lambda k: md5_file(A.frame_path(k)) if os.path.exists(A.frame_path(k)) else None, ks))
    return {str(k): h for k, h in zip(ks, hs)}
def move_aside(path, d):
    os.makedirs(d, exist_ok=True); dst = os.path.join(d, os.path.basename(path)); shutil.move(path, dst); return dst
def wait_free():
    try:
        import render_slots; render_slots.wait_free(log=print)
    except Exception as e: print("render_slots:", e)

def compute_beats(A):
    N, fps = A.n_frames, A.fps; st = [A.state(k) for k in range(N)]; cuts = [(0, ["start"])]
    for k in range(1, N):
        r, a, b = [], st[k - 1], st[k]
        if b["shot"] != a["shot"]: r.append("cut")
        if b["graphic"] != a["graphic"] and b["graphic"] not in (None, "face", "src", "cta"): r.append("board " + str(b["graphic"]))
        elif b["graphic"] != a["graphic"] and "cut" not in r and not getattr(A, "exits_are_not_beats", False): r.append("layout " + str(b["graphic"]))   # long-form: a graphic leaving is not a beat
        if b["caption"] != a["caption"] and b["caption"] is not None: r.append("caption line")
        if r: cuts.append((k, r))
    rank = lambda rs: max(3 if x.startswith(("board", "layout")) else 2 if x == "cut" else 1 for x in rs)
    bs = [dict(k0=k, reasons=r) for k, r in cuts]
    for i, b in enumerate(bs): b["k1"] = bs[i + 1]["k0"] if i + 1 < len(bs) else N
    while len(bs) > 1:
        short = [i for i, b in enumerate(bs) if (b["k1"] - b["k0"]) / fps < MIN_BEAT]
        if not short: break
        i = min(short, key=lambda i: bs[i]["k1"] - bs[i]["k0"])
        if i == 0: a = 0                                                           # first beat absorbs the next one
        elif i == len(bs) - 1: a = i - 1                                           # last beat joins the previous one
        else: a = i if rank(bs[i + 1]["reasons"]) < rank(bs[i]["reasons"]) else i - 1   # drop the weaker of the two boundaries
        bs[a]["k1"] = bs[a + 1]["k1"]; del bs[a + 1]
    W = A.words(); plan = A.sfx_plan(); base = A.base_sfx_plan(); out = []
    for n, b in enumerate(bs, 1):
        k0, k1 = b["k0"], b["k1"]; t0, t1 = k0 / fps, k1 / fps; mid = (k0 + k1 - 1) // 2; els = []
        for k in sorted({k0, mid, k1 - 1}):
            for e in st[k]["elements"]:
                if e not in els: els.append(e)
        inb = [w for w in W if t0 - 1e-6 <= w["s"] < t1 - 1e-6]
        ob = " ".join(w["w"].strip() for w in inb if w.get("who", "ob") == "ob"); her = " ".join(w["w"].strip() for w in inb if w.get("who", "ob") != "ob")
        sfx = []
        for item, bi in zip(plan, base):
            on = A.sfx_onset(item) if hasattr(A, "sfx_onset") else item[1]
            if t0 - LEAD <= on < t1 - LEAD: sfx.append(dict(file=item[0], base=bi[0], name=os.path.basename(item[0]), fam=item[3], t=round(item[1], 3), onset=round(on, 3), db=item[2]))
        mus = [A.music_on(k / fps) for k in (k0, mid, k1 - 1)]
        out.append(dict(id=n, t0=round(t0, 3), t1=round(t1, 3), k0=k0, k1=k1, dur=round(t1 - t0, 2), reasons=b["reasons"], ob_words=ob, her_words=her,
                        on_screen=els, sfx=sfx, music="on" if all(mus) else "off" if not any(mus) else "partial", graphic=st[mid]["graphic"]))
    return out

def thumb_b64(A, k, w=240):
    from PIL import Image
    im = Image.open(A.frame_path(k)).convert("RGB"); im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=72); return base64.b64encode(buf.getvalue()).decode()

CSS = """:root{color-scheme:light dark;--bg:#f6f5f1;--card:#fff;--ink:#1c1c20;--mut:#6c6c68;--line:#dedcd4;--chip:#ecebe4;--acc:#e0b400}
@media(prefers-color-scheme:dark){:root{--bg:#131315;--card:#1c1c20;--ink:#ecebe6;--mut:#9b9b94;--line:#33333a;--chip:#2a2a30}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 -apple-system,Helvetica,Arial,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0;flex:1 1 200px}header span{color:var(--mut);font-size:13px}
button{font:inherit;background:var(--acc);color:#1c1c20;border:0;border-radius:8px;padding:8px 14px;font-weight:600}
main{max-width:760px;margin:0 auto;padding:12px 16px 60px}
.beat{display:flex;flex-wrap:wrap;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px;margin:0 0 12px}
.th{flex:0 0 240px;max-width:100%}.th img{display:block;width:100%;height:auto;border-radius:8px;background:#000}
.info{flex:1 1 240px;min-width:0}.top{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.num{font-size:20px;font-weight:800}.tm{color:var(--mut);font-size:13px}
.chip{display:inline-block;background:var(--chip);border-radius:20px;padding:1px 9px;font-size:12px;margin:0 4px 4px 0}
.lab{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em;margin:8px 0 2px}
.words{font-size:15px}.her{color:var(--mut);font-style:italic}ul{margin:0;padding-left:18px}li{margin:1px 0}
textarea{width:100%;min-height:54px;margin-top:8px;font:inherit;background:var(--bg);color:var(--ink);border:1px dashed var(--line);border-radius:8px;padding:8px}
@media(max-width:560px){.th{flex-basis:100%}.th img{max-width:240px}}"""
def build_html(beats, thumbs, name):
    h = html.escape; rows = []
    for b in beats:
        sf = "".join(f"<li>{h(s['name'])} <span class=tm>({h(s['fam'])}, {s['onset']:.2f}s, {s['db']} dB)</span></li>" for s in b["sfx"]) or "<li class=tm>none</li>"
        els = "".join(f"<li>{h(e)}</li>" for e in b["on_screen"]) or "<li class=tm>-</li>"
        wd = (f"<div class=words>{h(b['ob_words'])}</div>" if b["ob_words"] else "") + (f"<div class='words her'>her: {h(b['her_words'])}</div>" if b["her_words"] else "") or "<div class=tm>no speech</div>"
        ch = "".join(f"<span class=chip>{h(r)}</span>" for r in b["reasons"])
        rows.append(f"""<section class=beat id=b{b['id']}><div class=th><img alt="beat {b['id']}" src="data:image/jpeg;base64,{thumbs[b['id']]}"></div><div class=info>
<div class=top><span class=num>{b['id']}</span><span class=tm>{fmt_t(b['t0'])} to {fmt_t(b['t1'])} &middot; {b['dur']:.1f}s &middot; frames {b['k0']}-{b['k1'] - 1}</span></div>{ch}
<div class=lab>Words</div>{wd}<div class=lab>On screen</div><ul>{els}</ul><div class=lab>Sounds &middot; music {h(b['music'])}</div><ul>{sf}</ul>
<textarea data-b="{b['id']}" placeholder="beat {b['id']}: ..."></textarea></div></section>""")
    js = """function notes(){var o=[];document.querySelectorAll('textarea').forEach(function(t){if(t.value.trim())o.push('beat '+t.dataset.b+': '+t.value.trim())});return o.join('\\n')}
document.getElementById('cp').onclick=function(){var b=this,s=notes();if(!s){b.textContent='No notes yet';return}
(navigator.clipboard?navigator.clipboard.writeText(s):Promise.reject()).then(function(){b.textContent='Copied'},function(){prompt('Copy your notes',s)})}"""
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Beats {h(name)}</title><style>{CSS}</style></head><body>
<header><h1>{h(name)}: {len(beats)} beats</h1><span>{fmt_t(beats[-1]['t1'])} total</span><button id=cp>Copy my notes</button></header>
<main>{''.join(rows)}</main><script>{js}</script></body></html>"""

# ------------------------------------------------------------------ commands
def cmd_map(A, args):
    t0 = time.time(); beats = compute_beats(A); bd = A.beats_dir
    thumbs = {b["id"]: thumb_b64(A, (b["k0"] + b["k1"] - 1) // 2) for b in beats}
    jsave(os.path.join(bd, "beats.json"), dict(edit=A.name, fps=A.fps, n_frames=A.n_frames, min_beat=MIN_BEAT, made=time.strftime("%Y-%m-%d %H:%M:%S"), beats=beats))
    open(os.path.join(bd, "beats.html"), "w").write(build_html(beats, thumbs, A.name))
    if "--no-hash" not in args:
        t1 = time.time(); jsave(os.path.join(bd, "frames_md5.json"), hash_frames(A)); print(f"frame manifest: {A.n_frames} frames hashed in {time.time() - t1:.1f}s")
    print(f"{A.name}: {len(beats)} beats in {fmt_t(beats[-1]['t1'])} ({time.time() - t0:.1f}s)\n  {os.path.join(bd, 'beats.html')}\n  {os.path.join(bd, 'beats.json')}")
    for b in beats[:3] + beats[-1:]: print(f"  beat {b['id']:>2} {fmt_t(b['t0'])}-{fmt_t(b['t1'])} {','.join(b['reasons'])} | {(b['ob_words'] or b['her_words'])[:50]}")

def load_beats(A):
    j = jload(os.path.join(A.beats_dir, "beats.json"))
    if not j: sys.exit(f"no {A.beats_dir}/beats.json: run  beats.py map {A.name}  first")
    if j["n_frames"] != A.n_frames: sys.exit(f"beats.json is for {j['n_frames']} frames, the edit now has {A.n_frames}: run map again")
    return j["beats"]
def pick(beats, ids):
    by = {b["id"]: b for b in beats}
    for i in ids:
        if i not in by: sys.exit(f"no beat {i} (1-{len(beats)})")
    return [by[i] for i in ids]

def ensure_mix(A, st):
    """(wav, remixed?): the mix on disk unless the sound plan or music changed since it was made"""
    sig = A.mix_sig(); mix = os.path.join(A.beats_dir, "mix.wav")
    have = (st.get("mix_sig"), mix) if st.get("mix_sig") and os.path.exists(mix) else (A.base_mix_sig(), A.base_mix())
    if have[0] == sig: return have[1], False
    t = time.time(); A.audio(mix); st["mix_sig"] = sig; print(f"audio remixed in {time.time() - t:.1f}s"); return mix, True

def cmd_redo(A, args):
    ids = [int(a) for a in args if a.isdigit()]
    if not ids: sys.exit("usage: beats.py redo <edit> <beat#>...")
    beats = load_beats(A); sel = pick(beats, ids); bd = A.beats_dir; st = jload(os.path.join(bd, "state.json"), {})
    ks = sorted({k for b in sel for k in range(b["k0"], b["k1"])}); T0 = time.time()
    man_p = os.path.join(bd, "frames_md5.json"); man = jload(man_p)
    if man is None: print("no frame manifest: hashing the cache first (map normally does this)"); man = hash_frames(A)
    stamp = time.strftime("%Y%m%d-%H%M%S"); aside = os.path.join(bd, "aside", stamp)
    for k in ks:
        if os.path.exists(A.frame_path(k)): move_aside(A.frame_path(k), aside)
    wait_free(); tr = time.time()
    for n, k in enumerate(ks):
        A.render_frame(k).save(A.frame_path(k), compress_level=1)
        if n and n % 50 == 0: print(f"  rendered {n}/{len(ks)}", flush=True)
    t_render = time.time() - tr; per = t_render / max(1, len(ks))
    tv = time.time(); now = hash_frames(A); kset = {str(k) for k in ks}
    missing = [k for k, v in now.items() if v is None]; outside = [k for k, v in now.items() if k not in kset and v != man.get(k)]; inside = [k for k in kset if now[k] != man.get(k)]
    print(f"verify: {len(now) - len(ks)} other frames byte-compared with the manifest: {len(outside)} differ; "
          f"{len(ks)} re-rendered frames: {len(inside)} differ from their old bytes ({time.time() - tv:.1f}s)")
    if missing or outside: sys.exit(f"STOP: frames missing {missing[:5]} or changed outside the beat {outside[:5]}; old frames are in {aside}")
    man.update({str(k): now[str(k)] for k in ks}); jsave(man_p, man)
    wav, remix = ensure_mix(A, st); out = os.path.join(bd, "out", "current.mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out): move_aside(out, aside)
    te = time.time(); wait_free(); A.encode(out, wav); t_enc = time.time() - te; jsave(os.path.join(bd, "state.json"), st); ok = None; t_gate = 0.0
    if "--no-gate" not in args:
        tg = time.time(); ok = A.gate(out); t_gate = time.time() - tg
    total = time.time() - T0; full = A.full_render_s()
    print(f"\nREDO beats {ids}: {len(ks)} of {A.n_frames} frames ({100 * len(ks) / A.n_frames:.1f}%)\n  render {t_render:.1f}s ({per:.2f}s/frame) + encode {t_enc:.1f}s + audio "
          f"{'remixed' if remix else 'reused'}" + (f" + gate {t_gate:.1f}s" if ok is not None else "") + f"  = {total:.1f}s total ({total - t_gate:.1f}s without the gate)"
          + f"\n  full render: {('%.0fs (last full build, render + audio + encode, no gate)' % full) if full else 'n/a'}"
          + f"\n  output: {out}" + (f"\n  GATE: {'PASS' if ok else 'NOT PASS'}" if ok is not None else "\n  gate skipped"))
    return ok

def sfx_catalog():
    out = {}
    for root in SFX_ROOTS:
        if not os.path.isdir(root): continue
        for d, _, fs in sorted(os.walk(root)):
            fs = sorted(f for f in fs if f.lower().endswith(AUDIO_EXT) and not f.startswith("._"))
            if fs: out[("lib/" if root == SFX_ROOTS[0] else "assets/") + os.path.relpath(d, root)] = fs
    return out
def resolve_new(new):
    if os.path.isabs(new) and os.path.exists(new): return new
    for r in SFX_ROOTS:
        if os.path.exists(os.path.join(r, new)): return os.path.join(r, new)
    hits = [os.path.join(d, f) for r in SFX_ROOTS if os.path.isdir(r) for d, _, fs in os.walk(r) for f in fs if not f.startswith("._") and (f == new or os.path.splitext(f)[0] == new)]
    if len(hits) == 1: return hits[0]
    sys.exit(("no sound named " if not hits else "several sounds named ") + new + "".join("\n  " + x for x in hits[:8]))

def cmd_sfx(A, args):
    pos = [a for a in args if not a.startswith("--")]
    if "--db" in args: pos = [a for a in pos if a != args[args.index("--db") + 1]]
    if len(pos) < 2: sys.exit("usage: beats.py sfx <edit> <beat#> list | swap <old> <new>")
    beats = load_beats(A); b = pick(beats, [int(pos[0])])[0]; sub = pos[1]; bd = A.beats_dir
    if sub == "list":
        print(f"beat {b['id']} {fmt_t(b['t0'])}-{fmt_t(b['t1'])}  music {b['music']}  words: {(b['ob_words'] or b['her_words'])[:70]}")
        for i, s in enumerate(b["sfx"], 1): print(f"  [{i}] {s['name']}  family {s['fam']}  at {s['onset']:.2f}s  {s['db']} dB")
        if not b["sfx"]: print("  (no sounds in this beat)")
        print("\nfamilies this engine uses:")
        for fam, fs in A.families().items(): print(f"  {fam}: " + ", ".join(os.path.basename(f) for f in fs))
        print("\navailable (folder (count): files):")
        for d, fs in sfx_catalog().items():
            shown = fs if "--all" in args else fs[:6]; print(f"  {d} ({len(fs)}): " + ", ".join(shown) + (" ..." if len(shown) < len(fs) else ""))
        return
    if sub != "swap" or len(pos) < 4: sys.exit("usage: beats.py sfx <edit> <beat#> swap <old> <new>")
    old, new = pos[2], pos[3]; cand = b["sfx"]
    hit = [cand[int(old) - 1]] if old.isdigit() and 0 < int(old) <= len(cand) else [s for s in cand if old in (s["name"], s["file"], s["fam"])]
    if len(hit) != 1: sys.exit(f"'{old}' matches {len(hit)} sounds in beat {b['id']}: " + ", ".join(f"[{i}] {s['name']}" for i, s in enumerate(cand, 1)))
    s = hit[0]; newp = resolve_new(new); p = os.path.join(bd, "sfx_overrides.json"); o = jload(p, {"swaps": []})
    # beats.json lists the plan as it was at map time; the override is keyed on the BASE plan's file, so a second swap of the same sound replaces the first
    sw = dict(t=s["t"], old=s.get("base", s["file"]), new=newp, beat=b["id"], was=s["name"])
    if "--db" in args: sw["db"] = float(args[args.index("--db") + 1])
    o["swaps"] = [x for x in o["swaps"] if not (abs(x["t"] - s["t"]) < 0.0015 and x["old"] == sw["old"])] + [sw]; jsave(p, o)
    print(f"beat {b['id']}: {s['name']} -> {os.path.basename(newp)} at {s['onset']:.2f}s  (override saved in {p})")
    st = jload(os.path.join(bd, "state.json"), {}); T0 = time.time(); wav, remix = ensure_mix(A, st); t_a = time.time() - T0
    out = os.path.join(bd, "out", "current.mp4"); os.makedirs(os.path.dirname(out), exist_ok=True); src = out if os.path.exists(out) else A.final_path()
    if os.path.exists(out): src = move_aside(out, os.path.join(bd, "aside", time.strftime("%Y%m%d-%H%M%S")))
    tm = time.time()
    if hasattr(A, "mux_audio"): A.mux_audio(src, wav, out)      # long-form: loudnorm to -14 LUFS and the colour tags, picture still copied
    else:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                        "-movflags", "+faststart", "-shortest", out], check=True)
    jsave(os.path.join(bd, "state.json"), st)
    print(f"audio only: remix {t_a:.1f}s + mux {time.time() - tm:.1f}s (video stream copied from {src}) -> {out}")
    if "--gate" in args: print("GATE:", "PASS" if A.gate(out) else "NOT PASS")
    else: print("(gate not run: add --gate, or run the engine's gate before delivering)")

def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"): print(__doc__); return
    if argv[1] == "adapters":
        for f in sorted(glob.glob(os.path.join(ADAPTERS, "*.py"))): print(os.path.basename(f)[:-3])
        return
    if len(argv) < 3: sys.exit("usage: beats.py map|redo|sfx <edit> ...")
    cmd, edit = argv[1], argv[2]; rest = list(argv[3:]); bdir = None
    if "--dir" in rest: i = rest.index("--dir"); bdir = os.path.abspath(rest[i + 1]); del rest[i:i + 2]
    A = load_adapter(edit, bdir)
    own = getattr(A, "cmd_" + cmd, None)      # an adapter can own a command (long-form: map, redo, build, check work on per-chapter segment encodes, not a frame cache)
    if own: return own(rest)
    {"map": cmd_map, "redo": cmd_redo, "sfx": cmd_sfx}.get(cmd, lambda *a: sys.exit(f"unknown command {cmd}"))(A, rest)

if __name__ == "__main__": main(sys.argv)
