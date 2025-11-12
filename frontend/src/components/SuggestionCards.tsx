import { Link } from 'react-router-dom'

type Direction = 'over' | 'under'
type SuggestionItem = {
  type: string
  marketLine?: number
  fairLine?: number
  confidence?: number
  rationale?: string[]
  chosenDirection?: Direction
  betterDirection?: Direction
  playerId?: number
  playerName?: string
  hitRate?: number
  sampleSize?: number
}

export function SuggestionCards({ suggestions, horizontal = false }: { suggestions: SuggestionItem[]; horizontal?: boolean }) {
  const CardContent = ({ s }: { s: SuggestionItem }) => (
    <>
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            <strong className="text-xs font-bold text-gray-900 dark:text-slate-100 truncate transition-colors duration-200">{s.type}</strong>
            {s.playerId && s.playerName && (
              <Link to={`/player/${s.playerId}`} className="text-[10px] text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 truncate transition-colors duration-200 hover:underline" title={s.playerName}>{s.playerName}</Link>
            )}
          </div>
          {s.marketLine != null && (
            (() => {
              const impliedOver = (s.fairLine != null && s.marketLine != null) ? (s.fairLine - s.marketLine) >= 0 : true
              const dir = (s.chosenDirection === 'over' || s.chosenDirection === 'under') ? s.chosenDirection : (impliedOver ? 'over' : 'under')
              const bg = dir === 'over' ? '#10B981' : '#EF4444'
              return <span className="text-[10px] px-1.5 py-0.5 rounded-full text-white font-semibold whitespace-nowrap" style={{ background: bg }}>{dir === 'over' ? 'O' : 'U'}</span>
            })()
          )}
        </div>
        {s.marketLine != null ? (
          <div className="space-y-0.5 text-[10px] text-gray-700 dark:text-gray-300 transition-colors duration-200">
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Market:</span>
              <span className="font-semibold dark:text-slate-100 transition-colors duration-200">{s.marketLine}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Fair:</span>
              <span className="font-semibold dark:text-slate-100 transition-colors duration-200">{s.fairLine != null ? s.fairLine.toFixed(1) : '—'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Edge:</span>
              <span className={`font-bold transition-colors duration-200 ${s.fairLine != null && s.marketLine != null && (s.fairLine - s.marketLine) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {s.fairLine != null && s.marketLine != null ? (s.fairLine - s.marketLine >= 0 ? '+' : '') + (s.fairLine - s.marketLine).toFixed(1) : '—'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Conf:</span>
              <span className="font-bold text-blue-700 dark:text-blue-400 transition-colors duration-200">{s.confidence != null ? Math.round((s.confidence > 1 ? s.confidence : s.confidence * 100)) + '%' : '—'}</span>
            </div>
            {s.hitRate != null && (
              <div className={`flex justify-between items-center text-[10px] transition-colors duration-200 ${s.hitRate >= 75 ? 'text-green-700 dark:text-green-400' : s.hitRate >= 65 ? 'text-blue-700 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'}`}>
              <span>Hit:</span>
              <span className="font-bold">{s.hitRate.toFixed(0)}%</span>
            </div>
            )}
            {s.betterDirection && s.chosenDirection && s.betterDirection !== s.chosenDirection && (
              <div className="mt-1">
                <span className="text-[9px] px-1.5 py-0.5 rounded-full text-gray-800 dark:text-gray-200 bg-yellow-200 dark:bg-yellow-900/40 font-semibold transition-colors duration-200">
                  Better: {s.betterDirection === 'over' ? 'O' : 'U'}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="text-[10px] text-gray-700 dark:text-gray-300 transition-colors duration-200">
            <span className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Fair:</span> <span className="font-semibold dark:text-slate-100 transition-colors duration-200">{s.fairLine?.toFixed?.(1) ?? '-'}</span>
          </div>
        )}
      </div>
      {Array.isArray(s.rationale) && s.rationale.length > 0 && (
        <div className="mt-2 p-2 bg-gray-50 dark:bg-slate-700/50 rounded border border-gray-200 dark:border-slate-600 transition-colors duration-200">
          <div className="text-[9px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1 transition-colors duration-200">
            Analysis
          </div>
          {(s.rationale || []).slice(0, 1).map((r: string, i: number) => {
            // Parse rationale text to extract key information
            const parseRationale = (text: string) => {
              const parts: { type: 'trend' | 'hitRate' | 'text'; value?: string; percentage?: number; line?: number }[] = []
              
              // Extract form trend (Up/Down/Flat)
              const trendMatch = text.match(/\b(Up|Down|Flat)\s+form/i)
              if (trendMatch) {
                parts.push({ 
                  type: 'trend', 
                  value: trendMatch[1],
                  percentage: trendMatch[1].toLowerCase() === 'up' ? 75 : trendMatch[1].toLowerCase() === 'down' ? 25 : 50
                })
              }
              
              // Extract hit rate percentage
              const hitRateMatch = text.match(/(\d+(?:\.\d+)?)%\s+hit/i)
              if (hitRateMatch) {
                parts.push({ 
                  type: 'hitRate', 
                  percentage: parseFloat(hitRateMatch[1])
                })
              }
              
              // Extract line value
              const lineMatch = text.match(/over\s+(\d+(?:\.\d+)?)/i) || text.match(/under\s+(\d+(?:\.\d+)?)/i)
              if (lineMatch) {
                parts.push({ 
                  type: 'text', 
                  line: parseFloat(lineMatch[1])
                })
              }
              
              return { parts, original: text }
            }
            
            const parsed = parseRationale(r)
            const trend = parsed.parts.find(p => p.type === 'trend')
            const hitRate = parsed.parts.find(p => p.type === 'hitRate')
            const line = parsed.parts.find(p => p.line)
            
            return (
              <div key={i} className="space-y-1">
                <div className="flex flex-wrap gap-1 items-center">
                  {trend && (
                    <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold transition-colors duration-200 ${
                      trend.value?.toLowerCase() === 'up' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' : 
                      trend.value?.toLowerCase() === 'down' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300' : 
                      'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
                    }`}>
                      <span>{trend.value === 'Up' ? '📈' : trend.value === 'Down' ? '📉' : '➡️'}</span>
                      <span>{trend.value}</span>
                    </div>
                  )}
                  {hitRate && (
                    <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold transition-colors duration-200 ${
                      hitRate.percentage! >= 75 ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' : 
                      hitRate.percentage! >= 65 ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300' : 
                      'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300'
                    }`}>
                      <span>{hitRate.percentage}%</span>
                    </div>
                  )}
                  {line && (
                    <div className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 text-gray-800 dark:text-slate-100 transition-colors duration-200">
                      <span>L:{line.line}</span>
                    </div>
                  )}
                </div>
                {!trend && !hitRate && (
                  <div className="text-[10px] text-gray-600 dark:text-gray-400 line-clamp-2 transition-colors duration-200">
                    {r}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </>
  )

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
