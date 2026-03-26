import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { analyzeAllGames, analyzeGame } from '../services/overUnderService'
import type { GameAnalysisResult } from '../types/overUnder'

const REFRESH_INTERVAL = 30000 // 30 seconds

function RecommendationBadge({ recommendation, confidence }: { recommendation: string; confidence: string }) {
  const getBadgeColor = () => {
    if (recommendation === 'OVER') return 'bg-betting-green'
    if (recommendation === 'UNDER') return 'bg-error'
    return 'bg-surface-container-high'
  }

  const getTextColor = () => {
    if (recommendation === 'OVER' || recommendation === 'UNDER') return 'text-white'
    return 'text-on-surface' // Darker text for NO BET
  }

  const getConfidenceColor = () => {
    if (confidence === 'HIGH') return 'text-green-300 dark:text-green-400'
    if (confidence === 'MEDIUM') return 'text-yellow-300 dark:text-amber-400'
    return 'text-on-surface-variant'
  }

  return (
    <div className="flex items-center gap-2">
      <span className={`px-3 py-1 rounded-full font-semibold ${getBadgeColor()} ${getTextColor()}`}>
        {recommendation}
      </span>
      {confidence !== 'N/A' && (
        <span className={`text-sm font-medium ${getConfidenceColor()}`}>
          {confidence} Confidence
        </span>
      )}
    </div>
  )
}

function GameCard({ gameResult }: { gameResult: GameAnalysisResult }) {
  const { game, analysis: initialAnalysis } = gameResult
  const gameId = gameResult.game_id // game_id is at the top level of gameResult, not in game object
  const [customLine, setCustomLine] = useState<string>('')
  const [analysis, setAnalysis] = useState(initialAnalysis)
  const [hasCustomAnalysis, setHasCustomAnalysis] = useState(false)
  
  // Sync analysis when gameResult prop changes (from auto-refresh)
  // But only if we don't have a custom analysis
  useEffect(() => {
    if (!hasCustomAnalysis) {
      setAnalysis(initialAnalysis)
    }
  }, [initialAnalysis, hasCustomAnalysis])
  
  // Mutation to analyze with custom line
  const analyzeWithLine = useMutation({
    mutationFn: async (line: number) => {
      if (!gameId) {
        throw new Error('Game ID is missing')
      }
      const data = await analyzeGame(gameId, line)
      if (!data.analysis) {
        throw new Error('No analysis data returned')
      }
      return data.analysis
    },
    onSuccess: (newAnalysis) => {
      console.log('Analysis updated with custom line:', newAnalysis)
      console.log('Recommendation:', newAnalysis.recommendation, 'Live line:', newAnalysis.live_line)
      setAnalysis(newAnalysis)
      setHasCustomAnalysis(true)
      // Clear the input after successful analysis
      setCustomLine('')
    },
    onError: (error) => {
      console.error('Error analyzing with custom line:', error)
    }
  })
  
  const handleLineSubmit = () => {
    const lineValue = parseFloat(customLine)
    if (isNaN(lineValue) || lineValue <= 0) {
      console.warn('Invalid line value:', customLine)
      return
    }
    console.log('Submitting custom line:', lineValue, 'for game:', gameId)
    analyzeWithLine.mutate(lineValue)
  }
  
  // Debounce timer ref
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  const handleLineChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setCustomLine(value)
    
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    
    // Only analyze if value is valid and we have a game ID
    const lineValue = parseFloat(value)
    if (!isNaN(lineValue) && lineValue > 0 && gameId) {
      // Debounce the analysis - wait 1 second after user stops typing
      debounceTimerRef.current = setTimeout(() => {
        console.log('Auto-analyzing with line:', lineValue, 'for game:', gameId)
        analyzeWithLine.mutate(lineValue)
      }, 1000) // 1 second delay
    }
  }
  
  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])
  
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      // Clear debounce and submit immediately
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
      handleLineSubmit()
    }
  }

  // Calculate the difference between projected and line
  const getRecommendationText = () => {
    if (analysis.recommendation === 'NO BET' || !analysis.live_line) {
      return null
    }
    
    const diff = analysis.projected_total - analysis.live_line
    if (analysis.recommendation === 'OVER') {
      return `Take the OVER - Projected ${diff.toFixed(1)} points above the line`
    } else if (analysis.recommendation === 'UNDER') {
      return `Take the UNDER - Projected ${Math.abs(diff).toFixed(1)} points below the line`
    }
    return null
  }

  const recommendationText = getRecommendationText()
  const diff = analysis.live_line ? analysis.projected_total - analysis.live_line : 0

  return (
    <div className="bg-surface border border-outline/30 p-8 rounded flex flex-col relative overflow-hidden group">
      {/* Tier badge */}
      {analysis.recommendation !== 'NO BET' && (
        <div className={`absolute top-0 right-0 px-6 py-2 font-black text-[10px] tracking-widest uppercase italic ${
          analysis.recommendation === 'OVER' ? 'bg-betting-green text-black' :
          analysis.recommendation === 'UNDER' ? 'bg-error text-black' :
          'bg-outline text-on-surface-variant'
        }`}>
          {analysis.confidence}
        </div>
      )}

      {/* Game Header */}
      <div className="flex items-center gap-5 mb-8">
        <div className="flex -space-x-4">
          <div className="w-14 h-14 border border-outline bg-surface-variant flex items-center justify-center font-black text-primary italic text-sm">
            {game.away_team.slice(0, 3).toUpperCase()}
          </div>
          <div className="w-14 h-14 border border-outline bg-surface-variant flex items-center justify-center font-black text-primary italic text-sm">
            {game.home_team.slice(0, 3).toUpperCase()}
          </div>
        </div>
        <div>
          <h4 className="text-xl font-black uppercase italic tracking-tight">
            {game.away_team} <span className="text-on-surface-variant text-sm lowercase font-normal not-italic px-1">vs</span> {game.home_team}
          </h4>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-widest font-bold">
            Q{game.quarter} · {game.time_remaining} · {game.away_score}-{game.home_score}
          </p>
        </div>
      </div>

      {/* Recommendation - Enhanced */}
      <div className="mb-4">
        {analysis.recommendation !== 'NO BET' && analysis.live_line ? (
          <div className={`border-2 rounded-lg p-4 ${
            analysis.recommendation === 'OVER' 
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          }`}>
            <div className="flex items-center gap-3 mb-2">
              <RecommendationBadge recommendation={analysis.recommendation} confidence={analysis.confidence} />
            </div>
            {recommendationText && (
              <p className={`text-base font-semibold mt-2 ${
                analysis.recommendation === 'OVER' 
                  ? 'text-green-900 dark:text-green-200' 
                  : 'text-red-900 dark:text-red-200'
              }`}>
                {recommendationText}
              </p>
            )}
            {analysis.edge_percentage > 0 && (
              <div className={`text-sm mt-2 ${
                analysis.recommendation === 'OVER' 
                  ? 'text-green-700 dark:text-green-300' 
                  : 'text-red-700 dark:text-red-300'
              }`}>
                <span className="font-semibold">Edge: {analysis.edge_percentage.toFixed(2)}%</span>
                {' | '}
                Projected: <span className="font-semibold">{analysis.projected_total.toFixed(1)}</span>
                {' vs '}
                Line: <span className="font-semibold">{analysis.live_line}</span>
                {' '}
                <span className={diff > 0 ? 'text-betting-green' : 'text-error'}>
                  ({diff > 0 ? '+' : ''}{diff.toFixed(1)})
                </span>
              </div>
            )}
            
            {/* Input box for changing the line even after recommendation */}
            <div className="mt-4 pt-4 border-t border-outline/20">
              <p className="text-xs text-on-surface-variant mb-2">Try a different line:</p>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={customLine}
                  onChange={handleLineChange}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter new line (e.g., 225.5)"
                  className="flex-1 px-3 py-2 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
                  step="0.5"
                  min="0"
                />
                <button
                  onClick={handleLineSubmit}
                  disabled={analyzeWithLine.isPending || !customLine || isNaN(parseFloat(customLine))}
                  className="px-4 py-2 text-sm font-medium text-on-surface bg-surface-container-high border border-outline/30 rounded-md hover:bg-surface-container-highest disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                  title="Or press Enter to analyze immediately"
                >
                  {analyzeWithLine.isPending ? 'Analyzing...' : 'Analyze'}
                </button>
              </div>
              {analyzeWithLine.isPending && (
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                  Analyzing with line {customLine}...
                </p>
              )}
              {analyzeWithLine.isError && (
                <p className="text-xs text-error mt-2">
                  Error: {analyzeWithLine.error instanceof Error ? analyzeWithLine.error.message : 'Failed to analyze. Please try again.'}
                </p>
              )}
              {customLine && !analyzeWithLine.isPending && !analyzeWithLine.isError && parseFloat(customLine) > 0 && (
                <p className="text-xs text-on-surface-variant mt-2">
                  Analysis will run automatically 1 second after you stop typing...
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-surface-container-low border border-outline/20 rounded p-4">
            <div className="flex items-center gap-2">
              <RecommendationBadge recommendation={analysis.recommendation} confidence={analysis.confidence} />
            </div>
            {!analysis.live_line && (
              <div className="mt-3">
                <p className="text-sm text-on-surface mb-3 font-medium">
                  No betting line provided. Projected total: <span className="font-semibold text-on-surface">{analysis.projected_total.toFixed(1)}</span>
                </p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={customLine}
                    onChange={handleLineChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter betting line (e.g., 225.5)"
                    className="flex-1 px-3 py-2 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
                    step="0.5"
                    min="0"
                  />
                  <button
                    onClick={handleLineSubmit}
                    disabled={analyzeWithLine.isPending || !customLine || isNaN(parseFloat(customLine))}
                    className="px-4 py-2 text-sm font-medium text-on-surface bg-surface-container-high border border-outline/30 rounded-md hover:bg-surface-container-highest disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                    title="Or press Enter to analyze immediately"
                  >
                    {analyzeWithLine.isPending ? 'Analyzing...' : 'Analyze'}
                  </button>
                </div>
                {analyzeWithLine.isPending && (
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                    Analyzing with line {customLine}...
                  </p>
                )}
                {analyzeWithLine.isError && (
                  <p className="text-xs text-error mt-2">
                    Error: {analyzeWithLine.error instanceof Error ? analyzeWithLine.error.message : 'Failed to analyze. Please try again.'}
                  </p>
                )}
                {customLine && !analyzeWithLine.isPending && !analyzeWithLine.isError && parseFloat(customLine) > 0 && (
                  <p className="text-xs text-on-surface-variant mt-2">
                    Analysis will run automatically 1 second after you stop typing...
                  </p>
                )}
              </div>
            )}
            {analysis.live_line && analysis.recommendation === 'NO BET' && (
              <div className="mt-3">
                <p className="text-sm text-on-surface font-medium">
                  No clear edge. Projected: <span className="font-semibold">{analysis.projected_total.toFixed(1)}</span> vs Line: <span className="font-semibold">{analysis.live_line}</span> (difference: <span className={Math.abs(diff) < 3 ? 'text-on-surface-variant' : 'text-on-surface'}>{diff > 0 ? '+' : ''}{diff.toFixed(1)}</span>)
                </p>
                <div className="flex items-center gap-2 mt-3">
                  <input
                    type="number"
                    value={customLine}
                    onChange={handleLineChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter new line (e.g., 225.5)"
                    className="flex-1 px-3 py-2 text-sm border border-outline/30 rounded-md text-on-surface bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
                    step="0.5"
                    min="0"
                  />
                  <button
                    onClick={handleLineSubmit}
                    disabled={analyzeWithLine.isPending || !customLine || isNaN(parseFloat(customLine))}
                    className="px-4 py-2 text-sm font-medium text-on-surface bg-surface-container-high border border-outline/30 rounded-md hover:bg-surface-container-highest disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                    title="Or press Enter to analyze immediately"
                  >
                    {analyzeWithLine.isPending ? 'Analyzing...' : 'Analyze'}
                  </button>
                </div>
                {analyzeWithLine.isPending && (
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                    Analyzing with line {customLine}...
                  </p>
                )}
                {analyzeWithLine.isError && (
                  <p className="text-xs text-error mt-2">
                    Error: {analyzeWithLine.error instanceof Error ? analyzeWithLine.error.message : 'Failed to analyze. Please try again.'}
                  </p>
                )}
                {customLine && !analyzeWithLine.isPending && !analyzeWithLine.isError && parseFloat(customLine) > 0 && (
                  <p className="text-xs text-on-surface-variant mt-2">
                    Analysis will run automatically 1 second after you stop typing...
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Analysis Details */}
      <div className="grid grid-cols-2 gap-4 mb-4 border-t border-outline/20 pt-4">
        <div className="bg-surface-container-low rounded border border-outline/20 p-3">
          <div className="text-xs font-black uppercase tracking-widest text-on-surface-variant">Projected Total</div>
          <div className="text-lg font-semibold text-on-surface">
            {analysis.projected_total.toFixed(1)}
          </div>
        </div>
        {analysis.live_line && (
          <div className="bg-surface-container-low rounded border border-outline/20 p-3">
            <div className="text-xs font-black uppercase tracking-widest text-on-surface-variant">Live Line</div>
            <div className="text-lg font-semibold text-on-surface">
              {analysis.live_line}
            </div>
            {analysis.recommendation !== 'NO BET' && (
              <div className="text-xs mt-1">
                <span className={diff > 0 ? 'text-betting-green' : 'text-error'}>
                  {diff > 0 ? '↑' : '↓'} {Math.abs(diff).toFixed(1)} from projected
                </span>
              </div>
            )}
          </div>
        )}
        <div className="bg-surface-container-low rounded border border-outline/20 p-3">
          <div className="text-xs font-black uppercase tracking-widest text-on-surface-variant">Current Pace</div>
          <div className="text-lg font-semibold text-on-surface">
            {analysis.current_pace.toFixed(1)}
          </div>
        </div>
        <div className="bg-surface-container-low rounded border border-outline/20 p-3">
          <div className="text-xs font-black uppercase tracking-widest text-on-surface-variant">Expected Pace</div>
          <div className="text-lg font-semibold text-on-surface">
            {analysis.expected_pace.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Key Factors */}
      {analysis.key_factors.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-on-surface-variant mb-2">Key Factors</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-on-surface-variant">
            {analysis.key_factors.map((factor, idx) => (
              <li key={idx}>{factor}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Reasoning */}
      {analysis.reasoning && (
        <div className="mt-4 pt-4 border-t border-outline/20">
          <p className="text-sm text-on-surface-variant leading-relaxed">
            {analysis.reasoning}
          </p>
        </div>
      )}

    </div>
  )
}

function LoadingProgressBar({
  progress,
  status,
  subtle = false,
}: {
  progress: number
  status: string
  subtle?: boolean
}) {
  return (
    <div
      className={`rounded border border-outline/20 bg-surface-container backdrop-blur-sm shadow-sm transition-colors duration-200 ${
        subtle ? 'p-4' : 'p-6'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
          <p className="text-sm font-medium text-on-surface">{status}</p>
        </div>
        <span className="text-sm font-semibold text-on-surface">
          {Math.min(progress, 100)}%
        </span>
      </div>
      <div className="h-3 rounded-full bg-surface-container-high overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-primary-container via-secondary-container to-tertiary-container transition-[width] duration-300 ease-out"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  )
}

export default function OverUnderPage() {
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [progress, setProgress] = useState(0)
  const [progressStatus, setProgressStatus] = useState('Connecting to live feeds…')
  const [showProgress, setShowProgress] = useState(false)
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['over-under-analysis'],
    queryFn: analyzeAllGames,
    refetchInterval: autoRefresh ? REFRESH_INTERVAL : false,
  })

  const updateStatusFor = useCallback((value: number) => {
    if (value < 15) {
      setProgressStatus('Connecting to live data feeds…')
    } else if (value < 40) {
      setProgressStatus('Pulling latest betting lines…')
    } else if (value < 65) {
      setProgressStatus('Crunching pace and scoring models…')
    } else if (value < 90) {
      setProgressStatus('Comparing projections vs live lines…')
    } else if (value < 100) {
      setProgressStatus('Finalizing edge calculations…')
    } else {
      setProgressStatus('Wrapping up live insights…')
    }
  }, [])

  const startProgress = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
    setShowProgress(true)
    setProgress(5)
    updateStatusFor(5)

    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current)
    }

    progressTimerRef.current = setInterval(() => {
      setProgress(prev => {
        const increment = prev < 30 ? 8 : prev < 60 ? 5 : prev < 85 ? 2 : 1
        const nextValue = Math.min(prev + increment, 95)
        updateStatusFor(nextValue)
        return nextValue
      })
    }, 400)
  }, [updateStatusFor])

  const stopProgress = useCallback(() => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current)
      progressTimerRef.current = null
    }
    setProgress(100)
    updateStatusFor(100)
    hideTimerRef.current = setTimeout(() => {
      setShowProgress(false)
      setProgress(0)
    }, 600)
  }, [updateStatusFor])

  useEffect(() => {
    const active = isLoading || isFetching
    if (active) {
      startProgress()
    } else if (showProgress) {
      stopProgress()
    }
  }, [isLoading, isFetching, startProgress, stopProgress, showProgress])

  useEffect(() => {
    return () => {
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current)
      }
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current)
      }
    }
  }, [])

  // Manual refresh handler
  const handleRefresh = () => {
    refetch()
  }

  if (isLoading && !data) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          <LoadingProgressBar progress={progress} status={progressStatus} />
          <div className="text-center py-8 rounded-2xl bg-surface-container border border-outline/20 shadow-sm">
            <div className="mx-auto h-12 w-12 rounded-full border-4 border-outline/30 border-t-primary-container animate-spin" />
            <p className="mt-4 text-sm text-on-surface-variant">
              Live odds and scoring data take a bit longer—hang tight while we load everything.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Analysis</h3>
          <p className="text-red-600 dark:text-red-300 text-sm">
            {error instanceof Error ? error.message : 'Failed to load game analysis'}
          </p>
          <button
            onClick={handleRefresh}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const games = data?.games ?? []
  const showInlineProgress = showProgress && Boolean(data)

  return (
    <div className="bg-background min-h-screen">
      {/* ── Page Header ── */}
      <div className="max-w-7xl mx-auto px-8 pt-8 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="font-black text-5xl md:text-7xl text-on-surface tracking-tighter leading-[0.9] uppercase italic">
            OVER/UNDER <span className="text-primary-container">INTELLIGENCE</span>
          </h1>
          <p className="mt-3 text-on-surface-variant max-w-lg font-medium tracking-tight">
            Kinetic high-density performance ledger. {games.length} game{games.length !== 1 ? 's' : ''} analyzed for today's slate using proprietary hardwood modeling.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-6 py-3.5 bg-primary-container text-on-primary font-black text-sm tracking-widest rounded hover:brightness-110 transition-all active:scale-95 uppercase"
          >
            <span className="material-symbols-outlined">psychology</span>
            ANALYZE SLATE
          </button>
          <label className="flex items-center justify-center p-3.5 bg-surface-variant text-on-surface rounded hover:bg-surface-container-highest transition-colors cursor-pointer gap-2 text-xs font-bold uppercase tracking-widest">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-3.5 h-3.5 accent-primary"
            />
            Auto-refresh
          </label>
        </div>
      </div>

      {showInlineProgress && (
        <div className="max-w-7xl mx-auto px-8 mb-4">
          <LoadingProgressBar progress={progress} status={progressStatus} subtle />
        </div>
      )}

      {/* ── Games Grid ── */}
      <div className="max-w-7xl mx-auto px-8 pb-8">
        {games.length === 0 ? (
          <div className="bg-primary-container/10 border-2 border-dashed border-primary-container/30 p-12 rounded flex flex-col items-center justify-center text-center gap-6">
            <div className="w-16 h-16 bg-surface-container rounded flex items-center justify-center">
              <span className="material-symbols-outlined text-4xl text-on-surface/30">sensors</span>
            </div>
            <div>
              <h4 className="text-2xl font-black text-primary-container uppercase italic tracking-tighter">NO LIVE GAMES</h4>
              <p className="text-xs text-on-surface/70 max-w-xs mt-2 font-medium uppercase tracking-widest">
                Check back during NBA game times to see live analysis.
              </p>
            </div>
          </div>
        ) : (
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {games.map((gameResult) => (
              <GameCard key={gameResult.game_id} gameResult={gameResult} />
            ))}
          </section>
        )}
      </div>
    </div>
  )
}

