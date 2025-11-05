import { createContext, useContext, useMemo, useState } from 'react'

type SeasonContextType = {
  season: string
  setSeason: (s: string) => void
}

const Ctx = createContext<SeasonContextType | undefined>(undefined)

export function SeasonProvider({ children }: { children: any }) {
  const [season, setSeason] = useState<string>('2025-26')
  const value = useMemo(() => ({ season, setSeason }), [season])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useSeason() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useSeason must be used within SeasonProvider')
  return ctx
}


