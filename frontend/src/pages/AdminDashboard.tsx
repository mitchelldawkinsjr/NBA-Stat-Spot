import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from '../utils/api'

async function fetchHealth() {
  return apiGet('/api/v1/admin/health')
}

async function fetchScanStatus() {
  return apiGet('/api/v1/admin/scan/status')
}

async function fetchBestBets() {
  return apiGet('/api/v1/admin/best-bets')
}

async function fetchCacheStatus() {
  return apiGet('/api/v1/admin/cache/status')
}

async function refreshDailyProps() {
  return apiPost('/api/v1/admin/refresh/daily-props?min_confidence=50&limit=50')
}

async function refreshHighHitRate() {
  return apiPost('/api/v1/admin/refresh/high-hit-rate?min_hit_rate=0.75&limit=10&last_n=10')
}

async function refreshAll() {
  return apiPost('/api/v1/admin/refresh/all')
}

async function triggerScan(params: { season: string; minConfidence: number; limit: number }) {
  const qs = new URLSearchParams({
    season: params.season,
    min_confidence: String(params.minConfidence),
    limit: String(params.limit),
  })
  return apiPost(`/api/v1/admin/scan/best-bets?${qs}`)
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

async function clearHighHitRateCache() {
  return apiPost('/api/v1/admin/cache/clear/high-hit-rate')
}

async function clearBestBetsCache() {
  return apiPost('/api/v1/admin/cache/clear/best-bets')
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

async function refreshHighHitRateCustom(params: { minHitRate: number; limit: number; lastN: number }) {
  const qs = new URLSearchParams({
    min_hit_rate: String(params.minHitRate),
    limit: String(params.limit),
    last_n: String(params.lastN),
  })
  return apiPost(`/api/v1/admin/refresh/high-hit-rate?${qs}`)
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

interface ActivityLog {
  id: string
  timestamp: Date
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  details?: string
}

export default function AdminDashboard() {
  const queryClient = useQueryClient()
  const [scanParams, setScanParams] = useState({ season: '2025-26', minConfidence: 65, limit: 50 })
  const [dailyPropsParams, setDailyPropsParams] = useState({ minConfidence: 50, limit: 50 })
  const [highHitRateParams, setHighHitRateParams] = useState({ minHitRate: 0.75, limit: 10, lastN: 10 })
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [activityLog, setActivityLog] = useState<ActivityLog[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)
  
  const { data: health, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery({ 
    queryKey: ['admin-health'], 
    queryFn: fetchHealth, 
    refetchInterval: 30000,
    staleTime: 10000
  })
  const { data: scanStatus, isLoading: scanStatusLoading, error: scanStatusError, refetch: refetchStatus } = useQuery({ 
    queryKey: ['scan-status'], 
    queryFn: fetchScanStatus, 
    refetchInterval: 10000,
    staleTime: 5000
  })
  const { data: bestBetsData, isLoading: bestBetsLoading, error: bestBetsError, refetch: refetchBestBets } = useQuery({ 
    queryKey: ['best-bets'], 
    queryFn: fetchBestBets,
    refetchInterval: 20000,
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

  const scanMutation = useMutation({
    mutationFn: triggerScan,
    onMutate: () => {
      addActivityLog('info', 'Starting prop scan...', `Season: ${scanParams.season}, Min Confidence: ${scanParams.minConfidence}%, Limit: ${scanParams.limit}`)
    },
    onSuccess: (data) => {
      addActivityLog('success', `Scan completed successfully`, `Found ${data?.count || 0} best bets`)
      setTimeout(() => {
        refetchBestBets()
        refetchStatus()
        refetchCacheStatus()
      }, 1000)
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Scan failed', error.message)
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
      refetchStatus()
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
      refetchStatus()
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
      addActivityLog('success', `Daily props refreshed`, `Cached ${data?.count || 0} props`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-50'] })
      queryClient.invalidateQueries({ queryKey: ['high-hit-rate'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Daily props refresh failed', error.message)
    }
  })

  const refreshHighHitRateMutation = useMutation({
    mutationFn: refreshHighHitRate,
    onMutate: () => {
      addActivityLog('info', 'Refreshing high hit rate cache...')
    },
    onSuccess: (data) => {
      addActivityLog('success', `High hit rate refreshed`, `Cached ${data?.count || 0} bets`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['high-hit-rate'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'High hit rate refresh failed', error.message)
    }
  })

  const refreshAllMutation = useMutation({
    mutationFn: refreshAll,
    onMutate: () => {
      addActivityLog('info', 'Refreshing all caches...')
    },
    onSuccess: (data) => {
      const results = data?.results || {}
      const dailyCount = results.dailyProps?.count || 0
      const hitRateCount = results.highHitRate?.count || 0
      addActivityLog('success', `All services refreshed`, `Daily Props: ${dailyCount}, High Hit Rate: ${hitRateCount}`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-50'] })
      queryClient.invalidateQueries({ queryKey: ['high-hit-rate'] })
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
    onSuccess: () => {
      addActivityLog('success', 'All caches cleared', 'Next requests will fetch fresh data')
      refetchCacheStatus()
      refetchHealth()
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

  const clearHighHitRateCacheMutation = useMutation({
    mutationFn: clearHighHitRateCache,
    onMutate: () => {
      addActivityLog('warning', 'Clearing high hit rate cache...')
    },
    onSuccess: () => {
      addActivityLog('success', 'High hit rate cache cleared')
      refetchCacheStatus()
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Cache clear failed', error.message)
    }
  })

  const clearBestBetsCacheMutation = useMutation({
    mutationFn: clearBestBetsCache,
    onMutate: () => {
      addActivityLog('warning', 'Clearing best bets cache...')
    },
    onSuccess: () => {
      addActivityLog('success', 'Best bets cache cleared')
      refetchCacheStatus()
      refetchBestBets()
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
      queryClient.invalidateQueries({ queryKey: ['daily-50'] })
      queryClient.invalidateQueries({ queryKey: ['high-hit-rate'] })
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
      addActivityLog('success', `Daily props refreshed (custom)`, `Cached ${data?.count || 0} props`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['daily-50'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Custom refresh failed', error.message)
    }
  })

  const refreshHighHitRateCustomMutation = useMutation({
    mutationFn: refreshHighHitRateCustom,
    onMutate: () => {
      addActivityLog('info', 'Refreshing high hit rate with custom params...', `Min Hit Rate: ${highHitRateParams.minHitRate}, Limit: ${highHitRateParams.limit}, Last N: ${highHitRateParams.lastN}`)
    },
    onSuccess: (data) => {
      addActivityLog('success', `High hit rate refreshed (custom)`, `Cached ${data?.count || 0} bets`)
      refetchCacheStatus()
      refetchHealth()
      queryClient.invalidateQueries({ queryKey: ['high-hit-rate'] })
    },
    onError: (error: Error) => {
      addActivityLog('error', 'Custom refresh failed', error.message)
    }
  })

  const integrityCheckMutation = useMutation({
    mutationFn: () => runDataIntegrityCheck(scanParams.season),
    onMutate: () => {
      addActivityLog('info', 'Running full data integrity check...', `Season: ${scanParams.season}`)
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
    mutationFn: () => checkGameStatsIntegrity(scanParams.season),
    onMutate: () => {
      addActivityLog('info', 'Checking game stats data integrity...', `Season: ${scanParams.season}`)
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
        refetchStatus()
        refetchBestBets()
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

  const bestBets = bestBetsData?.results || []
  
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
        <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">Monitor system health, data consistency, and refresh cached services.</p>
      </div>

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

        <div className={`rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200 ${scanStatusLoading ? 'opacity-60' : ''}`}>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 transition-colors duration-200">Total Players</div>
          <div className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {scanStatusLoading ? '...' : (scanStatus?.totalPlayers || health?.totalPlayers || 0)}
          </div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            {scanStatusLoading ? 'Loading...' : 'In database'}
            {scanStatusError && <span className="text-red-600 dark:text-red-400 ml-1">(Error)</span>}
          </div>
        </div>

        <div className={`rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-2.5 sm:p-3 transition-colors duration-200 ${bestBetsLoading ? 'opacity-60' : ''}`}>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 transition-colors duration-200">Best Bets</div>
          <div className="text-xl sm:text-2xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">
            {bestBetsLoading ? '...' : bestBets.length}
          </div>
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
            {bestBetsLoading ? 'Loading...' : (
              scanStatus?.lastScan || bestBetsData?.lastScanned 
                ? formatTimeAgo(scanStatus?.lastScan || bestBetsData?.lastScanned) 
                : (scanStatus?.bestBetsCount ? `${scanStatus.bestBetsCount} cached` : 'Not scanned')
            )}
            {bestBetsError && <span className="text-red-600 dark:text-red-400 ml-1">(Error)</span>}
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
                refetchStatus()
                refetchBestBets()
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

            {/* High Hit Rate Cache */}
            <div className={`p-2 rounded-lg border-2 transition-colors duration-200 ${cacheStatus?.highHitRate?.valid ? 'border-green-200 dark:border-green-700/50 bg-green-50/50 dark:bg-green-900/20' : 'border-amber-200 dark:border-amber-700/50 bg-amber-50/50 dark:bg-amber-900/20'}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">High Hit Rate</div>
                {cacheStatus?.highHitRate?.valid ? (
                  <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full font-medium transition-colors duration-200">Valid</span>
                ) : (
                  <span className="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full font-medium transition-colors duration-200">Stale/None</span>
                )}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 transition-colors duration-200">
                <span className="font-medium">Count:</span> {cacheStatus?.highHitRate?.count || 0}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
                <span className="font-medium">Updated:</span> {formatTimeAgo(cacheStatus?.highHitRate?.lastUpdated)}
              </div>
              {cacheStatus?.highHitRate?.date && (
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1 transition-colors duration-200">
                  Date: {cacheStatus.highHitRate.date}
                </div>
              )}
            </div>

            {/* Best Bets Cache */}
            <div className={`p-2 rounded-lg border-2 transition-colors duration-200 ${cacheStatus?.bestBets?.cached ? 'border-blue-200 dark:border-blue-700/50 bg-blue-50/50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-slate-600 bg-gray-50/50 dark:bg-slate-700/50'}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Best Bets Scan</div>
                {cacheStatus?.bestBets?.cached ? (
                  <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full font-medium transition-colors duration-200">Cached</span>
                ) : (
                  <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-full font-medium transition-colors duration-200">None</span>
                )}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 transition-colors duration-200">
                <span className="font-medium">Count:</span> {cacheStatus?.bestBets?.count || 0}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
                <span className="font-medium">Updated:</span> {formatTimeAgo(cacheStatus?.bestBets?.lastUpdated)}
              </div>
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

      {/* Data Refresh Controls & Scanning Controls - Side by Side */}
      <div className="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-2">
        {/* Data Refresh Controls */}
        <div className="rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
          <div className="mb-2">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Data Refresh</h2>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Refresh cached services</p>
          </div>

          <div className="grid grid-cols-1 gap-1.5">
          <button
            onClick={() => refreshDailyPropsMutation.mutate()}
            disabled={refreshDailyPropsMutation.isPending}
            className="px-3 py-2 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 text-xs font-semibold rounded-lg disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
          >
            {refreshDailyPropsMutation.isPending ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Refreshing...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Refresh Daily Props</span>
              </>
            )}
          </button>

          <button
            onClick={() => refreshHighHitRateMutation.mutate()}
            disabled={refreshHighHitRateMutation.isPending}
            className="px-3 py-2 bg-green-100 dark:bg-green-900/30 hover:bg-green-200 dark:hover:bg-green-900/50 text-green-900 dark:text-green-300 text-xs font-semibold rounded-lg disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 border border-green-300 dark:border-green-700 transition-colors duration-200"
          >
            {refreshHighHitRateMutation.isPending ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Refreshing...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Refresh High Hit Rate</span>
              </>
            )}
          </button>

          <button
            onClick={() => refreshAllMutation.mutate()}
            disabled={refreshAllMutation.isPending || refreshDailyPropsMutation.isPending || refreshHighHitRateMutation.isPending}
            className="px-3 py-2 bg-purple-100 dark:bg-purple-900/30 hover:bg-purple-200 dark:hover:bg-purple-900/50 text-purple-900 dark:text-purple-300 text-xs font-semibold rounded-lg disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 border border-purple-300 dark:border-purple-700 transition-colors duration-200"
          >
            {refreshAllMutation.isPending ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Refreshing All...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Refresh All Services</span>
              </>
            )}
          </button>
        </div>

        {/* Success/Error Messages */}
        {(refreshDailyPropsMutation.isSuccess || refreshHighHitRateMutation.isSuccess || refreshAllMutation.isSuccess) && (
          <div className="mt-2 p-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs text-emerald-800 dark:text-emerald-300 transition-colors duration-200">
            {refreshAllMutation.isSuccess && 'All services refreshed successfully! '}
            {refreshDailyPropsMutation.isSuccess && !refreshAllMutation.isSuccess && 'Daily props refreshed successfully! '}
            {refreshHighHitRateMutation.isSuccess && !refreshAllMutation.isSuccess && 'High hit rate bets refreshed successfully! '}
            Cache updated and ready for use.
          </div>
        )}

        {(refreshDailyPropsMutation.isError || refreshHighHitRateMutation.isError || refreshAllMutation.isError) && (
          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-800 dark:text-red-300 transition-colors duration-200">
            Error: {refreshAllMutation.error?.message || refreshDailyPropsMutation.error?.message || refreshHighHitRateMutation.error?.message}
          </div>
        )}

          {/* Advanced Controls Toggle */}
          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 flex items-center gap-1 transition-colors duration-200"
            >
              <svg className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              {showAdvanced ? 'Hide' : 'Show'} Advanced
            </button>
          </div>

          {/* Advanced Controls */}
          {showAdvanced && (
            <div className="mt-2 space-y-1.5">
            {/* Custom Refresh Parameters */}
            <div className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600 transition-colors duration-200">
              <h3 className="text-xs font-semibold text-gray-900 dark:text-slate-100 mb-3 transition-colors duration-200">Custom Refresh Parameters</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {/* Daily Props Custom */}
                <div className="space-y-2">
                  <div className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-200">Daily Props</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[10px] text-gray-600 dark:text-gray-400 mb-0.5 transition-colors duration-200">Min Confidence</label>
                      <input
                        type="number"
                        value={dailyPropsParams.minConfidence}
                        onChange={(e) => setDailyPropsParams({ ...dailyPropsParams, minConfidence: Number(e.target.value) })}
                        className="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
                        min="0"
                        max="100"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-gray-600 dark:text-gray-400 mb-0.5 transition-colors duration-200">Limit</label>
                      <input
                        type="number"
                        value={dailyPropsParams.limit}
                        onChange={(e) => setDailyPropsParams({ ...dailyPropsParams, limit: Number(e.target.value) })}
                        className="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
                        min="1"
                        max="200"
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => refreshDailyPropsCustomMutation.mutate(dailyPropsParams)}
                    disabled={refreshDailyPropsCustomMutation.isPending}
                    className="w-full px-3 py-1.5 text-xs bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 rounded disabled:opacity-50 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
                  >
                    {refreshDailyPropsCustomMutation.isPending ? 'Refreshing...' : 'Refresh with Custom Params'}
                  </button>
                </div>

                {/* High Hit Rate Custom */}
                <div className="space-y-2">
                  <div className="text-xs font-medium text-gray-700 dark:text-gray-300 transition-colors duration-200">High Hit Rate</div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="block text-[10px] text-gray-600 dark:text-gray-400 mb-0.5 transition-colors duration-200">Min Hit Rate</label>
                      <input
                        type="number"
                        step="0.05"
                        value={highHitRateParams.minHitRate}
                        onChange={(e) => setHighHitRateParams({ ...highHitRateParams, minHitRate: Number(e.target.value) })}
                        className="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
                        min="0"
                        max="1"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-gray-600 dark:text-gray-400 mb-0.5 transition-colors duration-200">Limit</label>
                      <input
                        type="number"
                        value={highHitRateParams.limit}
                        onChange={(e) => setHighHitRateParams({ ...highHitRateParams, limit: Number(e.target.value) })}
                        className="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
                        min="1"
                        max="50"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-gray-600 dark:text-gray-400 mb-0.5 transition-colors duration-200">Last N</label>
                      <input
                        type="number"
                        value={highHitRateParams.lastN}
                        onChange={(e) => setHighHitRateParams({ ...highHitRateParams, lastN: Number(e.target.value) })}
                        className="w-full px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
                        min="5"
                        max="20"
                      />
                    </div>
                  </div>
                  <button
                    onClick={() => refreshHighHitRateCustomMutation.mutate(highHitRateParams)}
                    disabled={refreshHighHitRateCustomMutation.isPending}
                    className="w-full px-3 py-1.5 text-xs bg-green-100 dark:bg-green-900/30 hover:bg-green-200 dark:hover:bg-green-900/50 text-green-900 dark:text-green-300 rounded disabled:opacity-50 border border-green-300 dark:border-green-700 transition-colors duration-200"
                  >
                    {refreshHighHitRateCustomMutation.isPending ? 'Refreshing...' : 'Refresh with Custom Params'}
                  </button>
                </div>
              </div>
            </div>

            {/* Cache Management */}
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border-2 border-red-200 dark:border-red-800 transition-colors duration-200">
              <h3 className="text-xs font-semibold text-red-900 dark:text-red-300 mb-3 transition-colors duration-200">⚠️ Cache Management</h3>
              <p className="text-xs text-red-700 dark:text-red-400 mb-3 transition-colors duration-200">Clear caches to force fresh data on next request. Use with caution.</p>
              
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                <button
                  onClick={() => clearDailyPropsCacheMutation.mutate()}
                  disabled={clearDailyPropsCacheMutation.isPending}
                  className="px-3 py-2 text-xs bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-900 dark:text-red-300 rounded disabled:opacity-50 border border-red-300 dark:border-red-700 transition-colors duration-200"
                >
                  Clear Daily Props
                </button>
                <button
                  onClick={() => clearHighHitRateCacheMutation.mutate()}
                  disabled={clearHighHitRateCacheMutation.isPending}
                  className="px-3 py-2 text-xs bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-900 dark:text-red-300 rounded disabled:opacity-50 border border-red-300 dark:border-red-700 transition-colors duration-200"
                >
                  Clear High Hit Rate
                </button>
                <button
                  onClick={() => clearBestBetsCacheMutation.mutate()}
                  disabled={clearBestBetsCacheMutation.isPending}
                  className="px-3 py-2 text-xs bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-900 dark:text-red-300 rounded disabled:opacity-50 border border-red-300 dark:border-red-700 transition-colors duration-200"
                >
                  Clear Best Bets
                </button>
                <button
                  onClick={() => clearTeamsCacheMutation.mutate()}
                  disabled={clearTeamsCacheMutation.isPending}
                  className="px-3 py-2 text-xs bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 rounded disabled:opacity-50 border border-blue-300 dark:border-blue-700 transition-colors duration-200"
                >
                  Clear Teams Cache
                </button>
                <button
                  onClick={() => {
                    if (confirm('Are you sure you want to clear ALL caches? This will force fresh data on next request.')) {
                      clearAllCacheMutation.mutate()
                    }
                  }}
                  disabled={clearAllCacheMutation.isPending}
                  className="px-3 py-2 text-xs bg-red-200 dark:bg-red-900/40 hover:bg-red-300 dark:hover:bg-red-900/60 text-red-900 dark:text-red-200 rounded font-bold disabled:opacity-50 border-2 border-red-400 dark:border-red-700 transition-colors duration-200"
                >
                  Clear All Caches
                </button>
              </div>

              {(clearAllCacheMutation.isSuccess || clearDailyPropsCacheMutation.isSuccess || clearHighHitRateCacheMutation.isSuccess || clearBestBetsCacheMutation.isSuccess || clearTeamsCacheMutation.isSuccess) && (
                <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-800 rounded text-xs text-red-800 dark:text-red-300 transition-colors duration-200">
                  Cache cleared successfully. Next request will fetch fresh data.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Scanning Controls */}
      <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 p-3 transition-colors duration-200">
          <div className="mb-2">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Prop Scanner</h2>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 transition-colors duration-200">Scan games for best bets</p>
          </div>
          {scanStatus?.lastScan && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 transition-colors duration-200">
              Last: {new Date(scanStatus.lastScan).toLocaleTimeString()}
              {scanStatus?.todayGames !== undefined && ` • ${scanStatus.todayGames} games`}
            </div>
          )}

          <div className="grid grid-cols-1 gap-1.5 mb-2">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 transition-colors duration-200">Season</label>
            <input
              value={scanParams.season}
              onChange={(e) => setScanParams({ ...scanParams, season: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-600/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
              placeholder="2025-26"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 transition-colors duration-200">Min Confidence (%)</label>
            <input
              type="number"
              value={scanParams.minConfidence}
              onChange={(e) => setScanParams({ ...scanParams, minConfidence: Number(e.target.value) })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-600/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
              min="0"
              max="100"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 transition-colors duration-200">Limit</label>
            <input
              type="number"
              value={scanParams.limit}
              onChange={(e) => setScanParams({ ...scanParams, limit: Number(e.target.value) })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-600/20 dark:focus:ring-blue-400/20 transition-colors duration-200"
              min="1"
              max="100"
            />
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={() => scanMutation.mutate(scanParams)}
              disabled={scanMutation.isPending}
              className="flex-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-900 dark:text-blue-300 text-xs font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed border border-blue-300 dark:border-blue-700 transition-colors duration-200"
            >
              {scanMutation.isPending ? 'Scanning...' : 'Start Scan'}
            </button>
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-slate-100 text-xs font-medium rounded-lg disabled:opacity-50 border border-gray-300 dark:border-slate-600 transition-colors duration-200"
            >
              {syncMutation.isPending ? 'Syncing...' : 'Sync Players'}
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

          {scanMutation.isError && (
            <div className="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-xs text-red-800 dark:text-red-300 transition-colors duration-200">
              Error: {String(scanMutation.error)}
            </div>
          )}

          {scanMutation.isSuccess && (
            <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs text-emerald-800 dark:text-emerald-300 transition-colors duration-200">
              Found {scanMutation.data?.count || 0} best bets
            </div>
          )}
        </div>
      </div>

      {/* Best Bets Results */}
      <div className="mt-2 rounded-lg bg-white dark:bg-slate-800 shadow-sm ring-1 ring-gray-100 dark:ring-slate-700 transition-colors duration-200">
        <div className="px-3 py-2 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between transition-colors duration-200">
          <div>
            <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Best Prop Bets</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
              Top suggestions from last scan
              {bestBetsData?.lastScanned && (
                <span className="ml-2">• Scanned: {formatTimeAgo(bestBetsData.lastScanned)}</span>
              )}
            </div>
          </div>
          <button
            onClick={() => {
              addActivityLog('info', 'Refreshing best bets...')
              refetchBestBets()
            }}
            disabled={bestBetsLoading}
            className="px-3 py-1.5 rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-xs font-medium text-gray-900 dark:text-slate-100 hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors duration-200"
          >
            {bestBetsLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        {bestBetsLoading && (
          <div className="flex items-center justify-center py-4">
            <svg className="animate-spin h-4 w-4 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="ml-2 text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">Loading best bets...</span>
          </div>
        )}
        {bestBetsError && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg m-3 text-xs text-red-800 dark:text-red-300 transition-colors duration-200">
            Error loading best bets: {String(bestBetsError)}
          </div>
        )}
        {!bestBetsLoading && !bestBetsError && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
            <thead className="bg-gray-50 dark:bg-slate-700 transition-colors duration-200">
              <tr>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Player</th>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Prop</th>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Line</th>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Confidence</th>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Hit Rate</th>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Trend</th>
                <th className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 transition-colors duration-200">Recent Avg</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700 transition-colors duration-200">
              {bestBets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-4 text-center text-gray-500 dark:text-gray-400 transition-colors duration-200">
                    No best bets found. Run a scan to generate suggestions.
                  </td>
                </tr>
              ) : (
                bestBets.slice(0, 30).map((bet: any, idx: number) => (
                  <tr key={idx} className={`transition-colors duration-200 ${idx % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-gray-50 dark:bg-slate-700/50'}`}>
                    <td className="px-3 py-1.5">
                      <a href={`/player/${bet.playerId}`} className="text-blue-600 dark:text-blue-400 hover:underline font-medium transition-colors duration-200">
                        {bet.playerName}
                      </a>
                    </td>
                    <td className="px-3 py-1.5 text-gray-900 dark:text-slate-100 transition-colors duration-200">{bet.type}</td>
                    <td className="px-3 py-1.5 text-gray-900 dark:text-slate-100 transition-colors duration-200">
                      {bet.suggestion === 'over' ? 'OVER' : 'UNDER'} {bet.marketLine}
                    </td>
                    <td className="px-3 py-1.5">
                      <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-medium transition-colors duration-200 ${
                        bet.confidence >= 80 ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' :
                        bet.confidence >= 70 ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' :
                        'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                      }`}>
                        {bet.confidence}%
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-gray-600 dark:text-gray-400 transition-colors duration-200">{bet.hitRate}%</td>
                    <td className="px-3 py-1.5">
                      {bet.trend === 'up' ? '📈' : bet.trend === 'down' ? '📉' : '➡️'}
                    </td>
                    <td className="px-3 py-1.5 text-gray-600 dark:text-gray-400 transition-colors duration-200">{bet.recentAvg}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        )}
      </div>
    </div>
  )
}
