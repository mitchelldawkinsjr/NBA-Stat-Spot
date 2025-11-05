import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { PlayerSearch } from './PlayerSearch'
import { SuggestionCards } from './SuggestionCards'
import { useSeason } from '../context/SeasonContext'

const TYPES = ['PTS','REB','AST','3PM','PRA'] as const
type PropType = typeof TYPES[number]

export function QuickPropLab() {
  const { season: globalSeason } = useSeason()
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  const [propType, setPropType] = useState<PropType>('PTS')
  const [line, setLine] = useState<string>('')
  const [season, setSeason] = useState<string>(globalSeason)
  const [lastN, setLastN] = useState<number | ''>('')
  const [home, setHome] = useState<'any'|'home'|'away'>('any')
  const [result, setResult] = useState<any>(null)

  const canRun = !!player?.id && line !== ''

  const run = useMutation({
    mutationFn: async () => {
      if (!player?.id) return null
      const body: any = {
        playerId: player.id,
        season: season || undefined,
        lastN: lastN || undefined,
        home: home === 'any' ? undefined : home,
        marketLines: { [propType]: line },
      }
      const res = await fetch('/api/v1/props/player', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      return res.json()
    },
    onSuccess: (data) => setResult(data)
  })

  const suggestions = useMemo(() => {
    const items = result?.suggestions || []
    return items.filter((s: any) => s.type === propType)
  }, [result, propType])

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Quick Prop Lab</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10 }}>
        <PlayerSearch onSelect={setPlayer} />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {TYPES.map((t) => (
            <button key={t} onClick={() => setPropType(t)} style={{ padding: '6px 10px', borderRadius: 999, border: '1px solid #ddd', background: propType === t ? '#17408B' : '#fff', color: propType === t ? '#fff' : '#111827' }}>{t}</button>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(120px, 1fr))', gap: 8 }}>
          <input value={line} onChange={(e) => setLine(e.target.value)} placeholder={`${propType} line (e.g. 24.5)`} inputMode="decimal" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
          <input value={season} onChange={(e) => setSeason(e.target.value)} placeholder="Season (e.g. 2025-26)" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
          <input value={lastN} onChange={(e) => setLastN(e.target.value ? Number(e.target.value) : '')} type="number" min={1} placeholder="Last N games" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
          <select value={home} onChange={(e) => setHome(e.target.value as any)} style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
            <option value="any">Venue: Any</option>
            <option value="home">Venue: Home</option>
            <option value="away">Venue: Away</option>
          </select>
        </div>
        <div>
          <button onClick={() => run.mutate()} disabled={!canRun || run.isPending} style={{ padding: '8px 12px', background: '#17408B', color: '#fff', border: '1px solid #17408B', borderRadius: 6, opacity: canRun ? 1 : 0.6 }}>{run.isPending ? 'Computing…' : 'Test Prop'}</button>
          <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>Enter your book's line to see Over/Under + Edge/Confidence.</span>
        </div>
        <div>
          {suggestions.length === 0 ? <div style={{ color: '#6b7280' }}>No result yet.</div> : <SuggestionCards suggestions={suggestions} />}
        </div>
      </div>
    </div>
  )
}


