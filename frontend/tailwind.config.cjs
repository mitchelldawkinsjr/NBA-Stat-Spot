/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: { extend: {
    colors: { 'nba-blue': '#17408B', 'over-green': '#10B981', 'under-red': '#EF4444' }
  } },
  plugins: [],
}
