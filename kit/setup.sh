#!/usr/bin/env bash
# One-time setup for the editing skills: checks ffmpeg and Node, makes kit/.venv, fetches GSAP,
# warms up HyperFrames and (with --cutout) downloads the matting model. Safe to run again.
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say() { printf '\033[1m%s\033[0m\n' "$*"; }

command -v ffmpeg >/dev/null || { echo "ffmpeg is missing. Mac: brew install ffmpeg"; exit 1; }
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libvpx-vp9 || echo "warning: this ffmpeg has no libvpx-vp9, so cutouts (behind-the-person, explainer) will fail"
command -v npx >/dev/null || { echo "Node.js is missing (HyperFrames renders with it). Mac: brew install node"; exit 1; }
PY=$(command -v python3) || { echo "python3 is missing"; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "python 3.9+ is needed"; exit 1; }

if [ ! -x "$KIT/.venv/bin/python" ]; then
  say "making kit/.venv"
  "$PY" -m venv "$KIT/.venv"
fi
"$KIT/.venv/bin/python" -m pip install -q --upgrade pip
"$KIT/.venv/bin/python" -m pip install -q groq numpy pillow onnxruntime

mkdir -p "$KIT/vendor"
if [ ! -s "$KIT/vendor/gsap.min.js" ]; then
  say "fetching GSAP"
  curl -fsSL https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js -o "$KIT/vendor/gsap.min.js"
fi

say "warming up HyperFrames (first run downloads it)"
npx --yes hyperframes@0.8.34 --version >/dev/null 2>&1 || echo "warning: could not run hyperframes yet; the first render will retry"

if [ "${1:-}" = "--cutout" ]; then
  say "downloading the matting model"
  "$KIT/.venv/bin/python" -c "import sys; sys.path.insert(0, '$KIT'); import cutout; cutout.model_path('mobilenetv3')"
fi

[ -n "${GROQ_API_KEY:-}" ] || echo "note: set GROQ_API_KEY (free at https://console.groq.com/keys) so clips can be transcribed"
say "ready: $KIT/.venv/bin/python"
