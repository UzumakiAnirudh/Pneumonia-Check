# Chapter 5 — Deep learning from zero

[← Chapter 4](04-programming-basics.md) · [README](../../README.md) · Next: [Chapter 6 →](06-densenet-and-swin.md)

No maths beyond school level is assumed. Every formula is followed by a plain-English reading and,
where useful, a worked example.

---

## 5.1 What "machine learning" means

Ordinary programming: a human writes the rules ("if the lower lung is white, say pneumonia").
**Machine learning:** we show the computer thousands of **examples with answers** (X-ray → "Normal",
X-ray → "Pneumonia") and it _finds the rules itself_ by adjusting millions of numbers until its
answers match. This is **supervised learning**; the answers are **labels**.

A **neural network** is a particular kind of adjustable function made of many simple units stacked in
layers. **Deep learning** = neural networks with many layers. Our networks have ~7 million (DenseNet121)
and ~27.5 million (Swin-T) adjustable numbers, called **parameters** or **weights**.

## 5.2 An image is just numbers

A grayscale X-ray is a grid of pixels; each pixel is a number from 0 (black) to 255 (white).
A 224 × 224 image is 50,176 numbers. Colour images have 3 grids (red, green, blue) — **channels**.
Our X-rays are grayscale, so we copy the gray grid into 3 channels because the networks were
originally built for colour photos.

```
    0   12   40  ...      ← each number = brightness of one pixel
   10   55  130  ...
   ...
```

In code an image is a NumPy array of **shape** `(224, 224)`; a batch of 32 colour-format images for
the network is a **tensor** of shape `(32, 3, 224, 224)` — (batch, channels, height, width).

## 5.3 Preprocessing — making images comparable

Before the network sees an image (`backend/app/services/preprocessing.py`):

1. **Grayscale** — remove any colour.
2. **Resize to 224 × 224** with area interpolation (averages pixels when shrinking — avoids jagged
   edges). The networks expect this size.
3. **CLAHE** — _Contrast Limited Adaptive Histogram Equalisation_. It splits the image into an 8×8
   grid of tiles and stretches the contrast inside each tile, with a limit (clip = 2.0) so noise is
   not amplified. Faint lung patterns become clearer, and X-rays from different machines look more
   alike.
4. **3 channels + normalise** — divide by 255 to get 0–1, then subtract the ImageNet mean
   (0.485, 0.456, 0.406) and divide by the standard deviation (0.229, 0.224, 0.225), because the
   pretrained networks learned on images normalised this way.

The exact same steps run during training and in the app. If they differed even slightly, accuracy
would silently drop — this is why training imports the backend's preprocessing module.

## 5.4 A single neuron

A neuron takes inputs x₁…xₙ, multiplies each by a weight w, adds a bias b, and applies an
**activation function**:

```
z = w₁x₁ + w₂x₂ + ... + wₙxₙ + b        (a weighted sum)
output = ReLU(z) = max(0, z)            (keep positives, zero negatives)
```

_Example:_ inputs (0.5, 0.2), weights (2, −1), bias 0.1 → z = 1.0 − 0.2 + 0.1 = 0.9 → ReLU → 0.9.

Without the activation, stacking layers would collapse into one big weighted sum; the **non-linearity**
is what lets deep networks represent complicated patterns. We use **ReLU** (DenseNet) and **GELU**
(Swin, a smooth version of ReLU).

## 5.5 From scores to probabilities — softmax

The last layer outputs one raw score per class, called **logits**, e.g. Normal: 1.2, Pneumonia: 3.4.
**Softmax** turns them into probabilities that add up to 1:

```
p_i = e^{z_i} / Σ_j e^{z_j}
```

_Example:_ e^1.2 = 3.32, e^3.4 = 29.96 → P(Pneumonia) = 29.96 / 33.28 = **0.90**.

The predicted class is the one with the highest probability (the **arg-max**).

## 5.6 How a network learns

### The loss — measuring "how wrong"

For classification we use **cross-entropy loss**: `loss = −log(p_correct)`.

- Correct class given probability 0.9 → loss = 0.105 (small, good).
- Correct class given probability 0.1 → loss = 2.30 (large, bad).

### Gradient descent — improving step by step

The **gradient** tells us, for every weight, which direction (up/down) would reduce the loss, and
how strongly. We nudge every weight a little in that direction:

```
w_new = w_old − learning_rate × gradient
```

Picture standing on a foggy hill and always stepping downhill; the **learning rate** is the step
size. Too big → you overshoot; too small → you never arrive. We use **1 × 10⁻⁴**.

**Backpropagation** is the efficient algorithm (the chain rule from calculus) that computes all
gradients at once, from the loss backwards through every layer. PyTorch does it for you:
`loss.backward()`.

### The training loop

```
for each epoch:                         # one pass over all training images
    for each batch of 32 images:
        predictions = model(images)     # forward pass
        loss = cross_entropy(predictions, labels)
        loss.backward()                 # gradients
        optimizer.step()                # update weights
    measure performance on the validation set
```

- **Batch** — process 32 images at once (faster, smoother gradients).
- **Epoch** — one full pass over the training set.
- **Optimizer** — the rule for updating weights. We use **AdamW**, which adapts the step size for each
  weight and adds **weight decay** (gently pulling weights towards zero to avoid overfitting).
- **Learning-rate schedule** — start with a short **warm-up** (slowly increase the rate so early
  big gradients do not wreck the pretrained weights), then **cosine decay** (smoothly lower it so the
  model settles into a good solution).
- **Gradient clipping** (max norm 5) — caps unusually large updates.
- **Mixed precision** — on NVIDIA GPUs, computing in 16-bit floats where safe is ~2× faster.

## 5.7 Train, validation, test — and why we split by patient

| Split          | Share | Used for                                                      |
| -------------- | ----- | ------------------------------------------------------------- |
| **Train**      | 70%   | Learning the weights                                          |
| **Validation** | 15%   | Choosing the best epoch, early stopping, calibration          |
| **Test**       | 15%   | **Only** the final, honest score. Never used for any decision |

**Data leakage:** some patients have several X-rays. If one of a patient's X-rays is in _train_ and
another in _test_, the model can recognise the _person_ rather than the disease and the test score is
inflated. We therefore split **by patient** — all of a patient's images go to the same split
(`training/prepare_data.py`).

## 5.8 Overfitting and how we fight it

**Overfitting**: the model memorises the training images instead of learning general patterns — training
accuracy keeps rising while validation accuracy stalls or falls.

Defences used here:

- **Transfer learning** (5.10) — start from knowledge learned on 1.2 million photos.
- **Data augmentation** — each epoch, randomly rotate (±7°), zoom (0.92–1.08), shift (±4%), and change
  brightness/contrast (±10%) of training images, so the model never sees the exact same image twice.
  **No horizontal flips:** the heart is on the left side of the body; flipping would create
  anatomically impossible images.
- **Weight decay** (AdamW).
- **Early stopping** — keep the epoch with the best validation AUC; stop if no improvement for several epochs.

## 5.9 Convolutional neural networks (CNNs)

Connecting every pixel to every neuron would need billions of weights. A **convolution** instead
slides a small **filter** (e.g. 3×3 numbers) across the image; at each position it computes a weighted
sum of the 9 pixels underneath. The _same_ 9 weights are reused everywhere — so a filter that detects
"a vertical edge" detects it anywhere in the image.

```
image patch      filter        result
 1  1  1        -1  0  1
 0  0  0    ×   -1  0  1   →  sum of products = one number in the output "feature map"
 1  1  1        -1  0  1
```

- **Feature map** — the output of one filter over the whole image. A layer has many filters → many
  feature maps → **channels** (e.g. 64).
- **Stride** — how far the filter jumps each step (stride 2 halves the size).
- **Pooling** — shrink a feature map by taking the max or average of small blocks.
- **Receptive field** — how much of the original image one neuron "sees". It grows with depth:
  early layers detect edges, middle layers textures (ribs, vessels), deep layers whole structures
  (an opacity in the lower lobe).
- **Batch Normalization (BN)** — rescales each channel to a stable range during training, which makes
  deep networks train much faster and more reliably.
- **Global average pooling (GAP)** — at the end, average each feature map to one number, giving a
  vector (1024 numbers for DenseNet) that a final **linear layer** turns into class scores.

## 5.10 Transfer learning

Both networks first learned on **ImageNet** (1.2 million everyday photos, 1,000 classes). Their early
layers already detect edges, textures and shapes — useful for X-rays too. We replace only the last layer
with a new 2-class layer and **fine-tune** the whole network on X-rays. This needs far less data and
time than learning from scratch, and generalises better.

## 5.11 Class imbalance

The children's dataset has about 2.7× more pneumonia than normal images. A lazy model could say
"pneumonia" always and be 73% accurate. We use a **class-weighted loss**: mistakes on the rarer class
cost more. Weight for class _c_ = total / (number of classes × count of _c_) — e.g. Normal 1.84,
Pneumonia 0.69.

## 5.12 Measuring performance — every metric explained

A **confusion matrix** counts the four outcomes (positive = pneumonia):

|                        | Predicted Normal                      | Predicted Pneumonia               |
| ---------------------- | ------------------------------------- | --------------------------------- |
| **Actually Normal**    | True Negative (TN)                    | False Positive (FP) — false alarm |
| **Actually Pneumonia** | False Negative (FN) — **missed case** | True Positive (TP)                |

_Example_ (DenseNet121, 879 test children): TN = 218, FP = 9, FN = 14, TP = 638.

| Metric                   | Formula              | Plain meaning                                                                                             | Example         |
| ------------------------ | -------------------- | --------------------------------------------------------------------------------------------------------- | --------------- |
| **Accuracy**             | (TP+TN)/all          | Share of all answers that are right                                                                       | 856/879 = 97.4% |
| **Sensitivity / Recall** | TP/(TP+FN)           | Of the sick, how many did we catch?                                                                       | 638/652 = 97.9% |
| **Specificity**          | TN/(TN+FP)           | Of the healthy, how many did we correctly clear?                                                          | 218/227 = 96.0% |
| **Precision**            | TP/(TP+FP)           | When we say "pneumonia", how often is it true?                                                            | 638/647 = 98.6% |
| **F1-score**             | 2·P·R/(P+R)          | Balance of precision and recall                                                                           | 98.2%           |
| **ROC-AUC**              | area under ROC curve | Probability a random sick case gets a higher score than a random healthy one (1.0 perfect, 0.5 coin flip) | 0.996           |

**ROC curve:** sweep the decision threshold from 0 to 1; at each threshold plot sensitivity (y) against
1 − specificity (x). A curve hugging the top-left corner = excellent. AUC summarises it in one number,
independent of any particular threshold.

For 3 classes, metrics are computed per class and averaged (**macro average**).

For screening, **sensitivity matters most** (a missed pneumonia is worse than a false alarm), but very
low specificity floods doctors with false alarms — both must be reported.

## 5.13 Calibration — can we trust the percentages?

A model is **calibrated** if, among all cases where it says "90%", about 90% are correct. Modern
networks tend to be **over-confident**.

**Temperature scaling** (Guo et al., 2017) fixes this with one number _T_ per model:

```
p = softmax(logits / T)
```

T > 1 softens over-confident predictions, T < 1 sharpens under-confident ones. It never changes which
class wins, only the confidence. We find T by minimising cross-entropy on the **validation** set
(`training/calibrate.py`). Our values: DenseNet Stage 1 0.95, Stage 2 2.15, Swin Stage 1 1.52, Stage 2 1.32
— the bacterial/viral models were the most over-confident.

**ECE (Expected Calibration Error)** measures calibration: group predictions into confidence bins, and
average |accuracy − confidence| weighted by bin size. Lower is better (0 = perfect). The dashboard's
_reliability diagram_ plots accuracy against confidence; a perfectly calibrated model lies on the diagonal.

## 5.14 Generalisation, domain shift and shortcut learning

A model is only proven on data like its test set. **Domain shift** = new data differs (different
hospital, X-ray machine, patient ages). **Shortcut learning** = the model latches onto an accidental
clue that happens to correlate with the label — e.g. "all normal images in my training set came from
hospital A". It then looks brilliant on a test set with the same accident and fails elsewhere.

We hit exactly this — the full story, with numbers, is in [Chapter 15](15-results-and-lessons.md).
The defence is **external validation**: test on a source the model never trained on, where the
shortcut cannot work.

---

Next: the two architectures in depth → [Chapter 6](06-densenet-and-swin.md)
