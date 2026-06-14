import { CSSProperties } from "react";
import { PageInfo, TextElement } from "../../lib/api";

interface Props {
  page: PageInfo;
  showBoxes?: boolean;
  highlightOcr?: boolean;
  className?: string;
}

/**
 * Reconstructs a page from the analysis payload: every recovered text span is
 * drawn as a coordinate-pinned box (mirroring the DOCX layout engine output)
 * and images are placed at their original rectangles. Uses CSS container-query
 * units so text scales perfectly with the rendered width — no JS measuring.
 */
export function PageCanvas({
  page,
  showBoxes = false,
  highlightOcr = false,
  className,
}: Props) {
  const ratio = page.height ? page.width / page.height : 0.7072;

  return (
    <div
      className={`relative w-full overflow-hidden rounded-lg bg-white ${className ?? ""}`}
      style={{
        aspectRatio: `${page.width} / ${page.height}`,
        containerType: "size",
      }}
    >
      {/* Images first (background layer) */}
      {page.elements.map((el, i) =>
        el.type === "image" && el.src ? (
          <img
            key={`img-${i}`}
            src={el.src}
            alt=""
            loading="lazy"
            className="absolute"
            style={rect(el.bbox)}
          />
        ) : null
      )}

      {/* Text boxes */}
      {page.elements.map((el, i) =>
        el.type === "text" ? (
          <span
            key={`txt-${i}`}
            className={`absolute leading-tight ${el.ocr ? "font-deva" : ""}`}
            style={textStyle(el, showBoxes, highlightOcr)}
            title={
              el.ocr && el.score != null
                ? `OCR · ${(el.score * 100).toFixed(0)}% confidence`
                : undefined
            }
          >
            {el.text}
          </span>
        ) : null
      )}

      {/* aspect spacer guard for very tall pages */}
      <span className="sr-only">{ratio}</span>
    </div>
  );
}

function rect(b: [number, number, number, number]): CSSProperties {
  return {
    left: `${b[0] * 100}%`,
    top: `${b[1] * 100}%`,
    width: `${(b[2] - b[0]) * 100}%`,
    height: `${(b[3] - b[1]) * 100}%`,
    objectFit: "fill",
  };
}

function textStyle(
  el: TextElement,
  showBoxes: boolean,
  highlightOcr: boolean
): CSSProperties {
  const b = el.bbox;
  const ocrTint = highlightOcr && el.ocr;
  return {
    left: `${b[0] * 100}%`,
    top: `${b[1] * 100}%`,
    width: `${Math.max(b[2] - b[0], 0.01) * 100}%`,
    height: `${Math.max(b[3] - b[1], 0.005) * 100}%`,
    // container-query height unit: 1cqh == 1% of the canvas height.
    fontSize: `calc(${el.size} * 100cqh)`,
    color: el.color || "#1d1d1f",
    fontWeight: el.bold ? 700 : 400,
    fontStyle: el.italic ? "italic" : "normal",
    whiteSpace: "nowrap",
    display: "flex",
    alignItems: "center",
    overflow: "visible",
    background: ocrTint
      ? "rgba(191,90,242,0.12)"
      : showBoxes
      ? "rgba(10,132,255,0.05)"
      : "transparent",
    outline: showBoxes
      ? "1px solid rgba(10,132,255,0.35)"
      : ocrTint
      ? "1px solid rgba(191,90,242,0.35)"
      : "none",
    borderRadius: showBoxes || ocrTint ? "2px" : undefined,
  };
}
