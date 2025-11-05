type BookOdds = { book: string; over: string; under: string }

export function OddsCard({ title, color = 'blue', odds, bestOver, bestUnder }: { title: string; color?: 'blue'|'green'; odds: BookOdds[]; bestOver: string; bestUnder: string }) {
  const colorMap: Record<string, { from: string; to: string; text: string; btn: string }> = {
    blue: { from: 'from-blue-50', to: 'to-blue-100', text: 'text-blue-900', btn: 'bg-blue-600' },
    green: { from: 'from-green-50', to: 'to-green-100', text: 'text-green-900', btn: 'bg-green-600' },
  }
  const colors = colorMap[color]
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
      <div className={`bg-gradient-to-r ${colors.from} ${colors.to} p-4 border-b border-gray-200`}>
        <div className={`font-semibold ${colors.text}`}>{title}</div>
      </div>
      <div className="divide-y divide-gray-100">
        {odds.map((o, i) => (
          <div key={i} className="grid grid-cols-3 p-4 hover:bg-gray-50">
            <div className="font-semibold text-gray-800">{o.book}</div>
            <div className="text-center"><span className="bg-green-100 text-green-800 font-bold px-3 py-1 rounded text-xs">O {o.over}</span></div>
            <div className="text-center"><span className="bg-gray-100 text-gray-800 font-bold px-3 py-1 rounded text-xs">U {o.under}</span></div>
          </div>
        ))}
        <div className={`grid grid-cols-3 p-4 bg-gray-50`}>
          <div className="font-extrabold text-gray-900">Best Odds</div>
          <div className="text-center"><span className={`${colors.btn} text-white font-bold px-3 py-1 rounded text-xs`}>O {bestOver} ⭐</span></div>
          <div className="text-center"><span className={`${colors.btn} text-white font-bold px-3 py-1 rounded text-xs`}>U {bestUnder} ⭐</span></div>
        </div>
      </div>
    </div>
  )
}


