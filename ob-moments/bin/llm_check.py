#!/usr/bin/env python3
"""
llm_check.py — one-shot self-diagnostic for the LLM scoring path.

OB runs this ONCE in his own terminal (where `claude` is actually logged in
or ANTHROPIC_API_KEY is actually set) to confirm the sharper LLM-scoring path
in score.py works before trusting it on a real video. It never renders
anything and never touches work/ — it's read-only diagnostics.

Two steps:
  1. Backend probe — prints availability exactly like clip.py's own probe
     (same function, same wording), so this tool and clip.py never disagree
     about whether a backend is available.
  2. If a backend IS available: run a tiny 2-candidate scoring round-trip
     through score.py's REAL llm_enrich()/_parse_scores() path (not a
     reimplementation) and print PASS/FAIL. On FAIL, print the raw model
     response so the failure is actionable instead of a bare "it broke".

Usage:
    python3 bin/llm_check.py
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clip import llm_backend_available
from score import llm_enrich, _llm_call, LLM_PROMPT

# two tiny, unambiguous candidates — cheap to score, easy to sanity-check
_TEST_CANDS = [
    {"id": 1, "first_sentence": "Nobody tells you this about losing 20 pounds.",
     "text": "Nobody tells you this about losing 20 pounds. Everyone thinks it's about "
             "the workout, but it's actually about what you eat every single day."},
    {"id": 2, "first_sentence": "So anyway, that's kind of what happened last week.",
     "text": "So anyway, that's kind of what happened last week. It was fine I guess, "
             "nothing crazy, just a normal training day."},
]


def main():
    available, how = llm_backend_available()
    if available:
        print(f"[llm_check] backend available: {how}")
    else:
        print("[llm_check] backend available: NO (claude CLI not logged in, "
              "no ANTHROPIC_API_KEY set)")
        print("[llm_check] this IS expected in a sandboxed/CI environment — "
              "score.py will use the deterministic lexicon path and is fully "
              "usable without an LLM backend.")
        print("[llm_check] to enable the sharper path: run `claude` and log in "
              "interactively once, or `export ANTHROPIC_API_KEY=...`, then re-run "
              "this check.")
        return

    print(f"[llm_check] running a tiny {len(_TEST_CANDS)}-candidate scoring "
          "round-trip through score.py's real llm_enrich() …")
    raw_probe = None
    try:
        raw_probe = _llm_call(LLM_PROMPT % json.dumps(_TEST_CANDS, ensure_ascii=False),
                              timeout=60)
    except Exception as e:
        print(f"[llm_check] RESULT: FAIL — _llm_call raised {type(e).__name__}: {e}")
        _print_actionable_failure(how, raw=None)
        sys.exit(1)

    scores = llm_enrich(_TEST_CANDS, timeout=60, batch_size=8)

    ok_ids = {1, 2}
    got_ids = set(scores.keys())
    if got_ids == ok_ids:
        print(f"[llm_check] RESULT: PASS — got valid scores for both test candidates "
              f"via {how}.")
        for cid in sorted(scores):
            s = scores[cid]
            print(f"  id={cid}  hook={s.get('hook_score')}  arousal={s.get('arousal')}  "
                  f"controversy={s.get('controversy')}  lever={s.get('engagement_lever')}  "
                  f"title={s.get('title')!r}")
        print("[llm_check] the sharper LLM-scoring path is working. score.py / clip.py "
              "will use it automatically (no --llm flag needed).")
        return

    # FAIL — show exactly what came back so it's debuggable, not a black box.
    print(f"[llm_check] RESULT: FAIL — expected LLM scores for ids {sorted(ok_ids)}, "
          f"got {sorted(got_ids) or 'none'}.")
    _print_actionable_failure(how, raw=raw_probe)
    sys.exit(1)


def _print_actionable_failure(how, raw):
    print("[llm_check] ---- raw model response (for debugging) ----")
    if raw:
        print(raw[:4000])
        if len(raw) > 4000:
            print(f"... [truncated, {len(raw)} chars total]")
    else:
        print("(empty / no response captured)")
    print("[llm_check] ---- end raw response ----")
    print("[llm_check] likely causes + fixes:")
    print("  - `claude -p` returned non-JSON prose: the model ignored the "
          "'return ONLY JSON' instruction — try again, or check for a stale/"
          "misconfigured CLAUDE.md injecting extra instructions into `claude -p`.")
    print("  - rate-limited or auth expired mid-call: run `claude` interactively "
          "and confirm you're logged in, then re-run this check.")
    print("  - ANTHROPIC_API_KEY set but invalid/expired: verify with a direct "
          "`curl https://api.anthropic.com/v1/messages` call using the same key.")
    print(f"  - backend reported as '{how}' by the probe — confirm that's the "
          "backend you intended to test.")


if __name__ == "__main__":
    main()
