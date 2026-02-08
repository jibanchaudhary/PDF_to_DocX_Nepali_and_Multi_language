import os
import json
import fitz
from typing import List, Dict, Any

import logging


logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

class PDFParser:

    """
    PDF parsing and Element configuration
    """
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page_data = []

    def extract_all_pages(self) -> List[Dict[str, Any]]:
        logger.info(f"Extracting text from PDF: {self.pdf_path}")

        for page_num in range(len(self.doc)):
            page_info = self.extract_page(page_num)
            self.page_data.append(page_info)

        return self.page_data
    
    def extract_page(self, page_num: int) -> Dict[str, Any]:
        page = self.doc[page_num]

        page_info = {
            "page_number" : page_num + 1,
            "width" : page.rect.width,
            "height" : page.rect.height,
            "elements" : []
        }
        text_blocks = page.get_text("dict")["blocks"]
        for block in text_blocks:
            if block["type"] == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        element = {
                            "type": "text",
                            "bbox": span["bbox"],
                            "text": span["text"],
                            "font_size": span["size"],
                            "color": self.__rgb_to_hex(span["color"]),
                            "flags": span["flags"],
                            "bold": bool(span["flags"] & 2**4),
                            "italic": bool(span["flags"] & 2**1)
                        }
                        page_info["elements"].append(element)


        # Extract_images
        image_list = page.get_images(full = True)
        for img_idx, img in enumerate(image_list):
            xref = img[0]
            base_img = self.doc.extract_image(xref)
            
            # Get image position
            img_rects = page.get_image_rects(xref)
            for rect in img_rects:
                element = {
                    "type": "image",
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "image_data": base_img['image'],
                    "ext": base_img["ext"],
                    "width": base_img["width"],
                    "height": base_img["height"],
                    "xref": xref
                }
                page_info["elements"].append(element)
        # Detect tables

        tables = self._detect_tables(page_info["elements"])
        page_info["tables"] = tables

        return page_info

    def __rgb_to_hex(self,rgb_int: int) -> str:
        '''convert RGB integer to hex'''
        r = (rgb_int >> 16) & 0xFF
        g = (rgb_int >> 8) & 0xFF
        b = rgb_int & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def _detect_tables(self, elements: List[Dict]) -> List[Dict]:
        tables = []
        text_elements = [e for e in elements if e["type"] == "text"]
        if len(text_elements) < 2:
            return tables

        sorted_by_y = sorted(text_elements, key=lambda e: e["bbox"][1])

        # Cluster elements by vertical gaps
        clusters = []
        current_cluster = [sorted_by_y[0]]
        GAP_THRESHOLD = 4
        for i in range(1, len(sorted_by_y)):
            prev_y = sorted_by_y[i-1]["bbox"][1]
            curr_y = sorted_by_y[i]["bbox"][1]
            gap = curr_y - prev_y

            if gap > GAP_THRESHOLD:
                clusters.append(current_cluster)
                current_cluster = []

            current_cluster.append(sorted_by_y[i])

        if current_cluster:
            clusters.append(current_cluster)
        # Process clusters
        for cluster in clusters:
            if len(cluster) < 1:
                continue

            bbox = None
            y_positions = [e["bbox"][1] for e in cluster]

            # Calculating vertical gaps within cluster
            gaps = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]

            if len(gaps) > 2:
                avg_gaps = sum(gaps) / len(gaps)
                consistent_gaps = sum(1 for g in gaps if abs(g - avg_gaps) < 2)

                if consistent_gaps / len(gaps) > 0.7:  # threshold met
                    bbox = [
                        min(e['bbox'][0] for e in cluster),
                        min(e['bbox'][1] for e in cluster),
                        max(e['bbox'][2] for e in cluster),
                        max(e['bbox'][3] for e in cluster)
                    ]
                else:
                    bbox = None 

            tables.append({"bbox": bbox})
        return tables
