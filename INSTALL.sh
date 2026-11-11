#!/bin/bash
# OB's Claude video editor kit: installer for macOS on Apple Silicon.
#   bash INSTALL.sh [WORK_FOLDER]          (default ~/EditorWork; footage, edits and renders live there)
# Safe to re-run: existing ~/ob-editor, ~/ob-clipper, ~/ob-moments and the skill are renamed with a timestamp, never deleted.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$HOME/EditorWork}"; WORK="${WORK%/}"
STAMP="$(date +%Y%m%d-%H%M%S)"
say() { printf "\n== %s\n" "$*"; }

say "Checking the basics"
[ "$(uname -s)" = "Darwin" ] || { echo "This kit needs macOS."; exit 1; }
command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
xcode-select -p >/dev/null 2>&1 || { echo "Run 'xcode-select --install' first (it builds the Apple Vision helpers), then run this again."; exit 1; }
SKIP="${KIT_SKIP_DOWNLOADS:-0}"      # 1 = skip brew/pip/npm/model downloads (for testing the copy and path steps)
if [ "$SKIP" != 1 ]; then
  for f in ffmpeg whisper-cpp yt-dlp node python; do
    brew list --versions "$f" >/dev/null 2>&1 || { echo "  installing $f"; brew install "$f"; }
  done
fi

say "Copying the kit (existing copies are renamed, not deleted)"
for d in ob-editor ob-clipper ob-moments; do
  [ -e "$HOME/$d" ] && mv "$HOME/$d" "$HOME/$d.before-kit-$STAMP" && echo "  kept your old $d as $d.before-kit-$STAMP"
  cp -R "$KIT/$d" "$HOME/$d"
done
SK="$HOME/.claude/skills/short-form-editor"
mkdir -p "$HOME/.claude/skills"
[ -e "$SK" ] && mv "$SK" "$SK.before-kit-$STAMP"
cp -R "$KIT/claude-skills/short-form-editor" "$SK"

for s in "$KIT"/claude-skills/*/; do n=$(basename "$s"); [ "$n" = short-form-editor ] && continue
  d="$HOME/.claude/skills/$n"; [ -e "$d" ] && mv "$d" "$d.before-kit-$STAMP"; cp -R "$s" "$d"; done
mkdir -p "$WORK/OB-EDITS/sfx-library"
cp -R "$KIT/banks/music" "$WORK/OB-EDITS/music"; cp "$KIT"/banks/music/picks/*.mp3 "$WORK/"
cp -R "$KIT/banks/sfx-openverse" "$WORK/OB-EDITS/sfx-library/openverse"
mkdir -p "$HOME/.claude/agents" "$HOME/.claude/hooks"; cp "$KIT"/claude-agents/*.md "$HOME/.claude/agents/"
cp "$KIT/claude-hooks/require_review.py" "$HOME/.claude/hooks/"
grep -q "Verification loop" "$HOME/.claude/CLAUDE.md" 2>/dev/null || cat "$KIT/VERIFICATION-LOOP.md" >> "$HOME/.claude/CLAUDE.md"
say "Now add the Stop hook from VERIFICATION-LOOP.md to ~/.claude/settings.json"

say "Pointing every path at $HOME and $WORK"
mkdir -p "$WORK/OB-EDITS/tmp" "$WORK/RAW-FOOTAGE/camera" "$WORK/MUSIC" "$WORK/ARCHIVE" "$HOME/ob-editor-tmp" "$HOME/.whisper-models"
{ grep -rlI -e /Users/YOU -e /Volumes/T7 -e /Volumes/OB-ARCHIVE -e OpenMontage/.venv -e '~/EditorWork' \
  "$HOME/ob-editor" "$HOME/ob-clipper" "$HOME/ob-moments" "$SK" 2>/dev/null || true; } | while IFS= read -r f; do
  sed -i '' -e "s#/Users/YOU#$HOME#g" -e "s#/Volumes/OB-ARCHIVE#$WORK/ARCHIVE#g" -e "s#/Volumes/T7#$WORK#g" \
            -e "s#~/OpenMontage/.venv#~/ob-editor/.venv#g" -e "s#$HOME/OpenMontage/.venv#$HOME/ob-editor/.venv#g" \
            -e "s#~/EditorWork#$WORK#g" "$f"
done

PY="$(brew --prefix)/bin/python3"
if [ "$SKIP" != 1 ]; then
  say "Python packages"
  "$PY" -m pip install --quiet --break-system-packages numpy scipy pillow
  "$PY" -m venv "$HOME/ob-editor/.venv"
  "$HOME/ob-editor/.venv/bin/pip" install --quiet --upgrade pip
  "$HOME/ob-editor/.venv/bin/pip" install --quiet opencv-contrib-python-headless numpy scipy pillow faster-whisper

  say "Node packages (Puppeteer, HyperFrames, GSAP)"
  ( cd "$HOME/ob-editor" && npm install --silent && mkdir -p vendor && cp node_modules/gsap/dist/gsap.min.js vendor/ )

  say "Whisper models (base and medium, English)"
  for m in base.en medium.en; do
    f="$HOME/.whisper-models/ggml-$m.bin"
    [ -s "$f" ] || curl -L --fail --progress-bar -o "$f" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$m.bin"
  done
fi

say "Apple Vision helpers"
for s in "$HOME"/ob-editor/bin/*.swift; do
  b="${s%.swift}"
  if swiftc -O "$s" -o "$b" 2>/dev/null; then echo "  built $(basename "$b")"; else echo "  could not build $(basename "$s")"; fi
done
ln -sf "$(command -v ffmpeg)" "$HOME/ob-editor/bin/ffmpeg-full"
ln -sf "$(command -v ffprobe)" "$HOME/ob-editor/bin/ffprobe-full"

say "Fonts (made from this Mac's own system fonts)"
"$PY" "$HOME/ob-editor/bin/font_setup.py" "$HOME/ob-editor/fonts"

[ "$SKIP" = 1 ] && { say "Copy and path steps done (downloads skipped)"; exit 0; }
say "Quick check"
ffmpeg -hide_banner -version | head -1
whisper-cli --help >/dev/null 2>&1 && echo "  whisper-cli ok"
"$HOME/ob-editor/.venv/bin/python" -c "import cv2; print('  opencv', cv2.__version__)"
( cd "$HOME/ob-editor" && npx --no-install hyperframes --version >/dev/null 2>&1 && echo "  hyperframes ok" ) || echo "  hyperframes: run 'cd ~/ob-editor && npm install' again"

say "Done. Last step, in Terminal:"
echo "  npx skills add heygen-com/hyperframes -g -a claude-code"
echo "  and the watch skill: https://github.com/bradautomates/claude-video"
echo "  optional, the sound-effect tools (earshot + Real SFX, about 1.5 GB of models, from their GitHub releases):"
echo "    zsh ~/ob-editor/bin/install_sfx_tools.sh"
echo "Then open Claude Code in your home folder and say: edit this $WORK/RAW-FOOTAGE/camera/<clip>.MP4"
