import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, getApiBaseDisplay } from '../utils/api'

async function fetchHealth() {
  return apiGet('/api/v1/admin/health')
}

async function fetchCacheStatus() {
  return apiGet('/api/v1/admin/cache/status')
}

async function refreshDailyProps() {
  return apiPost('/api/v1/admin/refresh/daily-props?min_confidence=50&limit=50')
}

async function refreshAll() {
  return apiPost('/api/v1/admin/refresh/all')
}

async function warmDashboard() {
  return apiPost('/api/v1/admin/warm-dashboard')
}

async function syncPlayers() {
  return apiPost('/api/v1/admin/sync/players')
}

async function syncTeams() {
  return apiPost('/api/v1/admin/sync/teams')
}

async function fetchTeamsStatus() {
  return apiGet('/api/v1/admin/teams/status')
}

async function clearAllCache() {
  return apiPost('/api/v1/admin/cache/clear')
}

async function clearDailyPropsCache() {
  return apiPost('/api/v1/admin/cache/clear/daily-props')
}

async function clearTeamsCache() {
  return apiPost('/api/v1/admin/cache/clear/teams')
}

async function fetchAIEnabled() {
  return apiGet('/api/v1/admin/settings/ai-enabled')
}

async function setAIEnabled(enabled: boolean) {
  return apiPost('/api/v1/admin/settings/ai-enabled', { enabled })
}

async function refreshDailyPropsCustom(params: { minConfidence: number; limit: number }) {
  const qs = new URLSearchParams({
    min_confidence: String(params.minConfidence),
    limit: String(params.limit),
  })
  return apiPost(`/api/v1/admin/refresh/daily-props?${qs}`)
}

async function runDataIntegrityCheck(season?: string) {
  const endpoint = season ? `/api/v1/admin/data-integrity/check?season=${encodeURIComponent(season)}` : '/api/v1/admin/data-integrity/check'
  return apiPost(endpoint)
}

async function fetchDataIntegrityStatus() {
  return apiGet('/api/v1/admin/data-integrity/status')
}

async function checkPlayersIntegrity() {
  return apiPost('/api/v1/admin/data-integrity/check/players')
}

async function checkGameStatsIntegrity(season?: string) {
  const endpoint = season ? `/api/v1/admin/data-integrity/check/game-stats?season=${encodeURIComponent(season)}` : '/api/v1/admin/data-integrity/check/game-stats'
  return apiPost(endpoint)
}

async function checkPropSuggestionsIntegrity() {
  return apiPost('/api/v1/admin/data-integrity/check/prop-suggestions')
}

async function cleanRecentPlayerNames() {
  return apiPost('/api/v1/admin/players/clean-recent-names')
}

async function refreshDefensiveRanks(season?: string) {
  const endpoint = season
    ? `/api/v1/admin/refresh/defensive-ranks?season=${encodeURIComponent(season)}`
    : '/api/v1/admin/refresh/defensive-ranks'
  return apiPost(endpoint)
}

async function refreshPaceRanks(season?: string) {
  const endpoint = season
    ? `/api/v1/admin/refresh/pace-ranks?season=${encodeURIComponent(season)}`
    : '/api/v1/admin/refresh/pace-ranks'
  return apiPost(endpoint)
}

async function refreshPositionDefenseRanks(season?: string) {
  const endpoint = season
    ? `/api/v1/admin/refresh/position-defense-ranks?season=${encodeURIComponent(season)}`
    : '/api/v1/admin/refresh/position-defense-ranks'
  return apiPost(endpoint)
}

async function clearTodaysGamesCache() {
  return apiPost('/api/v1/admin/cache/clear/todays-games')
}

async function clearGamePredictionsCache() {
  return apiPost('/api/v1/admin/cache/clear/game-predictions')
}

async function settleAccuracy(settleDate?: string, season?: string) {
  const params = new URLSearchParams()
  if (settleDate) params.set('settle_date', settleDate)
  if (season) params.set('season', season)
  const q = params.toString() ? `?${params.toString()}` : ''
  return apiPost(`/api/v1/admin/settle-accuracy${q}`)
}

async function cacheCleanup() {
  return apiPost('/api/v1/admin/cache/cleanup')
}

async function refreshStatLeaders() {
  return apiPost('/api/v1/admin/refresh/stat-leaders')
}

async function refreshTopPicks() {
  return apiPost('/api/v1/admin/refresh/top-picks')
}

async function fetchRateLimits() {
  return apiGet('/api/v1/admin/rate-limits')
}

interface ActivityLog {
  id: string
  timestamp: Date
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  details?: string
}

export default function AdminDashboard() {
  const queryClient = useQueryClient()
  const [integritySeason, setIntegritySeason] = useState('2025-26')
  const [settleDateInput, setSettleDateInput] = useState('')
  const [settleSeasonInput, setSettleSeasonInput] = useState('2025-26')
  const [dailyPropsParams, setDailyPropsParams] = useState({ minConfidence: 50, limit: 50 })
  const [activityLog, setActivityLog] = useState<ActivityLog[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)
  
  const { data: health, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery({ 
    queryKey: ['admin-health'], 
    queryFn: fetchHealth, 
    refetchInterval: 30000,
    staleTime: 10000
  })
  const { data: cacheStatus, isLoading: cacheStatusLoading, error: cacheStatusError, refetch: refetchCacheStatus } = useQuery({ 
    queryKey: ['cache-status'], 
    queryFn: fetchCacheStatus, 
    refetchInterval: 15000,
    staleTime: 5000
  })
  const { data: teamsStatus, isLoading: teamsStatusLoading, error: teamsStatusError, refetch: refetchTeamsStatus } = useQuery({ 
    queryKey: ['teams-status'], 
    queryFn: fetchTeamsStatus, 
    refetchInterval: 20000,
    staleTime: 10000
  })
  const { data: aiStatus, isLoading: aiStatusLoading, refetch: refetchAIStatus } = useQuery({
    queryKey: ['ai-enabled'],
    queryFn: fetchAIEnabled,
    refetchInterval: 30000,
    staleTime: 10000
  })
  
  const { data: integrityStatus, isLoading: integrityStatusLoading, refetch: refetchIntegrityStatus } = useQuery({
    queryKey: ['data-integrity-status'],
    queryFn: fetchDataIntegrityStatus,
    refetchInterval: 60000, // Check every minute
    staleTime: 30000
  })

  const { data: rateLimits, refetch: refetchRateLimits } = useQuery({
    queryKey: ['admin-rate-limits'],
    queryFn: fetchRateLimits,
    staleTime: 60000
  })

  // Auto-scroll activity log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activityLog])

  const addActivityLog = (type: ActivityLog['type'], message: string, details?: string) => {
    const log: ActivityLog = {
      id: `log-${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      type,
      message,
      details
    }
    setActivityLog(prev => [...prev.slice(-49), log]) // Keep last 50 entries
  }

  const warmDashboardMutation = useMutation({
    mutationFn: warmDashboard,
    onMutate: () => {
      addActivityLog('info', 'Warming dashboard (daily props, top picks, game predictions, stat leaders)...')
    },
    onSuccess: (data) => {
      const results = data?.results || {}
      addActivityLog('success', 'Dashboard warmed', Object.keys(results).map(k => `${k}: ${typeof results[k] === 'number' ? results[k] : results[k]?.count ?? results[k]}`).join(', '))
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
      queryClient.invalidateQueries({ queryKey: ['daily-props'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Warm dashboard failed', error.message)
    }
  })

  const syncMutation = useMutation({
    mutationFn: syncPlayers,
    onMutate: () => {
      addActivityLog('info', 'Syncing players from NBA API...')
    },
    onSuccess: (data) => {
      addActivityLog('success', `Player sync completed`, `Synced ${data?.count || 0} players`)
      refetchHealth()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Player sync failed', error.message)
    }
  })

  const syncTeamsMutation = useMutation({
    mutationFn: syncTeams,
    onMutate: () => {
      addActivityLog('info', 'Syncing teams from NBA API...')
    },
    onSuccess: (data) => {
      addActivityLog('success', `Team sync completed`, `Synced ${data?.count || 0} teams`)
      refetchHealth()
      refetchTeamsStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Team sync failed', error.message)
    }
  })

  const refreshDailyPropsMutation = useMutation({
    mutationFn: refreshDailyProps,
    onMutate: () => {
      addActivityLog('info', 'Refreshing daily props cache...')
    },
    onSuccess: (data) => {
      addActivityLog('success', `Daily props refreshed`, `Cached ${data?.count ?? data?.message ?? 0} props`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-props'] })
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Daily props refresh failed', error.message)
    }
  })

  const refreshAllMutation = useMutation({
    mutationFn: refreshAll,
    onMutate: () => {
      addActivityLog('info', 'Refreshing all caches...')
    },
    onSuccess: (data) => {
      const results = data?.results || {}
      const parts = Object.entries(results).map(([k, v]) => `${k}: ${typeof v === 'object' && v && 'count' in v ? (v as { count?: number }).count : v}`).filter(Boolean)
      addActivityLog('success', 'All services refreshed', parts.slice(0, 8).join(', '))
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-props'] })
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Refresh all failed', error.message)
    }
  })

  const clearAllCacheMutation = useMutation({
    mutationFn: clearAllCache,
    onMutate: () => {
      addActivityLog('warning', 'Clearing all caches...')
    },
    onSuccess: (_data: { entries_cleared?: number; message?: string }) => {
      addActivityLog('success', 'All caches cleared', _data?.message ?? 'Refresh the page or Warm dashboard to reload data.')
      refetchCacheStatus()
      refetchHealth()
      // Invalidate all dashboard and data queries so next visit refetches fresh data
      queryClient.invalidateQueries({ queryKey: ['games-today'] })
      queryClient.invalidateQueries({ queryKey: ['games-predictions'] })
      queryClient.invalidateQueries({ queryKey: ['daily-50'] })
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
      queryClient.invalidateQueries({ queryKey: ['daily-hot-form'] })
      queryClient.invalidateQueries({ queryKey: ['pick-of-the-day'] })
      queryClient.invalidateQueries({ queryKey: ['best-match-of-the-day'] })
      queryClient.invalidateQueries({ queryKey: ['stat-leaders'] })
      queryClient.invalidateQueries({ queryKey: ['team-stats-ranks'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Cache clear failed', error.message)
    }
  })

  const clearDailyPropsCacheMutation = useMutation({
    mutationFn: clearDailyPropsCache,
    onMutate: () => {
      addActivityLog('warning', 'Clearing daily props cache...')
    },
    onSuccess: () => {
      addActivityLog('success', 'Daily props cache cleared')
      refetchCacheStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Cache clear failed', error.message)
    }
  })

  const clearTeamsCacheMutation = useMutation({
    mutationFn: clearTeamsCache,
    onMutate: () => {
      addActivityLog('warning', 'Clearing teams and players cache...')
    },
    onSuccess: (data: any) => {
      const teamsCount = data?.teams_cleared || 0
      const playersCount = data?.players_cleared || 0
      addActivityLog('success', `Teams and players cache cleared (${teamsCount} teams, ${playersCount} players)`)
      refetchCacheStatus()
      refetchTeamsStatus()
      queryClient.invalidateQueries({ queryKey: ['team-stats-ranks'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Cache clear failed', error.message)
    }
  })

  const setAIEnabledMutation = useMutation({
    mutationFn: setAIEnabled,
    onMutate: (enabled: boolean) => {
      addActivityLog('info', `${enabled ? 'Enabling' : 'Disabling'} AI features...`)
    },
    onSuccess: (data) => {
      addActivityLog('success', `AI features ${data.aiEnabled ? 'enabled' : 'disabled'}`)
      refetchAIStatus()
      // Invalidate queries to refresh data with new AI setting
      queryClient.invalidateQueries({ queryKey: ['daily-props'] })
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
      queryClient.invalidateQueries({ queryKey: ['props'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Failed to update AI setting', error.message)
    }
  })

  const refreshDailyPropsCustomMutation = useMutation({
    mutationFn: refreshDailyPropsCustom,
    onMutate: () => {
      addActivityLog('info', 'Refreshing daily props with custom params...', `Min Confidence: ${dailyPropsParams.minConfidence}%, Limit: ${dailyPropsParams.limit}`)
    },
    onSuccess: (data) => {
      addActivityLog('success', 'Daily props refreshed (custom)', String(data?.count ?? data?.message ?? ''))
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-props'] })
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Custom refresh failed', error.message)
    }
  })

  const integrityCheckMutation = useMutation({
    mutationFn: () => runDataIntegrityCheck(integritySeason),
    onMutate: () => {
      addActivityLog('info', 'Running full data integrity check...', `Season: ${integritySeason}`)
    },
    onSuccess: (data) => {
      const results = data?.results
      const summary = results?.summary || {}
      addActivityLog(
        summary.total_issues === 0 ? 'success' : 'warning',
        `Integrity check completed`,
        `Status: ${results?.overall_status || 'unknown'}, Issues: ${summary.total_issues || 0} (${summary.critical_issues || 0} critical, ${summary.high_issues || 0} high)`
      )
      refetchIntegrityStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Integrity check failed', error.message)
    }
  })

  const playersIntegrityMutation = useMutation({
    mutationFn: checkPlayersIntegrity,
    onMutate: () => {
      addActivityLog('info', 'Checking players data integrity...')
    },
    onSuccess: (data) => {
      const results = data?.results
      addActivityLog(
        results?.status === 'pass' ? 'success' : 'warning',
        `Players integrity check completed`,
        `Status: ${results?.status || 'unknown'}, Issues: ${results?.issues?.length || 0}`
      )
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Players integrity check failed', error.message)
    }
  })

  const gameStatsIntegrityMutation = useMutation({
    mutationFn: () => checkGameStatsIntegrity(integritySeason),
    onMutate: () => {
      addActivityLog('info', 'Checking game stats data integrity...', `Season: ${integritySeason}`)
    },
    onSuccess: (data) => {
      const results = data?.results
      addActivityLog(
        results?.status === 'pass' ? 'success' : 'warning',
        `Game stats integrity check completed`,
        `Status: ${results?.status || 'unknown'}, Issues: ${results?.issues?.length || 0}`
      )
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Game stats integrity check failed', error.message)
    }
  })

  const propSuggestionsIntegrityMutation = useMutation({
    mutationFn: checkPropSuggestionsIntegrity,
    onMutate: () => {
      addActivityLog('info', 'Checking prop suggestions data integrity...')
    },
    onSuccess: (data) => {
      const results = data?.results
      addActivityLog(
        results?.status === 'pass' ? 'success' : 'warning',
        `Prop suggestions integrity check completed`,
        `Status: ${results?.status || 'unknown'}, Issues: ${results?.issues?.length || 0}`
      )
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Prop suggestions integrity check failed', error.message)
    }
  })

  const cleanRecentNamesMutation = useMutation({
    mutationFn: cleanRecentPlayerNames,
    onMutate: () => {
      addActivityLog('info', 'Cleaning recent player names (rostered only)...')
    },
    onSuccess: (data: { recent_players?: number; names_updated?: number }) => {
      addActivityLog(
        'success',
        'Player names cleaned',
        `${data?.names_updated ?? 0} updated of ${data?.recent_players ?? 0} recent players`
      )
      refetchHealth()
      refetchCacheStatus()
      refetchTeamsStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Clean recent names failed', error.message)
    }
  })

  const refreshDefensiveRanksMutation = useMutation({
    mutationFn: () => refreshDefensiveRanks(integritySeason),
    onMutate: () => {
      addActivityLog('info', 'Refreshing defensive ranks cache...', `Season: ${integritySeason}`)
    },
    onSuccess: (data: { teamsRanked?: number }) => {
      addActivityLog(
        'success',
        'Defensive ranks refreshed',
        `${data?.teamsRanked ?? 0} teams cached (24h)`
      )
      refetchCacheStatus()
      refetchHealth()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Defensive ranks refresh failed', error.message)
    }
  })

  const refreshPaceRanksMutation = useMutation({
    mutationFn: () => refreshPaceRanks(integritySeason),
    onMutate: () => {
      addActivityLog('info', 'Refreshing pace ranks cache...', `Season: ${integritySeason}`)
    },
    onSuccess: (data: { teamsRanked?: number }) => {
      addActivityLog('success', 'Pace ranks refreshed', `${data?.teamsRanked ?? 0} teams cached (24h)`)
      refetchCacheStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Pace ranks refresh failed', error.message)
    }
  })

  const refreshPositionDefenseMutation = useMutation({
    mutationFn: () => refreshPositionDefenseRanks(integritySeason),
    onMutate: () => {
      addActivityLog('info', 'Refreshing position defense ranks...', `Season: ${integritySeason}`)
    },
    onSuccess: (data: { positions?: string[] }) => {
      addActivityLog('success', 'Position defense ranks refreshed', `Positions: ${(data?.positions ?? []).join(', ')}`)
      refetchCacheStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Position defense ranks refresh failed', error.message)
    }
  })

  const clearTodaysGamesCacheMutation = useMutation({
    mutationFn: clearTodaysGamesCache,
    onMutate: () => {
      addActivityLog('info', 'Clearing today\'s games and top-picks cache...')
    },
    onSuccess: (data: { todays_games_cleared?: number; top_picks_cleared?: number }) => {
      addActivityLog(
        'success',
        'Today\'s games & top-picks cache cleared',
        `Games: ${data?.todays_games_cleared ?? 0}, Top picks: ${data?.top_picks_cleared ?? 0}`
      )
      refetchCacheStatus()
      refetchHealth()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Clear today\'s games cache failed', error.message)
    }
  })

  const clearGamePredictionsCacheMutation = useMutation({
    mutationFn: clearGamePredictionsCache,
    onMutate: () => {
      addActivityLog('info', 'Clearing game predictions cache...')
    },
    onSuccess: (data: { game_predictions_cleared?: number; game_prediction_detail_cleared?: number }) => {
      addActivityLog(
        'success',
        'Game predictions cache cleared',
        `List: ${data?.game_predictions_cleared ?? 0}, Detail: ${data?.game_prediction_detail_cleared ?? 0}. Next request will rebuild with current ranks/stats.`
      )
      refetchCacheStatus()
      queryClient.invalidateQueries({ queryKey: ['games-predictions'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Clear game predictions cache failed', error.message)
    }
  })

  const settleAccuracyMutation = useMutation({
    mutationFn: () => settleAccuracy(settleDateInput || undefined, settleSeasonInput || undefined),
    onMutate: () => {
      addActivityLog(
        'info',
        `Settling prediction accuracy${settleDateInput ? ` for ${settleDateInput}` : ' for yesterday'}...`,
        settleSeasonInput ? `Season: ${settleSeasonInput}` : undefined
      )
    },
    onSuccess: (data: { status?: string; result?: any }) => {
      const r = data?.result
      const gp = r?.game_predictions
      const pick = r?.pick_of_the_day
      const tp = r?.top_picks
      const tpDetail =
        tp != null
          ? `Top picks: ${tp?.settled ?? 0} settled, ${tp?.not_found ?? 0} not in log${(tp?.errors?.length ?? 0) > 0 ? `, ${tp.errors.length} errors` : ''}`
          : ''
      addActivityLog(
        'success',
        'Accuracy settled',
        `Games: ${gp?.settled ?? 0} settled, ${gp?.not_found ?? 0} not found. Pick: ${pick?.settled ? 'settled' : pick?.reason ?? '—'}.${tpDetail ? ` ${tpDetail}.` : ''}`
      )
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Settle accuracy failed', error.message)
    }
  })

  const cacheCleanupMutation = useMutation({
    mutationFn: cacheCleanup,
    onMutate: () => {
      addActivityLog('info', 'Cleaning up expired cache entries...')
    },
    onSuccess: (data: { count?: number }) => {
      addActivityLog('success', 'Cache cleanup completed', `${data?.count ?? 0} expired entries removed`)
      refetchCacheStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Cache cleanup failed', error.message)
    }
  })

  const refreshStatLeadersMutation = useMutation({
    mutationFn: refreshStatLeaders,
    onMutate: () => {
      addActivityLog('info', 'Refreshing stat leaders cache...')
    },
    onSuccess: (data: { total_entries?: number }) => {
      addActivityLog('success', 'Stat leaders refreshed', `${data?.total_entries ?? 0} entries cached`)
      refetchCacheStatus()
      refetchHealth()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Stat leaders refresh failed', error.message)
    }
  })

  const refreshTopPicksMutation = useMutation({
    mutationFn: refreshTopPicks,
    onMutate: () => {
      addActivityLog('info', 'Refreshing top picks cache...')
    },
    onSuccess: (data: { count?: number }) => {
      addActivityLog('success', 'Top picks refreshed', `Cached ${data?.count ?? 0} items`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-props'] })
      queryClient.invalidateQueries({ queryKey: ['top-picks'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Top picks refresh failed', error.message)
    }
  })

  // Monitor data changes and log them
  useEffect(() => {
    if (health && !healthLoading) {
      // Monitor health status changes if needed
      // const status = health.status === 'healthy' ? 'healthy' : 'degraded'
    }
  }, [health, healthLoading])

  // Auto-refresh all data when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        addActivityLog('info', 'Page visible - refreshing all data...')
        refetchHealth()
        refetchCacheStatus()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Initial load activity log
  useEffect(() => {
    addActivityLog('info', 'Admin dashboard loaded', 'Initializing data pipeline...')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const formatTimeAgo = (timestamp: string | null | undefined) => {
    if (!timestamp) return 'Never'
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleTimeString()
  }

  return (
    <div className="container mx-auto px-2 sm:px-3 md:px-4 max-w-7xl">
      <div className="mt-2">
        <h1 className="text-lg md:text-xl font-bold tracking-tight text-gray-900 dark:text-slate-100 transition-colors duration-200">Admin Dashboard</h1>
        <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
          Monitor system health, data consistency, and refresh cached services.
          <span className="ml-1 text-gray-500 dark:text-gray-500">API: {getApiBaseDisplay()}</span>
        </p>
      </div>

      {/* Connection error banner */}
      {healthError && !healthLoading && (
        <div className="mt-3 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3">
          <p className="text-sm font-medium text-red-800 dark:text-red-200">Cannot reach backend</p>
          <p className="mt-1 text-xs text-red-700 dark:text-red-300">
            Requests are sent to: <code className="bg-red-100 dark:bg-red-900/40 px-1 rounded">{getApiBaseDisplay()}</code>
          </p>
          <p className="mt-1 text-xs text-red-600 dark:text-red-400">
            Ensure the backend is running (e.g. <code className="bg-red-100 dark:bg-red-900/40 px-1 rounded">PORT=8007</code>), and in dev that Vite proxy target matches it.
          </p>
          <button
            type="button"
            onClick={() => refetchHealth()}
            className="mt-2 px-3 py-1.5 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700"
          >
            Retry connection
          </button>
        </div>
      )}

      {/* System Health & Data Consistency */}
      <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
        <div className={`rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200 ${health?.status === 'healthy' ? 'ring-emerald-500/20 dark:ring-emerald-500/30' : 'ring-red-500/20 dark:ring-red-500/30'} ${healthLoading ? 'opacity-60' : ''}`}>
          <div className="flex items-center justify-between">
            <div className="h-10 w-10 rounded-xl flex items-center justify-center bg-emerald-50 dark:bg-emerald-900/30 transition-colors duration-200">
              {healthLoading ? (
                <svg className="animate-spin h-5 w-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5 text-emerald-600 dark:text-emerald-400">
                  <path fillRule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full transition-colors duration-200 ${health?.status === 'healthy' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'}`}>
              {healthLoading ? 'Loading...' : (health?.status === 'healthy' ? 'Healthy' : 'Degraded')}
            </span>
          </div>
          <div className="mt-2 text-xs font-medium text-gray-500 dark:text-gray-400 transition-colors duration-200">System Status</div>
          <div className="text-lg font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {healthLoading ? '...' : (health?.nbaApiAvailable ? '✅' : '❌')} NBA API
          </div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            {healthLoading ? 'Loading...' : `${health?.todayGames || 0} games today`}
            {healthError && <span className="text-red-600 dark:text-red-400 ml-1">(Error)</span>}
          </div>
        </div>

        <div className={`rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200 ${cacheStatusLoading ? 'opacity-60' : ''}`}>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 transition-colors duration-200">Daily Props</div>
          <div className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {cacheStatusLoading ? '...' : (cacheStatus?.dailyProps?.count ?? 0)}
          </div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            {cacheStatus?.dailyProps?.valid ? 'Cached' : 'Not cached'}
          </div>
        </div>

        <div className={`rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200 ${cacheStatusLoading ? 'opacity-60' : ''}`}>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 transition-colors duration-200">Today&apos;s Games</div>
          <div className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {cacheStatusLoading ? '...' : (health?.todayGames ?? 0)}
          </div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            {cacheStatus?.nbaApiCache?.todaysGames ? 'Cached' : 'Not cached'}
          </div>
        </div>

        <div className={`rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200 ${healthLoading ? 'opacity-60' : ''}`}>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 transition-colors duration-200">Last Health Check</div>
          <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {healthLoading ? '...' : (health?.timestamp ? formatTimeAgo(health.timestamp) : 'Never')}
          </div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            Auto-refreshes every 30s
            {healthError && <span className="text-red-600 dark:text-red-400 ml-1">(Error)</span>}
          </div>
        </div>
      </div>

      {/* Activity Log & Cache Status - Side by Side */}
      <div className="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-2 sm:gap-3">
        {/* Activity Log & Pipeline Status */}
        <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Activity Log</h2>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Real-time monitoring</p>
            </div>
            <button
              onClick={() => setActivityLog([])}
              className="px-2 py-1 text-xs font-medium text-gray-900 dark:text-slate-100 bg-gray-100 dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors duration-200"
            >
              Clear
            </button>
          </div>
          <div className="h-24 overflow-y-auto bg-gray-50 dark:bg-slate-700/50 rounded-lg p-2 border border-gray-200 dark:border-slate-600 transition-colors duration-200">
            {activityLog.length === 0 ? (
              <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-6 transition-colors duration-200">No activity yet</div>
            ) : (
              <div className="space-y-1">
                {activityLog.map((log) => (
                  <div key={log.id} className="text-xs flex items-start gap-2 py-0.5">
                    <span className="text-gray-400 dark:text-gray-500 font-mono text-[10px] transition-colors duration-200">
                      {log.timestamp.toLocaleTimeString()}
                    </span>
                    <span className={`font-medium text-[10px] transition-colors duration-200 ${
                      log.type === 'success' ? 'text-green-700 dark:text-green-400' :
                      log.type === 'error' ? 'text-red-700 dark:text-red-400' :
                      log.type === 'warning' ? 'text-amber-700 dark:text-amber-400' :
                      'text-blue-700 dark:text-blue-400'
                    }`}>
                      [{log.type.toUpperCase()}]
                    </span>
                    <span className="text-gray-700 dark:text-gray-300 flex-1 text-[10px] transition-colors duration-200">{log.message}</span>
                    {log.details && (
                      <span className="text-gray-500 dark:text-gray-400 text-[9px] transition-colors duration-200">({log.details})</span>
                    )}
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Data Consistency & Cache Status */}
        <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Cache Status</h2>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Data freshness</p>
            </div>
            <button
              onClick={() => {
                addActivityLog('info', 'Manually refreshing status...')
                refetchCacheStatus()
                refetchHealth()
                refetchCacheStatus()
                refetchCacheStatus()
              }}
              disabled={cacheStatusLoading || healthLoading}
              className="px-2 py-1 text-xs font-medium text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors duration-200"
            >
              {cacheStatusLoading ? '...' : 'Refresh'}
            </button>
          </div>

          {cacheStatusLoading ? (
            <div className="flex items-center justify-center py-3">
              <svg className="animate-spin h-4 w-4 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          ) : cacheStatusError ? (
            <div className="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-800 dark:text-red-300 transition-colors duration-200">
              Error: {String(cacheStatusError)}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-1.5">
            {/* Daily Props Cache */}
            <div className={`p-2 rounded-lg border-2 transition-colors duration-200 ${cacheStatus?.dailyProps?.valid ? 'border-green-200 dark:border-green-700/50 bg-green-50/50 dark:bg-green-900/20' : 'border-amber-200 dark:border-amber-700/50 bg-amber-50/50 dark:bg-amber-900/20'}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Daily Props</div>
                {cacheStatus?.dailyProps?.valid ? (
                  <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full font-medium transition-colors duration-200">Valid</span>
                ) : (
                  <span className="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full font-medium transition-colors duration-200">Stale/None</span>
                )}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 transition-colors duration-200">
                <span className="font-medium">Count:</span> {cacheStatus?.dailyProps?.count || 0}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
                <span className="font-medium">Updated:</span> {formatTimeAgo(cacheStatus?.dailyProps?.lastUpdated)}
              </div>
              {cacheStatus?.dailyProps?.date && (
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1 transition-colors duration-200">
                  Date: {cacheStatus.dailyProps.date}
                </div>
              )}
            </div>

          </div>
          )}
        </div>
      </div>

      {/* Data Integrity & AI Features - Side by Side */}
      <div className="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-2">
        {/* Data Integrity & Checksum */}
        <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Data Integrity</h2>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Validate data consistency</p>
            </div>
            <button
              onClick={() => {
                addActivityLog('info', 'Refreshing integrity status...')
                refetchIntegrityStatus()
              }}
              disabled={integrityStatusLoading}
              className="px-2 py-1 text-xs font-medium text-gray-900 dark:text-slate-100 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors duration-200"
            >
              {integrityStatusLoading ? '...' : 'Refresh'}
            </button>
          </div>

          {/* Overall Status */}
          {integrityStatus?.status === 'no_check' ? (
            <div className="p-2 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-lg text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
              No check run yet. Click "Run Full Check".
            </div>
          ) : integrityStatus?.results ? (
            <div className="space-y-1.5">
              {/* Overall Status Badge */}
              <div className={`p-2 rounded-lg border-2 transition-colors duration-200 ${
              integrityStatus.results.overall_status === 'pass' ? 'border-green-200 dark:border-green-700/50 bg-green-50/50 dark:bg-green-900/20' :
              integrityStatus.results.overall_status === 'warning' ? 'border-amber-200 dark:border-amber-700/50 bg-amber-50/50 dark:bg-amber-900/20' :
              'border-red-200 dark:border-red-700/50 bg-red-50/50 dark:bg-red-900/20'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Overall Status</div>
                <span className={`text-xs px-2 py-1 rounded-full font-medium transition-colors duration-200 ${
                  integrityStatus.results.overall_status === 'pass' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' :
                  integrityStatus.results.overall_status === 'warning' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' :
                  'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                }`}>
                  {integrityStatus.results.overall_status?.toUpperCase() || 'UNKNOWN'}
                </span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-1.5 text-xs">
                <div>
                  <div className="text-gray-600 dark:text-gray-400 transition-colors duration-200">Total Issues</div>
                  <div className="font-bold text-gray-900 dark:text-slate-100 transition-colors duration-200">{integrityStatus.results.summary?.total_issues || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600 dark:text-gray-400 transition-colors duration-200">Critical</div>
                  <div className="font-bold text-red-700 dark:text-red-400 transition-colors duration-200">{integrityStatus.results.summary?.critical_issues || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600 dark:text-gray-400 transition-colors duration-200">High</div>
                  <div className="font-bold text-orange-700 dark:text-orange-400 transition-colors duration-200">{integrityStatus.results.summary?.high_issues || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600 dark:text-gray-400 transition-colors duration-200">Medium</div>
                  <div className="font-bold text-amber-700 dark:text-amber-400 transition-colors duration-200">{integrityStatus.results.summary?.medium_issues || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600 dark:text-gray-400 transition-colors duration-200">Low</div>
                  <div className="font-bold text-gray-700 dark:text-gray-300 transition-colors duration-200">{integrityStatus.results.summary?.low_issues || 0}</div>
                </div>
              </div>
              {integrityStatus.checked_at && (
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                  Last checked: {formatTimeAgo(integrityStatus.checked_at)}
                </div>
              )}
            </div>

              {/* Individual Checks */}
              <div className="grid grid-cols-1 gap-1.5">
              {/* Players Check */}
              {integrityStatus.results.checks?.players && (
                <div className={`p-2 rounded-lg border transition-colors duration-200 ${
                  integrityStatus.results.checks.players.status === 'pass' ? 'border-green-200 dark:border-green-700/50 bg-green-50/30 dark:bg-green-900/20' : 'border-red-200 dark:border-red-700/50 bg-red-50/30 dark:bg-red-900/20'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Players</div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors duration-200 ${
                      integrityStatus.results.checks.players.status === 'pass' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                    }`}>
                      {integrityStatus.results.checks.players.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 space-y-0.5 transition-colors duration-200">
                    <div>Source: {integrityStatus.results.checks.players.stats?.source_count || 0}</div>
                    <div>DB: {integrityStatus.results.checks.players.stats?.db_count || 0}</div>
                    <div>Missing: {integrityStatus.results.checks.players.stats?.missing_in_db || 0}</div>
                    {integrityStatus.results.checks.players.stats?.checksum_source && (
                      <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-1 font-mono truncate transition-colors duration-200" title={integrityStatus.results.checks.players.stats.checksum_source}>
                        Source: {integrityStatus.results.checks.players.stats.checksum_source.slice(0, 8)}...
                      </div>
                    )}
                    {integrityStatus.results.checks.players.stats?.checksum_db && (
                      <div className="text-[10px] text-gray-500 dark:text-gray-400 font-mono truncate transition-colors duration-200" title={integrityStatus.results.checks.players.stats.checksum_db}>
                        DB: {integrityStatus.results.checks.players.stats.checksum_db.slice(0, 8)}...
                      </div>
                    )}
                  </div>
                  {integrityStatus.results.checks.players.issues?.length > 0 && (
                    <div className="mt-2 text-[10px] text-red-700 dark:text-red-400 transition-colors duration-200">
                      {integrityStatus.results.checks.players.issues.length} issue(s)
                    </div>
                  )}
                </div>
              )}

              {/* Game Stats Check */}
              {integrityStatus.results.checks?.game_stats && (
                <div className={`p-3 rounded-lg border transition-colors duration-200 ${
                  integrityStatus.results.checks.game_stats.status === 'pass' ? 'border-green-200 dark:border-green-700/50 bg-green-50/30 dark:bg-green-900/20' : 'border-red-200 dark:border-red-700/50 bg-red-50/30 dark:bg-red-900/20'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Game Stats</div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors duration-200 ${
                      integrityStatus.results.checks.game_stats.status === 'pass' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                    }`}>
                      {integrityStatus.results.checks.game_stats.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 space-y-0.5 transition-colors duration-200">
                    <div>Source: {integrityStatus.results.checks.game_stats.stats?.source_count || 0}</div>
                    <div>DB: {integrityStatus.results.checks.game_stats.stats?.db_count || 0}</div>
                    <div>Missing: {integrityStatus.results.checks.game_stats.stats?.missing_in_db || 0}</div>
                    <div>Invalid: {integrityStatus.results.checks.game_stats.stats?.invalid_data || 0}</div>
                  </div>
                  {integrityStatus.results.checks.game_stats.issues?.length > 0 && (
                    <div className="mt-2 text-[10px] text-red-700 dark:text-red-400 transition-colors duration-200">
                      {integrityStatus.results.checks.game_stats.issues.length} issue(s)
                    </div>
                  )}
                </div>
              )}

              {/* Prop Suggestions Check */}
              {integrityStatus.results.checks?.prop_suggestions && (
                <div className={`p-3 rounded-lg border transition-colors duration-200 ${
                  integrityStatus.results.checks.prop_suggestions.status === 'pass' ? 'border-green-200 dark:border-green-700/50 bg-green-50/30 dark:bg-green-900/20' : 'border-red-200 dark:border-red-700/50 bg-red-50/30 dark:bg-red-900/20'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Prop Suggestions</div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors duration-200 ${
                      integrityStatus.results.checks.prop_suggestions.status === 'pass' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                    }`}>
                      {integrityStatus.results.checks.prop_suggestions.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 space-y-0.5 transition-colors duration-200">
                    <div>Total: {integrityStatus.results.checks.prop_suggestions.stats?.total_suggestions || 0}</div>
                    <div>Recent: {integrityStatus.results.checks.prop_suggestions.stats?.recent_suggestions || 0}</div>
                    <div>Stale: {integrityStatus.results.checks.prop_suggestions.stats?.stale_suggestions || 0}</div>
                    <div>Invalid: {integrityStatus.results.checks.prop_suggestions.stats?.invalid_confidence || 0}</div>
                  </div>
                  {integrityStatus.results.checks.prop_suggestions.issues?.length > 0 && (
                    <div className="mt-2 text-[10px] text-red-700 dark:text-red-400 transition-colors duration-200">
                      {integrityStatus.results.checks.prop_suggestions.issues.length} issue(s)
                    </div>
                  )}
                </div>
              )}
            </div>

              {/* Issues List */}
              {integrityStatus.results.all_issues && integrityStatus.results.all_issues.length > 0 && (
                <div className="mt-1.5 p-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600 transition-colors duration-200">
                  <div className="text-xs font-semibold text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">Issues ({integrityStatus.results.all_issues.length})</div>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                  {integrityStatus.results.all_issues.slice(0, 10).map((issue: any, idx: number) => (
                    <div key={idx} className={`text-xs p-2 rounded border transition-colors duration-200 ${
                      issue.severity === 'critical' ? 'border-red-300 dark:border-red-700/50 bg-red-50 dark:bg-red-900/20' :
                      issue.severity === 'high' ? 'border-orange-300 dark:border-orange-700/50 bg-orange-50 dark:bg-orange-900/20' :
                      issue.severity === 'medium' ? 'border-amber-300 dark:border-amber-700/50 bg-amber-50 dark:bg-amber-900/20' :
                      'border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50'
                    }`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="font-medium text-gray-900 dark:text-slate-100 transition-colors duration-200">{issue.message}</div>
                          {issue.details && (
                            <div className="text-[10px] text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">
                              {typeof issue.details === 'string' ? issue.details : JSON.stringify(issue.details).slice(0, 100)}
                            </div>
                          )}
                        </div>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors duration-200 ${
                          issue.severity === 'critical' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' :
                          issue.severity === 'high' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300' :
                          issue.severity === 'medium' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' :
                          'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300'
                        }`}>
                          {issue.severity}
                        </span>
                      </div>
                    </div>
                  ))}
                  {integrityStatus.results.all_issues.length > 10 && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 text-center transition-colors duration-200">
                      ... and {integrityStatus.results.all_issues.length - 10} more issues
                    </div>
                  )}
                </div>
              </div>
              )}
            </div>
          ) : null}

          {/* Season for integrity and ranks */}
          <div className="mt-2">
            <label className="block text-[10px] text-gray-600 dark:text-gray-400 mb-0.5 transition-colors duration-200">Season (integrity & ranks)</label>
            <input
              value={integritySeason}
              onChange={(e) => setIntegritySeason(e.target.value)}
              className="w-24 px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
              placeholder="2025-26"
            />
          </div>

          {/* Action Buttons */}
          <div className="mt-2 grid grid-cols-2 gap-1.5">
          <button
            onClick={() => integrityCheckMutation.mutate()}
            disabled={integrityCheckMutation.isPending}
            className="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 text-xs font-semibold rounded-lg disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
          >
            {integrityCheckMutation.isPending ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Checking...
              </>
            ) : (
              'Run Full Check'
            )}
          </button>
          <button
            onClick={() => playersIntegrityMutation.mutate()}
            disabled={playersIntegrityMutation.isPending}
            className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 text-xs font-medium rounded-lg disabled:opacity-60 disabled:cursor-not-allowed border border-gray-300 dark:border-slate-600 transition-colors duration-200"
          >
            {playersIntegrityMutation.isPending ? 'Checking...' : 'Check Players'}
          </button>
          <button
            onClick={() => gameStatsIntegrityMutation.mutate()}
            disabled={gameStatsIntegrityMutation.isPending}
            className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 text-xs font-medium rounded-lg disabled:opacity-60 disabled:cursor-not-allowed border border-gray-300 dark:border-slate-600 transition-colors duration-200"
          >
            {gameStatsIntegrityMutation.isPending ? 'Checking...' : 'Check Game Stats'}
          </button>
          <button
            onClick={() => propSuggestionsIntegrityMutation.mutate()}
            disabled={propSuggestionsIntegrityMutation.isPending}
            className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 text-xs font-medium rounded-lg disabled:opacity-60 disabled:cursor-not-allowed border border-gray-300 dark:border-slate-600 transition-colors duration-200"
          >
            {propSuggestionsIntegrityMutation.isPending ? 'Checking...' : 'Check Props'}
          </button>
          </div>
        </div>

        {/* AI Features Toggle */}
        <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
          <div className="mb-2">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">AI Features</h2>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Enable/disable ML & LLM</p>
          </div>
          <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600 transition-colors duration-200">
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-900 dark:text-slate-100 transition-colors duration-200">Enable AI Features</div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">
              When enabled, prop evaluations use ML models for confidence prediction and LLM for rationale generation.
              When disabled, the system uses rule-based calculations only.
            </div>
          </div>
          <div className="ml-4">
            <button
              onClick={() => {
                const newValue = !(aiStatus?.aiEnabled ?? false)
                setAIEnabledMutation.mutate(newValue)
              }}
              disabled={setAIEnabledMutation.isPending || aiStatusLoading}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:ring-offset-2 ${
                (aiStatus?.aiEnabled ?? false) ? 'bg-blue-600 dark:bg-blue-500' : 'bg-gray-300 dark:bg-slate-600'
              } ${setAIEnabledMutation.isPending || aiStatusLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                  (aiStatus?.aiEnabled ?? false) ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
          <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
            Status: <span className={`font-medium transition-colors duration-200 ${(aiStatus?.aiEnabled ?? false) ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}`}>
              {(aiStatus?.aiEnabled ?? false) ? 'Enabled' : 'Disabled'}
            </span>
            {setAIEnabledMutation.isPending && (
              <span className="ml-2 text-blue-600 dark:text-blue-400 transition-colors duration-200">Updating...</span>
            )}
          </div>
        </div>
      </div>

      {/* Dashboard (homepage) – refresh and clear caches */}
      <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
        <div className="mb-2">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Dashboard (homepage)</h2>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Warm and refresh caches that feed the main dashboard</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-1.5">
          <button
            onClick={() => warmDashboardMutation.mutate()}
            disabled={warmDashboardMutation.isPending}
            className="px-3 py-2 bg-emerald-100 dark:bg-emerald-900/30 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 text-emerald-900 dark:text-emerald-300 text-xs font-semibold rounded-lg disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 border border-emerald-300 dark:border-emerald-700 transition-colors duration-200"
          >
            {warmDashboardMutation.isPending ? <span className="animate-pulse">Warming...</span> : <>Warm dashboard</>}
          </button>
          <button
            onClick={() => refreshDailyPropsMutation.mutate()}
            disabled={refreshDailyPropsMutation.isPending}
            className="px-3 py-2 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 text-xs font-semibold rounded-lg disabled:opacity-60 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
          >
            {refreshDailyPropsMutation.isPending ? 'Refreshing...' : 'Refresh Daily Props'}
          </button>
          <button
            onClick={() => refreshTopPicksMutation.mutate()}
            disabled={refreshTopPicksMutation.isPending}
            className="px-3 py-2 bg-violet-100 dark:bg-violet-900/30 hover:bg-violet-200 dark:hover:bg-violet-900/50 text-violet-900 dark:text-violet-300 text-xs font-semibold rounded-lg disabled:opacity-60 border border-violet-300 dark:border-violet-700 transition-colors duration-200"
          >
            {refreshTopPicksMutation.isPending ? 'Refreshing...' : 'Refresh Top Picks'}
          </button>
          <button
            onClick={() => refreshStatLeadersMutation.mutate()}
            disabled={refreshStatLeadersMutation.isPending}
            className="px-3 py-2 bg-indigo-100 dark:bg-indigo-900/30 hover:bg-indigo-200 dark:hover:bg-indigo-900/50 text-indigo-900 dark:text-indigo-300 text-xs font-semibold rounded-lg disabled:opacity-60 border border-indigo-300 dark:border-indigo-700 transition-colors duration-200"
          >
            {refreshStatLeadersMutation.isPending ? 'Refreshing...' : 'Refresh Stat Leaders'}
          </button>
          <button
            onClick={() => refreshAllMutation.mutate()}
            disabled={refreshAllMutation.isPending || refreshDailyPropsMutation.isPending || warmDashboardMutation.isPending}
            className="px-3 py-2 bg-purple-100 dark:bg-purple-900/30 hover:bg-purple-200 dark:hover:bg-purple-900/50 text-purple-900 dark:text-purple-300 text-xs font-semibold rounded-lg disabled:opacity-60 border border-purple-300 dark:border-purple-700 transition-colors duration-200"
          >
            {refreshAllMutation.isPending ? 'Refreshing All...' : 'Refresh All'}
          </button>
        </div>

        {(refreshDailyPropsMutation.isSuccess || warmDashboardMutation.isSuccess || refreshAllMutation.isSuccess) && (
          <div className="mt-2 p-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs text-emerald-800 dark:text-emerald-300 transition-colors duration-200">
            {refreshAllMutation.isSuccess && 'All services refreshed. '}
            {warmDashboardMutation.isSuccess && !refreshAllMutation.isSuccess && 'Dashboard warmed. '}
            {refreshDailyPropsMutation.isSuccess && !refreshAllMutation.isSuccess && !warmDashboardMutation.isSuccess && 'Daily props refreshed. '}
            Cache updated.
          </div>
        )}
        {(refreshDailyPropsMutation.isError || warmDashboardMutation.isError || refreshAllMutation.isError) && (
          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-800 dark:text-red-300 transition-colors duration-200">
            Error: {refreshAllMutation.error?.message || refreshDailyPropsMutation.error?.message || warmDashboardMutation.error?.message}
          </div>
        )}

        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-700">
          <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Clear dashboard caches (then use Warm dashboard to refill)</div>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => clearDailyPropsCacheMutation.mutate()}
              disabled={clearDailyPropsCacheMutation.isPending}
              className="px-3 py-1.5 text-xs bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-900 dark:text-red-300 rounded disabled:opacity-50 border border-red-300 dark:border-red-700 transition-colors duration-200"
            >
              {clearDailyPropsCacheMutation.isPending ? 'Clearing...' : 'Clear Daily Props'}
            </button>
            <button
              onClick={() => clearTodaysGamesCacheMutation.mutate()}
              disabled={clearTodaysGamesCacheMutation.isPending}
              className="px-3 py-1.5 text-xs bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 text-amber-900 dark:text-amber-300 rounded disabled:opacity-50 border border-amber-300 dark:border-amber-700 transition-colors duration-200"
              title="Today's games + top picks"
            >
              {clearTodaysGamesCacheMutation.isPending ? 'Clearing...' : "Clear Today's Games"}
            </button>
            <button
              onClick={() => clearGamePredictionsCacheMutation.mutate()}
              disabled={clearGamePredictionsCacheMutation.isPending}
              className="px-3 py-1.5 text-xs bg-sky-100 dark:bg-sky-900/30 hover:bg-sky-200 dark:hover:bg-sky-900/50 text-sky-900 dark:text-sky-300 rounded disabled:opacity-50 border border-sky-300 dark:border-sky-700 transition-colors duration-200"
            >
              {clearGamePredictionsCacheMutation.isPending ? 'Clearing...' : 'Clear Game Predictions'}
            </button>
          </div>
        </div>

        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-slate-700">
          <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Other cache</div>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => clearTeamsCacheMutation.mutate()}
              disabled={clearTeamsCacheMutation.isPending}
              className="px-3 py-1.5 text-xs bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 rounded disabled:opacity-50 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
            >
              Clear Teams
            </button>
            <button
              onClick={() => cacheCleanupMutation.mutate()}
              disabled={cacheCleanupMutation.isPending}
              className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 rounded disabled:opacity-50 border border-gray-300 dark:border-slate-600 transition-colors duration-200"
            >
              {cacheCleanupMutation.isPending ? 'Cleaning...' : 'Cache Cleanup'}
            </button>
            <button
              onClick={() => { if (confirm('Clear ALL caches? Next request will refetch.')) clearAllCacheMutation.mutate(); }}
              disabled={clearAllCacheMutation.isPending}
              className="px-3 py-1.5 text-xs bg-red-200 dark:bg-red-900/40 hover:bg-red-300 dark:hover:bg-red-900/60 text-red-900 dark:text-red-200 rounded font-semibold disabled:opacity-50 border border-red-400 dark:border-red-700 transition-colors duration-200"
            >
              Clear All Caches
            </button>
          </div>
        </div>

        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-slate-700">
          <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Daily props (custom params)</div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-[10px] text-gray-500 dark:text-gray-400">Min confidence</label>
            <input
              type="number"
              value={dailyPropsParams.minConfidence}
              onChange={(e) => setDailyPropsParams({ ...dailyPropsParams, minConfidence: Number(e.target.value) })}
              className="w-16 px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100"
              min={0}
              max={100}
            />
            <label className="text-[10px] text-gray-500 dark:text-gray-400">Limit</label>
            <input
              type="number"
              value={dailyPropsParams.limit}
              onChange={(e) => setDailyPropsParams({ ...dailyPropsParams, limit: Number(e.target.value) })}
              className="w-16 px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100"
              min={1}
              max={200}
            />
            <button
              onClick={() => refreshDailyPropsCustomMutation.mutate(dailyPropsParams)}
              disabled={refreshDailyPropsCustomMutation.isPending}
              className="px-3 py-1.5 text-xs bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 rounded disabled:opacity-50 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
            >
              {refreshDailyPropsCustomMutation.isPending ? 'Refreshing...' : 'Refresh with params'}
            </button>
          </div>
        </div>

        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-slate-700">
          <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 transition-colors duration-200">Accuracy</div>
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <label className="text-[10px] text-gray-500 dark:text-gray-400">Settle date</label>
            <input
              type="date"
              value={settleDateInput}
              onChange={(e) => setSettleDateInput(e.target.value)}
              className="px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100"
              title="Leave empty to settle yesterday"
            />
            <label className="text-[10px] text-gray-500 dark:text-gray-400">Season</label>
            <input
              value={settleSeasonInput}
              onChange={(e) => setSettleSeasonInput(e.target.value)}
              className="w-20 px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100"
              placeholder="2025-26"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => settleAccuracyMutation.mutate()}
              disabled={settleAccuracyMutation.isPending}
              className="px-3 py-1.5 text-xs bg-emerald-100 dark:bg-emerald-900/30 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 text-emerald-900 dark:text-emerald-300 rounded disabled:opacity-50 border border-emerald-300 dark:border-emerald-700 transition-colors duration-200"
            >
              {settleAccuracyMutation.isPending ? 'Settling...' : 'Settle accuracy'}
            </button>
            <Link
              to="/accuracy"
              className="px-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-100 rounded border border-slate-300 dark:border-slate-600 transition-colors duration-200 inline-block"
            >
              View accuracy
            </Link>
          </div>
        </div>

        <div className="mt-2 pt-2 border-t border-gray-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 transition-colors duration-200">Rate limits</span>
            <button type="button" onClick={() => refetchRateLimits()} className="text-[10px] text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-slate-100">
              Refresh
            </button>
          </div>
          {rateLimits?.providers && Object.keys(rateLimits.providers).length > 0 ? (
            <div className="flex flex-wrap gap-2 text-[10px] text-gray-600 dark:text-gray-400">
              {Object.entries(rateLimits.providers).map(([name, p]: [string, any]) => (
                <span key={name} className="px-1.5 py-0.5 bg-gray-100 dark:bg-slate-700 rounded border border-gray-200 dark:border-slate-600">
                  {name}: {p?.used ?? '?'}/{p?.limit ?? '?'}
                </span>
              ))}
            </div>
          ) : (
            <div className="text-[10px] text-gray-500 dark:text-gray-500">No rate limit data</div>
          )}
        </div>

        {(clearAllCacheMutation.isSuccess || clearDailyPropsCacheMutation.isSuccess || clearTeamsCacheMutation.isSuccess || clearTodaysGamesCacheMutation.isSuccess || clearGamePredictionsCacheMutation.isSuccess || cacheCleanupMutation.isSuccess || refreshStatLeadersMutation.isSuccess || refreshTopPicksMutation.isSuccess) && (
          <div className="mt-2 p-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded text-xs text-emerald-800 dark:text-emerald-300 transition-colors duration-200">
            {clearAllCacheMutation.isSuccess ? 'All caches cleared. Refresh the page or click Warm dashboard to reload data.' : 'Cache cleared / refreshed. Next request will use updated data.'}
          </div>
        )}
      </div>

      {/* Sync – NBA API */}
      <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
        <div className="mb-2">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Sync (NBA API)</h2>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Sync players and teams from NBA API</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 text-xs font-medium rounded-lg disabled:opacity-50 border border-gray-300 dark:border-slate-600 transition-colors duration-200"
          >
            {syncMutation.isPending ? 'Syncing...' : 'Sync Players'}
          </button>
          <button
            onClick={() => syncTeamsMutation.mutate()}
            disabled={syncTeamsMutation.isPending}
            className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 text-xs font-medium rounded-lg disabled:opacity-50 border border-gray-300 dark:border-slate-600 transition-colors duration-200"
          >
            {syncTeamsMutation.isPending ? 'Syncing...' : 'Sync Teams'}
          </button>
        </div>
      </div>

      {/* Player & context */}
      <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
        <div className="mb-2">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Player & context</h2>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Clean names and refresh opponent defense ranks for player profiles</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => cleanRecentNamesMutation.mutate()}
            disabled={cleanRecentNamesMutation.isPending}
            className="px-3 py-1.5 bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/50 text-amber-900 dark:text-amber-300 text-xs font-medium rounded-lg disabled:opacity-50 border border-amber-300 dark:border-amber-700 transition-colors duration-200"
          >
            {cleanRecentNamesMutation.isPending ? 'Running...' : 'Clean recent player names'}
          </button>
          <button
            onClick={() => refreshDefensiveRanksMutation.mutate()}
            disabled={refreshDefensiveRanksMutation.isPending}
            className="px-3 py-1.5 bg-sky-100 dark:bg-sky-900/30 hover:bg-sky-200 dark:hover:bg-sky-900/50 text-sky-900 dark:text-sky-300 text-xs font-medium rounded-lg disabled:opacity-50 border border-sky-300 dark:border-sky-700 transition-colors duration-200"
          >
            {refreshDefensiveRanksMutation.isPending ? 'Refreshing...' : 'Refresh defensive ranks'}
          </button>
          <button
            onClick={() => refreshPaceRanksMutation.mutate()}
            disabled={refreshPaceRanksMutation.isPending}
            className="px-3 py-1.5 bg-orange-100 dark:bg-orange-900/30 hover:bg-orange-200 dark:hover:bg-orange-900/50 text-orange-900 dark:text-orange-300 text-xs font-medium rounded-lg disabled:opacity-50 border border-orange-300 dark:border-orange-700 transition-colors duration-200"
          >
            {refreshPaceRanksMutation.isPending ? 'Refreshing...' : 'Refresh pace ranks'}
          </button>
          <button
            onClick={() => refreshPositionDefenseMutation.mutate()}
            disabled={refreshPositionDefenseMutation.isPending}
            className="px-3 py-1.5 bg-violet-100 dark:bg-violet-900/30 hover:bg-violet-200 dark:hover:bg-violet-900/50 text-violet-900 dark:text-violet-300 text-xs font-medium rounded-lg disabled:opacity-50 border border-violet-300 dark:border-violet-700 transition-colors duration-200"
          >
            {refreshPositionDefenseMutation.isPending ? 'Refreshing...' : 'Refresh position defense ranks'}
          </button>
        </div>
      </div>

      {/* Team Management */}
      <div className="mt-3 rounded-2xl bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-4 transition-colors duration-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Team Management</h2>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Sync and check team data from NBA API</p>
          </div>
          <div className="flex items-center gap-2">
            {teamsStatusLoading && (
              <svg className="animate-spin h-4 w-4 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            <button
              onClick={() => {
                addActivityLog('info', 'Refreshing teams status...')
                refetchTeamsStatus()
              }}
              disabled={teamsStatusLoading}
              className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors duration-200"
            >
              {teamsStatusLoading ? 'Refreshing...' : 'Refresh Status'}
            </button>
          </div>
        </div>

        {teamsStatusLoading ? (
          <div className="flex items-center justify-center py-4">
            <svg className="animate-spin h-5 w-5 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="ml-2 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">Loading teams status...</span>
          </div>
        ) : teamsStatusError ? (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-300 transition-colors duration-200">
            Error loading teams status: {String(teamsStatusError)}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-lg p-3 transition-colors duration-200">
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 transition-colors duration-200">Total Teams</div>
                <div className="text-2xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">{teamsStatus?.totalTeams || 0}</div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                  {teamsStatus?.cached ? (
                    <span className="text-green-600 dark:text-green-400">✓ Cached</span>
                  ) : (
                    <span className="text-amber-600 dark:text-amber-400">Not cached</span>
                  )}
                </div>
              </div>
              <div className={`bg-gray-50 dark:bg-slate-700/50 border rounded-lg p-3 transition-colors duration-200 ${
                teamsStatus?.integrity?.status === 'good' ? 'border-green-200 dark:border-green-700/50' :
                teamsStatus?.integrity?.status === 'warning' ? 'border-amber-200 dark:border-amber-700/50' :
                'border-red-200 dark:border-red-700/50'
              }`}>
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 transition-colors duration-200">Data Integrity</div>
                <div className={`text-lg font-semibold transition-colors duration-200 ${
                  teamsStatus?.integrity?.status === 'good' ? 'text-green-700 dark:text-green-400' :
                  teamsStatus?.integrity?.status === 'warning' ? 'text-amber-700 dark:text-amber-400' :
                  'text-red-700 dark:text-red-400'
                }`}>
                  {teamsStatus?.integrity?.status === 'good' ? '✓ Good' :
                   teamsStatus?.integrity?.status === 'warning' ? '⚠ Warning' :
                   '✗ Error'}
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                  {teamsStatus?.integrity?.coverage?.teams || 0}% teams, {teamsStatus?.integrity?.coverage?.players || 0}% players
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-lg p-3 transition-colors duration-200">
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 transition-colors duration-200">Total Players</div>
                <div className="text-2xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">{teamsStatus?.totalPlayers || 0}</div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                  {teamsStatus?.lastUpdated ? formatTimeAgo(teamsStatus.lastUpdated) : 'Never checked'}
                </div>
              </div>
            </div>

            {/* Integrity Details */}
            {teamsStatus?.integrity && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700/50 rounded-lg p-3 transition-colors duration-200">
                  <div className="text-xs font-medium text-green-700 dark:text-green-300 mb-1 transition-colors duration-200">Teams w/ Players</div>
                  <div className="text-xl font-semibold text-green-900 dark:text-green-100 transition-colors duration-200">{teamsStatus.integrity.teamsWithPlayers}</div>
                  <div className="text-xs text-green-600 dark:text-green-400 mt-1 transition-colors duration-200">
                    {teamsStatus.integrity.coverage?.teams || 0}% coverage
                  </div>
                </div>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50 rounded-lg p-3 transition-colors duration-200">
                  <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1 transition-colors duration-200">Teams w/o Players</div>
                  <div className="text-xl font-semibold text-amber-900 dark:text-amber-100 transition-colors duration-200">{teamsStatus.integrity.teamsWithoutPlayers}</div>
                  {teamsStatus.integrity.teamsWithoutPlayers > 0 && (
                    <div className="text-xs text-amber-600 dark:text-amber-400 mt-1 transition-colors duration-200">
                      {teamsStatus.teamsWithoutPlayers?.length || 0} shown
                    </div>
                  )}
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700/50 rounded-lg p-3 transition-colors duration-200">
                  <div className="text-xs font-medium text-green-700 dark:text-green-300 mb-1 transition-colors duration-200">Players w/ Teams</div>
                  <div className="text-xl font-semibold text-green-900 dark:text-green-100 transition-colors duration-200">{teamsStatus.integrity.playersWithTeams}</div>
                  <div className="text-xs text-green-600 dark:text-green-400 mt-1 transition-colors duration-200">
                    {teamsStatus.integrity.coverage?.players || 0}% coverage
                  </div>
                </div>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50 rounded-lg p-3 transition-colors duration-200">
                  <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1 transition-colors duration-200">Players w/o Teams</div>
                  <div className="text-xl font-semibold text-amber-900 dark:text-amber-100 transition-colors duration-200">{teamsStatus.integrity.playersWithoutTeams}</div>
                  {teamsStatus.integrity.playersWithoutTeams > 0 && (
                    <div className="text-xs text-amber-600 dark:text-amber-400 mt-1 transition-colors duration-200">
                      {Math.round((teamsStatus.integrity.playersWithoutTeams / (teamsStatus.totalPlayers || 1)) * 100)}% of total
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Teams Without Players Warning */}
            {teamsStatus?.teamsWithoutPlayers && teamsStatus.teamsWithoutPlayers.length > 0 && (
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50 rounded-lg transition-colors duration-200">
                <div className="text-xs font-semibold text-amber-900 dark:text-amber-200 mb-2 transition-colors duration-200">
                  ⚠ Teams Without Players ({teamsStatus.teamsWithoutPlayers.length})
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                  {teamsStatus.teamsWithoutPlayers.map((team: any) => (
                    <div key={team.id} className="text-xs p-1.5 bg-white dark:bg-slate-700 rounded border border-amber-200 dark:border-amber-700/50 transition-colors duration-200">
                      <div className="font-medium text-amber-900 dark:text-amber-200 transition-colors duration-200">{team.abbreviation}</div>
                      <div className="text-amber-700 dark:text-amber-300 truncate transition-colors duration-200">{team.name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => syncTeamsMutation.mutate()}
                disabled={syncTeamsMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 text-white text-sm font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors duration-200"
              >
                {syncTeamsMutation.isPending ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Syncing...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Sync Teams</span>
                  </>
                )}
              </button>
            </div>

            {syncTeamsMutation.isSuccess && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-sm text-emerald-800 dark:text-emerald-300 transition-colors duration-200">
                Teams synced successfully! {syncTeamsMutation.data?.count || 0} teams loaded.
              </div>
            )}

            {syncTeamsMutation.isError && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-800 dark:text-red-300 transition-colors duration-200">
                Error: {syncTeamsMutation.error?.message || 'Failed to sync teams'}
              </div>
            )}

            {teamsStatus?.teams && teamsStatus.teams.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-200">Team Preview (First 10)</div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                  {teamsStatus.teams.map((team: any) => (
                    <div key={team.id} className="text-xs p-2 bg-gray-50 dark:bg-slate-700/50 rounded border border-gray-200 dark:border-slate-600 transition-colors duration-200">
                      <div className="font-medium text-gray-900 dark:text-slate-100 truncate transition-colors duration-200">{team.abbreviation}</div>
                      <div className="text-gray-600 dark:text-gray-400 truncate transition-colors duration-200">{team.full_name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
