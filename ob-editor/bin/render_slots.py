#!/usr/bin/env python3
"""How many heavy jobs (renders, 4K frame work) run on this Mac right now, and whether one more can start.

  python3 -I render_slots.py list | count | busy | wait [--max N]

It counts JOBS, not processes. One react_render.py with its HyperFrames children (npm exec, node, Chrome) is one job;
the 11-03 `pgrep | wc -l` busy() lines read a single graphics render as 3 of the 3 allowed. A job is a heavy process
with no heavy ancestor. Wrapper shells (`sh -c`, the `zsh -c` of a tool call) are never jobs, and the caller, its
ancestors and its children are left out.

The limit is OB_MAX_RENDERS, else set by the machine: 3 on the Mac mini (M5 Pro, 64 GB, 18 cores, since 2026-11-03),
2 from 16 GB, 1 below that (the 8 GB Air crashed with two renders on 10-16 and again on 11-01). Memory under pressure
(macOS free level under 15%) counts as full whatever the count.

`busy` exits 0 when there is no room and 1 when a job can start, so a queue script's line is
  busy() { python3 -I "$HOME/ob-editor/bin/render_slots.py" busy; }
From Python: `import render_slots; render_slots.wait_free(log=print)`.
"""
import os, re, subprocess, sys, time

HEAVY = re.compile(r"assemble\.py|react_render\.py|lecture_render\.py|tier_render\.py|brand_react_render\.py|render_clip\.py|"
                   r"trial_variants\.py render|ytclip\.py render|hyperframes render|render_final\.sh|run_feed\.sh|feed_render\.py|"
                   r"tenten\d*_?\w*\.py (render|prep)|c4\d\d\d\w*\.py (render|prep)|wordsafe_\w+\.py (render|prep)|"
                   r"moves\.py (kick|counter|comments)|thumb_frames\.py")
ENCODE = re.compile(r"-c:v (libx26[45]|h264_videotoolbox|hevc_videotoolbox|prores\w*)")   # an ffmpeg video encode
SHELL = re.compile(r"(\S*/)?(z|ba|da)?sh -\w*c ")


def machine():
    ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout or 0) / 2 ** 30
    return ram, os.cpu_count() or 1


def limit():
    if os.environ.get("OB_MAX_RENDERS"): return max(1, int(os.environ["OB_MAX_RENDERS"]))
    ram, cores = machine()
    return 3 if ram >= 48 and cores >= 12 else 2 if ram >= 16 else 1


def mem_free_pct():
    """macOS's own free-memory level (what `memory_pressure` prints as 'System-wide memory free percentage')."""
    r = subprocess.run(["sysctl", "-n", "kern.memorystatus_level"], capture_output=True, text=True).stdout.strip()
    return int(r) if r.isdigit() else 100


def jobs(me=None):
    """[(pid, command)] of the heavy jobs running now, outside the caller's own process tree."""
    rows = {}
    for l in subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout.splitlines():
        p = l.split(None, 2)
        if len(p) == 3: rows[int(p[0])] = (int(p[1]), p[2])
    heavy = lambda c: not SHELL.match(c) and bool(HEAVY.search(c) or (re.match(r"\S*ffmpeg(-full)?\s", c) and ENCODE.search(c)))
    mine, p = set(), me or os.getpid()
    while p > 1 and p in rows: mine.add(p); p = rows[p][0]   # the caller and its ancestors
    kids = {me or os.getpid()}
    for _ in range(6): kids |= {q for q, (pp, _) in rows.items() if pp in kids}
    mine |= kids
    def top(q):   # no heavy ancestor: the job itself, not one of its children
        p = rows[q][0]
        while p > 1 and p in rows:
            if heavy(rows[p][1]): return False
            p = rows[p][0]
        return True
    return [(q, c) for q, (pp, c) in sorted(rows.items()) if q not in mine and heavy(c) and top(q)]


def busy(max_jobs=None):
    """(True/False, why): no room for another heavy job."""
    n, js, free = max_jobs or limit(), jobs(), mem_free_pct()
    if free < 15: return True, f"memory pressure: {free}% free"
    return len(js) >= n, f"{len(js)} of {n} render slots in use" + (f": {js[0][1][-90:]}" if js else "")


def wait_free(log=lambda m: print(m, flush=True), max_jobs=None, quiet=2, step=20):
    """Block until a job can start, seen on `quiet` polls in a row, `step` seconds apart."""
    said, ok = None, 0
    while ok < quiet:
        b, why = busy(max_jobs)
        if b:
            ok = 0
            if why != said: log(f"{time.strftime('%H:%M:%S')} waiting for a render slot: {why}"); said = why
        else: ok += 1
        if ok < quiet: time.sleep(step)


if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    mx = int(a[a.index("--max") + 1]) if "--max" in a else None
    me = os.getppid()   # run from a shell's busy(): leave that shell's own tree out
    if a[0] == "count": print(len(jobs(me)))
    elif a[0] == "busy":
        b, why = busy(mx); print(why, file=sys.stderr); sys.exit(0 if b else 1)
    elif a[0] == "wait": wait_free(max_jobs=mx)
    else:
        ram, cores = machine(); js = jobs(me)
        print(f"{len(js)} heavy job(s) running, limit {mx or limit()} ({ram:.0f} GB, {cores} cores), memory {mem_free_pct()}% free")
        for q, c in js: print(f"  {q}  {c[:160]}")
