import { Reveal, SectionHeading } from "./ui/Reveal";
import { Languages, Scan, Image, Table } from "./icons";

const FAILURES = [
  {
    icon: Languages,
    title: "Legacy & CID fonts",
    body: "Preeti, Kantipur and subset-embedded Mangal render fine on screen but extract as Latin mojibake — your Nepali becomes nonsense.",
    demo: (
      <span>
        <code className="text-red-400">g]kfn ;/sf/</code>
        <span className="mx-2 text-ink-mute">→ usually stays</span>
        <code className="text-red-400">g]kfn ;/sf/</code>
      </span>
    ),
    tint: "from-rose-100/60",
  },
  {
    icon: Scan,
    title: "Scanned pages",
    body: "A photographed or scanned document is just an image. Converters embed the picture and hand you zero editable, selectable text.",
    demo: <span className="text-ink-mute">image in → image out, not a word editable</span>,
    tint: "from-amber-100/60",
  },
  {
    icon: Image,
    title: "Text trapped in images",
    body: "Banners, stamps and flattened instruction blocks bake text into pixels. Standard tools never look inside them.",
    demo: <span className="text-ink-mute">paragraphs locked inside graphics</span>,
    tint: "from-sky-100/60",
  },
  {
    icon: Table,
    title: "Collapsed structure",
    body: "Tables, label/value columns and alignment flatten to a single left-aligned stream — the layout you needed is gone.",
    demo: <span className="text-ink-mute">columns &amp; tables → one ragged column</span>,
    tint: "from-violet-100/60",
  },
];

export function ProblemSection() {
  return (
    <section id="why" className="relative py-24 md:py-32">
      <div className="section">
        <SectionHeading
          eyebrow="The problem"
          title={
            <>
              Why ordinary converters{" "}
              <span className="text-gradient">break Nepali documents</span>
            </>
          }
          sub="Devanagari, legacy encodings and scans defeat tools built for clean English PDFs. Four failures show up again and again."
        />

        <div className="mt-16 grid gap-5 sm:grid-cols-2">
          {FAILURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.08}>
              <div className="group relative h-full overflow-hidden rounded-3xl border border-black/5 bg-white p-7 shadow-card transition-all duration-500 hover:-translate-y-1 hover:shadow-glass">
                <div
                  className={`pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br ${f.tint} to-transparent opacity-70 blur-2xl transition-opacity duration-500 group-hover:opacity-100`}
                />
                <div className="relative">
                  <div className="mb-5 grid h-12 w-12 place-items-center rounded-2xl bg-ink/5 text-ink">
                    <f.icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-xl font-semibold tracking-tight">
                    {f.title}
                  </h3>
                  <p className="mt-3 leading-relaxed text-ink-mute">{f.body}</p>
                  <div className="mt-5 rounded-xl border border-black/5 bg-canvas px-4 py-3 font-mono text-sm">
                    {f.demo}
                  </div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
