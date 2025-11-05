import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'
import { useMutation } from '@tanstack/react-query'
import { SuggestionCards } from '../components/SuggestionCards'
import { PropCard } from '../components/PropCard'
import { calculateConfidenceBasic } from '../utils/confidence'
import { TrendChart } from '../components/TrendChart'

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

  useEffect(() => {
    (async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
        // Fetch player detail for display name
        try {
          const rName = await fetch(`/api/v1/players/${id}`)
          if (rName.ok) {
            const j = await rName.json()
            if (j?.player?.name) setPlayerName(String(j.player.name))
          }
        } catch {}
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

  // Keep last N slices for quick calculations if needed
  // (Replaced by windowN controls in charts/tiles)
  // const last5 = useMemo(() => enrichedLogs.slice(-5), [enrichedLogs])
  // const last10 = useMemo(() => enrichedLogs.slice(-10), [enrichedLogs])

  const chartData = useMemo(() => enrichedLogs.slice(-10).map((g, i) => ({
    idx: i + 1,
    date: g.game_date,
    PTS: g.pts,
    REB: g.reb,
    AST: g.ast,
    TPM: g.tpm,
    PRA: (g.pra as number),
  })), [enrichedLogs])

  const homeLogs = useMemo(() => enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('vs')), [enrichedLogs])
  const awayLogs = useMemo(() => enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('@')), [enrichedLogs])
  const venueAverages = useMemo(() => ({
    home: { pts: avg(homeLogs.map(g => g.pts)), reb: avg(homeLogs.map(g => g.reb)), ast: avg(homeLogs.map(g => g.ast)), tpm: avg(homeLogs.map(g => g.tpm)) },
    away: { pts: avg(awayLogs.map(g => g.pts)), reb: avg(awayLogs.map(g => g.reb)), ast: avg(awayLogs.map(g => g.ast)), tpm: avg(awayLogs.map(g => g.tpm)) },
  }), [homeLogs, awayLogs])

  function hitRate(logsIn: GameLog[], key: keyof GameLog | 'pra', line: number, dir: 'over' | 'under') {
    const vals = logsIn.map(g => key === 'pra' ? ((g.pts + g.reb + g.ast)) : Number(g[key] as number))
    if (!vals.length) return 0
    const hits = vals.filter(v => dir === 'over' ? v > line : v < line).length
    return Math.round((hits / vals.length) * 100)
  }

  const [hrStat, setHrStat] = useState<'PTS'|'REB'|'AST'|'3PM'|'PRA'>('PTS')
  const [hrLine, setHrLine] = useState<string>('')
  const [hrDir, setHrDir] = useState<'over'|'under'>('over')
  const hrKeyMap: Record<string, keyof GameLog | 'pra'> = { PTS: 'pts', REB: 'reb', AST: 'ast', '3PM': 'tpm', PRA: 'pra' }
  const hrSeason = useMemo(() => hrLine ? hitRate(enrichedLogs, hrKeyMap[hrStat], Number(hrLine), hrDir) : null, [enrichedLogs, hrStat, hrLine, hrDir])
  const hrRecent = useMemo(() => hrLine ? hitRate(recentN, hrKeyMap[hrStat], Number(hrLine), hrDir) : null, [recentN, hrStat, hrLine, hrDir])

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

  const selectedSuggestion: any | null = useMemo(() => {
    const items = evalResult?.suggestions || []
    const match = items.find((s: any) => s.type === hrStat)
    if (!match) return null
    return { ...match, chosenDirection: hrDir }
  }, [evalResult, hrStat, hrDir])

  function StatCard({ title, value, sub }: { title: string; value: string; sub?: string }) {
    return (
      <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, background: '#fff' }}>
        <div style={{ fontSize: 12, color: '#6b7280' }}>{title}</div>
        <div style={{ fontSize: 22, fontWeight: 700, marginTop: 2 }}>{value}</div>
        {sub && <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{sub}</div>}
      </div>
    )
  }

  

  return (
    <div>
      <h2>{playerName ? playerName : 'Player'} Profile</h2>
      <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>Season: {fallbackUsed ? fallbackUsed : season}</div>
      {fallbackUsed && (
        <div style={{ marginTop: 6, fontSize: 12, color: '#6b7280' }}>No recent logs for {season}. Showing {fallbackUsed}.</div>
      )}
      {loading ? (
        <div style={{ marginTop: 12 }}>Loading…</div>
      ) : error ? (
        <div style={{ marginTop: 12, color: '#b91c1c' }}>Error: {error}</div>
      ) : (
        <div>
          {/* Controls */}
          <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Window</div>
            <select value={windowN} onChange={(e) => setWindowN(Number(e.target.value))} style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
              {[5,10,20].map(n => <option key={n} value={n}>{n} games</option>)}
            </select>
            <div style={{ fontSize: 12, color: '#6b7280', marginLeft: 8 }}>Hit Rate</div>
            <select value={hrStat} onChange={(e) => setHrStat(e.target.value as any)} style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, background: '#fff' }}>
              {['PTS','REB','AST','3PM','PRA'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <input value={hrLine} onChange={(e) => setHrLine(e.target.value)} inputMode="decimal" placeholder="Line (e.g. 24.5)" style={{ padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6 }} />
            <div className="flex items-center gap-2">
              <button onClick={() => setHrDir('over')} className="px-3 py-2 rounded border border-gray-300" style={{ background: hrDir === 'over' ? '#17408B' : '#fff', color: hrDir === 'over' ? '#fff' : '#111827' }}>Over</button>
              <button onClick={() => setHrDir('under')} className="px-3 py-2 rounded border border-gray-300" style={{ background: hrDir === 'under' ? '#17408B' : '#fff', color: hrDir === 'under' ? '#fff' : '#111827' }}>Under</button>
            </div>
            <button onClick={() => evalLine.mutate()} disabled={!hrLine || evalLine.isPending} className="px-3 py-2 rounded" style={{ background: '#17408B', color: '#fff', opacity: (!hrLine || evalLine.isPending) ? 0.7 : 1 }}>{evalLine.isPending ? 'Evaluating…' : 'Evaluate Line'}</button>
          </div>

          {/* Hit rate cards (single row) - moved above season averages */}
          {hrLine && (
            <div style={{ display: 'flex', gap: 12, marginTop: 12, overflowX: 'auto' }}>
              <div style={{ minWidth: 200 }}>
                <StatCard title={`Season Hit Rate (${hrStat} ${hrDir} ${hrLine})`} value={`${hrSeason}%`} />
              </div>
              <div style={{ minWidth: 200 }}>
                <StatCard title={`${windowN}g Hit Rate (${hrStat} ${hrDir} ${hrLine})`} value={`${hrRecent}%`} />
              </div>
            </div>
          )}

          {/* Summary tiles - single row with horizontal scroll on small screens */}
          <div style={{ display: 'flex', gap: 12, marginTop: 12, overflowX: 'auto', paddingBottom: 4 }}>
            <div style={{ minWidth: 200 }}><StatCard title="Season Avg PTS" value={seasonAverages.pts.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.pts)).toFixed(1)}`} /></div>
            <div style={{ minWidth: 200 }}><StatCard title="Season Avg REB" value={seasonAverages.reb.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.reb)).toFixed(1)}`} /></div>
            <div style={{ minWidth: 200 }}><StatCard title="Season Avg AST" value={seasonAverages.ast.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.ast)).toFixed(1)}`} /></div>
            <div style={{ minWidth: 200 }}><StatCard title="Season Avg 3PM" value={seasonAverages.tpm.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.tpm)).toFixed(1)}`} /></div>
          </div>

          {/* Prop Highlights (v2) */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4 mt-4">
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
              const cards = [
                { label: 'Points', value: linePts, vals: lastPts },
                { label: 'Assists', value: lineAst, vals: lastAst },
                { label: 'Rebounds', value: lineReb, vals: lastReb },
                { label: '3-Pointers', value: lineTpm, vals: lastTpm },
                { label: 'PRA', value: linePra, vals: lastPra },
              ]
              return cards.map((c, idx) => {
                const recentAvg = c.vals.length ? c.vals.reduce((a,b)=>a+b,0)/c.vals.length : 0
                const delta = recentAvg - (Number(c.value) || 0)
                const trend: 'up'|'down'|'neutral' = delta > 0.5 ? 'up' : delta < -0.5 ? 'down' : 'neutral'
                const conf = calculateConfidenceBasic(c.vals as number[], Number(c.value))
                const rec = delta >= 0 ? 'OVER' : 'UNDER'
                return (
                  <PropCard key={idx} label={`${c.label} Prop Line`} value={c.value} trend={trend} trendText={`L${windowN} Avg: ${recentAvg.toFixed(1)} (${delta>=0?'+':''}${delta.toFixed(1)})`} confidence={conf} recommendation={rec} />
                )
              })
            })()}
          </div>

          {/* Venue split - below season averages */}
          <div style={{ display: 'flex', gap: 12, marginTop: 12, overflowX: 'auto', paddingBottom: 4 }}>
            <div style={{ minWidth: 220 }}><StatCard title="Home Splits (PTS/REB/AST/3PM)" value={`${venueAverages.home.pts.toFixed(1)} / ${venueAverages.home.reb.toFixed(1)} / ${venueAverages.home.ast.toFixed(1)} / ${venueAverages.home.tpm.toFixed(1)}`} /></div>
            <div style={{ minWidth: 220 }}><StatCard title="Away Splits (PTS/REB/AST/3PM)" value={`${venueAverages.away.pts.toFixed(1)} / ${venueAverages.away.reb.toFixed(1)} / ${venueAverages.away.ast.toFixed(1)} / ${venueAverages.away.tpm.toFixed(1)}`} /></div>
          </div>

          

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" style={{ marginTop: 12 }}>
            <TrendChart
              title="Points - Last 10 Games"
              data={chartData.map(d => ({ idx: d.idx, value: d.PTS, propLine: (hrStat==='PTS' && hrLine) ? Number(hrLine) : Math.round(seasonAverages.pts*2)/2 }))}
              color="#2563eb"
              yLabel="PTS"
            />
            <TrendChart
              title="Assists - Last 10 Games"
              data={chartData.map(d => ({ idx: d.idx, value: d.AST, propLine: (hrStat==='AST' && hrLine) ? Number(hrLine) : Math.round(seasonAverages.ast*2)/2 }))}
              color="#F59E0B"
              yLabel="AST"
            />
            <TrendChart
              title="Rebounds - Last 10 Games"
              data={chartData.map(d => ({ idx: d.idx, value: d.REB, propLine: (hrStat==='REB' && hrLine) ? Number(hrLine) : Math.round(seasonAverages.reb*2)/2 }))}
              color="#10B981"
              yLabel="REB"
            />
          </div>

          

          

          {/* Evaluated suggestion */}
          {selectedSuggestion && (
            <div style={{ marginTop: 12 }}>
              <SuggestionCards suggestions={[selectedSuggestion]} />
            </div>
          )}

          {/* Raw logs table */}
          <div style={{ marginTop: 12, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>Date</th>
                  <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>Matchup</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>PTS</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>REB</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>AST</th>
                  <th style={{ textAlign: 'right', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>3PM</th>
                </tr>
              </thead>
              <tbody>
                {sortedLogs.slice(-20).map((g) => (
                  <tr key={g.game_id}>
                    <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px' }}>{g.game_date}</td>
                    <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px' }}>{g.matchup}</td>
                    <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.pts}</td>
                    <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.reb}</td>
                    <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.ast}</td>
                    <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', textAlign: 'right' }}>{g.tpm}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {logs.length === 0 && (
              <div style={{ marginTop: 8, color: '#6b7280' }}>No recent game logs.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

