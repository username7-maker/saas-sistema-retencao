/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f4f2ec",
          100: "#dceaf1",
          300: "#9bc9df",
          500: "#6fa7c7",
          700: "#2f6f91",
          900: "#05080d",
        },
        command: {
          bg: "#05080d",
          surface: "#0b1118",
          raised: "#0f1720",
          ink: "#e5edf5",
          muted: "#8b9bad",
          cyan: "#38bdf8",
          blue: "#3b82f6",
          purple: "#8b5cf6",
        },
        lovable: {
          bg: "hsl(var(--lovable-bg))",
          "bg-muted": "hsl(var(--lovable-bg-muted))",
          surface: "hsl(var(--lovable-surface))",
          "surface-soft": "hsl(var(--lovable-surface-soft))",
          border: "hsl(var(--lovable-border))",
          "border-strong": "hsl(var(--lovable-border-strong))",
          ink: "hsl(var(--lovable-ink))",
          "ink-muted": "hsl(var(--lovable-ink-muted))",
          primary: "hsl(var(--lovable-primary))",
          "primary-soft": "hsl(var(--lovable-primary-soft))",
          success: "hsl(var(--lovable-success))",
          warning: "hsl(var(--lovable-warning))",
          danger: "hsl(var(--lovable-danger))",
          ai: "hsl(var(--lovable-ai))",
        },
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'Plus Jakarta Sans'", "sans-serif"],
        display: ["'Space Grotesk'", "sans-serif"],
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        lovable: "var(--shadow-lovable)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: "0.72", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.03)" },
        },
      },
      animation: {
        rise: "rise 0.45s ease-out",
        "pulse-glow": "pulseGlow 3.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
