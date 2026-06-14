// API client + shared types for the PDFlow backend.

export type Engine = "flow" | "layout";
export type Mode = "auto" | "flow" | "layout";

export interface TextElement {
  type: "text";
  bbox: [number, number, number, number]; // normalised 0..1
  text: string;
  ocr: boolean;
  score: number | null;
  source: string | null; // "legacy-font" | "image" | "scan"
  bold: boolean;
  italic: boolean;
  color: string;
  size: number; // font size as fraction of page height
}

export interface ImageElement {
  type: "image";
  bbox: [number, number, number, number];
  src: string | null;
}

export type PageElement = TextElement | ImageElement;

export interface TableInfo {
  bbox: [number, number, number, number];
  rows: number | null;
  cols: number | null;
  cells: (string | null)[][] | null;
}

export interface PageInfo {
  number: number;
  width: number;
  height: number;
  is_scanned: boolean;
  n_text: number;
  n_images: number;
  n_tables: number;
  preview: string;
  elements: PageElement[];
  tables: TableInfo[];
}

export interface RecoveredSpan {
  page: number;
  text: string;
  score: number | null;
  source: string;
  bbox: [number, number, number, number];
}

export interface DeviceInfo {
  device: "gpu" | "cpu";
  cuda: boolean;
  count: number;
  name: string | null;
  backend: string | null;
  detail: string;
}

export interface Quality {
  ocr_spans: number;
  avg_confidence: number | null;
  low_conf_spans: number;
  recovered_chars: number;
  images_recovered: number;
  scanned_pages: number;
  total_text_spans: number;
  total_images: number;
  total_tables: number;
}

export interface Analysis {
  engine: Engine;
  engine_reason: string;
  mode: Mode;
  filename: string;
  page_count: number;
  total_pages: number;
  partial: boolean;
  page_range: string;
  device: DeviceInfo;
  duration_sec: number;
  output_size: number;
  input_size: number;
  quality: Quality;
  pages: PageInfo[];
  recovered: RecoveredSpan[];
}

export interface StageDef {
  key: string;
  label: string;
}

export interface JobState {
  id: string;
  filename: string;
  mode: Mode;
  status: "queued" | "running" | "done" | "error";
  stage: string;
  progress: number;
  message: string;
  error: string | null;
  analysis: Analysis | null;
  stages: StageDef[];
}

export interface ProgressEvent {
  type: "progress" | "done" | "error" | "ping";
  stage?: string;
  message?: string;
  progress?: number;
  status?: string;
  engine?: Engine;
  engine_reason?: string;
  page?: number;
  page_count?: number;
  analysis?: Analysis;
  t?: number;
}

const API = ""; // same-origin; Vite proxies /api in dev

export async function startConversion(
  file: File,
  mode: Mode,
  pages = ""
): Promise<JobState> {
  const form = new FormData();
  form.append("file", file);
  form.append("mode", mode);
  form.append("pages", pages);
  const res = await fetch(`${API}/api/convert`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

/** Subscribe to a job's Server-Sent Events progress stream. */
export function streamProgress(
  jobId: string,
  onEvent: (ev: ProgressEvent) => void,
  onError: (err: Event) => void
): () => void {
  const es = new EventSource(`${API}/api/jobs/${jobId}/events`);
  es.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data) as ProgressEvent);
    } catch {
      /* ignore malformed keep-alive frames */
    }
  };
  es.onerror = (e) => onError(e);
  return () => es.close();
}

export async function fetchDevice(): Promise<DeviceInfo> {
  const res = await fetch(`${API}/api/device`);
  if (!res.ok) throw new Error("device check failed");
  return res.json();
}

export const resultUrl = (jobId: string) => `${API}/api/jobs/${jobId}/result`;
export const docxUrl = (jobId: string) => `${API}/api/jobs/${jobId}/docx`;

export async function fetchDocx(jobId: string): Promise<Blob> {
  const res = await fetch(docxUrl(jobId));
  if (!res.ok) throw new Error("Could not load Word document");
  return res.blob();
}

export function formatBytes(n: number): string {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(n) / Math.log(1024));
  return `${(n / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`;
}
