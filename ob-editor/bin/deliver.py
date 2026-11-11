#!/usr/bin/env python3
"""The only way a video goes into one of OB's AirDrop folders (2026-10-28, OB: "Yes, wire it in" to: run the QC gate at the
end of every render so nothing that fails gets copied to my AirDrop folder).

For each file it takes the gate report the render already wrote (qc_gate.after_render), or runs the gate when there is no
fresh one, then:
  FAIL  nothing is copied. It prints the failing checks and exits 1.
  PASS  (or PASS with WARNs) it copies the file into the folder and byte-checks the copy. ONE file per edit (OB 11-03:
        "stop with so many variations, just one after editing now", ledger M45): a 720p phone copy only with --phone.
Every delivery (and every block) is logged in ~/ob-editor/qc/deliveries.log.

  python3 -I deliver.py FILE [FILE ...] --to "/Volumes/T7/OB-EDITS/AIRDROP <what> (<date>)" [--as "NAME.mp4"]
                        [--script SCRIPT] [--src CAMERA.MP4 --pieces PIECES.json] [--override "why"] [--phone] [--work WORK]
With a job (WORK/job.json from ob_job.py start; found from --work or the file's gate runs) it copies only when
qc_route.delivery_problems() is empty (an --override counts only with a matching WORK/qc/gate_overrides.json entry holding OB's
words or proof). Without a job it prints a LEGACY DELIVERY notice until formats.json enforce.legacy_until, then refuses.

--override "why" ships a FAIL anyway. Only for a check proven wrong on that file (the frame or time shown), and the gate is
fixed in the same session (the never-again loop), or when OB himself says ship it. The reason goes into the report and the
log. --as renames a single file in the folder.
"""
import datetime, json, os, shutil, subprocess, sys

BIN = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, BIN)
import qc_gate as Q

LOG = os.environ.get("OB_DELIVERIES_LOG") or os.path.join(Q.QC, "deliveries.log")


def _id(path):
    """11-10 rebuild: every log line carries the absolute source path, sha256 and size."""
    try:
        import qc_route; return f"\tsha256: {qc_route.sha256(path)}\tsize: {os.path.getsize(path)}"
    except Exception: return f"\tsize: {os.path.getsize(path)}"


def fresh_report(path):
    p = Q.report_path(path)
    if not os.path.exists(p): return None
    d = json.load(open(p))
    return d if abs(d.get("mtime", 0) - os.path.getmtime(path)) < 1e-3 else None   # the report is for this exact render


def preview(src, dst_dir, name):
    """A 720p copy under 28 MB for his phone (3 minutes or less)."""
    info = Q.probe(src); dur = float(info["format"]["duration"])
    if dur > 180: return None
    kbps = max(800, min(4000, int(27.5 * 8 * 1000 / dur) - 128))
    out = os.path.join(dst_dir, os.path.splitext(name)[0] + " (720p phone).mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-vf", "scale=720:-2", "-c:v", "libx264", "-preset", "medium",
                    "-b:v", f"{kbps}k", "-maxrate", f"{kbps * 5 // 4}k", "-bufsize", f"{kbps * 2}k", "-pix_fmt", "yuv420p",
                    "-c:a", "aac_at", "-b:a", "128k", "-movflags", "+faststart", out], check=True)
    return out


def recorded(path):
    """The raw pieces and the creators' own text spans the render recorded (qc_gate.record_pieces), if they belong to this
    exact file (same mtime)."""
    p = Q.pieces_path(path)
    if not os.path.exists(p): return {}
    d = json.load(open(p))
    return d if abs(d.get("mtime", 0) - os.path.getmtime(path)) < 1e-3 else {}


def deliver(path, to, name=None, script=None, src=None, pieces=None, override=None, make_preview=False, work=None):
    import qc_route as QR   # 11-10 rebuild: jobs (ob_job.py) deliver only with no problems; no job = LEGACY until enforce.legacy_until
    try: job, work = QR.find_job(path, work)
    except Exception: job = None
    J = job or {}; W = work if job else None; sfx = os.path.join(W, "story", "sfx_plan.json") if W else None
    d = fresh_report(path)
    if d is None or script or (src and pieces):
        # a fresh gate runs the same full checks as the render's own (11-04 C4417): re-gated without the recorded pieces, the
        # edge check only saw the file's two ends and the word check couldn't excuse a whisper slip it hears in the raw take,
        # so a cut that passed its render's gate was blocked here
        rec = recorded(path)
        R = Q.gate(path, script, None, pieces, src, segs=rec.get("pieces") or None, theirs=rec.get("theirs"), work=W, route=J.get("route"), job=job,
                   sfx_plan=sfx if sfx and os.path.exists(sfx) else None, music=(J.get("inputs") or {}).get("music"),
                   cards=Q.cover_spans(W) if W and os.path.exists(os.path.join(W, "events_resolved.json")) else None)   # T6: same inputs as the job
        ok = Q.show(path, R); Q.save(path, R, ok); d = fresh_report(path)
        Q._log_run(path, R, dict(script=script, work=W, pieces=pieces, src=src, segs=len(rec.get("pieces") or []), via="deliver.py"), job)
    else:
        print(f"QC gate (report from the render): {os.path.basename(path)} -> {d['result']}")
        for k, v in d["checks"].items():
            if v["status"] in ("FAIL", "WARN"): print(f"  {v['status']:4s} {k:9s} {v['detail'][:150]}")
    fails = [k for k, v in d["checks"].items() if v["status"] == "FAIL"]
    warns = [k for k, v in d["checks"].items() if v["status"] == "WARN"]
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    try: rep = QR.report(path, W, use_overrides=bool(override)); probs = rep["problems"]
    except Exception as e: rep, probs = {"overrides_used": []}, [f"route layer crashed: {e!r}"]
    if job and probs:
        open(LOG, "a").write(f"{stamp}\tBLOCKED\t{os.path.abspath(path)}\t-> {to}\tjob: {J.get('name')}\tproblems: {' | '.join(probs)}{_id(path)}\n")
        print(f"BLOCKED: {os.path.basename(path)} (job {J.get('name')}, route {J.get('route')}). Nothing copied. Fix each, then deliver again:")
        for i, pr in enumerate(probs, 1): print(f"  {i}. {pr}")
        return False
    if job: fails = []   # every FAIL left is overridden in WORK/qc/gate_overrides.json with OB's words or proof (logged below)
    elif not QR.legacy_open():
        open(LOG, "a").write(f"{stamp}\tREFUSED-LEGACY\t{os.path.abspath(path)}\t-> {to}{_id(path)}\n")
        print("REFUSED: no job for this file and legacy deliveries have ended. python3 -I ~/ob-editor/bin/ob_job.py start ROUTE WORK, then ob_job.py finish WORK FILE"); return False
    else:
        print("=" * 70 + f"\nLEGACY DELIVERY (no job; allowed until {QR.load()['enforce']['legacy_until']}). Under the new loop this file would be blocked by:\n"
              + "".join(f"  {i}. {pr}\n" for i, pr in enumerate(probs, 1)) + "New command: ob_job.py start ROUTE WORK ... ob_job.py finish WORK FILE\n" + "=" * 70)
        open(LOG, "a").write(f"{stamp}\tLEGACY\t{os.path.abspath(path)}\t-> {to}\tproblems: {len(probs)}{_id(path)}\n")
    for k, why in (rep.get("overrides_used") or []) if job else []:
        open(LOG, "a").write(f"{stamp}\tOVERRIDE-CHECK\t{os.path.abspath(path)}\tcheck: {k}\tgate_overrides.json: {why}{_id(path)}\n")
    if fails and not override:
        open(LOG, "a").write(f"{stamp}\tBLOCKED\t{os.path.abspath(path)}\t-> {to}\tfail: {','.join(fails)}{_id(path)}\n")
        print(f"BLOCKED: {os.path.basename(path)} failed {', '.join(fails)}. Nothing copied. Fix it and render again.")
        return False
    os.makedirs(to, exist_ok=True); dst = os.path.join(to, name or os.path.basename(path))
    shutil.copy2(path, dst)
    same = subprocess.run(["cmp", "-s", path, dst]).returncode == 0
    if not same: print(f"COPY FAILED (bytes differ): {dst}"); return False
    Q.copy_pieces(path, dst)   # a clip cut from the delivered copy later is still checked down to the raw take
    pv = preview(path, to, os.path.basename(dst)) if make_preview and os.path.getsize(path) > 30e6 else None
    if override:
        rp = Q.report_path(path); r = json.load(open(rp)); r["override"] = {"when": stamp, "why": override, "failed": fails}; json.dump(r, open(rp, "w"), indent=1)
    open(LOG, "a").write(f"{stamp}\t{'OVERRIDE' if override else 'DELIVERED'}\t{os.path.abspath(path)}\t-> {dst}\twarn: {','.join(warns) or '-'}"
                         + (f"\tfail: {','.join(fails)}\twhy: {override}" if override else "") + (f"\tpreview: {os.path.basename(pv)}" if pv else "") + _id(path) + "\n")
    print(f"{'OVERRIDE' if override else 'DELIVERED'}: {dst}" + (f"  + {os.path.basename(pv)} ({os.path.getsize(pv) / 1e6:.0f} MB)" if pv else "")
          + (f"  | answer in the note: {', '.join(warns)}" if warns else ""))
    return True


def main():
    a = sys.argv[1:]
    if not a or "--to" not in a: print(__doc__); sys.exit(2)
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    flags = {"--to", "--as", "--script", "--src", "--pieces", "--override", "--work"}
    files, k = [], 0
    while k < len(a):
        if a[k] in flags: k += 2; continue
        if a[k] in ("--no-preview", "--phone"): k += 1; continue
        files.append(a[k]); k += 1
    if opt("--as") and len(files) != 1: sys.exit("--as names one file")
    ok = [deliver(f, opt("--to"), opt("--as"), opt("--script"), opt("--src"), opt("--pieces"), opt("--override"), "--phone" in a, opt("--work")) for f in files]
    print(f"{sum(ok)} of {len(ok)} delivered")
    sys.exit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
