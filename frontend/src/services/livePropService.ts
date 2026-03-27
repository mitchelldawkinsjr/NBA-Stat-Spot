import { apiGet } from '../utils/api'
import type { LivePropsDashboardResponse } from '../types/liveProps'

const BASE = 'api/v1/live-props'

export async function fetchLivePropsDashboard(params: {
  gameId?: string | null
  season?: string
  /** When false, skips ESPN box on the server (faster; live stats stay 0 in-game). */
  liveBox?: boolean
  /** Bypass 25s server response cache. */
  skipCache?: boolean
}): Promise<LivePropsDashboardResponse> {
  const sp = new URLSearchParams()
  if (params.gameId) sp.set('game_id', params.gameId)
  if (params.season) sp.set('season', params.season)
  if (params.liveBox === false) sp.set('live_box', 'false')
  if (params.skipCache) sp.set('skip_cache', 'true')
  const q = sp.toString()
  return apiGet<LivePropsDashboardResponse>(`${BASE}/dashboard${q ? `?${q}` : ''}`)
}
