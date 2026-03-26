import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { QuickPropLab } from './QuickPropLab'
import { PlayerAvatar } from './PlayerAvatar'
import { PlayerNewsSection } from './PlayerNewsSection'
import { useSeason } from '../context/SeasonContext'
import { useSnackbar } from '../context/SnackbarContext'
import { getCache, setCache, clearCache, getTodayDate } from '../utils/cache'

import { apiFetch, apiPost } from '../utils/api'
import { getLiveGames } from '../services/overUnderService'
import { useAddPropToTracker, type AddPropPayload } from '../hooks/useAddPropToTracker'
import type { SuggestionItem } from './SuggestionCards'

/** ESPN team logo (500px). Use uppercase abbreviation. */
function teamLogoUrl(abbr: string): string {
  const a = (abbr || '').trim().toUpperCase()
  return a ? `https://a.espncdn.com/i/teamlogos/nba/500/${a}.png` : ''
}

async function fetchPredictions(date?: string) {
  const params = new URLSearchParams()
  if (date) params.append('date', date)
  const endpoint = `api/v1/games/predictions${params.toString() ? '?' + params.toString() : ''}`
  const res = await apiFetch(endpoint)
  if (!res.ok) throw new Error('Failed to load predictions')
  return res.json()
}

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
  const cacheKey = 'top-picks'
  
  const cached = getCache(cacheKey, targetDate)
  if (cached) {
    return cached
  }
  
  const params = new URLSearchParams()
  params.append('limit', '12')
  params.append('min_confidence', '62')
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

async function fetchBestMatchOfTheDay(date?: string) {
  const params = date ? `?date=${encodeURIComponent(date)}` : ''
  const res = await apiFetch(`api/v1/games/best-match-of-the-day${params}`)
  if (!res.ok) throw new Error('Failed to load best match of the day')
  return res.json()
}

export function GoodBetsDashboard() {
  const navigate = useNavigate()
  const { season } = useSeason()
  const queryClient = useQueryClient()
  const { showSnackbar, updateProgress, hideSnackbar } = useSnackbar()
  const [shouldLoadTopPicks, setShouldLoadTopPicks] = useState(false)
  const [statLeadersFilterToday, setStatLeadersFilterToday] = useState(false) // Toggle for filtering by today - default to "All"
  const [featuredFilter, setFeaturedFilter] = useState<'all' | 'hot'>('hot') // Players to Watch: default Hot form; All = today's players from daily props
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
  const { liveGamesMap, liveGamesByMatchup } = useMemo(() => {
    const map: Record<string, { home_score: number; away_score: number; quarter: number; time_remaining: string; is_final: boolean }> = {}
    const byMatchup: Record<string, { home_score: number; away_score: number; quarter: number; time_remaining: string; is_final: boolean }> = {}
    for (const lg of liveGamesData?.games ?? []) {
      const entry = {
        home_score: lg.home_score,
        away_score: lg.away_score,
        quarter: lg.quarter,
        time_remaining: lg.time_remaining,
        is_final: lg.is_final,
      }
      map[String(lg.game_id)] = entry
      const key = `${String(lg.away_team || '').toUpperCase()}_${String(lg.home_team || '').toUpperCase()}`
      if (key !== '_') byMatchup[key] = entry
    }
    return { liveGamesMap: map, liveGamesByMatchup: byMatchup }
  }, [liveGamesData])
  
  const { data: dailyData, isLoading: dailyLoading, refetch: refetchDaily } = useQuery({ 
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

  const { data: bestMatchData } = useQuery({
    queryKey: ['best-match-of-the-day', today],
    queryFn: () => fetchBestMatchOfTheDay(today),
    enabled: gamesCount > 0,
    staleTime: 30 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
  })
  const bestMatchOfTheDay = bestMatchData?.match ?? null

  const { data: predictionsData } = useQuery({
    queryKey: ['games-predictions', today],
    queryFn: () => fetchPredictions(today),
    enabled: games.length > 0,
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  })
  const predictions = (predictionsData?.predictions ?? []) as Array<{
    gameId: string
    home: string
    away: string
    home_full_name?: string
    away_full_name?: string
    predicted_winner: string
    predicted_winner_name?: string
    win_probability_home: number
    win_probability_away: number
    key_advantage_summary?: string
    outlook_summary?: string
  }>

  // Hot form + high confidence props (players in good form, min 70% confidence)
  const { data: hotFormData, isLoading: hotFormLoading } = useQuery({
    queryKey: ['daily-hot-form', today],
    queryFn: () => fetchHotFormProps(today, 70),
    enabled: gamesCount > 0,
    staleTime: 15 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  })
  // Fetch league-wide stat leaders so "All" toggle has data; fetch on load so both All and Today show data
  const { data: leagueStatLeadersData, isLoading: leagueStatLeadersLoading } = useQuery({
    queryKey: ['stat-leaders', season],
    queryFn: () => fetchStatLeaders(season),
    enabled: true,
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
      clearCache('top-picks', today)
      updateProgress(40)

      // Step 3: Invalidate React Query cache
      queryClient.invalidateQueries({ queryKey: ['games-today', today] })
      queryClient.invalidateQueries({ queryKey: ['daily-50', today] })
      queryClient.invalidateQueries({ queryKey: ['top-picks', today] })
      queryClient.invalidateQueries({ queryKey: ['daily-hot-form', today] })
      queryClient.invalidateQueries({ queryKey: ['pick-of-the-day', today] })
      queryClient.invalidateQueries({ queryKey: ['best-match-of-the-day', today] })
      updateProgress(50)

      // Step 4: Refetch all data sources
      const tasks = [
        { name: 'Games', fn: () => refetchGames() },
        { name: 'Data', fn: () => refetchDaily() },
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
    const items = (topPicksData?.items ?? []) as SuggestionItem[]
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
    const items = (dailyData?.items ?? []) as SuggestionItem[]
    return items
      .filter((item) => {
        const d = item.gameDate || item.game_date
        return d && (d === today || d.startsWith(today))
      })
      .slice(0, 8)
  }, [topPicks, dailyData, today, games.length])

  const playersToWatch = useMemo(() => {
    if (games.length === 0) return []
    const items = (dailyData?.items ?? []) as SuggestionItem[]
    if (!items.length) return []
    const normalizeDate = (d: string | null | undefined) => (!d ? null : d.match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? d)
    const todayNorm = normalizeDate(today) || today
    // Prefer items with gameDate matching today; if none match, use all items when we have games today (API may omit date)
    let todayItems = items.filter((item) => {
      const itemDate = item.gameDate || item.game_date
      if (!itemDate) return false
      const norm = normalizeDate(itemDate)
      return norm === todayNorm || itemDate === today || String(itemDate).startsWith(today)
    })
    if (todayItems.length === 0 && items.length > 0) todayItems = items
    const byPlayer = new Map<number, { id: number; name: string; tags: string[]; highlight: SuggestionItem; confidence: number }>()
    for (const s of todayItems) {
      if (!s.playerId) continue
      const entry = byPlayer.get(s.playerId) || { id: s.playerId, name: s.playerName || 'Player', tags: [] as string[], highlight: s, confidence: s.confidence ?? 0 }
      if ((s.confidence ?? 0) > entry.confidence) {
        entry.highlight = s
        entry.confidence = s.confidence ?? 0
      }
      if (s.type === 'PTS' && !entry.tags.includes('🔥 Hot Scoring')) entry.tags.push('🔥 Hot Scoring')
      if ((s.confidence ?? 0) >= 65 && !entry.tags.includes('📈 Trending')) entry.tags.push('📈 Trending')
      byPlayer.set(s.playerId, entry)
    }
    return Array.from(byPlayer.values())
      .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
      .slice(0, 8)
  }, [dailyData, today, games.length])

  // Hot players: from hot-form-only props (same tag logic as Players to Watch, backend isHot filter)
  const hotPlayers = useMemo(() => {
    const items = (hotFormData?.items ?? []) as SuggestionItem[]
    const todayItems = items.filter((item) => {
      const itemDate = item.gameDate || item.game_date
      return itemDate && (itemDate === today || itemDate.startsWith(today))
    })
    const byPlayer = new Map<number, { id: number; name: string; tags: string[]; highlight: SuggestionItem; confidence: number }>()
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

  // Add prop to bet tracker from dashboard suggestions
  const { addToTracker, isAdding: isAddingToTracker } = useAddPropToTracker()
  const buildTrackerPayload = (s: SuggestionItem): AddPropPayload | null => {
    const playerId = s.playerId ?? s.player_id
    const playerName = s.playerName ?? s.player_name
    if (playerId == null || !playerName || !s.type) return null
    const line = s.marketLine ?? s.fairLine
    if (line == null) return null
    const dir = s.suggestion || s.chosenDirection || ((s.fairLine != null && s.marketLine != null && s.fairLine >= s.marketLine) ? 'over' : 'under')
    const gameDate = s.gameDate ?? s.game_date ?? today
    return {
      player_id: Number(playerId),
      player_name: String(playerName),
      prop_type: String(s.type),
      line_value: Number(line),
      direction: String(dir),
      game_date: gameDate,
      system_confidence: s.confidence ?? null,
      system_fair_line: s.fairLine ?? null,
      system_suggestion: (s.suggestion as string) ?? null,
    }
  }
  const handleAddToTracker = (s: SuggestionItem) => {
    const payload = buildTrackerPayload(s)
    if (payload) addToTracker(payload)
  }

  const statLeaders = useMemo(() => {
    const empty = { PTS: [] as any[], AST: [] as any[], REB: [] as any[], '3PM': [] as any[] }
    // "All" = league-wide stat leaders (cached from admin refresh)
    if (!statLeadersFilterToday) {
      const raw = leagueStatLeadersData?.items
      if (!raw || typeof raw !== 'object') return empty
      return {
        PTS: (raw.PTS || []).map((l: any) => ({
          playerId: l.playerId,
          playerName: l.playerName || 'Unknown',
          fairLine: l.value,
          marketLine: l.value,
        })),
        AST: (raw.AST || []).map((l: any) => ({
          playerId: l.playerId,
          playerName: l.playerName || 'Unknown',
          fairLine: l.value,
          marketLine: l.value,
        })),
        REB: (raw.REB || []).map((l: any) => ({
          playerId: l.playerId,
          playerName: l.playerName || 'Unknown',
          fairLine: l.value,
          marketLine: l.value,
        })),
        '3PM': (raw['3PM'] || []).map((l: any) => ({
          playerId: l.playerId,
          playerName: l.playerName || 'Unknown',
          fairLine: l.value,
          marketLine: l.value,
        })),
      }
    }
    // "Today" = top props per category from today's daily props
    const items = (dailyData?.items ?? []) as SuggestionItem[]
    if (!items.length) return empty
    const normalizeDate = (dateStr: string | null | undefined): string | null => {
      if (!dateStr) return null
      const m = String(dateStr).match(/(\d{4}-\d{2}-\d{2})/)
      return m ? m[1] : null
    }
    const todayNorm = normalizeDate(today) || today
    const filteredItems = items.filter((item: any) => {
      const itemDate = item.gameDate || item.game_date
      if (!itemDate) return false
      const norm = normalizeDate(itemDate)
      return norm === todayNorm || itemDate === today || String(itemDate).startsWith(today)
    })
    const useItems = filteredItems.length > 0 ? filteredItems : items
    const cats = ['PTS', 'AST', 'REB', '3PM'] as const
    const out: Record<string, any[]> = {}
    cats.forEach((c) => {
      const list = useItems
        .filter((it: any) => String(it.type || '').toUpperCase() === c)
        .filter((it: any) => it.playerId && it.playerName && (it.fairLine != null || it.marketLine != null))
        .sort((a: any, b: any) => (b.fairLine ?? b.marketLine ?? 0) - (a.fairLine ?? a.marketLine ?? 0))
        .slice(0, 3)
      out[c] = list
    })
    return out
  }, [dailyData, today, statLeadersFilterToday, games.length, leagueStatLeadersData])
  // ── Kinetic tier helpers ──
  const tierColor = (tier?: string) => {
    if (tier === 'lock')   return 'bg-betting-green text-black'
    if (tier === 'strong') return 'bg-primary-container text-black'
    return 'bg-outline-variant text-on-surface'
  }
  const tierLabel = (tier?: string) => {
    if (tier === 'lock')   return 'LOCK'
    if (tier === 'strong') return 'STRONG'
    return 'LEAN'
  }
  const confBarColor = (confidence?: number) => {
    if ((confidence ?? 0) >= 75) return 'bg-betting-green'
    if ((confidence ?? 0) >= 65) return 'bg-primary-container'
    return 'bg-outline'
  }

  const dateLabel = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <div className="bg-background min-h-screen">

      {/* ── News Ticker ── */}
      <div className="bg-surface-container-low border-b border-outline-variant/20 py-2.5 overflow-hidden whitespace-nowrap">
        <div className="inline-flex gap-16 animate-marquee items-center">
          {bestBets.slice(0, 4).map((b, i) => (
            <span key={i} className="text-[10px] font-black text-primary-container uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse" />
              {b.playerName}: {b.type} {b.suggestion === 'over' ? 'OVER' : 'UNDER'} {b.marketLine ?? b.fairLine} · {b.confidence}% CONF
            </span>
          ))}
          <span className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest">NBA STAT SPOT · AI-POWERED PERFORMANCE LEDGER</span>
        </div>
      </div>

      {/* ── Today's Games ── */}
      <section className="px-6 pt-6 pb-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-4xl font-black uppercase italic tracking-tighter text-on-surface">Tonight's Slate</h1>
            <p className="text-on-surface-variant font-medium text-sm mt-0.5">
              {games.length > 0 ? `${games.length} Games · ${dateLabel}` : dateLabel}
            </p>
          </div>
          <div className="flex gap-2 items-center">
            {games.length > 0 && (
              <span className="bg-secondary-container text-on-secondary-container px-3 py-1 rounded text-[10px] font-bold uppercase tracking-wider">Live Updates</span>
            )}
            <button
              onClick={refreshAll}
              disabled={isRefreshing || isOnCooldown}
              title={isOnCooldown ? `Wait ${formatCooldown(remainingCooldown)}` : 'Refresh data'}
              className="p-2 bg-surface-container rounded hover:bg-surface-container-high transition-colors disabled:opacity-40"
            >
              <span className={`material-symbols-outlined text-[20px] text-on-surface-variant ${isRefreshing ? 'animate-spin' : ''}`}>refresh</span>
            </button>
          </div>
        </div>

        {/* Game Cards */}
        {gamesLoading ? (
          <div className="flex gap-4 overflow-x-auto pb-2 no-scrollbar">
            {[1,2,3].map(i => (
              <div key={i} className="min-w-[280px] bg-surface-container h-28 rounded animate-pulse" />
            ))}
          </div>
        ) : gamesError ? (
          <div className="bg-error-container text-on-error-container px-4 py-3 rounded text-xs font-bold flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">error</span>
            Failed to load games. <button onClick={refreshAll} className="underline">Retry</button>
          </div>
        ) : games.length === 0 ? (
          <div className="bg-surface-container px-6 py-8 rounded text-center">
            <span className="material-symbols-outlined text-4xl text-on-surface/30 block mb-2">sports_basketball</span>
            <p className="text-on-surface-variant text-sm font-bold uppercase tracking-widest">No games scheduled today</p>
          </div>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2 no-scrollbar">
            {games.map((g: any, idx: number) => {
              const gameId = g.gameId != null ? String(g.gameId) : ''
              let live = liveGamesMap[gameId]
              if (!live) {
                const mk = `${String(g.away || '').toUpperCase()}_${String(g.home || '').toUpperCase()}`
                live = liveGamesByMatchup[mk]
              }
              const gameTime = g.gameTimeUTC
                ? new Date(g.gameTimeUTC).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                : 'TBD'
              const isLive = g.status === 'LIVE' || (live && !live.is_final && live.quarter > 0)
              const isFinal = g.status === 'FINAL' || live?.is_final
              const pred = predictions.find(p => String(p.gameId) === gameId)
              const winPct = pred ? (pred.predicted_winner === pred.home ? pred.win_probability_home : pred.win_probability_away) : null

              return (
                <button
                  key={g.gameId || idx}
                  onClick={() => pred && navigate(`/game/${pred.gameId}`)}
                  className={`min-w-[280px] flex-shrink-0 bg-surface-container p-4 rounded border-l-2 text-left transition-all hover:bg-surface-container-high ${
                    isLive ? 'border-betting-green ring-1 ring-betting-green/20' :
                    isFinal ? 'border-surface-container-highest opacity-70' :
                    pred ? 'border-primary' : 'border-outline-variant/30'
                  }`}
                >
                  <div className="flex justify-between items-start mb-4">
                    {isLive ? (
                      <span className="text-betting-green text-[10px] font-black uppercase tracking-widest flex items-center gap-1">
                        <span className="w-1 h-1 rounded-full bg-betting-green animate-pulse" /> LIVE {live?.quarter ? `Q${live.quarter}` : ''}
                      </span>
                    ) : isFinal ? (
                      <span className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest">FINAL</span>
                    ) : (
                      <span className="text-[10px] font-black text-on-surface-variant uppercase tracking-widest">{gameTime}</span>
                    )}
                    {pred && winPct != null && (
                      <div className={`text-[10px] font-black px-2 py-0.5 rounded flex items-center gap-1 ${
                        Number(winPct) >= 60 ? 'bg-betting-green/10 text-betting-green' :
                        Number(winPct) >= 50 ? 'bg-primary/10 text-primary' :
                        'bg-error/10 text-error'
                      }`}>
                        {pred.predicted_winner} {Math.round(Number(winPct))}%
                      </div>
                    )}
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <img src={teamLogoUrl(g.away)} alt={g.away} className="w-5 h-5 grayscale opacity-60" onError={e => (e.target as HTMLImageElement).style.display = 'none'} />
                        <span className="text-xs font-black uppercase tracking-widest">{g.away}</span>
                      </div>
                      {live && <span className={`text-xs font-black ${isLive ? 'text-betting-green' : 'text-on-surface'}`}>{live.away_score}</span>}
                    </div>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <img src={teamLogoUrl(g.home)} alt={g.home} className="w-5 h-5 grayscale opacity-60" onError={e => (e.target as HTMLImageElement).style.display = 'none'} />
                        <span className="text-xs font-black uppercase tracking-widest">{g.home}</span>
                      </div>
                      {live && <span className="text-xs font-black text-on-surface">{live.home_score}</span>}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </section>

      {/* ── Main Grid ── */}
      <div className="px-6 grid grid-cols-1 xl:grid-cols-12 gap-6 pb-8">

        {/* ── Hero: AI Pick of the Day ── */}
        <section className="xl:col-span-12">
          {pickOfTheDayLoading ? (
            <div className="bg-surface-container rounded min-h-[380px] animate-pulse" />
          ) : pickOfTheDay ? (
            <div className="relative overflow-hidden bg-surface-container rounded min-h-[380px] flex flex-col md:flex-row group border border-outline-variant/20">
              <div className="absolute inset-0 bg-gradient-to-r from-background via-background/70 to-transparent z-10" />
              <div className="absolute right-0 top-0 h-full w-full md:w-2/3 bg-surface-container-low flex items-center justify-center overflow-hidden">
                <PlayerAvatar
                  playerId={pickOfTheDay.playerId}
                  playerName={pickOfTheDay.playerName}
                  size="large"
                  className="w-full h-full object-cover object-center opacity-60 group-hover:scale-105 transition-transform duration-1000 grayscale brightness-75"
                />
              </div>
              <div className="relative z-20 p-8 flex flex-col justify-end h-full w-full md:w-3/5 min-h-[380px]">
                <div className="flex items-center gap-2 mb-4">
                  <span className="bg-primary-container text-on-primary text-[10px] font-black px-3 py-1 rounded uppercase tracking-[0.2em] flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px]">psychology</span> AI MASTER PICK
                  </span>
                  <span className="bg-betting-green/10 text-betting-green border border-betting-green/30 text-[10px] font-black px-3 py-1 rounded uppercase tracking-[0.2em]">
                    {pickOfTheDay.confidence}% HIT RATE
                  </span>
                </div>
                <h2 className="text-4xl md:text-5xl font-black text-on-surface leading-tight mb-2 uppercase italic tracking-tighter">
                  {pickOfTheDay.playerName?.toUpperCase()}
                </h2>
                <p className="text-xl font-black text-primary mb-4 uppercase tracking-widest">
                  {pickOfTheDay.type} <span className="text-betting-green">{(pickOfTheDay.suggestion || '').toUpperCase()} {pickOfTheDay.marketLine ?? pickOfTheDay.fairLine}</span>
                </p>
                {pickOfTheDay.rationale && (
                  <div className="bg-background/40 backdrop-blur-md p-4 rounded border border-outline-variant/20 mb-6">
                    <p className="text-on-surface-variant text-xs leading-relaxed italic font-medium line-clamp-3">
                      "{pickOfTheDay.rationale}"
                    </p>
                  </div>
                )}
                <div className="flex gap-4">
                  <button
                    onClick={() => handleAddToTracker(pickOfTheDay as SuggestionItem)}
                    className="flex-1 bg-primary text-black font-black py-3.5 rounded text-[10px] tracking-[0.2em] uppercase hover:brightness-110 active:scale-95 transition-all"
                  >
                    ADD TO PERFORMANCE LEDGER
                  </button>
                  {pickOfTheDay.playerId && (
                    <button
                      onClick={() => navigate(`/player/${pickOfTheDay.playerId}`)}
                      className="px-5 border border-outline-variant rounded hover:bg-surface-container-high transition-colors"
                    >
                      <span className="material-symbols-outlined text-on-surface-variant text-[20px]">person</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : bestMatchOfTheDay ? (
            <div className="bg-surface-container rounded p-8 border border-outline-variant/20 flex flex-col gap-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-1.5 h-1.5 bg-tertiary-container rounded-full animate-pulse" />
                <span className="text-[10px] font-black text-tertiary-container uppercase tracking-widest">Game of the Night</span>
              </div>
              <h2 className="text-3xl font-black uppercase italic text-primary-container">
                {bestMatchOfTheDay.away} @ {bestMatchOfTheDay.home}
              </h2>
              {bestMatchOfTheDay.outlook_summary && (
                <p className="text-on-surface-variant text-sm leading-relaxed italic">{bestMatchOfTheDay.outlook_summary}</p>
              )}
              <button
                onClick={() => navigate(`/game/${bestMatchOfTheDay.gameId}`)}
                className="mt-2 self-start bg-primary-container text-on-primary font-black py-3 px-6 rounded text-[10px] tracking-[0.2em] uppercase hover:brightness-110 transition-all"
              >
                VIEW ANALYSIS
              </button>
            </div>
          ) : (
            <div className="bg-surface-container rounded p-8 border border-outline-variant/20 flex items-center justify-center min-h-[200px]">
              <div className="text-center">
                <span className="material-symbols-outlined text-4xl text-on-surface/20 block mb-2">psychology</span>
                <p className="text-on-surface-variant text-sm font-bold uppercase tracking-widest">AI Pick of the Day loading…</p>
              </div>
            </div>
          )}
        </section>

        {/* ── Sidebar: Matchup Predictor ── */}
        <section className="xl:col-span-4">
          {/* Best Match Predictor */}
          {bestMatchOfTheDay && (
            <div className="bg-surface-container p-6 rounded border border-outline-variant/20">
              <h3 className="text-[10px] font-black text-primary-container tracking-[0.2em] uppercase mb-6 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary-container rounded-full" /> MATCHUP PREDICTOR
              </h3>
              {(() => {
                const pred = predictions.find(p => p.away === bestMatchOfTheDay.away && p.home === bestMatchOfTheDay.home) || predictions[0]
                if (!pred) return null
                const homeWinPct = Math.round(Number(pred.win_probability_home))
                return (
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <div className="text-center">
                        <img src={teamLogoUrl(pred.away)} alt={pred.away} className="w-10 h-10 mb-1 mx-auto grayscale opacity-60" onError={e => (e.target as HTMLImageElement).style.display = 'none'} />
                        <p className="text-[10px] font-black uppercase tracking-widest">{pred.away}</p>
                      </div>
                      <div className="flex-1 px-4 text-center">
                        <div className="h-1 w-full bg-outline-variant rounded-full mb-2 overflow-hidden flex">
                          <div className="bg-error h-full" style={{ width: `${100 - homeWinPct}%` }} />
                          <div className="bg-betting-green h-full" style={{ width: `${homeWinPct}%` }} />
                        </div>
                        <p className="text-[9px] font-black tracking-[0.2em] text-betting-green uppercase">{homeWinPct}% WIN PROB</p>
                      </div>
                      <div className="text-center">
                        <img src={teamLogoUrl(pred.home)} alt={pred.home} className="w-10 h-10 mb-1 mx-auto grayscale opacity-60" onError={e => (e.target as HTMLImageElement).style.display = 'none'} />
                        <p className="text-[10px] font-black uppercase tracking-widest">{pred.home}</p>
                      </div>
                    </div>
                    {pred.key_advantage_summary && (
                      <p className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest py-2 border-t border-outline-variant/10">
                        <span className="text-primary-container">KEY FACTOR</span> · {pred.key_advantage_summary}
                      </p>
                    )}
                    <button
                      onClick={() => navigate(`/game/${pred.gameId}`)}
                      className="w-full mt-4 py-2.5 bg-surface-container-high border border-outline-variant/30 rounded text-[10px] font-black uppercase tracking-widest hover:bg-primary-container/10 hover:text-primary-container transition-all"
                    >
                      FULL ANALYSIS
                    </button>
                  </div>
                )
              })()}
            </div>
          )}

        </section>

        {/* ── Quick Prop Lab (under AI Master Pick on xl) ── */}
        <section className="xl:col-span-8">
          <div className="bg-surface-container p-6 rounded border border-outline-variant/20">
            <h3 className="text-[10px] font-black text-on-surface-variant tracking-[0.2em] uppercase mb-6">QUICK PROP LAB</h3>
            <QuickPropLab />
          </div>
        </section>

        {/* ── High Conviction Props ── */}
        <section className="xl:col-span-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-[10px] font-black tracking-[0.2em] text-primary-container uppercase flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-primary-container rounded-full" /> HIGH CONVICTION PROPS
            </h2>
            <div className="flex gap-1.5">
              {(['ALL','PTS','REB','AST','3PM'] as const).map(cat => (
                <span key={cat} className="bg-surface-container-low px-3 py-1.5 text-[9px] font-black rounded uppercase tracking-widest cursor-pointer hover:bg-primary-container/20 hover:text-primary-container transition-all">
                  {cat}
                </span>
              ))}
            </div>
          </div>

          {(topPicksLoading || (dailyLoading && bestBets.length === 0)) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1,2,3,4].map(i => (
                <div key={i} className="bg-surface-container rounded h-48 animate-pulse" />
              ))}
            </div>
          ) : games.length === 0 ? (
            <div className="bg-surface-container p-8 rounded text-center border border-outline-variant/20">
              <p className="text-on-surface-variant text-sm font-bold uppercase tracking-widest">No games today — no props to show.</p>
            </div>
          ) : bestBets.length === 0 ? (
            <div className="bg-surface-container p-8 rounded text-center border border-outline-variant/20">
              <p className="text-on-surface-variant text-sm font-bold uppercase tracking-widest">Props are being generated — check back soon.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {bestBets.slice(0, 8).map((b, i) => (
                <div key={i} className="bg-surface-container rounded overflow-hidden flex flex-col border border-outline-variant/20 hover:border-primary-container/50 transition-all duration-300">
                  <div className="p-5 flex gap-4">
                    <div className="w-16 h-16 rounded bg-background overflow-hidden shrink-0 border border-outline-variant/20">
                      <PlayerAvatar playerId={b.playerId ?? 0} playerName={b.playerName} size="medium" className="w-full h-full object-cover grayscale brightness-75" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1">
                        <h4 className="text-[10px] font-black uppercase tracking-widest text-on-surface truncate">{b.playerName}</h4>
                        <span className={`text-[8px] font-black px-1.5 py-0.5 rounded shrink-0 ml-1 ${tierColor(b.tier)}`}>{tierLabel(b.tier)}</span>
                      </div>
                      <p className={`text-[10px] font-black uppercase tracking-widest mb-3 ${b.suggestion === 'over' ? 'text-betting-green' : 'text-error'}`}>
                        {b.type} {(b.suggestion || '').toUpperCase()} {b.marketLine ?? b.fairLine}
                      </p>
                      <div className="h-1 w-full bg-background rounded-full overflow-hidden">
                        <div className={`h-full ${confBarColor(b.confidence)}`} style={{ width: `${Number(b.confidence) || 0}%` }} />
                      </div>
                      <div className="flex justify-between mt-1.5 text-[8px] font-black text-on-surface-variant uppercase tracking-[0.1em]">
                        <span>Conf: {b.confidence}%</span>
                        {b.fairLine != null && b.marketLine != null && (
                          <span className={b.fairLine > b.marketLine ? 'text-betting-green' : 'text-error'}>
                            Fair: {b.fairLine}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {(b.rationale || b.matchup_explanation) && (
                    <div className="px-5 py-3 bg-background/50 border-t border-outline-variant/20">
                      <p className="text-[9px] text-on-surface-variant italic leading-relaxed line-clamp-2">{b.rationale || b.matchup_explanation}</p>
                    </div>
                  )}
                  <button
                    onClick={() => handleAddToTracker(b)}
                    disabled={isAddingToTracker}
                    className="w-full bg-surface-container-low text-primary text-[9px] font-black py-3 uppercase tracking-[0.2em] hover:bg-primary-container hover:text-on-primary transition-all mt-auto"
                  >
                    TRACK PERFORMANCE
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Hot Form Ledger ── */}
        <section className="xl:col-span-6">
          <div className="bg-surface-container p-6 rounded border border-outline-variant/20 h-full">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-[10px] font-black text-primary-container tracking-[0.2em] uppercase flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary-container rounded-full" /> HOT FORM LEDGER
              </h3>
              <div className="flex gap-1.5">
                <button
                  onClick={() => setFeaturedFilter('hot')}
                  className={`text-[8px] font-black px-2 py-1 rounded uppercase cursor-pointer transition-all ${featuredFilter === 'hot' ? 'bg-primary-container text-on-primary' : 'bg-surface-container-low text-on-surface-variant border border-outline-variant/30'}`}
                >HOT</button>
                <button
                  onClick={() => setFeaturedFilter('all')}
                  className={`text-[8px] font-black px-2 py-1 rounded uppercase cursor-pointer transition-all ${featuredFilter === 'all' ? 'bg-primary-container text-on-primary' : 'bg-surface-container-low text-on-surface-variant border border-outline-variant/30'}`}
                >ALL</button>
              </div>
            </div>
            {hotFormLoading ? (
              <div className="space-y-3">
                {[1,2,3].map(i => <div key={i} className="bg-background h-14 rounded animate-pulse" />)}
              </div>
            ) : featuredPlayers.length === 0 ? (
              <p className="text-on-surface-variant text-xs font-bold uppercase tracking-widest text-center py-6">No hot form data today</p>
            ) : (
              <div className="space-y-3">
                {featuredPlayers.map((p, i) => (
                  <button
                    key={p.id}
                    onClick={() => navigate(`/player/${p.id}`)}
                    className="w-full flex items-center gap-4 bg-background p-4 rounded border border-outline-variant/10 hover:border-betting-green/30 transition-colors text-left"
                  >
                    <span className={`text-xl font-black italic w-8 ${i === 0 ? 'text-betting-green' : i === 1 ? 'text-primary' : 'text-on-surface-variant'}`}>
                      #{String(i + 1).padStart(2, '0')}
                    </span>
                    <PlayerAvatar playerId={p.id} playerName={p.name} size="small" className="w-8 h-8 rounded shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-black uppercase tracking-widest truncate">{p.name}</p>
                      <p className="text-[10px] text-on-surface-variant font-medium truncate">
                        {p.highlight.type} · {p.highlight.confidence}% conf
                      </p>
                    </div>
                    <span className={`text-xs font-black tracking-tighter ${(p.confidence ?? 0) >= 70 ? 'text-betting-green' : 'text-primary'}`}>
                      {p.confidence}%
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── Stat Leaders ── */}
        <section className="xl:col-span-6">
          <div className="bg-surface-container p-6 rounded border border-outline-variant/20 h-full">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-[10px] font-black text-on-surface-variant tracking-[0.2em] uppercase">STAT LEADERS</h3>
              <div className="flex gap-1.5">
                <button
                  onClick={() => setStatLeadersFilterToday(false)}
                  className={`text-[8px] font-black px-2 py-1 rounded uppercase cursor-pointer transition-all ${!statLeadersFilterToday ? 'bg-primary-container text-on-primary' : 'bg-surface-container-low text-on-surface-variant border border-outline-variant/30'}`}
                >SEASON</button>
                <button
                  onClick={() => setStatLeadersFilterToday(true)}
                  className={`text-[8px] font-black px-2 py-1 rounded uppercase cursor-pointer transition-all ${statLeadersFilterToday ? 'bg-primary-container text-on-primary' : 'bg-surface-container-low text-on-surface-variant border border-outline-variant/30'}`}
                >TODAY</button>
              </div>
            </div>
            {(statLeadersFilterToday ? dailyLoading : leagueStatLeadersLoading) ? (
              <div className="space-y-2">
                {[1,2,3,4].map(i => <div key={i} className="bg-background h-10 rounded animate-pulse" />)}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[9px] font-black text-on-surface-variant uppercase tracking-[0.2em] border-b border-outline-variant/20">
                      <th className="pb-3 px-2">PLAYER</th>
                      <th className="pb-3 text-right px-2">STAT</th>
                      <th className="pb-3 text-right px-2">CAT</th>
                    </tr>
                  </thead>
                  <tbody className="text-[10px] font-black uppercase tracking-widest">
                    {(['PTS','AST','REB'] as const).flatMap(cat =>
                      (statLeaders[cat] ?? []).slice(0, 2).map((s: any, j: number) => (
                        <tr key={`${cat}-${j}`} className="border-b border-outline-variant/10 hover:bg-background/50 transition-colors">
                          <td className="py-3 px-2">
                            <button onClick={() => navigate(`/player/${s.playerId}`)} className="flex items-center gap-2 hover:text-primary-container transition-colors text-left">
                              <PlayerAvatar playerId={s.playerId} playerName={s.playerName} size="small" className="w-6 h-6 rounded shrink-0" />
                              <span className="truncate max-w-[100px]">{s.playerName}</span>
                            </button>
                          </td>
                          <td className="py-3 px-2 text-right text-primary">{(s.fairLine ?? s.marketLine ?? 0).toFixed(1)}</td>
                          <td className="py-3 px-2 text-right text-on-surface-variant">{cat}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* ── Prop Explorer Terminal ── */}
        <section className="xl:col-span-12">
          <div className="bg-surface-container rounded border border-outline-variant/20 overflow-hidden">
            <div className="p-6 border-b border-outline-variant/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <h2 className="text-[10px] font-black tracking-[0.2em] text-primary-container uppercase">PROP EXPLORER TERMINAL</h2>
              <div className="flex flex-wrap gap-2">
                <button className="px-3 py-1.5 bg-background border border-outline-variant/20 rounded text-[9px] font-black uppercase tracking-widest hover:border-primary-container transition-all">
                  70%+ CONFIDENCE
                </button>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[14px] text-on-surface-variant">search</span>
                  <input
                    className="pl-8 pr-4 py-1.5 bg-background border border-outline-variant/20 rounded text-[9px] font-black uppercase tracking-widest focus:ring-primary-container focus:border-primary-container w-48"
                    placeholder="FILTER BY PLAYER..."
                    readOnly
                  />
                </div>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left min-w-[800px]">
                <thead className="bg-background">
                  <tr className="text-[9px] font-black text-on-surface-variant uppercase tracking-[0.2em]">
                    <th className="px-6 py-4">PLAYER IDENTITY</th>
                    <th className="px-6 py-4">PROP</th>
                    <th className="px-6 py-4">LINE</th>
                    <th className="px-6 py-4">FAIR VALUE</th>
                    <th className="px-6 py-4">AI CONFIDENCE</th>
                    <th className="px-6 py-4 text-center">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10 text-[10px] font-black uppercase tracking-widest">
                  {bestBets.slice(0, 8).map((b, i) => (
                    <tr key={i} className="hover:bg-surface-container-high transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded bg-background overflow-hidden border border-outline-variant/20">
                            <PlayerAvatar playerId={b.playerId ?? 0} playerName={b.playerName} size="small" className="w-full h-full object-cover grayscale opacity-70" />
                          </div>
                          <div>
                            <p className="text-on-surface">{b.playerName}</p>
                            <p className="text-[8px] text-on-surface-variant opacity-60 normal-case">{b.type}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`${b.suggestion === 'over' ? 'text-betting-green' : 'text-error'}`}>
                          {(b.suggestion || '').toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-primary-container">{b.marketLine ?? b.fairLine}</td>
                      <td className="px-6 py-4 text-betting-green">{b.fairLine ?? '—'}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-20 h-1 bg-background rounded-full overflow-hidden">
                            <div className={`${confBarColor(b.confidence)} h-full`} style={{ width: `${Number(b.confidence) || 0}%` }} />
                          </div>
                          <span className={`text-[9px] ${(b.confidence ?? 0) >= 70 ? 'text-betting-green' : 'text-primary'}`}>{b.confidence}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button onClick={() => handleAddToTracker(b)} className="material-symbols-outlined text-primary hover:scale-110 transition-transform active:scale-90 text-[20px]">
                          add_circle
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {bestBets.length === 0 && !dailyLoading && (
              <div className="p-8 text-center text-on-surface-variant text-sm font-bold uppercase tracking-widest">
                No props available for today's slate.
              </div>
            )}
          </div>
        </section>

        {/* ── News Feed ── */}
        <section className="xl:col-span-12">
          <div className="bg-surface-container rounded border border-outline-variant/20 overflow-hidden">
            <div className="p-4 border-b border-outline-variant/20">
              <h2 className="text-[10px] font-black tracking-[0.2em] text-primary-container uppercase flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px]">newspaper</span> NBA NEWS WIRE
              </h2>
            </div>
            <div className="p-4">
              <PlayerNewsSection />
            </div>
          </div>
        </section>

      </div>
    </div>
  )
}
