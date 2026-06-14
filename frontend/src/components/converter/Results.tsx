import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Analysis, resultUrl } from "../../lib/api";
import { CompareView } from "./CompareView";
import { WordPreview } from "./WordPreview";
import { RecoveredText } from "./RecoveredText";
import { StructureView } from "./StructureView";
import { Details } from "./Details";
import {
  Download,
  Eye,
  FileWord,
  Languages,
  Layers,
  Gauge,
  Refresh,
  Check,
  ArrowRight,
} from "../icons";

const TABS = [
  { id: "compare", label: "Compare", icon: Eye },
  { id: "word", label: "Word preview", icon: FileWord },
  { id: "recovered", label: "Recovered text", icon: Languages },
  { id: "structure", label: "Structure", icon: Layers },
  { id: "details", label: "Details", icon: Gauge },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface Props {
  jobId: string;
  analysis: Analysis;
  onReset: () => void;
}

export function Results({ jobId, analysis, onReset }: Props) {
  const [tab, setTab] = useState<TabId>("compare");
  const [pageIdx, setPageIdx] = useState(0);
  const page = analysis.pages[pageIdx];
  const needsPageNav = tab === "compare" || tab === "structure";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Success banner + download */}
      <div className="relative overflow-hidden rounded-4xl border border-black/5 bg-white p-6 shadow-card md:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-gradient-to-br from-emerald-200/40 to-transparent blur-3xl" />
        <div className="relative flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 18, delay: 0.1 }}
              className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-emerald-500 text-white shadow-lg"
            >
              <Check className="h-7 w-7" />
            </motion.div>
            <div>
              <h3 className="text-2xl font-semibold tracking-tight">
                Your editable Word file is ready
              </h3>
              <p className="mt-1 text-ink-mute">
                <span className="font-medium text-ink">{analysis.filename}</span>{" "}
                ·{" "}
                {analysis.partial
                  ? `pages ${analysis.page_range} of ${analysis.total_pages}`
                  : `${analysis.page_count} page${
                      analysis.page_count === 1 ? "" : "s"
                    }`}{" "}
                ·{" "}
                <span
                  className={
                    analysis.engine === "flow" ? "text-flow" : "text-layout"
                  }
                >
                  {analysis.engine} engine
                </span>
              </p>
              {analysis.partial && (
                <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-flow/10 px-2.5 py-1 text-xs font-medium text-flow">
                  Partial conversion · {analysis.page_count} of{" "}
                  {analysis.total_pages} pages
                </span>
              )}
            </div>
          </div>

          <div className="flex w-full flex-col gap-2.5 sm:w-auto sm:flex-row">
            <a
              href={resultUrl(jobId)}
              className="btn-primary group w-full justify-center bg-emerald-600 hover:bg-emerald-700 sm:w-auto"
            >
              <Download className="h-4 w-4" />
              Download Word file
            </a>
            <button onClick={onReset} className="btn-ghost w-full justify-center sm:w-auto">
              <Refresh className="h-4 w-4" />
              Convert another
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-6 flex gap-1.5 overflow-x-auto rounded-2xl border border-black/5 bg-white/60 p-1.5 backdrop-blur">
        {TABS.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`relative flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors ${
                active ? "text-white" : "text-ink-soft hover:text-ink"
              }`}
            >
              {active && (
                <motion.span
                  layoutId="tab-pill"
                  className="absolute inset-0 rounded-xl bg-ink"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative flex items-center gap-2">
                <t.icon className="h-4 w-4" />
                {t.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Page navigation */}
      {needsPageNav && analysis.pages.length > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            onClick={() => setPageIdx((i) => Math.max(0, i - 1))}
            disabled={pageIdx === 0}
            className="grid h-9 w-9 place-items-center rounded-full border border-black/10 bg-white text-ink-soft transition-colors hover:border-black/20 disabled:opacity-30"
          >
            <ArrowRight className="h-4 w-4 rotate-180" />
          </button>
          <span className="text-sm font-medium text-ink-mute">
            Page {page.number} of {analysis.total_pages}
            {analysis.partial && analysis.pages.length > 1
              ? ` · ${pageIdx + 1}/${analysis.pages.length} selected`
              : ""}
          </span>
          <button
            onClick={() =>
              setPageIdx((i) => Math.min(analysis.pages.length - 1, i + 1))
            }
            disabled={pageIdx === analysis.pages.length - 1}
            className="grid h-9 w-9 place-items-center rounded-full border border-black/10 bg-white text-ink-soft transition-colors hover:border-black/20 disabled:opacity-30"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Panel */}
      <div className="mt-5 rounded-4xl border border-black/5 bg-white/70 p-5 shadow-card backdrop-blur md:p-7">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab + (needsPageNav ? pageIdx : "")}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
          >
            {tab === "compare" && <CompareView page={page} />}
            {tab === "word" && <WordPreview jobId={jobId} />}
            {tab === "recovered" && <RecoveredText analysis={analysis} />}
            {tab === "structure" && <StructureView page={page} />}
            {tab === "details" && <Details analysis={analysis} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
