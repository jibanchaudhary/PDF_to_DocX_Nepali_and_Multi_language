EMU_2_PX = 9525

def emu_to_px(v):
    """Docx image is stored in EMU, and pdf in pixel values"""
    return(v/EMU_2_PX)

def match_images(ocr_results, docx_images):
    matches = []

    pdf_images = []
    for page in ocr_results:
        for e in page["elements"]:
            if e["type"] == "image":
                if e["true_img"] == False:
                    pdf_images.append(e)

    for pdf_img in pdf_images:
        best_docx_img = None
        min_diff = float("inf")
        for docx_img in docx_images:
            dw = emu_to_px(docx_img.get("width", 0))
            dh =  emu_to_px(docx_img.get("height", 0))
            pw, ph = pdf_img.get("width", 0), pdf_img.get("height", 0)
            diff = abs(dw - pw) + abs(dh - ph)
            if diff < min_diff:
                min_diff = diff
                best_docx_img = docx_img
        if best_docx_img:
            matches.append({
                "pdf": pdf_img,
                "docx": best_docx_img
            })
    return matches
