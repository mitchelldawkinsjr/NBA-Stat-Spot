import { createContext, useCallback, useContext, useMemo, useState } from 'react'

/** NBA season strings like 2025-26 */
export const SEASON_PATTERN = /^\d{4}-\d{2}$/

type SeasonContextType = {
  season: string
  setSeason: (s: string) => void
}

const Ctx = createContext<SeasonContextType | undefined>(undefined)

export function SeasonProvider({ children }: { children: any }) {
  const [season, setSeasonState] = useState<string>('2025-26')
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
