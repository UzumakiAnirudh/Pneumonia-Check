#!/usr/bin/env bash
# Full local pipeline: train both architectures for both stages, calibrate, evaluate (overall and
# per population), Grad-CAM gallery, external validation, and export real example X-rays.
#
# Uses data/splits_combined.csv (pediatric + adult; build it with prepare_adult.py) when present,
# otherwise the pediatric-only data/splits.csv.
# Usage: bash run_pipeline.sh [extra train.py args, e.g. --epochs 10]
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python}
SPLITS=${SPLITS:-data/splits_combined.csv}
[ -f "$SPLITS" ] || SPLITS=data/splits.csv
echo "Using splits: $SPLITS"
COMMON=(--cache --workers 0 --splits "$SPLITS")

for arch in densenet swin; do
  for task in stage1 stage2; do
    echo "=== train $arch $task ==="
    $PY train.py --arch "$arch" --task "$task" "${COMMON[@]}" "$@"
  done
done
echo "=== calibrate ===";  $PY calibrate.py --all "${COMMON[@]}"
echo "=== evaluate ===";   $PY evaluate.py "${COMMON[@]}"
for arch in densenet swin; do
  echo "=== gradcam $arch ==="; $PY gradcam_analysis.py --arch "$arch" --per-category 6 --max-images 400 --splits "$SPLITS"
done
if [ -f data/external/actualmed.csv ]; then
  echo "=== external validation (Actualmed, unseen hospital) ==="
  $PY external_validate.py --name "Actualmed (unseen hospital, adults)" \
    --description "185 adult frontal CXRs (127 normal, 58 COVID-19) from a hospital never used in training; Stage 1 only." \
    --csv data/external/actualmed.csv --cache --workers 0
fi
echo "=== export samples ==="; $PY export_samples.py --splits "$SPLITS"
echo "=== PIPELINE DONE ==="
