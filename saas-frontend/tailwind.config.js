/** @type {import('tailwindcss').Config} */
export default {
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
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'Plus Jakarta Sans'", "sans-serif"],
      },
      boxShadow: {
        panel: "0 15px 35px -20px rgba(17, 103, 86, 0.35)",
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
