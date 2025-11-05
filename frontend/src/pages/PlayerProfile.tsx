import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'
import { useMutation } from '@tanstack/react-query'
import { SuggestionCards } from '../components/SuggestionCards'
import { PropCard } from '../components/PropCard'
import { calculateConfidenceBasic } from '../utils/confidence'
import { TrendChart } from '../components/TrendChart'
import { SplitsTable } from '../components/SplitsTable'
import { MatchupCard } from '../components/MatchupCard'
import { PropHistoryRow } from '../components/PropHistory'
import { OddsCard } from '../components/OddsCard'

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

  // Venue logs if needed later
  // const homeLogs = useMemo(() => enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('vs')), [enrichedLogs])
  // const awayLogs = useMemo(() => enrichedLogs.filter(g => (g.matchup || '').toLowerCase().includes('@')), [enrichedLogs])

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
                if (c.label === 'Points') {
                  const details = [
                    { label: 'Season Avg', value: seasonAverages.pts.toFixed(1) },
                    { label: `L${windowN} Avg`, value: recentAvg.toFixed(1) },
                    { label: 'Diff', value: `${delta>=0?'+':''}${delta.toFixed(1)}` },
                    { label: 'L10 Over Hit', value: `${Math.round((c.vals.filter(v=>v>Number(c.value)).length / Math.max(1,c.vals.length))*100)}%` },
                  ]
                  return (
                    <div key={idx} className="md:col-span-2">
                      <PropCard label={`Points Prop Line`} value={c.value} trend={trend} trendText={`L${windowN} Avg: ${recentAvg.toFixed(1)} (${delta>=0?'+':''}${delta.toFixed(1)})`} confidence={conf} recommendation={rec} highlight details={details} />
                    </div>
                  )
                }
                return <PropCard key={idx} label={`${c.label} Prop Line`} value={c.value} trend={trend} trendText={`L${windowN} Avg: ${recentAvg.toFixed(1)} (${delta>=0?'+':''}${delta.toFixed(1)})`} confidence={conf} recommendation={rec} />
              })
            })()}
          </div>

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
              <div style={{ marginTop: 12 }}>
                <SplitsTable rows={rows} />
              </div>
            )
          })()}

          {/* Matchup Analysis - placeholders for ranks/pace; real data TBD */}
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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4" style={{ marginTop: 12 }}>
                <MatchupCard
                  title="Opponent Defense Rank"
                  stats={[
                    { label: 'Points Allowed to Pos', value: '—' },
                    { label: 'Assists Allowed', value: '—' },
                    { label: 'Rebounds Allowed', value: '—' },
                  ]}
                />
                <MatchupCard
                  title="Pace & Style"
                  stats={[
                    { label: 'Expected Pace', value: '—' },
                    { label: 'Expected Possessions', value: '—' },
                  ]}
                />
                <MatchupCard
                  title="Recent Form"
                  stats={[
                    { label: `L${windowN} PTS Avg`, value: ptsRecent.toFixed(1), valueColor: trend >= 0 ? 'text-green-700' : 'text-red-700' },
                    { label: 'Season PTS Avg', value: ptsSeason.toFixed(1) },
                  ]}
                  tags={[trendTag]}
                />
                <MatchupCard
                  title="Game Context"
                  stats={[
                    { label: 'Home PTS', value: homeGames.length ? homePts.toFixed(1) : '—' },
                    { label: 'Away PTS', value: awayGames.length ? awayPts.toFixed(1) : '—' },
                  ]}
                />
              </div>
            )
          })()}

          {/* Historical Prop Performance */}
          {(() => {
            function makeRow(label: string, vals: number[], line: number) {
              const lastFive = vals.slice(-5)
              const hits5 = lastFive.map(v => v > line)
              const hitRate = vals.length ? Math.round((vals.filter(v => v > line).length / vals.length) * 100) : 0
              const marginAvg = lastFive.length ? (lastFive.reduce((a,b)=>a+(b-line),0) / lastFive.length) : 0
              const trend: 'Hot'|'Neutral'|'Cold'|'Fire' = hitRate >= 80 ? 'Fire' : hitRate >= 65 ? 'Hot' : hitRate >= 45 ? 'Neutral' : 'Cold'
              return { prop: `${label} Over ${line}`, hitRateText: `${hitRate}%`, last5: hits5, marginText: `${marginAvg>=0?'+':''}${marginAvg.toFixed(1)}` , trend }
            }
            function roundHalf(x: number) { return Math.round(x * 2) / 2 }
            const linePts = roundHalf(seasonAverages.pts)
            const lineAst = roundHalf(seasonAverages.ast)
            const lineReb = roundHalf(seasonAverages.reb)
            const lineTpm = roundHalf(seasonAverages.tpm)
            const linePra = roundHalf(seasonAverages.pra)
            const rows = [
              makeRow('PTS', enrichedLogs.map(g=>g.pts), linePts),
              makeRow('AST', enrichedLogs.map(g=>g.ast), lineAst),
              makeRow('REB', enrichedLogs.map(g=>g.reb), lineReb),
              makeRow('3PM', enrichedLogs.map(g=>g.tpm), lineTpm),
              makeRow('PRA', enrichedLogs.map(g=> (g.pra as number)), linePra),
            ]
            return (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm" style={{ marginTop: 12 }}>
                <div className="grid grid-cols-5 bg-gray-50 text-xs font-bold text-gray-700 uppercase">
                  <div className="p-3 border-r border-gray-200">Prop Type</div>
                  <div className="p-3 border-r border-gray-200">Hit Rate</div>
                  <div className="p-3 border-r border-gray-200">Last 5</div>
                  <div className="p-3 border-r border-gray-200">Avg Margin</div>
                  <div className="p-3">Trend</div>
                </div>
                <div className="divide-y divide-gray-100">
                  {rows.map((r, i) => (
                    <PropHistoryRow key={i} prop={r.prop} hitRateText={r.hitRateText} last5={r.last5} marginText={r.marginText} trend={r.trend} />
                  ))}
                </div>
              </div>
            )
          })()}

          {/* Live Odds Comparison (placeholder data) */}
          {(() => {
            function roundHalf(x: number) { return Math.round(x * 2) / 2 }
            const linePts = roundHalf(seasonAverages.pts)
            const lineAst = roundHalf(seasonAverages.ast)
            const books = [
              { book: 'DraftKings', over: '-115', under: '-105' },
              { book: 'FanDuel', over: '-120', under: '+100' },
              { book: 'BetMGM', over: '-110', under: '-110' },
            ]
            return (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4" style={{ marginTop: 12 }}>
                <OddsCard title={`Points - Over/Under ${linePts}`} color="blue" odds={books} bestOver="-110" bestUnder="+100" />
                <OddsCard title={`Assists - Over/Under ${lineAst}`} color="green" odds={books} bestOver="+100" bestUnder="-112" />
              </div>
            )
          })()}

          

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

