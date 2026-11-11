#!/usr/bin/env python3
"""Does every tool the editor skills lean on still work on this Mac? One table, PASS / WARN / FAIL, in about a minute.

  python3 -I ~/ob-editor/bin/doctor.py [--quick] [--brew] [--json]        (~/ob-editor/bin/doctor.sh runs the same)

Built 2026-11-03 for the move to the Mac mini (M5 Pro, 18 cores, 64 GB, macOS 27; OB: "make sure the skills are
working and upgrade anything needed with new setup"). Run it after any Homebrew upgrade, macOS update or migration.
The traps it watches for were all real on 11-03 (memory reference_mac_mini_setup_2026_11_03):
  - brew relinked `python3` to python@3.15, which has none of OB's packages, so every script broke
  - `yt-dlp` was a pip shim that a pip upgrade broke; it must resolve to the brew Cellar
  - a skill pointing at a script or model that no longer exists
Every check is a real run (encode a second of HEVC on the media engine, Vision on a fixture frame, on-device speech
and whisper on a spoken test line), not just "the file exists". The short-form tab's toolbox smoke test (doctor.sh,
11-03) is folded in: the person_mask_dir matte, an x264 + AudioToolbox AAC encode, a real Puppeteer launch, the gate's
planted-mistake selftest (lip sync too), react_window_audit's selftest, the /watch preflight, earshot and `brew outdated`.
--quick skips the slow ones (the two selftests and brew, ~10 s left). --brew adds `brew doctor`'s Command Line Tools warning.
Report: ~/ob-editor/qc/doctor/<date>.json. Exit 1 on any FAIL.
"""
import ast, glob, importlib.util, json, os, plistlib, re, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

HOME, ED = os.path.expanduser("~"), os.path.expanduser("~/ob-editor")
BIN = f"{ED}/bin"
VENVS = {"OpenMontage": f"{HOME}/OpenMontage/.venv/bin/python", "ob-youtube google": f"{HOME}/ob-youtube/.venv-google/bin/python",
         "earshot": f"{ED}/venvs/earshot/bin/python"}
MODELS = {"base.en": 140e6, "medium.en": 1.4e9, "large-v3-turbo": 1.5e9}   # whisper.cpp ggml files, rough minimum sizes


def sh(cmd, timeout=60, **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw); return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired: return -9, "", f"timed out after {timeout} s"
    except FileNotFoundError as e: return -2, "", str(e)


# ---------------------------------------------------------------------------------------------------- the checks
def c_machine():
    _, chip, _ = sh(["sysctl", "-n", "machdep.cpu.brand_string"]); _, ram, _ = sh(["sysctl", "-n", "hw.memsize"])
    _, ver, _ = sh(["sw_vers", "-productVersion"]); _, lvl, _ = sh(["sysctl", "-n", "kern.memorystatus_level"])
    free = int(lvl.strip() or 100)
    return ("WARN" if free < 20 else "PASS"), f"{chip.strip()}, {os.cpu_count()} cores, {int(ram) / 2 ** 30:.0f} GB, macOS {ver.strip()}, memory {free}% free"


def c_disks():
    out, bad = [], "PASS"
    for p, need in (("/", 100), ("/Volumes/T7", 60), ("/Volumes/OB-ARCHIVE", 20), ("/Volumes/OB-HEALTH", 20)):
        if not os.path.ismount(p): out.append(f"{p} NOT MOUNTED"); bad = "FAIL" if p in ("/", "/Volumes/T7") else ("WARN" if bad == "PASS" else bad); continue
        st = os.statvfs(p); g = st.f_bavail * st.f_frsize / 1e9; out.append(f"{'internal' if p == '/' else p[9:]} {g:.0f} GB free")
        if g < need and bad == "PASS": bad = "WARN"
    _, fs, _ = sh(["diskutil", "info", "/Volumes/T7"]); m = re.search(r"File System Personality:\s+(\S+)", fs)
    if m: out.append(f"T7 is {m.group(1)}" + (" (slow with many small files: frame temp belongs on the internal SSD)" if m.group(1) == "ExFAT" else ""))
    return bad, "; ".join(out)


def c_python():
    exe = shutil.which("python3") or ""; real = os.path.realpath(exe)
    _, v, _ = sh([exe, "--version"]); v = v.strip()
    if not real.startswith("/opt/homebrew/"):   # 11-03: python@3.14 3.14.10's keg ships only python3.14, so python3 fell back to /usr/bin (3.9.6)
        return "FAIL", (f"python3 is {real} ({v}), not Homebrew's 3.14: OB's packages live there. Fix: "
                        "ln -sf ../opt/python@3.14/bin/python3.14 /opt/homebrew/bin/python3 (and pip3 -> pip3.14)")
    if "3.14" not in v:
        return "FAIL", (f"{v} at {real}: brew relinked python3 (OB's packages live in 3.14). Fix: brew unlink python@3.15; "
                        "brew unlink python@3.14 && brew link python@3.14")
    code, _, err = sh([exe, "-I", "-c", "import numpy, scipy, PIL; from PIL import features; assert features.check('freetype2'); import numpy as n; print(n.__version__)"])
    if code: return "FAIL", f"{v}: numpy/scipy/PIL import failed: {err.strip()[-200:]}"
    return "PASS", f"{v} ({real.split('/Cellar/')[-1] if '/Cellar/' in real else real}), numpy + scipy + PIL with FreeType"


def bin_scripts():
    return sorted(p for p in glob.glob(f"{BIN}/*.py"))


def c_compile():
    bad = []
    for p in bin_scripts():
        try: compile(open(p, encoding="utf-8").read(), p, "exec")
        except SyntaxError as e: bad.append(f"{os.path.basename(p)}:{e.lineno} {e.msg}")
    return ("FAIL", f"{len(bad)} scripts don't compile: " + "; ".join(bad[:6])) if bad else ("PASS", f"all {len(bin_scripts())} scripts in bin/ compile")


def c_imports():
    """Third-party modules the bin/ scripts import that system python3 can't. Fine when a venv has them (the script runs
    with that venv's python); FAIL when nothing on this Mac has them."""
    local = {os.path.basename(p)[:-3] for p in bin_scripts()} | {os.path.basename(p) for p in glob.glob(f"{BIN}/*") if os.path.isdir(p)}
    users = {}
    for p in bin_scripts():
        try: tree = ast.parse(open(p, encoding="utf-8").read())
        except SyntaxError: continue
        for n in ast.walk(tree):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) and n.module and not n.level else []
            for m in names:
                top = m.split(".")[0]
                if top and top not in sys.stdlib_module_names and top not in local: users.setdefault(top, set()).add(os.path.basename(p))
    code_dirs = [BIN, f"{HOME}/ob-youtube", f"{HOME}/ob-clipper/bin", f"{HOME}/ob-brain"]   # scripts add these (and project dirs) to sys.path
    here = lambda m: any(os.path.exists(f"{d}/{m}.py") for d in code_dirs) or glob.glob(f"/Volumes/T7/OB-EDITS/*/{m}.py") or \
        glob.glob(f"/Volumes/T7/OB-EDITS/*/*/{m}.py") or glob.glob(f"/Volumes/T7/OB-EDITS/*/*/*/{m}.py")
    missing = sorted(m for m in users if importlib.util.find_spec(m) is None and not here(m))
    where, nowhere = {}, []
    for m in missing:
        hit = [k for k, py in VENVS.items() if os.path.exists(py) and sh([py, "-c", f"import importlib.util,sys; sys.exit(importlib.util.find_spec('{m}') is None)"], 30)[0] == 0]
        (where.setdefault(", ".join(hit), []).append(m) if hit else nowhere.append(m))
    txt = "; ".join(f"{', '.join(v)} via {k}" for k, v in where.items())
    if nowhere: return "FAIL", f"no python here has {', '.join(nowhere)} (used by {', '.join(sorted(set().union(*(users[m] for m in nowhere))))[:200]})" + (f"; {txt}" if txt else "")
    return "PASS", (f"python3 has every module; venv-only: {txt}" if txt else "python3 has every module")


def c_ffmpeg():
    _, v, _ = sh(["ffmpeg", "-hide_banner", "-version"]); ver = v.split("\n")[0].replace("ffmpeg version ", "").split(" ")[0]
    _, enc, _ = sh(["ffmpeg", "-hide_banner", "-encoders"]); _, flt, _ = sh(["ffmpeg", "-hide_banner", "-filters"])
    miss = [e for e in ("hevc_videotoolbox", "h264_videotoolbox", "prores_videotoolbox") if e not in enc]
    miss += [f for f in ("haldclut", "lut3d", "loudnorm", "ebur128", "agate", "xfade", "libvmaf") if not re.search(rf"\s{f}\s", flt)]
    code, _, err = sh(["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30000/1001", "-t", "2",
                       "-c:v", "hevc_videotoolbox", "-b:v", "24M", "-tag:v", "hvc1", "-f", "null", "-"])
    if code: return "FAIL", f"ffmpeg {ver}: the HEVC media-engine encode failed: {err.strip()[-200:]}"
    return ("WARN" if miss else "PASS"), f"ffmpeg {ver}, HEVC + H.264 + ProRes on the media engine (test encode ok), haldclut/loudnorm/vmaf" + (f"; missing: {', '.join(miss)}" if miss else "")


def c_ffmpeg_full():
    f = f"{BIN}/ffmpeg-full"
    if not os.path.exists(f): return "WARN", "bin/ffmpeg-full missing (styled .ass captions, drawtext, rubberband)"
    code, v, err = sh([f, "-hide_banner", "-version"])
    if code: return "FAIL", f"ffmpeg-full won't run: {err.strip()[-200:]}"
    _, flt, _ = sh([f, "-hide_banner", "-filters"]); miss = [x for x in ("subtitles", "ass", "drawtext", "rubberband") if not re.search(rf"\s{x}\s", flt)]
    return ("WARN" if miss else "PASS"), v.split("\n")[0].replace("ffmpeg version ", "ffmpeg-full ").split(" Copyright")[0] + (f"; missing {', '.join(miss)}" if miss else "; libass, drawtext, rubberband")


def c_ytdlp():
    exe = shutil.which("yt-dlp")
    if not exe: return "FAIL", "yt-dlp not on PATH (brew install yt-dlp)"
    real = os.path.realpath(exe); code, v, err = sh([exe, "--version"])
    if code: return "FAIL", f"yt-dlp won't run ({err.strip()[-160:]}); reinstall with brew, never pip"
    if "/Cellar/yt-dlp/" not in real: return "WARN", f"yt-dlp {v.strip()} is not the brew build ({real}); a pip upgrade broke the shim on 11-03"
    return "PASS", f"yt-dlp {v.strip()} (brew)"


def c_node():
    _, nv, _ = sh(["node", "--version"]); pk = lambda n: json.load(open(f"{ED}/node_modules/{n}/package.json"))["version"] if os.path.exists(f"{ED}/node_modules/{n}/package.json") else None
    hf, pp = pk("hyperframes"), pk("puppeteer")
    chrome = glob.glob(f"{HOME}/.cache/hyperframes/chrome/chrome-headless-shell/*/chrome-headless-shell-mac-arm64/chrome-headless-shell")
    bad = [x for x, ok in (("hyperframes", hf), ("puppeteer", pp), ("HyperFrames' Chrome", chrome)) if not ok]
    return ("FAIL" if bad else "PASS"), f"node {nv.strip()}, hyperframes {hf}, puppeteer {pp}, Chrome {os.path.basename(os.path.dirname(os.path.dirname(chrome[0]))) if chrome else 'missing'}" + (f"; missing {', '.join(bad)}" if bad else "")


def c_venvs():
    tests = {"OpenMontage": "import cv2, numpy; cv2.TrackerCSRT.create if hasattr(cv2, 'TrackerCSRT') else cv2.TrackerCSRT_create; print(cv2.__version__)",
             "ob-youtube google": "import googleapiclient, google_auth_oauthlib; print('ok')", "earshot": "print('ok')"}
    out, st = [], "PASS"
    for k, py in VENVS.items():
        if not os.path.exists(py): out.append(f"{k}: missing"); st = "WARN" if st == "PASS" else st; continue
        code, o, e = sh([py, "-c", tests[k]], 60)
        if code: out.append(f"{k}: BROKEN ({(e.strip().splitlines() or ['?'])[-1][:90]})"); st = "FAIL"
        else: out.append(f"{k} ok" + (f" (OpenCV {o.strip()})" if k == "OpenMontage" else ""))
    return st, "; ".join(out)


def c_fonts():
    f = f"{ED}/fonts/BigShoulders/BigShouldersDisplay[wght].ttf"
    code, o, e = sh([shutil.which("python3"), "-I", "-c", f"from PIL import ImageFont; t = ImageFont.truetype({f!r}, 40); "
                     "n = [x.decode() if isinstance(x, bytes) else x for x in t.get_variation_names()]; print(','.join(n))"])
    if code: return "FAIL", f"the brand font won't load: {e.strip()[-160:]}"
    need = [x for x in ("Black", "ExtraBold") if x not in o]
    return ("FAIL" if need else "PASS"), f"Big Shoulders Display loads ({o.strip()})" + (f"; missing {need}" if need else "")


def c_launchagents():
    _, lst, _ = sh(["launchctl", "list"]); loaded = {l.split("\t")[2]: l.split("\t")[1] for l in lst.splitlines()[1:] if l.count("\t") >= 2}
    on, off, failed = [], [], []
    for p in sorted(glob.glob(f"{HOME}/Library/LaunchAgents/com.obhealth.*.plist")):
        lab = os.path.basename(p)[:-6]
        try: dis = plistlib.load(open(p, "rb")).get("Disabled", False)
        except Exception: dis = False
        if lab in loaded: on.append(lab[13:]); failed += [f"{lab[13:]} (last exit {loaded[lab]})"] if loaded[lab] not in ("0", "-") else []
        elif not dis: off.append(lab[13:])
    st = "WARN" if (off or failed) else "PASS"
    return st, f"loaded: {', '.join(on)}" + (f"; NOT loaded: {', '.join(off)}" if off else "") + (f"; last run failed: {', '.join(failed)}" if failed else "")


def c_skills():
    """Paths in the skills' instructions (~/..., /Users/...) that don't exist: a skill that would send Claude to a missing tool."""
    miss = {}
    for md in glob.glob(f"{HOME}/.claude/skills/*/SKILL.md"):
        sk = md.split("/")[-2]
        for raw in re.findall(r"(?:~|/Users/YOU)/[\w.@{},\[\]/+<>-]+", open(md, encoding="utf-8", errors="ignore").read()):
            p = raw.rstrip(".,)]:;").replace("/Users/YOU", "~")
            if re.search(r"[<>*]|WORK|NAME|YYYY|\bOUT\b|\{\}", p) or p.count("/") < 2 or p.endswith(("-", "_")): continue
            m = re.search(r"\{([^}]+)\}", p)
            for x in ([p[:m.start()] + alt + p[m.end():] for alt in m.group(1).split(",")] if m else [p]):
                full = os.path.expanduser(x)
                if not os.path.exists(full) and not glob.glob(full) and os.path.splitext(full)[1] in (".py", ".sh", ".js", ".bin", ".md", ".json", ".swift", ".ttf", ".html", ""):
                    if os.path.splitext(full)[1] == "" and not full.startswith((BIN, f"{ED}/presets", f"{HOME}/ob-")): continue
                    miss.setdefault(sk, set()).add(x)
    if not miss: return "PASS", f"every tool path in {len(glob.glob(f'{HOME}/.claude/skills/*/SKILL.md'))} skills exists"
    return "WARN", "; ".join(f"{k}: {', '.join(sorted(v)[:4])}" + (f" +{len(v) - 4}" if len(v) > 4 else "") for k, v in sorted(miss.items()))


def c_gate():
    code, o, e = sh([shutil.which("python3"), "-I", f"{BIN}/qc_gate.py", "--rules"], 60)
    d = json.load(open(f"{ED}/qc/mistakes.json")) if os.path.exists(f"{ED}/qc/mistakes.json") else []
    n = len(d.get("mistakes", []) if isinstance(d, dict) else d)
    return ("FAIL", f"qc_gate.py --rules failed: {(e or o).strip()[-200:]}") if code else ("PASS", f"qc_gate loads, {n} never-again rules")


def c_selftest():
    code, o, e = sh([shutil.which("python3"), "-I", f"{BIN}/qc_gate.py", "--selftest"], 1800)
    if code == 0: return "PASS", f"qc_gate --selftest: every planted mistake still caught ({sum(1 for l in o.splitlines() if l.startswith('  ok '))} checks, lip sync too)"
    bad = [" ".join(l.split()[1:4]) for l in (o + e).splitlines() if l.strip().startswith("BAD")]
    if bad and all(" edges " in f" {b} " for b in bad):   # the edges check reads Apple's word edges: a busy Neural Engine refuses speech
        return "WARN", f"qc_gate --selftest: only the edges check misses ({'; '.join(bad)[:120]}). It needs Apple speech; if on-device speech is busy, rerun after the Vision job"
    return "FAIL", f"qc_gate --selftest: {'; '.join(bad)[:200] or (o + e).strip()[-160:]}"


def c_slots():
    code, o, e = sh([shutil.which("python3"), "-I", f"{BIN}/render_slots.py", "list"])
    return ("FAIL", e.strip()[-200:]) if code else ("PASS", o.strip().splitlines()[0])


def c_brew():
    code, o, e = sh(["brew", "doctor"], 300); txt = o + e
    m = re.search(r"(Your Command Line Tools[^\n]*(?:\n[^\n]+){0,2})", txt)
    return ("WARN", "brew doctor: " + " ".join(m.group(1).split())[:260]) if m else ("PASS" if code == 0 else "WARN", "brew doctor: " + (" ".join(txt.split())[:200] or "ready to brew"))


def c_yt_auth():
    """The YouTube Analytics sign-in the editor brief's retention pulls need (a 7-day testing token; OB signs in himself)."""
    py, tool = f"{HOME}/ob-youtube/.venv-google/bin/python", f"{HOME}/ob-youtube/yt_analytics.py"
    if not (os.path.exists(py) and os.path.exists(tool)): return "WARN", "ob-youtube analytics tool missing"
    code, o, e = sh([py, tool, "check"], 60); txt = " ".join((o + e).split())
    if code == 0: return "PASS", f"YouTube Analytics signed in ({txt[:80]})"
    return "WARN", ("YouTube Analytics sign-in expired: OB runs `~/ob-youtube/.venv-google/bin/python ~/ob-youtube/yt_analytics.py auth` "
                    "and signs in (retention pulls need it)") if "expired" in txt or "auth" in txt else f"yt_analytics check: {txt[:160]}"


def c_x264():
    """The short-form encode path: libx264 + AudioToolbox AAC (doctor.sh, 11-03)."""
    with tempfile.TemporaryDirectory() as td:
        code, _, e = sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30000/1001:d=1", "-f", "lavfi",
                         "-i", "sine=f=440:d=1:sample_rate=48000", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac_at", "-b:a", "192k", f"{td}/t.mp4"])
    return ("FAIL", f"libx264 + aac_at encode failed: {e.strip()[-160:]}") if code else ("PASS", "libx264 + AudioToolbox AAC encode a 9:16 second")


def c_puppeteer():
    code, o, e = sh(["node", "-e", "const p=require('puppeteer');(async()=>{const b=await p.launch({headless:'shell'});await b.close()})()"
                     ".catch(e=>{console.error(e.message);process.exit(1)})"], 90, cwd=ED)
    return ("FAIL", f"Puppeteer can't launch Chrome: {(e or o).strip()[-160:]}") if code else ("PASS", "Puppeteer launches headless Chrome")


def c_react_audit():
    if not os.path.ismount("/Volumes/T7"): return "WARN", "react_window_audit selftest needs the T7 (its fixtures are the 10-31 takes)"
    code, o, e = sh([shutil.which("python3"), "-I", f"{BIN}/react_window_audit.py", "--selftest"], 600)
    return ("FAIL", f"react_window_audit --selftest: {(o + e).strip()[-160:]}") if code else ("PASS", "react_window_audit selftest (watch windows)")


def c_watch():
    code, o, e = sh([sys.executable, f"{HOME}/.claude/skills/watch/scripts/setup.py", "--check"], 60)
    why = {2: "ffmpeg/ffprobe/yt-dlp missing", 3: "no Whisper key on a first run", 4: "binaries and key missing"}.get(code, (o + e).strip()[-120:])
    return ("PASS", "/watch preflight") if code == 0 else ("FAIL", f"/watch preflight: {why} (run its setup.py)")


def c_earshot():
    code, o, e = sh([f"{BIN}/earshot", "doctor"], 120)
    if code: return "FAIL", f"earshot doctor: {(o + e).strip()[-160:]}"
    return ("PASS", "earshot (SFX search) ready, offline") if "problems: []" in o else ("WARN", "earshot: " + " ".join(o.split())[:160])


def c_brew_outdated():
    """Pending updates of the formulas the editor runs on. ffmpeg 9 and node 26 are major jumps held on purpose (11-03): update
    those only between renders and run this again after; patch updates (python@3.14, uv, yt-dlp) are safe."""
    code, o, e = sh(["brew", "outdated", "--verbose"], 180)
    if "brew migrate" in o + e:   # 11-03: Homebrew renamed whisper-cpp to whisper.cpp; outdated errors until it is migrated
        m = re.search(r"brew migrate [\w.@-]+", o + e)
        return "WARN", f"Homebrew renamed a formula; run `{m.group(0) if m else 'brew migrate'}` between renders (it relinks whisper-cli), then this again"
    if code: return "WARN", f"brew outdated failed: {(e or o).strip()[-120:]}"
    keys = ("ffmpeg", "yt-dlp", "whisper-cpp", "node", "python@3", "uv")
    rows = [l.split(" (")[0] + " " + l.split("< ")[-1].strip() if "< " in l else l for l in o.splitlines() if l.startswith(keys)]
    return "PASS", ("up to date" if not rows else "pending: " + "; ".join(rows)[:220] + " (ffmpeg 9 and node 26 held on purpose)")


def c_scratch():
    d = f"{HOME}/ob-scratch"
    if not os.path.isdir(d): return "PASS", "no render scratch yet (~/ob-scratch)"
    _, o, _ = sh(["du", "-sk", d]); kb = int(o.split()[0]) if o else 0
    return ("WARN" if kb > 300e6 else "PASS"), f"~/ob-scratch holds {kb / 1e6:.1f} GB (render caches; safe to clear a finished project's folder)"


# ------------------------------------------------------------------------------------- checks that need test media
def media(tmp):
    """A fixture frame of OB (qc/regress/face.mp4) and a spoken test line (macOS `say`), made once for the media checks."""
    fr, wav = f"{tmp}/frame.jpg", f"{tmp}/line.wav"
    sh(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", "1", "-i", f"{ED}/qc/regress/face.mp4", "-frames:v", "1", fr])
    sh(["say", "-o", f"{tmp}/line.aiff", "testing one two three, the editor is ready"])
    sh(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", f"{tmp}/line.aiff", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav])
    return fr, wav


def c_vision(fr):
    if not os.path.exists(fr): return "FAIL", "could not make the fixture frame (qc/regress/face.mp4)"
    out, bad = [], []
    for b, args, ok in (("faces", [fr], lambda o: len(o.split()) >= 5), ("frame_obstacles", [fr], lambda o: '"faces":[[' in o),
                        ("vision_boxes", [fr], lambda o: '"humans":[[' in o), ("gaze", [fr], lambda o: len(o.split()) >= 5),
                        ("face_quality", [fr], lambda o: '"nf":1' in o), ("person_extent", [fr], lambda o: '"right"' in o),
                        ("person_mask", [fr, fr + ".mask.png"], lambda o: "mask" in o)):
        code, o, e = sh([f"{BIN}/{b}"] + args, 60)
        (out if code == 0 and ok(o) else bad).append(b)
    d_in, d_out = fr + ".in", fr + ".masks"; os.makedirs(d_in, exist_ok=True); os.makedirs(d_out, exist_ok=True)
    sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", fr, f"{d_in}/frame.png"])   # it reads PNGs only
    code, o, e = sh([f"{BIN}/person_mask_dir", d_in, d_out], 120)   # the FDOE cutouts' batch matte (doctor.sh, 11-03)
    (out if code == 0 and glob.glob(f"{d_out}/*.png") else bad).append("person_mask_dir")
    return ("FAIL" if bad else "PASS"), f"Apple Vision on a frame of OB: {len(out)} of {len(out) + len(bad)} helpers work" + (f"; broken: {', '.join(bad)}" if bad else "")


def c_speech(wav):
    code, o, e = sh([f"{BIN}/speech_words", "check"]); ok = "asset status: installed" in (o + e)
    code2, o2, e2 = sh([f"{BIN}/speech_words", "words", wav], 60)
    words = re.findall(r'"w":"([^"]+)"', o2 + e2); heard = " ".join(words).lower()
    good = ok and "testing" in heard and "three" in heard
    if not good and re.search(r"ANE|Espresso|inference plan", e2):   # 11-03: another job holds a big model on the Neural Engine
        return "WARN", ("Neural Engine busy: Apple speech can't load while another job holds a big Vision model (an FDOE cutout batch's "
                        "person_mask_dir). Until it ends, takes.py, zero_dead and the gate's Apple cues and edges fail; whisper still works")
    return ("PASS" if good else "FAIL"), (f"on-device speech (en-US installed) heard \"{' '.join(words)[:60]}\"" if good else
                                          f"speech_words: check={'ok' if ok else (o + e).strip()[:120]}, heard \"{heard[:60]}\"")


def c_whisper(wav):
    exe = shutil.which("whisper-cli")
    if not exe: return "FAIL", "whisper-cli not on PATH (brew install whisper-cpp)"
    have = {k: os.path.getsize(f"{HOME}/.whisper-models/ggml-{k}.bin") for k in MODELS if os.path.exists(f"{HOME}/.whisper-models/ggml-{k}.bin")}
    short = [k for k in MODELS if have.get(k, 0) < MODELS[k]]
    t0 = time.time(); code, o, e = sh([exe, "-m", f"{HOME}/.whisper-models/ggml-medium.en.bin", "-f", wav, "-nt", "-np"], 120); dt = time.time() - t0
    metal = bool(re.search(r"metal|MTL", e, re.I)) or code == 0 and "using cpu" not in e.lower()
    heard = " ".join(o.split()).lower()
    if code or "testing" not in heard: return "FAIL", f"whisper medium.en failed or heard nothing: {(e or o).strip()[-160:]}"
    return ("WARN" if short else "PASS"), (f"whisper medium.en {dt:.1f} s on a 3 s line ({'Metal' if metal else 'CPU only'}); models: "
                                           f"{', '.join(f'{k} {v / 1e9:.1f} GB' for k, v in have.items())}" + (f"; missing {', '.join(short)}" if short else ""))


def main():
    a = sys.argv[1:]
    checks = [("machine", c_machine), ("disks", c_disks), ("python3", c_python), ("scripts compile", c_compile),
              ("script imports", c_imports), ("ffmpeg", c_ffmpeg), ("ffmpeg-full", c_ffmpeg_full), ("yt-dlp", c_ytdlp),
              ("node + HyperFrames", c_node), ("venvs", c_venvs), ("brand font", c_fonts), ("LaunchAgents", c_launchagents),
              ("skill paths", c_skills), ("qc_gate", c_gate), ("render slots", c_slots), ("render scratch", c_scratch), ("YouTube sign-in", c_yt_auth)]
    checks += [("x264 + AAC", c_x264), ("Puppeteer", c_puppeteer), ("/watch preflight", c_watch), ("earshot", c_earshot)]
    if "--quick" not in a: checks += [("gate selftest", c_selftest), ("react_window_audit", c_react_audit), ("brew updates", c_brew_outdated)]
    if "--brew" in a: checks.append(("brew doctor", c_brew))
    tmp = tempfile.mkdtemp(prefix="ob-doctor-"); t0 = time.time()
    try:
        fr, wav = media(tmp)
        checks += [("Apple Vision", lambda: c_vision(fr)), ("on-device speech", lambda: c_speech(wav)), ("whisper", lambda: c_whisper(wav))]
        def safe(f):
            try: return f()
            except Exception as e: return "FAIL", f"check crashed: {e!r}"[:240]
        with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda kv: (kv[0], *safe(kv[1])), checks))
    finally: shutil.rmtree(tmp, ignore_errors=True)
    if "--json" in a: print(json.dumps(res, indent=1))
    else:
        for k, st, why in res: print(f"{st:4}  {k:18}  {why}")
        n = {s: sum(1 for _, x, _ in res if x == s) for s in ("PASS", "WARN", "FAIL")}
        print(f"\n{n['PASS']} pass, {n['WARN']} warn, {n['FAIL']} fail in {time.time() - t0:.0f} s")
    os.makedirs(f"{ED}/qc/doctor", exist_ok=True)
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M"), "checks": res}, open(f"{ED}/qc/doctor/{time.strftime('%Y-%m-%d')}.json", "w"), indent=1)
    sys.exit(1 if any(st == "FAIL" for _, st, _ in res) else 0)


if __name__ == "__main__":
    main()
