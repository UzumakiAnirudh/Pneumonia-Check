# Chapter 16 — Backend code walkthrough

[← Chapter 15](15-train-from-scratch-step-by-step.md) · [README](../../README.md) · Next: [Chapter 17 →](17-frontend-walkthrough.md)

Read this with the code open in VS Code. Files are presented in the order the server uses them when it
starts and when it handles a request.

---

## 16.1 Start-up: `app/main.py`

`uvicorn app.main:app` imports `main.py`, which calls `create_app()`:

1. Reads settings (`config.py`).
2. Adds **CORS** (which other websites may call the API) and the routes (`api/auth_routes.py`,
   `api/routes.py`).
3. Serves the gallery images (`/api/metrics/gallery/...`) and example X-rays (`/api/samples/files/...`)
   as static files.
4. On start-up (`lifespan`), `build_services()` creates every long-lived object once:
   the **model provider**, the **validator**, the **temperatures**, the **prediction service**, the
   **database engine**, the **auth service** and the **history repository** — and stores them in
   `app.state.services` so every request can reuse them (loading models is slow; doing it per request
   would be terrible).

## 16.2 Settings: `app/config.py`

A `Settings` class (pydantic-settings) with one field per option — e.g. `use_mock_models`,
`model_backend`, `classification_mode`, `weights_dir`, `image_size`, `use_clahe`, `default_threshold`,
`history_enabled`, `database_url`, `session_days`, `cookie_secure`, `cors_origins`. Each can be overridden
by an environment variable with the same name in capitals (`DEFAULT_THRESHOLD=0.8`) or in `backend/.env`.
An empty `DATABASE_URL` falls back to the SQLite file `backend/data/history.db`.

## 16.3 Database: `app/db.py`

`make_engine(url)` connects to SQLite (a local file) or PostgreSQL (`postgresql://...`), creates the
tables, and runs small **migrations** — e.g. adding the `user_id` column to databases created before
accounts existed (old rows without an owner become invisible rather than leaking).

## 16.4 The API layer: `app/api/`

- **`deps.py`** — the `Services` container, `get_services()`, and `current_user()`: reads the session
  cookie, looks up the user, or answers **401**. Any endpoint that declares
  `user: User = Depends(current_user)` is login-only.
- **`errors.py`** — `api_error()` builds uniform errors `{"detail": {"code", "message"}}`;
  `read_upload()` reads an upload **into memory only**, rejecting files over the size limit (413).
- **`auth_routes.py`** — `/api/auth/register`, `/login`, `/logout`, `/me`. Sets the cookie with
  `httponly=True`, `samesite="lax"` and `secure` from settings.
- **`routes.py`** — everything else:
  - `GET /api/health` — provider status, model version, calibration, training progress;
  - `POST /api/validate` and `POST /api/predict` (login required) — run in a thread pool so the server
    stays responsive; map errors to 400/422/503;
  - `GET /api/metrics`, `GET /api/samples` — public dashboard data and examples;
  - `GET/DELETE /api/history[...]` — always scoped to the logged-in user.

## 16.5 Data shapes: `app/schemas/`

Pydantic classes that define every request and response: `prediction.py` (`ImageInfo`,
`ValidationResult`, `StageResult`, `Reliability`, `Explanation`, `ModelResult`, `PredictResponse`),
`auth.py` (`RegisterRequest` with password rules, `LoginRequest`, `UserOut`), `health.py`, `history.py`,
`samples.py`. FastAPI uses them to validate input, convert output to JSON, and generate `/docs`. The
frontend mirrors them in `frontend/src/api/types.ts` — keep both in sync when you change one.

## 16.6 Models: `app/models/`

| File               | What it contains                                                                                                                                                                             |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `specs.py`         | PyTorch-free facts: `ARCHS` (display name, timm name, Grad-CAM target layer), `TASK_CLASSES` (`stage1: [NORMAL, PNEUMONIA]`, `stage2: [BACTERIAL, VIRAL]`, `three_class`), file-name helpers |
| `architectures.py` | `build_model()` with timm, `get_module()` to find the target layer, `swin_reshape_transform()`, `load_state_dict()`                                                                          |
| `provider.py`      | The `ModelProvider` interface: `available()`, `infer(arch, task, gray, explain) → InferenceOutput(logits, input_image, cam, ...)`, `status()`                                                |
| `real_provider.py` | `TorchModelProvider`: loads `.pth` + `.json`, runs PyTorch, computes Grad-CAM with pytorch-grad-cam; a lock per model keeps Grad-CAM hooks thread-safe                                       |
| `onnx_provider.py` | `OnnxModelProvider`: loads `.onnx`, runs ONNX Runtime; the model itself returns the 7×7 CAM, which is scaled exactly like pytorch-grad-cam                                                   |
| `mock_provider.py` | Fake but image-dependent outputs, used only by automated tests                                                                                                                               |
| `factory.py`       | `create_provider()`: mock if `USE_MOCK_MODELS`, else PyTorch or ONNX (`MODEL_BACKEND=auto` picks PyTorch if installed and `.pth` files exist, otherwise ONNX)                                |

PyTorch is imported _lazily_ (only inside the functions that need it), so the server runs with
PyTorch not installed at all — a test (`tests/test_onnx.py`) blocks `import torch` and checks that
registration and prediction still work.

## 16.7 Services: `app/services/` — the real work

### `preprocessing.py`

- `load_image(bytes, filename)` — detects DICOM (magic bytes `DICM`) or decodes PNG/JPEG with Pillow,
  applies EXIF rotation, converts 16-bit images to 8-bit, **keeps only pixels**. For DICOM:
  `strip_dicom_identifiers()` deletes patient/institution tags, applies the VOI LUT (the display
  windowing), inverts `MONOCHROME1` images.
- `PreprocessConfig` — image size and CLAHE settings (saved next to each model).
- `prepare_uint8()` (resize + CLAHE), `to_model_array()` / `to_model_tensor()` (3 channels + ImageNet
  normalisation), `make_display_image()`, PNG/JPEG data-URI encoders.

### `validator.py`

`HeuristicValidator` starts from a score of 1.0 and multiplies in penalties for: colour (×0.1), odd
aspect ratio, mostly white (documents) or black, nearly uniform, **no bright mediastinum between
darker lungs**, very different left/right density, **no left–right symmetry**, heavy fine-grained noise.
Score ≥ 0.5 → chest X-ray. `quality_checks()` rejects images under 128 px and warns under 512 px, at
very low contrast or when blurry. `LearnedValidator` uses a trained MobileNetV3 if
`weights/validator.pth` exists.

### `predictor.py` — the orchestra conductor

`PredictionService.predict()`:

1. decode + validate (raises `NotChestXrayError` → 422);
2. make the display image;
3. for each requested model, `_run_two_stage()`: Stage 1 with Grad-CAM → calibrated probabilities;
   Stage 2 only if pneumonia; joint probabilities (P(bacterial) = P(pneumonia) × P(bacterial | pneumonia));
   `reliability_for()` = high only if every stage ≥ threshold; `_explanation()` → heatmap/overlay PNGs,
   region text, lung attention;
4. or `_run_three_class()` when `CLASSIFICATION_MODE=three_class`;
5. agreement between models when both ran.

### `calibration.py`

`softmax(logits, T)`, `fit_temperature()` (L-BFGS on validation logits, clamped to 0.05–20),
`expected_calibration_error()`, `reliability_curve()`, `TemperatureStore` (reads `temperature.json`;
missing → T = 1).

### `gradcam.py` and `lung_mask.py`

`compute_gradcam()` (PyTorch path), `normalize_cam()`, `colorize()` (JET), `blend()`,
`describe_attention()` (zones, bilateral rule, patient-side naming, lung-attention vs lung-area), and the
template + Otsu + convex-hull lung mask — all explained in Chapter 12.

### `auth.py`

`User` and `AuthSession` tables; `hash_password()` / `verify_password()` (PBKDF2-SHA256, 310,000
iterations, random salt, constant-time comparison); `AuthService` (`register`, `authenticate` with a
dummy hash for unknown emails so timing does not reveal which emails exist, `create_session`,
`user_for_token`, `end_session`); `LoginThrottle` (5 failures → 15-minute lock).

### `history.py`

`AnalysisRecord` table and `HistoryRepository` (`add`, `list`, `get`, `delete`, `clear` — every one takes
`user_id`). `compact_response()` shrinks what is stored: a 192-px JPEG thumbnail, heatmaps resized to
match, **no overlay images, no full-resolution X-ray**.

### `resources.py` and `evaluation.py`

`load_metrics()` reads `metrics/metrics.json` and turns gallery file names into URLs; `load_samples()`
reads `samples/samples.json`. `evaluation.py` computes every metric for the dashboard (used by the
training scripts; metrics that are undefined for a dataset — e.g. sensitivity on a normals-only set —
are stored as `null`, never as a misleading 0).

## 16.8 Tests: `backend/tests/`

57 automated tests covering preprocessing (including EXIF/DICOM privacy), the validator, calibration,
Grad-CAM shapes and the radiological convention, the prediction logic, every API endpoint, accounts and
**history isolation between users**, and the ONNX path. Synthetic X-ray "phantoms"
(`tests/phantoms.py`) provide deterministic test images. Run: `cd backend && pytest` (Chapter 21).

---

Next: **Chapter 17 — Frontend code walkthrough** → [17-frontend-walkthrough.md](17-frontend-walkthrough.md)
