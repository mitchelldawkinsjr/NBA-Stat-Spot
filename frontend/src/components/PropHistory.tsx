export function PropHistoryRow({ prop, hitRateText, last5, marginText, trend }: { prop: string; hitRateText: string; last5: boolean[]; marginText: string; trend: 'Hot'|'Neutral'|'Cold'|'Fire' }) {
  const colorMap: Record<string, { bg: string; text: string; hit: string; bgDark: string; textDark: string; hitDark: string }> = {
    Hot: { bg: 'bg-green-100', text: 'text-green-800', hit: 'text-green-600', bgDark: 'dark:bg-green-900/30', textDark: 'dark:text-green-300', hitDark: 'dark:text-green-400' },
    Fire: { bg: 'bg-green-100', text: 'text-green-800', hit: 'text-green-600', bgDark: 'dark:bg-green-900/30', textDark: 'dark:text-green-300', hitDark: 'dark:text-green-400' },
    Neutral: { bg: 'bg-yellow-100', text: 'text-yellow-800', hit: 'text-yellow-600', bgDark: 'dark:bg-yellow-900/30', textDark: 'dark:text-yellow-300', hitDark: 'dark:text-yellow-400' },
    Cold: { bg: 'bg-red-100', text: 'text-red-800', hit: 'text-red-600', bgDark: 'dark:bg-red-900/30', textDark: 'dark:text-red-300', hitDark: 'dark:text-red-400' },
  }
  const colors = colorMap[trend]
  return (
    <div className="grid grid-cols-5 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors duration-200">
      <div className="p-3 font-semibold text-gray-800 dark:text-slate-100 border-r border-gray-100 dark:border-slate-700 transition-colors duration-200">{prop}</div>
      <div className="p-3 border-r border-gray-100 dark:border-slate-700 transition-colors duration-200">
        <span className={`font-bold ${colors.hit} ${colors.hitDark} transition-colors duration-200`}>{hitRateText}</span>
      </div>
      <div className="p-3 border-r border-gray-100 dark:border-slate-700 transition-colors duration-200">
        <div className="flex gap-1.5">
          {last5.map((h, i) => (
            <span key={i} className={`w-6 h-6 ${h ? 'bg-green-500 dark:bg-green-600' : 'bg-red-500 dark:bg-red-600'} rounded text-white text-[10px] flex items-center justify-center font-bold transition-colors duration-200`}>{h ? '✓' : '✗'}</span>
          ))}
        </div>
      </div>
      <div className="p-3 border-r border-gray-100 dark:border-slate-700 transition-colors duration-200">
        <span className="font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">{marginText}</span>
      </div>
      <div className="p-3">
        <span className={`${colors.bg} ${colors.bgDark} ${colors.text} ${colors.textDark} text-xs font-bold px-3 py-1 rounded-full inline-block transition-colors duration-200`}>{trend}</span>
      </div>
    </div>
  )
}


