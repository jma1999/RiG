/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nexus: {
          900: '#0d0d0d',
          950: '#050505',
          800: '#141419',
          700: '#1e1e26',
          600: '#2d2d3a',
          accent: '#00f0ff',
          success: '#00ff9d',
          warning: '#ffb020',
          danger: '#ff4d4d',
        },
      },
    },
  },
  plugins: [],
}

