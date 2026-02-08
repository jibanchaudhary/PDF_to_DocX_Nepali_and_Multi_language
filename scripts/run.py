from ml_worker.pipeline.pdf_parser import PDFParser

def main():
    test_path = "/home/jiban/Documents/jiban/PDFlow/pdflow/tests/sample-tables.pdf"
    test=PDFParser(test_path)
    result = test.extract_all_pages()
    breakpoint()
if __name__ == "__main__":
    main()