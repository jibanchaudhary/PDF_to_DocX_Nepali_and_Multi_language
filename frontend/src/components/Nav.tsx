import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "./icons";
import { DeviceBadge } from "./DeviceBadge";

const LINKS = [
  { id: "why", label: "Why PDFlow" },
  { id: "engines", label: "Dual engine" },
  { id: "how", label: "How it works" },
  { id: "convert", label: "Convert" },
];

function Logo() {
  return (
    <a href="#top" className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-flow via-[#5e5ce6] to-layout text-white shadow-md">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M7 4h7c3 0 5 2 5 4.5S17 13 14 13h-3v7H7V4Z"
            fill="currentColor"
          />
        </svg>
      </span>
      <span className="text-[17px] font-semibold tracking-tight">PDFlow</span>
    </a>
  );
}

export function Nav({ onConvert }: { onConvert: () => void }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-3"
    >
      <nav
        className={`flex w-full max-w-[1180px] items-center justify-between rounded-full px-4 py-2.5 transition-all duration-500 md:px-5 ${
          scrolled
            ? "glass shadow-glass"
            : "border border-transparent bg-white/0"
        }`}
      >
        <Logo />
        <div className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <a
              key={l.id}
              href={`#${l.id}`}
              className="rounded-full px-4 py-2 text-[14px] font-medium text-ink-soft transition-colors hover:text-ink"
            >
              {l.label}
            </a>
          ))}
        </div>
        <div className="flex items-center gap-2.5">
          <DeviceBadge />
          <button
            onClick={onConvert}
            className="group inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-[14px] font-semibold text-white transition-all hover:bg-black active:scale-95"
          >
            Convert a PDF
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>
      </nav>
    </motion.header>
  );
}
