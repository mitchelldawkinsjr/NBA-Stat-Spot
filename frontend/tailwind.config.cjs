/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Kinetic Performance Ledger – full surface hierarchy
        'background':                '#131313',
        'surface':                   '#131313',
        'surface-dim':               '#131313',
        'surface-container-lowest':  '#0e0e0e',
        'surface-container-low':     '#1c1b1b',
        'surface-container':         '#201f1f',
        'surface-container-high':    '#2a2a2a',
        'surface-container-highest': '#353534',
        'surface-variant':           '#353534',
        'surface-bright':            '#393939',
        // Primary – Hoop Orange
        'primary':                   '#ffb693',
        'primary-container':         '#ff6b00',
        'primary-fixed':             '#ffdbcc',
        'primary-fixed-dim':         '#ffb693',
        'on-primary':                '#561f00',
        'on-primary-container':      '#572000',
        'on-primary-fixed':          '#351000',
        'on-primary-fixed-variant':  '#7a3000',
        'inverse-primary':           '#a04100',
        // Secondary – Stat Blue
        'secondary':                 '#adc7ff',
        'secondary-container':       '#4a8eff',
        'secondary-fixed':           '#d8e2ff',
        'secondary-fixed-dim':       '#adc7ff',
        'on-secondary':              '#002e68',
        'on-secondary-container':    '#00285b',
        'on-secondary-fixed':        '#001a41',
        'on-secondary-fixed-variant':'#004493',
        // Tertiary – Live Blue
        'tertiary':                  '#9ccaff',
        'tertiary-container':        '#059eff',
        'tertiary-fixed':            '#d0e4ff',
        'tertiary-fixed-dim':        '#9ccaff',
        'on-tertiary':               '#003257',
        'on-tertiary-container':     '#003357',
        'on-tertiary-fixed':         '#001d35',
        'on-tertiary-fixed-variant': '#00497b',
        // Error – Betting Red
        'error':                     '#ffb4ab',
        'error-container':           '#93000a',
        'on-error':                  '#690005',
        'on-error-container':        '#ffdad6',
        // Neutral surfaces
        'on-surface':                '#e5e2e1',
        'on-surface-variant':        '#e2bfb0',
        'on-background':             '#e5e2e1',
        'inverse-surface':           '#e5e2e1',
        'inverse-on-surface':        '#313030',
        // Outline
        'outline':                   '#a98a7d',
        'outline-variant':           '#5a4136',
        // Tint
        'surface-tint':              '#ffb693',
        // Semantic aliases used in components
        'betting-green':             '#4edea3',
        'betting-red':               '#ff5252',
        // Legacy aliases kept for backward-compat with old component classes
        'nba-blue':                  '#17408B',
        'over-green':                '#4edea3',
        'under-red':                 '#ff5252',
      },
      fontFamily: {
        sans:     ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        headline: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        body:     ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        label:    ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        sm:      '0.125rem',
        md:      '0.25rem',
        lg:      '0.25rem',
        xl:      '0.5rem',
        '2xl':   '0.5rem',
        full:    '0.75rem',
      },
      keyframes: {
        marquee: {
          '0%':   { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        shimmer: {
          '0%':   { transform: 'translateX(-100%) skewX(-15deg)' },
          '100%': { transform: 'translateX(200%) skewX(-15deg)' },
        },
        progress: {
          '0%':   { transform: 'translateX(-100%)', width: '30%' },
          '50%':  { transform: 'translateX(0%)',    width: '100%' },
          '100%': { transform: 'translateX(100%)',  width: '30%' },
        },
      },
      animation: {
        marquee:  'marquee 30s linear infinite',
        shimmer:  'shimmer 2s ease-in-out infinite',
        progress: 'progress 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
  safelist: [
    // Confidence/tier bar colors
    'bg-betting-green', 'bg-betting-red',
    'bg-primary-container', 'bg-secondary-container', 'bg-tertiary-container',
    'bg-error-container',
    'text-betting-green', 'text-betting-red',
    'text-primary-container', 'text-secondary-container',
    'w-[82%]', 'w-[75%]', 'w-[69%]', 'w-[65%]', 'w-[58%]', 'w-[50%]',
    'w-[90%]', 'w-[80%]', 'w-[70%]', 'w-[60%]', 'w-[40%]', 'w-[30%]',
    'w-[92%]', 'w-[78%]', 'w-[74%]', 'w-[71%]',
  ],
}
