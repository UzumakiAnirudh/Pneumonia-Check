# Chapter 15 — Train the models from scratch, step by step

[← Chapter 14](14-training-pipeline.md) · [README](../../README.md) · Next: [Chapter 16 →](16-backend-walkthrough.md)

Chapter 14 is the _reference_ for each training script. This chapter is the **hands-on walkthrough**:
every click and command, what you should see, how long it takes, and how to check each result before
moving on. Pick **one** route.

| Route                     | You need                                                       | Time                     | Best for                          |
| ------------------------- | -------------------------------------------------------------- | ------------------------ | --------------------------------- |
| **A — Google Colab**      | A Google account, a browser                                    | ~1–1.5 h, mostly waiting | Anyone; no installation; free GPU |
| **B — Your own computer** | 15 GB free disk; ideally an Apple-silicon Mac or an NVIDIA GPU | ~2 h (Mac M-series)      | Full control; repeat experiments  |

At the end you will have the same kind of files the app uses: four models, their calibration, the
dashboard data, example images and the lightweight ONNX copies.

---

## Route A — Google Colab (free GPU, nothing to install)

### A.1 Open the notebook

1. Sign in to Google, open **https://colab.research.google.com**.
2. In the dialog that appears (or _File → Open notebook_), choose the **GitHub** tab.
3. Paste the repository address — `https://github.com/UzumakiAnirudh/Pneumonia-Check` (or your own
   copy) — and press Enter.
4. Click **`training/notebooks/train_colab.ipynb`**.

### A.2 Turn on the GPU

_Runtime → Change runtime type → Hardware accelerator: **T4 GPU** → Save._
(Without this, training takes many hours.)

### A.3 Run the cells, one at a time

Click into a code cell and press **Shift + Enter**. Wait for the ▶ to stop spinning before the next.

| Cell                 | What happens                                                                     | Takes     | You should see                                                                                |
| -------------------- | -------------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------- |
| 1. Get the code      | Clones the repository into `/content/project`, installs libraries, shows the GPU | 1–2 min   | `Tesla T4, 15360 MiB`                                                                         |
| 2. Download          | Downloads the 1.2 GB Kermany dataset from Mendeley Data                          | 2–5 min   | `kermany: 5856 images extracted`                                                              |
| 3. Split             | Patient-grouped 70/15/15                                                         | ~1 min    | `Wrote 5824 images (2789 patients)` and the table in Chapter 13.5                             |
| 4. Train             | Four models, one after another                                                   | 40–60 min | Epoch lines; each model ends with `Saved best weights (epoch N)`                              |
| 5. Calibrate         | Temperature scaling                                                              | 1 min     | Four lines like `densenet_stage2: T = 2.15 \| ECE 0.124 -> 0.024`                             |
| 6. Evaluate          | Test-set metrics + figures                                                       | 2 min     | Lines like `densenet stage1 n= 879 accuracy=0.97... roc_auc=0.99...` and ROC/confusion images |
| 7. Gallery + exports | Grad-CAM gallery, example images, ONNX files                                     | 5–10 min  | `Saved 18 gallery images`, `swin_stage1.onnx: 31.1 MB`                                        |
| 8. Download          | Zips everything and downloads `pneumoscan_trained.zip`                           | 1 min     | A file in your Downloads folder                                                               |

If Colab disconnects (free sessions time out after inactivity), re-run from cell 1 — already-finished
steps are quick, and each model can be retrained alone (Route B, step B.4).

### A.4 Put the results into your project

1. Unzip `pneumoscan_trained.zip`. It contains `backend/weights`, `backend/metrics`, `backend/samples` and
   `training/outputs`.
2. Copy those folders into your project folder, **replacing** the existing ones.
3. Restart the backend (Chapter 2.5) and open the app → **Settings → Model version & training** and the
   **Model Performance** page show your new results.

Skip to [Checking your results](#checking-your-results).

---

## Route B — Your own computer

### B.1 Prepare (once, ~10 minutes)

```bash
cd ~/Desktop/Pneumonia-Check/backend
python3 -m venv .venv                 # skip if it already exists
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # PyTorch, timm, grad-cam, onnx, pytest (~2–3 GB)
cd ../training
pip install -r requirements.txt       # pandas, matplotlib, scikit-learn
python -c "import torch; print(torch.__version__, 'GPU:', torch.cuda.is_available() or torch.backends.mps.is_available())"
```

Last line should print a version and `GPU: True` (on a Mac M-series or an NVIDIA PC). `False` means CPU
only: everything works, but training takes many hours — consider Route A.

**Windows + NVIDIA:** first install the CUDA build of PyTorch with the command from
https://pytorch.org/get-started/locally/, then the requirements.

### B.2 Download the data (~5 minutes)

```bash
python download_data.py kermany
```

```
kermany: download https://data.mendeley.com/... (~1.2 GB) and unzip to .../training/data/raw
  1,236 / 1,236 MB
kermany: 5856 images extracted
Done. Next: python prepare_data.py --data-root data/raw/chest_xray
```

**Check:** the folder `training/data/raw/chest_xray/train/PNEUMONIA` exists and contains `.jpeg` files.

### B.3 Split the data (~1 minute)

```bash
python prepare_data.py --data-root data/raw/chest_xray --out data/splits.csv
```

```
Wrote 5824 images (2789 patients) to data/splits.csv
label  BACTERIAL  NORMAL  VIRAL   All
split
test         427     227    225   879
train       1940    1114   1047  4101
val          393     238    213   844
```

**Check:** your numbers match (the split is deterministic).

### B.4 Train the four models (~1.5 hours on an Apple M4)

Run them one at a time so you can watch each:

```bash
python train.py --arch densenet --task stage1 --cache --workers 0 --epochs 10 --patience 4 --warmup-epochs 0.5
```

The first run builds the image cache (~20 s). Then one line per epoch. Our real DenseNet Stage 1 run:

```
densenet stage1 | device=mps | train=4101 val=844 | counts=[1114, 2987]
class weights: [1.841, 0.686]
epoch   1 | train loss 0.3244 acc 0.862 | val loss 0.1304 acc 0.954 auc 0.9890 | 135s
epoch   2 | train loss 0.1233 acc 0.959 | val loss 0.1058 acc 0.964 auc 0.9940 | 133s
epoch   3 | train loss 0.0979 acc 0.965 | val loss 0.0925 acc 0.976 auc 0.9954 | 136s
epoch   4 | train loss 0.0574 acc 0.980 | val loss 0.0958 acc 0.980 auc 0.9966 | 127s
epoch   5 | train loss 0.0386 acc 0.988 | val loss 0.0768 acc 0.974 auc 0.9968 | 121s
...
Early stopping at epoch 9 (best epoch 5, val AUC 0.9968)
Saved best weights (epoch 5) to .../backend/weights/densenet_stage1.pth
```

How to read it: **val auc** is what matters; it should climb quickly (~0.99 for Stage 1) and then
plateau. **train acc** should rise _together with_ val acc. If train acc stays far below val acc, or
falls, stop and read Chapter 22.3 — that pattern revealed two real bugs.

Then the other three:

```bash
python train.py --arch densenet --task stage2 --cache --workers 0 --epochs 10 --patience 4 --warmup-epochs 0.5
python train.py --arch swin     --task stage1 --cache --workers 0 --epochs 10 --patience 4 --warmup-epochs 0.5
python train.py --arch swin     --task stage2 --cache --workers 0 --epochs 10 --patience 4 --warmup-epochs 0.5
```

What our runs reached (best validation AUC): DenseNet Stage 1 **0.997**, Stage 2 **0.831**; Swin Stage 1
**0.998**, Stage 2 **0.850**. Stage 2 (bacterial vs viral) plateaus around 0.83–0.85 — that is the
difficulty of the task, not a bug.

Approximate time per epoch on an Apple M4: DenseNet ~2.2 min (Stage 1) / ~1.5 min (Stage 2); Swin
~2.6 min / ~2 min. An NVIDIA GPU is typically 2–4× faster.

**Check after each model:** `ls -la ../backend/weights` shows the new `.pth` (DenseNet ~28 MB, Swin
~110 MB) and `.json` files.

**Interrupted?** Just re-run that one command; the cache makes restarts quick.

### B.5 Calibrate (~2 minutes)

```bash
python calibrate.py --all --cache --workers 0
```

```
densenet_stage1: T = 0.9474 | ECE 0.0056 -> 0.0072 | n = 844
densenet_stage2: T = 2.1501 | ECE 0.1244 -> 0.0239 | n = 606
swin_stage1: T = 1.5159 | ECE 0.0157 -> 0.0061 | n = 844
swin_stage2: T = 1.3156 | ECE 0.0645 -> 0.0371 | n = 606
Wrote .../backend/weights/temperature.json
```

A temperature near 1 means the model was already well calibrated; > 1 means it was over-confident.

### B.6 Evaluate on the test set (~3 minutes)

```bash
python evaluate.py --cache --workers 0
```

```
densenet  stage1       n=  879 accuracy=0.9738 precision=0.9861 recall=0.9785 specificity=0.9604 f1=0.9823 roc_auc=0.9963
densenet  stage2       n=  652 accuracy=0.7699 ... roc_auc=0.8382
densenet  pipeline     n=  879 accuracy=0.8089 ... roc_auc=0.9301
swin      stage1       n=  879 accuracy=0.9772 precision=0.9969 recall=0.9724 specificity=0.9912 f1=0.9845 roc_auc=0.9985
swin      stage2       n=  652 accuracy=0.7745 ... roc_auc=0.8501
swin      pipeline     n=  879 accuracy=0.8203 ... roc_auc=0.9349
Updated .../backend/metrics/metrics.json; figures in .../training/outputs/figures
```

**Check:** open `training/outputs/figures/` — ROC curves, confusion matrices and calibration plots, ready
for a report.

### B.7 Grad-CAM gallery, example images, ONNX (~10 minutes)

```bash
python gradcam_analysis.py --arch densenet --per-category 6 --max-images 400
python gradcam_analysis.py --arch swin     --per-category 6 --max-images 400
python export_samples.py
python export_onnx.py --verify
```

`export_onnx.py --verify` prints, per model, the difference from PyTorch — tiny (e.g. `max logit diff
1.53e-05`) for DenseNet; Swin's 8-bit version differs a little more by design.

### B.8 (Optional) the unseen-hospital test

```bash
python download_data.py actualmed shenzhen cohen figure1     # ~3.5 GB
python prepare_adult.py
python external_validate.py --name "Actualmed (unseen hospital, adults)" --csv data/external/actualmed.csv --cache --workers 0
```

### B.9 Use your models

Restart the backend:

```bash
cd ../backend
python -m uvicorn app.main:app --port 8000
```

With PyTorch installed and `.pth` files present, the backend uses them directly (log line:
`Model backend: torch`); the website's Model Performance page shows your metrics.

### Shortcut: everything in one command

All of B.4–B.7 (and B.8 if the data is present):

```bash
SPLITS=data/splits.csv bash run_pipeline.sh --epochs 10 --patience 4 --warmup-epochs 0.5
```

---

## Checking your results

Compare with our reference run (Chapter 22.1). Because GPU arithmetic is not perfectly reproducible,
expect small differences:

| Metric                           | Our value     | Acceptable range |
| -------------------------------- | ------------- | ---------------- |
| DenseNet Stage 1 test AUC        | 0.996         | 0.990 – 0.999    |
| Swin Stage 1 test AUC            | 0.999         | 0.993 – 1.000    |
| DenseNet / Swin Stage 2 test AUC | 0.838 / 0.850 | 0.80 – 0.88      |

Much lower? Check that you used `data/splits.csv`, that the images loaded (Stage 1 val AUC should exceed
0.95 after the first epoch), and Chapter 23.

## Training "truly from scratch" (without ImageNet)

Our models start from ImageNet-pretrained weights (transfer learning, Chapter 10.10). To see why, try:

```bash
python train.py --arch densenet --task stage1 --no-pretrained --epochs 40 --patience 8 --cache --workers 0 --weights-dir outputs/scratch_weights --metrics-path outputs/scratch_metrics.json
```

(`--weights-dir` and `--metrics-path` keep it from overwriting your real models and dashboard.) Expect slower learning and a lower AUC —
a useful experiment for a report on why pretraining matters with ~4,000 training images.

## Publishing your new models online

1. `python export_onnx.py` (if not done).
2. `git add -A && git commit -m "Retrained models" && git push` — the `.onnx` files, `temperature.json`,
   metrics, gallery and samples are committed; the large `.pth` files are not.
3. Render redeploys the backend automatically (Chapter 20).

**Before replacing deployed models, compare them** with `compare_versions.py` on the same test sets
(Chapter 14.11) — a model that is better on your test split can still be worse at a new hospital
(Chapter 22.2).

---

Next: **Chapter 16 — Backend code walkthrough** → [16-backend-walkthrough.md](16-backend-walkthrough.md)
