import { useCallback, useRef, useState } from "react";
import {
  Analysis,
  Engine,
  Mode,
  ProgressEvent,
  StageDef,
  startConversion,
  streamProgress,
} from "./api";

export type Phase = "idle" | "uploading" | "processing" | "done" | "error";

export interface ConversionState {
  phase: Phase;
  jobId: string | null;
  file: File | null;
  stage: string;
  message: string;
  progress: number;
  engine: Engine | null;
  engineReason: string | null;
  stages: StageDef[];
  log: { stage: string; message: string; t?: number }[];
  analysis: Analysis | null;
  error: string | null;
  elapsed: number;
}

const DEFAULT_STAGES: StageDef[] = [
  { key: "uploaded", label: "Uploaded" },
  { key: "parsing", label: "Parsing" },
  { key: "routing", label: "Routing" },
  { key: "ocr", label: "OCR recovery" },
  { key: "building", label: "Building DOCX" },
  { key: "done", label: "Done" },
];

const initial: ConversionState = {
  phase: "idle",
  jobId: null,
  file: null,
  stage: "",
  message: "",
  progress: 0,
  engine: null,
  engineReason: null,
  stages: DEFAULT_STAGES,
  log: [],
  analysis: null,
  error: null,
  elapsed: 0,
};

export function useConversion() {
  const [state, setState] = useState<ConversionState>(initial);
  const closeRef = useRef<(() => void) | null>(null);
  const timerRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);

  const stopTimer = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const reset = useCallback(() => {
    closeRef.current?.();
    closeRef.current = null;
    stopTimer();
    setState(initial);
  }, []);

  const convert = useCallback(async (file: File, mode: Mode, pages = "") => {
    closeRef.current?.();
    stopTimer();
    startRef.current = Date.now();
    setState({
      ...initial,
      phase: "uploading",
      file,
      message: "Uploading…",
      stages: DEFAULT_STAGES,
    });

    timerRef.current = window.setInterval(() => {
      setState((s) =>
        s.phase === "processing" || s.phase === "uploading"
          ? { ...s, elapsed: (Date.now() - startRef.current) / 1000 }
          : s
      );
    }, 100);

    let job;
    try {
      job = await startConversion(file, mode, pages);
    } catch (e) {
      stopTimer();
      setState((s) => ({
        ...s,
        phase: "error",
        error: e instanceof Error ? e.message : "Upload failed",
      }));
      return;
    }

    setState((s) => ({
      ...s,
      phase: "processing",
      jobId: job.id,
      stages: job.stages?.length ? job.stages : DEFAULT_STAGES,
    }));

    const onEvent = (ev: ProgressEvent) => {
      if (ev.type === "ping") return;
      setState((s) => {
        const next = { ...s };
        if (typeof ev.progress === "number") next.progress = ev.progress;
        if (ev.stage) next.stage = ev.stage;
        if (ev.message) next.message = ev.message;
        if (ev.engine) next.engine = ev.engine;
        if (ev.engine_reason) next.engineReason = ev.engine_reason;
        if (ev.type === "progress" && ev.message && ev.stage) {
          const last = next.log[next.log.length - 1];
          if (!last || last.message !== ev.message) {
            next.log = [
              ...next.log,
              { stage: ev.stage, message: ev.message, t: ev.t },
            ];
          }
        }
        if (ev.type === "done" && ev.analysis) {
          next.phase = "done";
          next.analysis = ev.analysis;
          next.engine = ev.analysis.engine;
          next.engineReason = ev.analysis.engine_reason;
          next.progress = 1;
          stopTimer();
        }
        if (ev.type === "error") {
          next.phase = "error";
          next.error = ev.message || "Conversion failed";
          stopTimer();
        }
        return next;
      });
    };

    closeRef.current = streamProgress(job.id, onEvent, () => {
      // EventSource auto-reconnects; only treat as fatal if we never finished.
      setState((s) =>
        s.phase === "processing" && s.progress < 1 ? s : s
      );
    });
  }, []);

  return { state, convert, reset };
}
