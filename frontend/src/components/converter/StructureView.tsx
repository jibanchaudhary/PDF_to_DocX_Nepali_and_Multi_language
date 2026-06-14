import { useState } from "react";
import { PageInfo } from "../../lib/api";
import { PageCanvas } from "./PageCanvas";
import { Table } from "../icons";

function Toggle({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
        on
          ? "border-ink bg-ink text-white"
          : "border-black/10 bg-white text-ink-soft hover:border-black/20"
      }`}
    >
      {children}
    </button>
  );
}

export function StructureView({ page }: { page: PageInfo }) {
  const [boxes, setBoxes] = useState(true);
  const [ocr, setOcr] = useState(true);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Toggle on={boxes} onClick={() => setBoxes((v) => !v)}>
          Text boxes
        </Toggle>
        <Toggle on={ocr} onClick={() => setOcr((v) => !v)}>
          Highlight OCR
        </Toggle>
        <div className="ml-auto flex items-center gap-3 text-xs text-ink-mute">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm border border-flow/40 bg-flow/10" />
            text box
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm border border-layout/40 bg-layout/15" />
            OCR-recovered
          </span>
        </div>
      </div>

      <div className="rounded-xl border border-black/5 bg-[repeating-conic-gradient(#f6f6f8_0%_25%,#fff_0%_50%)] [background-size:18px_18px] p-3 shadow-card">
        <PageCanvas page={page} showBoxes={boxes} highlightOcr={ocr} />
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-sm text-ink-mute">
        <span className="rounded-full bg-ink/5 px-3 py-1">
          {page.n_text} text boxes
        </span>
        <span className="rounded-full bg-ink/5 px-3 py-1">
          {page.n_images} images
        </span>
        <span className="rounded-full bg-ink/5 px-3 py-1">
          {page.n_tables} tables
        </span>
        {page.is_scanned && (
          <span className="rounded-full bg-amber-50 px-3 py-1 font-medium text-amber-600">
            scanned page
          </span>
        )}
      </div>

      {page.tables.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <Table className="h-4 w-4" /> Detected tables
          </div>
          <div className="flex flex-wrap gap-2">
            {page.tables.map((t, i) => (
              <span
                key={i}
                className="rounded-lg border border-black/5 bg-white px-3 py-1.5 text-sm text-ink-soft shadow-sm"
              >
                {t.rows ?? "?"} × {t.cols ?? "?"} grid
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
