type Trend = 'up' | 'down' | 'neutral'

export function PropCard({ label, value, trend, trendText, confidence, recommendation, highlight, details }: { label: string; value: string | number; trend: Trend; trendText: string; confidence: number; recommendation: string; highlight?: boolean; details?: Array<{ label: string; value: string }> }) {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-yellow-600'
  const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  const borderClass = highlight ? 'border-blue-700' : 'border-blue-600'
  const clamped = Math.max(0, Math.min(100, Number(confidence) || 0))
  
  // Color based on confidence level with clearer thresholds
  // Using both Tailwind classes and inline style fallback
  let barColor = 'bg-gray-400' // default fallback
  let barColorHex = '#9ca3af' // gray-400
  
  if (clamped >= 80) {
    barColor = 'bg-emerald-600'
    barColorHex = '#059669' // emerald-600
  } else if (clamped >= 60) {
    barColor = 'bg-green-500'
    barColorHex = '#22c55e' // green-500
  } else if (clamped >= 40) {
    barColor = 'bg-amber-500'
    barColorHex = '#f59e0b' // amber-500
  } else if (clamped >= 20) {
    barColor = 'bg-orange-500'
    barColorHex = '#f97316' // orange-500
  } else {
    barColor = 'bg-red-600'
    barColorHex = '#dc2626' // red-600
  }
  return (
    <div className={`bg-gradient-to-br from-white via-gray-50 to-gray-100 rounded-lg p-3 border-l-2 ${borderClass} shadow-sm`}> 
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-0.5">{label}</div>
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${recommendation === 'OVER' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{recommendation}</span>
      </div>
      <div className={`text-2xl font-extrabold ${highlight ? 'text-blue-800' : 'text-blue-900'}`}>{value}</div>
      <div className={`mt-0.5 text-[11px] font-bold ${trendColor}`}>{arrow} {trendText}</div>
      <div
        className="mt-1.5 h-2 bg-gray-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-label={`Confidence ${clamped}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
      >
        <div 
          className={`h-full ${barColor} transition-all duration-700 ease-out rounded-full`} 
          style={{ 
            width: `${clamped}%`, 
            minWidth: clamped > 0 ? '2px' : '0',
            backgroundColor: barColorHex // Fallback inline color
          }} 
        />
      </div>
      <div className="mt-1 text-[10px] text-gray-700 font-semibold">{clamped}% confidence {recommendation}</div>
      {Array.isArray(details) && details.length > 0 && (
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2">
          {details.map((d, i) => (
            <div key={i} className="border border-gray-200 rounded-md p-1.5 bg-white">
              <div className="text-[10px] text-gray-500">{d.label}</div>
              <div className="text-xs font-bold text-gray-900">{d.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


