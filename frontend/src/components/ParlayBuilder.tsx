import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { PlayerSearch } from './PlayerSearch'
import { SuggestionCards } from './SuggestionCards'
import { useSeason } from '../context/SeasonContext'

const TYPES = ['PTS','REB','AST','3PM','PRA'] as const

type Leg = {
  player: { id: number; name: string } | null
  type: typeof TYPES[number]
  line: string
  season?: string
  lastN?: number | ''
  home?: 'any' | 'home' | 'away'
  direction?: 'over' | 'under'
  result?: any
}

export function ParlayBuilder() {
  const { season: globalSeason } = useSeason()
  const [legs, setLegs] = useState<Leg[]>([
    { player: null, type: 'PTS', line: '', season: globalSeason, direction: 'over' },
    { player: null, type: 'REB', line: '', season: globalSeason, direction: 'over' },
  ])

  const canCompute = useMemo(() =>
    legs.filter(l => l.player?.id && l.line !== '').length >= 2 && legs.filter(Boolean).length <= 3
  , [legs])

  const compute = useMutation({
    mutationFn: async () => {
      const resps = await Promise.all(legs.map(async (l) => {
        if (!l.player?.id || l.line === '') return { suggestions: [] }
        const body: any = {
          playerId: l.player.id,
          season: l.season || globalSeason || '2025-26',
          lastN: l.lastN || undefined,
          home: l.home && l.home !== 'any' ? l.home : undefined,
          marketLines: { [l.type]: l.line },
        }
        const r = await fetch('/api/v1/props/player', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        return r.json()
      }))
      return resps
    },
    onSuccess: (datas) => {
      setLegs((prev) => prev.map((l, idx) => ({ ...l, result: datas[idx] })))
    }
  })

  function addLeg() {
    if (legs.length >= 3) return
    setLegs((p) => [...p, { player: null, type: 'AST', line: '', season: globalSeason, direction: 'over' }])
  }
  function removeLeg(i: number) {
    setLegs((p) => p.filter((_, idx) => idx !== i))
  }

  // Build cards and compute combined confidence
  const perLegSuggestions = legs.map((l) => {
    const items = l.result?.suggestions || []
    return items.find((s: any) => s.type === l.type)
  }).filter(Boolean)

  const combinedConfidence = useMemo(() => {
    if (perLegSuggestions.length < 2) return null
    const ps = perLegSuggestions.map((s: any, idx: number) => {
      const leg = legs[idx]
      const conf = s.confidence
      const pRaw = conf > 1 ? conf / 100 : conf
      const p = Math.max(0, Math.min(1, pRaw || 0))
      const fair = s.fairLine
      const market = s.marketLine
      const suggestedOver = (fair != null && market != null) ? (fair - market) >= 0 : true
      const wantsOver = (leg?.direction ?? 'over') === 'over'
      const chooseP = (wantsOver === suggestedOver) ? p : (1 - p)
      return chooseP
    })
    const prod = ps.reduce((acc: number, v: number) => acc * v, 1)
    return Math.round(prod * 100)
  }, [perLegSuggestions, legs])

  return (
    <div className="p-4 md:p-5" style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ fontWeight: 600 }}>Parlay Builder</div>
        <div className="flex gap-2 md:gap-3">
          <button onClick={addLeg} disabled={legs.length >= 3} className="px-3 py-1.5 rounded border border-gray-300 bg-white">Add Leg</button>
          <button onClick={() => compute.mutate()} disabled={!canCompute || compute.isPending} className="px-3 py-1.5 rounded border border-[color:var(--tw-shadow-color)]" style={{ background: '#17408B', color: '#fff', border: '1px solid #17408B', opacity: canCompute ? 1 : 0.6 }}>{compute.isPending ? 'Reviewing…' : 'Review Parlay'}</button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:gap-4" style={{ marginTop: 10 }}>
        {legs.map((leg, idx) => (
          <div key={idx} className="p-3 md:p-4" style={{ border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
              <div style={{ fontWeight: 500 }}>Leg {idx + 1}</div>
              <button onClick={() => removeLeg(idx)} disabled={legs.length <= 2} className="px-2 py-1 rounded border border-gray-300 bg-white">Remove</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4" style={{ marginTop: 8 }}>
              <PlayerSearch onSelect={(p) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, player: p } : x))} />
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 md:gap-3">
                <select value={leg.type} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, type: e.target.value as any } : x))} className="px-3 py-2 rounded border border-gray-300 bg-white" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <input value={leg.line} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, line: e.target.value } : x))} placeholder={`${leg.type} line e.g. 24.5`} inputMode="decimal" className="px-3 py-2 rounded border border-gray-300" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
                <input value={leg.season || ''} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, season: e.target.value } : x))} placeholder="Season (e.g. 2025-26)" className="px-3 py-2 rounded border border-gray-300" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6 }} />
                <select value={leg.home || 'any'} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, home: e.target.value as any } : x))} className="px-3 py-2 rounded border border-gray-300 bg-white" style={{ padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
                  <option value="any">Venue: Any</option>
                  <option value="home">Venue: Home</option>
                  <option value="away">Venue: Away</option>
                </select>
                <div className="flex items-center gap-2">
                  <button onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, direction: 'over' } : x))} className="px-3 py-2 rounded border border-gray-300" style={{ background: (leg.direction ?? 'over') === 'over' ? '#17408B' : '#fff', color: (leg.direction ?? 'over') === 'over' ? '#fff' : '#111827' }}>Over</button>
                  <button onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, direction: 'under' } : x))} className="px-3 py-2 rounded border border-gray-300" style={{ background: (leg.direction ?? 'over') === 'under' ? '#17408B' : '#fff', color: (leg.direction ?? 'over') === 'under' ? '#fff' : '#111827' }}>Under</button>
                </div>
              </div>
            </div>
            {leg.result && leg.result.suggestions && leg.result.suggestions.length > 0 && (() => {
              const items = leg.result.suggestions || []
              const s = items.find((x: any) => x.type === leg.type)
              if (!s) return null
              const impliedOver = (s.fairLine != null && s.marketLine != null) ? (s.fairLine - s.marketLine) >= 0 : true
              const chosen = leg.direction || 'over'
              const better = impliedOver ? 'over' : 'under'
              const decorated = { ...s, chosenDirection: chosen, betterDirection: chosen === better ? undefined : better }
              return (
                <div style={{ marginTop: 8 }}>
                  <SuggestionCards suggestions={[decorated]} />
                </div>
              )
            })()}
          </div>
        ))}
      </div>

      <div className="mt-3 md:mt-4 pt-3 md:pt-4" style={{ borderTop: '1px solid #e5e7eb' }}>
        {combinedConfidence != null ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontWeight: 600 }}>Parlay Confidence</div>
            <div style={{ fontSize: 18 }}>{combinedConfidence}%</div>
          </div>
        ) : (
          <div style={{ color: '#6b7280', fontSize: 12 }}>Add 2-3 legs and click Review Parlay to see combined confidence.</div>
        )}
      </div>
    </div>
  )
}
