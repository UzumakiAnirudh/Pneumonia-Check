# Chapter 6 — React from zero (and a mini X-ray app)

[← Chapter 5](05-javascript-typescript-basics.md) · [README](../../README.md) · Next: [Chapter 7 →](07-python-basics.md)

React is a library for building user interfaces out of reusable pieces called **components**. Instead of
changing the page by hand (Chapter 5.8), you describe _what the page should look like for the current
data_, and React updates the screen whenever the data changes.

You need Node.js 20+. Keep the PneumoScan backend running on port 8000 for §6.10.

---

## 6.1 Create a React project (3 minutes)

```bash
cd ~/Desktop
npm create vite@latest xray-demo -- --template react-ts
cd xray-demo
npm install
npm run dev
```

Open the address it prints (http://localhost:5173). (Today's template installs React 19; PneumoScan uses
React 18. Everything in this chapter works on both.) Edit `src/App.tsx`, save — the page updates
instantly ("hot reload").

Project anatomy:

| File             | Purpose                                       |
| ---------------- | --------------------------------------------- |
| `index.html`     | The single HTML page, with `<div id="root">`  |
| `src/main.tsx`   | Starts React and draws `<App />` into `#root` |
| `src/App.tsx`    | Your first component                          |
| `package.json`   | Libraries and scripts                         |
| `vite.config.ts` | Dev server settings                           |

## 6.2 Components and JSX

A component is a function that returns **JSX** — HTML-like syntax inside TypeScript:

```tsx
function Title() {
  return <h1>PneumoScan demo</h1>;
}

export default function App() {
  const name = "Dr Rao";
  return (
    <main>
      <Title />
      <p>Welcome, {name}!</p> {/* {...} inserts a JavaScript value */}
      <p>2 + 2 = {2 + 2}</p>
    </main>
  );
}
```

JSX rules:

- Return **one** parent element (wrap siblings in `<div>` or `<>...</>`).
- Use `className` instead of `class`, and `htmlFor` instead of `for`.
- Close every tag: `<img />`, `<input />`.
- Component names start with a **capital letter**.
- `style={{ width: "50%" }}` — style is an object.

## 6.3 Props — passing data into components

```tsx
interface BarProps { label: string; value: number }   // the props' types

function ConfidenceBar({ label, value }: BarProps) {
  return (
    <div>
      <span>{label}: {(value * 100).toFixed(1)}%</span>
      <div style={{ background: "#eee", borderRadius: 8, height: 12 }}>
        <div style={{ background: "#d64545", borderRadius: 8, height: 12, width: `${value * 100}%` }} />
      </div>
    </div>
  );
}

// use it
<ConfidenceBar label="Pneumonia" value={0.973} />
<ConfidenceBar label="Normal" value={0.027} />
```

PneumoScan's real version is `frontend/src/components/ui/ConfidenceBar.tsx`.

## 6.4 State — data that changes

```tsx
import { useState } from "react";

function Counter() {
  const [count, setCount] = useState(0); // [current value, function to change it]
  return (
    <button onClick={() => setCount(count + 1)}>Clicked {count} times</button>
  );
}
```

**Never change state directly** (`count = 5` does nothing); always call the setter. When state changes,
React re-runs the component function and updates only what changed on screen.

## 6.5 Events and forms ("controlled inputs")

```tsx
function ThresholdSetting() {
  const [threshold, setThreshold] = useState(0.75);
  return (
    <label>
      Threshold: {Math.round(threshold * 100)}%
      <input
        type="range"
        min={0.5}
        max={0.99}
        step={0.01}
        value={threshold}
        onChange={(e) => setThreshold(Number(e.target.value))}
      />
    </label>
  );
}
```

The input _shows_ state and _changes_ state — so the state is the single source of truth.

## 6.6 Conditional rendering and lists

```tsx
{
  isLoading && <p>Analyzing…</p>;
} // show only if true
{
  error ? <p className="error">{error}</p> : <p>All good</p>;
} // either/or

const labels = ["NORMAL", "BACTERIAL", "VIRAL"];
<ul>
  {labels.map((l) => (
    <li key={l}>{l}</li>
  ))}{" "}
  {/* key = a stable unique id */}
</ul>;
```

React needs `key` on list items to track them efficiently.

## 6.7 Effects — doing things after drawing

`useEffect` runs code after the component appears (or when listed values change) — e.g. loading data:

```tsx
import { useEffect, useState } from "react";

function ServerStatus() {
  const [status, setStatus] = useState("checking…");
  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("offline"));
  }, []); // [] = run once, when the component first appears
  return <p>Backend: {status}</p>;
}
```

The array is the **dependency list**: `[userId]` would re-run whenever `userId` changes. Return a function
from the effect to clean up (stop timers, remove listeners).

## 6.8 Custom hooks — reusable logic

A function starting with `use` that uses other hooks:

```tsx
function useHealth() {
  const [status, setStatus] = useState("checking…");
  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setStatus(d.status));
  }, []);
  return status;
}
// any component: const status = useHealth();
```

PneumoScan examples: `useZoomPan` (viewer zoom), `useRunAnalysis` (the Analyze flow), `useApiStatus`.

## 6.9 The bigger toolbox (what PneumoScan adds)

| Need                             | Library              | Tiny example                                                                                                  |
| -------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------- |
| Several pages                    | **react-router-dom** | `<Route path="/history" element={<HistoryPage />} />`, `<Link to="/analyze">`, `useNavigate()`, `useParams()` |
| Shared state across pages        | **Zustand**          | `const useSettings = create((set) => ({ threshold: 0.75, setThreshold: (t) => set({ threshold: t }) }))`      |
| Server data with caching/retries | **TanStack Query**   | `const { data, isLoading } = useQuery({ queryKey: ["health"], queryFn: api.health })`                         |
| Styling                          | **Tailwind**         | `<div className="rounded-xl bg-white p-4 shadow">`                                                            |
| Animation                        | **Framer Motion**    | `<motion.div animate={{ opacity: 1 }} />`                                                                     |
| Icons                            | **lucide-react**     | `<ScanSearch className="h-5 w-5" />`                                                                          |
| Charts                           | **Recharts**         | `<LineChart data={...}><Line dataKey="tpr" /></LineChart>`                                                    |
| Drag-and-drop upload             | **react-dropzone**   | `useDropzone({ onDrop })`                                                                                     |

## 6.10 Mini project: a tiny X-ray analyzer (30 minutes)

This uses the real PneumoScan backend, so you see the whole system from the outside.

**1. Forward `/api` to the backend.** Replace `vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } }, // same idea as PneumoScan's config
});
```

Restart `npm run dev`. Because the website and the API now share one address, the login cookie works.

**2. Replace `src/App.tsx`:**

```tsx
import { useState } from "react";

interface ModelResult {
  model_name: string;
  final_label: string;
  final_confidence: number;
  explanation: { heatmap_png: string; description: string } | null;
}

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<{
    image_png: string;
    results: ModelResult[];
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function login() {
    setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) setLoggedIn(true);
    else setError((await res.json()).detail?.message ?? "Login failed");
  }

  async function analyze() {
    if (!file) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    form.append("model", "densenet");
    const res = await fetch("/api/predict", { method: "POST", body: form });
    const body = await res.json();
    if (res.ok) setResult(body);
    else setError(body.detail?.message ?? "Analysis failed");
    setBusy(false);
  }

  if (!loggedIn) {
    return (
      <main
        style={{ maxWidth: 360, margin: "40px auto", fontFamily: "system-ui" }}
      >
        <h1>Log in</h1>
        <p>Use an account you registered in the PneumoScan app.</p>
        <input
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={login}>Log in</button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </main>
    );
  }

  const r = result?.results[0];
  return (
    <main
      style={{ maxWidth: 640, margin: "40px auto", fontFamily: "system-ui" }}
    >
      <h1>Mini X-ray analyzer</h1>
      <input
        type="file"
        accept=".png,.jpg,.jpeg"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button onClick={analyze} disabled={!file || busy}>
        {busy ? "Analyzing…" : "Analyze"}
      </button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {result && r && (
        <section>
          <h2>
            {r.final_label} — {(r.final_confidence * 100).toFixed(1)}%
          </h2>
          <p>
            {r.model_name}: {r.explanation?.description}
          </p>
          <div style={{ position: "relative", width: 320 }}>
            <img
              src={result.image_png}
              alt="X-ray"
              style={{ width: "100%", display: "block" }}
            />
            {r.explanation && (
              <img
                src={r.explanation.heatmap_png}
                alt=""
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  opacity: 0.45,
                }}
              />
            )}
          </div>
        </section>
      )}
    </main>
  );
}
```

**3. Try it:** log in with your PneumoScan account, choose an X-ray, press Analyze. You will see the label,
confidence, the sentence about where the model looked, and the heatmap overlay — the same stacked-image
technique PneumoScan's viewer uses.

**What you practised:** state, events, controlled inputs, conditional rendering, async `fetch` with JSON
and `FormData`, error handling, and layering images with CSS positioning.

## 6.11 Build for production

```bash
npm run build      # creates dist/ — plain HTML/CSS/JS files any web host can serve
npm run preview    # test the built version locally
```

That `dist/` folder is exactly what Vercel serves for PneumoScan (Chapter 20).

## 6.12 Where to look in PneumoScan next

`src/App.tsx` (routes) → `src/pages/AnalyzePage.tsx` → `src/features/analysis/useRunAnalysis.ts` →
`src/pages/ResultsPage.tsx`. Chapter 17 walks through every file.

---

Next: **Chapter 7 — Python from zero** → [07-python-basics.md](07-python-basics.md)
