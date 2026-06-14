"""
PDF parsing and element extraction.

Reads a PDF with PyMuPDF (fitz) and turns every page into a structured list of
positioned elements (text spans, images, tables). Crucially for Nepali PDFs it
flags text spans whose embedded font cannot be decoded to Unicode (legacy/CID
fonts such as subset-embedded Mangal or Preeti) so a later OCR stage can recover
real, editable Devanagari from the rendered glyphs.
"""

import fitz
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Devanagari Unicode block.
DEVANAGARI_RANGE = ("ऀ", "ॿ")

# Font name fragments that indicate a Devanagari / Nepali typeface. When such a
# font is used but the extracted text contains no Devanagari codepoints, the text
# layer is broken (legacy 8-bit or undecodable CID encoding) and needs OCR.
DEVANAGARI_FONT_HINTS = (
    "mangal", "preeti", "kantipur", "devanagari", "himalaya", "kalimati",
    "sagarmatha", "aakar", "ganesh", "fontasy", "pcs nepali", "kanti",
    "ananda", "navjeevan", "shangrila",
)

# Fonts whose glyphs are icons / math symbols rather than recoverable text.
NON_TEXT_FONT_HINTS = (
    "wingding", "webding", "symbol", "dingbat", "zapf",
    # TeX / LaTeX math families (Computer Modern math, AMS, etc.)
    "cmex", "cmsy", "cmmi", "cmbsy", "msam", "msbm", "esint", "stmary",
    "rsfs", "wasy", "mathjax",
)


class PDFParser:
    """Parse a PDF into positioned, OCR-aware elements."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page_data: List[Dict[str, Any]] = []

    def close(self):
        try:
            self.doc.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def extract_all_pages(self) -> List[Dict[str, Any]]:
        logger.info("Extracting %d page(s) from %s", len(self.doc), self.pdf_path)
        self.page_data = [self.extract_page(i) for i in range(len(self.doc))]
        return self.page_data

    def extract_page(self, page_num: int) -> Dict[str, Any]:
        page = self.doc[page_num]
        page_info: Dict[str, Any] = {
            "page_number": page_num + 1,
            "page_index": page_num,
            "width": page.rect.width,
            "height": page.rect.height,
            "rotation": page.rotation,
            "elements": [],
        }

        self._extract_text(page, page_info)
        self._extract_images(page, page_info)
        page_info["tables"] = self._detect_tables(page)
        page_info["is_scanned"] = self._is_scanned(page_info)
        return page_info

    # ------------------------------------------------------------------ #
    # Text
    # ------------------------------------------------------------------ #
    def _extract_text(self, page, page_info: Dict[str, Any]) -> None:
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:  # 0 == text block
                continue
            for line in block.get("lines", []):
                line_dir = line.get("dir", (1.0, 0.0))
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    font = span.get("font", "")
                    element = {
                        "type": "text",
                        "bbox": list(span["bbox"]),
                        "text": text,
                        "font": font,
                        "font_size": span.get("size", 10.0),
                        "color": self._rgb_to_hex(span.get("color", 0)),
                        "flags": span.get("flags", 0),
                        "bold": self._is_bold(span),
                        "italic": bool(span.get("flags", 0) & 2 ** 1),
                        "dir": line_dir,
                        "needs_ocr": self._span_needs_ocr(text, font),
                    }
                    page_info["elements"].append(element)

    @staticmethod
    def _is_bold(span: Dict[str, Any]) -> bool:
        if span.get("flags", 0) & 2 ** 4:
            return True
        return "bold" in span.get("font", "").lower()

    @staticmethod
    def _span_needs_ocr(text: str, font: str) -> bool:
        """Decide whether a span's extracted text is unreliable.

        True when the glyphs render fine on screen but the extracted code points
        are garbage -- the classic Nepali legacy/CID-font problem. Such spans are
        re-read from the rendered page by the OCR stage. The check is deliberately
        precise so that ordinary Latin text and symbol glyphs (Wingdings, Symbol)
        are never sent through OCR.
        """
        stripped = text.strip()
        if not stripped:
            return False

        has_devanagari = any(DEVANAGARI_RANGE[0] <= c <= DEVANAGARI_RANGE[1] for c in text)
        if has_devanagari:
            return False  # already proper Unicode Nepali

        font_lc = font.lower()

        # Symbol / dingbat / math fonts deliberately use icon glyphs that map to
        # control or private-use code points; OCR cannot (and should not) help.
        if any(s in font_lc for s in NON_TEXT_FONT_HINTS):
            return False

        # Primary signal: a Devanagari typeface that produced no Devanagari.
        if any(hint in font_lc for hint in DEVANAGARI_FONT_HINTS):
            return True

        # Catch-all for unrecognised legacy encodings: a multi-character word with
        # a real share of control bytes, which correctly-extracted Latin text
        # never contains. The length guard avoids lone math/symbol glyphs.
        if len(stripped) >= 3:
            control = sum(1 for c in stripped if ord(c) < 32 and c not in "\t\n\r")
            if control and control / len(stripped) > 0.2:
                return True

        return False

    # ------------------------------------------------------------------ #
    # Images
    # ------------------------------------------------------------------ #
    def _extract_images(self, page, page_info: Dict[str, Any]) -> None:
        seen = set()
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                base_img = self.doc.extract_image(xref)
            except Exception as exc:  # corrupt / unsupported image stream
                logger.warning("Could not extract image xref=%s: %s", xref, exc)
                continue

            for rect in page.get_image_rects(xref):
                key = (xref, round(rect.x0, 1), round(rect.y0, 1))
                if key in seen:
                    continue
                seen.add(key)
                bbox = [rect.x0, rect.y0, rect.x1, rect.y1]
                page_info["elements"].append({
                    "type": "image",
                    "bbox": bbox,
                    "norm_bbox": self.normalize_bbox(bbox, page_info),
                    "image_data": base_img["image"],
                    "ext": base_img["ext"],
                    "width": rect.x1 - rect.x0,
                    "height": rect.y1 - rect.y0,
                    "px_width": base_img.get("width"),
                    "px_height": base_img.get("height"),
                    "xref": xref,
                })

    def normalize_bbox(self, bbox: List[float], page_info: Dict) -> List[float]:
        w = page_info["width"] or 1.0
        h = page_info["height"] or 1.0
        return [bbox[0] / w, bbox[1] / h, bbox[2] / w, bbox[3] / h]

    # ------------------------------------------------------------------ #
    # Tables (use PyMuPDF's native detector -- far more reliable than the
    # earlier vertical-gap heuristic).
    # ------------------------------------------------------------------ #
    def _detect_tables(self, page) -> List[Dict[str, Any]]:
        tables: List[Dict[str, Any]] = []
        try:
            found = page.find_tables()
        except Exception as exc:
            logger.debug("Table detection failed on page: %s", exc)
            return tables

        for tbl in found:
            try:
                cells = tbl.extract()  # list[rows] of cell text
            except Exception:
                cells = []
            tables.append({
                "bbox": list(tbl.bbox),
                "rows": tbl.row_count,
                "cols": tbl.col_count,
                "cells": cells,
            })
        return tables

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_scanned(page_info: Dict[str, Any]) -> bool:
        """A page is treated as scanned when it carries (almost) no real text but
        is dominated by a large image -- i.e. it is a picture of a document."""
        text_chars = sum(
            len(e["text"].strip())
            for e in page_info["elements"]
            if e["type"] == "text"
        )
        images = [e for e in page_info["elements"] if e["type"] == "image"]
        if text_chars >= 20 or not images:
            return False

        page_area = (page_info["width"] or 1) * (page_info["height"] or 1)
        largest = max(e["width"] * e["height"] for e in images)
        return largest / page_area > 0.4

    @staticmethod
    def _rgb_to_hex(rgb_int: int) -> str:
        r = (rgb_int >> 16) & 0xFF
        g = (rgb_int >> 8) & 0xFF
        b = rgb_int & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
