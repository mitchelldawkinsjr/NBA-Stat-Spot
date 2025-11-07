import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'
import { useMutation } from '@tanstack/react-query'
import { SuggestionCards } from '../components/SuggestionCards'
import { PropCard } from '../components/PropCard'
import { calculateConfidenceBasic } from '../utils/confidence'
import { TrendChart } from '../components/TrendChart'
import { SplitsTable } from '../components/SplitsTable'
import { MatchupCard } from '../components/MatchupCard'
// import { PropHistoryRow } from '../components/PropHistory'
import { OddsCard } from '../components/OddsCard'
import { DataTable } from '../components/ui/DataTable'
import type { DataTableColumn } from '../components/ui/DataTable'
import { pearsonCorrelation } from '../utils/correlation'

type GameLog = {
  game_id: string
  game_date: string
  matchup: string
  pts: number
  reb: number
  ast: number
  tpm: number
}

export default function PlayerProfile() {
  const { id } = useParams()
  const { season } = useSeason()
  const [logs, setLogs] = useState<GameLog[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [fallbackUsed, setFallbackUsed] = useState<string | null>(null)
  const [playerName, setPlayerName] = useState<string>('')
  const [teamId, setTeamId] = useState<number | null>(null)
  const [teamName, setTeamName] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
        // Fetch player detail for display name and team
        try {
          const rName = await fetch(`/api/v1/players/${id}`)
          if (rName.ok) {
            const j = await rName.json()
            if (j?.player?.name) setPlayerName(String(j.player.name))
            if (j?.player?.team_id) setTeamId(Number(j.player.team_id))
            if (j?.player?.team_name) setTeamName(String(j.player.team_name))
          }
        } catch { /* ignore name fetch failure */ }
        const res = await fetch(`/api/v1/players/${id}/stats?games=20&season=${encodeURIComponent(season)}`)
        if (!res.ok) throw new Error('Failed to load stats')
        const data = await res.json()
        const base: GameLog[] = (data.items || []).map((g: any) => ({
          game_id: String(g.game_id || g.gameId || g.Game_ID || ''),
          game_date: String(g.game_date || g.gameDate || g.GAME_DATE || ''),
          matchup: String(g.matchup || g.MATCHUP || ''),
          pts: Number(g.pts ?? g.PTS ?? 0),
          reb: Number(g.reb ?? g.REB ?? 0),
          ast: Number(g.ast ?? g.AST ?? 0),
          tpm: Number(g.tpm ?? g.FG3M ?? 0),
        }))
        if (base.length === 0 && season !== '2024-25') {
          // Fallback to prior season if current season has no logs
          const res2 = await fetch(`/api/v1/players/${id}/stats?games=20&season=${encodeURIComponent('2024-25')}`)
          if (res2.ok) {
            const d2 = await res2.json()
            const base2: GameLog[] = (d2.items || []).map((g: any) => ({
              game_id: String(g.game_id || g.gameId || g.Game_ID || ''),
              game_date: String(g.game_date || g.gameDate || g.GAME_DATE || ''),
              matchup: String(g.matchup || g.MATCHUP || ''),
              pts: Number(g.pts ?? g.PTS ?? 0),
              reb: Number(g.reb ?? g.REB ?? 0),
              ast: Number(g.ast ?? g.AST ?? 0),
              tpm: Number(g.tpm ?? g.FG3M ?? 0),
            }))
            setLogs(base2)
            if (base2.length > 0) setFallbackUsed('2024-25')
            else setLogs(base)
          } else {
            setLogs(base)
          }
        } else {
          setLogs(base)
        }
      } catch (e: any) {
        setError(e?.message || 'Error')
      } finally {
        setLoading(false)
      }
    })()
  }, [id, season])

  const sortedLogs = useMemo(() => {
    // API returns latest-first; normalize to oldest-first for charts
    return logs.slice().reverse()
  }, [logs])

  function avg(xs: number[]) {
    return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
  }

  const enrichedLogs = useMemo(() => sortedLogs.map(g => ({ ...g, pra: g.pts + g.reb + g.ast })), [sortedLogs])

  const [windowN, setWindowN] = useState<number>(10)
  const recentN = useMemo(() => enrichedLogs.slice(-windowN), [enrichedLogs, windowN])

  const seasonAverages = useMemo(() => ({
    pts: avg(enrichedLogs.map(g => g.pts)),
    reb: avg(enrichedLogs.map(g => g.reb)),
    ast: avg(enrichedLogs.map(g => g.ast)),
    tpm: avg(enrichedLogs.map(g => g.tpm)),
    pra: avg(enrichedLogs.map(g => g.pra as number)),
  }), [enrichedLogs])

  // Header trend badge
  const headerTrend = useMemo(() => {
    const ptsRecent = avg(recentN.map(g => g.pts))
    const delta = ptsRecent - seasonAverages.pts
    const tag = delta > 0.8 ? 'HOT' : delta < -0.8 ? 'COLD' : 'NEUTRAL'
    const color = tag === 'HOT' ? 'bg-green-50 text-green-700 ring-green-600/20' : tag === 'COLD' ? 'bg-red-50 text-red-700 ring-red-600/20' : 'bg-gray-50 text-gray-700 ring-gray-600/20'
    return { tag, delta, color }
  }, [recentN, seasonAverages])

  

  // Keep last N slices for quick calculations if needed
  // (Replaced by windowN controls in charts/tiles)
  // const last5 = useMemo(() => enrichedLogs.slice(-5), [enrichedLogs])
  // const last10 = useMemo(() => enrichedLogs.slice(-10), [enrichedLogs])

  const chartData = useMemo(() => enrichedLogs.slice(-10).map((g, i) => ({
    idx: i + 1,
    date: g.game_date,
    matchup: g.matchup,
    PTS: g.pts,
    REB: g.reb,
    AST: g.ast,
    TPM: g.tpm,
    PRA: (g.pra as number),
  })), [enrichedLogs])

  // Venue logs if needed later
  // const homeLogs = useMemo(() => enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('vs')), [enrichedLogs])
  // const awayLogs = useMemo(() => enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('@')), [enrichedLogs])

  // hitRate helper removed to reduce redundancy

  const [hrStat, setHrStat] = useState<'PTS'|'REB'|'AST'|'3PM'|'PRA'>('PTS')
  const [hrLine, setHrLine] = useState<string>('')
  const [hrDir, setHrDir] = useState<'over'|'under'>('over')
  // map removed usage in UI after cleanup
  // Hit rate metrics (unused in UI after cleanup)

  // Evaluate the entered line using backend suggestion engine
  const apiKeyMap: Record<'PTS'|'REB'|'AST'|'3PM'|'PRA', 'pts'|'reb'|'ast'|'tpm'|'pra'> = { PTS: 'pts', REB: 'reb', AST: 'ast', '3PM': 'tpm', PRA: 'pra' }
  const [evalResult, setEvalResult] = useState<any>(null)
  const evalLine = useMutation({
    mutationFn: async () => {
      if (!id || !hrLine) return null
      const seasonToUse = (fallbackUsed || season || '2025-26') as string
      const body: any = {
        playerId: Number(id),
        season: seasonToUse,
        lastN: windowN,
        marketLines: { [apiKeyMap[hrStat]]: Number(hrLine) },
      }
      const res = await fetch('/api/v1/props/player', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      return res.json()
    },
    onSuccess: (data) => setEvalResult(data)
  })

  // Section visibility toggles
  const [showHistorical, setShowHistorical] = useState<boolean>(true)
  const [showOpponent, setShowOpponent] = useState<boolean>(true)
  
  // Custom line values for Historical Prop Performance table
  const [histLines, setHistLines] = useState<Record<'PTS'|'AST'|'REB'|'3PM'|'PRA', number | null>>({
    PTS: null,
    AST: null,
    REB: null,
    '3PM': null,
    PRA: null
  })
  
  // Direction for each stat in Historical Prop Performance
  const [histDirs, setHistDirs] = useState<Record<'PTS'|'AST'|'REB'|'3PM'|'PRA', 'over'|'under'>>({
    PTS: 'over',
    AST: 'over',
    REB: 'over',
    '3PM': 'over',
    PRA: 'over'
  })
  
  // Last N games selector for Historical Prop Performance
  const [histLastN, setHistLastN] = useState<5 | 10>(5)

  const selectedSuggestion: any | null = useMemo(() => {
    const items = evalResult?.suggestions || []
    const match = items.find((s: any) => s.type === hrStat)
    if (!match) return null
    return { ...match, chosenDirection: hrDir }
  }, [evalResult, hrStat, hrDir])

  

  return (
    <div className="container mx-auto px-3 md:px-4 max-w-7xl">
      <a href="#player-profile-main" className="sr-only focus:not-sr-only">Skip to player content</a>

      {/* Breadcrumbs (TailGrids: Breadcrumbs) */}
      <nav className="relative z-10 mt-3" aria-label="Breadcrumb">
        <ol className="min-w-0 flex items-center gap-1 text-xs text-gray-500 overflow-hidden">
          <li>
            <a href="/" className="hover:text-gray-700">Home</a>
          </li>
          <li aria-hidden="true" className="px-1">/</li>
          <li>
            <a href="/explore" className="hover:text-gray-700">Players</a>
          </li>
          <li aria-hidden="true" className="px-1">/</li>
          <li className="flex-1 min-w-0 text-gray-700 font-medium truncate">{playerName || 'Player'}</li>
        </ol>
      </nav>

      {/* Header / Profile */}
      {/* Header / Profile (styled light for readability) */}
      <div className="relative overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-gray-200 mt-3">
        <div className="px-4 py-4 sm:px-6 sm:py-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-full bg-slate-100 ring-1 ring-gray-200 flex items-center justify-center text-lg font-semibold text-slate-800">
              {(playerName || 'P').slice(0,1)}
            </div>
            <div>
              <h2 id="player-profile-title" className="text-lg md:text-xl font-semibold tracking-tight text-slate-800">{playerName ? playerName : 'Player'} Profile</h2>
              <div className="mt-0.5 flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-700">Season: {fallbackUsed ? fallbackUsed : season}</span>
                {teamName && teamId && (
                  <>
                    <span className="text-xs text-slate-500">•</span>
                    <Link
                      to={`/team/${teamId}`}
                      className="text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline"
                    >
                      {teamName}
                    </Link>
                  </>
                )}
              </div>
              {/* Minimal season averages inline under name */}
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-800">PTS {seasonAverages.pts.toFixed(1)}</span>
                <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-800">REB {seasonAverages.reb.toFixed(1)}</span>
                <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-800">AST {seasonAverages.ast.toFixed(1)}</span>
                <span className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-800">3PM {seasonAverages.tpm.toFixed(1)}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset ${headerTrend.color}`}>
              {headerTrend.tag} {headerTrend.delta >= 0 ? '+' : ''}{headerTrend.delta.toFixed(1)} pts vs season
            </span>
            {fallbackUsed && (
              <span className="inline-flex items-center rounded-full bg-yellow-50 px-3 py-1 text-xs font-medium text-yellow-700 ring-1 ring-inset ring-yellow-200">Fallback to {fallbackUsed}</span>
            )}
          </div>
        </div>
      </div>
      
      
      {loading ? (
        <div className="mt-3 rounded-lg border border-gray-200 bg-white p-3 text-sm text-gray-700">Loading…</div>
      ) : error ? (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">Error: {error}</div>
      ) : (
        <div id="player-profile-main" role="main" aria-labelledby="player-profile-title" className="space-y-4">
          {/* Controls (TailGrids: Toolbar) */}
          <div className="mt-3 bg-white rounded-xl shadow-md ring-1 ring-gray-100 p-3 md:p-4 flex items-center gap-3 flex-wrap">
            <div className="text-xs font-semibold text-gray-600">Window</div>
            <select aria-label="Select window" value={windowN} onChange={(e) => setWindowN(Number(e.target.value))} className="px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20">
              {[5,10,20].map(n => <option key={n} value={n}>{n} games</option>)}
            </select>
            <div className="text-xs font-semibold text-gray-600 ml-1">Hit Rate</div>
            <select value={hrStat} onChange={(e) => setHrStat(e.target.value as 'PTS'|'REB'|'AST'|'3PM'|'PRA')} className="px-3 py-2 text-sm rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/20">
              {['PTS','REB','AST','3PM','PRA'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <input value={hrLine} onChange={(e) => setHrLine(e.target.value)} inputMode="decimal" placeholder="Line (e.g. 24.5)" className="px-3 py-2 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-600/20" />
            <div className="flex items-center gap-2">
              <button onClick={() => setHrDir('over')} aria-pressed={hrDir==='over'} aria-label="Select Over" className={`px-3 py-2 rounded-lg border text-sm font-medium shadow-sm ${hrDir==='over' ? 'bg-blue-700 text-white border-blue-700' : 'bg-white text-gray-900 border-gray-300'}`}>Over</button>
              <button onClick={() => setHrDir('under')} aria-pressed={hrDir==='under'} aria-label="Select Under" className={`px-3 py-2 rounded-lg border text-sm font-medium shadow-sm ${hrDir==='under' ? 'bg-blue-700 text-white border-blue-700' : 'bg-white text-gray-900 border-gray-300'}`}>Under</button>
            </div>
            <button onClick={() => evalLine.mutate()} aria-label="Evaluate line against recent performance" disabled={!hrLine || evalLine.isPending} className={`px-4 py-2 rounded-lg text-sm font-semibold ${(!hrLine || evalLine.isPending) ? 'opacity-70 cursor-not-allowed' : ''} bg-blue-600 hover:bg-blue-700 text-white shadow-sm`}>{evalLine.isPending ? 'Evaluating…' : 'Evaluate Line'}</button>
          </div>

          {/* Betting Recommendations */}
          {(() => {
            function roundHalf(x: number) { return Math.round(x * 2) / 2 }
            const stats = [
              { key: 'PTS', vals: enrichedLogs.map(g=>g.pts), season: seasonAverages.pts, color: 'text-blue-600 bg-blue-50', bar: 'bg-blue-600' },
              { key: 'AST', vals: enrichedLogs.map(g=>g.ast), season: seasonAverages.ast, color: 'text-amber-600 bg-amber-50', bar: 'bg-amber-500' },
              { key: 'REB', vals: enrichedLogs.map(g=>g.reb), season: seasonAverages.reb, color: 'text-emerald-600 bg-emerald-50', bar: 'bg-emerald-600' },
              { key: '3PM', vals: enrichedLogs.map(g=>g.tpm), season: seasonAverages.tpm, color: 'text-fuchsia-600 bg-fuchsia-50', bar: 'bg-fuchsia-600' },
              { key: 'PRA', vals: enrichedLogs.map(g=> (g.pra as number)), season: seasonAverages.pra, color: 'text-slate-600 bg-slate-50', bar: 'bg-slate-600' },
            ] as const
            const recs = stats.map(s => {
              const line = roundHalf(s.season)
              const recentVals = recentN.map(g => (
                s.key==='PTS'?g.pts : s.key==='AST'?g.ast : s.key==='REB'?g.reb : s.key==='3PM'?g.tpm : (g.pra as number)
              ))
              const recentAvg = recentVals.length ? recentVals.reduce((a,b)=>a+b,0)/recentVals.length : 0
              const delta = recentAvg - line
              const confidence = calculateConfidenceBasic(recentVals, line)
              const dir = delta >= 0 ? 'OVER' : 'UNDER'
              return { key: s.key, dir, line, confidence, recentAvg, reason: `${s.key} L${windowN} avg ${recentAvg.toFixed(1)} vs line ${line} (${delta>=0?'+':''}${delta.toFixed(1)})`, color: s.color, bar: s.bar }
            }).sort((a,b)=> (b.confidence - a.confidence)).slice(0,3)

            return (
              <div className="mt-3 overflow-x-auto px-1 py-2">
                <div className="flex gap-3">
                  {recs.map((r, i) => (
                  <div key={i} className="w-[280px] flex-none rounded-2xl bg-white shadow-sm ring-1 ring-gray-100 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${r.color}`}>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5"><path d="M12 3l4 7H8l4-7Zm0 18l-4-7h8l-4 7Z"/></svg>
                      </div>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${r.dir==='OVER' ? 'bg-green-50 text-green-700 ring-1 ring-green-600/20' : 'bg-red-50 text-red-700 ring-1 ring-red-600/20'}`}>{r.dir==='OVER' ? 'Trending up' : 'Trending down'}</span>
                    </div>
                    <div className="mt-2 text-xs font-medium text-gray-500">{r.key} {r.dir} {r.line.toFixed(1)}</div>
                    <div className="mt-0.5 text-2xl font-semibold text-gray-900">{r.confidence}%</div>
                    <div className="mt-1 text-[11px] text-gray-500">{r.reason}</div>
                    <div className="mt-2 h-2 rounded-full bg-gray-100" aria-label={`Confidence ${r.confidence}%`}>
                      <div className={`h-2 rounded-full ${r.dir==='OVER' ? 'bg-green-600' : 'bg-red-600'}`} style={{ width: `${Math.max(0, Math.min(100, r.confidence))}%` }} />
                    </div>
                  </div>
                  ))}
                </div>
              </div>
            )
          })()}

          

          {/* Season averages summary removed */}

          {/* Hit Rate Boxes for entered line (positioned above Prop Highlights) */}
          {hrLine && (() => {
            const lineVal = Number(hrLine)
            const vals = recentN.map(g => (
              hrStat==='PTS'?g.pts : hrStat==='AST'?g.ast : hrStat==='REB'?g.reb : hrStat==='3PM'?g.tpm : (g.pra as number)
            ))
            const compare = (v: number) => hrDir === 'over' ? v > lineVal : v < lineVal
            const lastNFlags = vals.map(compare)
            const hitCount = lastNFlags.filter(Boolean).length
            const rate = vals.length ? Math.round((hitCount / vals.length) * 100) : 0
            return (
              <div className="card p-4 mt-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-semibold text-slate-800">Hit Rate vs Line</div>
                  <div className="text-sm text-slate-600">{hrStat} {hrDir.toUpperCase()} {lineVal.toFixed(1)} • {rate}%</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {vals.map((v, i) => {
                    const hit = compare(v)
                    return (
                      <div key={i} className={`flex items-center justify-center w-6 h-6 rounded ${hit ? 'bg-emerald-500/15 text-emerald-700 ring-1 ring-emerald-600/20' : 'bg-red-500/10 text-red-600 ring-1 ring-red-600/20'}`} title={`${v} ${hit ? 'hit' : 'miss'}`}>
                        {hit ? (
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-3.5 h-3.5"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-3.5 h-3.5"><path fill="currentColor" d="M18.3 5.71 12 12.01 5.7 5.7 4.29 7.11 10.59 13.4 4.29 19.7 5.7 21.11 12 14.82l6.3 6.29 1.41-1.41-6.29-6.3 6.29-6.29z"/></svg>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })()}

          {/* Prop Highlights */}
          <div className="mt-3 grid grid-cols-4 md:grid-cols-4 gap-3">
            {(() => {
              const lastPts = recentN.map(g => g.pts)
              const lastAst = recentN.map(g => g.ast)
              const lastReb = recentN.map(g => g.reb)
              const lastTpm = recentN.map(g => g.tpm)
              const lastPra = recentN.map(g => (g.pra as number))
              function roundHalf(x: number) { return Math.round(x * 2) / 2 }
              const linePts = hrStat==='PTS' && hrLine ? Number(hrLine) : roundHalf(seasonAverages.pts)
              const lineAst = hrStat==='AST' && hrLine ? Number(hrLine) : roundHalf(seasonAverages.ast)
              const lineReb = hrStat==='REB' && hrLine ? Number(hrLine) : roundHalf(seasonAverages.reb)
              const lineTpm = hrStat==='3PM' && hrLine ? Number(hrLine) : roundHalf(seasonAverages.tpm)
              const linePra = hrStat==='PRA' && hrLine ? Number(hrLine) : roundHalf(seasonAverages.pra)
              
              // Map hrStat to card label
              const statToLabel: Record<string, string> = {
                'PTS': 'Points',
                'AST': 'Assists',
                'REB': 'Rebounds',
                '3PM': '3-Pointers',
                'PRA': 'PRA'
              }
              
              // Create cards array with original order
              const allCards = [
                { label: 'Points', value: linePts, vals: lastPts, statKey: 'PTS' },
                { label: 'Assists', value: lineAst, vals: lastAst, statKey: 'AST' },
                { label: 'Rebounds', value: lineReb, vals: lastReb, statKey: 'REB' },
                { label: '3-Pointers', value: lineTpm, vals: lastTpm, statKey: '3PM' },
                { label: 'PRA', value: linePra, vals: lastPra, statKey: 'PRA' },
              ]
              
              // Reorder: selected stat first, then Points (if different), then rest in original order
              const selectedLabel = statToLabel[hrStat]
              const selectedCard = allCards.find(c => c.label === selectedLabel)
              const pointsCard = allCards.find(c => c.label === 'Points')
              const otherCards = allCards.filter(c => c.label !== selectedLabel && c.label !== 'Points')
              
              // Build reordered array: [selected, points (if not selected), ...others]
              // If selected is Points, just put it first and keep rest in order
              const cards = selectedCard
                ? selectedLabel === 'Points'
                  ? [selectedCard, ...otherCards] // Points is selected, so don't duplicate it
                  : [selectedCard, pointsCard, ...otherCards].filter((c): c is NonNullable<typeof c> => c !== undefined) // Selected is different from Points
                : allCards
              
              return cards.map((c, idx) => {
                if (!c) return null
                const recentAvg = c.vals.length ? c.vals.reduce((a,b)=>a+b,0)/c.vals.length : 0
                const delta = recentAvg - (Number(c.value) || 0)
                const trend: 'up'|'down'|'neutral' = delta > 0.5 ? 'up' : delta < -0.5 ? 'down' : 'neutral'
                const conf = calculateConfidenceBasic(c.vals as number[], Number(c.value))
                const rec = delta >= 0 ? 'OVER' : 'UNDER'
                const overHitPct = Math.round((c.vals.filter(v=>v>Number(c.value)).length / Math.max(1,c.vals.length))*100)
                const details = (
                  c.label === 'Points' ? [
                    { label: 'Season Avg', value: seasonAverages.pts.toFixed(1) },
                    { label: `L${windowN} Avg`, value: recentAvg.toFixed(1) },
                    { label: 'Diff', value: `${delta>=0?'+':''}${delta.toFixed(1)}` },
                    { label: 'L10 Over Hit', value: `${overHitPct}%` },
                  ] : c.label === 'Assists' ? [
                    { label: 'Season Avg', value: seasonAverages.ast.toFixed(1) },
                    { label: `L${windowN} Avg`, value: recentAvg.toFixed(1) },
                    { label: 'Diff', value: `${delta>=0?'+':''}${delta.toFixed(1)}` },
                    { label: 'L10 Over Hit', value: `${overHitPct}%` },
                  ] : c.label === 'Rebounds' ? [
                    { label: 'Season Avg', value: seasonAverages.reb.toFixed(1) },
                    { label: `L${windowN} Avg`, value: recentAvg.toFixed(1) },
                    { label: 'Diff', value: `${delta>=0?'+':''}${delta.toFixed(1)}` },
                    { label: 'L10 Over Hit', value: `${overHitPct}%` },
                  ] : c.label === '3-Pointers' ? [
                    { label: 'Season Avg', value: seasonAverages.tpm.toFixed(1) },
                    { label: `L${windowN} Avg`, value: recentAvg.toFixed(1) },
                    { label: 'Diff', value: `${delta>=0?'+':''}${delta.toFixed(1)}` },
                    { label: 'L10 Over Hit', value: `${overHitPct}%` },
                  ] : [
                    { label: 'Season Avg', value: seasonAverages.pra.toFixed(1) },
                    { label: `L${windowN} Avg`, value: recentAvg.toFixed(1) },
                    { label: 'Diff', value: `${delta>=0?'+':''}${delta.toFixed(1)}` },
                    { label: 'L10 Over Hit', value: `${overHitPct}%` },
                  ]
                )
                // First card (selected stat) gets the highlight treatment
                if (idx === 0) {
                  return (
                    <div key={idx} className="col-span-4 md:col-span-4">
                      <PropCard label={`${c.label} Prop Line`} value={c.value} trend={trend} trendText={`L${windowN} Avg: ${recentAvg.toFixed(1)} (${delta>=0?'+':''}${delta.toFixed(1)})`} confidence={conf} recommendation={rec} highlight details={details} />
                    </div>
                  )
                }
                return <PropCard key={idx} label={`${c.label} Prop Line`} value={c.value} trend={trend} trendText={`L${windowN} Avg: ${recentAvg.toFixed(1)} (${delta>=0?'+':''}${delta.toFixed(1)})`} confidence={conf} recommendation={rec} details={details as Array<{ label: string; value: string }>} />
              }).filter(Boolean)
            })()}
          </div>

          {/* Historical Prop Performance (Slice Pro DataTable) - moved above Splits Table */}
          {(() => {
            type HistRow = { prop: ReactNode; hitRate: string; last5: ReactNode; margin: string; trend: ReactNode }
            function makeRow(label: string, vals: number[], line: number, dir: 'over'|'under' = 'over', lastN: number = 5) {
              const lastN_vals = vals.slice(-lastN)
              const cmp = (v: number) => dir === 'over' ? v > line : v < line
              const hitsN = lastN_vals.map(cmp)
              const hitRateNum = vals.length ? Math.round((vals.filter(cmp).length / vals.length) * 100) : 0
              // For margin, show how far on average in the chosen direction (positive is better)
              const marginAvg = lastN_vals.length ? (dir === 'over' ? (lastN_vals.reduce((a,b)=>a+(b-line),0) / lastN_vals.length) : (lastN_vals.reduce((a,b)=>a+(line-b),0) / lastN_vals.length)) : 0
              const trend: 'Hot'|'Neutral'|'Cold'|'Fire' = hitRateNum >= 80 ? 'Fire' : hitRateNum >= 65 ? 'Hot' : hitRateNum >= 45 ? 'Neutral' : 'Cold'
              return { label, line, dir, hitRate: `${hitRateNum}%`, lastN: hitsN, margin: Number(marginAvg.toFixed(1)), trend, hitRateNum }
            }
            function roundHalf(x: number) { return Math.round(x * 2) / 2 }
            
            // Get line values: use custom histLines if set, otherwise use hrLine for selected stat, otherwise season average
            const getLine = (key: 'PTS'|'AST'|'REB'|'3PM'|'PRA'): number => {
              if (histLines[key] !== null && histLines[key] !== undefined) {
                return histLines[key]!
              }
              if (hrLine && !isNaN(Number(hrLine)) && key === hrStat) {
                return Number(hrLine)
              }
              const avg = key === 'PTS' ? seasonAverages.pts : key === 'AST' ? seasonAverages.ast : key === 'REB' ? seasonAverages.reb : key === '3PM' ? seasonAverages.tpm : seasonAverages.pra
              return roundHalf(avg)
            }
            
            // Get direction: use histDirs if custom line is set, otherwise use hrDir for selected stat, otherwise 'over'
            const getDir = (key: 'PTS'|'AST'|'REB'|'3PM'|'PRA'): 'over'|'under' => {
              if (histLines[key] !== null) return histDirs[key]
              if (hrLine && !isNaN(Number(hrLine)) && key === hrStat) return hrDir
              return 'over'
            }
            
            const rowsBase = [
              makeRow('PTS', enrichedLogs.map(g=>g.pts), getLine('PTS'), getDir('PTS'), histLastN),
              makeRow('AST', enrichedLogs.map(g=>g.ast), getLine('AST'), getDir('AST'), histLastN),
              makeRow('REB', enrichedLogs.map(g=>g.reb), getLine('REB'), getDir('REB'), histLastN),
              makeRow('3PM', enrichedLogs.map(g=>g.tpm), getLine('3PM'), getDir('3PM'), histLastN),
              makeRow('PRA', enrichedLogs.map(g=> (g.pra as number)), getLine('PRA'), getDir('PRA'), histLastN),
            ]
            
            const columns: Array<DataTableColumn<HistRow>> = [
              { key: 'prop', header: 'Prop Type' },
              { key: 'hitRate', header: 'Hit Rate', align: 'right' },
              { key: 'last5', header: `Last ${histLastN}` },
              { key: 'margin', header: 'Avg Margin', align: 'right' },
              { key: 'trend', header: 'Trend' },
            ]
            
            const rows: HistRow[] = rowsBase.map((r, idx) => {
              const statKey = (['PTS', 'AST', 'REB', '3PM', 'PRA'] as const)[idx]
              const currentLine = getLine(statKey)
              const currentDir = getDir(statKey)
              
              return {
                prop: (
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{r.label}</span>
                    <select
                      value={currentDir}
                      onChange={(e) => {
                        setHistDirs(prev => ({ ...prev, [statKey]: e.target.value as 'over'|'under' }))
                        // If no custom line set, set one to preserve the direction change
                        if (histLines[statKey] === null) {
                          setHistLines(prev => ({ ...prev, [statKey]: currentLine }))
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs px-1.5 py-0.5 border border-gray-300 rounded bg-white text-gray-900"
                    >
                      <option value="over">Over</option>
                      <option value="under">Under</option>
                    </select>
                    <input
                      type="number"
                      step="0.5"
                      value={currentLine}
                      onChange={(e) => {
                        const val = e.target.value === '' ? null : (e.target.value ? Number(e.target.value) : null)
                        setHistLines(prev => ({ ...prev, [statKey]: val }))
                      }}
                      onBlur={(e) => {
                        // If empty, reset to null to use default
                        if (e.target.value === '') {
                          setHistLines(prev => ({ ...prev, [statKey]: null }))
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="w-20 px-2 py-1 text-xs border border-gray-300 rounded bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      placeholder="Line"
                    />
                  </div>
                ),
                hitRate: r.hitRate,
                last5: (
                  <div className="flex items-center gap-1">
                    {r.lastN.map((h, i) => (
                      <span key={i} className="inline-flex items-center justify-center w-4 h-4">
                        {h ? (
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-4 h-4 text-emerald-600"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z"/></svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-4 h-4 text-red-500"><path fill="currentColor" d="M18.3 5.71 12 12.01 5.7 5.7 4.29 7.11 10.59 13.4 4.29 19.7 5.7 21.11 12 14.82l6.3 6.29 1.41-1.41-6.29-6.3 6.29-6.29z"/></svg>
                        )}
                      </span>
                    ))}
                  </div>
                ),
                margin: (r.margin >= 0 ? '+' : '') + r.margin.toFixed(1),
                trend: (
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    r.trend==='Fire' ? 'bg-red-100 text-red-800 ring-2 ring-red-200' :
                    r.trend==='Hot' ? 'bg-orange-100 text-orange-800 ring-2 ring-orange-200' :
                    r.trend==='Neutral' ? 'bg-gray-100 text-gray-800 ring-2 ring-gray-200' :
                    'bg-blue-100 text-blue-800 ring-2 ring-blue-200'
                  }`}>{r.trend}</span>
                ),
              }
            })
            return (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-semibold text-slate-800">Historical Prop Performance</div>
                    <select
                      value={histLastN}
                      onChange={(e) => setHistLastN(Number(e.target.value) as 5 | 10)}
                      className="text-xs px-2 py-1 border border-gray-300 rounded bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    >
                      <option value={5}>Last 5</option>
                      <option value={10}>Last 10</option>
                    </select>
                  </div>
                  <button onClick={() => setShowHistorical(v => !v)} className="p-1 rounded hover:bg-gray-100" aria-label="Toggle historical section">
                    {showHistorical ? (
                      <svg className="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5c-7 0-11 7-11 7s4 7 11 7 11-7 11-7-4-7-11-7Zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10Z"/></svg>
                    ) : (
                      <svg className="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="currentColor"><path d="M2.1 3.5 1 4.6l3.3 3.3C2 9.7 1 12 1 12s4 7 11 7c2.3 0 4.3-.7 6-.1l3 3 1.1-1.1L2.1 3.5ZM12 17c-2.8 0-5-2.2-5-5 0-.6.1-1.1.3-1.6l1.5 1.5c-.1.3-.1.7-.1 1.1 0 1.9 1.5 3.5 3.5 3.5.4 0 .8-.1 1.1-.2l1.5 1.5c-.5.2-1.1.2-1.8.2Z"/></svg>
                    )}
                  </button>
                </div>
                {showHistorical && (
                  <DataTable<HistRow> columns={columns} rows={rows} defaultPageSize={5} pageSizeOptions={[5,10]} />
                )}
              </div>
            )
          })()}

          {/* Splits Table */}
          {(() => {
            const last5 = enrichedLogs.slice(-5)
            const mkRow = (label: string, list: typeof enrichedLogs, highlight?: 'blue'|'green'|'purple') => ({
              label,
              games: list.length,
              pts: avg(list.map(g=>g.pts)),
              ast: avg(list.map(g=>g.ast)),
              reb: avg(list.map(g=>g.reb)),
              threes: avg(list.map(g=>g.tpm)),
              pra: avg(list.map(g=> (g.pra as number))),
              highlight
            })
            const rows = [
              mkRow('Season Average', enrichedLogs),
              mkRow(`Last ${Math.min(windowN, enrichedLogs.length)} Games`, recentN, 'blue'),
              mkRow('Last 5 Games', last5),
              mkRow('Home Games', enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('vs')), 'green'),
              mkRow('Away Games', enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('@'))),
            ]
            return (
              <div className="mt-3">
                <SplitsTable rows={rows} />
              </div>
            )
          })()}

          {/* Matchup Analysis */}
          {(() => {
            const homeGames = enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('vs'))
            const awayGames = enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('@'))
            const homePts = avg(homeGames.map(g=>g.pts))
            const awayPts = avg(awayGames.map(g=>g.pts))
            const ptsRecent = avg(recentN.map(g=>g.pts))
            const ptsSeason = seasonAverages.pts
            const trend = ptsRecent - ptsSeason
            const trendTag = trend > 0.8 ? 'HOT' : trend < -0.8 ? 'COLD' : 'NEUTRAL'
            return (
              <div className="mt-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-semibold text-slate-800">Opponent Analysis</div>
                  <button onClick={() => setShowOpponent(v => !v)} className="p-1 rounded hover:bg-gray-100" aria-label="Toggle opponent analysis">
                    {showOpponent ? (
                      <svg className="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5c-7 0-11 7-11 7s4 7 11 7 11-7 11-7-4-7-11-7Zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10Z"/></svg>
                    ) : (
                      <svg className="w-4 h-4 text-slate-600" viewBox="0 0 24 24" fill="currentColor"><path d="M2.1 3.5 1 4.6l3.3 3.3C2 9.7 1 12 1 12s4 7 11 7c2.3 0 4.3-.7 6-.1l3 3 1.1-1.1L2.1 3.5ZM12 17c-2.8 0-5-2.2-5-5 0-.6.1-1.1.3-1.6l1.5 1.5c-.1.3-.1.7-.1 1.1 0 1.9 1.5 3.5 3.5 3.5.4 0 .8-.1 1.1-.2l1.5 1.5c-.5.2-1.1.2-1.8.2Z"/></svg>
                    )}
                  </button>
                </div>
                {showOpponent && (
                  <div className="overflow-x-auto">
                    <div className="flex gap-3 p-1">
                      <div className="w-[180px] flex-none">
                        <MatchupCard
                          title="Opponent Defense Rank"
                          stats={[
                            { label: 'Points Allowed to Pos', value: '—' },
                            { label: 'Assists Allowed', value: '—' },
                            { label: 'Rebounds Allowed', value: '—' },
                          ]}
                        />
                      </div>
                      <div className="w-[180px] flex-none">
                        <MatchupCard
                          title="Pace & Style"
                          stats={[
                            { label: 'Expected Pace', value: '—' },
                            { label: 'Expected Possessions', value: '—' },
                          ]}
                        />
                      </div>
                      <div className="w-[180px] flex-none">
                        <MatchupCard
                          title="Recent Form"
                          stats={[
                            { label: `L${windowN} PTS Avg`, value: ptsRecent.toFixed(1), valueColor: trend >= 0 ? 'text-green-700' : 'text-red-700' },
                            { label: 'Season PTS Avg', value: ptsSeason.toFixed(1) },
                          ]}
                          tags={[trendTag]}
                        />
                      </div>
                      <div className="w-[180px] flex-none">
                        <MatchupCard
                          title="Game Context"
                          stats={[
                            { label: 'Home PTS', value: homeGames.length ? homePts.toFixed(1) : '—' },
                            { label: 'Away PTS', value: awayGames.length ? awayPts.toFixed(1) : '—' },
                          ]}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })()}


          {/* Live Odds Comparison hidden for now */}
          {(() => {
            const showLiveOdds = false
            if (!showLiveOdds) return null
            function roundHalf(x: number) { return Math.round(x * 2) / 2 }
            const linePts = roundHalf(seasonAverages.pts)
            const lineAst = roundHalf(seasonAverages.ast)
            const books = [
              { book: 'DraftKings', over: '-115', under: '-105' },
              { book: 'FanDuel', over: '-120', under: '+100' },
              { book: 'BetMGM', over: '-110', under: '-110' },
            ]
            return (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4 mt-4">
                <OddsCard title={`Points - Over/Under ${linePts}`} color="blue" odds={books} bestOver="-110" bestUnder="+100" />
                <OddsCard title={`Assists - Over/Under ${lineAst}`} color="green" odds={books} bestOver="+100" bestUnder="-112" />
              </div>
            )
          })()}

          {/* Advanced Metrics & Correlations */}
          {(() => {
            const recentPts = recentN.map(g=>g.pts)
            const recentAst = recentN.map(g=>g.ast)
            const recentReb = recentN.map(g=>g.reb)
            const usageRecent = avg(recentN.map(g=> (g.pts + g.ast + g.reb)))
            const usageSeason = seasonAverages.pra
            const usageDelta = usageRecent - usageSeason
            const usageTrend = usageDelta > 1 ? '↑' : usageDelta < -1 ? '↓' : '→'
            const corrPtsAst = pearsonCorrelation(recentPts, recentAst)
            const corrPtsReb = pearsonCorrelation(recentPts, recentReb)
            const corrAstReb = pearsonCorrelation(recentAst, recentReb)
            const fmt = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`
            return (
              <div className="overflow-x-auto mt-3">
                <div className="flex gap-3 p-1">
                  <div className="w-[180px] flex-none bg-purple-50 border-2 border-purple-200 rounded-lg p-3">
                    <div className="font-semibold text-purple-900 mb-2 text-xs">Usage Trend (Proxy)</div>
                    <div className="text-[11px] text-purple-800 flex items-center justify-between"><span>Season PRA</span><span className="font-bold">{usageSeason.toFixed(1)}</span></div>
                    <div className="text-[11px] text-purple-800 flex items-center justify-between mt-1"><span>Recent (L{windowN})</span><span className="font-bold">{usageRecent.toFixed(1)}</span></div>
                    <div className="mt-1.5 text-xs text-purple-900 font-semibold">{usageTrend} {usageDelta >= 0 ? '+' : ''}{usageDelta.toFixed(1)}</div>
                  </div>
                  <div className="w-[180px] flex-none bg-orange-50 border-2 border-orange-200 rounded-lg p-3">
                    <div className="font-semibold text-orange-900 mb-2 text-xs">Prop Correlations (L{windowN})</div>
                    <div className="text-[11px] text-orange-800 flex items-center justify-between"><span>PTS ↔ AST</span><span className="font-bold">{fmt(corrPtsAst)}</span></div>
                    <div className="text-[11px] text-orange-800 flex items-center justify-between mt-1"><span>PTS ↔ REB</span><span className="font-bold">{fmt(corrPtsReb)}</span></div>
                    <div className="text-[11px] text-orange-800 flex items-center justify-between mt-1"><span>AST ↔ REB</span><span className="font-bold">{fmt(corrAstReb)}</span></div>
                  </div>
                  <div className="w-[180px] flex-none bg-teal-50 border-2 border-teal-200 rounded-lg p-3">
                    <div className="font-semibold text-teal-900 mb-2 text-xs">Defensive Matchup</div>
                    <div className="text-[11px] text-teal-800">Primary: —</div>
                    <div className="text-[11px] text-teal-800 mt-1">Rating: —</div>
                    <div className="text-[11px] text-teal-800 mt-1">Historical: —</div>
                  </div>
                </div>
              </div>
            )
          })()}

          

          

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ marginTop: 12 }}>
            <TrendChart
              title="Points - Last 10 Games"
              data={chartData.map(d => ({ 
                idx: d.idx, 
                value: d.PTS, 
                propLine: (hrStat==='PTS' && hrLine) ? Number(hrLine) : Math.round(seasonAverages.pts*2)/2,
                date: d.date,
                matchup: d.matchup
              }))}
              yLabel="PTS"
              ariaLabel={`Points last 10 games compared to line`}
              color="#2563eb"
            />
            <TrendChart
              title="Assists - Last 10 Games"
              data={chartData.map(d => ({ 
                idx: d.idx, 
                value: d.AST, 
                propLine: (hrStat==='AST' && hrLine) ? Number(hrLine) : Math.round(seasonAverages.ast*2)/2,
                date: d.date,
                matchup: d.matchup
              }))}
              yLabel="AST"
              ariaLabel={`Assists last 10 games compared to line`}
              color="#f59e0b"
            />
            <TrendChart
              title="Rebounds - Last 10 Games"
              data={chartData.map(d => ({ 
                idx: d.idx, 
                value: d.REB, 
                propLine: (hrStat==='REB' && hrLine) ? Number(hrLine) : Math.round(seasonAverages.reb*2)/2,
                date: d.date,
                matchup: d.matchup
              }))}
              yLabel="REB"
              ariaLabel={`Rebounds last 10 games compared to line`}
              color="#10b981"
            />
          </div>

          

          

          {/* Evaluated suggestion */}
          {selectedSuggestion && (
            <div className="mt-3">
              <SuggestionCards suggestions={[selectedSuggestion]} />
            </div>
          )}

          {/* Raw logs table (Slice Pro DataTable) */}
          {(() => {
            type GameRow = { date: string; matchup: string; pts: number; reb: number; ast: number; tpm: number }
            const columns: Array<DataTableColumn<GameRow>> = [
              { key: 'date', header: 'Date' },
              { key: 'matchup', header: 'Matchup' },
              { key: 'pts', header: 'PTS', align: 'right' },
              { key: 'reb', header: 'REB', align: 'right' },
              { key: 'ast', header: 'AST', align: 'right' },
              { key: 'tpm', header: '3PM', align: 'right' },
            ]
            const rows: GameRow[] = sortedLogs.slice(-50).map(g => ({
              date: g.game_date,
              matchup: g.matchup,
              pts: g.pts,
              reb: g.reb,
              ast: g.ast,
              tpm: g.tpm,
            }))
            return (
              <div className="mt-3">
                <DataTable<GameRow> columns={columns} rows={rows} caption="Game Logs" defaultPageSize={10} pageSizeOptions={[10,20,50]} />
                {logs.length === 0 && (
                  <div className="px-4 py-3 text-sm text-gray-500">No recent game logs.</div>
                )}
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}

