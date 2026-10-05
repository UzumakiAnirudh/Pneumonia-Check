# Chapter 4 — Programming basics (everything this project uses)

[← Chapter 3](03-how-it-works.md) · [README](../../README.md) · Next: [Chapter 5 →](05-deep-learning-fundamentals.md)

You will learn just enough of each language and tool to read and change this project. Every example
is runnable. To try Python snippets, type `python3` in a terminal (exit with `exit()`); to try
JavaScript, open your browser's developer tools (`F12` → _Console_).

---

## Part A — Python

Python reads almost like English. It runs top to bottom, one line at a time.

### A.1 Values, variables and types

```python
age = 4                    # an int (whole number)
confidence = 0.973         # a float (decimal number)
label = "PNEUMONIA"        # a str (text)
is_valid = True            # a bool (True/False)
nothing = None             # "no value"

print(label, confidence)   # PNEUMONIA 0.973
print(f"{confidence:.1%}") # 97.3%   ← an f-string formats values into text
```

### A.2 Collections

```python
labels = ["NORMAL", "BACTERIAL", "VIRAL"]       # list (ordered, changeable)
labels[0]                                        # "NORMAL" (counting starts at 0)
probs = {"NORMAL": 0.1, "PNEUMONIA": 0.9}        # dict (key → value)
probs["PNEUMONIA"]                               # 0.9
size = (224, 224)                                # tuple (fixed list)
classes = {"NORMAL", "VIRAL"}                    # set (unique items)
```

### A.3 Decisions and loops

```python
if confidence >= 0.75:
    message = "High confidence"
elif confidence >= 0.5:
    message = "Borderline"
else:
    message = "Low confidence"

for name in labels:            # repeat for each item
    print(name)

squares = [x * x for x in range(5)]   # list comprehension → [0, 1, 4, 9, 16]
```

**Indentation matters:** the 4 spaces under `if`/`for` mark the lines that belong to it.

### A.4 Functions

```python
def reliability(confidence: float, threshold: float = 0.75) -> str:
    """Return a human-readable reliability message."""      # docstring
    return "High confidence" if confidence >= threshold else "Low confidence"

reliability(0.9)                 # "High confidence"
reliability(0.9, threshold=0.95) # "Low confidence"
```

`confidence: float` and `-> str` are **type hints**: they document what goes in and out, and tools
check them. They do not change how the code runs.

### A.5 Classes and objects

A **class** bundles data and the functions that work on it. Our model providers are classes:

```python
class MockModelProvider:
    is_mock = True
    def __init__(self, latency_ms: int = 0):      # runs when an object is created
        self.latency_ms = latency_ms
    def infer(self, image):                       # a "method"
        ...

provider = MockModelProvider(latency_ms=150)      # an object (instance)
provider.infer(image)
```

**Inheritance**: `class OnnxModelProvider(ModelProvider)` means "an ONNX provider _is a_
ModelProvider" — it must offer the same methods (`infer`, `status`, ...). This is how the predictor
can use any provider without knowing which one (see `backend/app/models/provider.py`).

**Dataclasses** are short classes that just hold data: `@dataclass class LoadedImage: gray: np.ndarray ...`.

### A.6 Modules, imports and packages

Each `.py` file is a **module**. Folders with `__init__.py` are **packages**. You import code:

```python
from app.services.preprocessing import load_image   # our own code
import numpy as np                                   # an installed library, nicknamed np
```

**pip** installs libraries from the internet into the active **virtual environment**:
`pip install fastapi`. A `requirements.txt` lists them so anyone can run `pip install -r requirements.txt`.

### A.7 Errors (exceptions)

```python
try:
    img = load_image(data)
except ImageDecodeError as err:
    print("Bad image:", err)        # handle it instead of crashing
```

`raise SomeError("message")` signals a problem. FastAPI turns our errors into HTTP error responses.

### A.8 The scientific libraries we use

| Library               | Used for                                          | Tiny example                                      |
| --------------------- | ------------------------------------------------- | ------------------------------------------------- |
| **NumPy** (`np`)      | Fast arrays of numbers — an image _is_ an array   | `img.shape → (224, 224)`; `img.mean()`            |
| **OpenCV** (`cv2`)    | Image operations                                  | `cv2.resize(img, (224, 224))`, CLAHE, colour maps |
| **Pillow** (`PIL`)    | Reading PNG/JPEG                                  | `Image.open(file)`                                |
| **pydicom**           | Reading DICOM medical images                      | `pydicom.dcmread(file)`                           |
| **PyTorch** (`torch`) | Neural networks and training on GPUs              | `model(x)`, `loss.backward()`                     |
| **timm**              | Ready-made model architectures + ImageNet weights | `timm.create_model("densenet121")`                |
| **scikit-learn**      | Metrics and data splitting                        | `roc_auc_score(y, p)`                             |
| **pandas**            | Tables (CSV files)                                | `pd.read_csv("splits.csv")`                       |
| **ONNX Runtime**      | Running exported models without PyTorch           | `session.run(None, {"input": x})`                 |

### A.9 Async (you only need the idea)

`async def` functions can pause while waiting (e.g. for an upload to arrive) so the server can serve
other people meanwhile. Heavy work (running the model) is pushed to a thread pool with
`run_in_threadpool(...)` so it does not block everyone else.

---

## Part B — The web: HTTP, APIs and JSON

### B.1 Client and server

Your **browser** (the client) sends a **request** to a **server**, which sends back a **response**.

A request has:

- a **method** — `GET` (read), `POST` (create/send), `DELETE` (remove);
- a **URL path** — e.g. `/api/predict`;
- **headers** — extra information (e.g. cookies, content type);
- an optional **body** — e.g. the uploaded image.

A response has a **status code** and a body:

| Code            | Meaning                        | Where you meet it here                                  |
| --------------- | ------------------------------ | ------------------------------------------------------- |
| 200 / 201 / 204 | OK / Created / OK with no body | Success, registration, logout                           |
| 400             | Bad request                    | Unreadable image                                        |
| 401             | Not logged in                  | Calling `/api/predict` without logging in               |
| 404             | Not found                      | Someone else's history item (we never reveal it exists) |
| 405             | Method not allowed             | Website hosted without a backend behind `/api`          |
| 409             | Conflict                       | Email already registered                                |
| 413             | Too large                      | Upload over 25 MB                                       |
| 422             | Unprocessable                  | Not a chest X-ray, or invalid form fields               |
| 429             | Too many requests              | Too many wrong passwords                                |
| 503             | Service unavailable            | Model files missing                                     |

An **API** (Application Programming Interface) is the set of URLs a server offers. Ours is listed in
the README and live at `/docs`.

### B.2 JSON

JSON is how the two sides exchange structured data — text that looks like Python dicts/lists:

```json
{
  "model": "densenet",
  "stage1": { "label": "PNEUMONIA", "confidence": 0.973 },
  "stage2": { "label": "BACTERIAL", "confidence": 0.81 },
  "reliability": { "level": "high", "threshold": 0.75 }
}
```

### B.3 FastAPI — building the server

FastAPI turns Python functions into URLs:

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/health")          # a "decorator": run this function for GET /api/health
def health():
    return {"status": "ok"}      # automatically converted to JSON
```

Run with `uvicorn app.main:app` (Uvicorn is the program that listens on the port). Our real
endpoints are in `backend/app/api/routes.py` and `auth_routes.py`.

**Pydantic** models describe the exact shape of data and validate it automatically:

```python
class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str
    password: str = Field(min_length=8)
```

If a request breaks these rules, FastAPI replies `422` with an explanation — no extra code needed.

**Dependencies** (`Depends(...)`) are small functions FastAPI runs before your endpoint — we use one,
`current_user`, to require a valid login on protected routes.

---

## Part C — JavaScript and TypeScript

The website is written in **TypeScript** — JavaScript plus types. Browsers only run JavaScript, so a
build tool (Vite) strips the types away.

```ts
const threshold = 0.75; // const = cannot be reassigned
let attempts = 0; // let = can change
const labels: string[] = ["NORMAL", "BACTERIAL", "VIRAL"];
const probs: Record<string, number> = { NORMAL: 0.1, PNEUMONIA: 0.9 };

function pct(v: number, digits = 1): string {
  return `${(v * 100).toFixed(digits)}%`; // template string
}
const double = (x: number) => x * 2; // arrow function

interface User {
  id: string;
  name: string;
  email: string;
} // a type for objects
type ModelChoice = "densenet" | "swin" | "both"; // one of these strings
```

**Promises and `async`/`await`:** talking to the server takes time, so functions return a _Promise_
that resolves later:

```ts
async function health() {
  const res = await fetch("/api/health"); // wait for the response
  if (!res.ok) throw new Error("Server error");
  return await res.json(); // parse JSON
}
```

`?.` safely reads a property that might be missing (`user?.name`), and `??` supplies a default
(`value ?? 0`).

---

## Part D — HTML, CSS and Tailwind

- **HTML** describes _what_ is on the page: `<button>Analyze</button>`, `<img src="...">`, `<h1>Title</h1>`.
- **CSS** describes _how it looks_: colours, sizes, spacing, layout.
- **Tailwind CSS** lets you style by adding small class names instead of writing CSS files:

```html
<button class="rounded-xl bg-primary px-4 py-2 text-white hover:bg-primary/90">
  Analyze
</button>
<!-- rounded corners, our blue, padding, white text, slightly lighter when hovered -->
```

Our colours (clinical blue, cyan accent, green/red/orange/violet for results) are defined once as
CSS variables in `frontend/src/styles/index.css` and named in `frontend/tailwind.config.ts`. Dark mode
swaps the variables, so every component follows automatically.

Responsive design uses prefixes: `lg:grid-cols-2` means "two columns on large screens only".

---

## Part E — React

React builds interfaces from **components** — functions that return what to show:

```tsx
function ConfidenceBar({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <span>{label}</span>
      <div className="h-3 rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${value * 100}%` }}
        />
      </div>
    </div>
  );
}

// used like an HTML tag:
<ConfidenceBar value={0.973} label="Calibrated confidence" />;
```

- That HTML-like syntax inside TypeScript is **JSX/TSX**.
- **Props** are a component's inputs (`value`, `label`).
- **State** is data that changes over time; changing it re-draws the component:

```tsx
const [opacity, setOpacity] = useState(0.45);
<input
  type="range"
  value={opacity}
  onChange={(e) => setOpacity(Number(e.target.value))}
/>;
```

- **Hooks** are functions starting with `use` that add abilities: `useState` (state),
  `useEffect` (run code after drawing, e.g. check the login once at startup), `useRef`, and our own
  hooks such as `useRunAnalysis` or `useZoomPan`.
- **Routing** (`react-router-dom`): `frontend/src/App.tsx` maps URLs to pages (`/analyze` →
  `AnalyzePage`). `<RequireAuth>` sends logged-out visitors to `/login`.
- **Global state** with **Zustand**: small "stores" any component can read — settings (theme,
  threshold) in `store/settingsStore.ts`, the current analysis in `store/analysisStore.ts`, the
  logged-in user in `features/auth/authStore.ts`.
- **Server data** with **TanStack Query**: `useQuery` fetches, caches and refreshes data such as
  health, metrics and history (`api/hooks.ts`), handling loading and error states for us.
- **Animations** with **Framer Motion**, **icons** with **lucide-react**, **charts** with
  **Recharts**, **PDF reports** with **jsPDF + html2canvas**.

---

## Part F — Tools around the code

| Tool                      | What it does here                                                                                                |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **npm**                   | Installs JavaScript libraries listed in `package.json`; runs scripts: `npm run dev`, `npm run build`, `npm test` |
| **Vite**                  | Super-fast development server and production builder for the website                                             |
| **ESLint** / **Prettier** | Find mistakes / format code consistently (JavaScript)                                                            |
| **Black**                 | Formats Python code consistently                                                                                 |
| **pytest** / **Vitest**   | Run the automated tests (Chapter 14)                                                                             |
| **Git**                   | History and collaboration (Chapter 1)                                                                            |

---

## Part G — Databases

A **database** stores data permanently and lets you query it. Ours uses **SQL** tables:

| Table      | Columns (simplified)                                                        |
| ---------- | --------------------------------------------------------------------------- |
| `users`    | id, email, name, password_hash, created_at                                  |
| `sessions` | token_hash, user_id, expires_at                                             |
| `analyses` | id, user_id, created_at, final_label, confidence, thumbnail, payload (JSON) |

SQL looks like: `SELECT * FROM analyses WHERE user_id = 'abc' ORDER BY created_at DESC;`

We do not write SQL by hand: **SQLModel** lets us describe tables as Python classes and query them
with Python. The database is **SQLite** (a single file, `backend/data/history.db`) locally, or
**PostgreSQL** in the cloud when `DATABASE_URL` is set. Same code for both.

---

## Part H — Logins and security, explained simply

1. **Never store passwords.** We store a **hash**: a one-way scramble. PBKDF2-SHA256 with a random
   **salt** and 310,000 rounds makes guessing slow and makes identical passwords look different.
   To check a login, we hash the attempt the same way and compare.
2. **Sessions.** After login, the server creates a random 256-bit **token**, stores only _its hash_
   in the database, and gives the token to the browser in a **cookie**.
3. **Cookie safety flags:** `HttpOnly` (page scripts cannot read it, so a malicious script cannot
   steal it), `SameSite=Lax` (other websites cannot make your browser send it in a form post — this
   blocks **CSRF** attacks), `Secure` (only over HTTPS, in production).
4. **Every protected request** sends the cookie; the server looks up the token hash, finds the user,
   and **filters every history query by that user's ID** — so one account can never read another's
   analyses, even by guessing an ID.
5. **Brute-force protection:** 5 wrong passwords for an email → locked for 15 minutes.
6. **Logout** deletes the session on the server, so the old cookie stops working everywhere.

The code is short and readable: `backend/app/services/auth.py` and `backend/app/api/auth_routes.py`.

---

You can now read every file in the project. Next, the AI itself → [Chapter 5](05-deep-learning-fundamentals.md)
