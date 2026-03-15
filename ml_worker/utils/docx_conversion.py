from docx import Document
from docx.shared import Pt,Inches
from typing import Dict, List
from io import BytesIO
import unicodedata


# Filters nepali characters and positions too
def clean_text(text: str) -> str:
    if not isinstance(text,str):
        return ""
    return "".join(ch for ch in text if ch.isprintable())

def export_to_docx(pages: List[Dict], output_path = str):
    doc = Document()
    for page in pages:
        doc.add_paragraph(f"---Page{page["page_number"]}---")
        elements = sorted(
            page["elements"],key = lambda e: (e["bbox"][1],e["bbox"][0])
        )
        para = doc.add_paragraph()
        for element in elements:
            if element["type"] == "text":
                text = element["text"]

                if not text.strip():
                    continue

                cleaned = clean_text(text)
                if not cleaned.strip():
                    continue
            elif element["type"] == "image":
                 cleaned = element.get('ocr_text', '')
                 if element["true_img"]:
                    image_stream = BytesIO(element["image_data"])
                    doc.add_picture(image_stream, width=Inches(4))
                    continue
            else:
                continue
            run = para.add_run(cleaned)
            run.bold = element.get("bold", False)
            run.italic = element.get("italic", False)
            run.font.size = Pt(element.get("font_size", 12))
        doc.add_page_break()


    doc.save(output_path)