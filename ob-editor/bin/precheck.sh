#!/bin/bash
# precheck.sh WORK [--keep-going]
# The gate before ANY preview or final render of a long-form edit (OB 2026-10-20: look-aways on screen, graphics switching so fast
# it "looked glitchy", boring text slides). Runs the checks in this order and stops at the first one that fails:
#   1 coverage  coverage_check.py  graphics share, face-only stretches over 8 s, face first 5 s, recorded eyes-down runs under a card
#   2 flicker   flicker_check.py   no cover under ~1.5 s between face shots, no face sliver under ~1.5 s between covers, no
#                                  card-face-same-card break under ~2 s, no run under 9 frames, no clip-hold frame uncovered
#   3 lookaway  lookaway_check.py  raw gaze rows: eyes down (pupil_y >= 0.45, eyes shut, no face) for 2+ samples with his face on screen
#   4 fit       fit_check.py       every full-frame card fills the safe area and none is pushed off the edge (measures the mocks)
#   5 pace      pace_check.py      12+ visual changes a minute and a median shot of 3.5 s or less
# Read-only on WORK: nothing is written there. Exit code: that of the first failing step (1 = the check found problems,
# 2 = it could not read its inputs), 0 when all five pass.
#
#   precheck.sh WORK                 stop at the first failure (the normal use: fix it, run again)
#   precheck.sh WORK --keep-going    run all five anyway and print a table (to see everything at once)
# Environment (all optional):
#   OB_FLICKER_ALLOW=ID,ID   intentional gags that flicker_check should allow (or WORK/story/flicker_allow.json, or "allow_flicker": true)
#   OB_FIT_MODE=stored       fit_check without the browser (reads fit.json only, weaker); default measures the mocks, about 15 s
#   OB_COVERAGE_ARGS / OB_FLICKER_ARGS / OB_LOOKAWAY_ARGS / OB_FIT_ARGS / OB_PACE_ARGS   extra flags for one step, e.g.
#       OB_LOOKAWAY_ARGS="--yaw -0.5" for pickups where he reads off to the side; OB_PACE_ARGS="--min-rate 8" for a slower, older style.
# Fixes: a look-away is covered with an insert or a clip over the line (or the card before it held longer) or cut; flicker, see
# PRESET.md "No flicker"; fit, `fit_check.py WORK --write` and look at the cards again. Details: presets/youtube-longform/PRESET.md, "Precheck gate".
set -u
W="${1:-}"
if [ -z "$W" ] || [ ! -d "$W" ]; then echo "usage: precheck.sh WORK [--keep-going]" >&2; exit 2; fi
KEEP=0; [ "${2:-}" = "--keep-going" ] && KEEP=1
B="$(cd "$(dirname "$0")" && pwd)"
PY=/opt/homebrew/bin/python3
FITARGS="${OB_FIT_ARGS:-}"; [ "${OB_FIT_MODE:-measure}" = "stored" ] && FITARGS="$FITARGS --stored-only"
first=0; summary=""
run_step() {   # name script extra-args
  local name="$1" script="$2" extra="$3"
  echo "== $name ($script)"
  # shellcheck disable=SC2086
  "$PY" -I "$B/$script" "$W" $extra
  local rc=$?
  case $rc in 0) summary="$summary$name=OK ";; 1) summary="$summary$name=FAIL ";; *) summary="$summary$name=ERROR($rc) ";; esac
  if [ $rc -ne 0 ]; then
    [ $first -eq 0 ] && first=$rc
    if [ $KEEP -eq 0 ]; then echo; echo "PRECHECK STOPPED at $name (exit $rc). Fix it and run precheck.sh again."; exit $rc; fi
  fi
  echo
}
run_step coverage coverage_check.py "${OB_COVERAGE_ARGS:-}"
run_step flicker  flicker_check.py  "${OB_FLICKER_ARGS:-}"
run_step lookaway lookaway_check.py "${OB_LOOKAWAY_ARGS:-}"
run_step fit      fit_check.py      "$FITARGS"
run_step pace     pace_check.py     "${OB_PACE_ARGS:-}"
if [ $first -eq 0 ]; then echo "PRECHECK PASSED: $summary"; else echo "PRECHECK FAILED: $summary"; fi
exit $first
