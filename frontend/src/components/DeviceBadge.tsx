import { useEffect, useState } from "react";
import { DeviceInfo, fetchDevice } from "../lib/api";
import { Cpu } from "./icons";

/**
 * Live indicator of whether OCR inference runs on a CUDA GPU or falls back to
 * CPU. Polls /api/device once on mount; the value comes straight from Paddle.
 */
export function DeviceBadge({ className = "" }: { className?: string }) {
  const [dev, setDev] = useState<DeviceInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchDevice()
      .then((d) => alive && setDev(d))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  if (failed) return null;

  const gpu = dev?.device === "gpu";
  const label = !dev ? "···" : gpu ? "GPU" : "CPU";
  const title = dev
    ? `Inference device: ${gpu ? "GPU" : "CPU"} — ${dev.detail}`
    : "Detecting inference device…";

  return (
    <span
      title={title}
      className={`inline-flex select-none items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors ${
        !dev
          ? "border-black/10 bg-white/60 text-ink-mute"
          : gpu
          ? "border-emerald-200 bg-emerald-50 text-emerald-600"
          : "border-black/10 bg-white/70 text-ink-mute"
      } ${className}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {gpu && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        )}
        <span
          className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
            !dev
              ? "animate-pulse bg-ink-mute"
              : gpu
              ? "bg-emerald-500"
              : "bg-slate-400"
          }`}
        />
      </span>
      <Cpu className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}
