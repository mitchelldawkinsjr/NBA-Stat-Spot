import { useState, useEffect } from 'react'
import type { Filters, PropSuggestionsResponse, Player } from '../types/api'
import { apiPost } from '../utils/api'

export type { Filters }

export function FiltersPanel({ 
  value, 
  onChange, 
  player, 
  onEvaluate 
}: { 
  value: Filters
  onChange: (f: Filters) => void
  player?: Player | null
  onEvaluate?: (result: PropSuggestionsResponse) => void
}) {
  const [local, setLocal] = useState<Filters>(value)
  const [isEvaluating, setIsEvaluating] = useState(false)

  useEffect(() => { setLocal(value) }, [value])
  useEffect(() => { onChange(local) }, [local])

  const hasMarketLines = local.marketLines && Object.values(local.marketLines).some((v) => v && v !== '')

  const handleEvaluate = async () => {
    if (!player || !player.id || !hasMarketLines) {
      return
    }
    
    setIsEvaluating(true)
    // Clear previous result when starting new evaluation (set to loading state)
    if (onEvaluate) {
      onEvaluate({ suggestions: [], loading: true })
    }
    try {
      const marketLines = Object.fromEntries(
        Object.entries(local.marketLines || {})
          .map(([k, v]) => [k, v === '' ? undefined : Number(v)])
          .filter(([, v]) => v !== undefined && Number.isFinite(v as number))
      ) as Record<string, number>
      
      const data = await apiPost('api/v1/props/player', {
        playerId: player.id,
        season: local.season || undefined,
        lastN: local.lastN || undefined,
        home: local.home === 'any' ? undefined : local.home,
        marketLines,
        direction: local.direction || 'over',
      })
      // Ensure result has suggestions array and remove loading flag
      const result = {
        suggestions: data.suggestions || [],
        ...data,
        loading: false
      }
      if (onEvaluate) {
        onEvaluate(result)
      }
    } catch (error) {
      console.error('Failed to evaluate prop:', error)
      let errorMessage = 'Unknown error'
      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === 'object' && error !== null && 'response' in error) {
        const apiError = error as any
        errorMessage = apiError.response?.statusText || apiError.message || errorMessage
      }
      if (onEvaluate) {
        onEvaluate({ suggestions: [], error: errorMessage, loading: false })
      }
    } finally {
      setIsEvaluating(false)
    }
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3 p-3 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 transition-colors duration-200">
      <div>
        <label className="block text-xs text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">Season (e.g. 2024-25)</label>
        <input
          value={local.season ?? ''}
          onChange={(e) => setLocal((p) => ({ ...p, season: e.target.value }))}
          placeholder="YYYY-YY"
          className="w-full px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">Last N Games</label>
        <input
          type="number"
          min={1}
          value={local.lastN ?? ''}
          onChange={(e) => setLocal((p) => ({ ...p, lastN: e.target.value ? Number(e.target.value) : undefined }))}
          placeholder="10"
          className="w-full px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">Venue</label>
        <select
          value={local.home ?? 'any'}
          onChange={(e) => setLocal((p) => ({ ...p, home: e.target.value as Filters['home'] }))}
          className="w-full px-2.5 py-2 pr-7 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
        >
          <option value="any" className="text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700">Any</option>
          <option value="home" className="text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700">Home</option>
          <option value="away" className="text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700">Away</option>
        </select>
      </div>
      <div className="col-span-full">
        <div className="flex items-center gap-3 flex-wrap">
          <span title="Optional. Add your book's lines to compute edge/confidence." className="text-xs text-gray-900 dark:text-slate-100 transition-colors duration-200">Market Lines:</span>
          {(['PTS','REB','AST','3PM','PRA'] as const).map((k) => (
            <div key={k} className="flex items-center gap-1.5">
              <label className="w-9 text-xs text-gray-900 dark:text-slate-100 transition-colors duration-200">{k}</label>
              <input
                inputMode="decimal"
                aria-label={`${k} market line`}
                value={local.marketLines?.[k] ?? ''}
                onChange={(e) => {
                  const value = e.target.value
                  setLocal((p) => ({
                    ...p,
                    marketLines: {
                      ...(p.marketLines ?? {}),
                      [k]: value
                    }
                  }))
                }}
                placeholder="e.g. 24.5"
                className="w-24 px-2 py-1.5 text-xs border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
              />
            </div>
          ))}
          <div className="flex items-center gap-1.5 ml-auto">
            <label className="text-xs text-gray-900 dark:text-slate-100 font-medium transition-colors duration-200">Direction:</label>
            <div className="flex gap-0.5 border border-gray-300 dark:border-slate-600 rounded-md p-0.5 transition-colors duration-200">
              <button
                type="button"
                onClick={() => setLocal((p) => ({ ...p, direction: 'over' }))}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors duration-200 ${
                  local.direction === 'over' || !local.direction
                    ? 'bg-blue-700 dark:bg-blue-600 text-white'
                    : 'bg-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                Over
              </button>
              <button
                type="button"
                onClick={() => setLocal((p) => ({ ...p, direction: 'under' }))}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors duration-200 ${
                  local.direction === 'under'
                    ? 'bg-blue-700 dark:bg-blue-600 text-white'
                    : 'bg-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                Under
              </button>
            </div>
            <button
              type="button"
              onClick={handleEvaluate}
              disabled={!player || !player.id || !hasMarketLines || isEvaluating}
              className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-colors duration-200 ${
                !player || !player.id || !hasMarketLines || isEvaluating
                  ? 'bg-gray-300 dark:bg-slate-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                  : 'bg-blue-700 dark:bg-blue-600 text-white hover:bg-blue-800 dark:hover:bg-blue-700 cursor-pointer'
              }`}
            >
              {isEvaluating ? 'Evaluating...' : 'Evaluate'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
