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
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 p-3 transition-colors duration-200">
      <div className="font-semibold text-gray-900 dark:text-slate-100 mb-2 transition-colors duration-200">Quick Prop Lab</div>
      <div className="grid grid-cols-1 gap-2.5">
        <PlayerSearch onSelect={setPlayer} />
        <div className="flex gap-2 flex-wrap">
          {TYPES.map((t) => (
            <button 
              key={t} 
              onClick={() => setPropType(t)} 
              className={`px-2.5 py-1.5 rounded-full border transition-colors duration-200 ${
                propType === t 
                  ? 'bg-blue-900 dark:bg-blue-700 text-white border-blue-900 dark:border-blue-700' 
                  : 'bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <input 
            value={line} 
            onChange={(e) => setLine(e.target.value)} 
            placeholder={`${propType} line (e.g. 24.5)`} 
            inputMode="decimal" 
            className="px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
          />
          <input 
            value={season} 
            onChange={(e) => setSeason(e.target.value)} 
            placeholder="Season (e.g. 2025-26)" 
            className="px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
          />
          <input 
            value={lastN} 
            onChange={(e) => setLastN(e.target.value ? Number(e.target.value) : '')} 
            type="number" 
            min={1} 
            placeholder="Last N games" 
            className="px-2.5 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
          />
          <select 
            value={home} 
            onChange={(e) => setHome(e.target.value as any)} 
            className="px-2.5 py-2 pr-7 text-sm border border-gray-300 dark:border-slate-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
          >
            <option value="any" className="bg-white dark:bg-slate-700">Venue: Any</option>
            <option value="home" className="bg-white dark:bg-slate-700">Venue: Home</option>
            <option value="away" className="bg-white dark:bg-slate-700">Venue: Away</option>
          </select>
        </div>
        <div>
          <button 
            onClick={() => run.mutate()} 
            disabled={!canRun || run.isPending} 
            className={`px-3 py-2 text-sm font-medium rounded-md border transition-colors duration-200 ${
              canRun && !run.isPending
                ? 'bg-blue-900 dark:bg-blue-700 text-white border-blue-900 dark:border-blue-700 hover:bg-blue-800 dark:hover:bg-blue-600 cursor-pointer'
                : 'bg-gray-300 dark:bg-slate-600 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-slate-600 cursor-not-allowed opacity-60'
            }`}
          >
            {run.isPending ? 'Computing…' : 'Test Prop'}
          </button>
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">Enter your book's line to see Over/Under + Edge/Confidence.</span>
        </div>
        <div>
          {suggestions.length === 0 ? (
            <div className="text-gray-500 dark:text-gray-400 transition-colors duration-200">No result yet.</div>
          ) : (
            <>
              <SuggestionCards suggestions={suggestions} />
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}


