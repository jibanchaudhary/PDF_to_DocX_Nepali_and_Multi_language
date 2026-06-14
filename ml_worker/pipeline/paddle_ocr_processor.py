"""
Nepali OCR powered by PaddleOCR (Devanagari model).

Used to recover real, editable Unicode Devanagari from two situations that
defeat plain PDF text extraction:

  1. Text spans whose embedded legacy/CID font decodes to garbage. The span's
     region is rendered from the PDF page and re-read.
  2. Fully scanned pages, where the whole page is rasterised and read line by
     line so it can be rebuilt as positioned, editable text.

The heavy PaddleOCR engine is created lazily and reused as a singleton.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

import numpy as np
import cv2
import fitz

logger = logging.getLogger(__name__)

# Render scale for cropping regions out of the PDF page. Higher = sharper glyphs
# for OCR at the cost of speed/memory.
DEFAULT_ZOOM = 4.0

# Word-safe Devanagari font used for every recovered/OCR'd Nepali run.
DEVANAGARI_FONT = "Mangal"


class NepaliOCR:
    """Thin wrapper around a PaddleOCR Devanagari pipeline."""

    _engine = None  # class-level singleton (PaddleOCR load is expensive)

    def __init__(self, lang: str = "ne", min_confidence: float = 0.5,
                 zoom: float = DEFAULT_ZOOM, ocr_images: bool = True,
                 devanagari_font: str = DEVANAGARI_FONT):
        self.lang = lang
        self.min_confidence = min_confidence
        self.zoom = zoom
        # When True, embedded images that contain real text (a flattened
        # paragraph of Nepali instructions, a banner/heading, ...) have that
        # text recovered as editable, positioned runs. Pure graphics (photos,
        # logos, stamps, signatures) are left as images, and images that mix
        # the two (a logo + a heading) keep the graphic while the baked-in text
        # is erased and replaced with editable text.
        self.ocr_images = ocr_images
        self.devanagari_font = devanagari_font

    @classmethod
    def _get_engine(cls, lang: str):
        if cls._engine is None:
            from paddleocr import PaddleOCR  # imported lazily; slow + heavy
            logger.info("Initialising PaddleOCR (lang=%s)...", lang)
            cls._engine = PaddleOCR(
                lang=lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                # Orientation classification rotates small horizontal crops and
                # silently drops them; keep it off for region/line recognition.
                use_textline_orientation=False,
            )
        return cls._engine

    def _predict(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        if image is None or image.size == 0:
            return None
        engine = self._get_engine(self.lang)
        results = engine.predict(image)
        if not results:
            return None
        return results[0]

    def _lines_from_result(self, res: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalise a PaddleOCR result into [{text, bbox, score}] sorted in
        natural reading order (top-to-bottom, then left-to-right)."""
        if not res:
            return []
        texts = res.get("rec_texts") or []
        scores = res.get("rec_scores") or []
        boxes = res.get("rec_boxes")
        if boxes is None:
            boxes = res.get("rec_polys")

        items: List[Dict[str, Any]] = []
        for i, text in enumerate(texts):
            score = scores[i] if i < len(scores) else 0.0
            if score < self.min_confidence or not text.strip():
                continue
            bbox = self._box_to_bbox(boxes[i]) if boxes is not None and i < len(boxes) else None
            items.append({"text": text.strip(), "bbox": bbox, "score": float(score)})

        items.sort(key=lambda it: self._reading_key(it["bbox"]))
        return items

    @staticmethod
    def _box_to_bbox(box) -> List[float]:
        """Accept either an [x0,y0,x1,y1] box or a 4-point polygon."""
        arr = np.asarray(box, dtype=float).reshape(-1)
        if arr.size == 4:
            return [float(arr[0]), float(arr[1]), float(arr[2]), float(arr[3])]
        pts = np.asarray(box, dtype=float).reshape(-1, 2)
        return [float(pts[:, 0].min()), float(pts[:, 1].min()),
                float(pts[:, 0].max()), float(pts[:, 1].max())]

    @staticmethod
    def _reading_key(bbox: Optional[List[float]]):
        if not bbox:
            return (0.0, 0.0)
        # Bucket the y coordinate so words on the same visual line keep their
        # left-to-right order instead of being interleaved by tiny y jitter.
        y_bucket = round(bbox[1] / 10.0)
        return (y_bucket, bbox[0])


    def read_image(self, image: np.ndarray, joiner: str = " ") -> str:
        """Return the recognised text of an image as a single string."""
        res = self._predict(image)
        lines = self._lines_from_result(res)
        return joiner.join(it["text"] for it in lines)

    def read_page_lines(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Return positioned lines for a full page image (pixel coordinates)."""
        return self._lines_from_result(self._predict(image))

    def crop_region(self, page_image: np.ndarray, bbox: List[float],
                    pad: float = 3.0) -> np.ndarray:
        """Crop a PDF-coordinate bbox out of an already-rendered page image.

        Cropping from one high-DPI page render is both faster and noticeably
        more accurate than rasterising each region separately, which can clip
        ascenders/descenders of Devanagari glyphs.
        """
        h, w = page_image.shape[:2]
        x0 = max(int((bbox[0] - pad) * self.zoom), 0)
        y0 = max(int((bbox[1] - pad) * self.zoom), 0)
        x1 = min(int((bbox[2] + pad) * self.zoom), w)
        y1 = min(int((bbox[3] + pad) * self.zoom), h)
        if x1 <= x0 or y1 <= y0:
            return np.empty((0, 0, 3), dtype=np.uint8)
        return page_image[y0:y1, x0:x1].copy()

    def render_page(self, page: "fitz.Page", zoom: Optional[float] = None) -> np.ndarray:
        z = zoom or self.zoom
        pix = page.get_pixmap(matrix=fitz.Matrix(z, z))
        return self._pix_to_bgr(pix)

    @staticmethod
    def _pix_to_bgr(pix) -> np.ndarray:
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:        # RGBA -> BGR
            return img[:, :, [2, 1, 0]].copy()
        if pix.n == 3:        # RGB -> BGR
            return img[:, :, ::-1].copy()
        # grayscale -> BGR
        return np.repeat(img, 3, axis=2)

    def enrich_pages(self, doc: "fitz.Document", pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """For every page, replace garbage text spans with OCR'd Devanagari,
        recover text baked into images, and -- for scanned pages -- attach
        reconstructed positioned OCR lines."""
        for page_info in pages:
            page = doc[page_info["page_index"]]

            if page_info.get("is_scanned"):
                self._enrich_scanned_page(page, page_info)
                continue

            broken = [e for e in page_info["elements"]
                      if e["type"] == "text" and e.get("needs_ocr")]
            if broken:
                # Render the whole page once and crop each broken region from it.
                page_image = self.render_page(page)
                for el in broken:
                    crop = self.crop_region(page_image, el["bbox"])
                    recognised = self.read_image(crop)
                    if recognised:
                        el["text"] = recognised
                        el["ocr"] = True
                        el["font"] = self.devanagari_font  # Devanagari-capable
                    else:
                        # Could not recover this glyph run -- drop the
                        # undecodable text rather than emit raw legacy bytes.
                        logger.debug("OCR returned nothing for region %s", el["bbox"])
                        el["text"] = ""

            if self.ocr_images:
                self._extract_text_from_images(page_info)
        return pages


    def _extract_text_from_images(self, page_info: Dict[str, Any]) -> None:
        """Recover editable text from images that carry it.

        Each embedded image is OCR'd and classified:

        * ``graphic`` -- a photo / logo / stamp / signature with no recoverable
          text; left completely untouched.
        * ``text``    -- essentially a block of text (e.g. a flattened paragraph
          of Nepali instructions); the picture is dropped and replaced with
          positioned, editable text rows.
        * ``mixed``   -- a graphic that also contains text (e.g. a banner with a
          logo *and* a heading); the baked-in text is painted out of the image
          so the graphic survives, and the text is re-added as editable rows.
        """
        new_elements: List[Dict[str, Any]] = []
        for el in page_info["elements"]:
            if el.get("type") != "image" or el.get("replaced"):
                continue
            arr = self._decode_image(el.get("image_data"))
            if arr is None:
                continue
            lines = self.read_page_lines(arr)
            kind = self._classify_image(lines, arr.shape)
            if kind == "graphic":
                continue
            h, w = arr.shape[:2]
            rows = self._lines_to_row_elements(lines, w, h, el["bbox"])
            if not rows:
                continue
            if kind == "text":
                el["replaced"] = True  # builder skips the original picture
            else:  # mixed -- keep the graphic but erase its baked-in text
                masked = self._mask_lines(arr, lines)
                if masked is not None:
                    el["image_data"] = masked
                    el["ext"] = "png"
            new_elements.extend(rows)
        page_info["elements"].extend(new_elements)

    @staticmethod
    def _decode_image(data) -> Optional[np.ndarray]:
        if not data:
            return None
        try:
            return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return None

    def _classify_image(self, lines: List[Dict[str, Any]], shape) -> str:
        """Return ``"graphic"``, ``"text"`` or ``"mixed"`` for an OCR'd image.

        The decision keys off how much *confident, meaningful* text was found
        rather than raw area coverage, so a wide banner whose text only fills a
        quarter of the picture (a logo eats the rest) is still recognised as
        carrying editable text.
        """
        h, w = shape[:2]
        area = float(w * h) or 1.0
        confident = [
            ln for ln in lines
            if ln["bbox"] and ln["score"] >= 0.6 and ln["text"].strip()
        ]
        if len(confident) < 3:
            return "graphic"

        chars = sum(len(ln["text"]) for ln in confident)
        meaningful = sum(sum(c.isalnum() for c in ln["text"]) for ln in confident)
        mean_score = sum(ln["score"] for ln in confident) / len(confident)
        # Reject sparse / low-quality / symbol-noise detections (e.g. a stray
        # mark OCR'd off a signature) -- those are graphics, not text.
        if chars < 12 or mean_score < 0.7 or meaningful < 0.5 * chars:
            return "graphic"

        covered = sum(
            (ln["bbox"][2] - ln["bbox"][0]) * (ln["bbox"][3] - ln["bbox"][1])
            for ln in confident
        )
        # Densely text-filled -> drop the image; otherwise it is a graphic that
        # merely contains some text and must be preserved.
        return "text" if covered / area >= 0.45 else "mixed"

    def _mask_lines(self, bgr: np.ndarray, lines: List[Dict[str, Any]],
                    pad_frac: float = 0.18) -> Optional[bytes]:
        """Paint the detected text regions out of an image with its background
        colour and return the result as PNG bytes. Vertical padding is generous
        so Devanagari head-strokes (shirorekha) and matras are also removed."""
        out = bgr.copy()
        h, w = out.shape[:2]
        ring = np.concatenate([
            out[:4].reshape(-1, 3), out[-4:].reshape(-1, 3),
            out[:, :4].reshape(-1, 3), out[:, -4:].reshape(-1, 3),
        ])
        bg = np.median(ring, axis=0).tolist()
        for ln in lines:
            if not ln["bbox"]:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            py = (y1 - y0) * pad_frac
            px = (x1 - x0) * 0.02
            rx0, ry0 = max(int(x0 - px), 0), max(int(y0 - py), 0)
            rx1, ry1 = min(int(x1 + px), w), min(int(y1 + py), h)
            if rx1 > rx0 and ry1 > ry0:
                out[ry0:ry1, rx0:rx1] = bg
        ok, buf = cv2.imencode(".png", out)
        return buf.tobytes() if ok else None

    def _lines_to_row_elements(self, lines: List[Dict[str, Any]],
                               src_w: int, src_h: int,
                               dst_rect: List[float],
                               color: str = "#000000") -> List[Dict[str, Any]]:
        """Cluster OCR segments into visual rows and map them from source pixel
        coordinates onto ``dst_rect`` (a PDF-coordinate rectangle), returning one
        positioned, editable text element per row. Used for both text-bearing
        images and full-page scans so every path produces the same element shape.
        """
        rows = self._cluster_rows(lines)
        if not rows:
            return []
        dx0, dy0, dx1, dy1 = dst_rect
        sx = (dx1 - dx0) / float(src_w or 1)
        sy = (dy1 - dy0) / float(src_h or 1)

        elements: List[Dict[str, Any]] = []
        for r in rows:
            bx0, by0, bx1, by1 = r["bbox"]
            pdf_bbox = [dx0 + bx0 * sx, dy0 + by0 * sy,
                        dx0 + bx1 * sx, dy0 + by1 * sy]
            glyph_h = (by1 - by0) * sy
            elements.append({
                "type": "text",
                "bbox": pdf_bbox,
                "text": r["text"],
                "font": self.devanagari_font,
                "font_size": max(glyph_h * 0.68, 5.0),
                "color": color,
                "bold": False,
                "italic": False,
                "ocr": True,
                "needs_ocr": False,
            })
        return elements

    @staticmethod
    def _cluster_rows(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group recognised segments into visual rows (top-to-bottom), joining
        the segments of each row left-to-right. Each row carries its union
        bounding box so it can be positioned precisely."""
        boxed = [ln for ln in lines if ln["bbox"] and ln["text"].strip()]
        if not boxed:
            return []
        boxed.sort(key=lambda ln: ln["bbox"][1])
        heights = sorted(ln["bbox"][3] - ln["bbox"][1] for ln in boxed)
        tol = (heights[len(heights) // 2] * 0.6) or 6.0

        rows: List[Dict[str, Any]] = []
        current = [boxed[0]]
        ref_y = boxed[0]["bbox"][1]
        for ln in boxed[1:]:
            if abs(ln["bbox"][1] - ref_y) <= tol:
                current.append(ln)
            else:
                rows.append(NepaliOCR._merge_row(current))
                current = [ln]
                ref_y = ln["bbox"][1]
        rows.append(NepaliOCR._merge_row(current))
        return rows

    @staticmethod
    def _merge_row(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        segments.sort(key=lambda s: s["bbox"][0])
        text = " ".join(s["text"] for s in segments)
        return {
            "text": text,
            "bbox": [
                min(s["bbox"][0] for s in segments),
                min(s["bbox"][1] for s in segments),
                max(s["bbox"][2] for s in segments),
                max(s["bbox"][3] for s in segments),
            ],
        }

    def _enrich_scanned_page(self, page, page_info: Dict[str, Any]) -> None:
        img = self.render_page(page)
        h, w = img.shape[:2]
        lines = self.read_page_lines(img)
        dst = [0.0, 0.0, page_info["width"], page_info["height"]]
        page_info["ocr_lines"] = self._lines_to_row_elements(lines, w, h, dst)


PDFOCR = NepaliOCR
