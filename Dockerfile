# syntax=docker/dockerfile:1
# =============================================================================
# PDFlow — single-image deploy (FastAPI API + built React SPA), CPU-only.
# Designed for a free Hugging Face Space (Docker SDK, port 7860).
# For a GPU deploy, swap the base to nvidia/cuda:12.x-runtime and use
# requirements.txt (GPU Paddle) instead of requirements.cpu.txt — see DEPLOY.md.
# =============================================================================

# ---- Stage 1: build the Vite SPA into frontend/dist ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---- Stage 2: Python runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/user \
    PYTHONPATH=/home/user/app

# System libraries: tesseract (pytesseract fallback OCR) + OpenCV/Paddle runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-nep tesseract-ocr-eng \
        libgl1 libglib2.0-0 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — Hugging Face Spaces runs the container as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Python deps: install the CPU build of PaddlePaddle from Paddle's own index
# FIRST (the 3.2.1 CPU wheel isn't on PyPI), so paddleocr/paddlex below find it
# already satisfied and don't drag in the GPU build.
COPY requirements.cpu.txt ./
RUN pip install paddlepaddle==3.2.1 \
        -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
    && pip install -r requirements.cpu.txt

# Application code + the prebuilt SPA (served by FastAPI at "/").
COPY backend/ ./backend/
COPY ml_worker/ ./ml_worker/
COPY web_run.py ./
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Writable dirs for the runtime user: job artifacts + the PaddleX model cache.
RUN mkdir -p storage/jobs /home/user/.paddlex \
    && chown -R user:user /home/user

USER user

# Pre-bake the PaddleOCR Nepali models into the image (built as the runtime user
# so the cache path matches at run time). Keeps the first request fast and means
# a Space restart on ephemeral disk never re-downloads.
RUN python -c "from ml_worker.pipeline.paddle_ocr_processor import NepaliOCR; NepaliOCR._get_engine('ne'); print('PaddleOCR models cached')"

# CORS default; lock this to the real origin via the PDFLOW_ALLOW_ORIGINS env in
# the Space settings for production. All other PDFLOW_* controls are opt-in too.
ENV PDFLOW_ALLOW_ORIGINS="*"

EXPOSE 7860
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
