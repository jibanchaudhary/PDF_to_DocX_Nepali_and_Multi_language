from paddleocr import PaddleOCR
import numpy as np
import cv2
from typing import List, Dict, Any
from io import BytesIO
from PIL import Image


class PDFOCR:
    def __init__(self, ocr_engine = PaddleOCR):
        self.ocr_engine = ocr_engine(
            lang="ne",
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True
        )

    # def polygons_to_bboxes(self, rec_boxes: np.ndarray) -> tuple:
    #     xs = [p[0] for p in rec_boxes]
    #     ys = [p[1] for p in rec_boxes]

    #     x_min = int(min(xs))
    #     x_max = int(max(xs))
    #     y_min = int(min(ys))
    #     y_max = int(max(ys))

    #     return(x_min, y_min, x_max, y_max)
    # def _get_confidence(self, img: Image.Image, lang: str) -> float:
    #     """Get OCR confidence score"""
    #     try:
    #         data = self.ocr_engine.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    #         confidences = [int(conf) for conf in data['conf'] if conf != '-1']
    #         return sum(confidences) / len(confidences) if confidences else 0.0
    #     except:
    #         return 0.0
    def assemble_texts(self, rec_texts: List[str], rec_boxes: np.ndarray) -> str:
        data = []
        lines = []
        current_line = []
        threshold = 10

        prev_y = None
        for text, box in zip (rec_texts, rec_boxes):
            x = box[0]
            y = box[1]
            data.append((x,y,text))
        data = sorted(data, key=lambda x: (x[0], x[1]))      

        for y, x , text in data:
            if prev_y is None:
                current_line.append(text)
                prev_y = y
                continue
            if abs(y-prev_y) < threshold:
                current_line.append(text)
            else:
                lines.append(" ".join(current_line))
                current_line = [text]
            prev_y = y
        lines.append(" ".join(current_line))

        return ("\n".join(lines))
    
    def process_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for i, element in enumerate(elements[0]["elements"]):
            if element["type"] == "image":
                img_bytes = element["image_data"]
                img_nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(img_nparr, cv2.IMREAD_COLOR)
                ocr_results = self.ocr_engine.predict(img)
                ocr_texts = ocr_results[0]["rec_texts"]
                if ocr_texts:
                    text = ocr_texts[0].strip()
                else:
                    text = ''
                if len(text) < 5 :
                    element["true_img"] = True
                else:
                    element["true_img"] = False
                rec_bboxes = ocr_results[0].get("rec_boxes")  
                rec_confidence = ocr_results[0].get("rec_scores")
                if rec_bboxes is not None and rec_bboxes.size > 0:
                    ocr_bbox = tuple(map(int, rec_bboxes[0]))
                else:
                    ocr_bbox = []
                if len(rec_confidence)>=1 and rec_confidence[0] > 0.5:
                    assembled_text = self.assemble_texts(ocr_texts, rec_bboxes)
                else:
                    assembled_text = ''
                element["ocr_text"] = assembled_text
                element["ocr_bbox"] = ocr_bbox
                if rec_confidence:
                    ocr_confidence = rec_confidence[0]
                else:
                    ocr_confidence = 0
                element["ocr_confidence"] = ocr_confidence
                if element["ocr_confidence"] < 0.5:
                    element["osd"] = None
                    element["vis_fonts"] = None
                else:
                    element["osd"] = ocr_results[0]["textline_orientation_angles"]
                    element["vis_fonts"] =  ocr_results[0]["vis_fonts"]
                
        return elements

