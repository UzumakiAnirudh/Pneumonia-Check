# Chapter 7 — Explainability: how the heatmaps work

[← Chapter 6](06-densenet-and-swin.md) · [README](../../README.md) · Next: [Chapter 8 →](08-data.md)

A prediction alone ("Pneumonia, 97%") asks a doctor for blind trust. A heatmap showing _where_ the
model looked lets them check whether it focused on the lungs — or on a text marker, a tube, or the
image border. This chapter explains Grad-CAM, the method we use, all the way down to the formulas
implemented in the code.

Code: `backend/app/services/gradcam.py`, `backend/app/services/lung_mask.py`,
`training/export_onnx.py`, `training/gradcam_analysis.py`.

---

## 7.1 The intuition

The last convolutional/attention layer of each network produces a 7 × 7 grid of feature vectors (1024
numbers per cell for DenseNet, 768 for Swin). Each channel is a "detector" for some pattern; each cell
covers a region of the X-ray.

Grad-CAM asks two questions:

1. **Which channels matter for _this_ decision?** — measured by how much the class score would change
   if that channel became stronger (its **gradient**).
2. **Where are those important channels active?** — their activation maps.

Multiply the two and add them up: you get a 7 × 7 map of "evidence for the predicted class".

## 7.2 The formula (Selvaraju et al., 2017)

Let **A<sup>c</sup>** be the activation map of channel _c_ (7 × 7), and **S<sub>k</sub>** the score (logit) of
the predicted class _k_.

1. **Channel importance** — average the gradient over the 7 × 7 positions:

   ```
   α_c = (1 / 49) · Σ_{i,j} ∂S_k / ∂A^c_{ij}
   ```

2. **Weighted combination**, keeping only positive evidence:

   ```
   CAM = ReLU( Σ_c α_c · A^c )          → a 7 × 7 map
   ```

3. **Post-processing** (as in `pytorch-grad-cam`): subtract the minimum, divide by the maximum (→ 0–1),
   resize to the image size with bilinear interpolation.

4. **Colouring**: map 0 → dark blue … 1 → dark red with the **JET colour map**, and blend it over the
   X-ray (45% opacity by default; adjustable in the viewer).

## 7.3 Which layer, and why

| Model       | Target layer                              | Shape        | Why                                                     |
| ----------- | ----------------------------------------- | ------------ | ------------------------------------------------------- |
| DenseNet121 | `features.denseblock4` (last dense block) | 1024 × 7 × 7 | Highest-level features that still have a spatial layout |
| Swin-T      | `norm` (final LayerNorm)                  | 7 × 7 × 768  | Last layer before averaging away the spatial layout     |

Swin outputs "channels last" (7, 7, 768) while Grad-CAM expects "channels first" (768, 7, 7), so a small
**reshape transform** (`swin_reshape_transform` in `architectures.py`) swaps the axes.

## 7.4 Grad-CAM without PyTorch: the closed-form trick

The online server uses **ONNX Runtime**, which can run a model but **cannot compute gradients**. Our
solution: for these two networks, the layers between the target and the score are simple enough that
the gradient can be written out exactly and computed _inside_ the exported model.

**Swin** — after the target come only "average over 49 positions" and a linear layer with weights W:

```
S_k = Σ_c W[k,c] · (1/49) Σ_{ij} A_{ij,c} + b_k
⇒  ∂S_k/∂A_{ij,c} = W[k,c] / 49      (the same at every position)
⇒  α_c = W[k,c] / 49
```

**DenseNet** — after the target come BatchNorm (scale γ, shift β, running mean μ and variance σ²), ReLU,
average pooling and the linear layer:

```
pre_c,ij = γ_c (A_c,ij − μ_c)/σ_c + β_c
S_k = Σ_c W[k,c] · (1/49) Σ_{ij} ReLU(pre_c,ij) + b_k
⇒  ∂S_k/∂A_c,ij = W[k,c] · (γ_c/σ_c) · 1[pre_c,ij > 0] / 49
⇒  α_c = W[k,c] · (γ_c/σ_c) · (fraction of positions where pre > 0) / 49
```

`training/export_onnx.py` wraps each model so it returns **both** the logits and this CAM, and a
`--verify` option checks the result against `pytorch-grad-cam`: the difference is below 0.001% for the
full-precision models. This is a nice example of using maths to remove a heavy dependency.

## 7.5 Turning a heatmap into words

`describe_attention()` in `gradcam.py`:

1. Estimate the **lung fields** with `estimate_lung_mask()` (§7.6).
2. Split the lung area into **upper / middle / lower thirds** and **left / right halves**, and sum the
   attention in each of the 6 zones.
3. Report the strongest zone. If the same zone on the other side has ≥ 75% as much attention, call it
   **bilateral** ("middle zones of both lungs").
4. **Radiological convention:** X-rays are viewed as if facing the patient, so the **patient's right
   lung is on the left of the image**. The text always uses the _patient's_ side.

## 7.6 The lung mask and the "attention inside lung region" check

`lung_mask.py` builds a simple mask without a segmentation network:

1. Start from an anatomical **template** — two ellipses where lungs usually are on a frontal X-ray.
2. **Refine** it: within a slightly enlarged template, find dark (air-filled) pixels with Otsu's
   automatic threshold, keep the largest dark region on each side, and take its **convex hull** (the
   smallest shape without dents that contains it). The convex hull keeps consolidated (white) areas
   _inside_ the lung, where pneumonia actually is.
3. If the refined mask is implausibly small or large, fall back to the template.

**Attention inside lung region** = (CAM inside the mask) / (total CAM).

**How to read it:** the lungs cover only ~25% of a typical image (15–39%). So if attention were
spread evenly, about 25% would land inside them by chance. The app compares the two: if the
in-lung share is **below the lung area** (no better than chance), it warns that the model may be relying
on cues outside the lungs. Our models average ~33–38% inside the lungs on correct cases — about 1.4×
chance — and lower on failures.

## 7.7 The Grad-CAM gallery

`training/gradcam_analysis.py` runs Grad-CAM on up to 400 test images per model and sorts them into:

- **Correct** — right answer, confident, attention on the lungs;
- **Misclassified** — wrong answer;
- **Failure cases** — right answer but low confidence, or attention no better than chance.

These appear on the Performance page. Looking at failures is the best way to understand a model's
weaknesses.

## 7.8 What Grad-CAM can and cannot tell you

- ✔ It shows regions that _increased_ the predicted class's score.
- ✘ It is **coarse**: a 7 × 7 grid stretched over the image; small lesions cannot be outlined precisely.
- ✘ It shows **correlation, not causation**, and different methods (Grad-CAM++, Score-CAM, SHAP) can give
  different maps.
- ✘ A plausible-looking heatmap does not prove the model is right; a strange one is a strong warning.
- ✘ Swin's maps tend to be blockier (window structure) and to spill outside the lungs more than DenseNet's.

Use heatmaps as a **sanity check** and a teaching tool, never as a diagnosis.

---

Next: where the data comes from → [Chapter 8](08-data.md)
