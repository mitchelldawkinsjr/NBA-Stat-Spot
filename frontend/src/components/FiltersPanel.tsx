import { useState, useEffect } from 'react'

export type Filters = {
  season?: string
  lastN?: number
  home?: 'any' | 'home' | 'away'
  marketLines?: { [k: string]: string }
  direction?: 'over' | 'under'
}

export function FiltersPanel({ 
  value, 
  onChange, 
  player, 
  onEvaluate 
}: { 
  value: Filters
  onChange: (f: Filters) => void
  player?: { id: number; name: string } | null
  onEvaluate?: (result: any) => void
}) {
  const [local, setLocal] = useState<Filters>(value)
  const [isEvaluating, setIsEvaluating] = useState(false)

  useEffect(() => { setLocal(value) }, [value])
  useEffect(() => { onChange(local) }, [local])

  const hasMarketLines = local.marketLines && Object.values(local.marketLines).some((v: any) => v && v !== '')

  const handleEvaluate = async () => {
    if (!player || !player.id || !hasMarketLines) return
    
    setIsEvaluating(true)
    try {
      const marketLines = Object.fromEntries(
        Object.entries(local.marketLines || {})
          .map(([k, v]: any) => [k, v === '' ? undefined : Number(v)])
          .filter(([, v]) => Number.isFinite(v as number))
      )
      
      const res = await fetch('/api/v1/props/player', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({
          playerId: player.id,
          season: local.season || undefined,
          lastN: local.lastN || undefined,
          home: local.home === 'any' ? undefined : local.home,
          marketLines,
          direction: local.direction || 'over',
        }) 
      })
      const data = await res.json()
      if (onEvaluate) {
        onEvaluate(data)
      }
    } catch (error) {
      console.error('Failed to evaluate prop:', error)
    } finally {
      setIsEvaluating(false)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8, background: '#ffffff' }}>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: '#111827', marginBottom: 4 }}>Season (e.g. 2024-25)</label>
        <input
          value={local.season ?? ''}
          onChange={(e) => setLocal((p) => ({ ...p, season: e.target.value }))}
          placeholder="YYYY-YY"
          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, color: '#111827', background: '#ffffff' }}
          className="text-gray-900 bg-white"
        />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: '#111827', marginBottom: 4 }}>Last N Games</label>
        <input
          type="number"
          min={1}
          value={local.lastN ?? ''}
          onChange={(e) => setLocal((p) => ({ ...p, lastN: e.target.value ? Number(e.target.value) : undefined }))}
          placeholder="10"
          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, color: '#111827', background: '#ffffff' }}
          className="text-gray-900 bg-white"
        />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: '#111827', marginBottom: 4 }}>Venue</label>
        <select
          value={local.home ?? 'any'}
          onChange={(e) => setLocal((p) => ({ ...p, home: e.target.value as Filters['home'] }))}
          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, background: '#fff', color: '#111827' }}
          className="text-gray-900 bg-white"
        >
          <option value="any" className="text-gray-900">Any</option>
          <option value="home" className="text-gray-900">Home</option>
          <option value="away" className="text-gray-900">Away</option>
        </select>
      </div>
      <div style={{ gridColumn: '1 / -1' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span title="Optional. Add your book's lines to compute edge/confidence." style={{ fontSize: 12, color: '#111827' }}>Market Lines:</span>
          {['PTS','REB','AST','3PM','PRA'].map((k) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <label style={{ width: 36 }}>{k}</label>
              <input
                inputMode="decimal"
                aria-label={`${k} market line`}
                value={local.marketLines?.[k] ?? ''}
                onChange={(e) => setLocal((p) => ({ ...p, marketLines: { ...(p.marketLines ?? {}), [k]: e.target.value } }))}
                placeholder="e.g. 24.5"
                style={{ width: 90, padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, color: '#111827', background: '#ffffff' }}
                className="text-gray-900 bg-white"
              />
            </div>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}>
            <label style={{ fontSize: 12, color: '#111827', fontWeight: 500 }}>Direction:</label>
            <div style={{ display: 'flex', gap: 2, border: '1px solid #ddd', borderRadius: 6, padding: 2 }}>
              <button
                type="button"
                onClick={() => setLocal((p) => ({ ...p, direction: 'over' }))}
                style={{
                  padding: '4px 12px',
                  fontSize: 12,
                  fontWeight: 500,
                  borderRadius: 4,
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  ...(local.direction === 'over' || !local.direction
                    ? { background: '#1d4ed8', color: '#ffffff' }
                    : { background: 'transparent', color: '#6b7280' })
                }}
              >
                Over
              </button>
              <button
                type="button"
                onClick={() => setLocal((p) => ({ ...p, direction: 'under' }))}
                style={{
                  padding: '4px 12px',
                  fontSize: 12,
                  fontWeight: 500,
                  borderRadius: 4,
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  ...(local.direction === 'under'
                    ? { background: '#1d4ed8', color: '#ffffff' }
                    : { background: 'transparent', color: '#6b7280' })
                }}
              >
                Under
              </button>
            </div>
            <button
              type="button"
              onClick={handleEvaluate}
              disabled={!player || !player.id || !hasMarketLines || isEvaluating}
              style={{
                padding: '6px 16px',
                fontSize: 12,
                fontWeight: 600,
                borderRadius: 6,
                border: 'none',
                cursor: (!player || !player.id || !hasMarketLines || isEvaluating) ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
                ...((!player || !player.id || !hasMarketLines || isEvaluating)
                  ? { background: '#d1d5db', color: '#6b7280' }
                  : { background: '#1d4ed8', color: '#ffffff' })
              }}
            >
              {isEvaluating ? 'Evaluating...' : 'Evaluate'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
