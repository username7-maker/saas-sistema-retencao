/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff7ec",
          100: "#ffe7cc",
          300: "#ffc078",
          500: "#f58a1b",
          700: "#b66100",
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
        },
      },
      fontFamily: {
        heading:  ["'Barlow Condensed'", "'Space Grotesk'", "sans-serif"],
        display:  ["'Barlow Condensed'", "'Space Grotesk'", "sans-serif"],
        body:     ["'Barlow'", "'Plus Jakarta Sans'", "sans-serif"],
      },
      colors: {
        pi: {
          green:  "#22c55e",
          red:    "#ff3b30",
          cyan:   "#00c8ff",
          orange: "#f97316",
        },
      },
      boxShadow: {
        panel:       "0 16px 40px -24px rgba(245, 138, 27, 0.28)",
        lovable:     "0 16px 40px -24px rgba(15, 15, 15, 0.45)",
        "glow-green": "0 0 20px rgba(34, 197, 94, 0.45)",
        "glow-red":   "0 0 20px rgba(255, 59, 48, 0.5)",
        "glow-cyan":  "0 0 20px rgba(0, 200, 255, 0.4)",
      },
      keyframes: {
        rise: {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pi-pulse": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 0 0 rgba(255,59,48,0.5)" },
          "50%":      { opacity: "0.85", boxShadow: "0 0 0 6px rgba(255,59,48,0)" },
        },
        "pi-count-in": {
          from: { opacity: "0", transform: "translateY(8px) scale(0.95)" },
          to:   { opacity: "1", transform: "translateY(0) scale(1)" },
        },
      },
      animation: {
        rise:         "rise 0.45s ease-out",
        "pi-pulse":   "pi-pulse 2s ease-in-out infinite",
        "pi-count-in":"pi-count-in 0.4s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
};
