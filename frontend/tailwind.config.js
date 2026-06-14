/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        deva: ["Noto Sans Devanagari", "Mangal", "sans-serif"],
      },
      colors: {
        ink: {
          DEFAULT: "#1d1d1f",
          soft: "#3a3a3c",
          mute: "#6e6e73",
        },
        canvas: "#fbfbfd",
        flow: "#0a84ff",
        layout: "#bf5af2",
      },
      boxShadow: {
        glass: "0 8px 40px -12px rgba(15, 23, 42, 0.18)",
        card: "0 1px 2px rgba(15,23,42,0.04), 0 12px 40px -16px rgba(15,23,42,0.20)",
        glow: "0 0 0 1px rgba(255,255,255,0.6) inset, 0 20px 60px -20px rgba(80,80,160,0.35)",
        float: "0 30px 80px -30px rgba(40, 30, 90, 0.45)",
      },
      backdropBlur: {
        xs: "2px",
      },
      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.75rem",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "gradient-pan": {
          "0%,100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        marquee: {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.8s cubic-bezier(0.16,1,0.3,1) both",
        float: "float 7s ease-in-out infinite",
        "spin-slow": "spin-slow 22s linear infinite",
        shimmer: "shimmer 2s infinite",
        "gradient-pan": "gradient-pan 8s ease infinite",
        marquee: "marquee 34s linear infinite",
      },
    },
  },
  plugins: [],
};
