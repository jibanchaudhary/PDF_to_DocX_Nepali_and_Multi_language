import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ArrowRight, Sparkles, Bolt, Scan } from "./icons";

const ease = [0.16, 1, 0.3, 1] as const;

export function Hero({ onConvert }: { onConvert: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const visualY = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const visualScale = useTransform(scrollYProgress, [0, 1], [1, 0.94]);
  const visualOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0.3]);

  return (
    <section
      id="top"
      ref={ref}
      className="relative overflow-hidden pb-24 pt-36 md:pb-32 md:pt-44"
    >
      {/* Ambient background */}
      <div className="pointer-events-none absolute inset-0 bloom" />
      <div className="pointer-events-none absolute inset-0 grid-faint mask-fade-b opacity-60" />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -left-32 top-10 h-96 w-96 rounded-full bg-flow/20 blur-3xl"
        animate={{ y: [0, 30, 0], x: [0, 20, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-24 top-32 h-80 w-80 rounded-full bg-layout/20 blur-3xl"
        animate={{ y: [0, -26, 0], x: [0, -16, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="section relative">
        <div className="mx-auto max-w-3xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease }}
          >
            <span className="pill">
              <Sparkles className="h-4 w-4 text-layout" />
              Nepali Document AI · PDF → editable Word
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.08, ease }}
            className="h-display mt-7 text-balance text-[clamp(2.6rem,7vw,5.2rem)]"
          >
            Nepali PDFs, reborn as
            <br />
            <span className="text-gradient">truly editable Word.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.16, ease }}
            className="mx-auto mt-7 max-w-xl text-balance text-lg leading-relaxed text-ink-mute md:text-xl"
          >
            Legacy fonts, scanned pages and image-baked text turn to garbage in
            ordinary converters. PDFlow recovers real Unicode Devanagari and
            rebuilds every page — structure, tables and layout intact.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.24, ease }}
            className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <button onClick={onConvert} className="btn-primary group">
              Convert your PDF
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>
            <a href="#how" className="btn-ghost">
              See how it works
            </a>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.4 }}
            className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-ink-mute"
          >
            <span className="inline-flex items-center gap-1.5">
              <Bolt className="h-4 w-4 text-flow" /> Auto engine routing
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Scan className="h-4 w-4 text-layout" /> Scanned & legacy fonts
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-[#5e5ce6]" /> One-click .docx
            </span>
          </motion.div>
        </div>

        <motion.div
          style={{ y: visualY, scale: visualScale, opacity: visualOpacity }}
          className="mx-auto mt-16 max-w-4xl"
        >
          <TransformShowcase />
        </motion.div>
      </div>
    </section>
  );
}

/** Animated before→after: garbled legacy extraction becomes clean Devanagari. */
function TransformShowcase() {
  const rows = [
    { before: "g]kfn ;/sf/", after: "नेपाल सरकार" },
    { before: ":yfgLo tx", after: "स्थानीय तह" },
    { before: "k|df0fkq", after: "प्रमाणपत्र" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, delay: 0.3, ease }}
      className="glass rounded-4xl p-3 shadow-float"
    >
      <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr]">
        {/* Before */}
        <div className="rounded-3xl border border-black/5 bg-white/70 p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-widest text-ink-mute">
              Ordinary converter
            </span>
            <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-500">
              garbled
            </span>
          </div>
          <div className="space-y-3">
            {rows.map((r) => (
              <div
                key={r.before}
                className="rounded-lg bg-red-50/50 px-3 py-2 font-mono text-[15px] text-red-400/90 line-through decoration-red-300"
              >
                {r.before}
              </div>
            ))}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex items-center justify-center">
          <motion.div
            className="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-flow to-layout text-white shadow-glow"
            animate={{ scale: [1, 1.08, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          >
            <ArrowRight className="h-5 w-5" />
          </motion.div>
        </div>

        {/* After */}
        <div className="rounded-3xl border border-black/5 bg-gradient-to-br from-white to-indigo-50/40 p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-widest text-ink-mute">
              PDFlow output
            </span>
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-600">
              editable Unicode
            </span>
          </div>
          <div className="space-y-3">
            {rows.map((r, i) => (
              <motion.div
                key={r.after}
                initial={{ opacity: 0, x: -8 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 + i * 0.15, duration: 0.6, ease }}
                className="rounded-lg bg-white px-3 py-2 font-deva text-[17px] text-ink shadow-sm"
              >
                {r.after}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
