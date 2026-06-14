import { Analysis, RecoveredSpan } from "../../lib/api";
import { Languages, Image, Scan, Check } from "../icons";

const SOURCE_META: Record<
  string,
  { label: string; icon: typeof Languages; tint: string }
> = {
  "legacy-font": { label: "Legacy font", icon: Languages, tint: "text-rose-500 bg-rose-50" },
  image: { label: "From image", icon: Image, tint: "text-sky-500 bg-sky-50" },
  scan: { label: "Scanned", icon: Scan, tint: "text-amber-500 bg-amber-50" },
};

function confColor(score: number | null): string {
  if (score == null) return "bg-black/5 text-ink-mute";
  if (score >= 0.92) return "bg-emerald-50 text-emerald-600";
  if (score >= 0.8) return "bg-lime-50 text-lime-700";
  if (score >= 0.65) return "bg-amber-50 text-amber-600";
  return "bg-rose-50 text-rose-500";
}

export function RecoveredText({ analysis }: { analysis: Analysis }) {
  const spans = analysis.recovered;

  if (spans.length === 0) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-8 text-center">
        <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-emerald-500 text-white">
          <Check className="h-6 w-6" />
        </div>
        <h4 className="text-lg font-semibold">No OCR recovery needed</h4>
        <p className="mx-auto mt-2 max-w-md text-ink-mute">
          This PDF already had a clean, decodable text layer — every character
          extracted natively, so PDFlow used the fast flow engine. Nothing was
          re-read by OCR.
        </p>
      </div>
    );
  }

  const byPage = new Map<number, RecoveredSpan[]>();
  for (const s of spans) {
    const arr = byPage.get(s.page) ?? [];
    arr.push(s);
    byPage.set(s.page, arr);
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-3 text-sm text-ink-mute">
        <span className="font-medium text-ink">
          {spans.length} Unicode Devanagari span{spans.length === 1 ? "" : "s"}{" "}
          recovered
        </span>
        {analysis.quality.avg_confidence != null && (
          <span className="rounded-full bg-ink/5 px-3 py-1">
            avg confidence{" "}
            {(analysis.quality.avg_confidence * 100).toFixed(0)}%
          </span>
        )}
        <span className="rounded-full bg-ink/5 px-3 py-1">
          {analysis.quality.recovered_chars.toLocaleString()} characters
        </span>
      </div>

      <div className="max-h-[560px] space-y-6 overflow-y-auto pr-1">
        {[...byPage.entries()].map(([pageNum, list]) => (
          <div key={pageNum}>
            <div className="mb-2.5 text-xs font-semibold uppercase tracking-widest text-ink-mute">
              Page {pageNum}
            </div>
            <div className="space-y-2">
              {list.map((s, i) => {
                const meta =
                  SOURCE_META[s.source] ?? SOURCE_META["legacy-font"];
                return (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-xl border border-black/5 bg-white p-3 shadow-sm transition-colors hover:border-black/10"
                  >
                    <span
                      className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium ${meta.tint}`}
                    >
                      <meta.icon className="h-3.5 w-3.5" />
                      {meta.label}
                    </span>
                    <span className="min-w-0 flex-1 truncate font-deva text-[17px] text-ink">
                      {s.text}
                    </span>
                    {s.score != null && (
                      <span
                        className={`shrink-0 rounded-md px-2 py-1 font-mono text-xs font-semibold ${confColor(
                          s.score
                        )}`}
                      >
                        {(s.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
