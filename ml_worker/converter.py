"""
PDF -> Word converter orchestrator.

Two engines, chosen automatically:

* ``layout`` -- our OCR-aware, position-preserving rebuild. Used whenever the PDF
  contains Nepali text that cannot be decoded from its embedded font, or pages
  that are scanned images. This is what makes Nepali output editable.
* ``flow``   -- delegates to the ``pdf2docx`` library, which produces clean,
  reflowable Word output (paragraphs, native tables, images) for ordinary
  digital PDFs whose text extracts correctly.

Use :meth:`PDFToWordConverter.convert` for a single call.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, List, Dict, Any, Union, Iterable

from ml_worker.pipeline.pdf_parser import PDFParser
from ml_worker.pipeline.paddle_ocr_processor import NepaliOCR
from ml_worker.utils.docx_conversion import DocxLayoutBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# A page selection may be given as ``None`` (all pages), a human spec string
# (1-based, e.g. ``"1-5"``, ``"2,4,6"``, ``"3-"``) or an iterable of 0-based
# page indices.
PageSelection = Union[None, str, Iterable[int]]


def parse_page_spec(spec: Optional[str], total: int) -> Optional[List[int]]:
    """Turn a 1-based page-range string into sorted, unique 0-based indices.

    Supports comma-separated parts, each either a single page (``"3"``) or a
    range (``"1-5"``, ``"3-"`` for "3 to end", ``"-4"`` for "start to 4").
    Returns ``None`` for an empty/blank spec (meaning "all pages"). Pages
    outside ``1..total`` are clamped away; an all-out-of-range spec yields ``[]``.

    Raises:
        ValueError: if the spec contains a non-numeric token.
    """
    if spec is None:
        return None
    spec = spec.strip()
    if not spec:
        return None

    indices: set[int] = set()
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a, _, b = part.partition("-")
                start = int(a) if a.strip() else 1
                end = int(b) if b.strip() else total
                if start > end:
                    start, end = end, start
                for p in range(start, end + 1):
                    if 1 <= p <= total:
                        indices.add(p - 1)
            else:
                p = int(part)
                if 1 <= p <= total:
                    indices.add(p - 1)
        except ValueError as exc:
            raise ValueError(f"Invalid page selection: {raw!r}") from exc
    return sorted(indices)


class PDFToWordConverter:
    """Convert a PDF to an editable .docx, specialised for Nepali documents."""

    def __init__(self, mode: str = "auto", lang: str = "ne",
                 min_confidence: float = 0.5, zoom: float = 4.0):
        """
        Args:
            mode: ``auto`` (default), ``layout`` (force OCR rebuild) or
                ``flow`` (force pdf2docx).
            lang: PaddleOCR language code (``ne`` for Nepali/Devanagari).
            min_confidence: discard OCR results below this score.
            zoom: render scale used when rasterising regions/pages for OCR.
        """
        if mode not in ("auto", "layout", "flow"):
            raise ValueError("mode must be one of 'auto', 'layout', 'flow'")
        self.mode = mode
        self.lang = lang
        self.min_confidence = min_confidence
        self.zoom = zoom

    def convert(self, pdf_path: str, output_path: Optional[str] = None,
                pages: PageSelection = None) -> str:
        """Convert ``pdf_path`` to ``output_path``.

        Args:
            pages: optional page selection — ``None`` (all pages), a 1-based
                spec string (``"1-5"``, ``"2,4,6"``, ``"3-"``) or an iterable of
                0-based indices. Only the selected pages are parsed, OCR'd and
                written, so processing a slice of a large PDF is much faster.
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(pdf_path)
        if output_path is None:
            output_path = os.path.splitext(pdf_path)[0] + ".docx"

        parser = PDFParser(pdf_path)
        try:
            indices = self._resolve_pages(pages, len(parser.doc))
            page_data = parser.extract_all_pages(pages=indices)
            engine = self._choose_engine(page_data)
            logger.info("Converting %s using '%s' engine (%s page(s)) -> %s",
                        pdf_path, engine, len(page_data), output_path)
            if engine == "flow":
                self._convert_flow(pdf_path, output_path, pages=indices)
            else:
                self._convert_layout(parser, page_data, output_path)
        finally:
            parser.close()

        return output_path

    @staticmethod
    def _resolve_pages(pages: PageSelection, total: int) -> Optional[List[int]]:
        """Normalise any accepted page selection to 0-based indices (or None)."""
        if pages is None:
            return None
        if isinstance(pages, str):
            return parse_page_spec(pages, total)
        seen = set()
        out: List[int] = []
        for i in pages:
            i = int(i)
            if 0 <= i < total and i not in seen:
                seen.add(i)
                out.append(i)
        return out

    def _choose_engine(self, pages: List[Dict[str, Any]]) -> str:
        if self.mode != "auto":
            return self.mode
        return "layout" if self._needs_ocr(pages) else "flow"

    @staticmethod
    def _needs_ocr(pages: List[Dict[str, Any]]) -> bool:
        for page in pages:
            if page.get("is_scanned"):
                return True
            if any(e["type"] == "text" and e.get("needs_ocr") for e in page["elements"]):
                return True
        return False

    def _convert_layout(self, parser: PDFParser, pages: List[Dict[str, Any]],
                        output_path: str) -> None:
        ocr = NepaliOCR(lang=self.lang, min_confidence=self.min_confidence, zoom=self.zoom)
        ocr.enrich_pages(parser.doc, pages)
        builder = DocxLayoutBuilder()
        builder.add_pages(pages)
        builder.save(output_path)

    @staticmethod
    def _convert_flow(pdf_path: str, output_path: str,
                      pages: Optional[List[int]] = None) -> None:
        from pdf2docx import Converter
        cv = Converter(pdf_path)
        try:
            # pdf2docx accepts a list of 0-based page indices via ``pages``.
            if pages is not None:
                cv.convert(output_path, pages=pages)
            else:
                cv.convert(output_path)
        finally:
            cv.close()


def convert_pdf_to_word(pdf_path: str, output_path: Optional[str] = None,
                        mode: str = "auto", pages: PageSelection = None) -> str:
    """Convenience one-shot wrapper."""
    return PDFToWordConverter(mode=mode).convert(pdf_path, output_path, pages=pages)
