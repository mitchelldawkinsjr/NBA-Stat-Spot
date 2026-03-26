type Trend = 'up' | 'down' | 'neutral'

export function PropCard({ label, value, trend, trendText, confidence, recommendation, highlight, details }: { label: string; value: string | number; trend: Trend; trendText: string; confidence: number; recommendation: string; highlight?: boolean; details?: Array<{ label: string; value: string }> }) {
  const trendColor = trend === 'up' ? 'text-betting-green' : trend === 'down' ? 'text-error' : 'text-primary-container'
  const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  const borderClass = highlight ? 'border-primary' : 'border-primary-container/60'
  const clamped = Math.max(0, Math.min(100, Number(confidence) || 0))
  
  // Color based on confidence level with granular thresholds (5% increments)
  // Using both Tailwind classes and inline style fallback
  let barColor = 'bg-surface-container-highest' // default fallback
  let barColorHex = '#9ca3af' // gray-400
  
  // More granular color mapping with 5% increments for smoother transitions
  if (clamped >= 90) {
    barColor = 'bg-emerald-600'
    barColorHex = '#059669' // emerald-600
  } else if (clamped >= 85) {
    barColor = 'bg-emerald-500'
    barColorHex = '#10b981' // emerald-500
  } else if (clamped >= 80) {
    barColor = 'bg-green-600'
    barColorHex = '#16a34a' // green-600
  } else if (clamped >= 75) {
    barColor = 'bg-green-500'
    barColorHex = '#22c55e' // green-500
  } else if (clamped >= 70) {
    barColor = 'bg-lime-500'
    barColorHex = '#84cc16' // lime-500
  } else if (clamped >= 65) {
    barColor = 'bg-yellow-500'
    barColorHex = '#eab308' // yellow-500
  } else if (clamped >= 60) {
    barColor = 'bg-amber-500'
    barColorHex = '#f59e0b' // amber-500
  } else if (clamped >= 55) {
    barColor = 'bg-amber-600'
    barColorHex = '#d97706' // amber-600
  } else if (clamped >= 50) {
    barColor = 'bg-orange-500'
    barColorHex = '#f97316' // orange-500
  } else if (clamped >= 45) {
    barColor = 'bg-orange-600'
    barColorHex = '#ea580c' // orange-600
  } else if (clamped >= 40) {
    barColor = 'bg-red-500'
    barColorHex = '#ef4444' // red-500
  } else if (clamped >= 35) {
    barColor = 'bg-red-600'
    barColorHex = '#dc2626' // red-600
  } else if (clamped >= 30) {
    barColor = 'bg-red-700'
    barColorHex = '#b91c1c' // red-700
  } else if (clamped >= 25) {
    barColor = 'bg-red-800'
    barColorHex = '#991b1b' // red-800
  } else if (clamped >= 20) {
    barColor = 'bg-red-900'
    barColorHex = '#7f1d1d' // red-900
  } else {
    barColor = 'bg-surface-container-highest'
    barColorHex = '#4b5563' // gray-600
  }
  return (
    <div className={`rounded-lg bg-surface-container p-2.5 sm:p-3 border-l-2 ${borderClass} shadow-sm ring-1 ring-outline/15 transition-colors duration-200`}>
      <div className="flex items-center justify-between">
        <div className="text-[9px] sm:text-[10px] font-semibold text-on-surface-variant uppercase tracking-widest mb-0.5 transition-colors duration-200">{label}</div>
        <span className={`text-[9px] sm:text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${recommendation === 'OVER' ? 'bg-betting-green/15 text-betting-green ring-1 ring-betting-green/30' : 'bg-error/15 text-error ring-1 ring-error/30'} transition-colors duration-200`}>{recommendation}</span>
      </div>
      <div className={`text-xl sm:text-2xl font-extrabold ${highlight ? 'text-primary' : 'text-on-surface'} transition-colors duration-200`}>{value}</div>
      <div className={`mt-0.5 text-[11px] font-bold ${trendColor} transition-colors duration-200`}>{arrow} {trendText}</div>
      <div
        className="mt-1.5 h-2 bg-surface-container-high rounded-full overflow-hidden transition-colors duration-200"
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
      <div className="mt-1 text-[10px] text-on-surface-variant font-semibold transition-colors duration-200">{clamped}% confidence {recommendation}</div>
      {Array.isArray(details) && details.length > 0 && (
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2">
          {details.map((d, i) => (
            <div key={i} className="border border-outline/20 rounded-md p-1.5 bg-surface-container-high transition-colors duration-200">
              <div className="text-[10px] text-on-surface-variant transition-colors duration-200">{d.label}</div>
              <div className="text-xs font-bold text-on-surface transition-colors duration-200">{d.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


