/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        trust: {
          ink: '#10212a',
          teal: '#0f766e',
          mint: '#d9f99d',
          coral: '#f97316',
          sky: '#0284c7',
        },
      },
      boxShadow: {
        panel: '0 18px 45px rgba(15, 23, 42, 0.10)',
      },
    },
  },
  plugins: [],
};
