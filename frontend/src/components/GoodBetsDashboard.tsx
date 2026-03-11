import { useMemo, useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { QuickPropLab } from './QuickPropLab'
import { DailyPropsPanel } from './DailyPropsPanel'
import { SuggestionCards } from './SuggestionCards'
import { PlayerAvatar } from './PlayerAvatar'
import { PlayerNewsSection } from './PlayerNewsSection'
import { useSeason } from '../context/SeasonContext'
import { useSnackbar } from '../context/SnackbarContext'
import { getCache, setCache, clearCache, getTodayDate } from '../utils/cache'

import { apiFetch, apiPost } from '../utils/api'
import { getLiveGames } from '../services/overUnderService'

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

async function fetchHotFormProps(date?: string, minConfidence = 70) {
  const params = new URLSearchParams()
  params.append('hot_form_only', 'true')
  params.append('min_confidence', String(minConfidence))
  if (date) params.append('date', date)
  const res = await apiFetch(`api/v1/props/daily?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0, hotFormOnly: true }
  return res.json()
}

async function fetchTopPicks(date?: string) {
  const targetDate = date || getTodayDate()
  const cacheKey = 'top-picks-20'
  
  const cached = getCache(cacheKey, targetDate)
  if (cached) {
    return cached
  }
  
  const params = new URLSearchParams()
  params.append('limit', '20')
  if (date) params.append('date', date)
  const endpoint = `api/v1/props/top-picks?${params.toString()}`
  const res = await apiFetch(endpoint)
  if (!res.ok) throw new Error('Failed to load top picks')
  const data = await res.json()
  
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

async function fetchPickOfTheDay(date?: string) {
  const params = date ? `?date=${encodeURIComponent(date)}` : ''
  const res = await apiFetch(`api/v1/props/pick-of-the-day${params}`)
  if (!res.ok) throw new Error('Failed to load pick of the day')
  return res.json()
}

export function GoodBetsDashboard() {
  const { season } = useSeason()
  const queryClient = useQueryClient()
  const { showSnackbar, updateProgress, hideSnackbar } = useSnackbar()
  const [shouldLoadTopPicks, setShouldLoadTopPicks] = useState(false)
  const [statLeadersFilterToday, setStatLeadersFilterToday] = useState(false) // Toggle for filtering by today - default to "All"
  const [featuredFilter, setFeaturedFilter] = useState<'all' | 'hot'>('all') // Players to Watch: All today's players vs Hot form only
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  // Cooldown for refresh button (20 minutes = 1200000ms, backend allows 3/hour)
  const REFRESH_COOLDOWN_MS = 20 * 60 * 1000 // 20 minutes
  const [lastRefreshTime, setLastRefreshTime] = useState<number | null>(() => {
    // Load from localStorage on mount
    const stored = localStorage.getItem('lastRefreshTime')
    return stored ? parseInt(stored, 10) : null
  })
  
  // Calculate remaining cooldown
  const getRemainingCooldown = (): number => {
    if (!lastRefreshTime) return 0
    const elapsed = Date.now() - lastRefreshTime
    const remaining = REFRESH_COOLDOWN_MS - elapsed
    return Math.max(0, remaining)
  }
  
  const remainingCooldown = getRemainingCooldown()
  const isOnCooldown = remainingCooldown > 0
  
  // Format cooldown time for display
  const formatCooldown = (ms: number): string => {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`
    }
    return `${seconds}s`
  }
  
  // Update cooldown display every second when on cooldown
  const [, forceUpdate] = useState(0)
  useEffect(() => {
    if (!isOnCooldown) return
    
    const interval = setInterval(() => {
      // Recalculate cooldown inline to avoid dependency issues
      if (!lastRefreshTime) {
        clearInterval(interval)
        return
      }
      const elapsed = Date.now() - lastRefreshTime
      const remaining = REFRESH_COOLDOWN_MS - elapsed
      if (remaining <= 0) {
        clearInterval(interval)
        return
      }
      forceUpdate(prev => prev + 1) // Force re-render to update cooldown display
    }, 1000)
    
    return () => clearInterval(interval)
  }, [isOnCooldown, lastRefreshTime, REFRESH_COOLDOWN_MS])
  
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

  const games = gamesData?.games ?? []
  const hasGamesToday = games.length > 0
  const { data: liveGamesData } = useQuery({
    queryKey: ['over-under-live-games', today],
    queryFn: getLiveGames,
    staleTime: 60 * 1000,
    refetchInterval: hasGamesToday ? 60 * 1000 : false,
    enabled: hasGamesToday,
  })
  const liveGamesMap = useMemo(() => {
    const map: Record<string, { home_score: number; away_score: number; quarter: number; time_remaining: string; is_final: boolean }> = {}
    for (const lg of liveGamesData?.games ?? []) {
      map[String(lg.game_id)] = {
        home_score: lg.home_score,
        away_score: lg.away_score,
        quarter: lg.quarter,
        time_remaining: lg.time_remaining,
        is_final: lg.is_final,
      }
    }
    return map
  }, [liveGamesData])
  
  const { data: dailyData, isLoading: dailyLoading, error: dailyError, refetch: refetchDaily } = useQuery({ 
    queryKey: ['daily-50', today], 
    queryFn: () => fetchDaily(50, today),
    staleTime: 30 * 60 * 1000, // 30 minutes - daily props only change once per day
    gcTime: 24 * 60 * 60 * 1000, // Keep in cache for 24 hours (entire day)
    refetchOnMount: false, // Use cache first, don't refetch on mount
    refetchOnWindowFocus: false, // Don't refetch when window gains focus
    refetchOnReconnect: false, // Don't refetch on reconnect
  })
  
  // Lazy load top picks after main dashboard loads
  useEffect(() => {
    if (!dailyLoading && !gamesLoading) {
      const timer = setTimeout(() => {
        setShouldLoadTopPicks(true)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [dailyLoading, gamesLoading])

  const { data: topPicksData, isLoading: topPicksLoading, refetch: refetchTopPicks } = useQuery({
    queryKey: ['top-picks', today],
    queryFn: () => fetchTopPicks(today),
    enabled: shouldLoadTopPicks,
    staleTime: 30 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 1,
  })

  const gamesCount = gamesData?.games?.length ?? 0

  const { data: pickOfTheDayData, isLoading: pickOfTheDayLoading } = useQuery({
    queryKey: ['pick-of-the-day', today],
    queryFn: () => fetchPickOfTheDay(today),
    enabled: gamesCount > 0,
    staleTime: 30 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
  })
  const pickOfTheDay = pickOfTheDayData?.pick ?? null

  // Hot form + high confidence props (players in good form, min 70% confidence)
  const { data: hotFormData, isLoading: hotFormLoading } = useQuery({
    queryKey: ['daily-hot-form', today],
    queryFn: () => fetchHotFormProps(today, 70),
    enabled: gamesCount > 0,
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  })
  const hotFormItems = (hotFormData?.items ?? []) as any[]
  
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
    // Check cooldown
    if (isOnCooldown) {
      showSnackbar(
        `Please wait ${formatCooldown(remainingCooldown)} before refreshing again. This operation makes many API calls.`,
        'warning',
        { duration: 5000 }
      )
      return
    }
    
    setIsRefreshing(true)
    showSnackbar('Refreshing data...', 'info', { progress: 0 })
    
    try {
      // Step 1: Regenerate backend caches (this is the important part)
      updateProgress(10)
      try {
        await apiPost('api/v1/admin/refresh/all')
        updateProgress(30)
        // Update last refresh time on success
        const now = Date.now()
        setLastRefreshTime(now)
        localStorage.setItem('lastRefreshTime', now.toString())
      } catch (error: unknown) {
        // Handle rate limit errors specifically
        const err = error as { message?: string; response?: { status?: number } }
        if (err?.message?.includes('429') || err?.response?.status === 429) {
          hideSnackbar()
          showSnackbar(
            'Rate limit exceeded. Please wait before refreshing again. This operation makes many API calls.',
            'error',
            { duration: 8000 }
          )
          setIsRefreshing(false)
          return
        }
        // If backend refresh fails for other reasons, continue with frontend refresh anyway
        // This allows the button to work even if backend is having issues
        console.warn('Backend cache refresh failed, continuing with frontend refresh', error)
      }

      // Step 2: Clear local storage cache for today
      clearCache('daily-props-50', today)
      clearCache('top-picks-20', today)
      updateProgress(40)

      // Step 3: Invalidate React Query cache
      queryClient.invalidateQueries({ queryKey: ['games-today', today] })
      queryClient.invalidateQueries({ queryKey: ['daily-50', today] })
      queryClient.invalidateQueries({ queryKey: ['top-picks', today] })
      queryClient.invalidateQueries({ queryKey: ['daily-hot-form', today] })
      queryClient.invalidateQueries({ queryKey: ['pick-of-the-day', today] })
      updateProgress(50)

      // Step 4: Refetch all data sources
      const tasks = [
        { name: 'Games', fn: () => refetchGames() },
        { name: 'Daily Props', fn: () => refetchDaily() },
        { name: 'Top Picks', fn: () => shouldLoadTopPicks ? refetchTopPicks() : Promise.resolve() },
      ]

      // Execute tasks with progress tracking
      const taskStartProgress = 50
      const taskProgressRange = 50 // Remaining 50% for tasks
      
      for (let i = 0; i < tasks.length; i++) {
        const task = tasks[i]
        
        try {
          await task.fn()
          // Update progress after task completes
          const taskProgress = taskStartProgress + ((i + 1) / tasks.length) * taskProgressRange
          updateProgress(taskProgress)
        } catch {
          // Error handled - no console logging needed
          // Still update progress even if task fails
          const taskProgress = taskStartProgress + ((i + 1) / tasks.length) * taskProgressRange
          updateProgress(taskProgress)
        }
      }

      // Ensure we're at 100%
      updateProgress(100)
      
      // Wait a moment to show 100% progress
      await new Promise(resolve => setTimeout(resolve, 300))
      
      hideSnackbar()
      showSnackbar('Data refreshed successfully!', 'success', { duration: 3000 })
      
    } catch {
      // Error handled - no console logging needed
      hideSnackbar()
      showSnackbar('Failed to refresh data. Please try again.', 'error', { duration: 5000 })
    } finally {
      setIsRefreshing(false)
    }
  }

  // Removed debug logging - use browser dev tools if needed

  // Unified Top Picks — uses the new /top-picks endpoint
  const topPicks = useMemo(() => {
    if (games.length === 0) return []
    const items = (topPicksData?.items ?? []) as any[]
    return items
      .filter((item) => {
        const d = item.gameDate || item.game_date
        return d && (d === today || d.startsWith(today))
      })
      .slice(0, 12)
  }, [topPicksData, today, games.length])

  // Fallback: if top-picks hasn't loaded yet, use daily data as interim
  const bestBets = useMemo(() => {
    if (topPicks.length > 0) return topPicks
    if (games.length === 0) return []
    const items = (dailyData?.items ?? []) as any[]
    return items
      .filter((item) => {
        const d = item.gameDate || item.game_date
        return d && (d === today || d.startsWith(today))
      })
      .slice(0, 8)
  }, [topPicks, dailyData, today, games.length])

  const playersToWatch = useMemo(() => {
    // Only show players if there are games today
    if (games.length === 0) {
      return []
    }
    const items = (dailyData?.items ?? []) as any[]
    // Strict filter: only show props with gameDate matching today
    const todayItems = items.filter((item) => {
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

  // Hot players: from hot-form-only props (same tag logic as Players to Watch, backend isHot filter)
  const hotPlayers = useMemo(() => {
    const items = (hotFormData?.items ?? []) as any[]
    const todayItems = items.filter((item) => {
      const itemDate = item.gameDate || item.game_date
      return itemDate && (itemDate === today || itemDate.startsWith(today))
    })
    const byPlayer = new Map<number, { id: number; name: string; tags: string[]; highlight: any; confidence: number }>()
    for (const s of todayItems) {
      if (!s.playerId) continue
      const entry = byPlayer.get(s.playerId) || { id: s.playerId, name: s.playerName || 'Player', tags: [] as string[], highlight: s, confidence: s.confidence ?? 0 }
      if ((s.confidence ?? 0) > entry.confidence) {
        entry.highlight = s
        entry.confidence = s.confidence ?? 0
      }
      if (s.type === 'PTS' && !entry.tags.includes('🔥 Hot Scoring')) entry.tags.push('🔥 Hot Scoring')
      if ((s.confidence ?? 0) >= 65 && !entry.tags.includes('📈 Trending')) entry.tags.push('📈 Trending')
      if (s.isHot && !entry.tags.includes('🔥 Hot')) entry.tags.push('🔥 Hot')
      byPlayer.set(s.playerId, entry)
    }
    return Array.from(byPlayer.values())
      .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
      .slice(0, 8)
  }, [hotFormData, today, games.length])

  const featuredPlayers = useMemo(() => {
    const list = featuredFilter === 'hot' ? hotPlayers : playersToWatch
    return list.slice(0, 8)
  }, [featuredFilter, hotPlayers, playersToWatch])

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
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-slate-100 transition-colors duration-200">Dashboard</h2>
        <button
          onClick={() => refreshAll()}
          disabled={isRefreshing || gamesLoading || dailyLoading || isOnCooldown}
          className="px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors w-full sm:w-auto"
          title={isOnCooldown ? `Please wait ${formatCooldown(remainingCooldown)} before refreshing again` : 'Refresh all data (makes many API calls)'}
        >
          <svg 
            className={`w-4 h-4 ${isRefreshing || gamesLoading || dailyLoading ? 'animate-spin' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isRefreshing || gamesLoading || dailyLoading 
            ? 'Refreshing...' 
            : isOnCooldown 
            ? `Wait ${formatCooldown(remainingCooldown)}`
            : 'Refresh Data'}
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

      {/* Top Picks of the Day — unified section */}
      <div className="overflow-hidden rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm mb-3 transition-colors duration-200">
        <div className="px-2.5 sm:px-3 py-1.5 sm:py-2 border-b border-gray-200 dark:border-slate-700 bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20 transition-colors duration-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1.5">
            <div>
              <h3 className="text-sm sm:text-base font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Top Picks of the Day</h3>
              <p className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">
                High-probability props — scored by hit rate, consistency, trend &amp; volume
              </p>
            </div>
            {bestBets.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-bold text-amber-700 bg-amber-100 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 rounded-full">
                  {bestBets.filter((b: any) => b.tier === 'lock').length} LOCKS
                </span>
                <span className="text-[9px] font-bold text-emerald-700 bg-emerald-100 dark:bg-emerald-900/40 dark:text-emerald-300 px-1.5 py-0.5 rounded-full">
                  {bestBets.filter((b: any) => b.tier === 'strong').length} STRONG
                </span>
                <span className="text-[10px] font-medium text-gray-600 bg-gray-100 dark:bg-slate-700 dark:text-gray-300 px-1.5 py-0.5 rounded-full">
                  {bestBets.length} total
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="p-2 sm:p-2.5">
          {(topPicksLoading || (dailyLoading && topPicks.length === 0)) ? (
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Loading top picks…</span>
              </div>
            </div>
          ) : dailyError ? (
            <p className="text-red-600 dark:text-red-400 text-center py-2 text-sm">Error loading picks. Click "Refresh Data" to retry.</p>
          ) : games.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400 text-center py-2 text-sm transition-colors duration-200">No games scheduled for today.</p>
          ) : bestBets.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400 text-center py-2 text-sm transition-colors duration-200">Picks are being generated — check back soon.</p>
          ) : (
            <SuggestionCards suggestions={bestBets} horizontal={true} />
          )}
        </div>
      </div>

      {/* Player News - Horizontal Scrolling */}
      <div className="overflow-hidden rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm mb-3 transition-colors duration-200">
          <div className="px-2 sm:px-2.5 py-1 sm:py-1.5 border-b border-gray-200 dark:border-slate-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 transition-colors duration-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1">
            <div>
              <h3 className="text-xs sm:text-sm font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Player News</h3>
              <p className="text-[9px] sm:text-[10px] text-gray-600 dark:text-gray-400 transition-colors duration-200">Latest NBA news and updates</p>
            </div>
          </div>
        </div>
        <div className="p-1 sm:p-1.5 md:p-2">
          <PlayerNewsSection />
        </div>
      </div>

      {/* Old High Hit Rate section removed — merged into Top Picks above */}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          {/* Today's Games */}
          <div className="p-3 sm:p-4 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 shadow-sm transition-colors duration-200">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Today's Games</h3>
              {games.length > 0 && (
                <span className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">{games.length} game{games.length !== 1 ? 's' : ''}</span>
              )}
            </div>
            {gamesLoading ? (
              <div className="flex items-center justify-center py-8">
                <svg className="animate-spin h-5 w-5 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Loading games…</span>
              </div>
            ) : gamesError ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
                <p className="font-medium">Error loading schedule</p>
                {gamesError instanceof Error && (
                  <p className="text-xs mt-1">{gamesError.message}</p>
                )}
              </div>
            ) : games.length === 0 ? (
              <div className="p-6 text-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 transition-colors duration-200">
                <p className="text-gray-600 dark:text-gray-300 font-medium">No games scheduled</p>
                <p className="text-xs mt-1 text-gray-500 dark:text-gray-400">Date: {today}</p>
              </div>
            ) : (
              <div className="overflow-x-auto -mx-4 px-4 pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100" style={{ scrollbarWidth: 'thin' }}>
                <div className="flex gap-3 min-w-max">
                  {games.map((g: any, idx: number) => {
                    const gameId = g.gameId != null ? String(g.gameId) : ''
                    const live = liveGamesMap[gameId]
                    const gameTime = g.gameTimeUTC ? new Date(g.gameTimeUTC).toLocaleTimeString('en-US', { 
                      hour: '2-digit', 
                      minute: '2-digit',
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }) : 'TBD'
                    const statusColor = g.status === 'FINAL' ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-slate-600' :
                                       g.status === 'LIVE' ? 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700' :
                                       'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700'
                    const cardBorder = g.status === 'LIVE' ? 'border-red-300 dark:border-red-700 ring-1 ring-red-200 dark:ring-red-800/50' :
                                      g.status === 'FINAL' ? 'border-gray-300 dark:border-slate-600' :
                                      'border-gray-200 dark:border-slate-700'
                    const badgeLabel = g.status === 'FINAL'
                      ? 'Final'
                      : g.status === 'LIVE'
                        ? (live && !live.is_final && live.quarter ? `Q${live.quarter} ${(live.time_remaining || '').trim()}`.trim() || 'In progress' : 'In progress')
                        : (gameTime !== 'TBD' ? gameTime : 'Upcoming')
                    
                    return (
                      <div 
                        key={g.gameId || idx} 
                        className={`flex-none w-44 sm:w-52 bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 p-3 sm:p-4 ${cardBorder} ${g.status === 'LIVE' ? 'animate-pulse' : ''}`}
                      >
                        {/* Status Badge */}
                        <div className="flex items-center justify-between mb-3">
                          <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wider border ${statusColor}`}>
                            {badgeLabel}
                          </span>
                          {g.status === 'LIVE' && (
                            <div className="flex items-center gap-1">
                              <span className="h-2 w-2 bg-red-500 rounded-full animate-pulse" aria-hidden />
                              <span className="text-[10px] font-semibold text-red-600 dark:text-red-400">Live</span>
                            </div>
                          )}
                        </div>
                        
                        {/* Matchup */}
                        <div className="space-y-2.5 mb-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-bold text-gray-900 dark:text-slate-100 transition-colors duration-200 truncate">{g.away}</span>
                            {live && <span className="text-sm font-bold text-gray-900 dark:text-slate-100 tabular-nums flex-shrink-0">{live.away_score}</span>}
                          </div>
                          <div className="flex items-center justify-center py-1">
                            <span className="text-xs font-medium text-gray-400 dark:text-gray-500 transition-colors duration-200">@</span>
                          </div>
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-bold text-gray-900 dark:text-slate-100 transition-colors duration-200 truncate">{g.home}</span>
                            {live && <span className="text-sm font-bold text-gray-900 dark:text-slate-100 tabular-nums flex-shrink-0">{live.home_score}</span>}
                          </div>
                        </div>
                        
                        {/* Live quarter/time or game time */}
                        <div className="pt-3 border-t border-gray-100 dark:border-slate-700 transition-colors duration-200">
                          <div className="flex items-center gap-1.5">
                            <svg className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 transition-colors duration-200 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 transition-colors duration-200">
                              {live && (live.is_final ? 'Final' : (live.quarter ? `Q${live.quarter} ${live.time_remaining || ''}`.trim() : gameTime))}
                              {!live && gameTime}
                            </span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* AI Pick of the Day — single best bet from today's props */}
          <div className="p-3 sm:p-4 border-2 border-violet-200 dark:border-violet-800/50 rounded-xl bg-gradient-to-br from-violet-50 to-indigo-50 dark:from-violet-950/30 dark:to-indigo-950/20 shadow-md transition-colors duration-200">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xl" aria-hidden>⭐</span>
              <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-slate-100 transition-colors duration-200">AI Pick of the Day</h3>
              {(pickOfTheDay?.confidenceSource === 'ml_blended' || pickOfTheDay?.rationaleSource === 'llm' || pickOfTheDay?.mlAvailable) && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-200 dark:bg-violet-800/50 text-violet-800 dark:text-violet-200 font-medium">AI</span>
              )}
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-3 transition-colors duration-200">
              Best prop for today based on confidence — same pipeline as daily props (ML/LLM when AI is on).
            </p>
            {pickOfTheDayLoading ? (
              <div className="flex items-center justify-center py-8">
                <svg className="animate-spin h-6 w-6 text-violet-600" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Loading pick…</span>
              </div>
            ) : games.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-2 text-center transition-colors duration-200">No games today.</p>
            ) : !pickOfTheDay ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-2 text-center transition-colors duration-200">No pick available for today. Try refreshing daily props in Admin.</p>
            ) : (() => {
              const firstTopPick = bestBets.length > 0 ? bestBets[0] : null
              const isSameAsFirstTopPick = firstTopPick && firstTopPick.playerId === pickOfTheDay.playerId && String(firstTopPick.type || '').toUpperCase() === String(pickOfTheDay.type || '').toUpperCase()
              if (isSameAsFirstTopPick) {
                return (
                  <a href={`/player/${pickOfTheDay.playerId}`} className="block py-2 px-3 rounded-lg bg-white dark:bg-slate-800/80 border border-violet-200 dark:border-violet-800/50 hover:border-violet-400 dark:hover:border-violet-600 transition-colors duration-200 text-sm">
                    <span className="font-semibold text-violet-700 dark:text-violet-300">Today&apos;s spotlight:</span>{' '}
                    <span className="font-bold text-gray-900 dark:text-slate-100">{pickOfTheDay.playerName}</span>{' '}
                    {pickOfTheDay.type} {pickOfTheDay.marketLine != null ? Number(pickOfTheDay.marketLine) : '—'}{' '}
                    <span className={pickOfTheDay.suggestion === 'over' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>{String(pickOfTheDay.suggestion).toUpperCase()}</span>
                    {pickOfTheDay.confidence != null && <span className="ml-1.5 font-bold text-violet-700 dark:text-violet-300">— {Math.round(Number(pickOfTheDay.confidence))}% confidence</span>}
                  </a>
                )
              }
              return (
              <a
                href={`/player/${pickOfTheDay.playerId}`}
                className="block p-4 rounded-xl bg-white dark:bg-slate-800/80 border border-violet-200 dark:border-violet-800/50 hover:border-violet-400 dark:hover:border-violet-600 hover:shadow-lg transition-all duration-200"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-lg font-bold text-gray-900 dark:text-slate-100 truncate transition-colors duration-200">{pickOfTheDay.playerName}</div>
                    <div className="mt-1 text-sm font-semibold text-violet-700 dark:text-violet-300 transition-colors duration-200">
                      {pickOfTheDay.type} {pickOfTheDay.marketLine != null ? Number(pickOfTheDay.marketLine) : '—'}{' '}
                      <span className={pickOfTheDay.suggestion === 'over' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                        {String(pickOfTheDay.suggestion).toUpperCase()}
                      </span>
                    </div>
                    {pickOfTheDay.confidence != null && (
                      <div className="mt-1.5 inline-flex items-center px-2.5 py-1 rounded-lg bg-violet-100 dark:bg-violet-900/40 text-violet-800 dark:text-violet-200 text-sm font-bold">
                        {Math.round(Number(pickOfTheDay.confidence))}% confidence
                      </div>
                    )}
                  </div>
                  {pickOfTheDay.rationale && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 sm:max-w-[50%] sm:text-right transition-colors duration-200 line-clamp-3">
                      {typeof pickOfTheDay.rationale === 'string' ? pickOfTheDay.rationale : (Array.isArray(pickOfTheDay.rationale) ? pickOfTheDay.rationale[0] : '')}
                    </p>
                  )}
                </div>
                <div className="mt-2 pt-2 border-t border-violet-100 dark:border-violet-800/30 text-[11px] text-gray-500 dark:text-gray-400 transition-colors duration-200">
                  View full analysis →
                </div>
              </a>
              )
            })()}
          </div>

          {/* Players to Watch — All today's players or Hot form only; hide when no games */}
          {games.length > 0 && (
          <div className={`p-3 sm:p-4 border rounded-lg shadow-sm transition-colors duration-200 ${featuredFilter === 'hot' ? 'border-amber-200 dark:border-amber-800/50 bg-amber-50/30 dark:bg-amber-900/10' : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800'}`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Players to Watch</h3>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold transition-colors ${featuredFilter === 'all' ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>All</span>
                <button
                  type="button"
                  onClick={() => setFeaturedFilter(featuredFilter === 'all' ? 'hot' : 'all')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-800 shadow-inner ${
                    featuredFilter === 'hot'
                      ? 'bg-amber-500 dark:bg-amber-500 ring-2 ring-amber-400/60 dark:ring-amber-400/40'
                      : 'bg-slate-400 dark:bg-slate-600 ring-2 ring-slate-300/80 dark:ring-slate-500/60'
                  }`}
                  role="switch"
                  aria-checked={featuredFilter === 'hot'}
                  aria-label="Filter by hot form"
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md ring-2 ring-slate-200/80 dark:ring-slate-400/80 transition-transform duration-200 ${featuredFilter === 'hot' ? 'translate-x-6' : 'translate-x-0.5'}`} />
                </button>
                <span className={`text-xs font-bold transition-colors ${featuredFilter === 'hot' ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>Hot form</span>
              </div>
            </div>
            {(featuredFilter === 'hot' ? hotFormLoading : dailyLoading) ? (
              <div className="flex items-center justify-center py-6">
                <svg className="animate-spin h-5 w-5 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Loading…</span>
              </div>
            ) : games.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-2">No games today.</p>
            ) : featuredPlayers.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-2">{featuredFilter === 'hot' ? 'No hot-form players for today.' : 'No players to watch for today\'s games.'}</p>
            ) : (
              <>
                <div className="overflow-x-auto -mx-4 px-4">
                  <div className="flex gap-3 min-w-max">
                    {featuredPlayers.map((p) => {
                      const topConfidence = Math.round(p.highlight?.confidence ?? 0)
                      const hasTopProp = topConfidence > 0
                      const isHot = featuredFilter === 'hot'
                      return (
                        <a
                          key={p.id}
                          href={`/player/${p.id}`}
                          className={`flex-shrink-0 w-[160px] sm:w-[200px] rounded-xl border p-2.5 sm:p-3 hover:shadow-md transition-colors duration-200 flex flex-col ${
                            isHot
                              ? hasTopProp ? 'border-amber-300 dark:border-amber-700/50 bg-amber-50/50 dark:bg-amber-900/20' : 'border-amber-200 dark:border-amber-800/30 bg-white dark:bg-slate-800/80'
                              : hasTopProp ? 'border-blue-300 dark:border-blue-700/50 bg-blue-50/30 dark:bg-blue-900/20' : 'border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-800/80'
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <PlayerAvatar playerId={p.id} playerName={p.name} size="medium" className="flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 truncate">{p.name}</div>
                              {hasTopProp && (
                                <div className="mt-1 flex items-center gap-1.5">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-white text-[10px] font-bold shadow-sm ${isHot ? 'bg-gradient-to-r from-amber-400 to-orange-500' : 'bg-gradient-to-r from-yellow-400 to-orange-500'}`}>
                                    {isHot ? 'HOT' : '⭐ TOP PROP'}
                                  </span>
                                  <span className={`text-xs font-semibold ${isHot ? 'text-amber-700 dark:text-amber-400' : 'text-blue-700 dark:text-blue-400'}`}>{topConfidence}%</span>
                                </div>
                              )}
                              {hasTopProp && (
                                <div className="mt-1.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                                  {p.highlight?.type} {p.highlight?.marketLine ?? p.highlight?.fairLine ?? '—'}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {p.tags.map((t, i) => (
                              <span key={i} className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${isHot ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200' : 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-200'}`}>{t}</span>
                            ))}
                          </div>
                          {!hasTopProp && <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">{isHot ? 'Hot form' : 'No top prop'}</div>}
                        </a>
                      )
                    })}
                  </div>
                </div>
                {featuredFilter === 'hot' && hotFormItems.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-amber-200/50 dark:border-amber-800/30">
                    <p className="text-[10px] sm:text-xs font-semibold text-amber-800 dark:text-amber-200 mb-2">Today&apos;s hot-form props</p>
                    <ul className="space-y-1.5">
                      {hotFormItems.slice(0, 5).map((item: any, idx: number) => (
                        <li key={`${item.playerId}-${item.type}-${idx}`}>
                          <a href={`/player/${item.playerId}`} className="flex items-center justify-between gap-2 py-1.5 px-2 rounded-lg bg-white/80 dark:bg-slate-800/80 border border-amber-100 dark:border-amber-800/30 hover:border-amber-300 dark:hover:border-amber-600/50 transition-colors text-sm">
                            <span className="font-medium text-gray-900 dark:text-slate-100 truncate">{item.playerName}</span>
                            <span className="text-xs text-gray-600 dark:text-gray-400 shrink-0">{item.type} {item.marketLine ?? item.fairLine ?? '—'} {item.suggestion === 'over' ? 'O' : 'U'}</span>
                            <span className="text-xs font-bold text-amber-700 dark:text-amber-400 shrink-0">{Math.round(item.confidence ?? 0)}%</span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
          )}

          {/* Daily Props Panel */}
          <DailyPropsPanel />
        </div>

        {/* Right column */}
        <div className="lg:col-span-1 space-y-4 sm:space-y-6">
          <QuickPropLab />

          {/* Stat Leaders */}
          <div className="p-3 sm:p-4 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 shadow-sm transition-colors duration-200">
            {/* Header with title and toggle */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-slate-100 transition-colors duration-200">Stat Leaders</h3>
              {/* Minimal toggle aligned to the right */}
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold transition-colors ${statLeadersFilterToday ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                  All
                </span>
                <button
                  onClick={() => setStatLeadersFilterToday(!statLeadersFilterToday)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-800 shadow-inner ${
                    statLeadersFilterToday
                      ? 'bg-blue-600 dark:bg-blue-500 ring-2 ring-blue-400/60 dark:ring-blue-400/40'
                      : 'bg-slate-400 dark:bg-slate-600 ring-2 ring-slate-300/80 dark:ring-slate-500/60'
                  }`}
                  role="switch"
                  aria-checked={statLeadersFilterToday}
                  aria-label="Filter by today's games"
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md ring-2 ring-slate-200/80 dark:ring-slate-400/80 transition-transform duration-200 ${
                      statLeadersFilterToday ? 'translate-x-6' : 'translate-x-0.5'
                    }`}
                  />
                </button>
                <span className={`text-xs font-bold transition-colors ${statLeadersFilterToday ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`}>
                  Today
                </span>
              </div>
            </div>
            {(dailyLoading || (leagueStatLeadersLoading && !statLeadersFilterToday)) ? (
              <p className="text-gray-600 dark:text-gray-400">Loading…</p>
            ) : leagueStatLeadersError && !statLeadersFilterToday ? (
              <p className="text-xs text-red-600 dark:text-red-400">Error loading stat leaders. Please try again.</p>
            ) : (statLeadersFilterToday && !gamesLoading && games.length === 0) ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-2">No games today.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(['PTS','AST','REB','3PM'] as const).map((cat) => {
                  const leaders = statLeaders[cat] ?? []
                  return (
                    <div key={cat} className="rounded-lg bg-gray-50 dark:bg-slate-700/50 p-3 ring-1 ring-gray-200 dark:ring-slate-600">
                      <div className="text-xs font-bold text-gray-700 dark:text-slate-200 mb-2">{cat}</div>
                      {leaders.length === 0 ? (
                        <p className="text-xs text-gray-500 dark:text-gray-400">No data available</p>
                      ) : (
                        <ol className="space-y-1 text-sm">
                          {leaders.map((s: any, idx: number) => (
                            <li key={`${s.playerId}-${idx}`} className="flex items-center justify-between gap-2">
                              <a 
                                href={`/player/${s.playerId}`} 
                                className="flex items-center gap-2 text-gray-900 dark:text-slate-100 hover:text-blue-700 dark:hover:text-blue-400 font-semibold truncate flex-1 min-w-0"
                                title={s.playerName || 'Player'}
                              >
                                <PlayerAvatar playerId={s.playerId} playerName={s.playerName} size="small" />
                                <span className="truncate">{s.playerName || 'Unknown Player'}</span>
                              </a>
                              <span className="text-gray-700 dark:text-slate-200 text-xs font-bold whitespace-nowrap">
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
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
