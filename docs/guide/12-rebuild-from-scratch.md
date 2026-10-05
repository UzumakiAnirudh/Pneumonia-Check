# Chapter 12 — Rebuild everything from scratch

[← Chapter 11](11-frontend-walkthrough.md) · [README](../../README.md) · Next: [Chapter 13 →](13-deployment.md)

This is a recipe to recreate the whole project in an **empty folder**, in an order where every step
can be tested before moving on. Each phase lists what to build, the essential code, a **checkpoint**
(how to know it works), and the **reference file** in this repository to compare with.

Rule of thumb: **type the code yourself** rather than copying whole files — you will understand it and
remember it. Use the reference files when stuck.

---

## Phase 0 — Tools and an empty project

Install Git, Python 3.10+, Node.js 20+ and VS Code ([Chapter 1](01-computer-basics.md)).

```bash
mkdir PneumoScan && cd PneumoScan
git init -b main
mkdir backend frontend training docs
```

**Checkpoint:** `git status` says "No commits yet".

---

## Phase 1 — A backend that answers

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" python-multipart pydantic pydantic-settings
mkdir -p app && touch app/__init__.py
```

`app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="PneumoScan AI")

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

**Checkpoint:** `python -m uvicorn app.main:app --reload --port 8000` → open
http://localhost:8000/api/health → `{"status":"ok"}`. Reference: `backend/app/main.py`, `backend/app/config.py`.

---

## Phase 2 — Preprocessing (shared by training and the app)

```bash
pip install numpy opencv-python-headless pillow pydicom
mkdir -p app/services && touch app/services/__init__.py
```

`app/services/preprocessing.py` — the essential core:

```python
import io
import cv2
import numpy as np
from PIL import Image, ImageOps

MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)

def load_gray(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as im:
        im = ImageOps.exif_transpose(im)            # respect camera rotation, then forget metadata
        return np.array(im.convert("L"))            # grayscale uint8 (H, W)

def prepare_uint8(gray, size=224, clahe=True):
    img = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    if clahe:
        img = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
    return img

def to_model_array(img_uint8):
    x = np.repeat((img_uint8 / 255.0).astype(np.float32)[None], 3, axis=0)   # (3, H, W)
    return (x - np.array(MEAN, np.float32)[:, None, None]) / np.array(STD, np.float32)[:, None, None]
```

**Checkpoint:** in Python, load any X-ray image and check `to_model_array(prepare_uint8(load_gray(open("x.jpeg","rb").read()))).shape == (3, 224, 224)`.
Then add DICOM support, 16-bit images and DICOM de-identification. Reference:
`backend/app/services/preprocessing.py`, tests in `backend/tests/test_preprocessing.py`.

---

## Phase 3 — Data

Copy `training/download_data.py` and `training/prepare_data.py` (or write them following
[Chapter 8](08-data.md)): download Kermany, parse labels from file names, remove duplicates by MD5,
split 70/15/15 **grouped by patient** with `StratifiedGroupKFold`.

```bash
cd ../training
pip install pandas scikit-learn
python download_data.py kermany
python prepare_data.py --data-root data/raw/chest_xray
```

**Checkpoint:** `data/splits.csv` exists with ~5,824 rows; the printed table matches Chapter 8.5; no
patient ID appears in two splits.

---

## Phase 4 — Train your first model

```bash
pip install torch torchvision timm   # (CPU-only on Linux/Windows: --index-url https://download.pytorch.org/whl/cpu)
```

The essential training loop (`train.py` adds validation, early stopping, scheduling, logging, caching):

```python
import sys, torch, timm, pandas as pd
from torch import nn
from torch.utils.data import Dataset, DataLoader
sys.path.insert(0, "../backend")
from app.services.preprocessing import load_gray, prepare_uint8, to_model_array

LABEL = {"NORMAL": 0, "BACTERIAL": 1, "VIRAL": 1}           # Stage 1

class CXR(Dataset):
    def __init__(self, df): self.df = df.reset_index(drop=True)
    def __len__(self): return len(self.df)
    def __getitem__(self, i):
        row = self.df.loc[i]
        img = prepare_uint8(load_gray(open(row.path, "rb").read()))
        return torch.from_numpy(to_model_array(img)), LABEL[row.label]

df = pd.read_csv("data/splits.csv")
train = DataLoader(CXR(df[df.split == "train"]), batch_size=32, shuffle=True)
device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
model = timm.create_model("densenet121", pretrained=True, num_classes=2).to(device)
counts = torch.bincount(torch.tensor([LABEL[l] for l in df[df.split == "train"].label]))
loss_fn = nn.CrossEntropyLoss(weight=(counts.sum() / (2 * counts)).float().to(device))
opt = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)

for epoch in range(3):
    model.train()
    for x, y in train:
        x, y = x.to(device), y.to(device)      # NOTE: no non_blocking=True on Apple MPS (Chapter 15)
        opt.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        opt.step()
    print("epoch", epoch, "last loss", loss.item())
torch.save(model.state_dict(), "../backend/weights/densenet_stage1.pth")
```

**Checkpoint:** the loss goes down. Then grow it into the full `train.py`: augmentation
(`dataset.py`, careful to **clip** brightness changes rather than using `cv2.convertScaleAbs`), a
validation loop with AUC, warm-up + cosine schedule, early stopping, the JSON sidecar, and Stage 2
(filter to pneumonia images, labels BACTERIAL=0 / VIRAL=1). Train all four models.
Reference: `training/train.py`, `training/dataset.py`, `training/_common.py`.

---

## Phase 5 — Calibrate and evaluate

- `fit_temperature()` — optimise log _T_ with `torch.optim.LBFGS` on validation logits
  (reference: `backend/app/services/calibration.py`) → `calibrate.py` writes `temperature.json`.
- `evaluate.py` — test-set metrics with scikit-learn (`roc_auc_score`, `confusion_matrix`, ...) →
  `metrics.json` + figures (reference: `backend/app/services/evaluation.py`, `training/evaluate.py`).

**Checkpoint:** your Stage 1 test AUC is around 0.99.

---

## Phase 6 — Serve predictions

1. `app/models/specs.py` and `architectures.py` — model names, classes, `build_model()`.
2. `app/models/provider.py` — the `ModelProvider` interface; `real_provider.py` — load `.pth`, run.
3. `app/services/predictor.py` — Stage 1 → (if pneumonia) Stage 2 → softmax(logits / T) → reliability.
4. `app/schemas/prediction.py` — response shapes.
5. `POST /api/predict` in `app/api/routes.py` — read the upload, call the predictor in a thread pool.

**Checkpoint:** with the server running,

```bash
curl -F file=@some_xray.jpeg -F model=densenet http://localhost:8000/api/predict
```

returns JSON with `stage1.label`. Reference: the files named above.

---

## Phase 7 — Explainability and safety checks

```bash
pip install grad-cam
```

- Grad-CAM with `pytorch_grad_cam.GradCAM(model, target_layers=[...], reshape_transform=...)`
  (`services/gradcam.py`), JET colouring, blending, `describe_attention()`.
- `services/lung_mask.py` — template ellipses + Otsu + convex hull.
- `services/validator.py` — the heuristic CXR check and quality checks; `POST /api/validate`.

**Checkpoint:** predictions now contain `explanation.heatmap_png` (a `data:image/png;base64,...` string
you can paste into a browser address bar to view) and a sentence like "lower right lung".

---

## Phase 8 — Accounts and history

```bash
pip install sqlmodel
```

- `app/db.py` — engine + tables; `services/auth.py` — `User`, `AuthSession`, PBKDF2 hashing, sessions,
  throttling; `api/auth_routes.py` — register/login/logout/me with an httpOnly SameSite cookie;
  `api/deps.py` — `current_user`.
- `services/history.py` — `AnalysisRecord` with `user_id`; every query filtered by user.

**Checkpoint:** write the test "Bob cannot read Alice's history item" — see
`backend/tests/test_auth.py::test_history_is_private_per_account`.

---

## Phase 9 — The website

```bash
cd ../frontend
npm create vite@latest . -- --template react-ts
npm install react@18.3.1 react-dom@18.3.1 react-router-dom@6 @tanstack/react-query@5 zustand@5 \
  framer-motion@12 lucide-react recharts@2 react-dropzone@14 jspdf@3 html2canvas@1.4.1 \
  @fontsource/inter @fontsource/jetbrains-mono clsx
npm install -D tailwindcss@3 postcss autoprefixer @types/react@18 @types/react-dom@18 \
  vitest@3 jsdom @testing-library/react@16 @testing-library/dom @testing-library/jest-dom \
  @testing-library/user-event eslint@9 @eslint/js@9 typescript-eslint eslint-plugin-react-hooks@5 \
  eslint-plugin-react-refresh eslint-config-prettier globals prettier prettier-plugin-tailwindcss@0.6
npx tailwindcss init -p
```

Build in this order, testing in the browser after each step:

1. `vite.config.ts` — add the `/api` proxy to `http://localhost:8000` and the `@` alias.
2. `styles/index.css` + `tailwind.config.ts` — colour variables and theme.
3. `api/types.ts`, `api/httpClient.ts`, `api/client.ts`, `api/hooks.ts`.
4. A first page that shows `useHealth()` data → proves the frontend↔backend connection.
5. `components/ui/*`, `components/layout/AppShell.tsx`, routing in `App.tsx`.
6. `features/auth/*`, `pages/LoginPage.tsx`, `pages/RegisterPage.tsx`.
7. `features/upload/*`, `pages/AnalyzePage.tsx`, `features/analysis/useRunAnalysis.ts`.
8. `features/analysis/ExplanationViewer.tsx`, `ResultsPanel.tsx`, `pages/ResultsPage.tsx`.
9. `pages/HistoryPage.tsx`, `pages/SettingsPage.tsx`, `pages/PerformancePage.tsx`, the PDF report.

A minimal first page to prove the connection:

```tsx
import { useEffect, useState } from "react";
export default function App() {
  const [status, setStatus] = useState("checking…");
  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("offline"));
  }, []);
  return <h1>Backend: {status}</h1>;
}
```

**Checkpoint:** `npm run dev`, open http://localhost:5173, see "Backend: ok". Reference: `frontend/src/`.

---

## Phase 10 — Tests, quality, export, deployment

1. Tests: pytest (`backend/tests/`), Vitest (`frontend/src/__tests__/`) — [Chapter 14](14-testing-and-quality.md).
2. `training/export_onnx.py` + `app/models/onnx_provider.py` — the PyTorch-free path.
3. `vercel.json`, `render.yaml`, `backend/requirements-deploy.txt` — [Chapter 13](13-deployment.md).

**Final checkpoint:** your rebuilt app reaches the numbers in [Chapter 15](15-results-and-lessons.md)
within about ±0.005 AUC, and every test passes.

---

## How long will this take?

| Experience             | Running the existing project | Rebuilding from scratch                                |
| ---------------------- | ---------------------------- | ------------------------------------------------------ |
| Never coded            | an afternoon (Chapters 1–2)  | several weeks, working through Chapters 4–11 alongside |
| Some Python/JavaScript | 30 minutes                   | 1–2 weeks                                              |
| Experienced developer  | 10 minutes                   | 2–4 days                                               |

---

Next: put it on the internet for free → [Chapter 13](13-deployment.md)
