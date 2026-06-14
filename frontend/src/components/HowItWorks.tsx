import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { SectionHeading } from "./ui/Reveal";
import { FileText, Cpu, Languages, FileWord } from "./icons";

const STEPS = [
  {
    n: "01",
    icon: FileText,
    title: "Parse",
    body: "PyMuPDF reads every page into positioned elements — text spans with font, size and colour; images; and tables — flagging legacy-font spans and scanned pages.",
  },
  {
    n: "02",
    icon: Cpu,
    title: "Route",
    body: "A single decision: any scan or undecodable Devanagari sends the page to the layout engine; clean pages take the fast flow path.",
  },
  {
    n: "03",
    icon: Languages,
    title: "Recover",
    body: "PaddleOCR re-reads garbled regions, images and full scans, restoring real, editable Unicode Devanagari with per-span confidence.",
  },
  {
    n: "04",
    icon: FileWord,
    title: "Rebuild",
    body: "Each page is reconstructed in Word — sized to the original, images anchored, every span pinned to its coordinates as an editable text box.",
  },
];

const ease = [0.16, 1, 0.3, 1] as const;

export function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start center", "end center"],
  });
  const lineScale = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <section id="how" className="relative py-24 md:py-32">
      <div className="section">
        <SectionHeading
          eyebrow="How it works"
          title={
            <>
              Four stages, from{" "}
              <span className="text-gradient">PDF to editable Word</span>
            </>
          }
          sub="Parse, route, recover, rebuild — the same orchestrator that powers the PDFlow command line."
        />

        <div ref={ref} className="relative mt-16">
          {/* Progress spine (desktop) */}
          <div className="absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 bg-black/5 lg:block">
            <motion.div
              style={{ scaleY: lineScale }}
              className="h-full w-full origin-top bg-gradient-to-b from-flow via-[#5e5ce6] to-layout"
            />
          </div>

          <div className="space-y-6 lg:space-y-0">
            {STEPS.map((s, i) => {
              const left = i % 2 === 0;
              return (
                <div
                  key={s.n}
                  className="relative lg:grid lg:grid-cols-2 lg:gap-12"
                >
                  <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-60px" }}
                    transition={{ duration: 0.7, ease }}
                    className={`lg:py-10 ${
                      left ? "" : "lg:col-start-2"
                    }`}
                  >
                    <div className="group relative overflow-hidden rounded-3xl border border-black/5 bg-white p-7 shadow-card transition-all duration-500 hover:shadow-glass">
                      <div className="flex items-center gap-4">
                        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-flow/10 to-layout/10 text-ink">
                          <s.icon className="h-6 w-6" />
                        </div>
                        <span className="font-mono text-3xl font-semibold text-black/10">
                          {s.n}
                        </span>
                      </div>
                      <h3 className="mt-5 text-2xl font-semibold tracking-tight">
                        {s.title}
                      </h3>
                      <p className="mt-3 leading-relaxed text-ink-mute">
                        {s.body}
                      </p>
                    </div>
                  </motion.div>

                  {/* Spine node */}
                  <div className="absolute left-1/2 top-1/2 hidden h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-gradient-to-br from-flow to-layout shadow-md lg:block" />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
