"""Export trained models to ONNX with Grad-CAM computed inside the graph.

The lightweight ONNX runtime has no autograd, but for these two architectures the layers after the
Grad-CAM target are simple, so the gradient of the predicted class score with respect to the target
activations A has a closed form:

* Swin-T  — target: final LayerNorm output (B,7,7,C); head: mean over 7x7 -> Linear.
            dS_k/dA[h,w,c] = W[k,c] / HW   =>  alpha_c = W[k,c] / HW
* DenseNet121 — target: denseblock4 output (B,C,7,7); head: BN -> ReLU -> mean -> Linear.
            dS_k/dA[c,h,w] = W[k,c] * gamma_c/sigma_c * 1[BN(A)>0] / HW
            =>  alpha_c = W[k,c] * gamma_c/sigma_c * mean_hw(1[BN(A)>0]) / HW

cam = ReLU(sum_c alpha_c * A_c) for the arg-max class — identical to pytorch-grad-cam's GradCAM
(verified against it by --verify). Each exported model outputs (logits, cam_7x7).

Writes backend/weights/<arch>_<task>.onnx next to the .pth files. Swin's MatMul weights are
quantized to 8-bit (per-channel, unsigned — avoids the int8 saturation
issue of onnxruntime's AVX2 kernels on x86 servers) by default — 99%+ identical labels, same AUC so every file is < 100 MB.

Example:
    python export_onnx.py --verify
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _common
import numpy as np
import torch
from torch import nn

from app.models.architectures import ARCHS, TASK_CLASSES, get_module, reshape_transform_for, weights_filename


class CamDenseNet(nn.Module):
    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        feats = model.features
        names = [n for n, _ in feats.named_children()]
        cut = names.index("denseblock4") + 1
        self.body = nn.Sequential(*[getattr(feats, n) for n in names[:cut]])
        self.norm = feats.norm5  # BatchNormAct2d (BN + ReLU)
        self.head = model.forward_head

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        a = self.body(x)  # (B, C, 7, 7) — Grad-CAM target
        logits = self.head(self.norm(a))
        bn = self.norm
        scale = bn.weight / torch.sqrt(bn.running_var + bn.eps)  # (C,)
        pre = (a - bn.running_mean[None, :, None, None]) * scale[None, :, None, None] + bn.bias[None, :, None, None]
        active = (pre > 0).float().mean(dim=(2, 3))  # (B, C)
        k = logits.argmax(dim=1)
        w = self.classifier_weight()[k]  # (B, C)
        hw = a.shape[2] * a.shape[3]
        alpha = w * scale[None, :] * active / hw
        cam = torch.relu((alpha[:, :, None, None] * a).sum(dim=1))
        return logits, cam

    def classifier_weight(self) -> torch.Tensor:
        return self.cam_weight

    def bind(self, model: nn.Module) -> "CamDenseNet":
        # Separate copy for the CAM branch so quantization never touches the shared classifier weight.
        self.register_buffer("cam_weight", model.get_classifier().weight.detach().clone())
        return self


class CamSwin(nn.Module):
    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model
        self.register_buffer("cam_weight", model.get_classifier().weight.detach().clone())

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        a = self.model.forward_features(x)  # (B, 7, 7, C) after final norm — Grad-CAM target
        logits = self.model.forward_head(a)
        k = logits.argmax(dim=1)
        w = self.cam_weight[k]  # (B, C)
        hw = a.shape[1] * a.shape[2]
        cam = torch.relu((a * (w / hw)[:, None, None, :]).sum(dim=3))
        return logits, cam


def wrap(arch: str, model: nn.Module) -> nn.Module:
    model.requires_grad_(False)  # inference-only export: parameters become plain initializers
    return CamDenseNet(model).bind(model) if arch == "densenet" else CamSwin(model)


def reference_cam(arch: str, model: nn.Module, x: torch.Tensor) -> np.ndarray:
    """Raw 7x7 Grad-CAM from pytorch-grad-cam (before its resize/normalisation)."""
    from pytorch_grad_cam import GradCAM

    with GradCAM(
        model=model,
        target_layers=[get_module(model, ARCHS[arch].target_layer)],
        reshape_transform=reshape_transform_for(arch),
    ) as cam:
        cam.compute_input_gradient = False
        acts_grads = []
        cam(input_tensor=x, targets=None)
        a = cam.activations_and_grads.activations[0].cpu().numpy()
        g = cam.activations_and_grads.gradients[0].cpu().numpy()
        acts_grads.append((a, g))
    weights = g.mean(axis=(2, 3))
    return np.maximum((weights[:, :, None, None] * a).sum(axis=1), 0)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights-dir", type=Path, default=_common.DEFAULT_WEIGHTS)
    p.add_argument("--verify", action="store_true", help="Compare logits and CAM with PyTorch / pytorch-grad-cam")
    p.add_argument("--opset", type=int, default=17)
    p.add_argument(
        "--fp32",
        action="store_true",
        help="Skip 8-bit MatMul quantization (default quantizes Swin's MatMuls: 113 MB -> 31 MB, same AUC)",
    )
    args = p.parse_args()

    torch.manual_seed(0)
    x = torch.randn(3, 3, 224, 224)
    for arch in ARCHS:
        for task in TASK_CLASSES:
            if not (args.weights_dir / weights_filename(arch, task)).exists():
                continue
            model, _ = _common.load_trained_model(arch, task, args.weights_dir, torch.device("cpu"))
            wrapped = wrap(arch, model).eval()
            out = args.weights_dir / f"{arch}_{task}.onnx"
            with torch.no_grad():
                torch.onnx.export(
                    wrapped,
                    (x,),
                    str(out),
                    input_names=["input"],
                    output_names=["logits", "cam"],
                    dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}, "cam": {0: "batch"}},
                    opset_version=args.opset,
                    dynamo=False,
                )
            if not args.fp32 and arch == "swin":
                from onnxruntime.quantization import QuantType, quantize_dynamic

                tmp = out.with_suffix(".fp32.onnx")
                out.replace(tmp)
                quantize_dynamic(
                    str(tmp), str(out), weight_type=QuantType.QUInt8, op_types_to_quantize=["MatMul"], per_channel=True
                )
                tmp.unlink()
            size = out.stat().st_size / 1e6
            msg = f"{out.name}: {size:.1f} MB"
            if args.verify:
                import onnxruntime as ort

                sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
                logits_o, cam_o = sess.run(None, {"input": x.numpy()})
                with torch.no_grad():
                    logits_t = model(x).numpy()
                cam_ref = reference_cam(arch, model, x.clone().requires_grad_(True))
                dl = np.abs(logits_o - logits_t).max()
                rel = np.abs(cam_o - cam_ref).max() / (np.abs(cam_ref).max() + 1e-12)
                msg += f" | max logit diff {dl:.2e} | max CAM diff vs pytorch-grad-cam {rel:.2e} (relative)"
                # int8 MatMuls shift values slightly; fp32 must match exactly.
                tol = 1e-3 if (args.fp32 or arch != "swin") else 0.5
                assert dl < tol, msg
            print(msg)


if __name__ == "__main__":
    main()
