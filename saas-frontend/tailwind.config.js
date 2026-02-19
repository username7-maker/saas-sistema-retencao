/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eefbf7",
          100: "#d6f5eb",
          300: "#7bdcbf",
          500: "#1d9a7f",
          700: "#116756",
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
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'Plus Jakarta Sans'", "sans-serif"],
        display: ["'Space Grotesk'", "sans-serif"],
      },
      boxShadow: {
        panel: "0 15px 35px -20px rgba(17, 103, 86, 0.35)",
        lovable: "0 16px 40px -24px rgba(9, 30, 28, 0.35)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 0.45s ease-out",
      },
    },
  },
  plugins: [],
};
