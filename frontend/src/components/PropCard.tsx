type Trend = 'up' | 'down' | 'neutral'

export function PropCard({ label, value, trend, trendText, confidence, recommendation, highlight, details }: { label: string; value: string | number; trend: Trend; trendText: string; confidence: number; recommendation: string; highlight?: boolean; details?: Array<{ label: string; value: string }> }) {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-yellow-600'
  const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  const borderClass = highlight ? 'border-blue-700' : 'border-blue-600'
  return (
    <div className={`bg-gradient-to-br from-white via-gray-50 to-gray-100 rounded-xl p-4 border-l-4 ${borderClass} shadow`}> 
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">{label}</div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${recommendation === 'OVER' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{recommendation}</span>
      </div>
      <div className={`text-3xl font-extrabold ${highlight ? 'text-blue-800' : 'text-blue-900'}`}>{value}</div>
      <div className={`mt-1 text-xs font-bold ${trendColor}`}>{arrow} {trendText}</div>
      <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-green-500 via-blue-500 to-purple-500" style={{ width: `${Math.max(0, Math.min(100, confidence))}%` }} />
      </div>
      <div className="mt-1 text-[11px] text-gray-700 font-semibold">{confidence}% confidence {recommendation}</div>
      {Array.isArray(details) && details.length > 0 && (
        <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-gray-700">
          {details.map((d, i) => (
            <div key={i} className="flex items-center justify-between">
              <span className="text-gray-500">{d.label}</span>
              <span className="font-semibold text-gray-800">{d.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


