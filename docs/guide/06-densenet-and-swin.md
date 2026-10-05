# Chapter 6 — DenseNet121 and Swin Transformer, from zero to mastery

[← Chapter 5](05-deep-learning-fundamentals.md) · [README](../../README.md) · Next: [Chapter 7 →](07-explainability-gradcam.md)

We compare two very different ways of "seeing": a **convolutional network** (DenseNet121, 2017) and a
**vision transformer** (Swin-Tiny, 2021). Both are created in one line with the `timm` library
(`backend/app/models/architectures.py`), but understanding _what is inside_ lets you choose, debug,
explain and improve them.

All shapes below were measured on the real models; you can reproduce them with the script in §6.5.

---

## Part 1 — DenseNet121

### 6.1 The problem it solves

Very deep CNNs used to be hard to train: gradients shrank as they travelled back through many layers
("vanishing gradients"). **ResNet** (2015) added _shortcuts_ that **add** a layer's input to its output.
**DenseNet** (Huang et al., 2017) goes further: inside a block, **every layer receives the outputs of
_all_ previous layers, concatenated**:

```
x₁ = H₁([x₀])
x₂ = H₂([x₀, x₁])
x₃ = H₃([x₀, x₁, x₂])          [ ... ] = stack along the channel dimension
```

Benefits: features are **reused** (no need to re-learn them), every layer has a short path to the loss
(strong gradients), and the network needs **fewer parameters** for the same accuracy.

### 6.2 The building blocks

- **Growth rate k = 32** — each layer adds just 32 new channels to the "collective knowledge".
- **Dense layer H** (a "bottleneck"): `BN → ReLU → 1×1 conv (to 4k = 128 channels) → BN → ReLU → 3×3 conv (to k = 32)`.
  The 1×1 conv cheaply squeezes the growing input before the expensive 3×3 conv.
- **Transition layer** (between blocks): `BN → ReLU → 1×1 conv (halves the channels, "compression" θ = 0.5) → 2×2 average pool (halves width and height)`.

### 6.3 The whole network, layer by layer (input 224 × 224)

| Stage             | Operation                             | Output (channels × H × W)          |
| ----------------- | ------------------------------------- | ---------------------------------- |
| conv0             | 7×7 conv, 64 filters, stride 2        | 64 × 112 × 112                     |
| norm0 + pool0     | BN, ReLU, 3×3 max-pool stride 2       | 64 × 56 × 56                       |
| **Dense block 1** | 6 dense layers: 64 + 6×32             | **256** × 56 × 56                  |
| Transition 1      | halve channels and size               | 128 × 28 × 28                      |
| **Dense block 2** | 12 layers: 128 + 12×32                | **512** × 28 × 28                  |
| Transition 2      |                                       | 256 × 14 × 14                      |
| **Dense block 3** | 24 layers: 256 + 24×32                | **1024** × 14 × 14                 |
| Transition 3      |                                       | 512 × 7 × 7                        |
| **Dense block 4** | 16 layers: 512 + 16×32                | **1024 × 7 × 7** ← Grad-CAM target |
| norm5             | BN + ReLU                             | 1024 × 7 × 7                       |
| Head              | global average pool → linear 1024 → 2 | 2 logits                           |

**Why "121"?** 1 first conv + (6+12+24+16) dense layers × 2 convs each (= 116) + 3 transition convs +
1 final linear layer = **121** layers with weights.

**Size:** 6.96 million parameters (with our 2-class head) — tiny by modern standards. Model file: 28 MB.

**Each output position "sees" a large area:** after four downsamplings each of the 7 × 7 final
positions summarises a 32 × 32-pixel region of the input, with a receptive field covering most of the
image.

### 6.4 Strengths and weaknesses for X-rays

| ✔ Strengths                                                                                       | ✘ Weaknesses                                                                              |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Excellent with limited data; the classic architecture for chest X-rays (CheXNet used DenseNet121) | Concatenation uses a lot of GPU memory during training                                    |
| Convolutions build in useful assumptions: nearby pixels relate; a pattern means the same anywhere | Mostly _local_ reasoning; relating distant regions (left vs right lung) takes many layers |
| Grad-CAM works naturally on its feature maps                                                      | Slower on CPUs than its parameter count suggests                                          |

---

## Part 2 — Swin Transformer (Tiny)

### 6.5 From words to pictures: attention

Transformers came from language. Their core operation, **self-attention**, lets every element of a
sequence look at every other element and decide how much to pay attention to it.

Each element (a **token** — here, a small patch of the image represented by a vector) produces three
vectors via learned weight matrices:

- **Query** Q — "what am I looking for?"
- **Key** K — "what do I contain?"
- **Value** V — "what information do I pass on?"

```
Attention(Q, K, V) = softmax( Q·Kᵀ / √d  +  B ) · V
```

Reading it: compare my query with every key (dot product = similarity); divide by √d (keeps numbers
stable); softmax turns similarities into weights that sum to 1; the output is the weighted average of
the values. **B** is a _relative position bias_ (§6.7). **Multi-head** attention runs several of these
in parallel (e.g. 3, 6, 12, 24 heads), each free to focus on different relationships, then combines
them.

**Vision Transformer (ViT, 2020)** cut an image into 16×16 patches and ran attention between _all_
patches. Two problems: cost grows with the **square** of the number of patches, and there is only one
scale — bad for high-resolution, multi-scale images like X-rays.

### 6.6 Swin's two ideas

**1. Hierarchy (like a CNN).** Start with small 4×4 patches; after each stage, **patch merging** groups
every 2×2 neighbouring tokens (concatenates their 4 vectors → 4C), then a linear layer reduces to 2C.
Resolution halves, channels double — exactly like a CNN's feature pyramid.

**2. Local windows, shifted.** Attention is computed only **within non-overlapping 7×7 windows**
(49 tokens), so cost grows _linearly_ with image size:

```
Global attention cost:  4·h·w·C² + 2·(h·w)²·C       (quadratic in h·w)
Window attention cost:  4·h·w·C² + 2·M²·h·w·C      (linear,  M = 7)
```

But then windows never talk to each other. So every second block uses **shifted windows**: the window
grid is moved by ⌊M/2⌋ = 3 tokens, so the new windows straddle the old boundaries and information flows
across them. Implementation trick: _cyclically shift_ the feature map, compute attention in regular
windows, and use a **mask** so tokens that were not originally neighbours do not attend to each other.

```
Block 2k:    W-MSA   — regular windows          ┌──┬──┐
Block 2k+1:  SW-MSA  — windows shifted by 3     │ ┼ │   ← crosses old borders
```

### 6.7 Relative position bias

Attention by itself ignores _where_ tokens are. Swin adds a learned bias **B** that depends only on the
_relative_ offset between two tokens in a window (−6…+6 in each direction → a 13 × 13 table per head).
"The token two to my left" has the same bias everywhere in the image — a built-in notion of geometry.

### 6.8 One Swin block

```
x = x + (S)W-MSA( LayerNorm(x) )          ← attention, with a residual (skip) connection
x = x + MLP( LayerNorm(x) )               ← MLP = Linear(C→4C) → GELU → Linear(4C→C)
```

**LayerNorm** normalises each token's vector (the transformer counterpart of BatchNorm). Residual
connections, as in ResNet, keep gradients healthy.

### 6.9 The whole network (Swin-T, input 224 × 224)

| Stage       | What happens                                | Tokens (H × W)                    | Channels | Blocks | Heads |
| ----------- | ------------------------------------------- | --------------------------------- | -------- | ------ | ----- |
| Patch embed | 4×4 patches (48 values) → linear → 96       | 56 × 56                           | 96       | —      | —     |
| **Stage 1** | 2 Swin blocks (W, SW)                       | 56 × 56                           | 96       | 2      | 3     |
| **Stage 2** | patch merging + 2 blocks                    | 28 × 28                           | 192      | 2      | 6     |
| **Stage 3** | patch merging + 6 blocks                    | 14 × 14                           | 384      | 6      | 12    |
| **Stage 4** | patch merging + 2 blocks                    | 7 × 7                             | 768      | 2      | 24    |
| Final norm  | LayerNorm                                   | **7 × 7 × 768** ← Grad-CAM target |          |        |       |
| Head        | average over the 49 tokens → linear 768 → 2 | 2 logits                          |          |        |       |

**Size:** 27.52 million parameters; model file 113 MB in full precision (31 MB in the 8-bit version used online).

Note the shapes at the end match DenseNet's spatial grid (7 × 7) — which is why Grad-CAM produces a
7 × 7 map for both, upsampled onto the X-ray.

### 6.10 Strengths and weaknesses for X-rays

| ✔ Strengths                                                                        | ✘ Weaknesses                                                             |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Attention can relate distant regions (both lungs) within one layer at later stages | Needs more data to train well; we rely heavily on ImageNet pretraining   |
| Best scores in our Stage 1 test (AUC 0.999, specificity 99.1%)                     | Its Grad-CAM is blockier and often spreads outside the lungs (Chapter 7) |
| Hierarchical features like a CNN — strong all-round backbone                       | 4× more parameters and memory than DenseNet121                           |

---

## Part 3 — Side by side

|                                   | DenseNet121                          | Swin-T                                       |
| --------------------------------- | ------------------------------------ | -------------------------------------------- |
| Family                            | CNN (convolutions)                   | Vision transformer (windowed self-attention) |
| Core operation                    | 3×3 convolution, dense concatenation | Multi-head attention in 7×7 windows, shifted |
| Normalisation                     | BatchNorm                            | LayerNorm                                    |
| Activation                        | ReLU                                 | GELU                                         |
| Parameters                        | 6.96 M                               | 27.52 M                                      |
| Last feature map                  | 7 × 7 × 1024                         | 7 × 7 × 768                                  |
| Our test AUC, Normal vs Pneumonia | 0.996                                | 0.999                                        |
| Our test AUC, Bacterial vs Viral  | 0.838                                | 0.850                                        |
| `timm` name                       | `densenet121`                        | `swin_tiny_patch4_window7_224`               |

Both were trained with **identical** settings (same data, augmentation, optimiser, learning rate,
epochs) so the comparison is fair — a requirement for any scientific claim that one is better.

## 6.11 See it yourself (exercise)

With the full backend installed (`pip install -r backend/requirements.txt`), run from `backend/`:

```python
import torch, timm
m = timm.create_model("densenet121", pretrained=False, num_classes=2).eval()
x = torch.zeros(1, 3, 224, 224)
for name, layer in m.features.named_children():
    x = layer(x); print(name, tuple(x.shape[1:]))
print(sum(p.numel() for p in m.parameters()) / 1e6, "M parameters")

s = timm.create_model("swin_tiny_patch4_window7_224", pretrained=False, num_classes=2).eval()
x = s.patch_embed(torch.zeros(1, 3, 224, 224)); print("patch_embed", tuple(x.shape[1:]))
for i, stage in enumerate(s.layers):
    x = stage(x); print(f"stage{i+1}", tuple(x.shape[1:]), len(stage.blocks), "blocks")
```

Try: change the input to 448 × 448 — what happens to every shape? (DenseNet: all spatial sizes
double. Swin: also double; the 7 × 7 windows stay 7 × 7 but there are 4× as many.)

## 6.12 How to go further

1. Read the papers (both are readable): Huang et al., _Densely Connected Convolutional Networks_
   (CVPR 2017); Liu et al., _Swin Transformer: Hierarchical Vision Transformer using Shifted Windows_
   (ICCV 2021); Dosovitskiy et al., _An Image is Worth 16x16 Words_ (ViT, 2021); Vaswani et al.,
   _Attention Is All You Need_ (2017).
2. Implement a dense block and a single window-attention layer yourself in ~50 lines of PyTorch each,
   and check your output shapes against the tables above.
3. Swap in another `timm` model (e.g. `convnext_tiny`, `efficientnet_b0`) — add an entry to `ARCHS`
   in `backend/app/models/specs.py`, choose its Grad-CAM target layer, and train with the same
   settings (Chapter 9). Compare fairly on the same test set and external set.

---

Next: how the heatmaps are computed → [Chapter 7](07-explainability-gradcam.md)
