import { useEffect, useRef, useState } from "react";
import { renderAsync } from "docx-preview";
import { fetchDocx } from "../../lib/api";

/** Renders the real generated .docx in-browser with docx-preview. */
export function WordPreview({ jobId }: { jobId: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    (async () => {
      try {
        const blob = await fetchDocx(jobId);
        if (cancelled || !containerRef.current) return;
        containerRef.current.innerHTML = "";
        await renderAsync(blob, containerRef.current, undefined, {
          className: "docx",
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          breakPages: true,
          experimental: true,
          renderHeaders: true,
          renderFooters: true,
        });
        if (!cancelled) setStatus("ready");
      } catch {
        if (!cancelled) setStatus("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return (
    <div className="relative">
      {status === "loading" && (
        <div className="flex h-64 flex-col items-center justify-center gap-3 text-ink-mute">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-black/10 border-t-flow" />
          Rendering Word document…
        </div>
      )}
      {status === "error" && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-amber-700">
          Couldn’t render an inline preview. The download is still perfectly
          valid — use the Download button above.
        </div>
      )}
      <div
        ref={containerRef}
        className={`max-h-[640px] overflow-auto rounded-2xl bg-[#f1f1f4] p-4 ${
          status === "ready" ? "block" : "hidden"
        }`}
      />
    </div>
  );
}
