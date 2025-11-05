export interface Player {
  id: string | number
  name: string
  team?: string
  number?: string
  position?: string
}

export interface GameStats {
  gameId: string
  date: string
  opponent?: string
  points: number
  assists: number
  rebounds: number
  threesMade: number
  pra?: number
}

export interface StatSplit {
  category: string
  games: number
  points: number
  assists: number
  rebounds: number
  threesMade: number
  pra: number
}

export interface OddsEntry {
  sportsbook: string
  propType: string
  line: number
  overOdds: string
  underOdds: string
  lastUpdated: string
}

export type PropTypeKey = 'PTS' | 'REB' | 'AST' | '3PM' | 'PRA'


