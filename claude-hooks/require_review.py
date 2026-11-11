#!/usr/bin/env python3
"""Stop hook (OB 11-10: "add this to all tasks", the verification loop): a turn that rendered or delivered a video can't
end until a fresh `video-reviewer` (or `work-checker`) agent has returned VERDICT: PASS after the last render.

- Looks only at this turn: entries after the last real user message, read from the tail of the transcript.
- Blocks at most 3 times per user message, then lets the turn end (OB gets told what is still unreviewed).
- Any error lets the turn end: the hook must never trap a session.
"""
import json, os, re, sys

RENDER = re.compile(
    r"(tmpl\.py\s+render\b|ytclip(?:\.py)?\s+(?:render|deliver)\b|\brender_final\b|render_clip\.py|\bdeliver\.py\b|"
    r"fdoe_artzen\.py\b(?!.*\bstill\b)|brand_react_render\.py|react_render\.py|lf_render|final_deliver\.py|"
    # added 2026-11-10 (editor rebuild): engines the list missed, only when they are run, never when they are read
    r"python3?\s+(?:-\w+\s+)*\S*(?:assemble|lecture_render|tier_render)\.py\b|lk\.py\s+render\b|render_final_music\.sh|"
    r"trial_variants\.py\s+(?:render|deliver)\b|beats\.py\s+redo\b|ob_job\.py\s+finish\b)")
SKIP = re.compile(r"(\bstill\b|--dry-run|\brea-video\b|\btiles\b|--help|\bgrep\b.*render|cat\s+.*render|\bls\b|importlib\.util)")  # importlib.util: a test of this file's own patterns (11-10), never a render
VIDEO_EXT = (".mp4", ".mov", ".m4v")
REVIEWERS = ("video-reviewer", "work-checker")
MAX_BLOCKS = 3
TAIL = 12 * 1024 * 1024


def tail_entries(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - TAIL))
        data = f.read()
    lines = data.split(b"\n")
    if size > TAIL:
        lines = lines[1:]          # first line is probably cut
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def blocks(e):
    c = (e.get("message") or {}).get("content")
    return c if isinstance(c, list) else ([{"type": "text", "text": c}] if isinstance(c, str) else [])


def is_real_user(e):
    if e.get("type") != "user" or e.get("isSidechain") or e.get("isMeta"):
        return False
    b = blocks(e)
    if not b or any(x.get("type") == "tool_result" for x in b):
        return False
    txt = " ".join(x.get("text", "") for x in b if x.get("type") == "text")
    return bool(txt.strip()) and "<task-notification>" not in txt


def main():
    d = json.load(sys.stdin)
    tp = d.get("transcript_path")
    if not tp or not os.path.exists(tp):
        return 0
    ents = [e for e in tail_entries(tp) if not e.get("isSidechain")]
    start = 0
    for i in range(len(ents) - 1, -1, -1):
        if is_real_user(ents[i]):
            start = i
            break
    turn = ents[start:]
    anchor = turn[0].get("uuid", "none") if turn else "none"

    last_render, renders, agent_ids = -1, [], {}
    for i, e in enumerate(turn):
        for b in blocks(e):
            if b.get("type") != "tool_use":
                continue
            name, inp = b.get("name", ""), b.get("input") or {}
            if name == "Bash":
                cmd = inp.get("command", "")
                if RENDER.search(cmd) and not SKIP.search(cmd):
                    last_render = i; renders.append(cmd[:90])
            elif name == "SendUserFile":
                if any(str(f).lower().endswith(VIDEO_EXT) for f in inp.get("files", [])):
                    last_render = i; renders.append("sent " + ", ".join(os.path.basename(str(f)) for f in inp.get("files", [])))
            elif name in ("Agent", "Task") and inp.get("subagent_type") in REVIEWERS:
                agent_ids[b.get("id")] = i
    if last_render < 0:
        return 0

    passed = False
    for i, e in enumerate(turn):
        for b in blocks(e):
            if b.get("type") == "tool_result" and agent_ids.get(b.get("tool_use_id"), -1) > last_render:
                c = b.get("content")
                txt = c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
                if re.search(r"VERDICT:\s*PASS", txt):
                    passed = True
    if passed:
        return 0

    sid = d.get("session_id", "unknown")
    sf = os.path.expanduser(f"~/.claude/hooks/state/review_{sid}.json")
    try:
        st = json.load(open(sf))
    except Exception:
        st = {}
    if st.get("anchor") != anchor:
        st = {"anchor": anchor, "n": 0}
    st["n"] += 1
    os.makedirs(os.path.dirname(sf), exist_ok=True)
    json.dump(st, open(sf, "w"))
    if st["n"] > MAX_BLOCKS:
        return 0
    sys.stderr.write(
        f"Verification loop (OB 11-10), round {st['n']} of {MAX_BLOCKS}: this turn rendered or sent a video "
        f"({renders[-1]}) and no fresh reviewer has passed it since. Run the `video-reviewer` agent on the latest render "
        f"(give it the file, the script or plan, the template), fix everything it flags, re-render, and review again. "
        f"Only say done after VERDICT: PASS. If this was a test or scratch render that OB will never see, say so in one line and stop.\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
