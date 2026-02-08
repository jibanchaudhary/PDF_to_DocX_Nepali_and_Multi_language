import pikepdf

pdf = pikepdf.Pdf.open("/home/jiban/Documents/jiban/PDFlow/pdflow/tests/sample-tables.pdf")
if "StructTreeRoot" in pdf.docinfo.keys():
    print("Pdf is accessible format")
else:
    print("Pdf is visual and use fitz")