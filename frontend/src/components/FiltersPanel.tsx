import { useState, useEffect } from 'react'

export type Filters = {
  season?: string
  lastN?: number
  home?: 'any' | 'home' | 'away'
  marketLines?: { [k: string]: string }
}

export function FiltersPanel({ value, onChange }: { value: Filters; onChange: (f: Filters) => void }) {
  const [local, setLocal] = useState<Filters>(value)

  useEffect(() => { setLocal(value) }, [value])
  useEffect(() => { onChange(local) }, [local])

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, padding: 12, border: '1px solid #e5e7eb', borderRadius: 8, background: '#ffffff' }}>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: '#111827', marginBottom: 4 }}>Season (e.g. 2024-25)</label>
        <input
          value={local.season ?? ''}
          onChange={(e) => setLocal((p) => ({ ...p, season: e.target.value }))}
          placeholder="YYYY-YY"
          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
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
          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }}
        />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, color: '#111827', marginBottom: 4 }}>Venue</label>
        <select
          value={local.home ?? 'any'}
          onChange={(e) => setLocal((p) => ({ ...p, home: e.target.value as Filters['home'] }))}
          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}
        >
          <option value="any">Any</option>
          <option value="home">Home</option>
          <option value="away">Away</option>
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
                style={{ width: 90, padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6 }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
