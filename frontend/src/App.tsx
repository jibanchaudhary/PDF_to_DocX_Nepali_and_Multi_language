import { useEffect, useRef } from "react";
import Lenis from "lenis";
import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { ProblemSection } from "./components/ProblemSection";
import { DualEngine } from "./components/DualEngine";
import { HowItWorks } from "./components/HowItWorks";
import { Converter } from "./components/converter/Converter";
import { Footer } from "./components/Footer";

export default function App() {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.15,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });
    lenisRef.current = lenis;

    let raf = 0;
    const loop = (time: number) => {
      lenis.raf(time);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    // Smooth in-page anchor navigation.
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement).closest('a[href^="#"]');
      if (!a) return;
      const id = a.getAttribute("href");
      if (!id || id === "#") return;
      const el = document.querySelector(id);
      if (el) {
        e.preventDefault();
        lenis.scrollTo(el as HTMLElement, { offset: -16 });
      }
    };
    document.addEventListener("click", onClick);

    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("click", onClick);
      lenis.destroy();
    };
  }, []);

  const scrollToConvert = () => {
    const el = document.getElementById("convert");
    if (el) lenisRef.current?.scrollTo(el, { offset: -16 });
  };

  return (
    <div className="relative">
      <Nav onConvert={scrollToConvert} />
      <main>
        <Hero onConvert={scrollToConvert} />
        <ProblemSection />
        <DualEngine />
        <HowItWorks />
        <Converter />
      </main>
      <Footer />
    </div>
  );
}
