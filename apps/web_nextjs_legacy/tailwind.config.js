/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14221c",
        moss: {
          50: "#f4f7f4",
          100: "#e4eee8",
          200: "#c5ddd0",
          700: "#0f6e56",
          800: "#0b5344",
          900: "#08382e",
        },
        sun: {
          100: "#fff4d6",
          500: "#e09b12",
          700: "#8a5a08",
        },
        clay: {
          50: "#fdf2f1",
          700: "#b42318",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(20, 34, 28, 0.06), 0 8px 24px rgba(20, 34, 28, 0.04)",
      },
    },
  },
  plugins: [],
};
