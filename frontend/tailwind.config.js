/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#F5F3F0",
        surface: "#FFFFFF",
        card: "#FFFFFF",
        primary: "#3D3048",
        secondary: "#766080",
        accent: "#766080",
        lavender: "#E9E1EC",
        success: "#3E7C68",
        warning: "#B98532",
        danger: "#A6535B",
        ink: "#242329",
        muted: "#6F6B75",
        border: "#E4E0E5",
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 3px rgba(61, 48, 72, 0.06), 0 4px 16px rgba(61, 48, 72, 0.04)",
        glow: "0 1px 3px rgba(61, 48, 72, 0.06), 0 4px 16px rgba(61, 48, 72, 0.04)",
      },
    },
  },
  plugins: [],
};
