type Trend = 'up' | 'down' | 'neutral'

export function PropCard({ label, value, trend, trendText, confidence, recommendation }: { label: string; value: string | number; trend: Trend; trendText: string; confidence: number; recommendation: string }) {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-yellow-600'
  const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  return (
    <div className="bg-gradient-to-br from-white via-gray-50 to-gray-100 rounded-xl p-4 border-l-4 border-blue-600 shadow">
      <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">{label}</div>
      <div className="text-3xl font-extrabold text-blue-900">{value}</div>
      <div className={`mt-1 text-xs font-bold ${trendColor}`}>{arrow} {trendText}</div>
      <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-green-500 via-blue-500 to-purple-500" style={{ width: `${Math.max(0, Math.min(100, confidence))}%` }} />
      </div>
      <div className="mt-1 text-[11px] text-gray-700 font-semibold">{confidence}% confidence {recommendation}</div>
    </div>
  )
}


