/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0c1210",
          900: "#121a17",
          800: "#1a2621",
          700: "#243530",
        },
        fuel: {
          400: "#6bbf8a",
          500: "#3d9b63",
          600: "#2f7a4d",
        },
        amber: {
          signal: "#d4a24c",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        body: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
