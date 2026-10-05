# Chapter 2 — Install and run the app

[← Chapter 1](01-computer-basics.md) · [README](../../README.md) · Next: [Chapter 3 →](03-how-it-works.md)

Goal: the full application running on your computer, with the trained AI models, in about 30
minutes. No coding required. You need Git, Python 3.10+ and Node.js 20+ ([Chapter 1](01-computer-basics.md)).

---

## 2.1 Download the project

Open a terminal and run:

```bash
cd ~/Desktop                      # Windows: cd $HOME\Desktop
git clone https://github.com/UzumakiAnirudh/Pneumonia-Check.git
cd Pneumonia-Check
ls                                # Windows: dir
```

You should see `README.md`, `backend`, `frontend`, `training`, `docs` and a few configuration files.

> Received the project as a **zip file** instead? Unzip it, then `cd` into the unzipped folder.

## 2.2 Start the backend (the AI server)

The backend is Python. Python projects keep their libraries in a **virtual environment** — a
private folder (`.venv`) so this project's libraries never clash with other projects'.

```bash
cd backend

# 1. Create the virtual environment (once)
python3 -m venv .venv             # Windows: python -m venv .venv

# 2. Activate it (every time you open a new terminal)
source .venv/bin/activate         # Windows PowerShell: .venv\Scripts\Activate.ps1
```

Your prompt now starts with `(.venv)` — that means it is active.

```bash
# 3. Install the libraries (once; takes 1–3 minutes)
pip install -r requirements-deploy.txt
```

**Which requirements file?**

| File                      | Size              | Contains                                       | Use it to                                                                   |
| ------------------------- | ----------------- | ---------------------------------------------- | --------------------------------------------------------------------------- |
| `requirements-deploy.txt` | ~400 MB           | FastAPI, OpenCV, **ONNX Runtime**              | **Run the app** with the models already in `backend/weights/` (recommended) |
| `requirements.txt`        | ~2–3 GB           | Everything above + **PyTorch**, timm, Grad-CAM | Train or re-export models (Chapter 9)                                       |
| `requirements-dev.txt`    | same + test tools | `requirements.txt` + pytest, black             | Develop and run the automated tests (Chapter 14)                            |

```bash
# 4. Start the server
python -m uvicorn app.main:app --port 8000
```

You should see lines like:

```
INFO app.models.factory: Model backend: onnx
INFO pneumoscan: Ready: provider=OnnxModelProvider mode=two_stage device=cpu (onnxruntime) ...
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Check it:** open **http://localhost:8000/api/health** in your browser. You should see text
starting with `{"status":"ok", ...`. Also try **http://localhost:8000/docs** — FastAPI's automatic,
clickable documentation of every endpoint.

Leave this terminal open — closing it stops the server.

### Optional settings

```bash
cp .env.example .env              # Windows: copy .env.example .env
```

Edit `.env` in VS Code to change settings (all explained in the [README](../../README.md#configuration-backendenv)).
Restart the server after changing it.

## 2.3 Start the website

Open a **second terminal** (keep the first one running):

```bash
cd ~/Desktop/Pneumonia-Check/frontend
npm install                       # once; downloads ~200 MB of libraries into node_modules/
npm run dev
```

You should see:

```
  VITE v7.x  ready in 400 ms
  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173**. During development the website forwards every request starting
with `/api` to the backend on port 8000 (configured in `frontend/vite.config.ts`), so the two work
together automatically.

## 2.4 A guided tour of the app

1. **Home** — what the project does, the 4-step workflow, the medical disclaimer.
2. **Register** (sidebar, bottom) — enter your name, email and a password with at least 8
   characters mixing letters with a number or symbol. You are logged in automatically.
3. **Analyze**
   - Pick a **model**: _DenseNet121_ (a convolutional network), _Swin Transformer_ (a vision
     transformer) or _Compare Both_.
   - Click one of the **six example X-rays** (a child and an adult for Normal, Bacterial and
     Viral — all real images from the held-out test set), or **drag your own** PNG/JPEG/DICOM file
     onto the dark panel.
   - Press **Analyze**. A scan line sweeps the image while five steps tick off.
4. **Results**
   - **Stage 1** says NORMAL or PNEUMONIA with a _calibrated confidence_ (Chapter 5 explains
     calibration). If pneumonia, **Stage 2** says BACTERIAL or VIRAL.
   - The badge says **High confidence** or **Low confidence — recommend expert review**.
   - The **viewer** has four modes: _Original_, _Overlay_ (heatmap on the X-ray), _Heatmap_, _Side by
     side_. Use the opacity slider; zoom with the mouse wheel or `+`/`-`; drag to pan; `0` resets.
   - "**What the model looked at**" describes the hottest region in words and reports how much of
     the attention fell inside the lungs (Chapter 7).
   - **Download Report (PDF)**, **Compare Models**, **Analyze Another**.
5. **History** — your own past analyses (other accounts never see them). Search, filter, reopen,
   delete one or all.
6. **Model Performance** — the real evaluation numbers: metric cards, ROC and calibration curves,
   confusion matrices, results split into children vs adults, training curves, a Grad-CAM gallery of
   correct and incorrect cases, and an _External Validation_ tab with a hospital the models never saw.
7. **Settings** — light/dark theme, default model, the confidence threshold for the expert-review
   warning, whether to save history, which model version is active, and the API status.
8. **About** — the project, datasets, architectures and limitations.

## 2.5 Stopping and starting again

- Stop either program: click its terminal and press `Ctrl + C`.
- Next time:
  ```bash
  # terminal 1
  cd ~/Desktop/Pneumonia-Check/backend
  source .venv/bin/activate         # Windows: .venv\Scripts\Activate.ps1
  python -m uvicorn app.main:app --port 8000

  # terminal 2
  cd ~/Desktop/Pneumonia-Check/frontend
  npm run dev
  ```

Accounts and history are saved in `backend/data/history.db` (a SQLite database file) and survive
restarts. Delete that file to start fresh.

## 2.6 If something goes wrong

| Symptom                                                                  | Fix                                                                                                                                                                                                         |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `command not found: python3` / `node` / `git`                            | The tool is not installed or the terminal was opened before installing — reopen it ([Chapter 1](01-computer-basics.md))                                                                                     |
| `ModuleNotFoundError: No module named 'fastapi'`                         | The virtual environment is not active — run the `activate` command again, then retry                                                                                                                        |
| `Address already in use` / `Port 5173 is in use`                         | Another program uses that port. Use different ports: `python -m uvicorn app.main:app --port 8010` and `VITE_PROXY_TARGET=http://localhost:8010 npm run dev -- --port 5180`, then open http://localhost:5180 |
| Website says **"API offline"** or **"analysis server is not connected"** | The backend is not running, or is on a different port than the website expects (see the line above)                                                                                                         |
| `/api/health` shows `"status":"degraded"`                                | Model files are missing from `backend/weights/` — re-download the project or see [Chapter 9](09-training-pipeline.md)                                                                                       |
| `npm install` fails                                                      | Check `node --version` is 20 or newer                                                                                                                                                                       |

More in [Chapter 16 — Troubleshooting](16-troubleshooting-faq.md).

## 2.7 Optional: Docker

If you already use Docker, `docker compose up --build` in the project folder starts both parts at
http://localhost:8080 using `docker-compose.yml`. Docker is **not** required for anything in this guide.

---

Next, understand what happens inside when you press _Analyze_ → [Chapter 3](03-how-it-works.md)
