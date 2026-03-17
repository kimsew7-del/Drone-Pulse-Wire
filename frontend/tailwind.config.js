/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: '#f4f1eb', 2: '#fffaf4' },
        panel: 'rgba(255, 250, 244, 0.92)',
        card: '#ffffff',
        line: 'rgba(53, 40, 31, 0.08)',
        text: '#201913',
        muted: '#766657',
        accent: { DEFAULT: '#ff6b2c', 2: '#ffbf69', 3: '#ff8fab' },
        ok: '#22c55e',
        warn: '#f59e0b',
        danger: '#ef4444',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['Instrument Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
