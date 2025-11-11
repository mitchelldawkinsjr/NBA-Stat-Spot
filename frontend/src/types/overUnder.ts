/**
 * TypeScript types for Over/Under Analysis API
 */

export interface LiveGame {
  game_id: string
  home_team: string
  away_team: string
  home_score: number
  away_score: number
  quarter: number
  time_remaining: string
  is_final: boolean
  current_total: number
}

export interface OverUnderAnalysis {
  game_id: string
  current_total: number
  projected_total: number
  live_line: number | null
  current_pace: number
  expected_pace: number
  pace_differential: number
  quarter: number
  time_remaining_minutes: number
  recommendation: "OVER" | "UNDER" | "NO BET"
  confidence: "HIGH" | "MEDIUM" | "LOW" | "N/A"
  edge_percentage: number
  key_factors: string[]
  reasoning: string
}

export interface GameAnalysisResult {
  game_id: string
  game: {
    home_team: string
    away_team: string
    home_score: number
    away_score: number
    quarter: number
    time_remaining: string
    is_final: boolean
  }
  analysis: OverUnderAnalysis
}

export interface LiveGamesResponse {
  games: LiveGame[]
}

export interface AnalyzeGameResponse {
  game_id: string
  game: {
    home_team: string
    away_team: string
    home_score: number
    away_score: number
    quarter: number
    time_remaining: string
    is_final: boolean
  }
  analysis: OverUnderAnalysis
}

export interface AnalyzeAllGamesResponse {
  games: GameAnalysisResult[]
}

