#!/bin/zsh
# The editing toolbox health check lives in doctor.py (one canonical). The short-form checks this file first held
# (11-03: person_mask_dir matte, gaze, qc_gate --selftest with lipsync, react_window_audit, /watch, brand font, render_slots,
# brew outdated) are in doctor.sh.2026-11-03-short-form until doctor.py covers them.
exec python3 -I "$HOME/ob-editor/bin/doctor.py" "$@"
