from docx import Document

def extract_docx_images(docx_path):
    doc = Document(docx_path)
    images = []
    for idx, shape in enumerate(doc.inline_shapes):
        images.append({
            "index": idx,
            "width": shape.width,
            "height": shape.height
        })
    return doc, images
