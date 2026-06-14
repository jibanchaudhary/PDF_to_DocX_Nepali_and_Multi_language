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

# Convert only some pages (1-based) — the rest of the PDF is never parsed
python -m scripts.run input.pdf output.docx --pages 1-5     # first five pages
python -m scripts.run input.pdf output.docx --pages 2,4,6   # specific pages
python -m scripts.run input.pdf output.docx --pages 3-      # page 3 to the end
```

Or from Python:

```python
from ml_worker.converter import PDFToWordConverter

PDFToWordConverter(mode="auto").convert("input.pdf", "output.docx")
# only pages 1–5 (accepts a "1-5" spec or a list of 0-based indices)
PDFToWordConverter().convert("input.pdf", "output.docx", pages="1-5")
```

### Options

- `--mode {auto,layout,flow}` — engine selection (default `auto`).
- `--pages` — pages to convert, 1-based, e.g. `1-5`, `2,4,6`, `3-` (default: all).
  Only the selected pages are parsed, OCR'd and built.
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
backend/                           FastAPI web API (upload → convert → download)
  app.py                           routes: convert, SSE progress, previews, download
  service.py                       instrumented pipeline (progress + rich analysis)
  jobs.py                          in-memory job registry + event stream
frontend/                          premium React/Vite web UI (see frontend/README.md)
```

## Web app

A premium, Apple-inspired website wraps the same pipeline: drag-and-drop a PDF,
watch live progress (parse → route → OCR → build), then **download the editable
`.docx`** and explore the result — a draggable PDF-vs-Word comparison, an
in-browser Word preview, the OCR-recovered Unicode Devanagari with confidence
scores, a layout/structure reconstruction, and the engine reasoning. A live
badge in the header shows whether OCR inference is running on **GPU** (CUDA) or
has fallen back to **CPU**.

The frontend is a React/TypeScript SPA (Vite, Tailwind, Framer Motion); the
backend is FastAPI, reusing `ml_worker` for the conversion and streaming
progress over Server-Sent Events.

### Run it

```bash
# one-time: install the web layer into the same venv
pip install -r backend/requirements.txt          # fastapi, uvicorn, multipart
# and build the UI (needs Node 18+)
cd frontend && npm install && npm run build && cd ..

# serve the whole app (SPA at /, API under /api)
python web_run.py                                  # http://127.0.0.1:8000
```

`web_run.py` auto-builds the frontend on first run; pass `--port`, `--reload`,
or `--no-build` as needed. Use the venv interpreter, e.g.
`../.pvenv/bin/python web_run.py`.

For frontend development with hot reload, run `npm run dev` (port 5173, proxies
`/api`) alongside `uvicorn backend.app:app --reload`. See
[`frontend/README.md`](frontend/README.md) for details.

### API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/convert` | upload a PDF (`file`, `mode`, optional `pages` e.g. `1-5`), starts a job |
| `GET`  | `/api/jobs/{id}/events` | Server-Sent Events progress stream |
| `GET`  | `/api/jobs/{id}` | job status + analysis (poll/fallback) |
| `GET`  | `/api/jobs/{id}/result` | download the generated `.docx` |
| `GET`  | `/api/jobs/{id}/docx` | the `.docx` inline (in-browser preview) |
| `GET`  | `/api/jobs/{id}/pages/page-N.png` | rendered original page (before view) |
| `GET`  | `/api/device` | inference device — `gpu` (CUDA) or `cpu` fallback |
