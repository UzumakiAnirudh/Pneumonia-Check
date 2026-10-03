# Model weights

Trained weights loaded by the API (`USE_MOCK_MODELS=false`, the default).

| File | Produced by | Purpose |
|---|---|---|
| `densenet_stage1.pth` | `training/train.py --arch densenet --task stage1` | DenseNet121 · Normal vs Pneumonia |
| `densenet_stage2.pth` | `training/train.py --arch densenet --task stage2` | DenseNet121 · Bacterial vs Viral |
| `swin_stage1.pth` | `training/train.py --arch swin --task stage1` | Swin-Tiny · Normal vs Pneumonia |
| `swin_stage2.pth` | `training/train.py --arch swin --task stage2` | Swin-Tiny · Bacterial vs Viral |
| `temperature.json` | `training/calibrate.py` | Temperature per model, e.g. `{"densenet_stage1": 1.31}` |
| `validator.pth` | `training/train_validator.py` | MobileNetV3-Small CXR vs non-CXR input validator |
| `densenet_three_class.pth`, `swin_three_class.pth` | `--task three_class` | Only for `CLASSIFICATION_MODE=three_class` |

Each `.pth` may have a sidecar `<name>.json` (written automatically by `train.py`) recording the
preprocessing used in training — image size and CLAHE settings — which the API then applies, so
inference always matches training.

Format: a plain `state_dict` (or `{"state_dict": ...}`) for the corresponding `timm` model
(`densenet121`, `swin_tiny_patch4_window7_224`, `mobilenetv3_small_100`) with a 2- or 3-class head.

## Updating the weights

Copy new files into this folder (any subset works; `/api/health` shows what loaded) and restart the API.

If `validator.pth` is missing the heuristic validator is used; if `temperature.json` is missing,
probabilities are uncalibrated (T = 1).
