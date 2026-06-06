import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        war: {
          bg: "#0a0f1a",
          panel: "#111827",
          border: "#1f2937",
          accent: "#22d3ee",
          danger: "#f87171",
          warn: "#fbbf24",
          ok: "#34d399",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
