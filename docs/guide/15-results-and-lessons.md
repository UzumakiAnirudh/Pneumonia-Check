# Chapter 15 — Results, lessons and how to improve

[← Chapter 14](14-testing-and-quality.md) · [README](../../README.md) · Next: [Chapter 16 →](16-troubleshooting-faq.md)

This chapter reports what the models really achieve — including where they fail — and the mistakes we
made and caught. Learning from them is worth more than any single number.

---

## 15.1 Deployed models (Version 1): results

Trained only on the Kermany children's dataset. Calibrated temperatures: DenseNet Stage 1 0.95,
Stage 2 2.15; Swin Stage 1 1.52, Stage 2 1.32.

### Children — 879 held-out test images

| Task                                                                    | Metric      | DenseNet121 | Swin-T |
| ----------------------------------------------------------------------- | ----------- | ----------- | ------ |
| **Stage 1** Normal vs Pneumonia                                         | Accuracy    | 97.4%       | 97.7%  |
|                                                                         | Sensitivity | 97.9%       | 97.2%  |
|                                                                         | Specificity | 96.0%       | 99.1%  |
|                                                                         | AUC         | 0.996       | 0.999  |
| **Stage 2** Bacterial vs Viral (652 pneumonia images; positive = viral) | Accuracy    | 77.0%       | 77.5%  |
|                                                                         | AUC         | 0.838       | 0.850  |
| **Two-stage pipeline** (3 classes, macro)                               | Accuracy    | 80.9%       | 82.0%  |
|                                                                         | AUC         | 0.930       | 0.935  |

### Adults — the same models on adult X-rays they never trained on

| Test set                                                   | Metric                                     | DenseNet121                   | Swin-T                        |
| ---------------------------------------------------------- | ------------------------------------------ | ----------------------------- | ----------------------------- |
| 142 held-out adult images (Cohen, Figure1, Shenzhen)       | Accuracy / Sensitivity / Specificity / AUC | 90.1% / 88.9% / 92.3% / 0.964 | 88.0% / 83.3% / 96.2% / 0.972 |
| **Unseen hospital** (Actualmed: 127 normal, 58 COVID-19)   | Accuracy / Sensitivity / Specificity / AUC | 78.4% / 91.4% / 72.4% / 0.914 | 86.0% / 77.6% / 89.8% / 0.923 |
| Adult **bacterial vs viral** (90 images, only 7 bacterial) | AUC                                        | 0.59                          | 0.56                          |

**What this means:**

- Detecting pneumonia in **children** is excellent and well-calibrated.
- In **adults** detection still works but is clearly weaker, and depends on the hospital.
- **Bacterial vs viral** is hard everywhere and essentially unreliable for adults — which is why the app
  always shows "confirm with clinical and laboratory tests".

## 15.2 The Version 2 experiment — a failure that teaches the most important lesson

**Goal:** fix the adult gap by adding 952 adult X-rays (Cohen, Figure1, Shenzhen) to training, with
balanced sampling (30% adults per epoch).

**Internal result — looked great:** adult accuracy jumped to 96.5% (DenseNet) and 95.8% (Swin) on the
held-out adult test images.

**External result — the truth:** on the unseen hospital it got _worse_:

| Unseen hospital                                          | Version 1 | Version 2 |
| -------------------------------------------------------- | --------- | --------- |
| DenseNet: healthy adults correctly cleared (specificity) | **72%**   | 29%       |
| DenseNet: AUC                                            | **0.914** | 0.884     |
| Swin: specificity                                        | **90%**   | 54%       |
| Swin: AUC                                                | **0.923** | 0.866     |

**Why:** in the public adult data, **every normal adult image came from one hospital (Shenzhen)** and
**almost every adult pneumonia came from COVID-19 collections**. The easiest rule the network could
learn was "looks like a Shenzhen film → normal; looks like an ICU COVID film → pneumonia". That rule
works perfectly on test images from the same sources (so internal metrics were inflated) and fails on
a new hospital. This is **shortcut learning caused by source confounding** (Chapter 5.14). The same
cause made Version 2 call almost every adult pneumonia "viral" (only 1 of 7 adult bacterial cases correct).

**What saved us:** we held out an entire hospital (Actualmed) that contained _both_ classes, so a
source-based shortcut could not score well there. `compare_versions.py` compared both versions on the
same images and Version 2 was **rejected**. It is archived, not deployed.

**Lesson:** a big internal improvement means nothing until it holds on data from somewhere new — and
normal and abnormal examples must come from the _same_ places.

## 15.3 Two real bugs we found during training (and how to spot them)

1. **Augmentation inverted dark pixels.** `cv2.convertScaleAbs(img, alpha, beta)` takes the _absolute
   value_ after scaling, so when the brightness shift was negative, black background became grey-white.
   Symptom: training accuracy far below validation accuracy. Fix: compute the change in floating point
   and **clip** to 0–255 (`training/dataset.py`). Proof: a test image with values `[0, 10, 30]` became
   `[40, 29, 7]` instead of `[0, 0, 0]`.
2. **Images paired with the wrong labels on Apple GPUs.** `tensor.to("mps", non_blocking=True)` from
   ordinary memory can finish _after_ the data loader has reused the buffer. Symptom: training accuracy
   collapsing over epochs on a Mac, while the identical command on CPU trained normally. We isolated it
   by removing one difference at a time between the real training script and a minimal copy. Fix:
   asynchronous copies only on NVIDIA GPUs (`to_device()` in `training/_common.py`).

**Lesson:** if training and validation disagree strangely, suspect the data path before the model,
and debug by **controlled comparison** (same thing, one change at a time).

## 15.4 Other limitations

- Children's data from a **single centre**; ages 1–5.
- Labels are expert gradings of images, not always laboratory-confirmed causes.
- Grad-CAM is coarse (7 × 7) and correlational (Chapter 7.8).
- The input validator is rule-based and can be fooled by unusual images.
- The online Swin model uses 8-bit weights: 99%+ of answers match the full model; borderline (~50/50)
  bacterial/viral cases can differ.
- **Not a medical device; not clinically validated.**

## 15.5 How to improve it — and prove it

| Idea                                 | How                                                                                       | How to know it helped                                                    |
| ------------------------------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Matched adult data                   | RSNA (Kaggle), NIH ChestX-ray14, CheXpert: normal _and_ pneumonia from the same hospitals | Better on Actualmed **and** no worse on children (`compare_versions.py`) |
| Lab-confirmed bacterial/viral labels | Partner with a hospital (Chapter 8.6)                                                     | Stage 2 AUC on an external set                                           |
| Learned input validator              | `train_validator.py` with photos, documents, other X-rays                                 | Fewer false accepts on a held-out set of non-X-rays                      |
| Lung segmentation                    | A U-Net trained on lung masks (e.g. Montgomery/JSRT masks) to replace the template mask   | Lung-attention numbers agree with radiologists                           |
| Higher resolution                    | Train at 384 or 512 px (`--image-size`)                                                   | AUC up, especially for subtle opacities                                  |
| Ensembles                            | Average DenseNet and Swin probabilities                                                   | Higher AUC and better calibration than either alone                      |
| Other architectures                  | ConvNeXt, EfficientNet via timm (Chapter 6.12)                                            | Same fair protocol, same test sets                                       |
| Uncertainty                          | Test-time augmentation or Monte-Carlo dropout                                             | Low-confidence flags catch more errors                                   |

Whatever you try: identical training settings for a fair comparison, the untouched test split, an
external hospital, and the same decision rule before deploying.

---

Next: fixes for common problems → [Chapter 16](16-troubleshooting-faq.md)
