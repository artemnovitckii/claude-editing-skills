#!/usr/bin/env bash
# Links every skill in skills/ into ~/.claude/skills/ (so /trial-reels, /explainer ... show up in Claude Code)
# and runs the one-time kit setup. Re-run it after a git pull to pick up new skills.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
for d in "$ROOT"/skills/*/; do
  name=$(basename "$d")
  if [ -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
    echo "skip $name: $DEST/$name already exists and is not a link"
    continue
  fi
  ln -sfn "${d%/}" "$DEST/$name"
  echo "linked /$name"
done
bash "$ROOT/kit/setup.sh" "$@"
