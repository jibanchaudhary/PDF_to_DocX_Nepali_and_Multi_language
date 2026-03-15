from ml_worker.pipeline.pdf_parser import PDFParser
from ml_worker.utils.docx_conversion import export_to_docx
from ml_worker.utils.docx_img_extracter import extract_docx_images
from ml_worker.pipeline.ocr_processor import PDFOCR
from ml_worker.utils.img_matcher import match_images
from pdf2docx import Converter
from docx.shared import Pt
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph

def should_replace(img):
    return (
        img.get("ocr_confidence", 0) > 0 and
        len(img.get("ocr_text", "").strip()) > 0
    )

def replace_image_with_text(doc, shape, text):
    """
    Replaces an inline image shape in a docx with text.

    Args:
        doc: docx.Document object
        shape: InlineShape object to replace
        text: Text to insert in place of the image
    """
    inline = shape._inline
    drawing_elm = inline.getparent() # This contains the drawing part too, so getting the parent elm of drawing.
    run_elm = drawing_elm.getparent()         
    paragraph_elm = run_elm.getparent()        

    if paragraph_elm is None or run_elm is None:
        print("Cannot find run or paragraph to remove the image")
        return

    # Remove the run containing the image
    paragraph_elm.remove(run_elm)
    print("Removed image run")

    # Add a new run with text in the same paragraph
    paragraph = Paragraph(paragraph_elm, doc)
    run = paragraph.add_run(text)
    run.font.size = Pt(10)
    print("Added text in place of image")


def main():
    pdf_path = "/home/jiban/Documents/jiban/PDFlow/pdflow/tests/License.Pdf"
    docx_path = "/home/jiban/Documents/jiban/PDFlow/pdflow/tests/license.docx"
    test = PDFParser(pdf_path)
    pdf_pages = test.extract_all_pages()
    ocr = PDFOCR()
    ocr_results = ocr.process_elements(pdf_pages)
    cv = Converter(pdf_path)
    cv.convert(docx_path)
    cv.close()

    doc, docx_imgs = extract_docx_images(docx_path)
    matches = match_images(ocr_results, docx_imgs)
    for match in sorted(matches, key=lambda x: x["docx"]["index"], reverse=True):
        pdf_img = match["pdf"]
        shape_idx = match["docx"]["index"]
        docx_shape = doc.inline_shapes[shape_idx]
        if should_replace(pdf_img):
            # print(pdf_img["ocr_text"])
            replace_image_with_text(doc, docx_shape, pdf_img["ocr_text"])

    doc.save(docx_path)
    print("EEEEEEENNNNNDDDDD")

if __name__ == "__main__":
    main()