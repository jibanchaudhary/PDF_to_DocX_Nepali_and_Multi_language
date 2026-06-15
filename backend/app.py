"""PDFlow web API.

Endpoints
---------
POST /api/convert            upload a PDF, start a conversion job
GET  /api/jobs/{id}          current job status + analysis (poll/fallback)
GET  /api/jobs/{id}/events   Server-Sent Events stream of live progress
GET  /api/jobs/{id}/result   download the generated .docx (attachment)
GET  /api/jobs/{id}/docx     the generated .docx (inline, for in-browser preview)
GET  /api/jobs/{id}/pages/*  rendered original-PDF page PNGs (the "before" view)
GET  /api/jobs/{id}/img/*    extracted layout image assets (structure view)
GET  /api/health             liveness probe

Run from the project root:
    uvicorn backend.app:app --reload
"""

from __future__ import annotations

import os
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .jobs import registry, Job
from .service import run_conversion
from .device import get_device_info, warm as warm_device
from .security import (auth_identity, rate_limiter, ALLOW_ORIGINS,
                       MAX_UPLOAD_BYTES, JOB_TTL_SEC)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdflow.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Detect the inference device off the request path so /api/device is instant.
    threading.Thread(target=warm_device, name="pdflow-device", daemon=True).start()
    if JOB_TTL_SEC:
        threading.Thread(target=_reaper_loop, name="pdflow-reaper",
                         daemon=True).start()
    yield


app = FastAPI(title="PDFlow API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# A small pool: conversions (especially OCR) are heavy, so don't over-subscribe.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdflow-conv")


def _reaper_loop() -> None:
    interval = max(60, min(JOB_TTL_SEC, 300))
    while True:
        time.sleep(interval)
        try:
            n = registry.reap(JOB_TTL_SEC)
            if n:
                logger.info("Reaped %d expired job(s)", n)
        except Exception:  # noqa: BLE001 - never let the reaper die
            logger.exception("job reaper error")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "pdflow"}


@app.get("/api/device")
def device():
    """Whether OCR inference runs on GPU or falls back to CPU."""
    return get_device_info()


@app.post("/api/convert")
async def convert(file: UploadFile = File(...), mode: str = Form("auto"),
                  pages: str = Form(""),
                  identity: str = Depends(auth_identity)):
    if mode not in ("auto", "layout", "flow"):
        raise HTTPException(400, "mode must be auto, layout or flow")
    name = file.filename or "document.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a .pdf file")

    pages_spec = (pages or "").strip() or None
    job = registry.create(filename=name, mode=mode)
    try:
        size = 0
        head = b""
        with open(job.input_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                if len(head) < 1024:
                    head += chunk[:1024 - len(head)]
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "File exceeds the upload size limit")
                out.write(chunk)
        await file.close()

        if size == 0:
            raise HTTPException(400, "Uploaded file is empty")
        # Don't trust the extension: feed only real PDFs to the native parsers.
        if b"%PDF-" not in head:
            raise HTTPException(400, "This file is not a valid PDF.")

        # Hold a concurrency slot for the job's lifetime; the worker releases it.
        rate_limiter.acquire_slot(identity)
    except HTTPException:
        registry.remove(job.id)
        raise

    def _run_and_release() -> None:
        try:
            run_conversion(job, mode, pages_spec)
        finally:
            rate_limiter.release_slot(identity)

    _executor.submit(_run_and_release)
    logger.info("Queued job %s (%s, %.1f KB, mode=%s, pages=%s)", job.id, name,
                size / 1024, mode, pages_spec or "all")
    return JSONResponse(job.to_dict(), status_code=202)


def _require_job(job_id: str) -> Job:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return _require_job(job_id).to_dict()


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = _require_job(job_id)

    def stream():
        # Late joiner (job already finished): replay the full history once.
        if job.status in ("done", "error"):
            for ev in list(job.events):
                yield f"data: {json.dumps(ev)}\n\n"
            return
        # Live listener: the per-job queue is still unconsumed and holds every
        # event from the start, so draining it alone delivers the whole timeline
        # in order — no separate replay (which would duplicate early events).
        for ev in job.drain(timeout=1.0):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str):
    job = _require_job(job_id)
    if not os.path.exists(job.output_path):
        raise HTTPException(409, "Conversion not finished")
    download = os.path.splitext(job.filename)[0] + ".docx"
    return FileResponse(
        job.output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=download,
    )


@app.get("/api/jobs/{job_id}/docx")
def job_docx(job_id: str):
    job = _require_job(job_id)
    if not os.path.exists(job.output_path):
        raise HTTPException(409, "Conversion not finished")
    return FileResponse(
        job.output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/jobs/{job_id}/pages/{name}")
def job_page(job_id: str, name: str):
    job = _require_job(job_id)
    path = os.path.join(job.pages_dir, os.path.basename(name))
    if not os.path.exists(path):
        raise HTTPException(404, "Page not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/jobs/{job_id}/img/{name}")
def job_img(job_id: str, name: str):
    job = _require_job(job_id)
    path = os.path.join(job.img_dir, os.path.basename(name))
    if not os.path.exists(path):
        raise HTTPException(404, "Asset not found")
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# Serve the built frontend (production). During development the Vite dev server
# proxies /api to this app, so this block is simply skipped when dist is absent.
# --------------------------------------------------------------------------- #
_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
