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
 */
export async function analyzeGame(
  gameId: string,
  liveLine?: number
): Promise<AnalyzeGameResponse> {
  const params = liveLine !== undefined ? `?live_line=${liveLine}` : ''
  return apiGet<AnalyzeGameResponse>(`${BASE_PATH}/analyze/${gameId}${params}`)
}

/**
 * Analyze all live games for over/under opportunities
 */
export async function analyzeAllGames(): Promise<AnalyzeAllGamesResponse> {
  return apiGet<AnalyzeAllGamesResponse>(`${BASE_PATH}/analyze-all`)
}

