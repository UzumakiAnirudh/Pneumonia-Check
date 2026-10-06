# Chapter 21 — Testing and code quality

[← Chapter 20](20-hosting-and-rehosting.md) · [README](../../README.md) · Next: [Chapter 22 →](22-results-and-lessons.md)

An **automated test** is a small program that uses your code and checks the result. Run them after
every change: if they still pass, you have not broken what already worked.

---

## 21.1 Run everything

```bash
# Backend — 57 tests (needs requirements-dev.txt)
cd backend
source .venv/bin/activate
pytest                         # prints a dot per passing test; F = failure
black --check app tests        # is the Python code formatted?

# Frontend — 22 tests
cd ../frontend
npm test                       # Vitest
npm run lint                   # ESLint: likely mistakes
npm run typecheck              # TypeScript: type errors
npm run build                  # the production build must succeed
```

All of these pass in the repository. If one fails after your change, read the failure message — it
shows the expected and actual values and the line.

## 21.2 What the backend tests check (`backend/tests/`)

| File                    | Checks                                                                                                                                                                                          |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_preprocessing.py` | Output shape (1,3,224,224); normalisation values; CLAHE deterministic and switchable; EXIF metadata removed; 16-bit PNGs; DICOM reading **and** identifier removal; corrupt files rejected      |
| `test_validator.py`     | Chest X-ray phantoms accepted; colour photos, documents, noise and tiny images rejected; low-resolution warning                                                                                 |
| `test_calibration.py`   | Softmax with temperature; `fit_temperature` recovers a known over-confidence factor and lowers ECE; undefined metrics reported as `None`                                                        |
| `test_gradcam.py`       | Radiological convention (image-left = patient's right); bilateral detection; attention outside lungs flagged; real DenseNet/Swin Grad-CAM shapes; Swin reshape transform                        |
| `test_prediction.py`    | Response schema; Stage 2 skipped for Normal; joint probabilities; 3-class mode; reliability threshold; PyTorch provider with real (random) weights                                              |
| `test_api.py`           | Every endpoint; non-CXR → 422; bad files → 400; history saved/deleted; history disabled; missing models → 503; training status in health                                                        |
| `test_auth.py`          | Password hashing; register/login/logout (token revoked server-side); validation; duplicate email → 409; lockout after 5 failures; login required; **Bob cannot read or delete Alice's history** |
| `test_onnx.py`          | ONNX outputs match PyTorch; **the API runs with PyTorch blocked**                                                                                                                               |

Tests use **synthetic phantoms** (`tests/phantoms.py` draws X-ray-like images with ribs, lungs, heart and
simulated pneumonia) so they run anywhere without patient data, and a **temporary database**
for each test.

## 21.3 What the frontend tests check (`frontend/src/__tests__/`)

Confidence bar accessibility values; labels shown as text (not colour alone); reliability rules; the
probability chart never invents a subtype for Normal results; keyboard navigation; the upload zone
accepts PNG and rejects other files; logged-out users are redirected to login; post-login redirects
cannot leave the site; password rules; clear messages when no backend is connected.

## 21.4 Writing your own test

Backend (pytest) — create `backend/tests/test_mine.py`:

```python
from app.services.calibration import softmax

def test_softmax_sums_to_one():
    p = softmax([2.0, 0.5])
    assert abs(p.sum() - 1.0) < 1e-9
```

Frontend (Vitest) — create `frontend/src/__tests__/mine.test.ts`:

```ts
import { pct } from "@/utils/format";

it("formats percentages", () => {
  expect(pct(0.973)).toBe("97.3%");
});
```

## 21.5 Formatting and style

- Python: **Black** (line length 120, configured in `pyproject.toml`) — run `black app tests`.
- JavaScript/TypeScript: **Prettier** (`npm run format`) and **ESLint** (`npm run lint`).
- Consistent formatting makes changes easy to review: a diff then shows only real changes.

## 21.6 Checking the ML side

Tests cannot tell you whether a model is _good_. For that:

1. Watch training curves (training and validation should improve together).
2. Evaluate on the untouched **test** split (`evaluate.py`).
3. Evaluate on an **external** source (`external_validate.py`).
4. Compare new vs old models on the same images (`compare_versions.py`).
5. Look at the Grad-CAM gallery's failures.

---

Next: **Chapter 22 — Results, lessons and how to improve** → [22-results-and-lessons.md](22-results-and-lessons.md)
