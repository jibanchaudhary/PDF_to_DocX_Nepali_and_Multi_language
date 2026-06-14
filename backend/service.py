"""Instrumented conversion pipeline for the web backend.

This mirrors :class:`ml_worker.converter.PDFToWordConverter` but drives the
pipeline stage-by-stage so we can (a) stream granular progress to the browser
and (b) collect a rich analysis payload (engine reasoning, per-page structure,
OCR-recovered Unicode spans and confidence) used to power the result views.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from ml_worker.pipeline.pdf_parser import PDFParser
from ml_worker.pipeline.paddle_ocr_processor import NepaliOCR
from ml_worker.utils.docx_conversion import DocxLayoutBuilder
from ml_worker.converter import parse_page_spec

from .jobs import Job
from .device import get_device_info

logger = logging.getLogger("pdflow.service")

PREVIEW_ZOOM = 2.0  # render scale for the original-PDF page preview images


def run_conversion(job: Job, mode: str = "auto", pages_spec: Optional[str] = None,
                   lang: str = "ne", zoom: float = 4.0) -> None:
    """Run the full conversion for ``job`` and populate its analysis.

    Args:
        pages_spec: optional 1-based page selection string (``"1-5"``,
            ``"2,4,6"``, ``"3-"``). When given, only those pages are parsed,
            rendered, OCR'd and built — the rest of the PDF is skipped entirely.

    Designed to be executed in a worker thread. All failures are routed to
    :meth:`Job.fail` so the SSE stream always terminates cleanly.
    """
    started = time.time()
    parser: Optional[PDFParser] = None
    try:
        job.emit("uploaded", "File received", 0.04)

        parser = PDFParser(job.input_path)
        total_pages = len(parser.doc)

        try:
            indices = parse_page_spec(pages_spec, total_pages)
        except ValueError as exc:
            job.fail(str(exc))
            return
        if indices is not None and not indices:
            job.fail(f"Page selection “{pages_spec}” matches no pages — "
                     f"this PDF has {total_pages} page(s).")
            return

        sel_msg = (f"selected {len(indices)} of {total_pages}"
                   if indices is not None else f"all {total_pages}")
        job.emit("parsing",
                 f"Reading PDF structure with PyMuPDF ({sel_msg} page(s))", 0.12)
        pages = parser.extract_all_pages(pages=indices)

        # Render only the selected original pages so the comparison view can show
        # the "before" immediately while heavier OCR work continues.
        _render_pdf_previews(parser.doc, job, pages)
        job.emit("parsing",
                 f"Parsed {len(pages)} page(s), {_count_spans(pages)} text spans",
                 0.22, extra={"page_count": len(pages)})

        engine = _choose_engine(pages, mode)
        reason = _engine_reason(pages, engine, mode)
        job.emit("routing", f"Routed to the “{engine}” engine", 0.30,
                 extra={"engine": engine, "engine_reason": reason})

        if engine == "flow":
            job.emit("building",
                     "Reflowing to Word via pdf2docx (clean digital PDF)", 0.55)
            _convert_flow(job.input_path, job.output_path, pages=indices)
            job.emit("building", "Word document assembled", 0.92)
        else:
            ocr = NepaliOCR(lang=lang, min_confidence=0.5, zoom=zoom)
            total = len(pages) or 1
            for i, page_info in enumerate(pages):
                frac = 0.32 + 0.50 * (i / total)
                job.emit("ocr",
                         f"OCR recovering Devanagari — page {i + 1}/{total}",
                         frac, extra={"page": i + 1, "page_count": total})
                # enrich_pages iterates a list; feed one page for live progress.
                ocr.enrich_pages(parser.doc, [page_info])
            job.emit("building", "Rebuilding layout as editable text boxes", 0.86)
            builder = DocxLayoutBuilder()
            builder.add_pages(pages)
            builder.save(job.output_path)
            job.emit("building", "Word document assembled", 0.93)

        # Persist layout images referenced by the structure view.
        _export_layout_images(pages, job)

        analysis = _build_analysis(job, pages, engine, reason, mode,
                                   duration=time.time() - started,
                                   total_pages=total_pages)
        job.emit("done", "Conversion complete", 1.0)
        job.finish(analysis)
        logger.info("Job %s done in %.1fs (engine=%s)", job.id,
                    time.time() - started, engine)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        logger.exception("Job %s failed", job.id)
        job.fail(str(exc) or exc.__class__.__name__)
    finally:
        if parser is not None:
            parser.close()


# --------------------------------------------------------------------------- #
# Engine routing (mirrors ml_worker.converter, with human-readable reasons)
# --------------------------------------------------------------------------- #
def _choose_engine(pages: List[Dict[str, Any]], mode: str) -> str:
    if mode != "auto":
        return mode
    return "layout" if _needs_ocr(pages) else "flow"


def _needs_ocr(pages: List[Dict[str, Any]]) -> bool:
    for page in pages:
        if page.get("is_scanned"):
            return True
        if any(e["type"] == "text" and e.get("needs_ocr") for e in page["elements"]):
            return True
    return False


def _engine_reason(pages: List[Dict[str, Any]], engine: str, mode: str) -> str:
    if mode != "auto":
        return f"Engine was manually forced to “{mode}”."
    scanned = sum(1 for p in pages if p.get("is_scanned"))
    legacy = sum(
        1 for p in pages
        for e in p["elements"]
        if e["type"] == "text" and e.get("needs_ocr")
    )
    if engine == "layout":
        bits = []
        if scanned:
            bits.append(f"{scanned} scanned page(s)")
        if legacy:
            bits.append(f"{legacy} undecodable legacy-font span(s)")
        detail = " and ".join(bits) if bits else "image-based Nepali content"
        return (f"Detected {detail}, so PDFlow rebuilt the document with the "
                f"layout engine — OCR recovers real Unicode Devanagari and every "
                f"element is repositioned as an editable text box.")
    return ("Every page has a clean, decodable text layer, so PDFlow used the "
            "fast flow engine (pdf2docx) for reflowable paragraphs and native "
            "Word tables.")


def _convert_flow(pdf_path: str, output_path: str,
                  pages: Optional[List[int]] = None) -> None:
    from pdf2docx import Converter
    cv = Converter(pdf_path)
    try:
        if pages is not None:
            cv.convert(output_path, pages=pages)
        else:
            cv.convert(output_path)
    finally:
        cv.close()


# --------------------------------------------------------------------------- #
# Preview rendering
# --------------------------------------------------------------------------- #
def _render_pdf_previews(doc: "fitz.Document", job: Job,
                         pages: List[Dict[str, Any]]) -> None:
    """Rasterise each *selected* original page to a PNG for the 'before' view.

    Named by the real 1-based page number so previews line up with the analysis
    even when only a subset of the document was parsed.
    """
    mat = fitz.Matrix(PREVIEW_ZOOM, PREVIEW_ZOOM)
    for page_info in pages:
        idx = page_info["page_index"]
        num = page_info["page_number"]
        try:
            pix = doc[idx].get_pixmap(matrix=mat, alpha=False)
            pix.save(os.path.join(job.pages_dir, f"page-{num}.png"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("preview render failed page %d: %s", num, exc)


def _export_layout_images(pages: List[Dict[str, Any]], job: Job) -> None:
    """Write the (possibly OCR-masked) image bytes of every surviving image
    element so the structure view can position them precisely."""
    for page_info in pages:
        pnum = page_info["page_number"]
        for idx, el in enumerate(page_info["elements"]):
            if el.get("type") != "image" or el.get("replaced"):
                continue
            data = el.get("image_data")
            if not data:
                continue
            ext = (el.get("ext") or "png").lower()
            if ext == "jpx":
                ext = "png"
            fname = f"p{pnum}-{idx}.{ext}"
            try:
                with open(os.path.join(job.img_dir, fname), "wb") as fh:
                    fh.write(data)
                el["_asset"] = fname
            except Exception as exc:  # noqa: BLE001
                logger.warning("image export failed %s: %s", fname, exc)


# --------------------------------------------------------------------------- #
# Analysis payload
# --------------------------------------------------------------------------- #
def _count_spans(pages: List[Dict[str, Any]]) -> int:
    return sum(1 for p in pages for e in p["elements"]
               if e["type"] == "text" and e.get("text", "").strip())


def _norm(bbox: List[float], w: float, h: float) -> List[float]:
    w = w or 1.0
    h = h or 1.0
    return [round(bbox[0] / w, 5), round(bbox[1] / h, 5),
            round(bbox[2] / w, 5), round(bbox[3] / h, 5)]


def _format_page_range(numbers: List[int]) -> str:
    """Collapse a sorted list of 1-based page numbers into a compact label,
    e.g. [2,3,4,7] -> '2–4, 7'."""
    if not numbers:
        return ""
    parts: List[str] = []
    start = prev = numbers[0]
    for n in numbers[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(f"{start}–{prev}" if start != prev else f"{start}")
        start = prev = n
    parts.append(f"{start}–{prev}" if start != prev else f"{start}")
    return ", ".join(parts)


def _build_analysis(job: Job, pages: List[Dict[str, Any]], engine: str,
                    reason: str, mode: str, duration: float,
                    total_pages: int) -> Dict[str, Any]:
    pages_out: List[Dict[str, Any]] = []
    recovered: List[Dict[str, Any]] = []
    scores: List[float] = []
    total_text = 0
    total_images = 0
    total_tables = 0
    recovered_chars = 0
    images_recovered = 0
    scanned_pages = 0

    for page_info in pages:
        w = page_info["width"]
        h = page_info["height"]
        pnum = page_info["page_number"]
        if page_info.get("is_scanned"):
            scanned_pages += 1

        elements_out: List[Dict[str, Any]] = []
        n_text = n_img = 0
        for el in page_info["elements"]:
            if el.get("type") == "text":
                text = (el.get("text") or "").strip()
                if not text:
                    continue
                n_text += 1
                total_text += 1
                is_ocr = bool(el.get("ocr"))
                score = el.get("ocr_score")
                elements_out.append({
                    "type": "text",
                    "bbox": _norm(el["bbox"], w, h),
                    "text": text,
                    "ocr": is_ocr,
                    "score": round(score, 4) if isinstance(score, (int, float)) else None,
                    "source": el.get("ocr_source"),
                    "bold": bool(el.get("bold")),
                    "italic": bool(el.get("italic")),
                    "color": el.get("color", "#000000"),
                    "size": round((el.get("font_size", 10.0) / (h or 1)), 5),
                })
                if is_ocr:
                    recovered_chars += len(text)
                    if isinstance(score, (int, float)):
                        scores.append(score)
                    recovered.append({
                        "page": pnum,
                        "text": text,
                        "score": round(score, 4) if isinstance(score, (int, float)) else None,
                        "source": el.get("ocr_source") or "ocr",
                        "bbox": _norm(el["bbox"], w, h),
                    })
            elif el.get("type") == "image" and not el.get("replaced"):
                n_img += 1
                total_images += 1
                asset = el.get("_asset")
                elements_out.append({
                    "type": "image",
                    "bbox": _norm(el["bbox"], w, h),
                    "src": (f"/api/jobs/{job.id}/img/{asset}" if asset else None),
                })
                if el.get("ext") == "png" and engine == "layout":
                    # masked-and-recovered "mixed" image
                    images_recovered += 1

        tables_out = []
        for tbl in page_info.get("tables", []):
            total_tables += 1
            tables_out.append({
                "bbox": _norm(tbl["bbox"], w, h),
                "rows": tbl.get("rows"),
                "cols": tbl.get("cols"),
                "cells": tbl.get("cells"),
            })

        pages_out.append({
            "number": pnum,
            "width": w,
            "height": h,
            "is_scanned": bool(page_info.get("is_scanned")),
            "n_text": n_text,
            "n_images": n_img,
            "n_tables": len(tables_out),
            "preview": f"/api/jobs/{job.id}/pages/page-{pnum}.png",
            "elements": elements_out,
            "tables": tables_out,
        })

    avg_conf = round(sum(scores) / len(scores), 4) if scores else None
    low_conf = sum(1 for s in scores if s < 0.85)
    out_size = (os.path.getsize(job.output_path)
                if os.path.exists(job.output_path) else 0)

    page_numbers = [p["number"] for p in pages_out]
    partial = len(page_numbers) < total_pages

    return {
        "engine": engine,
        "engine_reason": reason,
        "mode": mode,
        "filename": job.filename,
        "page_count": len(pages),
        "total_pages": total_pages,
        "partial": partial,
        "page_range": _format_page_range(page_numbers) if partial else "all",
        "device": get_device_info(),
        "duration_sec": round(duration, 2),
        "output_size": out_size,
        "input_size": (os.path.getsize(job.input_path)
                       if os.path.exists(job.input_path) else 0),
        "quality": {
            "ocr_spans": len(recovered),
            "avg_confidence": avg_conf,
            "low_conf_spans": low_conf,
            "recovered_chars": recovered_chars,
            "images_recovered": images_recovered,
            "scanned_pages": scanned_pages,
            "total_text_spans": total_text,
            "total_images": total_images,
            "total_tables": total_tables,
        },
        "pages": pages_out,
        "recovered": recovered,
    }
