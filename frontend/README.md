# PDFlow web frontend

A premium, Apple-inspired single-page app for PDFlow, built with **React +
TypeScript + Vite**, **Tailwind CSS**, **Framer Motion** (animations &
micro-interactions), **Lenis** (smooth scrolling) and **docx-preview** (true
in-browser Word rendering).

## Develop

```bash
npm install
npm run dev          # http://localhost:5173  (proxies /api → http://127.0.0.1:8000)
```

Run the API alongside it from the project root:

```bash
../.pvenv/bin/python -m uvicorn backend.app:app --reload
```

## Build

```bash
npm run build        # → dist/  (FastAPI serves this at "/")
```

## Structure

```
src/
  App.tsx                  Lenis smooth-scroll + page composition
  lib/
    api.ts                 typed API client + analysis types
    useConversion.ts       upload → SSE progress → result state machine
  components/
    Nav, Hero, ProblemSection, DualEngine, HowItWorks, Footer
    ui/Reveal.tsx          scroll-reveal + section headings
    converter/
      Converter.tsx        idle → progress → results orchestration
      Uploader.tsx         drag-and-drop + engine mode selector
      ProgressView.tsx     live stage timeline + log (Server-Sent Events)
      Results.tsx          download CTA + tabbed result views
      CompareView.tsx      draggable PDF-vs-Word before/after slider
      WordPreview.tsx      renders the real .docx with docx-preview
      RecoveredText.tsx    OCR-recovered Unicode Devanagari + confidence
      StructureView.tsx    reconstructed layout / text-box overlay
      PageCanvas.tsx       coordinate-pinned page reconstruction
      Details.tsx          engine reasoning + quality indicators
```
