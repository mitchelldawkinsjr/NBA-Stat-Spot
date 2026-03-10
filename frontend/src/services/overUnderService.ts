/**
 * Over/Under Analysis API Service
 * Handles API calls for live game over/under analysis
 */

import { apiGet } from '../utils/api'
import type {
  LiveGamesResponse,
  AnalyzeGameResponse,
  AnalyzeAllGamesResponse,
} from '../types/overUnder'

const BASE_PATH = 'api/v1/over-under'

/**
 * Get all live games happening today
 */
export async function getLiveGames(): Promise<LiveGamesResponse> {
  return apiGet<LiveGamesResponse>(`${BASE_PATH}/live-games`)
}

/**
 * Analyze a specific game for over/under opportunities
 * @param gameId - Game ID to analyze
 * @param liveLine - Optional current betting line
 * use_ai=true so backend applies admin AI setting (ML/LLM when enabled)
 */
export async function analyzeGame(
  gameId: string,
  liveLine?: number
): Promise<AnalyzeGameResponse> {
  const search = new URLSearchParams()
  if (liveLine !== undefined) search.set('live_line', String(liveLine))
  search.set('use_ai', 'true')
  const params = search.toString()
  return apiGet<AnalyzeGameResponse>(`${BASE_PATH}/analyze/${gameId}${params ? `?${params}` : ''}`)
}

/**
 * Analyze all live games for over/under opportunities.
 * use_ai=true so backend applies admin AI setting when enabled.
 */
export async function analyzeAllGames(): Promise<AnalyzeAllGamesResponse> {
  return apiGet<AnalyzeAllGamesResponse>(`${BASE_PATH}/analyze-all?use_ai=true`)
}

