import { useMemo, useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { QuickPropLab } from './QuickPropLab'
import { DailyPropsPanel } from './DailyPropsPanel'
import { SuggestionCards } from './SuggestionCards'
import { useSeason } from '../context/SeasonContext'
import { useSnackbar } from '../context/SnackbarContext'
import { getCache, setCache, clearCache, getTodayDate } from '../utils/cache'

import { apiFetch } from '../utils/api'

async function fetchToday(date?: string) {
  const params = new URLSearchParams()
  if (date) params.append('date', date)
  const endpoint = `api/v1/games/today${params.toString() ? '?' + params.toString() : ''}`
  const res = await apiFetch(endpoint)
  if (!res.ok) {
    // Error handled by React Query - no console logging needed
    throw new Error(`Failed to load games: ${res.status}`)
  }
  const data = await res.json()
  return data
}

async function fetchDaily(minConfidence?: number, date?: string) {
  const targetDate = date || getTodayDate()
  const cacheKey = `daily-props-${minConfidence || 50}`
  
  // Check cache first
  const cached = getCache(cacheKey, targetDate)
  if (cached) {
    return cached
  }
  
  // Fetch from API
  const params = new URLSearchParams()
  if (minConfidence) params.append('min_confidence', minConfidence.toString())
  if (date) params.append('date', date)
  const endpoint = `api/v1/props/daily${params.toString() ? '?' + params.toString() : ''}`
  const res = await apiFetch(endpoint)
  if (!res.ok) throw new Error('Failed to load daily')
  const data = await res.json()
  
  // Cache the result
  setCache(cacheKey, data, targetDate)
  
  return data
}

async function fetchHighHitRate(date?: string) {
  const targetDate = date || getTodayDate()
  const cacheKey = 'high-hit-rate-0.75-6-10'
  
  // Check cache first
  const cached = getCache(cacheKey, targetDate)
  if (cached) {
    return cached
  }
  
  // Fetch from API
  const params = new URLSearchParams()
  params.append('min_hit_rate', '0.75')
  params.append('limit', '6')
  params.append('last_n', '10')
  if (date) params.append('date', date)
  const endpoint = `api/v1/props/high-hit-rate?${params.toString()}`
  const res = await apiFetch(endpoint)
  if (!res.ok) throw new Error('Failed to load high hit rate bets')
  const data = await res.json()
  
  // Cache the result
  setCache(cacheKey, data, targetDate)
  
  return data
}

async function fetchStatLeaders(season?: string) {
  const params = new URLSearchParams()
  if (season) params.append('season', season)
  params.append('limit', '3')
  const url = `api/v1/players/stat-leaders${params.toString() ? '?' + params.toString() : ''}`
  const res = await apiFetch(url)
  if (!res.ok) throw new Error('Failed to load stat leaders')
  return res.json()
}

export function GoodBetsDashboard() {
  const { season } = useSeason()
  const queryClient = useQueryClient()
  const { showSnackbar, updateProgress, hideSnackbar } = useSnackbar()
  const [shouldLoadHighHitRate, setShouldLoadHighHitRate] = useState(false)
  const [statLeadersFilterToday, setStatLeadersFilterToday] = useState(false) // Toggle for filtering by today - default to "All"
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  // Get today's date for filtering - use browser's local date/time (EST if user is in NY)
  const today = new Date().toLocaleDateString('en-CA') // YYYY-MM-DD format in browser's local timezone
  
  const { data: gamesData, isLoading: gamesLoading, error: gamesError, refetch: refetchGames } = useQuery({ 
    queryKey: ['games-today', today], 
    queryFn: () => fetchToday(today),
    staleTime: 0, // Always refetch
    refetchOnMount: true,
    refetchOnWindowFocus: true, // Refetch when window gains focus
    gcTime: 0, // Don't cache - always fetch fresh
  })
  
  const { data: dailyData, isLoading: dailyLoading, error: dailyError, refetch: refetchDaily } = useQuery({ 
    queryKey: ['daily-50', today], 
    queryFn: () => fetchDaily(50, today),
    staleTime: 30 * 60 * 1000, // 30 minutes - daily props only change once per day
    gcTime: 24 * 60 * 60 * 1000, // Keep in cache for 24 hours (entire day)
    refetchOnMount: false, // Use cache first, don't refetch on mount
    refetchOnWindowFocus: false, // Don't refetch when window gains focus
    refetchOnReconnect: false, // Don't refetch on reconnect
  })
  
  // Lazy load high hit rate after main dashboard loads
  useEffect(() => {
    if (!dailyLoading && !gamesLoading) {
      // Wait for the main dashboard to render, then load high hit rate
      // This prevents blocking the initial dashboard load
      const timer = setTimeout(() => {
        setShouldLoadHighHitRate(true)
      }, 1500) // 1.5 second delay to ensure smooth dashboard rendering
      return () => clearTimeout(timer)
    }
  }, [dailyLoading, gamesLoading])
  
  const { data: highHitRateData, isLoading: highHitRateLoading, refetch: refetchHighHitRate } = useQuery({ 
    queryKey: ['high-hit-rate', today], 
    queryFn: () => fetchHighHitRate(today),
    enabled: shouldLoadHighHitRate, // Only load when enabled
    staleTime: 30 * 60 * 1000, // 30 minutes - high hit rate only changes once per day
    gcTime: 24 * 60 * 60 * 1000, // Keep in cache for 24 hours (entire day)
    refetchOnMount: false, // Use cache first
    refetchOnWindowFocus: false, // Don't refetch when window gains focus
    refetchOnReconnect: false, // Don't refetch on reconnect
    retry: 1,
  })
  
  // Fetch league-wide stat leaders when "All" is selected
  const { data: leagueStatLeadersData, isLoading: leagueStatLeadersLoading, error: leagueStatLeadersError } = useQuery({
    queryKey: ['stat-leaders', season],
    queryFn: () => fetchStatLeaders(season),
    enabled: !statLeadersFilterToday, // Only fetch when "All" is selected
    staleTime: 300000, // Cache for 5 minutes
    retry: 2,
  })
  
  // Function to refresh all data
  const refreshAll = async () => {
    setIsRefreshing(true)
    showSnackbar('Refreshing data...', 'info', { progress: 0 })
    
    try {
      const tasks = [
        { name: 'Games', fn: () => refetchGames() },
        { name: 'Daily Props', fn: () => refetchDaily() },
        { name: 'High Hit Rate', fn: () => shouldLoadHighHitRate ? refetchHighHitRate() : Promise.resolve() },
      ]

      // Clear local storage cache for today
      clearCache('daily-props-50', today)
      clearCache('high-hit-rate-0.75-6-10', today)
      
      // Invalidate queries first
      queryClient.invalidateQueries({ queryKey: ['games-today', today] })
      queryClient.invalidateQueries({ queryKey: ['daily-50', today] })
      queryClient.invalidateQueries({ queryKey: ['high-hit-rate', today] })

      // Execute tasks with progress tracking
      for (let i = 0; i < tasks.length; i++) {
        const task = tasks[i]
        
        try {
          await task.fn()
          // Update progress after task completes
          updateProgress(((i + 1) / tasks.length) * 100)
        } catch (error) {
          // Error handled - no console logging needed
          // Still update progress even if task fails
          updateProgress(((i + 1) / tasks.length) * 100)
        }
      }

      // Ensure we're at 100%
      updateProgress(100)
      
      // Wait a moment to show 100% progress
      await new Promise(resolve => setTimeout(resolve, 300))
      
      hideSnackbar()
      showSnackbar('Data refreshed successfully!', 'success', { duration: 3000 })
      
    } catch (error) {
      // Error handled - no console logging needed
      hideSnackbar()
      showSnackbar('Failed to refresh data. Please try again.', 'error', { duration: 5000 })
    } finally {
      setIsRefreshing(false)
    }
  }
  
  const games = gamesData?.games ?? []
  
  // Removed debug logging - use browser dev tools if needed

  const bestBets = useMemo(() => {
    // Only show bets if there are games today
    if (games.length === 0) {
      return []
    }
    const items = (dailyData?.items ?? []) as any[]
    // Strict filter: only show props with gameDate matching today
    const todayItems = items.filter((item: any) => {
      const itemDate = item.gameDate || item.game_date
      // Must have a date and it must match today
      return itemDate && (itemDate === today || itemDate.startsWith(today))
    })
    return todayItems.slice(0, 5)
  }, [dailyData, today, games.length])

  const playersToWatch = useMemo(() => {
    // Only show players if there are games today
    if (games.length === 0) {
      return []
    }
    const items = (dailyData?.items ?? []) as any[]
    // Strict filter: only show props with gameDate matching today
    const todayItems = items.filter((item: any) => {
      const itemDate = item.gameDate || item.game_date
      // Must have a date and it must match today
      return itemDate && (itemDate === today || itemDate.startsWith(today))
    })
    const byPlayer = new Map<number, { id: number; name: string; tags: string[]; highlight: any; confidence: number }>()
    for (const s of todayItems) {
      if (!s.playerId) continue
      const entry = byPlayer.get(s.playerId) || { id: s.playerId, name: s.playerName || 'Player', tags: [] as string[], highlight: s, confidence: s.confidence ?? 0 }
      // Update highlight if this prop has higher confidence
      if ((s.confidence ?? 0) > entry.confidence) {
        entry.highlight = s
        entry.confidence = s.confidence ?? 0
      }
      if (s.type === 'PTS' && !entry.tags.includes('🔥 Hot Scoring')) entry.tags.push('🔥 Hot Scoring')
      if ((s.confidence ?? 0) >= 65 && !entry.tags.includes('📈 Trending')) entry.tags.push('📈 Trending')
      byPlayer.set(s.playerId, entry)
    }
    // Sort by confidence (highest first) so top props appear on the left
    return Array.from(byPlayer.values())
      .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
      .slice(0, 6)
  }, [dailyData, today, games.length])

  const statLeaders = useMemo(() => {
    // If "All" is selected, use league-wide stat leaders
    if (!statLeadersFilterToday) {
      if (leagueStatLeadersData?.items) {
        const leaders = leagueStatLeadersData.items
        return {
          PTS: (leaders.PTS || []).map((l: any) => ({
            playerId: l.playerId,
            playerName: l.playerName || 'Unknown',
            fairLine: l.value,
            marketLine: l.value,
          })),
          AST: (leaders.AST || []).map((l: any) => ({
            playerId: l.playerId,
            playerName: l.playerName || 'Unknown',
            fairLine: l.value,
            marketLine: l.value,
          })),
          REB: (leaders.REB || []).map((l: any) => ({
            playerId: l.playerId,
            playerName: l.playerName || 'Unknown',
            fairLine: l.value,
            marketLine: l.value,
          })),
          '3PM': (leaders['3PM'] || []).map((l: any) => ({
            playerId: l.playerId,
            playerName: l.playerName || 'Unknown',
            fairLine: l.value,
            marketLine: l.value,
          })),
        }
      }
      // If still loading or no data, return empty
      return { PTS: [], AST: [], REB: [], '3PM': [] }
    }
    
    // If "Today" is selected, use daily props data
    const items = (dailyData?.items ?? []) as any[]
    if (!items || items.length === 0) {
      return { PTS: [], AST: [], REB: [], '3PM': [] }
    }
    
    // Filter: only include items with gameDate matching today
    const normalizeDate = (dateStr: string | null | undefined): string | null => {
      if (!dateStr) return null
      const match = dateStr.match(/(\d{4}-\d{2}-\d{2})/)
      return match ? match[1] : null
    }
    
    const todayNormalized = normalizeDate(today) || today
    const filteredItems = items.filter((item: any) => {
      const itemDate = item.gameDate || item.game_date
      if (itemDate) {
        const normalizedItemDate = normalizeDate(itemDate)
        if (normalizedItemDate) {
          return normalizedItemDate === todayNormalized
        }
        return itemDate === today || itemDate.startsWith(today)
      }
      return false
    })
    
    const cats = ['PTS','AST','REB','3PM'] as const
    const out: Record<string, any[]> = {}
    cats.forEach(c => {
      const categoryItems = filteredItems
        .filter((it: any) => {
          const itemType = String(it.type || '').toUpperCase()
          return itemType === c
        })
        .filter((it: any) => {
          return it.playerId && it.playerName && (it.fairLine != null || it.marketLine != null)
        })
        .sort((a: any, b: any) => {
          const aValue = a.fairLine ?? a.marketLine ?? 0
          const bValue = b.fairLine ?? b.marketLine ?? 0
          return bValue - aValue
        })
        .slice(0, 3)
      out[c] = categoryItems
    })
    return out
  }, [dailyData, today, statLeadersFilterToday, games.length, leagueStatLeadersData])
  return (
    <div className="container mx-auto px-2 sm:px-4 py-4 sm:py-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4 mb-4">
        <h2 className="text-xl sm:text-2xl font-bold">Dashboard</h2>
        <button
          onClick={() => refreshAll()}
          disabled={isRefreshing || gamesLoading || dailyLoading}
          className="px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors w-full sm:w-auto"
        >
          <svg 
            className={`w-4 h-4 ${isRefreshing || gamesLoading || dailyLoading ? 'animate-spin' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isRefreshing || gamesLoading || dailyLoading ? 'Refreshing...' : 'Refresh Data'}
        </button>
      </div>
      
      {/* Error Messages */}
      {(gamesError || dailyError) && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-800">Error loading data</p>
              <p className="text-xs text-red-600 mt-1">
                {gamesError && 'Failed to load games. '}
                {dailyError && 'Failed to load daily props. '}
                Click "Refresh Data" to try again.
              </p>
            </div>
            <button
              onClick={refreshAll}
              className="px-3 py-1 text-xs font-medium text-red-800 bg-red-100 rounded hover:bg-red-200"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Best Bets Hero */}
      <div className="overflow-hidden rounded-lg bg-white border border-gray-200 shadow-sm mb-4 sm:mb-6">
        <div className="px-3 sm:px-4 py-2 sm:py-3 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-800">Best Bets of the Day</h3>
              <p className="text-xs text-gray-600 mt-0.5">Top props for today's games ({new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone })})</p>
            </div>
            {bestBets.length > 0 && (
              <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-1 rounded-full">
                {bestBets.length} bets
              </span>
            )}
          </div>
        </div>
        <div className="p-3 sm:p-4">
          {dailyLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center gap-2 text-gray-600">
                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Loading best bets…</span>
              </div>
            </div>
          ) : dailyError ? (
            <p className="text-red-600 text-center py-4">Error loading bets. Click "Refresh Data" to retry.</p>
          ) : games.length === 0 ? (
            <p className="text-gray-600 text-center py-4">No games scheduled for today.</p>
          ) : bestBets.length === 0 ? (
            <p className="text-gray-600 text-center py-4">No best bets available for today's games.</p>
          ) : (
            <SuggestionCards suggestions={bestBets} />
          )}
        </div>
      </div>

      {/* High Hit Rate Bets - Lazy Loaded */}
      {shouldLoadHighHitRate && (
        <div className="overflow-hidden rounded-lg bg-white border border-gray-200 shadow-sm mb-4 sm:mb-6">
          <div className="px-3 sm:px-4 py-2 sm:py-3 border-b border-gray-200 bg-gradient-to-r from-green-50 to-emerald-50">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-base sm:text-lg font-semibold text-gray-800">High Hit Rate Bets</h3>
                <p className="text-xs text-gray-600 mt-0.5">Props with 75%+ historical hit rate for today's games ({new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone })})</p>
              </div>
              {highHitRateData?.items && highHitRateData.items.length > 0 && (
                <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded-full">
                  {highHitRateData.items.length} bets
                </span>
              )}
            </div>
          </div>
          <div className="p-3 sm:p-4">
            {highHitRateLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="flex items-center gap-2 text-gray-600">
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Loading high hit rate bets…</span>
                </div>
              </div>
            ) : !highHitRateData?.items || highHitRateData.items.length === 0 || games.length === 0 ? (
              <p className="text-gray-600 text-center py-4">No high hit rate bets available for today's games.</p>
            ) : (
              <SuggestionCards suggestions={highHitRateData.items.filter((item: any) => {
                const itemDate = item.gameDate || item.game_date
                // Strict filter: must have a date and it must match today
                return itemDate && (itemDate === today || itemDate.startsWith(today))
              })} />
            )}
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          {/* Today's Games */}
          <div className="p-3 sm:p-4 border border-gray-200 rounded-lg bg-white shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base sm:text-lg font-semibold text-gray-800">Today's Games</h3>
              {games.length > 0 && (
                <span className="text-xs text-gray-500">{games.length} game{games.length !== 1 ? 's' : ''}</span>
              )}
            </div>
            {gamesLoading ? (
              <div className="flex items-center justify-center py-8">
                <svg className="animate-spin h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="ml-2 text-sm text-gray-600">Loading games…</span>
              </div>
            ) : gamesError ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
                <p className="font-medium">Error loading schedule</p>
                {gamesError instanceof Error && (
                  <p className="text-xs mt-1">{gamesError.message}</p>
                )}
              </div>
            ) : games.length === 0 ? (
              <div className="p-6 text-center bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-gray-600 font-medium">No games scheduled</p>
                <p className="text-xs mt-1 text-gray-500">Date: {today}</p>
              </div>
            ) : (
              <div className="overflow-x-auto -mx-4 px-4 pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100" style={{ scrollbarWidth: 'thin' }}>
                <div className="flex gap-3 min-w-max">
                  {games.map((g: any, idx: number) => {
                    const gameTime = g.gameTimeUTC ? new Date(g.gameTimeUTC).toLocaleTimeString('en-US', { 
                      hour: '2-digit', 
                      minute: '2-digit',
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }) : 'TBD'
                    const statusColor = g.status === 'FINAL' ? 'bg-gray-100 text-gray-700 border-gray-300' :
                                       g.status === 'LIVE' ? 'bg-red-100 text-red-700 border-red-300' :
                                       'bg-blue-100 text-blue-700 border-blue-300'
                    const cardBorder = g.status === 'LIVE' ? 'border-red-300 ring-1 ring-red-200' :
                                      g.status === 'FINAL' ? 'border-gray-300' :
                                      'border-gray-200'
                    
                    return (
                      <div 
                        key={g.gameId || idx} 
                        className={`flex-none w-44 sm:w-52 bg-white border rounded-lg shadow-sm hover:shadow-md transition-all duration-200 p-3 sm:p-4 ${cardBorder} ${g.status === 'LIVE' ? 'animate-pulse' : ''}`}
                      >
                        {/* Status Badge */}
                        <div className="flex items-center justify-between mb-3">
                          <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border ${statusColor}`}>
                            {g.status || 'SCHEDULED'}
                          </span>
                          {g.status === 'LIVE' && (
                            <div className="flex items-center gap-1">
                              <span className="h-2 w-2 bg-red-500 rounded-full animate-pulse"></span>
                              <span className="text-[10px] font-semibold text-red-600">LIVE</span>
                            </div>
                          )}
                        </div>
                        
                        {/* Matchup */}
                        <div className="space-y-2.5 mb-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-bold text-gray-900">{g.away}</span>
                          </div>
                          <div className="flex items-center justify-center py-1">
                            <span className="text-xs font-medium text-gray-400">@</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-bold text-gray-900">{g.home}</span>
                          </div>
                        </div>
                        
                        {/* Time */}
                        <div className="pt-3 border-t border-gray-100">
                          <div className="flex items-center gap-1.5">
                            <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span className="text-xs font-semibold text-gray-700">{gameTime}</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Players to Watch */}
          <div className="p-3 sm:p-4 border border-gray-200 rounded-lg bg-white shadow-sm">
            <h3 className="text-base sm:text-lg font-semibold mb-3 text-gray-800">Players to Watch</h3>
            {dailyLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-sm text-gray-600">Loading players…</p>
                </div>
              </div>
            ) : games.length === 0 ? (
              <p className="text-gray-600">No games scheduled for today.</p>
            ) : playersToWatch.length === 0 ? (
              <p className="text-gray-600">No players to watch for today's games.</p>
            ) : (
              <div className="overflow-x-auto -mx-4 px-4">
                <div className="flex gap-3 min-w-max">
                  {playersToWatch.map((p) => {
                    const topConfidence = Math.round(p.highlight?.confidence ?? 0)
                    const hasTopProp = topConfidence > 0
                    return (
                      <a key={p.id} href={`/player/${p.id}`} className={`flex-shrink-0 w-[160px] sm:w-[200px] rounded-xl border p-2.5 sm:p-3 hover:shadow-sm transition ${hasTopProp ? 'border-blue-300 bg-blue-50/30' : 'border-gray-200 bg-gray-50'}`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-gray-900 truncate">{p.name}</div>
                            {hasTopProp && (
                              <div className="mt-1 flex items-center gap-1.5">
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gradient-to-r from-yellow-400 to-orange-500 text-white text-[10px] font-bold shadow-sm">
                                  ⭐ TOP PROP
                                </span>
                                <span className="text-xs font-semibold text-blue-700">{topConfidence}%</span>
                              </div>
                            )}
                            {hasTopProp && (
                              <div className="mt-1.5 text-xs font-medium text-gray-700">
                                {p.highlight?.type} {p.highlight?.marketLine ?? p.highlight?.fairLine ?? '—'}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {p.tags.map((t, i) => (
                            <span key={i} className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[11px] font-medium">{t}</span>
                          ))}
                        </div>
                        {!hasTopProp && (
                          <div className="mt-2 text-xs text-gray-500">No top prop available</div>
                        )}
                      </a>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Daily Props Panel */}
          <DailyPropsPanel />
        </div>

        {/* Right column */}
        <div className="lg:col-span-1 space-y-4 sm:space-y-6">
          <QuickPropLab />

          {/* Stat Leaders */}
          <div className="p-3 sm:p-4 border border-gray-200 rounded-lg bg-white shadow-sm">
            {/* Header with title and toggle */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base sm:text-lg font-semibold text-gray-800">Stat Leaders</h3>
              {/* Minimal toggle aligned to the right */}
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold transition-colors ${statLeadersFilterToday ? 'text-gray-500' : 'text-black'}`}>
                  All
                </span>
                <button
                  onClick={() => setStatLeadersFilterToday(!statLeadersFilterToday)}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                    statLeadersFilterToday 
                      ? 'bg-blue-800' 
                      : 'bg-gray-500'
                  }`}
                  role="switch"
                  aria-checked={statLeadersFilterToday}
                  aria-label="Filter by today's games"
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
                      statLeadersFilterToday ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
                <span className={`text-xs font-bold transition-colors ${statLeadersFilterToday ? 'text-black' : 'text-gray-500'}`}>
                  Today
                </span>
              </div>
            </div>
            {(dailyLoading || (leagueStatLeadersLoading && !statLeadersFilterToday)) ? (
              <p className="text-gray-600">Loading…</p>
            ) : leagueStatLeadersError && !statLeadersFilterToday ? (
              <p className="text-xs text-red-600">Error loading stat leaders. Please try again.</p>
            ) : (!statLeadersFilterToday || games.length > 0) ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(['PTS','AST','REB','3PM'] as const).map((cat) => {
                  const leaders = statLeaders[cat] ?? []
                  return (
                    <div key={cat} className="rounded-lg bg-gray-50 p-3 ring-1 ring-gray-200">
                      <div className="text-xs font-bold text-gray-700 mb-2">{cat}</div>
                      {leaders.length === 0 ? (
                        <p className="text-xs text-gray-500">No data available</p>
                      ) : (
                        <ol className="space-y-1 text-sm">
                          {leaders.map((s: any, idx: number) => (
                            <li key={`${s.playerId}-${idx}`} className="flex items-center justify-between gap-2">
                              <a 
                                href={`/player/${s.playerId}`} 
                                className="text-gray-900 hover:text-blue-700 font-semibold truncate flex-1 min-w-0"
                                title={s.playerName || 'Player'}
                              >
                                {s.playerName || 'Unknown Player'}
                              </a>
                              <span className="text-gray-700 text-xs font-bold whitespace-nowrap">
                                {(s.fairLine ?? s.marketLine ?? 0).toFixed(1)}
                              </span>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-gray-600">No games scheduled for today.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
