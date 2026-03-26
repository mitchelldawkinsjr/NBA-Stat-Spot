import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { PlayerSearch } from './PlayerSearch'
import { useSeason } from '../context/SeasonContext'
import { apiPost } from '../utils/api'
import type { SuggestionItem } from './SuggestionCards'

const TYPES = ['PTS','REB','AST','3PM','PRA'] as const
type PropType = typeof TYPES[number]

function PropLabResult({ s, playerName, playerId }: { s: SuggestionItem; playerName?: string; playerId?: number }) {
  const direction = s.suggestion || s.chosenDirection || ((s.fairLine != null && s.marketLine != null && s.fairLine >= s.marketLine) ? 'over' : 'under')
  const isOver = direction === 'over'
  const rationaleText = Array.isArray(s.rationale)
    ? (s.rationale.length > 1 ? s.rationale[s.rationale.length - 1] : s.rationale[0])
    : (s.rationale || '')

  const tierColors: Record<string, string> = {
    lock: 'bg-primary-container text-white',
    strong: 'bg-betting-green text-white',
    lean: 'bg-secondary-container text-white',
  }

  return (
    <div className="rounded-xl border border-outline/20 bg-surface-container-high overflow-hidden">
      {/* Direction banner */}
      <div className={`px-4 py-3 flex items-center justify-between ${isOver ? 'bg-betting-green/15' : 'bg-error/15'}`}>
        <div className="flex items-center gap-2">
          {s.tier && tierColors[s.tier] && (
            <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded tracking-wider ${tierColors[s.tier]}`}>
              {s.tier.toUpperCase()}
            </span>
          )}
          <span className="text-sm font-bold text-on-surface">{s.type}</span>
          {(s.confidenceSource === 'ml_blended' || s.rationaleSource === 'llm' || s.mlAvailable) && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 font-semibold">AI</span>
          )}
        </div>
        <span className={`text-sm font-extrabold px-3 py-1 rounded-full text-white tracking-wide ${isOver ? 'bg-betting-green' : 'bg-error'}`}>
          {isOver ? '▲ OVER' : '▼ UNDER'}
        </span>
      </div>

      {/* Stats grid */}
      <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        {s.marketLine != null && (
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">Market Line</span>
            <span className="text-lg font-bold text-on-surface">{typeof s.marketLine === 'number' ? (Number.isInteger(s.marketLine) ? s.marketLine : s.marketLine.toFixed(1)) : s.marketLine}</span>
          </div>
        )}
        {s.fairLine != null && (
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">Fair Line</span>
            <span className="text-lg font-bold text-primary-container">{typeof s.fairLine === 'number' ? s.fairLine.toFixed(1) : s.fairLine}</span>
          </div>
        )}
        {s.confidence != null && (
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">Confidence</span>
            <span className="text-lg font-bold text-on-surface">{Math.round(s.confidence > 1 ? s.confidence : s.confidence * 100)}%</span>
          </div>
        )}
        {s.hitRate != null && (
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">Hit Rate</span>
            <span className={`text-lg font-bold ${s.hitRate >= 75 ? 'text-betting-green' : s.hitRate >= 65 ? 'text-primary-container' : 'text-on-surface'}`}>
              {typeof s.hitRate === 'number' && s.hitRate <= 1 ? (s.hitRate * 100).toFixed(0) : s.hitRate?.toFixed?.(0) ?? s.hitRate}%
            </span>
          </div>
        )}
        {typeof s.streak === 'number' && s.streak >= 3 && (
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">Streak</span>
            <span className="text-lg font-bold text-amber-400">{s.streak}G</span>
          </div>
        )}
        {typeof s.consistency === 'number' && s.consistency > 0 && (
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">Consistency</span>
            <span className="text-lg font-bold text-on-surface">{(s.consistency * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>

      {/* Rationale */}
      {rationaleText && (
        <div className="px-4 pb-3">
          <div className="p-3 rounded-lg bg-surface-container border border-outline/20">
            <p className="text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-1.5">Analysis</p>
            <p className="text-sm text-on-surface leading-relaxed">{rationaleText}</p>
          </div>
        </div>
      )}

      {/* Matchup explanation */}
      {s.matchup_explanation && (
        <div className="px-4 pb-3">
          <div className="p-3 rounded-lg bg-amber-900/10 border border-amber-400/20">
            <p className="text-xs font-medium text-amber-400 uppercase tracking-wider mb-1.5">Matchup Insight</p>
            <p className="text-sm text-on-surface leading-relaxed">{s.matchup_explanation}</p>
          </div>
        </div>
      )}

      {/* View profile link */}
      {(playerId ?? s.playerId) && (playerName ?? s.playerName) && (
        <div className="px-4 pb-4">
          <Link
            to={`/player/${playerId ?? s.playerId}`}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary-container hover:underline"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
            </svg>
            View {playerName ?? s.playerName}'s Full Profile
          </Link>
        </div>
      )}
    </div>
  )
}

export function QuickPropLab() {
  const { season: globalSeason } = useSeason()
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  const [propType, setPropType] = useState<PropType>('PTS')
  const [line, setLine] = useState<string>('')
  const [season, setSeason] = useState<string>(globalSeason)
  const [lastN, setLastN] = useState<number | ''>('')
  const [home, setHome] = useState<'any'|'home'|'away'>('any')
  const [result, setResult] = useState<{ suggestions?: Array<{ type: string }> } | null>(null)
  const [runError, setRunError] = useState<string | null>(null)

  const canRun = !!player?.id && line !== ''

  const run = useMutation({
    mutationFn: async () => {
      if (!player?.id) return { suggestions: [] }
      setRunError(null)
      const body = {
        playerId: player.id,
        season: season || undefined,
        lastN: lastN || undefined,
        home: home === 'any' ? undefined : home,
        marketLines: { [propType]: Number(line) },
      }
      return apiPost<{ suggestions?: Array<{ type: string }> }>('/api/v1/props/player', body)
    },
    onSuccess: (data) => {
      setResult(data ?? { suggestions: [] })
      setRunError(null)
    },
    onError: (err: Error & { response?: { status: number } }) => {
      setResult(null)
      const status = err?.response?.status
      if (status === 429) {
        setRunError('Too many requests. Please wait a minute and try again.')
      } else {
        setRunError(err?.message || 'Request failed. Check your connection and try again.')
      }
    },
  })

  useEffect(() => {
    if (!player?.id) setResult(null)
  }, [player?.id])

  const suggestions = useMemo(() => {
    const items = result?.suggestions || []
    return items.filter((s) => s.type === propType)
  }, [result, propType])

  return (
    <div className="overflow-hidden rounded-lg bg-surface-container border border-outline/20 shadow-sm transition-colors duration-200">
      {/* Header */}
      <div className="px-2.5 sm:px-3 py-1.5 sm:py-2 border-b border-outline/20 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 transition-colors duration-200">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1">
          <div>
            <h3 className="text-sm sm:text-base font-semibold text-on-surface transition-colors duration-200">Quick Prop Lab</h3>
            <p className="text-[10px] sm:text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">Test any prop line instantly</p>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-2.5 sm:p-3 space-y-3">
        {/* Player Search */}
        <div>
          <label className="block text-xs font-medium text-on-surface-variant mb-1.5 transition-colors duration-200">Select Player</label>
          <PlayerSearch onSelect={setPlayer} />
        </div>

        {/* Prop Type Selection */}
        <div>
          <label className="block text-xs font-medium text-on-surface-variant mb-1.5 transition-colors duration-200">Prop Type</label>
          <div className="flex gap-2 flex-wrap">
            {TYPES.map((t) => (
              <button 
                key={t} 
                onClick={() => setPropType(t)} 
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all duration-200 ${
                  propType === t 
                    ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700 shadow-sm font-semibold' 
                    : 'bg-surface-container-high text-on-surface border-outline/30 hover:bg-surface-container-highest hover:border-outline/50'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Input Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1.5 transition-colors duration-200">Line</label>
            <input 
              value={line} 
              onChange={(e) => setLine(e.target.value)} 
              placeholder={`${propType} line (e.g. 24.5)`} 
              inputMode="decimal" 
              className="w-full px-2.5 py-2 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1.5 transition-colors duration-200">Season</label>
            <input 
              value={season} 
              onChange={(e) => setSeason(e.target.value)} 
              placeholder="2025-26" 
              className="w-full px-2.5 py-2 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1.5 transition-colors duration-200">Last N Games</label>
            <input 
              value={lastN} 
              onChange={(e) => setLastN(e.target.value ? Number(e.target.value) : '')} 
              type="number" 
              min={1} 
              placeholder="Optional" 
              className="w-full px-2.5 py-2 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-on-surface-variant mb-1.5 transition-colors duration-200">Venue</label>
            <select 
              value={home} 
              onChange={(e) => setHome(e.target.value as any)} 
              className="w-full px-2.5 py-2 pr-7 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            >
              <option value="any" className="bg-surface-container-high">Any</option>
              <option value="home" className="bg-surface-container-high">Home</option>
              <option value="away" className="bg-surface-container-high">Away</option>
            </select>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2 pt-1">
          <button 
            onClick={() => run.mutate()} 
            disabled={!canRun || run.isPending} 
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all duration-200 ${
              canRun && !run.isPending
                ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-700 hover:bg-purple-200 dark:hover:bg-purple-900/60 cursor-pointer shadow-sm hover:shadow-md'
                : 'bg-surface-container-highest text-on-surface-variant cursor-not-allowed opacity-60'
            }`}
          >
            {run.isPending ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Computing…
              </span>
            ) : (
              'Test Prop'
            )}
          </button>
          <span className="text-xs text-on-surface-variant transition-colors duration-200">Enter your book's line to see analysis</span>
        </div>

        {/* Error from API */}
        {runError && (
          <div className="pt-3 border-t border-outline/20">
            <p className="text-sm text-error" role="alert">{runError}</p>
            <button
              type="button"
              onClick={() => setRunError(null)}
              className="mt-2 text-xs text-on-surface-variant hover:text-primary-container"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Results */}
        {suggestions.length > 0 && (
          <div className="pt-3 border-t border-outline/20 transition-colors duration-200">
            <h4 className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-3">Analysis Result</h4>
            {suggestions.map((s, idx) => (
              <PropLabResult
                key={idx}
                s={s}
                playerName={player?.name}
                playerId={player?.id}
              />
            ))}
          </div>
        )}

        {/* Ran successfully but no suggestion (e.g. not enough data) */}
        {result != null && !run.isPending && suggestions.length === 0 && !runError && (
          <div className="pt-3 border-t border-outline/20 text-center py-3 text-sm text-amber-700 dark:text-amber-300">
            No suggestion for this line—player may not have enough data or didn&apos;t meet minimum minutes.
          </div>
        )}

        {/* Idle empty state */}
        {!canRun && !run.isPending && result == null && !runError && (
          <div className="text-center py-4 text-sm text-on-surface-variant transition-colors duration-200">
            Select a player and enter a line to test
          </div>
        )}
      </div>
    </div>
  )
}


