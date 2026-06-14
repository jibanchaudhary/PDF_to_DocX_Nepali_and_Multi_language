# PDFlow — Nepali PDF → editable Word converter

Traditional PDF→Word converters mangle Nepali documents: text encoded with
legacy/CID fonts (subset Mangal, Preeti, …) extracts as garbage, and scanned or
image-based Nepali becomes a flat picture. PDFlow fixes this by recovering real,
**editable Unicode Devanagari** while preserving the original structure, sizes,
alignment, images and tables.

## How it works

Each PDF is routed automatically to one of two engines:

| Engine   | When it runs | What it does |
|----------|--------------|--------------|
| `flow`   | Clean digital PDFs whose text extracts correctly | Delegates to `pdf2docx` → reflowable paragraphs, native Word tables, images |
| `layout` | Any page with undecodable Nepali text or scanned content | Rebuilds the page with absolutely-positioned, fully editable text boxes + anchored images, using PaddleOCR (Devanagari) to recover text |

The `layout` engine handles four Nepali-specific cases:

1. **Legacy/CID text spans** (font renders Devanagari but extracts as garbage):
   the span's region is rendered and re-read with OCR.
2. **Text trapped in images** (e.g. a flattened paragraph of instructions): the
   image is OCR'd and replaced with positioned, editable text — one box per
   recovered line — placed over the original rectangle.
3. **Mixed graphics + text** (e.g. a banner with a logo *and* a heading): the
   baked-in text is painted out of the image so the graphic survives, then
   re-added as editable text on top. Pure graphics (photos, logos, stamps,
   signatures) are detected and kept untouched.
4. **Fully scanned pages**: the whole page is OCR'd and rebuilt as positioned text.

Every recovered span is emitted as its own coordinate-pinned text box, so form
label/value columns, side-by-side fields and table cells keep their original
horizontal positions instead of collapsing to the left edge of the line.

## Overall flow

A conversion runs through four stages. The orchestrator
([`ml_worker/converter.py`](ml_worker/converter.py)) wires them together; each
stage lives in its own module.

```
 input.pdf
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. PARSE         PDFParser.extract_all_pages()   (pipeline/pdf_parser)│
│    PyMuPDF reads every page into positioned elements:                 │
│      • text spans  → bbox, font, size, colour, bold/italic            │
│                      + needs_ocr flag (Devanagari font but no          │
│                        Devanagari codepoints = legacy/CID garbage)    │
│      • images      → raw bytes, bbox, pixel size                      │
│      • tables      → via page.find_tables()                           │
│      • is_scanned  → little text + one page-dominating image          │
└─────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. ROUTE         PDFToWordConverter._choose_engine()                  │
│    any page scanned OR any needs_ocr span ──► layout                  │
│    otherwise                              ──► flow                    │
│    (--mode can force either)                                          │
└─────────────────────────────────────────────────────────────────────┘
     │                                              │
   flow                                          layout
     │                                              │
     ▼                                              ▼
┌──────────────────────────┐   ┌────────────────────────────────────────┐
│ 3a. pdf2docx             │   │ 3b. OCR ENRICH   NepaliOCR.enrich_pages()│
│  reflowable paragraphs,  │   │       (pipeline/paddle_ocr_processor)    │
│  native Word tables,     │   │  • garbage spans → crop region, re-read  │
│  images. Done.           │   │    with PaddleOCR → real Unicode (Mangal)│
└──────────────────────────┘   │  • each image → classify & recover text  │
     │                         │    (graphic / text / mixed, see above)   │
     │                         │  • scanned page → OCR whole page into     │
     │                         │    positioned rows                       │
     │                         └────────────────────────────────────────┘
     │                                              │
     │                                              ▼
     │                         ┌────────────────────────────────────────┐
     │                         │ 4. BUILD   DocxLayoutBuilder.add_pages() │
     │                         │       (utils/docx_conversion)            │
     │                         │  • one Word section per page, sized to   │
     │                         │    the PDF page, zero margins            │
     │                         │  • images anchored first (background)    │
     │                         │  • every span/row → its own coordinate-  │
     │                         │    pinned floating text box (real runs)  │
     │                         └────────────────────────────────────────┘
     │                                              │
     └──────────────────────┬───────────────────────┘
                            ▼
                       output.docx
```

In short: **parse** the PDF into positioned elements, **route** to the right
engine, **recover** real Unicode text for anything the layout engine can't trust
(legacy fonts, images, scans), then **rebuild** the page in Word — clean digital
PDFs take the fast `pdf2docx` reflow path, while Nepali/scanned/image-text pages
are reconstructed coordinate-for-coordinate as editable text boxes and images.

## Setup

```bash
python -m venv .pvenv
source .pvenv/bin/activate
pip install -r requirements.txt          # plus a paddle backend:
pip install paddlepaddle                  # CPU  (or paddlepaddle-gpu for GPU)
```

The Devanagari OCR models are downloaded on first run (cached under `~/.paddlex`).

## Usage

Run from the `pdflow` directory:

```bash
# Auto-detect the best engine (default)
python -m scripts.run input.pdf output.docx

# Force a specific engine
python -m scripts.run input.pdf output.docx --mode layout   # OCR rebuild
python -m scripts.run input.pdf output.docx --mode flow     # pdf2docx reflow
```

Or from Python:

```python
from ml_worker.converter import PDFToWordConverter

PDFToWordConverter(mode="auto").convert("input.pdf", "output.docx")
```

### Options

- `--mode {auto,layout,flow}` — engine selection (default `auto`).
- `--lang` — OCR language code (default `ne` for Nepali/Devanagari).
- `--zoom` — render scale used for OCR; higher is sharper but slower (default `4.0`).

## Project layout

```
ml_worker/
  converter.py                     orchestrator + engine routing
  pipeline/
    pdf_parser.py                  PyMuPDF parsing, legacy-font / scan detection
    paddle_ocr_processor.py        PaddleOCR Nepali engine (regions, pages, images)
    ocr_processor.py               optional Tesseract fallback
  utils/
    docx_conversion.py             layout-preserving DOCX builder (text boxes/images)
scripts/
  run.py                           command-line entry point
```
