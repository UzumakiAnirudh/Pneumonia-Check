"""Decide whether newly trained models (v2) should replace the current ones (v1).

Both versions are compared on the SAME images:
* the pediatric (Kermany) test split — v1's whole test set, v2's ``by_domain.pediatric``;
* the unseen-hospital adult set (Actualmed) — external validation of each version.

v2 is accepted only if, for every architecture, its ROC-AUC on each of those sets is no more than
``--tolerance`` below v1's. The decision and a comparison table are written as JSON.

Example:
    python compare_versions.py --v1-metrics outputs/backup_pediatric_only/metrics.json \\
        --v1-external outputs/v1_external.json --v2-metrics ../backend/metrics/metrics.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXTERNAL_PREFIX = "Actualmed"
METRICS = ("accuracy", "recall", "specificity", "roc_auc")


def _external(metrics: dict) -> dict:
    for entry in metrics.get("external", []):
        if entry.get("name", "").startswith(EXTERNAL_PREFIX):
            return {arch: m["stage1"]["metrics"] for arch, m in entry.get("models", {}).items()}
    return {}


def compare(v1: dict, v1_ext: dict, v2: dict, tolerance: float) -> dict:
    v1_external, v2_external = _external(v1_ext), _external(v2)
    rows, reasons = [], []
    for arch in ("densenet", "swin"):
        old_ped = v1.get("internal", {}).get(arch, {}).get("stage1", {}).get("metrics")
        new_ped = v2.get("by_domain", {}).get(arch, {}).get("stage1", {}).get("pediatric", {}).get("metrics")
        for test_set, old, new in (
            ("children (Kermany test)", old_ped, new_ped),
            ("unseen-hospital adults (Actualmed)", v1_external.get(arch), v2_external.get(arch)),
        ):
            if not old or not new:
                reasons.append(f"{arch}: missing {test_set} results")
                continue
            rows.append({"model": arch, "test_set": test_set, "v1": {k: old.get(k) for k in METRICS}, "v2": {k: new.get(k) for k in METRICS}})
            if new["roc_auc"] is None or old["roc_auc"] is None:
                continue
            if new["roc_auc"] < old["roc_auc"] - tolerance:
                reasons.append(f"{arch} AUC on {test_set} dropped {old['roc_auc']:.3f} -> {new['roc_auc']:.3f}")
    return {"accept": not reasons, "reasons": reasons, "tolerance": tolerance, "rows": rows}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--v1-metrics", type=Path, required=True)
    p.add_argument("--v1-external", type=Path, required=True)
    p.add_argument("--v2-metrics", type=Path, required=True)
    p.add_argument("--tolerance", type=float, default=0.005)
    p.add_argument("--out", type=Path, default=Path(__file__).parent / "outputs" / "version_comparison.json")
    args = p.parse_args()

    load = lambda path: json.loads(path.read_text()) if path.exists() else {}  # noqa: E731
    result = compare(load(args.v1_metrics), load(args.v1_external), load(args.v2_metrics), args.tolerance)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    for r in result["rows"]:
        fmt = lambda m: " ".join(f"{k}={v:.3f}" if v is not None else f"{k}=n/a" for k, v in m.items())  # noqa: E731
        print(f"{r['model']:9s} {r['test_set']:36s}\n   v1: {fmt(r['v1'])}\n   v2: {fmt(r['v2'])}")
    print("DECISION:", "ACCEPT v2" if result["accept"] else "KEEP v1 — " + "; ".join(result["reasons"]))


if __name__ == "__main__":
    main()
