/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  darkMode: 'class',
  theme: { extend: {
    colors: { 'nba-blue': '#17408B', 'over-green': '#10B981', 'under-red': '#EF4444' },
    fontFamily: { sans: ['Outfit', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
  } },
  plugins: [require('@tailwindcss/forms')],
  safelist: [
    // Ensure progress bar colors are always included
    'bg-emerald-600',
    'bg-green-500',
    'bg-amber-500',
    'bg-orange-500',
    'bg-red-600',
  ],
}
