# Deploying PDFlow

PDFlow ships as a **single Docker image**: it builds the React/Vite SPA, installs
a CPU-only Python stack, pre-bakes the PaddleOCR Nepali models, and serves both
the API and the SPA from FastAPI on **port 7860**.

The same image runs free on a CPU host now and on a GPU host later with only a
base-image / requirements swap — no application code changes (the device is
auto-detected by `backend/device.py`).

---

## 1. Deploy free on Hugging Face Spaces (CPU)

Free Spaces give 2 vCPU / 16 GB RAM with no request timeout — enough for the OCR
pipeline and its long jobs + SSE streams.

1. **Create the Space**: <https://huggingface.co/new-space>
   → SDK **Docker**, Hardware **CPU basic (free)**.
2. **Push this repo to the Space's git remote:**
   ```bash
   git remote add space https://huggingface.co/spaces/<user>/pdflow
   git push space webapp:main          # the Space builds from its `main` branch
   ```
   (Or connect the GitHub repo from the Space's settings instead of pushing.)
3. Hugging Face builds the `Dockerfile` and serves the app at
   `https://<user>-pdflow.hf.space`. The first build is slow (model pre-bake);
   later starts are fast.
4. **Harden for production** under *Space → Settings → Variables and secrets*
   (all are opt-in `PDFLOW_*` env vars read by `backend/security.py`):

   | Var | Why |
   |-----|-----|
   | `PDFLOW_API_KEYS` | Comma-separated keys gating `POST /api/convert` — stops anonymous CPU/GPU abuse. |
   | `PDFLOW_ALLOW_ORIGINS` | Lock CORS to `https://<user>-pdflow.hf.space` instead of `*`. |
   | `PDFLOW_MAX_PER_HOUR`, `PDFLOW_MAX_CONCURRENT`, `PDFLOW_MAX_PAGES` | Tighten limits on a shared free box. |

   The Space's config (title, port `7860`, Docker SDK) comes from the YAML
   front-matter at the top of `README.md`.

> **Note:** the free Space's disk is ephemeral across restarts. That's fine —
> job artifacts are temporary (TTL ~1h) and the OCR models are baked into the
> image, so nothing is re-downloaded.

---

## 2. Test locally first (Docker)

```bash
docker build -t pdflow .
docker run --rm -p 7860:7860 pdflow
```

Then open <http://localhost:7860> and check:

- `GET /api/health` → `{"status":"ok"}`
- `GET /api/device` → `"device":"cpu"`
- Upload a PDF (e.g. `tests/constitution.pdf`), watch the live progress
  timeline complete, and download the `.docx`.

---

## 3. Move to GPU later (no app changes)

OCR on CPU is correct but slow (a few seconds per page). To go fast, deploy the
same app on a GPU host:

- **Keep `requirements.txt`** (the GPU set: `paddlepaddle-gpu` + CUDA wheels).
- **Switch the Dockerfile base** to a CUDA runtime image, e.g.
  `nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04` (install Python in it), drop the
  separate CPU-Paddle step, and `pip install -r requirements.txt`.
- **Deploy to** any of: Hugging Face Spaces GPU hardware (one-toggle paid
  upgrade — no Dockerfile change needed if you keep CPU Paddle, but you won't get
  GPU speed without the GPU build), Fly.io GPU machines, Modal, RunPod, or a
  cloud VM with an NVIDIA GPU.

`backend/device.py` detects the CUDA device automatically and the UI badge flips
to **GPU** — nothing else changes.

---

## Files involved

| File | Role |
|------|------|
| `Dockerfile` | Multi-stage build (Node SPA build → Python runtime), model pre-bake, runs on `:7860`. |
| `requirements.cpu.txt` | Slim CPU-only deps (no CUDA/torch/Jupyter). Used by the Dockerfile. |
| `requirements.txt` | Full GPU/dev reference set — used only for the GPU path. |
| `.dockerignore` | Keeps the build context small. |
| `README.md` (front-matter) | Hugging Face Space configuration. |
