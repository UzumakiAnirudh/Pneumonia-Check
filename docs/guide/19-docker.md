# Chapter 19 — Docker from zero

[← Chapter 18](18-rebuild-from-scratch.md) · [README](../../README.md) · Next: [Chapter 20 →](20-hosting-and-rehosting.md)

Docker is **optional** for this project — Chapters 2 and 20 run and host everything without it. It is
still worth learning: it is how most software is shipped to servers, and it makes "it works on my
machine" problems disappear.

> **Honesty note:** the Docker files in this repository follow standard practice and match the code, but
> the project was developed and deployed without Docker, so they have had less real-world testing than
> the rest. If something fails, Chapter 23 and the commands in §19.8 will help you find out why.

---

## 19.1 The problem Docker solves

Running PneumoScan needs a specific Python version, dozens of libraries, system libraries for OpenCV,
Node.js to build the website, and a web server. Setting that up by hand differs on every computer.

Docker packages a program **together with everything it needs** into a sealed, portable unit. Anyone
with Docker can run it identically — on a Mac, Windows, Linux, or a cloud server.

## 19.2 Core ideas

| Term               | Meaning                                                                                   | Analogy                                |
| ------------------ | ----------------------------------------------------------------------------------------- | -------------------------------------- |
| **Image**          | A read-only package: an operating-system base + libraries + your code + the start command | A recipe _and_ all ingredients, frozen |
| **Container**      | A running instance of an image, isolated from your computer                               | A dish cooked from the recipe          |
| **Dockerfile**     | Text file with step-by-step instructions to build an image                                | The written recipe                     |
| **Layer**          | Each instruction adds a cached layer; unchanged layers are reused on rebuild              | Pre-prepared ingredients               |
| **Registry**       | A website storing images (Docker Hub, GitHub Container Registry)                          | A recipe library                       |
| **Port mapping**   | `-p 8080:80` connects port 8080 on your computer to port 80 in the container              | A door between two rooms               |
| **Volume**         | Storage that survives when a container is deleted                                         | A fridge outside the kitchen           |
| **Docker Compose** | A YAML file describing several containers that work together                              | The menu for a full meal               |

Containers are lighter than virtual machines: they share your computer's operating-system kernel instead
of running a whole separate one.

## 19.3 Install Docker

- **macOS / Windows:** install **Docker Desktop** from https://www.docker.com/products/docker-desktop/ and
  start it (whale icon in the menu bar / system tray). Windows uses WSL 2 — the installer sets it up.
- **Linux:** follow https://docs.docker.com/engine/install/ for your distribution.

Check: `docker --version` and `docker compose version`. Try: `docker run hello-world`.

## 19.4 The backend image — `backend/Dockerfile`, line by line

```dockerfile
FROM python:3.11-slim
```

Start from an official, small Debian Linux image with Python 3.11.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
```

Environment variables: don't write `.pyc` files, print logs immediately, don't keep pip's download cache
(smaller image).

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 curl \
    && rm -rf /var/lib/apt/lists/*
```

Install the Linux libraries OpenCV needs, plus `curl` for the health check; delete package lists to save
space. Everything in one `RUN` = one layer.

```dockerfile
WORKDIR /app
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
```

Work in `/app`. Copy **only** the requirements first and install them — so this slow layer is cached and
re-used as long as `requirements.txt` doesn't change, even when your code does. The extra index provides
the CPU-only PyTorch (much smaller than the GPU build).

```dockerfile
COPY app ./app
COPY samples ./samples
COPY metrics ./metrics
COPY weights ./weights
```

Copy the code and data files into the image. `backend/.dockerignore` excludes `.venv`, `tests`, `data`
(your local database) and `.env`, so secrets and junk never enter the image.

```dockerfile
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD curl -fs http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Document the port; let Docker check every 30 s that the API answers; and the command that starts the
server. `--host 0.0.0.0` means "accept connections from outside the container" (the default
`127.0.0.1` would only accept connections from inside it).

Which models does it run? It installs PyTorch **and** ONNX Runtime; with `MODEL_BACKEND=auto` it uses
`.pth` files if present in `weights/`, otherwise the committed `.onnx` files.

## 19.5 The website image — `frontend/Dockerfile` (a "multi-stage" build)

```dockerfile
FROM node:22-alpine AS build          # stage 1: a Node.js image, named "build"
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci                            # exact versions from the lock file (cached layer)
COPY . .
RUN npm run build                     # TypeScript check + Vite build → /app/dist

FROM nginx:1.27-alpine                # stage 2: a tiny web server image
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html   # take ONLY the built files from stage 1
EXPOSE 80
```

The final image contains nginx and the static website — no Node.js, no `node_modules` (~25 MB instead of
hundreds).

`frontend/nginx.conf` explained:

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;              # serve the built website
  client_max_body_size 30m;                # allow X-ray uploads up to 30 MB

  location /api/ {                          # forward API calls to the backend container
    proxy_pass http://backend:8000;         # "backend" = the service name in docker-compose.yml
    proxy_set_header Host $host;
    proxy_read_timeout 120s;                # predictions can take a while
  }
  location /assets/ {                       # Vite's hashed files never change → cache for a year
    expires 1y;
    add_header Cache-Control "public, immutable";
  }
  location / {                              # single-page app: unknown paths → index.html
    try_files $uri $uri/ /index.html;
  }
}
```

Same idea as Vercel's rewrites (Chapter 20) and Vite's dev proxy: the browser talks to one address, so
the login cookie just works.

## 19.6 Both together — `docker-compose.yml`

```yaml
services:
  backend:
    build: ./backend # build from backend/Dockerfile
    environment: # settings (Chapter 16.2); ${X:-default} reads your shell
      USE_MOCK_MODELS: ${USE_MOCK_MODELS:-false}
      CLASSIFICATION_MODE: ${CLASSIFICATION_MODE:-two_stage}
      HISTORY_ENABLED: ${HISTORY_ENABLED:-true}
      DATABASE_URL: sqlite:////data/history.db # database file inside the "history" volume
    volumes:
      - ./backend/weights:/app/weights:ro # use the weights from your folder (read-only)
      - ./backend/metrics:/app/metrics:ro
      - history:/data # named volume: accounts survive container rebuilds
    ports:
      - "8000:8000" # API also reachable at http://localhost:8000
  frontend:
    build: ./frontend
    depends_on: [backend] # start backend first
    ports:
      - "8080:80" # website at http://localhost:8080
volumes:
  history:
```

Compose creates a private network where the containers find each other by **service name** — that is why
nginx can reach `http://backend:8000`.

## 19.7 Run it

From the project folder (where `docker-compose.yml` is):

```bash
docker compose up --build        # build both images and start; first build takes 5–15 minutes
```

Open **http://localhost:8080** → register → analyze. Stop with `Ctrl + C`, or run in the background:

```bash
docker compose up --build -d     # -d = detached (background)
docker compose ps                # what is running
docker compose logs -f backend   # follow the backend's logs (Ctrl + C to stop following)
docker compose down              # stop and remove the containers (the history volume is kept)
docker compose down -v           # ... and delete the volume too (all accounts and history!)
```

After changing code, run `docker compose up --build` again — only changed layers rebuild.

Use your own trained `.pth` models: put them in `backend/weights/`; the volume mount makes them visible
without rebuilding. Override a setting: `HISTORY_ENABLED=false docker compose up`.

## 19.8 Everyday Docker commands

| Command                                             | Does                                                             |
| --------------------------------------------------- | ---------------------------------------------------------------- |
| `docker build -t pneumoscan-api ./backend`          | Build an image and name ("tag") it                               |
| `docker run -p 8000:8000 pneumoscan-api`            | Run a container from it                                          |
| `docker ps` / `docker ps -a`                        | Running / all containers                                         |
| `docker logs <container>`                           | Its output                                                       |
| `docker exec -it <container> sh`                    | Open a shell **inside** a running container (explore, debug)     |
| `docker stop <container>` / `docker rm <container>` | Stop / delete a container                                        |
| `docker images` / `docker rmi <image>`              | List / delete images                                             |
| `docker volume ls`                                  | List volumes                                                     |
| `docker system prune`                               | Delete unused containers, images and networks (frees disk space) |

## 19.9 Shipping containers to a server

1. Create a free Docker Hub account; `docker login`.
2. Tag and push: `docker build -t <you>/pneumoscan-api ./backend && docker push <you>/pneumoscan-api`.
3. On any Linux server with Docker (a cloud VM): `docker run -d -p 80:8000 <you>/pneumoscan-api`.

Many hosts can also build directly from a Dockerfile in your repository (Render's _Docker_ runtime, Fly.io,
Google Cloud Run). The full PyTorch image needs **more than 512 MB of RAM**, so on free tiers use the
ONNX-only setup of Chapter 20 instead.

## 19.10 Troubleshooting Docker

| Problem                               | Fix                                                                                                |
| ------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `Cannot connect to the Docker daemon` | Start Docker Desktop                                                                               |
| `port is already allocated`           | Something else uses 8000/8080 — change the left number in `ports` (e.g. `"8081:80"`)               |
| Build fails during `pip install`      | Check internet access; retry; Docker Desktop → Settings → Resources → give it more memory (≥ 4 GB) |
| Website loads, API calls fail         | `docker compose logs backend`; check `/api/health` at http://localhost:8000                        |
| Out of disk space                     | `docker system prune`                                                                              |

---

Next: **Chapter 20 — Hosting and re-hosting from scratch (free)** → [20-hosting-and-rehosting.md](20-hosting-and-rehosting.md)
