"""
Command-line entry point for PDFlow.

Usage:
    python -m scripts.run INPUT.pdf [OUTPUT.docx] [--mode auto|layout|flow]

Run from the ``pdflow`` directory (the one containing ``ml_worker`` and
``scripts``) so the package imports resolve.
"""

import argparse
import sys
import os

# Allow running both as a module (-m scripts.run) and as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_worker.converter import PDFToWordConverter  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdflow",
        description="Convert a (Nepali) PDF into an editable Word document.",
    )
    parser.add_argument("input", help="Path to the input PDF")
    parser.add_argument("output", nargs="?", default=None,
                        help="Path to the output .docx (default: alongside input)")
    parser.add_argument("--mode", choices=["auto", "layout", "flow"], default="auto",
                        help="Conversion engine: auto-detect (default), force the "
                             "OCR layout rebuild, or force pdf2docx reflow.")
    parser.add_argument("--lang", default="ne", help="OCR language (default: ne)")
    parser.add_argument("--zoom", type=float, default=4.0,
                        help="Render scale for OCR (default: 4.0)")
    args = parser.parse_args(argv)

    converter = PDFToWordConverter(mode=args.mode, lang=args.lang, zoom=args.zoom)
    out = converter.convert(args.input, args.output)
    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
