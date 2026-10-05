# Chapter 9 — The training pipeline: from images to models

[← Chapter 8](08-data.md) · [README](../../README.md) · Next: [Chapter 10 →](10-backend-walkthrough.md)

This chapter takes you from downloaded images to the exact model files the app uses, one script at a
time. You need the data from [Chapter 8](08-data.md).

---

## 9.1 Hardware: where to train

| Option                           | Speed                       | Cost | Notes                                                                                      |
| -------------------------------- | --------------------------- | ---- | ------------------------------------------------------------------------------------------ |
| **Google Colab** (free GPU)      | Fast                        | Free | Easiest for beginners. Use `training/notebooks/train_colab.ipynb` (§9.10)                  |
| Apple-silicon Mac (M1–M4)        | ~2–3 min per epoch          | Free | Uses the Mac GPU ("MPS"); add `--cache`                                                    |
| Windows/Linux with an NVIDIA GPU | Fastest                     | —    | Install the CUDA build of PyTorch from pytorch.org; mixed precision turns on automatically |
| CPU only                         | Very slow (hours per model) | —    | Fine for tiny tests (`--limit 300 --epochs 1`)                                             |

Our reference run on an Apple M4: ~1.5–2 hours for all four models plus evaluation.

## 9.2 Set up the training environment

Training uses the **full** backend libraries (PyTorch etc.) because it imports the backend's
preprocessing and model code:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate       # if not done already
pip install -r requirements-dev.txt                       # PyTorch, timm, grad-cam, ONNX, pytest...
cd ../training
pip install -r requirements.txt                           # + pandas, matplotlib, scikit-learn
```

On Linux/Windows without a GPU, a much smaller CPU-only PyTorch can be installed first with
`pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`.

## 9.3 The whole pipeline in one command

```bash
cd training
python download_data.py kermany
python prepare_data.py --data-root data/raw/chest_xray
SPLITS=data/splits.csv bash run_pipeline.sh --epochs 10 --patience 4 --warmup-epochs 0.5
```

This reproduces the **deployed Version 1 models**. `run_pipeline.sh` runs, in order: training ×4,
calibration, evaluation, the Grad-CAM gallery, external validation (if the Actualmed data exists),
example-image export and ONNX export. Results land directly in `backend/weights/` and
`backend/metrics/` — restart the backend and the app uses them.

(On Windows, run `bash` from _Git Bash_, or run the individual commands below.)

The rest of this chapter explains each step so you can run, change and understand it.

## 9.4 Step 1 — `train.py`: teaching one model

```bash
python train.py --arch densenet --task stage1 --cache --workers 0 --epochs 10 --patience 4 --warmup-epochs 0.5
```

| Option                                   | Meaning                                                                                             | Default           |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------- |
| `--arch`                                 | `densenet` or `swin`                                                                                | —                 |
| `--task`                                 | `stage1` (Normal vs Pneumonia), `stage2` (Bacterial vs Viral, pneumonia images only), `three_class` | —                 |
| `--splits`                               | Which split CSV to use                                                                              | `data/splits.csv` |
| `--epochs` / `--patience`                | Maximum epochs / stop after this many epochs without improvement                                    | 25 / 6            |
| `--lr`, `--weight-decay`, `--batch-size` | AdamW settings                                                                                      | 1e-4, 1e-4, 32    |
| `--warmup-epochs`                        | Linear warm-up before cosine decay                                                                  | 1.0               |
| `--cache`                                | Pre-process all images once and keep them on disk — much faster on Mac/CPU                          | off               |
| `--no-clahe`                             | Disable CLAHE (recorded with the model so the app follows)                                          | CLAHE on          |
| `--hflip`                                | Allow horizontal flips (not recommended — heart position)                                           | off               |
| `--adult-fraction`                       | Share of adult images per epoch when the CSV mixes sources                                          | 0.3               |
| `--limit N`, `--no-pretrained`           | Quick smoke tests                                                                                   | —                 |
| `--device`                               | `auto`, `cpu`, `cuda`, `mps`                                                                        | auto              |

What it does, in order:

1. Loads the split CSV and builds datasets (`training/dataset.py`): decode → shared preprocessing →
   random augmentation (train only) → tensor.
2. Computes **class weights** from the training labels (e.g. `[1.841, 0.686]`).
3. Creates the ImageNet-pretrained model with a new 2-class head (`timm`).
4. Trains with AdamW, warm-up + cosine learning-rate schedule, gradient clipping, mixed precision on
   NVIDIA GPUs, and skips any batch whose loss is not a finite number.
5. After every epoch, measures validation loss, accuracy and **AUC**; saves the weights whenever the
   AUC improves; stops early after `--patience` epochs without improvement.

You will see lines like:

```
densenet stage1 | device=mps | train=4101 val=844 | counts=[1114, 2987]
epoch   1 | train loss 0.3244 acc 0.862 | val loss 0.1304 acc 0.954 auc 0.9890 | 135s
...
Early stopping at epoch 9 (best epoch 5, val AUC 0.9968)
Saved best weights (epoch 5) to backend/weights/densenet_stage1.pth
```

Outputs:

- `backend/weights/densenet_stage1.pth` — the learned weights;
- `backend/weights/densenet_stage1.json` — preprocessing settings + hyper-parameters (the app reads
  these, so inference always matches training);
- training curves in `backend/metrics/metrics.json` (shown on the dashboard).

Repeat for all four: `densenet stage1`, `densenet stage2`, `swin stage1`, `swin stage2`.

**How to read the epoch lines:** training accuracy should rise steadily _together_ with validation
accuracy. If training accuracy stalls near chance while validation looks fine, something is wrong in the
training data path — see the two real bugs we found in [Chapter 15](15-results-and-lessons.md).

## 9.5 Step 2 — `calibrate.py`: honest confidence

```bash
python calibrate.py --all --cache --workers 0
```

For each model, collects validation-set logits and finds the temperature _T_ that minimises the
cross-entropy (Chapter 5.13). Prints e.g. `densenet_stage2: T = 2.1501 | ECE 0.1244 -> 0.0239` and writes
`backend/weights/temperature.json`. (If the validation set is tiny or perfectly separated, _T_ is
clamped to 0.05–20 and a warning is shown.)

## 9.6 Step 3 — `evaluate.py`: the final exam

```bash
python evaluate.py --cache --workers 0
```

Runs each model on the **test** split (never seen before) and computes accuracy, precision,
sensitivity, specificity, F1, ROC-AUC, the confusion matrix, the ROC curve and a calibration curve. It
also evaluates the **full two-stage pipeline** as a 3-class problem, and — when the CSV mixes children
and adults — repeats everything **per population**. Writes:

- `backend/metrics/metrics.json` → the Performance dashboard;
- `training/outputs/figures/*.png` → ROC, confusion-matrix and calibration plots for your report.

## 9.7 Step 4 — `external_validate.py`: a hospital the model never saw

```bash
python external_validate.py --name "Actualmed (unseen hospital, adults)" \
  --csv data/external/actualmed.csv --cache --workers 0
```

Stage 1 only (external sets rarely have bacterial/viral labels). Reports the metrics and the **drop**
versus the internal test set, shown in the dashboard's _External Validation_ tab. It also accepts the
RSNA challenge format (`--rsna-labels`, `--rsna-images`) if you download it from Kaggle.

## 9.8 Step 5 — `gradcam_analysis.py`: looking inside

```bash
python gradcam_analysis.py --arch densenet --per-category 6 --max-images 400
python gradcam_analysis.py --arch swin     --per-category 6 --max-images 400
```

Computes Grad-CAM for up to 400 test images, measures in-lung attention, sorts cases into correct /
misclassified / failure, saves gallery images to `backend/metrics/gallery/` and a summary to
`training/outputs/gradcam_summary_<arch>.json`.

## 9.9 Step 6 — exports for the app

```bash
python export_samples.py         # 6 example X-rays from the TEST split → backend/samples/
python export_onnx.py --verify   # .onnx copies of the 4 models → backend/weights/
```

`export_onnx.py` builds the "logits + Grad-CAM" graph described in Chapter 7.4, checks it against
PyTorch with `--verify`, and stores Swin's matrix weights in 8 bits (per-channel, unsigned) so each
file is under GitHub's 100 MB limit and the online server fits in 512 MB of memory — with 99%+ of
predictions identical and the same AUC. Use `--fp32` to skip the 8-bit step.

## 9.10 Training on Google Colab (free GPU)

1. Push the project to your GitHub (Chapter 13) or upload it as a zip.
2. Open https://colab.research.google.com → _File → Upload notebook_ → `training/notebooks/train_colab.ipynb`.
3. _Runtime → Change runtime type → GPU_.
4. Edit the first code cell's `REPO_URL`, then run the cells in order (_Runtime → Run all_). The notebook
   downloads Kermany (with a Kaggle token — instructions inside; or use `download_data.py kermany`
   instead), splits it, trains all four models, calibrates, and zips the weights for download.
5. `evaluate_colab.ipynb` runs evaluation, Grad-CAM and optional external validation the same way.
6. Unzip the downloaded weights into `backend/weights/`, then run `python export_onnx.py` locally.

## 9.11 Comparing versions safely

If you retrain with different data or settings, **do not simply replace the old models**. Use
`compare_versions.py`: it compares the new and old models on the **same** test images — the pediatric
test set and the unseen-hospital set — and accepts the new version only if its AUC is not worse
anywhere. We learned why the hard way ([Chapter 15](15-results-and-lessons.md)).

For the adult experiment:

```bash
python download_data.py                    # all datasets
python prepare_adult.py                    # → data/splits_combined.csv, data/external/actualmed.csv
bash run_pipeline.sh --epochs 10 --patience 4 --warmup-epochs 0.5    # uses splits_combined.csv
```

## 9.12 Other scripts

| Script                  | Purpose                                                                                                                       |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `train_validator.py`    | Train a MobileNetV3 "is this a chest X-ray?" classifier from `data/validator/{cxr,other}` (Chapter 8.7)                       |
| `watch_and_activate.py` | Follow a running pipeline, show live progress in the app, and switch to new models only if `compare_versions.py` accepts them |
| `_common.py`            | Shared helpers: device selection, loading models, collecting logits                                                           |
| `dataset.py`            | The PyTorch dataset: loading, the on-disk cache, augmentation                                                                 |

## 9.13 Reproducibility

Seeds are fixed (`--seed 42`), the split is deterministic, and every hyper-parameter is saved next to
the weights. Results can still differ slightly between machines (GPU arithmetic is not perfectly
deterministic) — expect test AUCs within about ±0.005 of ours.

---

Next: how the backend code works → [Chapter 10](10-backend-walkthrough.md)
