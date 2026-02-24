import { Link } from 'react-router-dom'

type Direction = 'over' | 'under'
type SuggestionItem = {
  type: string
  marketLine?: number
  fairLine?: number
  confidence?: number
  rationale?: string[] | string
  chosenDirection?: Direction
  betterDirection?: Direction
  suggestion?: string
  playerId?: number
  playerName?: string
  hitRate?: number
  sampleSize?: number
  tier?: 'lock' | 'strong' | 'lean'
  streak?: number
  consistency?: number
}

const TIER_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  lock: { bg: 'bg-gradient-to-r from-yellow-400 to-amber-500', text: 'text-white', label: 'LOCK' },
  strong: { bg: 'bg-gradient-to-r from-emerald-500 to-green-600', text: 'text-white', label: 'STRONG' },
  lean: { bg: 'bg-gradient-to-r from-sky-400 to-blue-500', text: 'text-white', label: 'LEAN' },
}

function TierBadge({ tier }: { tier?: string }) {
  if (!tier) return null
  const style = TIER_STYLES[tier]
  if (!style) return null
  return (
    <span className={`${style.bg} ${style.text} text-[9px] font-extrabold px-1.5 py-0.5 rounded-full tracking-wider shadow-sm`}>
      {style.label}
    </span>
  )
}

export function SuggestionCards({ suggestions, horizontal = false }: { suggestions: SuggestionItem[]; horizontal?: boolean }) {
  const CardContent = ({ s }: { s: SuggestionItem }) => {
    const direction = s.suggestion || s.chosenDirection || ((s.fairLine != null && s.marketLine != null && s.fairLine >= s.marketLine) ? 'over' : 'under')
    const isOver = direction === 'over'
    const rationaleText = Array.isArray(s.rationale) ? s.rationale[0] : (s.rationale || '')

    return (
      <>
        {/* Header: tier + direction */}
        <div className="flex items-center justify-between gap-1 mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            <TierBadge tier={s.tier} />
            <strong className="text-xs font-bold text-gray-900 dark:text-slate-100 truncate transition-colors duration-200">{s.type}</strong>
          </div>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded-full text-white font-semibold whitespace-nowrap ${isOver ? 'bg-emerald-500' : 'bg-red-500'}`}
          >
            {isOver ? 'OVER' : 'UNDER'}
          </span>
        </div>

        {/* Player name */}
        {s.playerId && s.playerName && (
          <Link
            to={`/player/${s.playerId}`}
            className="block text-[11px] text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 truncate transition-colors duration-200 hover:underline mb-1.5"
            title={s.playerName}
          >
            {s.playerName}
          </Link>
        )}

        {/* Stats grid */}
        <div className="space-y-0.5 text-[10px] text-gray-700 dark:text-gray-300 transition-colors duration-200">
          {s.marketLine != null && (
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400">Line:</span>
              <span className="font-bold text-gray-900 dark:text-slate-100">{s.marketLine}</span>
            </div>
          )}
          {s.confidence != null && (
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400">Conf:</span>
              <span className="font-bold text-blue-700 dark:text-blue-400">{Math.round(s.confidence > 1 ? s.confidence : s.confidence * 100)}%</span>
            </div>
          )}
          {s.hitRate != null && (
            <div className={`flex justify-between items-center ${s.hitRate >= 75 ? 'text-green-700 dark:text-green-400' : s.hitRate >= 65 ? 'text-blue-700 dark:text-blue-400' : ''}`}>
              <span>Hit Rate:</span>
              <span className="font-bold">{typeof s.hitRate === 'number' && s.hitRate <= 1 ? (s.hitRate * 100).toFixed(0) : s.hitRate?.toFixed?.(0) ?? s.hitRate}%</span>
            </div>
          )}
          {typeof s.streak === 'number' && s.streak >= 3 && (
            <div className="flex justify-between items-center text-amber-600 dark:text-amber-400">
              <span>Streak:</span>
              <span className="font-bold">{s.streak} games</span>
            </div>
          )}
          {typeof s.consistency === 'number' && s.consistency > 0 && (
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400">Consist:</span>
              <span className="font-semibold">{(s.consistency * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>

        {/* Rationale */}
        {rationaleText && (
          <div className="mt-2 p-1.5 bg-gray-50 dark:bg-slate-700/50 rounded border border-gray-200 dark:border-slate-600 transition-colors duration-200">
            <div className="flex flex-wrap gap-1 items-center">
              {(() => {
                const trendMatch = rationaleText.match(/\b(Up|Down|Flat)\s+form/i)
                const hitRateMatch = rationaleText.match(/(\d+(?:\.\d+)?)%\s+hit/i)
                const streakMatch = rationaleText.match(/(\d+)-game streak/i)
                const consistMatch = rationaleText.match(/very consistent|consistent/i)
                return (
                  <>
                    {trendMatch && (
                      <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                        trendMatch[1].toLowerCase() === 'up' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                        trendMatch[1].toLowerCase() === 'down' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300' :
                        'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
                      }`}>
                        {trendMatch[1] === 'Up' ? '↑' : trendMatch[1] === 'Down' ? '↓' : '→'} {trendMatch[1]}
                      </span>
                    )}
                    {hitRateMatch && (
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold ${
                        parseFloat(hitRateMatch[1]) >= 75 ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                        'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300'
                      }`}>
                        {hitRateMatch[1]}%
                      </span>
                    )}
                    {streakMatch && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300">
                        {streakMatch[1]}x
                      </span>
                    )}
                    {consistMatch && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300">
                        {consistMatch[0]}
                      </span>
                    )}
                    {!trendMatch && !hitRateMatch && (
                      <span className="text-[9px] text-gray-600 dark:text-gray-400 line-clamp-2">{rationaleText}</span>
                    )}
                  </>
                )
              })()}
            </div>
          </div>
        )}
      </>
    )
  }

  if (horizontal) {
    return (
      <div className="overflow-x-auto -mx-2.5 px-2.5 pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100" style={{ scrollbarWidth: 'thin' }}>
        <div className="flex gap-2.5 min-w-max">
          {suggestions.map((s: SuggestionItem, idx: number) => (
            <div key={idx} className="flex-none w-48 sm:w-56 p-2.5 sm:p-3 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 shadow-sm hover:shadow-md transition-all duration-200">
              <CardContent s={s} />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="w-full">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-2 md:gap-3">
        {suggestions.map((s: SuggestionItem, idx: number) => (
          <div key={idx} className="p-2.5 sm:p-3 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 shadow-sm hover:shadow-md transition-all duration-200">
            <CardContent s={s} />
          </div>
        ))}
      </div>
    </div>
  )
}
