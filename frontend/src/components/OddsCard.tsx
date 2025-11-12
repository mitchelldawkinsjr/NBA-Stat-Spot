type BookOdds = { book: string; over: string; under: string }

export function OddsCard({ title, color = 'blue', odds, bestOver, bestUnder }: { title: string; color?: 'blue'|'green'; odds: BookOdds[]; bestOver: string; bestUnder: string }) {
  const colorMap: Record<string, { from: string; to: string; text: string; btn: string; fromDark: string; toDark: string; textDark: string }> = {
    blue: { from: 'from-blue-50', to: 'to-blue-100', text: 'text-blue-900', btn: 'bg-blue-600', fromDark: 'dark:from-blue-900/30', toDark: 'dark:to-blue-900/40', textDark: 'dark:text-blue-200' },
    green: { from: 'from-green-50', to: 'to-green-100', text: 'text-green-900', btn: 'bg-green-600', fromDark: 'dark:from-green-900/30', toDark: 'dark:to-green-900/40', textDark: 'dark:text-green-200' },
  }
  const colors = colorMap[color]
  return (
    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden shadow-sm transition-colors duration-200">
      <div className={`bg-gradient-to-r ${colors.from} ${colors.to} ${colors.fromDark} ${colors.toDark} p-4 border-b border-gray-200 dark:border-slate-700 transition-colors duration-200`}>
        <div className={`font-semibold ${colors.text} ${colors.textDark} transition-colors duration-200`}>{title}</div>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-slate-700 transition-colors duration-200">
        {odds.map((o, i) => (
          <div key={i} className="grid grid-cols-3 p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors duration-200">
            <div className="font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">{o.book}</div>
            <div className="text-center"><span className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 font-bold px-3 py-1 rounded text-xs transition-colors duration-200">O {o.over}</span></div>
            <div className="text-center"><span className="bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-gray-300 font-bold px-3 py-1 rounded text-xs transition-colors duration-200">U {o.under}</span></div>
          </div>
        ))}
        <div className={`grid grid-cols-3 p-4 bg-gray-50 dark:bg-slate-700/50 transition-colors duration-200`}>
          <div className="font-extrabold text-gray-900 dark:text-slate-100 transition-colors duration-200">Best Odds</div>
          <div className="text-center"><span className={`${colors.btn} dark:bg-blue-500 text-white font-bold px-3 py-1 rounded text-xs transition-colors duration-200`}>O {bestOver} ⭐</span></div>
          <div className="text-center"><span className={`${colors.btn} dark:bg-blue-500 text-white font-bold px-3 py-1 rounded text-xs transition-colors duration-200`}>U {bestUnder} ⭐</span></div>
        </div>
      </div>
    </div>
  )
}


