# Chapter 13 — Deployment: putting it on the internet for free

[← Chapter 12](12-rebuild-from-scratch.md) · [README](../../README.md) · Next: [Chapter 14 →](14-testing-and-quality.md)

The website and the AI backend are hosted separately, both free, both redeploying automatically every
time you push to GitHub.

```mermaid
flowchart LR
  U[Visitor's browser] -->|https://your-site.vercel.app| V[Vercel<br/>website files]
  V -->|/api/* forwarded| R[Render free web service<br/>FastAPI + ONNX models]
  R --> DB[(SQLite on the instance<br/>or free Postgres)]
  G[GitHub repository] -->|push| V
  G -->|push| R
```

Because Vercel forwards `/api/*`, the browser only ever talks to **one** address — so the login cookie
works without any cross-site configuration.

---

## 13.1 Why not one host?

| Need                  | Problem                                                                       | Solution used                                                                            |
| --------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Website               | Static files — any host works                                                 | **Vercel** (free, global CDN)                                                            |
| AI backend            | Must run Python with the models; PyTorch alone is ~700 MB and needs >1 GB RAM | **ONNX Runtime** instead of PyTorch (~350 MB RAM total) on **Render's free 512 MB plan** |
| Model files on GitHub | GitHub rejects files > 100 MB; Swin was 113 MB                                | Swin's matrix weights stored in 8 bits → 31 MB                                           |

Things we tried that did **not** work for free (so you don't have to): Hugging Face _Docker/Gradio_
Spaces now require a paid PRO plan (static Spaces are free but cannot run Python); free tiers with
512 MB RAM cannot run full PyTorch with four models.

## 13.2 Step 1 — Put the project on GitHub

1. Create an empty repository on https://github.com/new (no README).
2. In the project folder:
   ```bash
   git init -b main                      # skip if already a git repository
   git add -A
   git commit -m "PneumoScan AI"
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. If the push says **403 / Permission denied to `other-user`**, your Mac remembers a different GitHub
   account. Fix:
   ```bash
   printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain erase   # macOS
   gh auth login --web && gh auth setup-git                                           # log in as the repo owner
   git push -u origin main
   ```
   (Or add the other account as a collaborator: repository → _Settings → Collaborators_.)

What gets uploaded is controlled by `.gitignore`: code, the ONNX models, the dashboard metrics and
examples — **not** the datasets, the local database, `.venv` or `node_modules`.

## 13.3 Step 2 — The backend on Render (free)

`render.yaml` (in the project root) describes the service:

```yaml
services:
  - type: web
    name: pneumonia-check-api # → https://pneumonia-check-api.onrender.com
    runtime: python
    plan: free
    rootDir: backend
    buildCommand: pip install -r requirements-deploy.txt # no PyTorch
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/health
    # envVars: PYTHON_VERSION 3.11.9, MODEL_BACKEND onnx, COOKIE_SECURE true, ...
    #          (excerpt — copy the real render.yaml, which lists them in Render's format)
```

1. Go to https://render.com → **Get Started** → **Sign in with GitHub** (no card needed).
2. **New → Blueprint** → choose your repository → Render shows `pneumonia-check-api`.
3. If asked for `DATABASE_URL`, leave it **empty** (or see §13.5) → **Apply**.
4. Wait for the build (~5–10 minutes) until the service is **Live**.
5. Check: `https://<service-name>.onrender.com/api/health` → `{"status":"ok", "device":"cpu (onnxruntime)", ...}`.

If the name is taken, Render adds a suffix — then update the address in `vercel.json` (§13.4).

**Free-plan behaviour:** the service **sleeps after ~15 minutes without traffic**; the next request wakes
it in about a minute (the website may show "not connected" during that minute — retry).

## 13.4 Step 3 — The website on Vercel (free)

`vercel.json` (project root) builds the frontend and forwards the API:

```json
{
  "installCommand": "cd frontend && npm ci",
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://pneumonia-check-api.onrender.com/api/$1"
    },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

1. https://vercel.com → sign in with GitHub → **Add New → Project** → import your repository.
2. Leave **Root Directory** empty (the root `vercel.json` handles everything) → **Deploy**.
3. Open the `*.vercel.app` address → **Register** → **Analyze**.

The second rewrite sends every other path (`/login`, `/analyze`, ...) to `index.html` so React's router
can handle it — without it, refreshing on `/history` gives "404 Not Found".

## 13.5 Optional — keep accounts permanently (free Postgres)

On Render's free plan the disk is temporary: accounts and history disappear when the service restarts
or redeploys. To keep them:

1. Create a free database at https://neon.tech (sign in with GitHub, no card).
2. Copy its **connection string** (`postgresql://user:password@host/db?sslmode=require`).
3. Render → your service → **Environment** → set `DATABASE_URL` to it → **Save** (it redeploys).

The backend creates the tables automatically (`app/db.py`); no other change is needed.

## 13.6 Updating the live site

```bash
git add -A && git commit -m "What I changed" && git push
```

Vercel and Render both redeploy automatically within a few minutes. If you retrain models, run
`python training/export_onnx.py` before committing so the `.onnx` files are updated.

## 13.7 Problems we actually hit (and the fixes)

| Symptom                                                                      | Cause                                                                                                                           | Fix                                                                                 |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Vercel: **404 NOT_FOUND** for every page                                     | Vercel built the repository root, which has no website                                                                          | The root `vercel.json` (§13.4)                                                      |
| Register fails with **405** / "analysis server is not connected"             | The website has no backend behind `/api`                                                                                        | Deploy the backend (§13.3) and the `/api` rewrite                                   |
| `…onrender.com` says **Not Found** with header `x-render-routing: no-server` | No Render service exists yet (or the code with `render.yaml` was not pushed)                                                    | Push, then create the Blueprint                                                     |
| Vercel shows a **Request Access** page                                       | Vercel _Deployment Protection_ on preview URLs                                                                                  | Use the main production URL, or disable it in _Settings → Deployment Protection_    |
| Swin gives much lower confidences online than locally                        | ONNX Runtime's fast 8-bit kernels on Intel/AMD servers can **saturate** with _signed_ 8-bit weights; Apple chips are unaffected | Export Swin with **unsigned** 8-bit, per-channel weights (`export_onnx.py` default) |
| Hugging Face: "Docker Spaces require PRO" (402)                              | Policy change on Hugging Face                                                                                                   | Use Render (free) — or pay for PRO and use `deploy/huggingface/`                    |

## 13.8 Costs and limits summary

| Service         | Free tier used    | Limits that matter                              |
| --------------- | ----------------- | ----------------------------------------------- |
| GitHub          | Public repository | 100 MB per file                                 |
| Vercel          | Hobby             | Personal/non-commercial use                     |
| Render          | Free web service  | 512 MB RAM, sleeps after idle, temporary disk   |
| Neon (optional) | Free Postgres     | Small storage — plenty for accounts and history |

---

Next: making sure everything still works after you change it → [Chapter 14](14-testing-and-quality.md)
