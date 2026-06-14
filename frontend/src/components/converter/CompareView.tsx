import { useRef, useState } from "react";
import { PageInfo } from "../../lib/api";
import { PageCanvas } from "./PageCanvas";

/** Draggable before/after slider: original PDF render vs PDFlow reconstruction. */
export function CompareView({ page }: { page: PageInfo }) {
  const [pos, setPos] = useState(50);
  const wrapRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const move = (clientX: number) => {
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const p = ((clientX - r.left) / r.width) * 100;
    setPos(Math.max(0, Math.min(100, p)));
  };

  return (
    <div>
      <div
        ref={wrapRef}
        className="relative select-none overflow-hidden rounded-xl border border-black/5 bg-white shadow-card"
        style={{ aspectRatio: `${page.width} / ${page.height}` }}
        onPointerMove={(e) => dragging.current && move(e.clientX)}
        onPointerUp={() => (dragging.current = false)}
        onPointerLeave={() => (dragging.current = false)}
      >
        {/* Base: original PDF page */}
        <img
          src={page.preview}
          alt={`PDF page ${page.number}`}
          className="absolute inset-0 h-full w-full object-contain"
          draggable={false}
        />
        <span className="absolute left-3 top-3 rounded-full bg-black/70 px-3 py-1 text-xs font-semibold text-white backdrop-blur">
          Original PDF
        </span>

        {/* Overlay: reconstructed Word, clipped to the slider */}
        <div
          className="absolute inset-0"
          style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
        >
          <div className="absolute inset-0 bg-white">
            <PageCanvas page={page} highlightOcr />
          </div>
          <span className="absolute right-3 top-3 rounded-full bg-gradient-to-r from-flow to-layout px-3 py-1 text-xs font-semibold text-white">
            PDFlow Word
          </span>
        </div>

        {/* Handle */}
        <div
          className="absolute inset-y-0 z-10 w-0.5 cursor-ew-resize bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.1)]"
          style={{ left: `${pos}%` }}
          onPointerDown={(e) => {
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
            dragging.current = true;
          }}
        >
          <div className="absolute left-1/2 top-1/2 grid h-9 w-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-black/10 bg-white shadow-md">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="text-ink-soft">
              <path d="M9 7 4 12l5 5M15 7l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
      </div>

      <p className="mt-3 text-center text-sm text-ink-mute">
        Drag the handle — left is the original PDF, right is the rebuilt,
        editable Word layout. Recovered Unicode is tinted{" "}
        <span className="font-medium text-layout">violet</span>.
      </p>
    </div>
  );
}
