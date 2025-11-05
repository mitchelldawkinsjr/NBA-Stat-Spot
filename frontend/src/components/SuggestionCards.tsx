export function SuggestionCards({ suggestions }: { suggestions: any[] }) {
  function colorFor(conf?: number | null) {
    if (conf == null) return '#6b7280'
    if (conf >= 0.6) return '#065f46' // green
    if (conf >= 0.55) return '#2563eb' // blue
    if (conf >= 0.5) return '#374151' // gray
    return '#b91c1c' // red
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
      {suggestions.map((s, idx) => (
        <div key={idx} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>{s.type}</strong>
            {s.marketLine != null && (
              <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 999, color: '#fff', background: (s.confidence ?? 0) >= 0.5 ? '#10B981' : '#EF4444' }}>
                {(s.confidence ?? 0) >= 0.5 ? 'Over' : 'Under'}
              </span>
            )}
          </div>
          <div style={{ marginTop: 6, color: '#111827' }}>
            {s.marketLine != null ? (
              <div>
                <div title="Your line from the sportsbook"><strong>Market:</strong> {s.marketLine} {s.type}</div>
                <div title="Model-implied fair line"><strong>Fair:</strong> {s.fairLine != null ? s.fairLine.toFixed(1) : '—'}</div>
                <div title="Fair - Market, positive favors Over, negative favors Under"><strong>Edge:</strong> {s.fairLine != null && s.marketLine != null ? (s.fairLine - s.marketLine >= 0 ? '+' : '') + (s.fairLine - s.marketLine).toFixed(1) : '—'}</div>
                <div title="Confidence in recommendation"><strong>Confidence:</strong> {s.confidence != null ? Math.round((s.confidence > 1 ? s.confidence : s.confidence * 100)) + '%' : '—'}</div>
              </div>
            ) : (
              <div><strong>Fair Line:</strong> {s.fairLine?.toFixed?.(1) ?? '-'}</div>
            )}
          </div>
          {Array.isArray(s.rationale) && s.rationale.length > 0 && (
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {s.rationale.slice(0, 3).map((r: string, i: number) => (
                <span key={i} style={{ background: '#f3f4f6', color: '#1f2937', borderRadius: 999, padding: '2px 8px', fontSize: 12 }}>{r}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
