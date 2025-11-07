export function PropHistoryRow({ prop, hitRateText, last5, marginText, trend }: { prop: string; hitRateText: string; last5: boolean[]; marginText: string; trend: 'Hot'|'Neutral'|'Cold'|'Fire' }) {
  const colorMap: Record<string, { bg: string; text: string; hit: string }> = {
    Hot: { bg: 'bg-green-100', text: 'text-green-800', hit: 'text-green-600' },
    Fire: { bg: 'bg-green-100', text: 'text-green-800', hit: 'text-green-600' },
    Neutral: { bg: 'bg-yellow-100', text: 'text-yellow-800', hit: 'text-yellow-600' },
    Cold: { bg: 'bg-red-100', text: 'text-red-800', hit: 'text-red-600' },
  }
  const colors = colorMap[trend]
  return (
    <div className="grid grid-cols-5 hover:bg-gray-50 transition-colors">
      <div className="p-3 font-semibold text-gray-800 border-r border-gray-100">{prop}</div>
      <div className="p-3 border-r border-gray-100">
        <span className={`font-bold ${colors.hit}`}>{hitRateText}</span>
      </div>
      <div className="p-3 border-r border-gray-100">
        <div className="flex gap-1.5">
          {last5.map((h, i) => (
            <span key={i} className={`w-6 h-6 ${h ? 'bg-green-500' : 'bg-red-500'} rounded text-white text-[10px] flex items-center justify-center font-bold`}>{h ? '✓' : '✗'}</span>
          ))}
        </div>
      </div>
      <div className="p-3 border-r border-gray-100">
        <span className="font-semibold text-gray-800">{marginText}</span>
      </div>
      <div className="p-3">
        <span className={`${colors.bg} ${colors.text} text-xs font-bold px-3 py-1 rounded-full inline-block`}>{trend}</span>
      </div>
    </div>
  )
}


