"""Follow a running ``run_pipeline.sh``, publish live status, and activate the new models when done.

* Every few seconds it parses the pipeline log and writes ``outputs/training_status.json``
  (stage, epoch, % done). The API exposes it in ``/api/health`` and the app shows it.
* When the log reports ``PIPELINE DONE`` it runs ``compare_versions.py``. If the new models are at
  least as good as the current ones on the same test images, it restarts the API on the new
  weights (both DenseNet and Swin). Otherwise the current models stay active.
* A macOS notification is shown when training finishes or fails.

Example (started automatically by the developer, see README):
    python watch_and_activate.py --log outputs/pipeline_combined.log
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT.parent / "backend"
STATUS = ROOT / "outputs" / "training_status.json"

TRAIN_STEPS = [("densenet", "stage1"), ("densenet", "stage2"), ("swin", "stage1"), ("swin", "stage2")]
NAMES = {"densenet": "DenseNet121", "swin": "Swin Transformer", "stage1": "Stage 1", "stage2": "Stage 2"}
# Share of total progress per phase (training dominates).
TRAIN_WEIGHT = 0.20
TAIL_PHASES = {"calibrate": 0.03, "evaluate": 0.05, "gradcam": 0.07, "external": 0.03, "export": 0.02}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(**fields) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    data.update(fields, updated_at=now())
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(STATUS)


def notify(title: str, message: str) -> None:
    if sys.platform == "darwin":
        script = f'display notification "{message}" with title "{title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", script], check=False)


def parse(log_text: str, epochs: int) -> dict:
    """Current phase, step and % done from the pipeline log."""
    headers = re.findall(r"^=== (.+?) ===$", log_text, re.MULTILINE)
    current = headers[-1] if headers else "starting"
    done = "PIPELINE DONE" in headers
    progress, label, epoch = 0.0, current, None

    m = re.match(r"train (\w+) (\w+)", current)
    if m:
        idx = TRAIN_STEPS.index((m.group(1), m.group(2)))
        section = log_text.rsplit(f"=== {current} ===", 1)[-1]
        epochs_seen = re.findall(r"^epoch +(\d+) \|", section, re.MULTILINE)
        epoch = int(epochs_seen[-1]) if epochs_seen else 0
        stopped = "Early stopping" in section or "Saved best weights" in section
        frac = 1.0 if stopped else epoch / epochs
        progress = TRAIN_WEIGHT * (idx + frac)
        label = f"Training {NAMES[m.group(1)]} {NAMES[m.group(2)]} (model {idx + 1} of 4)"
    elif not done:
        progress = TRAIN_WEIGHT * len(TRAIN_STEPS)
        for phase, weight in TAIL_PHASES.items():
            if current.startswith(phase):
                label = {
                    "calibrate": "Calibrating confidence scores",
                    "evaluate": "Evaluating on the held-out test set",
                    "gradcam": "Building the Grad-CAM gallery",
                    "external": "Testing on an unseen hospital",
                    "export": "Exporting example X-rays",
                }[phase]
                break
            progress += weight
    else:
        progress, label = 1.0, "Training finished"
    return {"done": done, "label": label, "epoch": epoch, "percent": round(100 * min(progress, 1.0), 1)}


def pipeline_running() -> bool:
    return subprocess.run(["pgrep", "-f", "run_pipeline.sh"], capture_output=True).returncode == 0


def restart_api(port: int, env_overrides: dict[str, str]) -> None:
    """Restart uvicorn on ``port`` so it loads the newly active weights."""
    subprocess.run(["pkill", "-f", f"uvicorn app.main:app --host 127.0.0.1 --port {port}"], check=False)
    time.sleep(2)
    env = {**os.environ, **env_overrides}
    for key in ("WEIGHTS_DIR", "METRICS_PATH", "SAMPLES_DIR", "DEVICE"):
        if key not in env_overrides:
            env.pop(key, None)  # fall back to the project defaults (backend/weights etc.)
    log = open(ROOT / "outputs" / "api.log", "a")
    subprocess.Popen(
        [str(BACKEND / ".venv" / "bin" / "python"), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--log", type=Path, default=ROOT / "outputs" / "pipeline_combined.log")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--port", type=int, default=8010)
    p.add_argument("--v1-dir", type=Path, default=ROOT / "outputs" / "backup_pediatric_only")
    p.add_argument("--interval", type=float, default=10.0)
    args = p.parse_args()

    write_status(
        state="training",
        active_version="v1",
        new_version="v2",
        description="Version 2: children + adult X-rays",
        started_at=now(),
        comparison=None,
        message="",
    )
    while True:
        text = args.log.read_text(errors="ignore") if args.log.exists() else ""
        info = parse(text, args.epochs)
        if info["done"]:
            break
        if not pipeline_running():
            write_status(state="failed", label=info["label"], percent=info["percent"], message="Training stopped unexpectedly — see the pipeline log.")
            notify("PneumoScan AI", "Model training stopped unexpectedly. Version 1 stays active.")
            return
        state = "training" if info["label"].startswith("Training") else "evaluating"
        write_status(state=state, label=info["label"], epoch=info["epoch"], epochs=args.epochs, percent=info["percent"])
        time.sleep(args.interval)

    write_status(state="comparing", label="Comparing Version 2 with Version 1", percent=100.0)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "compare_versions.py"),
            "--v1-metrics", str(args.v1_dir / "metrics.json"),
            "--v1-external", str(ROOT / "outputs" / "v1_external.json"),
            "--v2-metrics", str(BACKEND / "metrics" / "metrics.json"),
        ],
        capture_output=True,
        text=True,
    )
    comparison_path = ROOT / "outputs" / "version_comparison.json"
    comparison = json.loads(comparison_path.read_text()) if comparison_path.exists() else {"accept": False, "reasons": [result.stderr[-500:]]}

    if comparison.get("accept"):
        restart_api(args.port, {})
        write_status(state="activated", active_version="v2", label="Version 2 is active", comparison=comparison,
                     message="Version 2 (children + adults) passed the comparison and is now serving predictions.")
        notify("PneumoScan AI", "Training finished — Version 2 is now active.")
    else:
        write_status(state="kept_previous", active_version="v1", label="Version 1 kept", comparison=comparison,
                     message="Version 2 did not beat Version 1 on every test set: " + "; ".join(comparison.get("reasons", [])))
        notify("PneumoScan AI", "Training finished — Version 1 kept (Version 2 was not better).")


if __name__ == "__main__":
    main()
