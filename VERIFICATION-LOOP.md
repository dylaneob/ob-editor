# OB's standing rule for every task (added 2026-11-10 at OB's request)

**Verification loop:** make it, look at the real result, compare it to what right means, fix, and repeat. OB is never the verifier.
- **Look at the real output**, not the code that made it: render frames, the QC gate, the transcript diff, running the code, the number's source. Test a new method on a few known cases before running it at scale.
- **A separate, fresh checker passes it**, never the chat that made it. Videos: the `video-reviewer` agent, checking against `~/ob-editor/qc/REVIEW-CHECKLIST.md` plus the QC gate. Everything else: the `work-checker` agent. Both are read-only and answer `VERDICT: PASS` or `FAIL`.
- **Only PASS ends the job.** Fix what the checker flags, re-check, at most 3 rounds, then tell OB exactly what is still wrong. A Stop hook (`~/.claude/hooks/require_review.py`) blocks a turn that rendered or sent a video until a reviewer PASS.
- **Any note OB gives twice** goes into the checklist or the QC gate the same day.
- Report what was checked. Anything unchecked is "not verified".

## Install
`INSTALL.sh` copies `claude-agents/` to `~/.claude/agents/` and `claude-hooks/require_review.py` to `~/.claude/hooks/`, and appends
this rule to `~/.claude/CLAUDE.md`. Then add the Stop hook to `~/.claude/settings.json`:

```json
"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/require_review.py", "timeout": 15}]}]}
```
