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
from typing import Optional, List, Dict, Any

from ml_worker.pipeline.pdf_parser import PDFParser
from ml_worker.pipeline.paddle_ocr_processor import NepaliOCR
from ml_worker.utils.docx_conversion import DocxLayoutBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def convert(self, pdf_path: str, output_path: Optional[str] = None) -> str:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(pdf_path)
        if output_path is None:
            output_path = os.path.splitext(pdf_path)[0] + ".docx"

        parser = PDFParser(pdf_path)
        try:
            pages = parser.extract_all_pages()
            engine = self._choose_engine(pages)
            logger.info("Converting %s using '%s' engine -> %s",
                        pdf_path, engine, output_path)
            if engine == "flow":
                self._convert_flow(pdf_path, output_path)
            else:
                self._convert_layout(parser, pages, output_path)
        finally:
            parser.close()

        return output_path

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
    def _convert_flow(pdf_path: str, output_path: str) -> None:
        from pdf2docx import Converter
        cv = Converter(pdf_path)
        try:
            cv.convert(output_path)
        finally:
            cv.close()


def convert_pdf_to_word(pdf_path: str, output_path: Optional[str] = None,
                        mode: str = "auto") -> str:
    """Convenience one-shot wrapper."""
    return PDFToWordConverter(mode=mode).convert(pdf_path, output_path)
