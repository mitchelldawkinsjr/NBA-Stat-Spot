export type HitPeriod = 'L5' | 'L10' | 'L20'

export interface TrendSlice {
  hit_rate_percentage: number
  hits: number
  total: number
  results: boolean[]
}

export interface LivePropTrend {
  L5: TrendSlice
  L10: TrendSlice
  L20: TrendSlice
}

export interface LivePropProgression {
  current: number
  pace: number
  completion_pct: number
}

export interface LivePropRowDetail {
  prop_type: string
  stat_key: string
  line: number
  suggestion: string
  confidence: number
  odds_over: string
  odds_under: string
  progression: LivePropProgression
  trend: LivePropTrend
  rationale_summary: string
}

export interface LivePropsPlayerRow {
  player_id: number
  name: string
  team: string
  position: string
  rotation_tier?: boolean
  headshot_url: string
  live_stats: { pts: number; reb: number; ast: number }
  props: LivePropRowDetail[]
}

export interface LivePropsGameSummary {
  game_id: string
  home_team: string
  away_team: string
  home_score: number
  away_score: number
  quarter: number
  time_remaining: string
  is_final: boolean
  is_live: boolean
  current_total: number
}

export interface LivePropsConfidenceCard {
  tier: string
  label: string
  confidence_pct: number
  player_id: number
  rationale: string
  trend_L5_hit: number
}

export interface LivePropsMarketSentiment {
  bars: number[]
  headline_team: string
  spread_note: string
}

export interface LivePropsDashboardResponse {
  games: LivePropsGameSummary[]
  selected_game_id: string | null
  home_team?: string
  away_team?: string
  players: LivePropsPlayerRow[]
  confidence: LivePropsConfidenceCard[]
  market_sentiment: LivePropsMarketSentiment | null
  error?: string
  /** Backend included ESPN box in this payload */
  live_box_applied?: boolean
}
