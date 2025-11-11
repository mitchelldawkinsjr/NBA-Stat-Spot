/**
 * Centralized TypeScript type definitions for all API responses
 * These types match the backend Pydantic models and API responses
 */

// Common response wrappers
export interface ApiResponse<T> {
  items?: T[]
  [key: string]: unknown
}

export interface ApiError {
  detail?: string
  message?: string
  error?: string
}

// Player types
export interface Player {
  id: number
  name: string
  full_name?: string
  team?: number
  team_id?: number
  position?: string
  jersey_number?: string
  first_name?: string
  last_name?: string
}

export interface PlayerSearchResponse {
  items: Player[]
}

export interface PlayerStatsResponse {
  items: GameLog[]
}

export interface GameLog {
  game_id: string
  game_date: string
  matchup: string
  pts: number
  reb: number
  ast: number
  tpm: number
  minutes?: number
  pra?: number
  [key: string]: unknown
}

export interface StatLeader {
  playerId: number
  playerName: string
  value: number
}

export interface StatLeadersResponse {
  items: {
    PTS: StatLeader[]
    AST: StatLeader[]
    REB: StatLeader[]
    '3PM': StatLeader[]
  }
}

// Team types
export interface Team {
  id: number
  full_name: string
  abbreviation: string
  city: string
  nickname: string
  conference?: string
  division?: string
}

export interface TeamsResponse {
  items: Team[]
}

export interface TeamResponse {
  team: Team
  roster: Player[]
  roster_count: number
}

export interface TeamPlayersResponse {
  items: Player[]
  team_id: number
  total: number
  debug?: {
    total_players: number
    players_with_team_id: number
    requested_team_id: number
    normalized_team_id: number | null
  }
}

// Prop suggestion types
export type PropType = 'PTS' | 'REB' | 'AST' | '3PM' | 'PRA'
export type Direction = 'over' | 'under'
export type BetResult = 'pending' | 'won' | 'lost' | 'push' | 'void'

export interface PropSuggestion {
  type: PropType
  marketLine?: number
  fairLine?: number
  direction?: Direction
  confidence?: number
  suggestion?: Direction
  hitRate?: number
  hitRateOver?: number
  hitRateUnder?: number
  mlConfidence?: number
  mlPredictedLine?: number
  confidenceSource?: string
  rationale?: string[]
  rationaleSource?: string
  [key: string]: unknown
}

export interface PropSuggestionsResponse {
  suggestions: PropSuggestion[]
  error?: string
  deprecated?: boolean
  message?: string
  loading?: boolean
}

export interface DailyProp {
  playerId: number
  playerName: string
  suggestions: PropSuggestion[]
  [key: string]: unknown
}

export interface DailyPropsResponse {
  items: DailyProp[]
}

// Bet types
export interface Bet {
  id: number
  player_id: number
  player_name: string
  prop_type: PropType
  line_value: number
  direction: Direction
  game_date: string
  system_confidence?: number | null
  system_fair_line?: number | null
  system_suggestion?: string | null
  amount?: number | null
  odds?: string | null
  notes?: string | null
  result: BetResult
  actual_value?: number | null
  payout?: number | null
  created_at: string
  updated_at: string
  settled_at?: string | null
}

export interface BetsResponse {
  items: Bet[]
}

export interface BetStats {
  overall: {
    total: number
    won: number
    lost: number
    push: number
    win_rate: number
  }
  system_accuracy: {
    total: number
    won: number
    win_rate: number
  }
  by_prop_type: Record<PropType, {
    total: number
    won: number
    win_rate: number
  }>
  by_confidence: {
    high: { total: number; won: number; win_rate: number }
    medium: { total: number; won: number; win_rate: number }
    low: { total: number; won: number; win_rate: number }
  }
  pending: number
}

// Parlay types
export interface ParlayLeg {
  id: number
  parlay_id: number
  player_id: number
  player_name: string
  prop_type: PropType
  line_value: number
  direction: Direction
  system_confidence?: number | null
  system_fair_line?: number | null
  system_suggestion?: string | null
  system_hit_rate?: number | null
  result: BetResult
  actual_value?: number | null
  created_at: string
}

export interface Parlay {
  id: number
  name?: string | null
  game_date: string
  total_amount?: number | null
  total_odds?: string | null
  total_payout?: number | null
  system_confidence?: number | null
  leg_count: number
  result: BetResult
  notes?: string | null
  created_at: string
  updated_at: string
  settled_at?: string | null
  legs?: ParlayLeg[]
}

export interface ParlaysResponse {
  items: Parlay[]
}

// Game types
export interface Game {
  gameId?: string
  home?: string
  away?: string
  gameTimeUTC?: string
  [key: string]: unknown
}

export interface GamesResponse {
  games: Game[]
}

// Filter types
export interface Filters {
  season?: string
  lastN?: number
  home?: 'any' | 'home' | 'away'
  marketLines?: Record<PropType, string>
  direction?: Direction
}

// Component prop types
export interface PlayerSearchProps {
  onSelect: (player: Player) => void
}

export interface FiltersPanelProps {
  value: Filters
  onChange: (filters: Filters) => void
  player?: Player | null
  onEvaluate?: (result: PropSuggestionsResponse) => void
}

export interface EnhancedSuggestProps {
  player: Player | null
  result?: PropSuggestionsResponse
}

