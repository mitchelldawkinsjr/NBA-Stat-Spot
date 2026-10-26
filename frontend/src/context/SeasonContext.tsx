import { createContext, useCallback, useContext, useMemo, useState } from 'react'

/** NBA season strings like 2026-27. Season flips on October 1, matching the API. */
export const SEASON_PATTERN = /^\d{4}-\d{2}$/

export function currentNbaSeason(now = new Date()): string {
  const month = now.getMonth() + 1
  const year = now.getFullYear()
  const start = month >= 10 ? year : year - 1
  const end = String((start + 1) % 100).padStart(2, '0')
  return `${start}-${end}`
}

type SeasonContextType = {
  season: string
  setSeason: (s: string) => void
}

const Ctx = createContext<SeasonContextType | undefined>(undefined)

export function SeasonProvider({ children }: { children: any }) {
  const [season, setSeasonState] = useState<string>(() => currentNbaSeason())
  const setSeason = useCallback((s: string) => {
    const next = (s || '').trim()
    // Ignore partial edits (e.g. "2025-2") so queries don't fire mid-typing
    if (!SEASON_PATTERN.test(next)) return
    setSeasonState(next)
  }, [])
  const value = useMemo(() => ({ season, setSeason }), [season, setSeason])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSeason() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useSeason must be used within SeasonProvider')
  return ctx
}
