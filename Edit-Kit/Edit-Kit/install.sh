#!/bin/bash
# Edit Kit installer (Mac / Linux). Copies the skills into ~/.claude/skills.
# Skills with the same name are backed up first to ~/.claude/skills-backup/<date>, nothing is lost.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.claude/skills"
BK="$HOME/.claude/skills-backup/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DST"
for s in "$DIR"/skills/*/; do
  name=$(basename "$s")
  if [ -d "$DST/$name" ]; then mkdir -p "$BK"; mv "$DST/$name" "$BK/$name"; fi
  cp -R "$s" "$DST/$name"; echo "installed /$name"
done
[ -d "$BK" ] && echo "(your previous versions were saved in $BK)"
# brand-kit folder: only the template, never overwrites brands you already have
mkdir -p "$HOME/.claude/motion-kit/brands"
[ -f "$HOME/.claude/motion-kit/brands/README.md" ] || cp "$DIR/brands/README.md" "$HOME/.claude/motion-kit/brands/"
[ -d "$HOME/.claude/motion-kit/brands/_template" ] || cp -R "$DIR/brands/_template" "$HOME/.claude/motion-kit/brands/"
echo ""
echo "Done. Close and reopen Claude Code, then type:  /edit"
command -v node >/dev/null || echo "Missing: Node.js 22+  ->  download from nodejs.org"
command -v ffmpeg >/dev/null || ls ~/.local/node/bin/ffmpeg >/dev/null 2>&1 || echo "Missing: FFmpeg  ->  after Node is installed run:  npm i -g ffmpeg-static"
python3 -c "import PIL, numpy" 2>/dev/null || echo "Missing: Python packages  ->  run:  pip3 install pillow numpy"
