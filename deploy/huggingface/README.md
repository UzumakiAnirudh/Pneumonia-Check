---
title: PneumoScan AI API
emoji: 🫁
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# PneumoScan AI — API

FastAPI backend of [PneumoScan AI](https://github.com/UzumakiAnirudh/Pneumonia-Check): two-stage
pneumonia detection (DenseNet121 and Swin Transformer) with calibrated confidence and Grad-CAM.

**Decision support only — not a diagnosis.**

Health check: `/api/health`. The web app is served separately (Vercel) and forwards `/api/*` here.
