import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { analyzeAllGames } from '../services/overUnderService'
import type { GameAnalysisResult } from '../types/overUnder'
import { apiFetch } from '../utils/api'

const REFRESH_INTERVAL = 30000 // 30 seconds

function RecommendationBadge({ recommendation, confidence }: { recommendation: string; confidence: string }) {
  const getBadgeColor = () => {
    if (recommendation === 'OVER') return 'bg-green-500'
    if (recommendation === 'UNDER') return 'bg-red-500'
    return 'bg-gray-600 dark:bg-gray-700'
  }

  const getTextColor = () => {
    if (recommendation === 'OVER' || recommendation === 'UNDER') return 'text-white'
    return 'text-gray-900 dark:text-gray-100' // Darker text for NO BET
  }

  const getConfidenceColor = () => {
    if (confidence === 'HIGH') return 'text-green-300'
    if (confidence === 'MEDIUM') return 'text-yellow-300'
    return 'text-gray-300'
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
      const response = await apiFetch(`api/v1/over-under/analyze/${gameId}?live_line=${line}`)
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to analyze game: ${response.status} ${errorText}`)
      }
      const data = await response.json()
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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-4 border border-gray-200 dark:border-gray-700">
      {/* Game Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            {game.away_team} @ {game.home_team}
          </h3>
          <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Q{game.quarter} - {game.time_remaining}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {game.away_score} - {game.home_score}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Total: {analysis.current_total}
          </div>
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
                <span className={diff > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                  ({diff > 0 ? '+' : ''}{diff.toFixed(1)})
                </span>
              </div>
            )}
            
            {/* Input box for changing the line even after recommendation */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">Try a different line:</p>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={customLine}
                  onChange={handleLineChange}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter new line (e.g., 225.5)"
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
                  step="0.5"
                  min="0"
                />
                <button
                  onClick={handleLineSubmit}
                  disabled={analyzeWithLine.isPending || !customLine || isNaN(parseFloat(customLine))}
                  className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
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
                <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                  Error: {analyzeWithLine.error instanceof Error ? analyzeWithLine.error.message : 'Failed to analyze. Please try again.'}
                </p>
              )}
              {customLine && !analyzeWithLine.isPending && !analyzeWithLine.isError && parseFloat(customLine) > 0 && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  Analysis will run automatically 1 second after you stop typing...
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <RecommendationBadge recommendation={analysis.recommendation} confidence={analysis.confidence} />
            </div>
            {!analysis.live_line && (
              <div className="mt-3">
                <p className="text-sm text-gray-800 dark:text-gray-200 mb-3 font-medium">
                  No betting line provided. Projected total: <span className="font-semibold text-gray-900 dark:text-white">{analysis.projected_total.toFixed(1)}</span>
                </p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={customLine}
                    onChange={handleLineChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter betting line (e.g., 225.5)"
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
                    step="0.5"
                    min="0"
                  />
                  <button
                    onClick={handleLineSubmit}
                    disabled={analyzeWithLine.isPending || !customLine || isNaN(parseFloat(customLine))}
                    className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
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
                  <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                    Error: {analyzeWithLine.error instanceof Error ? analyzeWithLine.error.message : 'Failed to analyze. Please try again.'}
                  </p>
                )}
                {customLine && !analyzeWithLine.isPending && !analyzeWithLine.isError && parseFloat(customLine) > 0 && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Analysis will run automatically 1 second after you stop typing...
                  </p>
                )}
              </div>
            )}
            {analysis.live_line && analysis.recommendation === 'NO BET' && (
              <div className="mt-3">
                <p className="text-sm text-gray-800 dark:text-gray-200 font-medium">
                  No clear edge. Projected: <span className="font-semibold">{analysis.projected_total.toFixed(1)}</span> vs Line: <span className="font-semibold">{analysis.live_line}</span> (difference: <span className={Math.abs(diff) < 3 ? 'text-gray-500 dark:text-gray-400' : 'text-gray-800 dark:text-gray-200'}>{diff > 0 ? '+' : ''}{diff.toFixed(1)}</span>)
                </p>
                <div className="flex items-center gap-2 mt-3">
                  <input
                    type="number"
                    value={customLine}
                    onChange={handleLineChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Enter new line (e.g., 225.5)"
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
                    step="0.5"
                    min="0"
                  />
                  <button
                    onClick={handleLineSubmit}
                    disabled={analyzeWithLine.isPending || !customLine || isNaN(parseFloat(customLine))}
                    className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
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
                  <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                    Error: {analyzeWithLine.error instanceof Error ? analyzeWithLine.error.message : 'Failed to analyze. Please try again.'}
                  </p>
                )}
                {customLine && !analyzeWithLine.isPending && !analyzeWithLine.isError && parseFloat(customLine) > 0 && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Analysis will run automatically 1 second after you stop typing...
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Analysis Details */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <div className="text-sm text-gray-600 dark:text-gray-400">Projected Total</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            {analysis.projected_total.toFixed(1)}
          </div>
        </div>
        {analysis.live_line && (
          <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
            <div className="text-sm text-gray-600 dark:text-gray-400">Live Line</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {analysis.live_line}
            </div>
            {analysis.recommendation !== 'NO BET' && (
              <div className="text-xs mt-1">
                <span className={diff > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                  {diff > 0 ? '↑' : '↓'} {Math.abs(diff).toFixed(1)} from projected
                </span>
              </div>
            )}
          </div>
        )}
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <div className="text-sm text-gray-600 dark:text-gray-400">Current Pace</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            {analysis.current_pace.toFixed(1)}
          </div>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <div className="text-sm text-gray-600 dark:text-gray-400">Expected Pace</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            {analysis.expected_pace.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Key Factors */}
      {analysis.key_factors.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Key Factors</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {analysis.key_factors.map((factor, idx) => (
              <li key={idx}>{factor}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Reasoning */}
      {analysis.reasoning && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {analysis.reasoning}
          </p>
        </div>
      )}

    </div>
  )
}

export default function OverUnderPage() {
  const [autoRefresh, setAutoRefresh] = useState(true)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['over-under-analysis'],
    queryFn: analyzeAllGames,
    refetchInterval: autoRefresh ? REFRESH_INTERVAL : false,
  })

  // Manual refresh handler
  const handleRefresh = () => {
    refetch()
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading game analysis...</p>
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

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Over/Under Analysis</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Live game analysis for over/under betting opportunities
          </p>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Auto-refresh (30s)</span>
          </label>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* Games List */}
      {games.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-12 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-gray-600 dark:text-gray-400 text-lg">
            No live games available at this time.
          </p>
          <p className="text-gray-500 dark:text-gray-500 text-sm mt-2">
            Check back during NBA game times to see live analysis.
          </p>
        </div>
      ) : (
        <div>
          {games.map((gameResult) => (
            <GameCard key={gameResult.game_id} gameResult={gameResult} />
          ))}
        </div>
      )}
    </div>
  )
}

