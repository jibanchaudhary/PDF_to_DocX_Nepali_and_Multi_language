"""
Tesseract-based OCR fallback.

This is a lightweight alternative to :class:`NepaliOCR` (PaddleOCR) for
environments where Paddle is unavailable. It requires the system ``tesseract``
binary with the ``nep`` and ``eng`` language data installed. PaddleOCR is the
default engine because it is markedly more accurate on Devanagari; this module
is kept only as a drop-in fallback.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import List, Dict, Any

from PIL import Image

logger = logging.getLogger(__name__)


class TesseractOCR:
    def __init__(self, lang: str = "nep+eng"):
        import pytesseract  # imported lazily so Paddle-only installs still work
        self.pytesseract = pytesseract
        self.lang = lang

    def _confidence(self, img: Image.Image) -> float:
        try:
            data = self.pytesseract.image_to_data(
                img, lang=self.lang, output_type=self.pytesseract.Output.DICT
            )
            confs = [int(c) for c in data["conf"] if c not in ("-1", -1)]
            return sum(confs) / len(confs) if confs else 0.0
        except Exception as exc:
            logger.debug("Tesseract confidence failed: %s", exc)
            return 0.0

    def read_image(self, img: Image.Image) -> str:
        return self.pytesseract.image_to_string(img, lang=self.lang).strip()

    def process_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run OCR over every embedded image on every page (in place)."""
        for page in pages:
            for element in page.get("elements", []):
                if element.get("type") != "image":
                    continue
                try:
                    img = Image.open(BytesIO(element["image_data"]))
                except Exception as exc:
                    logger.warning("Cannot open image for OCR: %s", exc)
                    continue
                text = self.read_image(img)
                element["ocr_text"] = text
                element["ocr_confidence"] = self._confidence(img)
                element["true_img"] = len(text) < 5
        return pages


# Backwards-compatible alias.
PDFOCR = TesseractOCR
