# Chapter 20 — Hosting and re-hosting from scratch (free)

[← Chapter 19](19-docker.md) · [README](../../README.md) · Next: [Chapter 21 →](21-testing-and-quality.md)

This chapter puts PneumoScan on the internet under **your own accounts**, from nothing, for free — and
explains how to move it, update it, roll it back, or host it elsewhere. Follow the steps in order; each
ends with a check.

---

## 20.1 The big picture

```mermaid
flowchart LR
  U[Visitor's browser] -->|https://your-site.vercel.app| V[Vercel<br/>website files]
  V -->|/api/* forwarded| R[Render free web service<br/>FastAPI + ONNX models]
  R --> DB[(SQLite on the instance<br/>or free Postgres on Neon)]
  G[Your GitHub repository] -->|every push| V
  G -->|every push| R
```

| Piece                        | Host       | Why this host                                            | Cost         |
| ---------------------------- | ---------- | -------------------------------------------------------- | ------------ |
| Code                         | **GitHub** | Both hosts deploy straight from it                       | Free         |
| Website (static files)       | **Vercel** | Fast global hosting for static sites; builds from GitHub | Free (Hobby) |
| AI backend                   | **Render** | Runs a Python web service for free (512 MB RAM)          | Free         |
| Accounts database (optional) | **Neon**   | Free Postgres that survives restarts                     | Free         |

Why not one host? The AI needs a Python server; the free way to run one is Render, but only with ~512 MB of
memory — which is why the backend runs the models with **ONNX Runtime** (~350 MB total) instead of PyTorch
(Chapter 14.9). Vercel forwards `/api/*` to Render, so visitors see one address and login cookies work.

Things that do **not** work for free (tested): Hugging Face _Docker/Gradio_ Spaces (now require a paid PRO
plan; static Spaces cannot run Python), and free 512 MB tiers running full PyTorch with four models.

## 20.2 Before you start

Create these free accounts (each takes ~2 minutes; "Sign in with GitHub" is easiest):

1. **GitHub** — https://github.com/signup
2. **Render** — https://render.com (no card needed)
3. **Vercel** — https://vercel.com/signup (choose _Hobby_)
4. _(Optional)_ **Neon** — https://neon.tech

Decide two names now (lowercase, hyphens):

- your **repository** name, e.g. `pneumoscan`;
- your **backend service** name, e.g. `pneumoscan-api-yourname` → its address will be
  `https://pneumoscan-api-yourname.onrender.com`. Check it is free: open that address — Render's
  "Not Found" page with header `x-render-routing: no-server` means nobody uses it.

## 20.3 Step 1 — Your own copy on GitHub

**Option A — Fork (easiest):** open https://github.com/UzumakiAnirudh/Pneumonia-Check → **Fork** →
**Create fork**. You now own `https://github.com/<you>/Pneumonia-Check`. Then download it:

```bash
git clone https://github.com/<you>/Pneumonia-Check.git
cd Pneumonia-Check
```

**Option B — From a copy you received (zip or folder):**

1. On GitHub: **+ → New repository** → name it → **Public** → do _not_ add a README → **Create**.
2. In a terminal, inside the project folder:
   ```bash
   git init -b main                     # skip if the folder already has .git
   git add -A
   git commit -m "PneumoScan AI"
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

**Logging in for `git push`:** GitHub no longer accepts your password in the terminal. Easiest:

```bash
brew install gh          # macOS; Windows/Linux: https://cli.github.com
gh auth login --web      # choose GitHub.com → HTTPS → log in in the browser
gh auth setup-git
```

If `git push` says **403 — Permission to … denied to `some-other-account`**, your computer remembers a
different GitHub account. Clear it and log in again:

```bash
printf "protocol=https\nhost=github.com\n\n" | git credential-osxkeychain erase    # macOS
# Windows: Control Panel → Credential Manager → Windows Credentials → remove "git:https://github.com"
gh auth login --web && gh auth setup-git
```

**Check:** your repository page on GitHub shows `README.md`, `render.yaml`, `vercel.json`, `backend/`,
`frontend/`.

## 20.4 Step 2 — Point the files at your names

Edit two lines (VS Code), using your backend service name from §20.2:

1. **`render.yaml`** → `name: pneumonia-check-api` → `name: pneumoscan-api-yourname`
2. **`vercel.json`** → in the first rewrite, change the destination host:
   `"destination": "https://pneumoscan-api-yourname.onrender.com/api/$1"`

Commit and push:

```bash
git add render.yaml vercel.json
git commit -m "Use my own hosting names"
git push
```

## 20.5 Step 3 — The backend on Render

1. Open https://dashboard.render.com → **New +** → **Blueprint**.
2. **Connect GitHub** if asked; allow access to your repository → select it → **Connect**.
3. Render reads `render.yaml` and lists the web service **pneumoscan-api-yourname**.
4. For `DATABASE_URL`: leave **empty** for now (or paste a Neon URL, §20.7). Click **Apply**.
5. Open the service → **Events / Logs**. The build installs `requirements-deploy.txt` (no PyTorch) and
   starts `uvicorn`. Wait until the status says **Live** (~5–10 minutes the first time). Healthy log lines:
   ```
   INFO app.models.factory: Model backend: onnx
   INFO pneumoscan: Ready: provider=OnnxModelProvider mode=two_stage device=cpu (onnxruntime) ...
   ```
6. **Check:** open `https://pneumoscan-api-yourname.onrender.com/api/health` →
   `{"status":"ok", ... "device":"cpu (onnxruntime)", ...}`.

What `render.yaml` sets up: Python 3.11, root folder `backend/`, install `requirements-deploy.txt`, start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`, auto-deploy on every push,
and the settings `MODEL_BACKEND=onnx`, `COOKIE_SECURE=true`, `HISTORY_ENABLED=true`.

**Free-plan behaviour:** after ~15 minutes without visitors the service sleeps; the next request wakes it in
about a minute.

## 20.6 Step 4 — The website on Vercel

1. Open https://vercel.com/new → **Import Git Repository** → pick your repository → **Import**.
2. Settings screen: leave **Root Directory** empty and the other fields as detected — the root
   `vercel.json` tells Vercel to install and build `frontend/` and publish `frontend/dist`. Click **Deploy**.
3. Wait ~1–2 minutes → **Congratulations** → click the preview to open `https://<project>.vercel.app`.
4. **Check:** open `https://<project>.vercel.app/api/health` — the _same_ JSON as Render's, proving the
   forwarding works. Then on the site: **Register** → **Analyze** → pick a sample → **Analyze**.

Use the **production** address (_Project → Domains_). Preview addresses can show a **"Request Access"**
page because of Vercel's _Deployment Protection_; disable it under _Settings → Deployment Protection_ if
you want previews public.

## 20.7 Step 5 (optional) — Keep accounts permanently with Neon

Render's free disk is temporary: accounts and history vanish when the service restarts or redeploys.
To keep them:

1. https://console.neon.tech → **New Project** → any name → region near your Render region → **Create**.
2. On the project dashboard, copy the **connection string**
   (`postgresql://user:password@ep-....neon.tech/neondb?sslmode=require`).
3. Render → your service → **Environment** → `DATABASE_URL` → paste → **Save changes** (it redeploys).
4. **Check:** register on the website, wait for or trigger a redeploy (_Manual Deploy → Deploy latest
   commit_), log in again — your account still exists.

The backend creates its tables automatically; nothing else changes.

## 20.8 End-to-end checklist

- [ ] `https://<backend>.onrender.com/api/health` → `"status":"ok"`
- [ ] `https://<site>.vercel.app/api/health` → same JSON
- [ ] Register, log out, log in again
- [ ] Analyze a sample with _Compare Both_ → results, heatmaps, PDF download
- [ ] History shows the analysis; a second account (private window) does **not** see it
- [ ] Model Performance page shows charts
- [ ] Settings → API status: _API online · trained models_

## 20.9 Updating, rolling back, monitoring

- **Update:** change code → `git add -A && git commit -m "..." && git push`. Vercel and Render rebuild
  automatically (watch progress in their dashboards).
- **New models:** retrain (Chapter 15) → `python training/export_onnx.py` → commit and push.
- **Roll back:** Vercel → _Deployments_ → an older one → **⋯ → Promote to Production**. Render → service →
  _Events_ → an earlier deploy → **Rollback**.
- **Logs:** Render → service → _Logs_ (backend errors); Vercel → deployment → _Functions/Build logs_
  (build errors); your browser's DevTools → _Network_ (request failures).

## 20.10 Your own domain (optional)

Buy a domain from any registrar → Vercel → _Project → Settings → Domains_ → add it → set the DNS records
Vercel shows. The `/api` forwarding keeps working because it lives in `vercel.json`.

## 20.11 Secrets and safety checklist

- `COOKIE_SECURE=true` in production (already set by `render.yaml`).
- Never commit tokens, passwords or `.env` files (they are git-ignored). Store secrets in the host's
  **Environment** settings.
- If a token is ever pasted somewhere public (a chat, an issue, a screenshot), **revoke it immediately** and
  create a new one.
- Real patient images need consent and ethics approval (Chapter 13.6) — and a host contract that permits
  health data. The free tiers here are for demos and coursework.

## 20.12 Hosting elsewhere

| Option                                            | Cost                   | How                                                                                                |
| ------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------- |
| Hugging Face Space (Docker)                       | PRO subscription       | `bash deploy/huggingface/prepare_space.sh <cloned-space>` then push (kit in `deploy/huggingface/`) |
| Any Linux VM (cloud server)                       | From a few $/month     | Docker Compose (Chapter 19.7) behind a reverse proxy with HTTPS                                    |
| Render / Fly.io / Railway / Cloud Run with Docker | Paid tiers for >512 MB | Point the service at `backend/Dockerfile`                                                          |
| University / hospital server                      | Varies                 | Chapter 2 setup + a process manager and HTTPS; ask IT about health-data rules                      |

**Moving accounts between databases:** with Postgres use `pg_dump` / `pg_restore`; the local SQLite file is
`backend/data/history.db`.

## 20.13 Problems we actually hit (and the fixes)

| Symptom                                                               | Cause                                                                                                                | Fix                                                                                  |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Vercel: **404 NOT_FOUND** for every page                              | Vercel built the repository root, which has no website                                                               | The root `vercel.json` (§20.6)                                                       |
| Register fails with **405** / "analysis server is not connected"      | No backend behind `/api` yet                                                                                         | Deploy Render (§20.5) and set the rewrite (§20.4)                                    |
| `…onrender.com` → **Not Found**, header `x-render-routing: no-server` | No Render service with that name (or `render.yaml` not pushed)                                                       | Push, then create the Blueprint                                                      |
| Vercel shows **Request Access**                                       | Deployment Protection on preview URLs                                                                                | Use the production URL or disable protection                                         |
| Swin's confidence much lower online than locally                      | ONNX Runtime's fast 8-bit kernels on Intel/AMD servers saturate with _signed_ 8-bit weights (Apple chips unaffected) | Export Swin with **unsigned** per-channel 8-bit weights — `export_onnx.py`'s default |
| Hugging Face: **402**, "Docker Spaces require PRO"                    | Hugging Face policy                                                                                                  | Use Render (free) or subscribe                                                       |
| `git push` **403** to another account                                 | Saved credentials for a different GitHub user                                                                        | §20.3                                                                                |

## 20.14 Limits summary

| Service | Free tier         | Limits that matter                              |
| ------- | ----------------- | ----------------------------------------------- |
| GitHub  | Public repository | 100 MB per file                                 |
| Vercel  | Hobby             | Personal / non-commercial use                   |
| Render  | Free web service  | 512 MB RAM, sleeps when idle, temporary disk    |
| Neon    | Free Postgres     | Small storage — plenty for accounts and history |

---

Next: **Chapter 21 — Testing and code quality** → [21-testing-and-quality.md](21-testing-and-quality.md)
