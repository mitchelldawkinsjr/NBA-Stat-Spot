type Direction = 'over' | 'under'
type SuggestionItem = {
  type: string
  marketLine?: number
  fairLine?: number
  confidence?: number
  rationale?: string[]
  chosenDirection?: Direction
  betterDirection?: Direction
  playerId?: number
  playerName?: string
  hitRate?: number
  sampleSize?: number
}

export function SuggestionCards({ suggestions }: { suggestions: SuggestionItem[] }) {
  return (
    <div className="gap-3 md:gap-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      {suggestions.map((s: SuggestionItem, idx: number) => (
        <div key={idx} className="p-4 md:p-5" style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <strong>{s.type}</strong>
              {s.playerId && s.playerName && (
                <a href={`/player/${s.playerId}`} style={{ color: '#2563eb', fontSize: 12 }}>{s.playerName}</a>
              )}
            </div>
            {s.marketLine != null && (
              (() => {
                const impliedOver = (s.fairLine != null && s.marketLine != null) ? (s.fairLine - s.marketLine) >= 0 : true
                const dir = (s.chosenDirection === 'over' || s.chosenDirection === 'under') ? s.chosenDirection : (impliedOver ? 'over' : 'under')
                const bg = dir === 'over' ? '#10B981' : '#EF4444'
                return <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 999, color: '#fff', background: bg }}>{dir === 'over' ? 'Over' : 'Under'}</span>
              })()
            )}
          </div>
          <div style={{ marginTop: 6, color: '#111827' }}>
            {s.marketLine != null ? (
              <div>
                <div title="Your line from the sportsbook"><strong>Market:</strong> {s.marketLine} {s.type}</div>
                <div title="Model-implied fair line"><strong>Fair:</strong> {s.fairLine != null ? s.fairLine.toFixed(1) : '—'}</div>
                <div title="Fair - Market, positive favors Over, negative favors Under"><strong>Edge:</strong> {s.fairLine != null && s.marketLine != null ? (s.fairLine - s.marketLine >= 0 ? '+' : '') + (s.fairLine - s.marketLine).toFixed(1) : '—'}</div>
                <div title="Confidence in recommendation"><strong>Confidence:</strong> {s.confidence != null ? Math.round((s.confidence > 1 ? s.confidence : s.confidence * 100)) + '%' : '—'}</div>
                {s.hitRate != null && (
                  <div title={`Historical hit rate based on ${s.sampleSize || 0} games`} style={{ color: s.hitRate >= 75 ? '#059669' : s.hitRate >= 65 ? '#2563eb' : '#6b7280' }}>
                    <strong>Hit Rate:</strong> {s.hitRate.toFixed(1)}% {s.sampleSize && `(${s.sampleSize} games)`}
                  </div>
                )}
                {s.betterDirection && s.chosenDirection && s.betterDirection !== s.chosenDirection && (
                  <div style={{ marginTop: 6 }}>
                    <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 999, color: '#111827', background: '#FDE68A' }}>
                      Better: {s.betterDirection === 'over' ? 'Over' : 'Under'}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div><strong>Fair Line:</strong> {s.fairLine?.toFixed?.(1) ?? '-'}</div>
            )}
          </div>
          {Array.isArray(s.rationale) && s.rationale.length > 0 && (
            <div style={{ marginTop: 12, padding: '12px', background: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                Analysis
              </div>
              {(s.rationale || []).slice(0, 2).map((r: string, i: number) => {
                // Parse rationale text to extract key information
                const parseRationale = (text: string) => {
                  const parts: { type: 'trend' | 'hitRate' | 'text'; value?: string; percentage?: number; line?: number }[] = []
                  
                  // Extract form trend (Up/Down/Flat)
                  const trendMatch = text.match(/\b(Up|Down|Flat)\s+form/i)
                  if (trendMatch) {
                    parts.push({ 
                      type: 'trend', 
                      value: trendMatch[1],
                      percentage: trendMatch[1].toLowerCase() === 'up' ? 75 : trendMatch[1].toLowerCase() === 'down' ? 25 : 50
                    })
                  }
                  
                  // Extract hit rate percentage
                  const hitRateMatch = text.match(/(\d+(?:\.\d+)?)%\s+hit/i)
                  if (hitRateMatch) {
                    parts.push({ 
                      type: 'hitRate', 
                      percentage: parseFloat(hitRateMatch[1])
                    })
                  }
                  
                  // Extract line value
                  const lineMatch = text.match(/over\s+(\d+(?:\.\d+)?)/i) || text.match(/under\s+(\d+(?:\.\d+)?)/i)
                  if (lineMatch) {
                    parts.push({ 
                      type: 'text', 
                      line: parseFloat(lineMatch[1])
                    })
                  }
                  
                  return { parts, original: text }
                }
                
                const parsed = parseRationale(r)
                const trend = parsed.parts.find(p => p.type === 'trend')
                const hitRate = parsed.parts.find(p => p.type === 'hitRate')
                const line = parsed.parts.find(p => p.line)
                
                return (
                  <div key={i} style={{ marginBottom: i < (s.rationale?.length || 0) - 1 ? '10px' : 0 }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                      {trend && (
                        <div style={{ 
                          display: 'inline-flex', 
                          alignItems: 'center', 
                          gap: '4px',
                          padding: '4px 10px', 
                          background: trend.value?.toLowerCase() === 'up' ? '#dcfce7' : trend.value?.toLowerCase() === 'down' ? '#fee2e2' : '#fef3c7',
                          color: trend.value?.toLowerCase() === 'up' ? '#166534' : trend.value?.toLowerCase() === 'down' ? '#991b1b' : '#92400e',
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 600
                        }}>
                          <span>{trend.value === 'Up' ? '📈' : trend.value === 'Down' ? '📉' : '➡️'}</span>
                          <span>{trend.value} Form</span>
                        </div>
                      )}
                      {hitRate && (
                        <div style={{ 
                          display: 'inline-flex', 
                          alignItems: 'center', 
                          gap: '4px',
                          padding: '4px 10px', 
                          background: hitRate.percentage! >= 75 ? '#dbeafe' : hitRate.percentage! >= 65 ? '#e0e7ff' : '#f3f4f6',
                          color: hitRate.percentage! >= 75 ? '#1e40af' : hitRate.percentage! >= 65 ? '#3730a3' : '#374151',
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 700
                        }}>
                          <span>{hitRate.percentage}%</span>
                          <span style={{ fontWeight: 500, fontSize: '11px' }}>Hit Rate</span>
                        </div>
                      )}
                      {line && (
                        <div style={{ 
                          display: 'inline-flex', 
                          alignItems: 'center',
                          padding: '4px 10px', 
                          background: '#ffffff',
                          border: '1px solid #d1d5db',
                          color: '#111827',
                          borderRadius: '6px',
                          fontSize: '12px',
                          fontWeight: 600
                        }}>
                          <span>Line: {line.line}</span>
                        </div>
                      )}
                    </div>
                    {!trend && !hitRate && (
                      <div style={{ fontSize: '13px', color: '#4b5563', lineHeight: '1.5', marginTop: '4px' }}>
                        {r}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
