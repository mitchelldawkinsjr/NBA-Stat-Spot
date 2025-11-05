import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Line } from 'recharts'

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

  useEffect(() => {
    (async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
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

  const last5 = useMemo(() => enrichedLogs.slice(-5), [enrichedLogs])
  const last10 = useMemo(() => enrichedLogs.slice(-10), [enrichedLogs])
  // Keep recent averages for potential display/overlays
  const recentAverages = useMemo(() => ({
    pts5: avg(last5.map(g => g.pts)),
    reb5: avg(last5.map(g => g.reb)),
    ast5: avg(last5.map(g => g.ast)),
    tpm5: avg(last5.map(g => g.tpm)),
    pts10: avg(last10.map(g => g.pts)),
    reb10: avg(last10.map(g => g.reb)),
    ast10: avg(last10.map(g => g.ast)),
    tpm10: avg(last10.map(g => g.tpm)),
    pra5: avg(last5.map(g => (g.pra as number))),
    pra10: avg(last10.map(g => (g.pra as number))),
  }), [last5, last10])

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
      <h2>Player Profile</h2>
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
          </div>

          {/* Summary tiles */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" style={{ marginTop: 12 }}>
            <StatCard title="Season Avg PTS" value={seasonAverages.pts.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.pts)).toFixed(1)}`} />
            <StatCard title="Season Avg REB" value={seasonAverages.reb.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.reb)).toFixed(1)}`} />
            <StatCard title="Season Avg AST" value={seasonAverages.ast.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.ast)).toFixed(1)}`} />
            <StatCard title="Season Avg 3PM" value={seasonAverages.tpm.toFixed(1)} sub={`${windowN}g: ${avg(recentN.map(g=>g.tpm)).toFixed(1)}`} />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3" style={{ marginTop: 12 }}>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Points - Last 10 Games</div>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="idx" />
                    <YAxis allowDecimals />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="PTS" fill="#2563eb" name="PTS" />
                    <Line type="monotone" dataKey={() => avg(recentN.map(g=>g.pts))} stroke="#059669" name={`${windowN}g avg`} dot={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Rebounds/Assists - Last 10</div>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="idx" />
                    <YAxis allowDecimals />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="REB" fill="#10B981" name="REB" />
                    <Bar dataKey="AST" fill="#F59E0B" name="AST" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>PRA - Last 10</div>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="idx" />
                    <YAxis allowDecimals />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="PRA" fill="#7c3aed" name="PRA" />
                    <Line type="monotone" dataKey={() => avg(recentN.map(g=> (g.pra as number)))} stroke="#111827" name={`${windowN}g avg`} dot={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Venue split */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" style={{ marginTop: 12 }}>
            <StatCard title="Home Splits (PTS/REB/AST/3PM)" value={`${venueAverages.home.pts.toFixed(1)} / ${venueAverages.home.reb.toFixed(1)} / ${venueAverages.home.ast.toFixed(1)} / ${venueAverages.home.tpm.toFixed(1)}`} />
            <StatCard title="Away Splits (PTS/REB/AST/3PM)" value={`${venueAverages.away.pts.toFixed(1)} / ${venueAverages.away.reb.toFixed(1)} / ${venueAverages.away.ast.toFixed(1)} / ${venueAverages.away.tpm.toFixed(1)}`} />
          </div>

          {/* Hit rate cards */}
          {hrLine && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" style={{ marginTop: 12 }}>
              <StatCard title={`Season Hit Rate (${hrStat} ${hrDir} ${hrLine})`} value={`${hrSeason}%`} />
              <StatCard title={`${windowN}g Hit Rate (${hrStat} ${hrDir} ${hrLine})`} value={`${hrRecent}%`} />
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


