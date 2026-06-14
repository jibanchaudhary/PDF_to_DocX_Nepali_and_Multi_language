import { motion } from "framer-motion";
import { Reveal, SectionHeading } from "./ui/Reveal";
import { Bolt, Layers, Check, Cpu } from "./icons";

const ease = [0.16, 1, 0.3, 1] as const;

const ENGINES = [
  {
    key: "flow",
    name: "flow engine",
    icon: Bolt,
    accent: "text-flow",
    ring: "ring-flow/30",
    glow: "from-flow/15",
    tagline: "Clean digital PDFs",
    desc: "When every page has a decodable text layer, PDFlow takes the fast path and delegates to pdf2docx for reflowable Word output.",
    points: [
      "Reflowable paragraphs & headings",
      "Native, editable Word tables",
      "Embedded images preserved",
      "Millisecond-fast, faithful styling",
    ],
  },
  {
    key: "layout",
    name: "layout engine",
    icon: Layers,
    accent: "text-layout",
    ring: "ring-layout/30",
    glow: "from-layout/15",
    tagline: "Scanned · legacy · image text",
    desc: "When Nepali can't be trusted, PDFlow rebuilds the page: PaddleOCR recovers Unicode Devanagari and every element becomes a coordinate-pinned, editable text box.",
    points: [
      "OCR-recovered Unicode Devanagari",
      "Legacy/CID font regions re-read",
      "Text rescued from inside images",
      "Original positions & layout kept",
    ],
  },
];

export function DualEngine() {
  return (
    <section id="engines" className="relative py-24 md:py-32">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white via-canvas to-white" />
      <div className="section relative">
        <SectionHeading
          eyebrow="Dual-engine architecture"
          title={
            <>
              One pipeline,{" "}
              <span className="text-gradient">two specialised engines</span>
            </>
          }
          sub="Every PDF is analysed and routed automatically — you never have to choose."
        />

        <div className="mt-16 grid gap-6 lg:grid-cols-2">
          {ENGINES.map((e, i) => (
            <Reveal key={e.key} delay={i * 0.1}>
              <div
                className={`group relative h-full overflow-hidden rounded-4xl border border-black/5 bg-white p-8 shadow-card ring-1 ${e.ring} transition-all duration-500 hover:-translate-y-1.5 hover:shadow-float md:p-10`}
              >
                <div
                  className={`pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-gradient-to-br ${e.glow} to-transparent opacity-80 blur-3xl`}
                />
                <div className="relative">
                  <div className="flex items-center gap-3">
                    <div
                      className={`grid h-12 w-12 place-items-center rounded-2xl bg-ink/5 ${e.accent}`}
                    >
                      <e.icon className="h-6 w-6" />
                    </div>
                    <div>
                      <div className="font-mono text-sm text-ink-mute">
                        {e.tagline}
                      </div>
                      <h3 className="text-2xl font-semibold tracking-tight">
                        {e.name}
                      </h3>
                    </div>
                  </div>

                  <p className="mt-6 text-[17px] leading-relaxed text-ink-soft">
                    {e.desc}
                  </p>

                  <ul className="mt-7 space-y-3">
                    {e.points.map((p) => (
                      <li key={p} className="flex items-start gap-3">
                        <span
                          className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-ink/5 ${e.accent}`}
                        >
                          <Check className="h-3.5 w-3.5" />
                        </span>
                        <span className="text-ink-soft">{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        {/* Router strip */}
        <Reveal delay={0.1}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease }}
            className="mx-auto mt-10 flex max-w-3xl flex-col items-center gap-4 rounded-3xl border border-black/5 bg-white/70 px-6 py-6 text-center shadow-card backdrop-blur md:flex-row md:text-left"
          >
            <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-flow to-layout text-white">
              <Cpu className="h-6 w-6" />
            </div>
            <p className="text-ink-soft">
              <span className="font-semibold text-ink">Automatic routing.</span>{" "}
              PDFlow inspects every page — any scan or undecodable Nepali span
              sends the document to <span className="text-layout font-medium">layout</span>;
              otherwise it stays on the fast{" "}
              <span className="text-flow font-medium">flow</span> path.
            </p>
          </motion.div>
        </Reveal>
      </div>
    </section>
  );
}
