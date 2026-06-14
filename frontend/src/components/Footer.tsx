import { Github } from "./icons";

export function Footer() {
  return (
    <footer className="relative border-t border-black/5 py-14">
      <div className="section flex flex-col items-center justify-between gap-6 md:flex-row">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-flow via-[#5e5ce6] to-layout text-white">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M7 4h7c3 0 5 2 5 4.5S17 13 14 13h-3v7H7V4Z"
                fill="currentColor"
              />
            </svg>
          </span>
          <div>
            <div className="font-semibold tracking-tight">PDFlow</div>
            <div className="text-xs text-ink-mute">
              Nepali PDF → editable Word
            </div>
          </div>
        </div>

        <p className="text-center text-sm text-ink-mute">
          Built with PyMuPDF · pdf2docx · PaddleOCR — recovering real Unicode
          Devanagari.
        </p>

        <a
          href="https://github.com"
          className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/70 px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:text-ink"
        >
          <Github className="h-4 w-4" />
          Source
        </a>
      </div>
    </footer>
  );
}
