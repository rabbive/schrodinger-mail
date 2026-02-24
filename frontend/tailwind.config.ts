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
          DEFAULT: "#6c5ce7",
          light: "#a29bfe",
        },
        quantum: {
          green: "#00b894",
          red: "#e17055",
          orange: "#fdcb6e",
          blue: "#74b9ff",
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
