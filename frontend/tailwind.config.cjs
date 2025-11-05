/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}', './node_modules/flowbite/**/*.js'],
  theme: { extend: {
    colors: { 'nba-blue': '#17408B', 'over-green': '#10B981', 'under-red': '#EF4444' }
  } },
  plugins: [require('flowbite/plugin')],
}
