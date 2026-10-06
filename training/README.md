# Training & evaluation

> New here? The step-by-step course is in [docs/guide](../docs/guide/14-training-pipeline.md) — start with
> [Chapter 13 (data)](../docs/guide/13-data.md) and [Chapter 14 (training)](../docs/guide/14-training-pipeline.md).

Scripts to train, calibrate and evaluate the PneumoScan AI models. They import preprocessing,
model definitions, calibration and metric code directly from `backend/app`, so **inference
always matches training**.

A GPU is strongly recommended. Use the notebooks in [`notebooks/`](notebooks/) on Google Colab or Kaggle:

| Notebook               | What it does                                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `train_colab.ipynb`    | Download data → patient-grouped split → train DenseNet121 & Swin (Stage 1, Stage 2) → calibrate → download weights |
| `evaluate_colab.ipynb` | Internal test metrics + figures → Grad-CAM gallery → RSNA external validation → download metrics                   |

## Datasets

### Primary — Kermany et al., _Chest X-Ray Images (Pneumonia)_

- 5,856 anterior-posterior chest X-rays from Guangzhou Women and Children's Medical Center.
- Labels: `NORMAL`, and `PNEUMONIA` subdivided into **bacterial** and **viral** via filenames
  (`person1_bacteria_1.jpeg`, `person1_virus_6.jpeg`).
- **Pediatric patients aged 1–5, single hospital** — expect reduced performance on adults and other sites.
- Kaggle: `paultimothymooney/chest-xray-pneumonia` (CC BY 4.0). Original: Mendeley Data, doi:10.17632/rscbjbr9sj.

### External validation (Stage 1 only)

These sets have no viral/bacterial labels, so only Normal-vs-Pneumonia is evaluated:

- **RSNA Pneumonia Detection Challenge** (adult CXRs from NIH ChestX-ray14; `Target = 1` → pneumonia).
  Its negative class includes "not normal, no lung opacity" images — a deliberately harder, shifted domain.
- Optionally **NIH ChestX-ray14** (“Pneumonia” finding label) or any CSV of `path,label`.

> Testing with real patient X-rays must only be done with informed consent and appropriate
> institutional / ethics approval.

## Pipeline

```bash
pip install -r requirements.txt

# 0. Download the datasets from their original sources (no accounts needed)
python download_data.py kermany        # or just: python download_data.py   (everything)

# 1. Fresh 70/15/15 split grouped by patient (no leakage; Kaggle's 16-image val folder is NOT used)
python prepare_data.py --data-root data/raw/chest_xray --out data/splits.csv

# 2. Train — identical settings for both architectures
python train.py --arch densenet --task stage1
python train.py --arch densenet --task stage2
python train.py --arch swin     --task stage1
python train.py --arch swin     --task stage2
#    optional single 3-class model, to compare approaches
python train.py --arch densenet --task three_class

# 3. Temperature scaling on the validation set -> backend/weights/temperature.json
python calibrate.py --all

# 4. Internal test-set evaluation -> backend/metrics/metrics.json + outputs/figures/*.png
python evaluate.py

# 5. Grad-CAM gallery + lung-attention statistics
python gradcam_analysis.py --arch densenet
python gradcam_analysis.py --arch swin

# 6. External validation (Stage 1)
python external_validate.py --name "RSNA Pneumonia Detection" \
  --rsna-labels rsna/stage_2_train_labels.csv --rsna-images rsna/stage_2_train_images --limit 3000

# 7. Input validator (CXR vs non-CXR)
python train_validator.py --data data/validator   # folders: cxr/ and other/
```

Then export real demo samples from the test split (`python export_samples.py`) and restart the API.

On a Mac or CPU add `--cache` to `train.py`, `calibrate.py` and `evaluate.py`: preprocessed 224 px images are cached in `data/cache/`, which makes epochs several times faster.

## Design choices

| Item            | Choice                                                                                                                                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Preprocessing   | grayscale → resize 224×224 (INTER_AREA) → CLAHE (clip 2.0, 8×8) → 3 channels → ImageNet mean/std. Recorded in `weights/<model>.json`; `--no-clahe` to disable (the API follows automatically).                                                                            |
| Augmentation    | rotation ±7°, zoom 0.92–1.08, translation ±4 %, brightness/contrast ±10 %. **No horizontal flip** by default (heart position matters); `--hflip` to enable.                                                                                                               |
| Models          | `timm` `densenet121` and `swin_tiny_patch4_window7_224`, ImageNet-pretrained, new 2/3-class head.                                                                                                                                                                         |
| Optimisation    | AdamW, lr 1e-4, wd 1e-4, batch 32, 25 epochs, 1 warm-up epoch + cosine decay, grad-clip 5, mixed precision on CUDA. Same for both architectures.                                                                                                                          |
| Imbalance       | Class-weighted cross-entropy (inverse frequency).                                                                                                                                                                                                                         |
| Model selection | Early stopping on validation ROC-AUC (patience 6); best epoch saved.                                                                                                                                                                                                      |
| Calibration     | Single temperature per model fitted on validation NLL (L-BFGS), clamped to [0.05, 20]. ECE reported before/after.                                                                                                                                                         |
| Metrics         | Accuracy, precision, recall/sensitivity, specificity, F1, ROC-AUC, confusion matrix, ROC and reliability curves. Positive class: PNEUMONIA (Stage 1), VIRAL (Stage 2); macro-averaged for 3-class. The two-stage pipeline is also scored end-to-end as a 3-class problem. |
| Grad-CAM        | DenseNet: `features.denseblock4`. Swin: final `norm` with an NHWC→NCHW reshape transform. Lung attention = share of CAM mass inside a template/Otsu-refined lung mask.                                                                                                    |

## Outputs

| Path                                                        | Content                                                                                 |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `backend/weights/<arch>_<task>.pth`                         | best state_dict                                                                         |
| `backend/weights/<arch>_<task>.json`                        | preprocessing + hyper-parameters + best epoch                                           |
| `backend/weights/temperature.json`                          | `{"densenet_stage1": 1.31, ...}`                                                        |
| `backend/weights/validator.pth`                             | input validator                                                                         |
| `backend/metrics/metrics.json`                              | everything the Performance dashboard shows (replaces the demo file on first real write) |
| `backend/metrics/gallery/*.jpg`                             | Grad-CAM gallery images                                                                 |
| `training/outputs/figures/*.png`                            | ROC, confusion-matrix and calibration plots for the report                              |
| `training/outputs/history_*.json`, `gradcam_summary_*.json` | training logs and attention statistics                                                  |

All scripts accept `--weights-dir`, `--metrics-path` and `--splits` to write elsewhere, and `--help` for every option.
