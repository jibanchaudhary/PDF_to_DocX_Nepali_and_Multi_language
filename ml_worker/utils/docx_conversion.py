"""
Layout-preserving DOCX builder.

Rebuilds each PDF page inside Word using absolutely-positioned, fully editable
floating text boxes (one per visual line) and anchored pictures placed at their
exact coordinates. Because every glyph becomes a real Word run, the output keeps
the original structure, size, alignment and orientation while remaining
character-by-character editable -- the core goal for Nepali documents whose text
would otherwise arrive as broken legacy-font glyphs or flattened images.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Dict, Any
import logging

from docx import Document
from docx.oxml import parse_xml
from docx.shared import Emu
from docx.enum.section import WD_SECTION

logger = logging.getLogger(__name__)

EMU_PER_PT = 12700

# Namespaces required by the DrawingML we emit (python-docx's nsmap lacks wps/pic).
_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
)

# Map common PDF base-14 / embedded font names to Word-safe equivalents.
_LATIN_FONT_MAP = {
    "helvetica": "Arial",
    "arial": "Arial",
    "times": "Times New Roman",
    "timesnewroman": "Times New Roman",
    "courier": "Courier New",
    "symbol": "Symbol",
}
_DEVANAGARI_FONT = "Mangal"


def _xml_escape(text: str) -> str:
    # Drop control characters that are illegal in XML 1.0 (e.g. leftover legacy
    # font bytes) before escaping the markup-significant characters.
    text = "".join(c for c in text if c in "\t\n\r" or ord(c) >= 32)
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))


def _is_devanagari(text: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in text)


def _map_font(font: str, text: str) -> str:
    if _is_devanagari(text):
        return _DEVANAGARI_FONT
    base = font.split("+")[-1].split("-")[0].replace(" ", "").lower()
    for key, val in _LATIN_FONT_MAP.items():
        if key in base:
            return val
    # Strip subset prefix but otherwise trust the embedded name.
    return font.split("+")[-1] if font else "Calibri"


class DocxLayoutBuilder:
    """Assemble a DOCX from parsed, OCR-enriched PDF pages."""

    def __init__(self):
        self.doc = Document()
        self._shape_id = 0
        _zero_default_section(self.doc.sections[0])

    def add_pages(self, pages: List[Dict[str, Any]]) -> None:
        for idx, page in enumerate(pages):
            self.add_page(page, first=(idx == 0))

    def add_page(self, page_info: Dict[str, Any], first: bool = False) -> None:
        if first:
            section = self.doc.sections[0]
        else:
            section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        _configure_section(section, page_info["width"], page_info["height"])

        host = self.doc.add_paragraph()
        host.paragraph_format.space_before = Emu(0)
        host.paragraph_format.space_after = Emu(0)

        text_elements, image_elements = self._collect_elements(page_info)

        # Pictures first so text boxes sit on top of any background imagery
        # (e.g. editable text re-added over a masked banner/logo).
        for img in image_elements:
            self._add_image(host, img)

        for span in text_elements:
            self._add_text_element(host, span)


    def _collect_elements(self, page_info: Dict[str, Any]):
        elements = page_info["elements"]
        if page_info.get("is_scanned"):
            text_elements = [e for e in page_info.get("ocr_lines", []) if e["text"].strip()]
            # Drop the full-page scan image; keep only small embedded graphics.
            page_area = (page_info["width"] or 1) * (page_info["height"] or 1)
            image_elements = [
                e for e in elements
                if e["type"] == "image" and (e["width"] * e["height"]) / page_area < 0.4
            ]
        else:
            text_elements = [
                e for e in elements
                if e["type"] == "text" and e["text"].strip()
            ]
            image_elements = [
                e for e in elements
                if e["type"] == "image" and not e.get("replaced")
            ]
        # Stable top-to-bottom, left-to-right order keeps the document's reading
        # order sane for anyone tabbing/selecting through the boxes.
        text_elements.sort(key=lambda e: (round(e["bbox"][1], 1), e["bbox"][0]))
        return text_elements, image_elements

    def _next_id(self) -> int:
        self._shape_id += 1
        return self._shape_id

    def _add_text_element(self, paragraph, span: Dict[str, Any]) -> None:
        """Emit a single span/line as its own floating text box pinned to the
        span's exact PDF coordinates.

        One box *per span* (rather than one merged box per visual line) is what
        preserves the document's horizontal structure: form label/value columns,
        side-by-side fields and table cells keep their original x positions
        instead of collapsing together at the line's left edge.
        """
        run_xml = self._run_xml(span)
        if not run_xml:
            return
        x0, y0, x1, y1 = span["bbox"]
        # A little slack so substituted fonts (e.g. Mangal -> a system
        # Devanagari face) are never clipped; wrap="none" stops any reflow.
        width = max(x1 - x0, 2.0) + 4.0
        height = max(y1 - y0, 6.0) + 2.0
        sid = self._next_id()
        xml = (
            f"<w:r {_NS}><w:drawing>"
            f'<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" '
            f'relativeHeight="{sid}" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
            f'<wp:simplePos x="0" y="0"/>'
            f'{_pos("H", x0)}{_pos("V", y0)}'
            f'<wp:extent cx="{_emu(width)}" cy="{_emu(height)}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
            f'<wp:docPr id="{sid}" name="TextBox{sid}"/><wp:cNvGraphicFramePr/>'
            f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
            f'<wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr>'
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{_emu(width)}" cy="{_emu(height)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'<a:noFill/><a:ln><a:noFill/></a:ln></wps:spPr>'
            f'<wps:txbx><w:txbxContent>'
            f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
            f'</w:pPr>{run_xml}</w:p>'
            f'</w:txbxContent></wps:txbx>'
            # wrap="none": keep the span on a single line so it never reflows and
            # piles up on top of neighbouring boxes.
            f'<wps:bodyPr rot="0" spcFirstLastPara="0" vertOverflow="overflow" '
            f'horzOverflow="overflow" wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" '
            f'numCol="1" anchor="t" anchorCtr="0"><a:noAutofit/></wps:bodyPr>'
            f'</wps:wsp></a:graphicData></a:graphic>'
            f'</wp:anchor></w:drawing></w:r>'
        )
        paragraph._p.append(parse_xml(xml))

    def _run_xml(self, span: Dict[str, Any]) -> str:
        text = _xml_escape(span["text"])
        if not text.strip():  # nothing survived control-char stripping
            return ""
        font = _map_font(span.get("font", ""), span["text"])
        size_hp = max(int(round(span.get("font_size", 10) * 2)), 2)  # half-points
        color = span.get("color", "#000000").lstrip("#") or "000000"
        bold = "<w:b/>" if span.get("bold") else ""
        italic = "<w:i/>" if span.get("italic") else ""
        return (
            f"<w:r><w:rPr>{bold}{italic}"
            f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
            f'<w:color w:val="{color}"/><w:sz w:val="{size_hp}"/><w:szCs w:val="{size_hp}"/>'
            f'</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'
        )

    def _add_image(self, paragraph, img: Dict[str, Any]) -> None:
        try:
            rId, _ = self.doc.part.get_or_add_image(BytesIO(img["image_data"]))
        except Exception as exc:
            logger.warning("Skipping unembeddable image: %s", exc)
            return
        x0, y0, x1, y1 = img["bbox"]
        width, height = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
        sid = self._next_id()
        xml = (
            f"<w:r {_NS}><w:drawing>"
            f'<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" '
            f'relativeHeight="{sid}" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
            f'<wp:simplePos x="0" y="0"/>'
            f'{_pos("H", x0)}{_pos("V", y0)}'
            f'<wp:extent cx="{_emu(width)}" cy="{_emu(height)}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
            f'<wp:docPr id="{sid}" name="Picture{sid}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks '
            f'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            f'</wp:cNvGraphicFramePr>'
            f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr>'
            f'<pic:cNvPr id="{sid}" name="Picture{sid}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rId}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{_emu(width)}" cy="{_emu(height)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic>'
            f'</wp:anchor></w:drawing></w:r>'
        )
        paragraph._p.append(parse_xml(xml))

    def save(self, output_path: str) -> str:
        self.doc.save(output_path)
        logger.info("Saved DOCX -> %s", output_path)
        return output_path


def _emu(pt: float) -> int:
    return int(round(pt * EMU_PER_PT))


def _pos(axis: str, pt: float) -> str:
    rel = "page"
    tag = "positionH" if axis == "H" else "positionV"
    return f'<wp:{tag} relativeFrom="{rel}"><wp:posOffset>{_emu(pt)}</wp:posOffset></wp:{tag}>'


def _zero_default_section(section) -> None:
    section.top_margin = section.bottom_margin = Emu(0)
    section.left_margin = section.right_margin = Emu(0)


def _configure_section(section, width_pt: float, height_pt: float) -> None:
    section.page_width = Emu(_emu(width_pt))
    section.page_height = Emu(_emu(height_pt))
    section.top_margin = section.bottom_margin = Emu(0)
    section.left_margin = section.right_margin = Emu(0)
    section.header_distance = Emu(0)
    section.footer_distance = Emu(0)


def export_to_docx(pages: List[Dict[str, Any]], output_path: str) -> str:
    builder = DocxLayoutBuilder()
    builder.add_pages(pages)
    return builder.save(output_path)
