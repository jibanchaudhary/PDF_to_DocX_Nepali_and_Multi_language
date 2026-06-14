"""Inference device detection.

Reports whether OCR inference (PaddleOCR / PaddlePaddle) will run on a CUDA GPU
or fall back to CPU. PaddleOCR uses Paddle's default device, so the truthful
signal is "Paddle is a CUDA build *and* at least one CUDA device is visible".

Importing Paddle is slow, so the result is computed once and cached; call
:func:`warm` at startup (in a thread) so the first request to ``/api/device`` is
instant.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("pdflow.device")

_lock = threading.Lock()
_cache: Optional[Dict[str, Any]] = None


def get_device_info() -> Dict[str, Any]:
    """Return cached device info, detecting it on first call.

    Shape::

        {"device": "gpu"|"cpu", "cuda": bool, "count": int,
         "name": str|None, "backend": str|None, "detail": str}
    """
    global _cache
    with _lock:
        if _cache is None:
            _cache = _detect()
            logger.info("Inference device: %s (%s)",
                        _cache["device"].upper(), _cache["detail"])
        return _cache


def warm() -> None:
    """Compute the device info ahead of time, off the request path."""
    try:
        get_device_info()
    except Exception:  # noqa: BLE001 - never let warming crash startup
        logger.exception("device warm-up failed")


def _detect() -> Dict[str, Any]:
    try:
        import paddle  # heavy import; only happens once
    except Exception as exc:  # noqa: BLE001
        return {
            "device": "cpu", "cuda": False, "count": 0, "name": None,
            "backend": None, "detail": f"paddle unavailable ({exc.__class__.__name__})",
        }

    try:
        compiled = bool(paddle.is_compiled_with_cuda())
    except Exception:  # noqa: BLE001
        compiled = False

    count = 0
    name: Optional[str] = None
    if compiled:
        try:
            count = int(paddle.device.cuda.device_count())
        except Exception:  # noqa: BLE001
            count = 0
        if count > 0:
            try:
                name = paddle.device.cuda.get_device_properties(0).name
            except Exception:  # noqa: BLE001
                name = None

    if compiled and count > 0:
        return {
            "device": "gpu", "cuda": True, "count": count, "name": name,
            "backend": "paddlepaddle",
            "detail": f"CUDA GPU ×{count}" + (f" · {name}" if name else ""),
        }

    detail = ("GPU build, but no CUDA device is visible — running on CPU"
              if compiled else "CPU-only Paddle build")
    return {
        "device": "cpu", "cuda": False, "count": 0, "name": None,
        "backend": "paddlepaddle", "detail": detail,
    }
