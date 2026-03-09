import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "var(--surface)",
          secondary: "var(--surface2)",
          tertiary: "var(--surface3)",
        },
        accent: {
          DEFAULT: "#4493f8",
          light: "#79c0ff",
        },
        quantum: {
          green: "#3fb950",
          red: "#f85149",
          orange: "#d29922",
          blue: "#58a6ff",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "SF Mono",
          "Cascadia Code",
          "Fira Code",
          "Consolas",
          "monospace",
        ],
      },
      borderRadius: {
        DEFAULT: "6px",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "fade-slide": "fadeSlideIn 0.3s ease-out",
        "pulse-gentle": "pulse-gentle 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
