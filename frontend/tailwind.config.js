/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        occupied: '#ef4444',
        cleaning: '#eab308',
        available: '#22c55e',
        reserved: '#3b82f6',
      },
    },
  },
  plugins: [],
};
