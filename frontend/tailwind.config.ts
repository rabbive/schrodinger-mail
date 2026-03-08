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
        },
        accent: {
          DEFAULT: "#0891b2",
          light: "#67e8f9",
        },
        quantum: {
          green: "#3fb950",
          red: "#f85149",
          orange: "#d29922",
          blue: "#58a6ff",
        },
      },
      fontFamily: {
        mono: [
          "SF Mono",
          "Cascadia Code",
          "Fira Code",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
