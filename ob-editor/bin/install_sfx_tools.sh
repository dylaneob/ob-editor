#!/bin/zsh
# Hand install of the two SFX tools OB asked for on 2026-11-01 ("download this to our editor skill long form and short"),
# both read line by line first (verdicts: safe with limits). Pinned tarballs in ~/ob-editor/vendor, checked by sha256.
#   1. earshot 0.4.0 (MIT) into its own Python 3.12 env, then its pinned models (~1.1 GB, Hugging Face, once); used only
#      through ~/ob-editor/bin/earshot (no Google keys, no uploads, offline after this).
#   2. Real SFX (Clipwing/skills @ edbefcb) into ~/.claude/skills/real-sfx with OB's rules on top and a narrowed trigger,
#      libraries pointed at his kits. Its optional installers (npm, pip, models) are never run.
set -euo pipefail
V=$HOME/ob-editor/vendor
mkdir -p $V
get() { [ -s "$V/$1" ] || curl -fL --progress-bar -o "$V/$1" "$2"; }   # the exact archives OB reviewed
get earshot-v0.4.0.tar.gz https://github.com/Leonxlnx/earshot/archive/refs/tags/v0.4.0.tar.gz
get clipwing-skills-edbefcb.tar.gz https://github.com/Clipwing/skills/archive/edbefcbc3474869e6cc1e8a7ca583b0efd0dab7e.tar.gz
command -v uv >/dev/null || brew install uv
mkdir -p /Volumes/T7/OB-EDITS/sfx-library/openverse
check() { [ "$(shasum -a 256 "$1" | cut -d' ' -f1)" = "$2" ] || { echo "CHECKSUM MISMATCH: $1" >&2; exit 1; }; }
check $V/earshot-v0.4.0.tar.gz c286b4542bc2ec67573e0d2b547dd123f89fd47cb5d708ab68f8af72b3c56cd4
check $V/clipwing-skills-edbefcb.tar.gz b187ed76a746fff245d1acd40a2157490a64b975fc803c8b37a7156642de6cc7
cd "$HOME"   # never run an installer from inside a downloaded folder

echo "== earshot"
rm -rf $V/earshot-0.4.0 && tar -xzf $V/earshot-v0.4.0.tar.gz -C $V
uv venv "$HOME/ob-editor/venvs/earshot" --python 3.12
uv pip install --python "$HOME/ob-editor/venvs/earshot/bin/python" "$V/earshot-0.4.0"
env -u GEMINI_API_KEY -u GOOGLE_API_KEY EARSHOT_HOME="$HOME/ob-editor/earshot-home" EARSHOT_OFFLINE=0 \
  "$HOME/ob-editor/venvs/earshot/bin/earshot" doctor --fetch
chmod +x "$HOME/ob-editor/bin/earshot"
"$HOME/ob-editor/bin/earshot" doctor

echo "== Real SFX"
D="$HOME/.claude/skills/real-sfx"
[ -e "$D" ] && { echo "already installed at $D: leaving it alone" >&2; exit 0; }
T=$(mktemp -d); tar -xzf $V/clipwing-skills-edbefcb.tar.gz -C "$T"
S=$(ls -d "$T"/*/skills/real-sfx)
mkdir -p "$D" && rsync -a --exclude evals "$S/" "$D/"
python3 -I - "$D/SKILL.md" "$V/real-sfx-OB-RULES.md" <<'PY'
import sys
p, rules = sys.argv[1], open(sys.argv[2]).read()
s = open(p).read(); head, sep, body = s.partition("\n---\n")
lines = head.split("\n")
desc = ("description: Real SFX (Clipwing): places real recorded sound effects on the exact frame from a cue list and returns a new "
        "MP4 plus a separate SFX track and a self-critique. For OB's edits only when /short-form-editor's sound-effects step routes "
        "here with his planned cue list, or OB names Real SFX. It never decides how many sounds go in (OB's caps: about 3-4 a "
        "minute in reels, entrances only).")
lines = [desc if l.startswith("description:") else l for l in lines]
open(p, "w").write("\n".join(lines) + sep + "\n" + rules + "\n" + body)
print("OB rules on top, trigger narrowed:", p)
PY
rm -rf "$T"
cd "$HOME"
python3 -I "$D/scripts/setup.py" add-library ob-kenney "$HOME/ob-editor/assets/sfx_real" --tier main
python3 -I "$D/scripts/setup.py" add-library openverse /Volumes/T7/OB-EDITS/sfx-library/openverse --tier extra --index
python3 -I "$D/scripts/setup.py" check
echo "DONE"
