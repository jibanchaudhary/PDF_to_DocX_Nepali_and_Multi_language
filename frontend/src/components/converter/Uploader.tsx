import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mode, formatBytes } from "../../lib/api";
import { Upload, FileText, X, ArrowRight, Bolt, Layers, Sparkles } from "../icons";

const MODES: { id: Mode; label: string; desc: string; icon: typeof Bolt }[] = [
  { id: "auto", label: "Auto", desc: "Detect the best engine", icon: Sparkles },
  { id: "flow", label: "Flow", desc: "Force pdf2docx reflow", icon: Bolt },
  { id: "layout", label: "Layout", desc: "Force OCR rebuild", icon: Layers },
];

interface Props {
  onConvert: (file: File, mode: Mode, pages: string) => void;
}

export function Uploader({ onConvert }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<Mode>("auto");
  const [scope, setScope] = useState<"all" | "range">("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [drag, setDrag] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Build the 1-based page spec the backend understands ("" = all pages).
  const buildPages = (): string => {
    if (scope === "all") return "";
    const a = from.trim();
    const b = to.trim();
    if (!a && !b) return "";
    return b ? `${a || "1"}-${b}` : `${a || "1"}-`;
  };

  const accept = (f: File | undefined | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErr("Please choose a PDF file.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setErr("File is larger than 50 MB.");
      return;
    }
    setErr(null);
    setFile(f);
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* Dropzone */}
      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          accept(e.dataTransfer.files?.[0]);
        }}
        onClick={() => !file && inputRef.current?.click()}
        animate={{ scale: drag ? 1.01 : 1 }}
        transition={{ duration: 0.2 }}
        className={`relative cursor-pointer overflow-hidden rounded-4xl border-2 border-dashed p-10 text-center transition-colors duration-300 md:p-14 ${
          drag
            ? "border-flow bg-flow/5"
            : file
            ? "border-emerald-300 bg-emerald-50/40 cursor-default"
            : "border-black/15 bg-white/60 hover:border-flow/50 hover:bg-white"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => accept(e.target.files?.[0])}
        />

        {!file ? (
          <div className="pointer-events-none flex flex-col items-center">
            <motion.div
              animate={{ y: drag ? -6 : 0 }}
              className="mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-flow to-layout text-white shadow-glow"
            >
              <Upload className="h-7 w-7" />
            </motion.div>
            <h3 className="text-xl font-semibold tracking-tight">
              {drag ? "Drop to convert" : "Drag & drop your PDF"}
            </h3>
            <p className="mt-2 text-ink-mute">
              or <span className="font-medium text-flow">browse</span> — Nepali,
              scanned or legacy-font documents welcome
            </p>
            <p className="mt-4 text-xs text-ink-mute">PDF · up to 50 MB</p>
          </div>
        ) : (
          <div className="flex items-center gap-4 text-left">
            <div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-white text-flow shadow-sm">
              <FileText className="h-7 w-7" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate font-semibold">{file.name}</div>
              <div className="text-sm text-ink-mute">
                {formatBytes(file.size)}
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className="grid h-9 w-9 place-items-center rounded-full bg-black/5 text-ink-mute transition-colors hover:bg-black/10 hover:text-ink"
              aria-label="Remove file"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
      </motion.div>

      {err && (
        <p className="mt-3 text-center text-sm font-medium text-red-500">{err}</p>
      )}

      {/* Engine mode */}
      <div className="mt-6">
        <div className="mb-2.5 text-center text-sm font-medium text-ink-mute">
          Engine
        </div>
        <div className="grid grid-cols-3 gap-2 rounded-2xl border border-black/5 bg-white/60 p-1.5 backdrop-blur">
          {MODES.map((m) => {
            const active = mode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`relative rounded-xl px-2 py-3 text-center transition-colors ${
                  active ? "text-white" : "text-ink-soft hover:text-ink"
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="mode-pill"
                    className="absolute inset-0 rounded-xl bg-ink"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
                <span className="relative flex flex-col items-center gap-1">
                  <m.icon className="h-4 w-4" />
                  <span className="text-sm font-semibold">{m.label}</span>
                  <span
                    className={`text-[11px] ${
                      active ? "text-white/70" : "text-ink-mute"
                    }`}
                  >
                    {m.desc}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Page selection */}
      <div className="mt-5">
        <div className="mb-2.5 flex items-center justify-center gap-2 text-sm font-medium text-ink-mute">
          Pages to convert
        </div>
        <div className="grid grid-cols-2 gap-2 rounded-2xl border border-black/5 bg-white/60 p-1.5 backdrop-blur">
          {([
            { id: "all", label: "All pages", desc: "Convert the whole PDF" },
            { id: "range", label: "Page range", desc: "Only the pages you pick" },
          ] as const).map((s) => {
            const active = scope === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setScope(s.id)}
                className={`relative rounded-xl px-2 py-3 text-center transition-colors ${
                  active ? "text-white" : "text-ink-soft hover:text-ink"
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="scope-pill"
                    className="absolute inset-0 rounded-xl bg-ink"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
                <span className="relative flex flex-col items-center gap-0.5">
                  <span className="text-sm font-semibold">{s.label}</span>
                  <span
                    className={`text-[11px] ${
                      active ? "text-white/70" : "text-ink-mute"
                    }`}
                  >
                    {s.desc}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <AnimatePresence initial={false}>
          {scope === "range" && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-3 flex items-center justify-center gap-3 rounded-2xl border border-black/5 bg-white/60 px-4 py-3.5 backdrop-blur">
                <label className="flex items-center gap-2 text-sm font-medium text-ink-soft">
                  From
                  <input
                    type="number"
                    min={1}
                    inputMode="numeric"
                    value={from}
                    onChange={(e) => setFrom(e.target.value)}
                    placeholder="1"
                    className="w-20 rounded-lg border border-black/10 bg-white px-3 py-2 text-center text-ink outline-none transition-colors focus:border-flow"
                  />
                </label>
                <span className="text-ink-mute">→</span>
                <label className="flex items-center gap-2 text-sm font-medium text-ink-soft">
                  To
                  <input
                    type="number"
                    min={1}
                    inputMode="numeric"
                    value={to}
                    onChange={(e) => setTo(e.target.value)}
                    placeholder="end"
                    className="w-20 rounded-lg border border-black/10 bg-white px-3 py-2 text-center text-ink outline-none transition-colors focus:border-flow"
                  />
                </label>
              </div>
              <p className="mt-2 text-center text-xs text-ink-mute">
                1-based and inclusive. Leave “To” empty to go to the last page —
                only these pages are parsed, OCR’d and converted.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button
        disabled={!file}
        onClick={() => file && onConvert(file, mode, buildPages())}
        className="btn-primary group mt-7 w-full disabled:cursor-not-allowed disabled:opacity-40"
      >
        Convert to editable Word
        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
      </button>
    </div>
  );
}
