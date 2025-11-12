import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
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
        marketLines: { [propType]: Number(line) },
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
    <div className="overflow-hidden rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm transition-colors duration-200">
      {/* Header */}
      <div className="px-2.5 sm:px-3 py-1.5 sm:py-2 border-b border-gray-200 dark:border-slate-700 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 transition-colors duration-200">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1">
          <div>
            <h3 className="text-sm sm:text-base font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Quick Prop Lab</h3>
            <p className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Test any prop line instantly</p>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-2.5 sm:p-3 space-y-3">
        {/* Player Search */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Select Player</label>
          <PlayerSearch onSelect={setPlayer} />
        </div>

        {/* Prop Type Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Prop Type</label>
          <div className="flex gap-2 flex-wrap">
            {TYPES.map((t) => (
              <button 
                key={t} 
                onClick={() => setPropType(t)} 
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all duration-200 ${
                  propType === t 
                    ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700 shadow-sm font-semibold' 
                    : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600 hover:border-gray-400 dark:hover:border-slate-500'
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
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Line</label>
            <input 
              value={line} 
              onChange={(e) => setLine(e.target.value)} 
              placeholder={`${propType} line (e.g. 24.5)`} 
              inputMode="decimal" 
              className="w-full px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Season</label>
            <input 
              value={season} 
              onChange={(e) => setSeason(e.target.value)} 
              placeholder="2025-26" 
              className="w-full px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Last N Games</label>
            <input 
              value={lastN} 
              onChange={(e) => setLastN(e.target.value ? Number(e.target.value) : '')} 
              type="number" 
              min={1} 
              placeholder="Optional" 
              className="w-full px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Venue</label>
            <select 
              value={home} 
              onChange={(e) => setHome(e.target.value as any)} 
              className="w-full px-2.5 py-2 pr-7 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-colors duration-200"
            >
              <option value="any" className="bg-white dark:bg-slate-700">Any</option>
              <option value="home" className="bg-white dark:bg-slate-700">Home</option>
              <option value="away" className="bg-white dark:bg-slate-700">Away</option>
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
                : 'bg-gray-300 dark:bg-slate-600 text-gray-500 dark:text-gray-400 cursor-not-allowed opacity-60'
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
          <span className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">Enter your book's line to see analysis</span>
        </div>

        {/* Results */}
        {suggestions.length > 0 && (
          <div className="pt-3 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
            <div className="mb-3">
              <h4 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-200">Analysis Result</h4>
              <SuggestionCards suggestions={suggestions} />
            </div>
            {player && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
                <Link
                  to={`/player/${player.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-gray-100 dark:bg-slate-700 text-blue-600 dark:text-blue-400 rounded-md no-underline text-sm font-medium hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors duration-200"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                  </svg>
                  View {player.name}'s Profile
                </Link>
              </div>
            )}
          </div>
        )}
        
        {!canRun && !run.isPending && suggestions.length === 0 && (
          <div className="text-center py-4 text-sm text-gray-400 dark:text-gray-500 transition-colors duration-200">
            Select a player and enter a line to test
          </div>
        )}
      </div>
    </div>
  )
}


