import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef } from "react";
import { ConversionState } from "../../lib/useConversion";
import { Check, Bolt, Layers } from "../icons";

const STAGE_HINT: Record<string, string> = {
  uploaded: "Your file reached the converter.",
  parsing: "Reading positioned text, images and tables.",
  routing: "Deciding between the flow and layout engines.",
  ocr: "Recovering Unicode Devanagari with PaddleOCR.",
  building: "Reassembling the editable Word document.",
  done: "Ready to preview and download.",
};

export function ProgressView({ state }: { state: ConversionState }) {
  const logRef = useRef<HTMLDivElement>(null);
  const activeIdx = state.stages.findIndex((s) => s.key === state.stage);

  useEffect(() => {
    logRef.current?.scrollTo({
      top: logRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [state.log.length]);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="text-center">
        <div className="relative mx-auto mb-6 grid h-20 w-20 place-items-center">
          <motion.span
            className="absolute inset-0 rounded-full bg-gradient-to-br from-flow/20 to-layout/20"
            animate={{ scale: [1, 1.15, 1], opacity: [0.6, 0.3, 0.6] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <motion.span
            className="absolute inset-2 rounded-full border-2 border-transparent border-t-flow border-r-layout"
            animate={{ rotate: 360 }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}
          />
          <span className="relative font-mono text-lg font-semibold text-ink">
            {Math.round(state.progress * 100)}%
          </span>
        </div>

        <h3 className="text-2xl font-semibold tracking-tight">
          {state.phase === "uploading" ? "Uploading…" : "Converting your PDF"}
        </h3>
        <p className="mt-2 min-h-[1.5rem] text-ink-mute">
          {state.message || STAGE_HINT[state.stage] || "Working…"}
        </p>

        <AnimatePresence>
          {state.engine && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="mt-4 inline-flex items-center gap-2 rounded-full border border-black/5 bg-white px-4 py-1.5 text-sm font-semibold shadow-sm"
            >
              {state.engine === "flow" ? (
                <Bolt className="h-4 w-4 text-flow" />
              ) : (
                <Layers className="h-4 w-4 text-layout" />
              )}
              <span
                className={
                  state.engine === "flow" ? "text-flow" : "text-layout"
                }
              >
                {state.engine} engine
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Progress bar */}
      <div className="mt-8">
        <div className="h-2 w-full overflow-hidden rounded-full bg-black/[0.06]">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-flow via-[#5e5ce6] to-layout"
            animate={{ width: `${Math.max(3, state.progress * 100)}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
        <div className="mt-2 flex justify-between text-xs text-ink-mute">
          <span>elapsed {state.elapsed.toFixed(1)}s</span>
          <span>{state.file?.name}</span>
        </div>
      </div>

      {/* Stage timeline */}
      <div className="mt-9 grid grid-cols-3 gap-2.5 sm:grid-cols-6">
        {state.stages.map((s, i) => {
          const done = i < activeIdx || state.phase === "done";
          const active = i === activeIdx && state.phase !== "done";
          return (
            <div
              key={s.key}
              className={`rounded-2xl border p-3 text-center transition-colors duration-500 ${
                done
                  ? "border-emerald-200 bg-emerald-50/60"
                  : active
                  ? "border-flow/30 bg-flow/5"
                  : "border-black/5 bg-white/50"
              }`}
            >
              <div
                className={`mx-auto mb-1.5 grid h-7 w-7 place-items-center rounded-full text-xs font-semibold ${
                  done
                    ? "bg-emerald-500 text-white"
                    : active
                    ? "bg-ink text-white"
                    : "bg-black/5 text-ink-mute"
                }`}
              >
                {done ? <Check className="h-4 w-4" /> : i + 1}
              </div>
              <div
                className={`text-[11px] font-medium leading-tight ${
                  active ? "text-ink" : "text-ink-mute"
                }`}
              >
                {s.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Live log */}
      <div
        ref={logRef}
        className="mt-7 max-h-40 overflow-y-auto rounded-2xl border border-black/5 bg-ink/[0.02] p-4 font-mono text-[13px]"
      >
        <AnimatePresence initial={false}>
          {state.log.map((l, i) => (
            <motion.div
              key={`${i}-${l.message}`}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-start gap-2 py-0.5 text-ink-soft"
            >
              <span className="text-ink-mute">
                {l.t != null ? `${l.t.toFixed(1)}s` : "·"}
              </span>
              <span className="text-flow">›</span>
              <span>{l.message}</span>
            </motion.div>
          ))}
          {state.log.length === 0 && (
            <div className="text-ink-mute">waiting for the pipeline…</div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
