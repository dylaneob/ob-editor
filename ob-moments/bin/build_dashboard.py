#!/usr/bin/env python3
"""
build_dashboard.py: assembles the ob-moments review dashboard.

Scans work/*.moments.json (one per episode), pulls matching
work/<id>.advice.md (per-clip improvement notes) and video titles from
~/ob-social-dashboard/data/yt-meta/<id>.json, and writes a single
self-contained /Users/YOU/ob-moments/app/index.html with all
data embedded inline (no fetch, no CDN, file:// openable).

Usage:
    python3 bin/build_dashboard.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK_DIR = os.path.join(ROOT, "work")
APP_DIR = os.path.join(ROOT, "app")
YT_META_DIR = os.path.expanduser("~/ob-social-dashboard/data/yt-meta")


def load_yt_title(video_id):
    path = os.path.join(YT_META_DIR, f"{video_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            meta = json.load(f)
        return meta.get("title")
    except Exception:
        return None


def parse_advice_md(path):
    """
    Parses an advice.md file into a dict keyed by clip title (the text
    after the '### N. ' heading, stripped of the trailing timestamp
    parenthetical), mapping to the raw markdown block for that clip.
    """
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        text = f.read()

    blocks = {}
    # Split on "### N. <title>  (hh:mm:ss–hh:mm:ss, Ns)" headings
    heading_re = re.compile(r"^###\s+\d+\.\s+(.*?)\s{2,}\(.*?\)\s*$", re.MULTILINE)
    matches = list(heading_re.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        blocks[title] = body
    return blocks


def norm_title_key(title):
    """Normalize a clip title for matching between moments.json and advice.md."""
    return re.sub(r"\s+", " ", (title or "")).strip()


def collect_episodes():
    episodes = []
    if not os.path.isdir(WORK_DIR):
        return episodes

    moments_files = sorted(f for f in os.listdir(WORK_DIR) if f.endswith(".moments.json"))

    for fname in moments_files:
        video_id = fname[: -len(".moments.json")]
        path = os.path.join(WORK_DIR, fname)
        try:
            with open(path) as f:
                raw = json.load(f)
        except Exception as e:
            print(f"WARNING: failed to parse {path}: {e}", file=sys.stderr)
            continue

        moments = raw.get("moments", [])
        advice_path = os.path.join(WORK_DIR, f"{video_id}.advice.md")
        advice_blocks = parse_advice_md(advice_path)

        title = load_yt_title(video_id) or video_id

        out_moments = []
        for m in moments:
            title_key = norm_title_key(m.get("title", ""))
            advice = advice_blocks.get(title_key)
            if advice is None:
                # fallback: fuzzy match by prefix, advice.md titles can be
                # truncated/cleaned slightly differently than moments.json
                for k, v in advice_blocks.items():
                    if k[:30] and (k[:30] == title_key[:30]):
                        advice = v
                        break

            out_moments.append({
                "id": m.get("id"),
                "title": m.get("title", ""),
                "start": m.get("start", 0),
                "end": m.get("end", 0),
                "dur": m.get("dur", 0),
                "hook_line": m.get("hook_line", ""),
                "onscreen_hook": m.get("onscreen_hook"),
                "hook_archetype": m.get("hook_archetype"),
                "quotable_line": m.get("quotable_line", ""),
                "text": m.get("text", ""),
                "score": m.get("score", 0),
                "subscores": m.get("subscores", {}),
                "engagement_lever": m.get("engagement_lever"),
                "buyer_relevance": m.get("buyer_relevance"),
                "gate_passed": bool(m.get("gate_passed")),
                "gate_reason": m.get("gate_reason", ""),
                "music": m.get("music", {}),
                "ig_post": m.get("ig_post", {}),
                "advice": advice,
            })

        # rank gate-passed moments by score desc; keep others out of the
        # ranked list but still available in the data if needed later
        passed = [m for m in out_moments if m["gate_passed"]]
        passed.sort(key=lambda m: m.get("score", 0), reverse=True)
        for i, m in enumerate(passed):
            m["rank"] = i + 1

        rendered_clips = rendered_clips_for(video_id)
        mtimes = [c["mtime"] for c in rendered_clips if c.get("mtime")]
        last_rendered_at = max(mtimes) if mtimes else None

        episodes.append({
            "video_id": video_id,
            "title": title,
            "moments": passed,
            "total_moments": len(out_moments),
            "gate_passed_count": len(passed),
            "rendered_clips": rendered_clips,
            "last_rendered_at": last_rendered_at,
        })

    return episodes


def probe_duration_seconds(path):
    """Best-effort clip duration via ffprobe; returns None if unavailable."""
    try:
        import subprocess
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        return round(float(out.stdout.strip()), 1)
    except Exception:
        return None


def probe_orientation(path):
    """Return 'horizontal' or 'vertical' by probing the actual frame dims
    (fallback when the filename doesn't carry the '_h' suffix)."""
    try:
        import subprocess
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0", path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        w, h = out.stdout.strip().split(",")
        return "horizontal" if int(w) >= int(h) else "vertical"
    except Exception:
        return "vertical"


def rendered_clips_for(video_id):
    """Finished mp4s for this episode, served through the app/clips symlink
    (-> ~/ob-clipper/out) so the dashboard can play them in <video> tags."""
    out_root = os.path.expanduser("~/ob-clipper/out")
    clips = []
    if not os.path.isdir(out_root):
        return clips
    for folder in sorted(os.listdir(out_root)):
        if not folder.startswith(video_id):
            continue
        fdir = os.path.join(out_root, folder)
        if not os.path.isdir(fdir):
            continue
        for f in sorted(os.listdir(fdir)):
            if f.endswith(".mp4"):
                fpath = os.path.join(fdir, f)
                try:
                    mtime = os.path.getmtime(fpath)
                except OSError:
                    mtime = None
                # orientation: filename '_h' suffix is authoritative (cheap, no
                # ffprobe needed); fall back to probing actual dims for clips
                # rendered before this convention existed.
                if f.endswith("_h.mp4"):
                    orientation = "horizontal"
                else:
                    orientation = probe_orientation(fpath)
                clips.append({
                    "name": f,
                    "src": f"clips/{folder}/{f}",
                    "mtime": mtime,
                    "duration": probe_duration_seconds(fpath),
                    "orientation": orientation,
                })
    return clips


def build():
    episodes = collect_episodes()

    tpl_path = os.path.join(HERE, "dashboard_template.html")
    with open(tpl_path) as f:
        tpl = f.read()

    blob = json.dumps({"episodes": episodes}, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("__OB_MOMENTS_DATA__", blob)

    os.makedirs(APP_DIR, exist_ok=True)
    out_path = os.path.join(APP_DIR, "index.html")
    with open(out_path, "w") as f:
        f.write(html)

    print(f"Wrote {out_path}")
    print(f"Episodes: {len(episodes)}")
    for ep in episodes:
        print(f"  {ep['video_id']}: {ep['gate_passed_count']}/{ep['total_moments']} gate-passed: {ep['title']}")


if __name__ == "__main__":
    build()
