import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PlayerSearch } from './PlayerSearch'
import { SuggestionCards } from './SuggestionCards'
import { useSeason } from '../context/SeasonContext'
import { apiPost } from '../utils/api'

const TYPES = ['PTS','REB','AST','3PM','PRA'] as const
type Direction = 'over' | 'under'
type SuggestionItem = {
  type: string
  marketLine?: number
  fairLine?: number
  confidence?: number
  suggestion?: string
  hitRate?: number
  hitRateOver?: number
  hitRateUnder?: number
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
  odds?: string // American odds format (e.g. "-110", "+150")
  result?: { suggestions: SuggestionItem[] }
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 80) return '#10b981'
  if (confidence >= 60) return '#84cc16'
  if (confidence >= 40) return '#f59e0b'
  if (confidence >= 20) return '#f97316'
  return '#ef4444'
}

function getConfidenceLabel(confidence: number) {
  if (confidence >= 80) return 'High Confidence'
  if (confidence >= 60) return 'Good Confidence'
  if (confidence >= 40) return 'Moderate Risk'
  if (confidence >= 20) return 'High Risk'
  return 'Very High Risk'
}

function calculateVolumeAdjustment(legCount: number) {
  if (legCount === 2) return 0.98
  if (legCount === 3) return 1.02
  if (legCount === 4) return 1.01
  if (legCount === 5) return 1.0
  if (legCount === 6) return 0.95
  if (legCount === 7) return 0.9
  if (legCount >= 8) return 0.85
  return 1.0
}

function americanToDecimalOdds(american: number) {
  if (american > 0) return 1 + american / 100
  return 1 + 100 / Math.abs(american)
}

function formatCurrency(n: number) {
  return n.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function ConfidenceRing({ confidence, legCount, isCalculating }: { confidence: number; legCount: number; isCalculating: boolean }) {
  const diameter = 120
  const stroke = 8
  const radius = (diameter - stroke) / 2
  const circumference = radius * 2 * Math.PI
  const color = getConfidenceColor(confidence)
  const [displayConfidence, setDisplayConfidence] = useState(0)

  useEffect(() => {
    let start = 0
    const target = Math.max(0, Math.min(100, confidence))
    const duration = 700
    const step = Math.max(1, Math.round(target / (duration / 16)))
    const t = setInterval(() => {
      start += step
      if (start >= target) {
        setDisplayConfidence(target)
        clearInterval(t)
      } else {
        setDisplayConfidence(start)
      }
    }, 16)
    return () => clearInterval(t)
  }, [confidence])

  const offset = circumference - (displayConfidence / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: diameter, height: diameter }}>
        <svg className="transform -rotate-90" width={diameter} height={diameter}>
          <circle cx={diameter/2} cy={diameter/2} r={radius} fill="none" stroke="#e5e7eb" className="dark:stroke-slate-700" strokeWidth={stroke} />
        </svg>
        <svg className="absolute top-0 left-0 transform -rotate-90" width={diameter} height={diameter}>
          <circle
            cx={diameter/2}
            cy={diameter/2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.7s ease-out', filter: confidence >= 75 ? 'drop-shadow(0 0 8px currentColor)' : 'none' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-extrabold" style={{ color }}>{displayConfidence}%</span>
          <span className="mt-0.5 text-[10px] font-semibold text-on-surface-variant transition-colors duration-200">{legCount} leg{legCount===1?'':'s'}</span>
        </div>
      </div>
      <div className="text-xs font-semibold px-2 py-0.5 rounded-full transition-colors duration-200" style={{ backgroundColor: `${color}20`, color }}>{isCalculating ? 'Calculating…' : getConfidenceLabel(confidence)}</div>
    </div>
  )
}

export function ParlayBuilder() {
  const { season: globalSeason } = useSeason()
  const queryClient = useQueryClient()
  const [legs, setLegs] = useState<Leg[]>([])
  const [riskAmount, setRiskAmount] = useState<number>(100)
  // Available Bets quick-add state (left column)
  const [availPlayer, setAvailPlayer] = useState<{ id: number; name: string } | null>(null)
  const [availType, setAvailType] = useState<typeof TYPES[number]>('PTS')
  const [availLine, setAvailLine] = useState<string>('')
  const [availDir, setAvailDir] = useState<Direction>('over')
  const [availOdds, setAvailOdds] = useState<string>('-110')
  
  // Get today's date for game_date
  const today = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD format

  const canCompute = useMemo(() =>
    legs.length >= 2 && legs.length <= 3 && legs.every(l => l.player?.id && l.line !== '')
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
          direction: l.direction || 'over',
        }
        return apiPost('api/v1/props/player', body)
      }))
      return resps
    },
    onSuccess: (datas) => {
      setLegs((prev) => prev.map((l, idx) => ({ ...l, result: datas[idx] })))
    }
  })

  const createParlay = useMutation({
    mutationFn: async () => {
      // Ensure we have computed results before saving
      if (!legs.every(l => l.result && l.result.suggestions && l.result.suggestions.length > 0)) {
        throw new Error('Please click "Review" to compute confidence before placing bet')
      }

      // Build legs with system data from computed results
      const parlayLegs = legs.map((leg) => {
        const items: SuggestionItem[] = leg.result?.suggestions || []
        const suggestion = items.find((s: SuggestionItem) => s.type === leg.type)
        
        if (!suggestion) {
          throw new Error(`Missing suggestion data for leg: ${leg.player?.name} ${leg.type}`)
        }
        
        // Get hit rate for the chosen direction
        const direction = leg.direction || 'over'
        const hitRateValue = direction === 'over' 
          ? (suggestion.hitRateOver || suggestion.hitRate || null)
          : (suggestion.hitRateUnder || suggestion.hitRate || null)
        
        // Convert hit rate to percentage (0-100) if it's a decimal (0-1)
        let hitRatePercentage = null
        if (hitRateValue !== null && hitRateValue !== undefined) {
          const numValue = typeof hitRateValue === 'number' ? hitRateValue : Number(hitRateValue)
          // If value is less than 1, assume it's a decimal and convert to percentage
          hitRatePercentage = numValue < 1 ? numValue * 100 : numValue
        }
        
        return {
          player_id: leg.player!.id,
          player_name: leg.player!.name,
          prop_type: leg.type,
          line_value: Number(leg.line),
          direction: direction,
          system_confidence: suggestion.confidence || null,
          system_fair_line: suggestion.fairLine || null,
          system_suggestion: suggestion.suggestion || null,
          system_hit_rate: hitRatePercentage,
        }
      })

      const parlayData = {
        game_date: today,
        total_amount: riskAmount > 0 ? riskAmount : null,
        total_odds: americanOdds,
        system_confidence: combinedConfidence || null,
        legs: parlayLegs,
      }

      return apiPost('api/v1/parlays', parlayData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parlays'] })
      queryClient.invalidateQueries({ queryKey: ['bet-stats'] })
      // Show success message and optionally clear the form
      alert('Parlay saved successfully!')
      // Optionally clear the form
      // clearAll()
    },
    onError: (error: Error) => {
      alert(`Failed to save parlay: ${error.message}`)
    }
  })

  function removeLeg(i: number) {
    setLegs((p) => p.filter((_, idx) => idx !== i))
  }
  function clearAll() {
    setLegs([])
    setAvailPlayer(null)
    setAvailLine('')
    setAvailOdds('-110')
  }

  // Build cards and compute combined confidence
  const perLegSuggestions = legs.map((l) => {
    const items: SuggestionItem[] = l.result?.suggestions || []
    return items.find((s: SuggestionItem) => s.type === l.type)
  }).filter((x): x is SuggestionItem => Boolean(x))

  const combinedConfidenceRaw = useMemo(() => {
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
    return Math.max(0, Math.min(1, prod))
  }, [perLegSuggestions, legs])

  const combinedConfidence = useMemo(() => {
    if (combinedConfidenceRaw == null) return null
    const adjustment = calculateVolumeAdjustment(perLegSuggestions.length)
    return Math.round(combinedConfidenceRaw * adjustment * 100)
  }, [combinedConfidenceRaw, perLegSuggestions.length])

  // Payout calculator using actual odds from each leg (or -110 default)
  const validLegCount = useMemo(() => legs.filter(l => l.player?.id && l.line !== '').length, [legs])
  const decimalOdds = useMemo(() => {
    if (validLegCount === 0) return 1
    const legDecimals = legs
      .filter(l => l.player?.id && l.line !== '')
      .map(l => {
        const oddsStr = l.odds || '-110'
        const oddsNum = Number(oddsStr)
        if (isNaN(oddsNum)) return americanToDecimalOdds(-110) // Default if invalid
        return americanToDecimalOdds(oddsNum)
      })
    return legDecimals.reduce((acc, dec) => acc * dec, 1)
  }, [legs, validLegCount])
  const toWin = useMemo(() => Math.max(0, riskAmount * (decimalOdds - 1)), [riskAmount, decimalOdds])
  const totalPayout = useMemo(() => Math.max(0, riskAmount * decimalOdds), [riskAmount, decimalOdds])
  const americanOdds = useMemo(() => {
    if (decimalOdds >= 2) return `+${Math.round((decimalOdds - 1) * 100)}`
    const val = Math.round(-100 / (decimalOdds - 1))
    return `${val}`
  }, [decimalOdds])
  const expectedValue = useMemo(() => {
    if (combinedConfidence == null) return 0
    const p = Math.max(0, Math.min(1, combinedConfidence / 100))
    return p * toWin - (1 - p) * riskAmount
  }, [combinedConfidence, toWin, riskAmount])

  return (
    <div className="bg-background min-h-screen p-4 md:p-6">
      <header className="flex flex-col mb-6 space-y-1">
        <h1 className="text-4xl font-black italic tracking-tighter text-on-surface uppercase">PARLAY BUILDER</h1>
        <p className="text-on-surface-variant text-sm tracking-wide border-l-2 border-primary-container pl-4">Asymmetric intelligence engine for multi-leg execution.</p>
      </header>
      
      {/* Add Leg Section - Top */}
      <div className="bg-surface-container p-4 mb-3 rounded border border-outline/20 transition-colors duration-200">
        <div className="text-xs sm:text-sm font-semibold text-on-surface mb-2 transition-colors duration-200">Add Leg to Parlay</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2">
          <div>
            <div className="text-xs font-medium text-on-surface-variant mb-0.5 transition-colors duration-200">Player</div>
            <PlayerSearch key={`top-search-${availPlayer?.id || 'empty'}`} onSelect={setAvailPlayer} />
            {availPlayer?.id ? (
              <div className="mt-0.5 text-xs">
                <a href={`/player/${availPlayer.id}`} className="text-primary-container hover:underline transition-colors duration-200">View {availPlayer.name} →</a>
              </div>
            ) : null}
          </div>
          <div>
            <div className="text-xs font-medium text-on-surface-variant mb-0.5 transition-colors duration-200">Prop Type</div>
            <select value={availType} onChange={(e) => setAvailType(e.target.value as typeof TYPES[number])} className="w-full px-2 pr-8 py-1.5 text-sm rounded-md border border-outline/30 bg-surface-container-high text-on-surface transition-colors duration-200">
              {TYPES.map((t) => <option key={t} value={t} className="bg-surface-container-high">{t}</option>)}
            </select>
          </div>
          <div>
            <div className="text-xs font-medium text-on-surface-variant mb-0.5 transition-colors duration-200">Line</div>
            <input value={availLine} onChange={(e) => setAvailLine(e.target.value)} placeholder={`24.5`} inputMode="decimal" className="w-full px-2 py-1.5 text-sm rounded-md border border-outline/30 bg-surface-container-high text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container/30 transition-colors duration-200" />
          </div>
          <div>
            <div className="text-xs font-medium text-on-surface-variant mb-0.5 transition-colors duration-200">Direction</div>
            <div className="flex items-center gap-1">
              <button onClick={() => setAvailDir('over')} className={`flex-1 px-2 py-1.5 rounded border border-outline/30 text-xs font-black uppercase tracking-wide transition-colors duration-200 ${availDir==='over' ? 'bg-primary-container text-on-primary' : 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest'}`}>Over</button>
              <button onClick={() => setAvailDir('under')} className={`flex-1 px-2 py-1.5 rounded border border-outline/30 text-xs font-black uppercase tracking-wide transition-colors duration-200 ${availDir==='under' ? 'bg-primary-container text-on-primary' : 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest'}`}>Under</button>
            </div>
          </div>
          <div>
            <div className="text-xs font-medium text-on-surface-variant mb-0.5 transition-colors duration-200">Odds</div>
            <input value={availOdds} onChange={(e) => setAvailOdds(e.target.value)} placeholder="-110" className="w-full px-2 py-1.5 text-sm rounded-md border border-outline/30 bg-surface-container-high text-on-surface focus:outline-none focus:ring-2 focus:ring-primary-container/30 transition-colors duration-200" />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => {
                if (!availPlayer?.id || !availLine || legs.length >= 3) return
                setLegs((p) => [...p, { player: { id: availPlayer.id, name: availPlayer.name }, type: availType, line: availLine, season: globalSeason, direction: availDir, odds: availOdds || '-110' }])
                // Reset all form fields
                setAvailPlayer(null)
                setAvailLine('')
                setAvailOdds('-110')
                setAvailType('PTS')
                setAvailDir('over')
              }}
              disabled={!availPlayer?.id || !availLine || legs.length >= 3}
              className="w-full px-3 py-1.5 text-sm rounded bg-primary-container text-on-primary font-black uppercase tracking-wide hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-200"
            >
              Add Leg
            </button>
          </div>
        </div>
        <div className="mt-1.5 text-xs text-on-surface-variant transition-colors duration-200">Max 3 legs. Add 2+ legs and click "Review Parlay".</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 sm:gap-4">
        {/* Main Builder Section - spans 2 columns */}
        <div className="lg:col-span-2 bg-surface-container p-4 rounded border border-outline/20 transition-colors duration-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-2">
            <div className="text-xs sm:text-sm font-semibold text-on-surface transition-colors duration-200">Your Parlay ({legs.length} leg{legs.length !== 1 ? 's' : ''})</div>
            <div className="flex gap-1.5">
              <button onClick={clearAll} disabled={legs.length === 0} className="px-2 py-1 text-xs rounded border border-outline/30 bg-surface-container-high text-on-surface hover:bg-surface-container-highest disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-200">Clear</button>
              <button onClick={() => compute.mutate()} disabled={!canCompute || compute.isPending} className="px-3 py-1 text-xs rounded bg-primary-container text-on-primary font-black uppercase tracking-wide hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-200">{compute.isPending ? 'Reviewing…' : 'Review'}</button>
            </div>
          </div>

          {/* Selected Legs List */}
          {legs.length === 0 ? (
            <div className="text-center py-6 text-on-surface-variant transition-colors duration-200">
              <p className="text-sm">No legs added yet. Use the form above to add legs.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {legs.map((leg, idx) => (
              <div key={idx} className="p-4 border border-outline/20 rounded bg-surface-container-low transition-colors duration-200">
            <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="text-sm font-semibold text-on-surface transition-colors duration-200">Leg {idx + 1}</div>
              <button onClick={() => removeLeg(idx)} className="px-2 py-1 text-xs rounded border border-outline/30 bg-surface-container-high text-on-surface hover:bg-surface-container-highest transition-colors duration-200">Remove</button>
            </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                {leg.player?.id ? (
                  <div className="px-2 py-1.5 rounded-md border border-outline/30 bg-surface-container-high flex items-center justify-between transition-colors duration-200">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-sm font-medium text-on-surface truncate transition-colors duration-200">{leg.player.name}</span>
                      <a href={`/player/${leg.player.id}`} className="text-primary-container hover:underline text-xs whitespace-nowrap transition-colors duration-200">View →</a>
                    </div>
                    <button
                      onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, player: null } : x))}
                      className="ml-2 px-2 py-0.5 text-xs rounded border border-outline/30 bg-surface-container-high text-on-surface hover:bg-surface-container-highest transition-colors duration-200"
                      title="Change player"
                    >
                      Change
                    </button>
                  </div>
                ) : (
                  <PlayerSearch onSelect={(p) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, player: p } : x))} />
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-1.5">
                <select value={leg.type} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, type: e.target.value as unknown as typeof TYPES[number] } : x))} className="px-2 pr-6 py-1 rounded-md border border-outline/30 bg-surface-container-high text-on-surface text-xs transition-colors duration-200">
                  {TYPES.map((t) => <option key={t} value={t} className="bg-surface-container-high">{t}</option>)}
                </select>
                <input value={leg.line} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, line: e.target.value } : x))} placeholder={`Line`} inputMode="decimal" className="px-2 py-1 rounded-md border border-outline/30 bg-surface-container-high text-on-surface text-xs focus:outline-none focus:ring-2 focus:ring-primary-container/30 transition-colors duration-200" />
                <input value={leg.odds || '-110'} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, odds: e.target.value } : x))} placeholder="Odds" className="px-2 py-1 rounded-md border border-outline/30 bg-surface-container-high text-on-surface text-xs focus:outline-none focus:ring-2 focus:ring-primary-container/30 transition-colors duration-200" />
                <select value={leg.home || 'any'} onChange={(e) => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, home: e.target.value as Leg['home'] } : x))} className="px-2 pr-6 py-1 rounded-md border border-outline/30 bg-surface-container-high text-on-surface text-xs transition-colors duration-200">
                  <option value="any" className="bg-surface-container-high">Any</option>
                  <option value="home" className="bg-surface-container-high">Home</option>
                  <option value="away" className="bg-surface-container-high">Away</option>
                </select>
                <div className="flex items-center gap-1 col-span-2 md:col-span-2">
                  <button onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, direction: 'over' } : x))} className={`flex-1 px-2 py-1 rounded border border-outline/30 text-xs font-black uppercase tracking-wide transition-colors duration-200 ${((leg.direction ?? 'over') === 'over') ? 'bg-primary-container text-on-primary' : 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest'}`}>Over</button>
                  <button onClick={() => setLegs((prev) => prev.map((x, i) => i === idx ? { ...x, direction: 'under' } : x))} className={`flex-1 px-2 py-1 rounded border border-outline/30 text-xs font-black uppercase tracking-wide transition-colors duration-200 ${((leg.direction ?? 'over') === 'under') ? 'bg-primary-container text-on-primary' : 'bg-surface-container-high text-on-surface hover:bg-surface-container-highest'}`}>Under</button>
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
                <div className="mt-2">
                  <SuggestionCards suggestions={[decorated]} />
                </div>
              )
            })()}
          </div>
        ))}
            </div>
          )}

          {/* Confidence Hero */}
          {legs.length > 0 && (
            <div className="mt-3">
              {combinedConfidence != null ? (
                <div className="flex items-center justify-center">
                  <ConfidenceRing confidence={combinedConfidence} legCount={validLegCount} isCalculating={compute.isPending} />
                </div>
              ) : (
                <div className="text-xs text-on-surface-variant text-center transition-colors duration-200">Add 2+ legs and click "Review" to see confidence.</div>
              )}
            </div>
          )}

          {/* Parlay Stats */}
          <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2">
            <div className="p-2 border border-outline/20 rounded bg-surface-container-low transition-colors duration-200">
              <div className="text-xs text-on-surface-variant transition-colors duration-200">Legs</div>
              <div className="text-lg font-bold text-on-surface transition-colors duration-200">{validLegCount}</div>
            </div>
            <div className="p-2 border border-outline/20 rounded bg-surface-container-low transition-colors duration-200">
              <div className="text-xs text-on-surface-variant transition-colors duration-200">Combined Odds</div>
              <div className="text-lg font-bold text-on-surface transition-colors duration-200">{americanOdds} <span className="text-xs text-on-surface-variant transition-colors duration-200">({decimalOdds.toFixed(2)}x)</span></div>
            </div>
            <div className="p-2 border border-outline/20 rounded bg-surface-container-low transition-colors duration-200">
              <div className="text-xs text-on-surface-variant transition-colors duration-200">Expected Value</div>
              <div className={`text-5xl font-black tracking-tighter transition-colors duration-200 ${expectedValue >= 0 ? 'text-betting-green' : 'text-error'}`}>{formatCurrency(Math.abs(expectedValue))}{expectedValue>=0?'':' loss'}{expectedValue>=0?' gain':''}</div>
            </div>
          </div>

        </div>

        {/* Payout Calculator */}
        <div className="bg-surface-container p-6 rounded border border-outline/20 h-fit sticky top-20 transition-colors duration-200">
          <div className="text-sm font-black uppercase tracking-widest text-on-surface transition-colors duration-200">Payout Calculator</div>
          <div className="mt-1.5 text-xs text-on-surface-variant transition-colors duration-200">Uses your custom odds from each leg.</div>
          {legs.filter(l => l.player?.id && l.line !== '').length > 0 && (
            <div className="mt-1.5 text-xs text-on-surface-variant space-y-0.5 transition-colors duration-200">
              {legs.filter(l => l.player?.id && l.line !== '').map((l, idx) => (
                <div key={idx} className="flex justify-between">
                  <span>Leg {idx + 1}:</span>
                  <span className="font-medium">{l.odds || '-110'}</span>
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <label className="text-xs font-medium text-on-surface-variant transition-colors duration-200">Risk Amount</label>
            <div className="mt-1">
              <div className="flex items-center gap-1.5">
                <span className="text-on-surface-variant text-sm transition-colors duration-200">$</span>
                <input
                  value={riskAmount}
                  onChange={(e) => setRiskAmount(Math.max(0, Math.min(10000, Number(e.target.value || 0))))}
                  inputMode="numeric"
                  className="px-2 py-1.5 text-sm rounded-md border border-outline/30 bg-surface-container-high text-on-surface w-full focus:outline-none focus:ring-2 focus:ring-primary-container/30 transition-colors duration-200"
                />
              </div>
              <div className="mt-2 grid grid-cols-4 gap-1.5">
                {[25, 50, 100, 200].map(v => (
                  <button 
                    key={v} 
                    onClick={() => setRiskAmount(v)} 
                    className={`px-2 py-1 rounded-md border text-xs transition-colors duration-200 ${riskAmount===v ? 'bg-primary-container/15 text-primary-container border-primary-container/30' : 'bg-surface-container-high text-on-surface border-outline/30 hover:bg-surface-container-highest'}`}
                  >
                    ${v}
                  </button>
                ))}
              </div>
              <div className="mt-2">
                <input
                  type="range"
                  min={0}
                  max={1000}
                  step={5}
                  value={Math.max(0, Math.min(1000, riskAmount))}
                  onChange={(e) => setRiskAmount(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 border border-outline/20 rounded bg-surface-container-low transition-colors duration-200">
              <div className="text-on-surface-variant transition-colors duration-200">To Win</div>
              <div className="text-lg font-bold text-on-surface transition-colors duration-200">{formatCurrency(toWin)}</div>
            </div>
            <div className="p-2 border border-outline/20 rounded bg-surface-container-low transition-colors duration-200">
              <div className="text-on-surface-variant transition-colors duration-200">Total Payout</div>
              <div className="text-lg font-bold text-on-surface transition-colors duration-200">{formatCurrency(totalPayout)}</div>
            </div>
          </div>
          <div className="mt-2 text-xs text-on-surface-variant transition-colors duration-200">Odds: {decimalOdds.toFixed(2)}x • {validLegCount} leg{validLegCount !== 1 ? 's' : ''}</div>
          <div className="mt-3">
            <button 
              onClick={() => createParlay.mutate()} 
              disabled={validLegCount < 2 || !combinedConfidence || riskAmount <= 0 || createParlay.isPending || compute.isPending}
              className="w-full px-3 py-2 text-sm rounded bg-primary-container text-on-primary font-black uppercase tracking-wide hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-200"
              title={riskAmount <= 0 ? 'Please enter an amount above' : ''}
            >
              {createParlay.isPending ? 'Saving...' : 'Place Bet'}
            </button>
            {validLegCount >= 2 && combinedConfidence && riskAmount <= 0 && (
              <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 text-center transition-colors duration-200">
                ⚠️ Enter amount above to place bet
              </div>
            )}
          </div>
      </div>
    </div>
    </div>
  )
}
