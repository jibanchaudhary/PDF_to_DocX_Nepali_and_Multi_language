import pytesseract
from typing import List, Dict, Any
from io import BytesIO
from PIL import Image


class PDFOCR:
    def __init__(self, ocr_engine = pytesseract):
        self.ocr_engine = ocr_engine

    def _get_confidence(self, img: Image.Image, lang: str) -> float:
        """Get OCR confidence score"""
        try:
            data = self.ocr_engine.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            return sum(confidences) / len(confidences) if confidences else 0.0
        except:
            return 0.0
        
    def process_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for i, element in enumerate(elements[0]["elements"]):
            if element["type"] == "image":
                img = Image.open(BytesIO(element["image_data"]))
                ocr_text = self.ocr_engine.image_to_string(img, lang="nep+eng")
                element["ocr_text"] = ocr_text
                element["ocr_bbox"] = self.ocr_engine.image_to_boxes(img, lang="nep+eng")
                element["ocr_confidence"] = self._get_confidence(img, lang="nep+eng")
                if element["ocr_confidence"] < 50:
                    element["osd"] = None
                else:
                    element["osd"] = self.ocr_engine.image_to_osd(img)
        return elements

