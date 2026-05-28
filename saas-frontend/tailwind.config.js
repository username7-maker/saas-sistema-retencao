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
          bg: "#000000",
          surface: "#080808",
          raised: "#101010",
          ink: "#f5f5f5",
          muted: "#a1a1aa",
          cyan: "#00c8ff",
          blue: "#3b82f6",
          purple: "#8b5cf6",
        },
        pi: {
          green: "#22c55e",
          red: "#ff3b30",
          cyan: "#00c8ff",
          orange: "#f97316",
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
        heading: ["'Barlow Condensed'", "'Space Grotesk'", "sans-serif"],
        body: ["'Barlow'", "'Plus Jakarta Sans'", "sans-serif"],
        display: ["'Barlow Condensed'", "'Space Grotesk'", "sans-serif"],
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        lovable: "var(--shadow-lovable)",
        "glow-green": "0 0 20px rgba(34, 197, 94, 0.45)",
        "glow-red": "0 0 20px rgba(255, 59, 48, 0.5)",
        "glow-cyan": "0 0 20px rgba(0, 200, 255, 0.4)",
        "glow-orange": "0 0 20px rgba(249, 115, 22, 0.42)",
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
        piPulse: {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 0 0 rgba(255, 59, 48, 0.5)" },
          "50%": { opacity: "0.85", boxShadow: "0 0 0 6px rgba(255, 59, 48, 0)" },
        },
        piCountIn: {
          "0%": { opacity: "0", transform: "translateY(8px) scale(0.95)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
      },
      animation: {
        rise: "rise 0.45s ease-out",
        "pulse-glow": "pulseGlow 3.5s ease-in-out infinite",
        "pi-pulse": "piPulse 2s ease-in-out infinite",
        "pi-count-in": "piCountIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
};
