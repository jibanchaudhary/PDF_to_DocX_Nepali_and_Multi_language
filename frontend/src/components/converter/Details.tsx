import { Analysis, formatBytes } from "../../lib/api";
import { Bolt, Layers, Gauge, Languages, Image, Scan, Table, FileText, Cpu } from "../icons";

function Ring({ value }: { value: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value));
  return (
    <svg viewBox="0 0 80 80" className="h-24 w-24 -rotate-90">
      <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth="8" />
      <circle
        cx="40"
        cy="40"
        r={r}
        fill="none"
        stroke="url(#ringg)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct)}
        style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.16,1,0.3,1)" }}
      />
      <defs>
        <linearGradient id="ringg" x1="0" y1="0" x2="80" y2="80">
          <stop stopColor="#0a84ff" />
          <stop offset="1" stopColor="#bf5af2" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function Details({ analysis }: { analysis: Analysis }) {
  const q = analysis.quality;
  const isLayout = analysis.engine === "layout";

  const stats = [
    {
      icon: FileText,
      label: analysis.partial ? "Pages (selected)" : "Pages",
      value: analysis.partial
        ? `${analysis.page_count}/${analysis.total_pages}`
        : analysis.page_count,
    },
    { icon: FileText, label: "Text spans", value: q.total_text_spans.toLocaleString() },
    { icon: Table, label: "Tables", value: q.total_tables },
    { icon: Image, label: "Images", value: q.total_images },
    { icon: Languages, label: "OCR spans", value: q.ocr_spans },
    { icon: Scan, label: "Scanned pages", value: q.scanned_pages },
  ];

  return (
    <div className="space-y-6">
      {/* Engine explainer */}
      <div
        className={`relative overflow-hidden rounded-3xl border border-black/5 bg-white p-7 shadow-card ring-1 ${
          isLayout ? "ring-layout/25" : "ring-flow/25"
        }`}
      >
        <div
          className={`pointer-events-none absolute -right-12 -top-12 h-44 w-44 rounded-full blur-3xl ${
            isLayout ? "bg-layout/15" : "bg-flow/15"
          }`}
        />
        <div className="relative flex items-start gap-4">
          <div
            className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-ink/5 ${
              isLayout ? "text-layout" : "text-flow"
            }`}
          >
            {isLayout ? <Layers className="h-6 w-6" /> : <Bolt className="h-6 w-6" />}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-xl font-semibold tracking-tight">
                {analysis.engine} engine
              </h4>
              <span className="rounded-full bg-ink/5 px-2.5 py-0.5 text-xs font-medium text-ink-mute">
                mode: {analysis.mode}
              </span>
              <span
                title={analysis.device.detail}
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  analysis.device.device === "gpu"
                    ? "bg-emerald-50 text-emerald-600"
                    : "bg-ink/5 text-ink-mute"
                }`}
              >
                <Cpu className="h-3 w-3" />
                {analysis.device.device === "gpu" ? "GPU" : "CPU"} inference
              </span>
            </div>
            <p className="mt-2 leading-relaxed text-ink-soft">
              {analysis.engine_reason}
            </p>
          </div>
        </div>
      </div>

      {/* Quality + stats */}
      <div className="grid gap-6 md:grid-cols-[auto_1fr]">
        {isLayout && q.avg_confidence != null && (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-black/5 bg-white p-7 shadow-card">
            <div className="relative grid place-items-center">
              <Ring value={q.avg_confidence} />
              <div className="absolute text-center">
                <div className="font-mono text-xl font-semibold">
                  {(q.avg_confidence * 100).toFixed(0)}%
                </div>
                <div className="text-[10px] uppercase tracking-widest text-ink-mute">
                  OCR conf
                </div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-sm text-ink-mute">
              <Gauge className="h-4 w-4" />
              {q.low_conf_spans} low-confidence span
              {q.low_conf_spans === 1 ? "" : "s"}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-2xl border border-black/5 bg-white p-4 shadow-sm"
            >
              <s.icon className="h-5 w-5 text-ink-mute" />
              <div className="mt-3 text-2xl font-semibold tracking-tight">
                {s.value}
              </div>
              <div className="text-sm text-ink-mute">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* File facts */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Input", value: formatBytes(analysis.input_size) },
          { label: "Output .docx", value: formatBytes(analysis.output_size) },
          { label: "Conversion time", value: `${analysis.duration_sec.toFixed(1)}s` },
          {
            label: "Recovered chars",
            value: q.recovered_chars.toLocaleString(),
          },
        ].map((f) => (
          <div
            key={f.label}
            className="rounded-2xl border border-black/5 bg-canvas p-4"
          >
            <div className="text-xs uppercase tracking-widest text-ink-mute">
              {f.label}
            </div>
            <div className="mt-1 font-mono text-lg font-semibold">
              {f.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
