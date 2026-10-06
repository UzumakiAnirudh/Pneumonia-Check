# Chapter 23 — Troubleshooting & FAQ

[← Chapter 22](22-results-and-lessons.md) · [README](../../README.md) · Next: [Chapter 24 →](24-glossary.md)

Find your symptom, apply the fix. Always read the **last line** of an error message first.

---

## 23.1 Installing

| Problem                                                                    | Fix                                                                                                                                                                              |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `command not found: python3` (Windows: `python` opens the Microsoft Store) | Install Python from python.org and tick **Add python.exe to PATH**; reopen the terminal                                                                                          |
| `command not found: node` / `npm` / `git`                                  | Install it (Chapter 1) and reopen the terminal                                                                                                                                   |
| `pip: command not found`                                                   | Use `python3 -m pip install ...`                                                                                                                                                 |
| `error: externally-managed-environment`                                    | You are installing outside a virtual environment — create and activate `.venv` first (Chapter 2.2)                                                                               |
| PowerShell: "running scripts is disabled"                                  | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`                                                                                                                            |
| PyTorch download is huge or fails                                          | Run the app with `requirements-deploy.txt` (no PyTorch). For training on a machine without GPU: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` |
| `npm install` fails with peer-dependency errors                            | Use Node 20+ and the committed `package-lock.json` (`npm ci`)                                                                                                                    |

## 23.2 Running

| Problem                                                                   | Fix                                                                                                                                                  |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'app'`                              | Run uvicorn from inside `backend/`                                                                                                                   |
| `ModuleNotFoundError: No module named 'fastapi'` (or cv2, onnxruntime...) | Activate the virtual environment; reinstall requirements                                                                                             |
| `Address already in use` / port busy                                      | Another program uses the port: `python -m uvicorn app.main:app --port 8010` and `VITE_PROXY_TARGET=http://localhost:8010 npm run dev -- --port 5180` |
| Website: "API offline" / "analysis server is not connected"               | The backend is not running, or the website proxies to the wrong port                                                                                 |
| `/api/health` → `"status":"degraded"`                                     | No model files in `backend/weights/` — re-download the repository, or train/export (Chapter 14)                                                      |
| Register: "Password must mix letters with numbers or symbols"             | Use at least 8 characters including a digit or symbol                                                                                                |
| "Too many failed attempts"                                                | Wait 15 minutes (or restart the backend in development)                                                                                              |
| Analysis: "This doesn't look like a chest X-ray"                          | Use a frontal (PA/AP) chest X-ray; colour photos, documents and other body parts are rejected by design                                              |
| "Low resolution — results may be less reliable"                           | The image's shorter side is under 512 px; it is still analysed                                                                                       |
| PDF report button does nothing                                            | Allow downloads for the site in your browser                                                                                                         |
| Dark/light theme wrong                                                    | Settings → Theme                                                                                                                                     |

## 23.3 Training

| Problem                                            | Fix                                                                                           |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `No Kermany images found`                          | Check the path: `--data-root data/raw/chest_xray` must contain `train/NORMAL` etc.            |
| Very slow epochs on Mac/CPU                        | Add `--cache --workers 0`                                                                     |
| `CUDA out of memory` / Mac memory pressure         | Lower `--batch-size` to 16 or 8                                                               |
| Training accuracy far below validation, or falling | A data-path bug — see Chapter 22.3; compare against `--device cpu` on a small `--limit`       |
| Loss is `nan`                                      | Lower `--lr`; check images load correctly; the trainer skips non-finite batches automatically |
| Calibration warns T was clamped                    | Your validation set is too small or perfectly separated — use more data                       |
| `export_onnx.py`: `No module named onnx`           | `pip install onnx onnxruntime`                                                                |

## 23.4 Deployment

See the table of real deployment problems in [Chapter 20.13](20-hosting-and-rehosting.md#2013-problems-we-actually-hit-and-the-fixes)
(404 on Vercel, 405 on register, Render `no-server`, Vercel _Request Access_, low Swin confidence on
servers, Hugging Face PRO requirement, GitHub 403).

## 23.5 FAQ

**Can I use this to diagnose patients?**
No. It is a research/teaching project, not a medical device. Any clinical use requires regulatory
approval, prospective validation and clinical oversight.

**Why two models (DenseNet and Swin)?**
To compare a convolutional network with a vision transformer fairly. _Compare Both_ also gives a useful
safety signal: when they disagree, a human should look.

**Why does the model say "Low confidence" so often for bacterial vs viral?**
Because that distinction is genuinely hard on X-rays — the calibrated confidence is honest about it.

**Why does Swin give a slightly different answer online than on my computer?**
Online, Swin uses 8-bit weights to fit the free server; 99%+ of answers are identical, but near-50/50
cases can flip. DenseNet is identical.

**Are my images stored?**
Only if history is on: a 192-pixel thumbnail, a small heatmap and the results, visible only to your
account. Turn it off in Settings or delete history any time.

**Why does the first request online take a minute?**
The free Render service sleeps when idle and needs about a minute to wake up.

**Can I add another model?**
Yes — Chapter 11.12 and Chapter 14.

**How do I change the team names on the About page?**
Edit `frontend/src/config/project.ts`.

---

Next: **Chapter 24 — Glossary** → [24-glossary.md](24-glossary.md)
