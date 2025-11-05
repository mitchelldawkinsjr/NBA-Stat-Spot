import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { PlayerSearch } from './PlayerSearch'
import { SuggestionCards } from './SuggestionCards'
import { useSeason } from '../context/SeasonContext'

const TYPES = ['PTS','REB','AST','3PM','PRA'] as const
type Direction = 'over' | 'under'
type SuggestionItem = {
  type: string
  marketLine?: number
  fairLine?: number
  confidence?: number
  rationale?: string[]
  chosenDirection?: Direction
  betterDirection?: Direction
}

type Leg = {
  player: { id: number; name: string } | null
  type: typeof TYPES[number]
  line: string
  season?: string
  lastN?: number | ''
  home?: 'any' | 'home' | 'away'
  direction?: 'over' | 'under'
  result?: { suggestions: SuggestionItem[] }
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
      const resps = await Promise.all(legs.map(async (l): Promise<{ suggestions: SuggestionItem[] }> => {
        if (!l.player?.id || l.line === '') return { suggestions: [] }
        const body: Record<string, unknown> = {
          playerId: l.player.id,
          season: l.season || globalSeason || '2025-26',
          lastN: l.lastN || undefined,
          home: l.home && l.home !== 'any' ? l.home : undefined,
          marketLines: { [l.type]: Number(l.line) },
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
    const items: SuggestionItem[] = l.result?.suggestions || []
    return items.find((s: SuggestionItem) => s.type === l.type)
  }).filter((x): x is SuggestionItem => Boolean(x))

  const combinedConfidence = useMemo(() => {
    if (perLegSuggestions.length < 2) return null
    const ps = perLegSuggestions.map((s: SuggestionItem, idx: number) => {
      const leg = legs[idx]
      const conf = s.confidence ?? 0
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
    <div className="container mx-auto px-4 py-6">
      <h2 className="text-2xl font-bold mb-4">Parlay Builder</h2>
      <div className="p-4 md:p-6 border border-gray-200 rounded-lg bg-white shadow-sm">
        <div className="flex items-baseline justify-between gap-3 flex-wrap">
          <div className="font-semibold text-gray-800">Build Your Parlay</div>
          <div className="flex gap-2 md:gap-3">
            <button onClick={addLeg} disabled={legs.length >= 3} className="px-4 py-2 rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed">Add Leg</button>
            <button onClick={() => compute.mutate()} disabled={!canCompute || compute.isPending} className="px-4 py-2 rounded-md bg-blue-700 text-white font-medium hover:bg-blue-800 disabled:opacity-60 disabled:cursor-not-allowed">{compute.isPending ? 'Reviewing…' : 'Review Parlay'}</button>
          </div>
        </div>

      <div className="grid grid-cols-1 gap-3 md:gap-4" style={{ marginTop: 10 }}>
        {legs.map((leg, idx) => (
          <div key={idx} className="p-3 md:p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="font-medium text-gray-800">Leg {idx + 1}</div>
              <button onClick={() => removeLeg(idx)} disabled={legs.length <= 2} className="px-3 py-1.5 rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed">Remove</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4" style={{ marginTop: 8 }}>
              <div>
                <PlayerSearch onSelect={(p) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, player: p } : x))} />
                {leg.player?.id ? (
                  <div style={{ marginTop: 6, fontSize: 13 }}>
                    <a href={`/player/${leg.player.id}`} style={{ color: '#2563eb' }}>View {leg.player.name} profile →</a>
                  </div>
                ) : null}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 md:gap-3">
                <select value={leg.type} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, type: e.target.value as unknown as typeof TYPES[number] } : x))} className="px-3 py-2 rounded-md border border-gray-300 bg-white">
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <input value={leg.line} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, line: e.target.value } : x))} placeholder={`${leg.type} line e.g. 24.5`} inputMode="decimal" className="px-3 py-2 rounded-md border border-gray-300" />
                <input value={leg.season || ''} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, season: e.target.value } : x))} placeholder="Season (e.g. 2025-26)" className="px-3 py-2 rounded-md border border-gray-300" />
                <select value={leg.home || 'any'} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, home: e.target.value as Leg['home'] } : x))} className="px-3 py-2 rounded-md border border-gray-300 bg-white">
                  <option value="any">Venue: Any</option>
                  <option value="home">Venue: Home</option>
                  <option value="away">Venue: Away</option>
                </select>
                <div className="flex items-center gap-2">
                  <button onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, direction: 'over' } : x))} className={`px-3 py-2 rounded-md border border-gray-300 ${((leg.direction ?? 'over') === 'over') ? 'bg-blue-700 text-white' : 'bg-white text-gray-700'}`}>Over</button>
                  <button onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, direction: 'under' } : x))} className={`px-3 py-2 rounded-md border border-gray-300 ${((leg.direction ?? 'over') === 'under') ? 'bg-blue-700 text-white' : 'bg-white text-gray-700'}`}>Under</button>
                </div>
              </div>
            </div>
            {leg.result && leg.result.suggestions && leg.result.suggestions.length > 0 && (() => {
              const items: SuggestionItem[] = leg.result.suggestions || []
              const s = items.find((x: SuggestionItem) => x.type === leg.type)
              if (!s) return null
              const impliedOver = (s.fairLine != null && s.marketLine != null) ? (s.fairLine - s.marketLine) >= 0 : true
              const chosen: Direction = leg.direction || 'over'
              const better: Direction = impliedOver ? 'over' : 'under'
              const decorated = { ...s, chosenDirection: chosen, betterDirection: chosen === better ? undefined : better }
              return (
                <div className="mt-3">
                  <SuggestionCards suggestions={[decorated]} />
                </div>
              )
            })()}
          </div>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200">
        {combinedConfidence != null ? (
          <div className="flex items-center justify-between">
            <div className="font-semibold text-gray-800">Parlay Confidence</div>
            <div className="text-2xl font-bold text-blue-700">{combinedConfidence}%</div>
          </div>
        ) : (
          <div className="text-sm text-gray-600">Add 2-3 legs and click Review Parlay to see combined confidence.</div>
        )}
      </div>
    </div>
    </div>
  )
}
