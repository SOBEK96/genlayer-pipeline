/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Deep, layered dark base
        base: {
          900: "#05060d",
          800: "#0a0c18",
          700: "#111427",
          600: "#181c33",
          500: "#222746",
        },
        // Ambient accents
        accent: {
          cyan: "#38e1ff",
          violet: "#9b6bff",
          magenta: "#ff5cf4",
          lime: "#7cf67c",
        },
        status: {
          accepted: "#37f5a3",
          pending: "#ffcf5c",
          rejected: "#ff6b6b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 30px -8px rgba(56,225,255,0.45)",
        "glow-violet": "0 0 34px -8px rgba(155,107,255,0.5)",
        card: "0 20px 60px -20px rgba(0,0,0,0.8), inset 0 1px 0 0 rgba(255,255,255,0.06)",
        float: "0 30px 80px -30px rgba(0,0,0,0.9)",
      },
      backdropBlur: { xs: "2px" },
      keyframes: {
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "glow-pulse": {
          "0%,100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "spin-slow": { to: { transform: "rotate(360deg)" } },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "glow-pulse": "glow-pulse 4s ease-in-out infinite",
        shimmer: "shimmer 1.8s linear infinite",
        "spin-slow": "spin-slow 3s linear infinite",
      },
    },
  },
  plugins: [],
};
