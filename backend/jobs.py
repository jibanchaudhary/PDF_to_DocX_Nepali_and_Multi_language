"""In-memory job registry with a thread-safe progress event stream.

A :class:`Job` owns its own working directory under ``storage/jobs/<id>`` and a
queue of progress events that the conversion worker (running in a thread) pushes
to and the SSE endpoint drains. Everything here is deliberately lightweight: a
single-process FastAPI app driving a handful of conversions at a time.
"""

from __future__ import annotations

import os
import time
import shutil
import secrets
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# All job artifacts live under <project>/storage/jobs/<id>/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_ROOT = os.path.join(_PROJECT_ROOT, "storage", "jobs")


# Ordered pipeline stages, used by the UI to render the progress timeline.
STAGES = [
    {"key": "uploaded", "label": "Uploaded"},
    {"key": "parsing", "label": "Parsing"},
    {"key": "routing", "label": "Routing"},
    {"key": "ocr", "label": "OCR recovery"},
    {"key": "building", "label": "Building DOCX"},
    {"key": "done", "label": "Done"},
]


@dataclass
class Job:
    id: str
    filename: str
    mode: str = "auto"
    status: str = "queued"          # queued | running | done | error
    stage: str = "uploaded"
    progress: float = 0.0           # 0..1
    message: str = ""
    error: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    events: List[Dict[str, Any]] = field(default_factory=list)
    _queue: "queue.Queue" = field(default_factory=queue.Queue, repr=False)

    @property
    def dir(self) -> str:
        return os.path.join(STORAGE_ROOT, self.id)

    @property
    def input_path(self) -> str:
        return os.path.join(self.dir, "input.pdf")

    @property
    def output_path(self) -> str:
        return os.path.join(self.dir, "output.docx")

    @property
    def pages_dir(self) -> str:
        return os.path.join(self.dir, "pages")

    @property
    def img_dir(self) -> str:
        return os.path.join(self.dir, "img")

    # -- progress ---------------------------------------------------------- #
    def emit(self, stage: str, message: str, progress: float,
             extra: Optional[Dict[str, Any]] = None) -> None:
        """Record a progress event and push it to the SSE queue."""
        self.stage = stage
        self.message = message
        self.progress = max(0.0, min(1.0, progress))
        if stage in ("done",):
            self.status = "done"
        elif self.status == "queued":
            self.status = "running"
        event = {
            "type": "progress",
            "stage": stage,
            "message": message,
            "progress": self.progress,
            "status": self.status,
            "t": round(time.time() - self.created_at, 2),
        }
        if extra:
            event.update(extra)
        self.events.append(event)
        self._queue.put(event)

    def fail(self, message: str) -> None:
        self.status = "error"
        self.error = message
        event = {"type": "error", "status": "error", "message": message,
                 "stage": self.stage, "progress": self.progress}
        self.events.append(event)
        self._queue.put(event)

    def finish(self, analysis: Dict[str, Any]) -> None:
        self.analysis = analysis
        self.status = "done"
        event = {"type": "done", "status": "done", "stage": "done",
                 "progress": 1.0, "analysis": analysis}
        self.events.append(event)
        self._queue.put(event)
        self._queue.put(None)  # sentinel: closes the SSE stream

    def drain(self, timeout: float = 1.0):
        """Yield queued events; blocks up to ``timeout`` per item. Returns when
        the sentinel (None) is seen."""
        while True:
            try:
                item = self._queue.get(timeout=timeout)
            except queue.Empty:
                yield {"type": "ping"}
                continue
            if item is None:
                return
            yield item

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "mode": self.mode,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "analysis": self.analysis,
            "stages": STAGES,
        }


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        os.makedirs(STORAGE_ROOT, exist_ok=True)

    def create(self, filename: str, mode: str = "auto") -> Job:
        # A high-entropy id: the job URL itself is the read capability, so it
        # must not be guessable. ~192 bits, URL-safe (valid as a path segment).
        job_id = secrets.token_urlsafe(24)
        job = Job(id=job_id, filename=filename, mode=mode)
        os.makedirs(job.pages_dir, exist_ok=True)
        os.makedirs(job.img_dir, exist_ok=True)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def remove(self, job_id: str) -> None:
        """Drop a job from the registry and delete its working directory."""
        with self._lock:
            self._jobs.pop(job_id, None)
        shutil.rmtree(os.path.join(STORAGE_ROOT, job_id), ignore_errors=True)

    def reap(self, ttl: float) -> int:
        """Evict jobs (and their files) older than ``ttl`` seconds.

        Bounds both the in-memory registry and on-disk ``storage/jobs`` so an
        unauthenticated stream of uploads cannot grow them without limit.
        """
        if ttl <= 0:
            return 0
        cutoff = time.time() - ttl
        with self._lock:
            stale = [jid for jid, j in self._jobs.items() if j.created_at < cutoff]
            for jid in stale:
                self._jobs.pop(jid, None)
        for jid in stale:
            shutil.rmtree(os.path.join(STORAGE_ROOT, jid), ignore_errors=True)
        return len(stale)


registry = JobRegistry()
