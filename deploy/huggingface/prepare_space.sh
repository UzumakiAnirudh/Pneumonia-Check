#!/usr/bin/env bash
# Assemble a Hugging Face Space folder from this project.
# Usage: bash deploy/huggingface/prepare_space.sh <path-to-cloned-space-repo>
#   WEIGHTS_SRC=...  override where the trained weights come from (default: backend/weights)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SPACE="${1:?usage: prepare_space.sh <space-dir>}"
WEIGHTS_SRC="${WEIGHTS_SRC:-$ROOT/backend/weights}"
METRICS_SRC="${METRICS_SRC:-$ROOT/backend/metrics}"
SAMPLES_SRC="${SAMPLES_SRC:-$ROOT/backend/samples}"

[ -d "$SPACE/.git" ] || { echo "$SPACE is not a cloned Space repository"; exit 1; }
git lfs version >/dev/null 2>&1 || { echo "Git LFS is required (model files are >10 MB). Install it: brew install git-lfs"; exit 1; }
ls "$WEIGHTS_SRC"/*.pth >/dev/null 2>&1 || { echo "No trained weights in $WEIGHTS_SRC"; exit 1; }

rm -rf "$SPACE/app" "$SPACE/samples" "$SPACE/metrics" "$SPACE/weights"
cp -R "$ROOT/backend/app" "$SPACE/app"
cp -R "$SAMPLES_SRC" "$SPACE/samples"
mkdir -p "$SPACE/metrics/gallery" && cp "$METRICS_SRC/metrics.json" "$SPACE/metrics/"
[ -d "$METRICS_SRC/gallery" ] && cp -R "$METRICS_SRC/gallery/." "$SPACE/metrics/gallery/"
mkdir -p "$SPACE/weights" && cp "$WEIGHTS_SRC"/*.pth "$WEIGHTS_SRC"/*_stage*.json "$WEIGHTS_SRC"/temperature.json "$SPACE/weights/"
cp "$ROOT/backend/requirements.txt" "$ROOT/deploy/huggingface/Dockerfile" "$ROOT/deploy/huggingface/README.md" "$SPACE/"
find "$SPACE/app" -name __pycache__ -type d -prune -exec rm -rf {} +

cd "$SPACE"
git lfs install --local >/dev/null
git lfs track "*.pth" "*.jpg" >/dev/null
echo "Space folder ready: $(du -sh . | cut -f1). Next: git add -A && git commit -m 'Deploy API' && git push"
