# Chapter 8 — FastAPI from zero (build a small image API)

[← Chapter 7](07-python-basics.md) · [README](../../README.md) · Next: [Chapter 9 →](09-web-apis-databases-security.md)

**FastAPI** is the Python framework PneumoScan's backend is built with. It turns Python functions into
web addresses (URLs) that browsers and other programs can call. In this chapter you build a small API
step by step; every feature you use is one PneumoScan uses.

---

## 8.1 Set up a practice project

```bash
mkdir ~/Desktop/fastapi-practice && cd ~/Desktop/fastapi-practice
python3 -m venv .venv
source .venv/bin/activate                    # Windows: .venv\Scripts\activate
pip install fastapi "uvicorn[standard]" python-multipart pydantic-settings numpy opencv-python-headless httpx pytest
```

| Package                           | Why                                                         |
| --------------------------------- | ----------------------------------------------------------- |
| `fastapi`                         | The framework                                               |
| `uvicorn`                         | The server program that listens on a port and runs your app |
| `python-multipart`                | Needed to receive uploaded files and forms                  |
| `pydantic-settings`               | Settings from environment variables                         |
| `numpy`, `opencv-python-headless` | Image handling                                              |
| `httpx`, `pytest`                 | Testing                                                     |

## 8.2 Hello, API

`main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Practice API")


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

Run it:

```bash
uvicorn main:app --reload --port 8000
```

- `main:app` = "the variable `app` in the file `main.py`".
- `--reload` restarts automatically when you save a file (development only).

Open http://localhost:8000/api/health → `{"status":"ok"}`.
Open **http://localhost:8000/docs** → interactive documentation generated automatically; you can call
every endpoint from there with _Try it out_.

`@app.get("/api/health")` is a **decorator**: it registers the function below it to handle `GET` requests
to that path. Returning a dict produces JSON.

## 8.3 Path and query parameters

```python
@app.get("/api/models/{name}")                        # {name} is a path parameter
def model_info(name: str, details: bool = False):     # details is a query parameter (?details=true)
    info = {"name": name}
    if details:
        info["family"] = "CNN" if name == "densenet" else "Transformer"
    return info
```

http://localhost:8000/api/models/densenet?details=true → `{"name":"densenet","family":"CNN"}`.
FastAPI converts `"true"` to the `bool` `True` because of the type hint — and rejects `?details=banana`
with a **422** error explaining why.

## 8.4 Request bodies with Pydantic

```python
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8)


@app.post("/api/register")
def register(body: RegisterRequest):
    # body is already validated here
    return {"message": f"Welcome, {body.name}"}
```

Try it in `/docs` with a 3-character password: FastAPI answers **422** with the exact field and rule
that failed — you wrote no validation code. PneumoScan's real version: `backend/app/schemas/auth.py`.

## 8.5 Response models and status codes

```python
from fastapi import HTTPException


class Reliability(BaseModel):
    level: str
    threshold: float


@app.get("/api/reliability", response_model=Reliability)
def reliability(confidence: float, threshold: float = 0.75):
    if not 0 <= confidence <= 1:
        raise HTTPException(status_code=400, detail="confidence must be between 0 and 1")
    return Reliability(level="high" if confidence >= threshold else "low", threshold=threshold)
```

`response_model` documents and enforces the output shape. `HTTPException` returns an error status.
PneumoScan wraps this in `api_error()` (`backend/app/api/errors.py`) so every error looks like
`{"detail": {"code": "...", "message": "..."}}`.

## 8.6 Uploading an image (the heart of PneumoScan)

```python
import cv2
import numpy as np
from fastapi import File, Form, UploadFile


@app.post("/api/brightness")
async def brightness(file: UploadFile = File(...), side: str = Form("both")):
    data = await file.read()                                   # the uploaded bytes, in memory
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise HTTPException(status_code=400, detail="Not an image")
    h, w = img.shape
    region = {"left": img[:, : w // 2], "right": img[:, w // 2 :]}.get(side, img)
    return {"filename": file.filename, "width": w, "height": h, "mean_brightness": float(region.mean())}
```

Test from a terminal (**curl** sends HTTP requests; `-F` sends a form field, `@` means "this file"):

```bash
curl -F file=@/path/to/xray.jpeg -F side=left http://localhost:8000/api/brightness
```

Or use _Try it out_ in `/docs`, which shows a file picker.

`async def` + `await file.read()` lets the server handle other requests while the upload arrives.

## 8.7 Dependencies — shared logic before your endpoint

```python
from fastapi import Depends, Header


def require_api_key(x_api_key: str = Header(...)):            # reads the "X-API-Key" header
    if x_api_key != "secret123":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.get("/api/private")
def private(_key: str = Depends(require_api_key)):
    return {"message": "You are allowed in"}
```

Any endpoint that declares `Depends(require_api_key)` is protected: a wrong key gets **401**, a missing
header **422** (a required input is missing). PneumoScan's `current_user`
dependency (`backend/app/api/deps.py`) works the same way, but reads a **session cookie** instead.

## 8.8 Cookies — a tiny login

```python
import secrets
from fastapi import Request, Response

SESSIONS: dict[str, str] = {}          # token → user (PneumoScan stores a *hash* of the token in a database)


@app.post("/api/login")
def login(body: RegisterRequest, response: Response):
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = body.email
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=7 * 24 * 3600)
    return {"email": body.email}


@app.get("/api/me")
def me(request: Request):
    email = SESSIONS.get(request.cookies.get("session", ""))
    if email is None:
        raise HTTPException(status_code=401, detail="Please log in")
    return {"email": email}
```

The browser stores the cookie and sends it back automatically on every request to the same site.
(Never store real passwords like this — Chapter 9 explains hashing.)

## 8.9 Doing work once at start-up: lifespan

Loading a neural network takes seconds — do it once when the server starts, not on every request.
Add the `lifespan` function near the top of `main.py` and **change the existing** `app = FastAPI(...)`
line to pass it (do not create a second `app`, or the routes defined earlier would be lost):

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = "pretend this is a loaded model"   # runs at start-up
    yield
    # code here runs at shut-down


app = FastAPI(title="Practice API", lifespan=lifespan)     # ← the one and only app line

@app.get("/api/model")
def model(request: Request):
    return {"model": request.app.state.model}
```

PneumoScan's `build_services()` in `backend/app/main.py` loads the models, validator, database and
auth service this way.

## 8.10 Heavy work without freezing the server

Running a model blocks the CPU for a while. Inside an `async` endpoint, push it to a worker thread:

```python
from fastapi.concurrency import run_in_threadpool

def slow_predict(data: bytes) -> dict:
    ...                                   # CPU-heavy work

@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    data = await file.read()
    return await run_in_threadpool(slow_predict, data)
```

## 8.11 Settings from the environment

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    default_threshold: float = 0.75
    history_enabled: bool = True


settings = Settings()      # reads DEFAULT_THRESHOLD / HISTORY_ENABLED from the environment or .env
```

Run `DEFAULT_THRESHOLD=0.8 uvicorn main:app` and `settings.default_threshold` is `0.8`. Full version:
`backend/app/config.py`.

## 8.12 CORS, static files and routers

```python
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app.add_middleware(                                 # allow a website on another address to call the API
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,                         # allow cookies
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.mount("/samples", StaticFiles(directory="samples"), name="samples")   # serve files as-is (create a samples/ folder first)

router = APIRouter(prefix="/api/history", tags=["history"])              # group related endpoints

@router.get("")
def list_history():
    return []

app.include_router(router)
```

PneumoScan splits endpoints into `api/routes.py` and `api/auth_routes.py` with routers.

## 8.13 Testing your API

`test_main.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_register_rejects_short_password():
    r = client.post("/api/register", json={"name": "A", "email": "a@b.co", "password": "123"})
    assert r.status_code == 422
```

Run `pytest`. `TestClient` calls your app directly — no server needed. PneumoScan has 57 such tests
(Chapter 21).

## 8.14 How this maps onto PneumoScan

| You built                           | PneumoScan's real version                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------------- |
| `main.py` with `app = FastAPI(...)` | `backend/app/main.py` (`create_app`, `build_services`)                                            |
| `/api/health`                       | `GET /api/health` in `backend/app/api/routes.py`                                                  |
| Pydantic `RegisterRequest`          | `backend/app/schemas/auth.py`, `schemas/prediction.py`                                            |
| `/api/brightness` upload            | `POST /api/predict` and `/api/validate`                                                           |
| `require_api_key` dependency        | `current_user` in `backend/app/api/deps.py`                                                       |
| Toy cookie login                    | `backend/app/api/auth_routes.py` + `services/auth.py` (hashed passwords, hashed tokens, database) |
| `lifespan`                          | `create_app()` in `main.py`                                                                       |
| `Settings`                          | `backend/app/config.py`                                                                           |
| `TestClient` tests                  | `backend/tests/`                                                                                  |

## 8.15 Exercises

1. Add `GET /api/labels` returning `["NORMAL", "BACTERIAL", "VIRAL"]`.
2. Make `/api/brightness` return **413** if the file is larger than 5 MB.
3. Add a `/api/logout` that deletes the session and the cookie (`response.delete_cookie("session")`).
4. Write tests for exercises 1–3.
5. Read `backend/app/api/routes.py` from top to bottom — you should now understand every line.

---

Next: **Chapter 9 — The web, APIs, databases and security** → [09-web-apis-databases-security.md](09-web-apis-databases-security.md)
