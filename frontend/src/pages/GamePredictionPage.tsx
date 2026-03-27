import { useEffect, useState, useMemo, useRef } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts'
import { apiFetch } from '../utils/api'

const NUM_TEAMS = 30
function rankToStrength(rank: number | null | undefined): number {
  if (rank == null) return 0
  return Math.max(0, NUM_TEAMS + 1 - rank)
}

function rankLabel(rank: number | null | undefined): string {
  if (rank == null) return '—'
  return `#${rank}`
}

function teamLogoUrl(abbr: string): string {
  const a = (abbr || '').trim().toUpperCase()
  return a ? `https://a.espncdn.com/i/teamlogos/nba/500/${a}.png` : ''
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}

function dateFromGameTimeUtc(iso: string | undefined): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString().slice(0, 10)
}

type RankBlock = { pts?: number | null; reb?: number | null; ast?: number | null; '3pm'?: number | null }
type PaceData = { possessions?: number; pace_rank?: number }

type PlayerRow = {
  id: number
  name: string
  position?: string
  avg_min?: number
  season_pts?: number | null
  season_reb?: number | null
  season_ast?: number | null
  last5_pts?: number | null
  last5_reb?: number | null
  last5_ast?: number | null
  games_played?: number
}

type H2HGame = {
  date: string
  home: string
  away: string
  home_score: number
  away_score: number
  winner: string
}

type PredictionDetail = {
  gameId: string
  home: string
  away: string
  home_full_name?: string
  away_full_name?: string
  predicted_winner: string
  predicted_winner_name?: string
  win_probability_home: number
  win_probability_away: number
  key_advantage_summary?: string
  outlook_summary?: string
  outlook_extended?: string
  home_ppg?: number
  away_ppg?: number
  home_pace?: number
  away_pace?: number
  home_off_rank_pts?: number | null
  home_def_rank_pts?: number | null
  away_off_rank_pts?: number | null
  away_def_rank_pts?: number | null
  // Full rank data
  home_def_full?: RankBlock
  away_def_full?: RankBlock
  home_off_full?: RankBlock
  away_off_full?: RankBlock
  home_pace_data?: PaceData
  away_pace_data?: PaceData
  // Position defense
  home_pos_defense?: Record<string, RankBlock>
  away_pos_defense?: Record<string, RankBlock>
  // Key players
  home_key_players?: PlayerRow[]
  away_key_players?: PlayerRow[]
  // H2H
  h2h_games?: H2HGame[]
  h2h_wins_home?: number
  h2h_wins_away?: number
  game_time_utc?: string
  _incomplete?: boolean
}

export default function GamePredictionPage() {
  const { gameId } = useParams()
  const [searchParams] = useSearchParams()
  const dateFromUrl = searchParams.get('date') || ''
  const [dateQuery, setDateQuery] = useState<string>(() => dateFromUrl || todayISO())
  const [refreshNonce, setRefreshNonce] = useState(0)
  const dateCorrectedRef = useRef(false)
  const [data, setData] = useState<PredictionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dateCorrectedRef.current = false
    setDateQuery(dateFromUrl || todayISO())
  }, [gameId, dateFromUrl])

  useEffect(() => {
    if (!gameId) return
    let cancelled = false
    const run = async () => {
      setLoading(true)
      setError(null)
      try {
        const q = new URLSearchParams({ date: dateQuery })
        if (refreshNonce > 0) q.set('_refresh', String(refreshNonce))
        const res = await apiFetch(`api/v1/games/predictions/${gameId}?${q.toString()}`)
        if (cancelled) return
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          setError((body as { error?: string }).error || 'Failed to load game prediction')
          return
        }
        const json = (await res.json()) as PredictionDetail & { error?: string }
        if (json.error) {
          setError(json.error)
          return
        }
        setData(json)
        const gameDate = dateFromGameTimeUtc(json.game_time_utc)
        if (gameDate && gameDate !== dateQuery && !dateCorrectedRef.current) {
          dateCorrectedRef.current = true
          setDateQuery(gameDate)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error loading prediction')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [gameId, dateQuery, refreshNonce])

  // Team comparison bar chart data (full ranks)
  const comparisonBarData = useMemo(() => {
    if (!data) return []
    const home = data.home_full_name || data.home
    const away = data.away_full_name || data.away
    const hd = data.home_def_full || {}
    const ad = data.away_def_full || {}
    const ho = data.home_off_full || {}
    const ao = data.away_off_full || {}
    const rows = [
      { metric: 'Off. PTS strength', home: rankToStrength(ho.pts), away: rankToStrength(ao.pts), homeLabel: home, awayLabel: away },
      { metric: 'Off. REB strength', home: rankToStrength(ho.reb), away: rankToStrength(ao.reb), homeLabel: home, awayLabel: away },
      { metric: 'Off. AST strength', home: rankToStrength(ho.ast), away: rankToStrength(ao.ast), homeLabel: home, awayLabel: away },
      { metric: 'Def. PTS strength', home: rankToStrength(hd.pts), away: rankToStrength(ad.pts), homeLabel: home, awayLabel: away },
      { metric: 'Def. REB strength', home: rankToStrength(hd.reb), away: rankToStrength(ad.reb), homeLabel: home, awayLabel: away },
      { metric: 'Def. AST strength', home: rankToStrength(hd.ast), away: rankToStrength(ad.ast), homeLabel: home, awayLabel: away },
      { metric: 'Pace (possessions)', home: data.home_pace_data?.possessions ?? (data.home_pace ?? 0), away: data.away_pace_data?.possessions ?? (data.away_pace ?? 0), homeLabel: home, awayLabel: away },
      { metric: 'PPG', home: data.home_ppg ?? 0, away: data.away_ppg ?? 0, homeLabel: home, awayLabel: away },
    ]
    // Always keep Off. PTS and Def. PTS rows so charts do not disappear when ranks are still loading
    return rows.filter((row, i) => i === 0 || i === 3 || row.home > 0 || row.away > 0)
  }, [data])

  // Radar data from the same source
  const radarData = useMemo(() => {
    if (!data || comparisonBarData.length === 0) return []
    const home = data.home_full_name || data.home
    const away = data.away_full_name || data.away
    // Use the first 6 metrics for radar (skip Pace/PPG since different scale)
    return comparisonBarData.slice(0, 6).map((d) => ({
      subject: d.metric,
      [home]: d.home,
      [away]: d.away,
      fullMark: NUM_TEAMS,
    }))
  }, [data, comparisonBarData])

  // Defensive matchup bar chart: each team's def rank by stat (lower rank = better)
  const defMatchupData = useMemo(() => {
    if (!data) return []
    const home = data.home_full_name || data.home
    const away = data.away_full_name || data.away
    const hd = data.home_def_full || {}
    const ad = data.away_def_full || {}
    return [
      { stat: 'PTS allowed', home: hd.pts ?? null, away: ad.pts ?? null, homeLabel: home, awayLabel: away },
      { stat: 'REB allowed', home: hd.reb ?? null, away: ad.reb ?? null, homeLabel: home, awayLabel: away },
      { stat: 'AST allowed', home: hd.ast ?? null, away: ad.ast ?? null, homeLabel: home, awayLabel: away },
      { stat: '3PM allowed', home: hd['3pm'] ?? null, away: ad['3pm'] ?? null, homeLabel: home, awayLabel: away },
    ].filter((d, i) => i === 0 || d.home != null || d.away != null)
  }, [data])

  // Position defense bar chart: how each team defends each position
  const posDefData = useMemo(() => {
    if (!data) return []
    const home = data.home_full_name || data.home
    const away = data.away_full_name || data.away
    const positions = ['PG', 'SG', 'SF', 'PF', 'C']
    return positions.map((pos) => {
      const hr = (data.home_pos_defense || {})[pos] || {}
      const ar = (data.away_pos_defense || {})[pos] || {}
      return {
        pos,
        homeRank: hr.pts ?? null,
        awayRank: ar.pts ?? null,
        homeStrength: rankToStrength(hr.pts),
        awayStrength: rankToStrength(ar.pts),
        homeLabel: home,
        awayLabel: away,
      }
    }).filter((d, i) => i === 0 || d.homeStrength > 0 || d.awayStrength > 0)
  }, [data])

  if (loading) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-5xl">
        <div className="text-center py-12">
          <div className="text-on-surface-variant">Loading game analysis...</div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-5xl">
        <div className="text-center py-12">
          <div className="text-red-600 dark:text-red-400 mb-4">{error || 'Prediction not found'}</div>
          <Link to="/" className="text-blue-600 dark:text-blue-400 hover:underline">Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  const winPct = data.predicted_winner === data.home ? data.win_probability_home : data.win_probability_away
  const outlook = data.outlook_extended || data.outlook_summary || ''
  const homeName = data.home_full_name || data.home
  const awayName = data.away_full_name || data.away

  return (
    <div className="container mx-auto px-3 md:px-4 max-w-5xl pb-8">
      <nav className="mt-3 text-xs text-on-surface-variant">
        <Link to="/" className="hover:text-primary-container">Home</Link>
        <span className="mx-1">/</span>
        <span className="text-on-surface-variant font-medium">Game prediction</span>
      </nav>

      {data._incomplete && (
        <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-on-surface">
          <p className="m-0">
            Some data is still loading. Refresh in a few seconds for complete stats.
          </p>
          <button
            type="button"
            onClick={() => setRefreshNonce((n) => n + 1)}
            className="shrink-0 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 dark:bg-amber-700 dark:hover:bg-amber-600"
          >
            Refresh now
          </button>
        </div>
      )}

      {/* Header: matchup + predicted winner */}
      <div className="mt-4 rounded bg-surface-container border border-outline/20 shadow-sm overflow-hidden">
        <div className="p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 mb-4">
            <div className="flex flex-col items-center gap-1">
              <img src={teamLogoUrl(data.away)} alt={data.away} className="h-14 w-14 object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
              <span className="text-xs text-on-surface-variant">Away</span>
            </div>
            <span className="text-lg font-bold text-on-surface-variant">@</span>
            <div className="flex flex-col items-center gap-1">
              <img src={teamLogoUrl(data.home)} alt={data.home} className="h-14 w-14 object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
              <span className="text-xs text-on-surface-variant">Home</span>
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black uppercase italic tracking-tighter text-center text-on-surface">
            {awayName} vs {homeName}
          </h1>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-3">
            <span className="px-3 py-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 font-semibold">
              Predicted winner: {data.predicted_winner_name || data.predicted_winner}
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-surface-container-high text-on-surface font-bold">
              Win probability: {Math.round(winPct)}%
            </span>
          </div>
          {data.key_advantage_summary && (
            <p className="mt-2 text-sm text-on-surface-variant text-center">
              Key advantage: {data.key_advantage_summary}
            </p>
          )}
        </div>
      </div>

      {/* Game outlook */}
      {outlook && (
        <section className="mt-6 rounded bg-surface-container border border-outline/20 shadow-sm p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-on-surface mb-2">Game outlook</h2>
          <p className="text-sm text-on-surface-variant leading-relaxed">{outlook}</p>
        </section>
      )}

      {/* Team comparison */}
      <section className="mt-6 rounded bg-surface-container border border-outline/20 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-on-surface mb-1">Team comparison</h2>
        <p className="text-xs text-on-surface-variant mb-4">
          Strength = 31 − league rank (higher is better). Pace = estimated possessions per game.
          {data._incomplete && (
            <span className="block mt-1 text-amber-800 dark:text-amber-200/90">
              Full defensive data may still be loading — charts show partial ranks where available.
            </span>
          )}
        </p>
        {comparisonBarData.length > 0 ? (
          <>
            <div className="h-80 sm:h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparisonBarData} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="metric" width={150} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value: number) => [value.toFixed(1), '']} />
                  <Legend />
                  <Bar dataKey="home" name={homeName} fill="#10b981" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="away" name={awayName} fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {/* Quick stats table */}
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low">
                    <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Metric</th>
                    <th className="py-1.5 px-2 font-semibold text-emerald-700 dark:text-emerald-300 text-right">{homeName}</th>
                    <th className="py-1.5 px-2 font-semibold text-indigo-700 dark:text-indigo-300 text-right">{awayName}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: 'Off. PTS rank', h: rankLabel(data.home_off_full?.pts), a: rankLabel(data.away_off_full?.pts) },
                    { label: 'Off. AST rank', h: rankLabel(data.home_off_full?.ast), a: rankLabel(data.away_off_full?.ast) },
                    { label: 'Def. PTS rank', h: rankLabel(data.home_def_full?.pts), a: rankLabel(data.away_def_full?.pts) },
                    { label: 'Def. REB rank', h: rankLabel(data.home_def_full?.reb), a: rankLabel(data.away_def_full?.reb) },
                    { label: 'Pace rank', h: rankLabel(data.home_pace_data?.pace_rank), a: rankLabel(data.away_pace_data?.pace_rank) },
                    { label: 'Possessions/g', h: data.home_pace_data?.possessions?.toFixed(1) ?? '—', a: data.away_pace_data?.possessions?.toFixed(1) ?? '—' },
                    { label: 'PPG', h: data.home_ppg?.toFixed(1) ?? '—', a: data.away_ppg?.toFixed(1) ?? '—' },
                  ].map((row) => (
                    <tr key={row.label} className="border-t border-outline/20">
                      <td className="py-1.5 px-2 text-on-surface-variant">{row.label}</td>
                      <td className="py-1.5 px-2 text-right font-medium text-on-surface">{row.h}</td>
                      <td className="py-1.5 px-2 text-right font-medium text-on-surface">{row.a}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-on-surface-variant">No comparison data available.</p>
        )}
      </section>

      {/* Radar (1+ strength metrics) */}
      {radarData.length >= 1 && (
        <section className="mt-6 rounded bg-surface-container border border-outline/20 shadow-sm p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-on-surface mb-4">Strength radar</h2>
          <div className="h-72 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10 }} />
                <PolarRadiusAxis tick={{ fontSize: 9 }} domain={[0, NUM_TEAMS]} />
                <Radar name={homeName} dataKey={homeName} stroke="#10b981" fill="#10b981" fillOpacity={0.35} />
                <Radar name={awayName} dataKey={awayName} stroke="#6366f1" fill="#6366f1" fillOpacity={0.35} />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* Defensive matchup insights */}
      <section className="mt-6 rounded bg-surface-container border border-outline/20 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-on-surface mb-1">Defensive matchup insights</h2>
        <p className="text-xs text-on-surface-variant mb-4">
          League defensive rank per category — lower rank (#1) = best defense (allows fewest).
        </p>
        {defMatchupData.length > 0 ? (
          <>
            <div className="h-52 sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={defMatchupData} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
                  <XAxis type="number" domain={[0, NUM_TEAMS]} tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="stat" width={100} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value: number) => [`#${value} (${value <= 10 ? 'elite' : value <= 20 ? 'avg' : 'poor'})`, '']} />
                  <Legend />
                  <Bar dataKey="home" name={homeName} fill="#10b981" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="away" name={awayName} fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {/* Position defense table */}
            {posDefData.length > 0 && (
              <div className="mt-5">
                <h3 className="text-sm font-semibold text-on-surface mb-2">Points allowed by position (def rank — lower = better)</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-container-low">
                        <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Position</th>
                        <th className="py-1.5 px-2 font-semibold text-emerald-700 dark:text-emerald-300 text-right">{homeName}</th>
                        <th className="py-1.5 px-2 font-semibold text-indigo-700 dark:text-indigo-300 text-right">{awayName}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {posDefData.map((row) => {
                        const homeBetter = (row.homeRank ?? 99) < (row.awayRank ?? 99)
                        return (
                          <tr key={row.pos} className="border-t border-outline/20">
                            <td className="py-1.5 px-2 font-medium text-on-surface-variant">{row.pos}</td>
                            <td className={`py-1.5 px-2 text-right font-semibold ${homeBetter ? 'text-emerald-700 dark:text-emerald-300' : 'text-on-surface-variant'}`}>
                              {rankLabel(row.homeRank)}
                            </td>
                            <td className={`py-1.5 px-2 text-right font-semibold ${!homeBetter ? 'text-emerald-700 dark:text-emerald-300' : 'text-on-surface-variant'}`}>
                              {rankLabel(row.awayRank)}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-on-surface-variant">Defensive rank data not yet available. Run the morning cache warm to compute ranks.</p>
        )}
      </section>

      {/* Player impact */}
      <section className="mt-6 rounded bg-surface-container border border-outline/20 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-on-surface mb-1">Player impact</h2>
        <p className="text-xs text-on-surface-variant mb-4">Top players by scoring avg. Last 5 = average over last 5 games.</p>
        {(data.home_key_players?.length || data.away_key_players?.length) ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { label: homeName, players: data.home_key_players || [], color: 'emerald' },
              { label: awayName, players: data.away_key_players || [], color: 'indigo' },
            ].map(({ label, players, color }) => (
              <div key={label}>
                <h3 className={`text-sm font-semibold mb-2 ${color === 'emerald' ? 'text-emerald-700 dark:text-emerald-300' : 'text-indigo-700 dark:text-indigo-300'}`}>
                  {label}
                </h3>
                {players.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left border-collapse">
                      <thead>
                        <tr className="bg-surface-container-low">
                          <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Player</th>
                          <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Avg PTS</th>
                          <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Avg REB</th>
                          <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Avg AST</th>
                          <th className="py-1.5 px-2 text-right font-semibold text-blue-600 dark:text-blue-400">L5 PTS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {players.map((p) => (
                          <tr key={p.id} className="border-t border-outline/20">
                            <td className="py-1.5 px-2">
                              <div className="font-medium text-on-surface">{p.name}</div>
                              <div className="text-on-surface-variant">{p.position || '—'} · {p.avg_min != null ? `${p.avg_min} mpg` : ''}</div>
                            </td>
                            <td className="py-1.5 px-2 text-right text-on-surface">{p.season_pts ?? '—'}</td>
                            <td className="py-1.5 px-2 text-right text-on-surface">{p.season_reb ?? '—'}</td>
                            <td className="py-1.5 px-2 text-right text-on-surface">{p.season_ast ?? '—'}</td>
                            <td className={`py-1.5 px-2 text-right font-bold ${(p.last5_pts ?? 0) > (p.season_pts ?? 0) ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                              {p.last5_pts ?? '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-on-surface-variant">No player data available.</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-on-surface-variant">Player data not yet cached. Run the morning warm to load player game logs.</p>
        )}
      </section>

      {/* Historical matchup */}
      <section className="mt-6 rounded bg-surface-container border border-outline/20 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-on-surface mb-1">Historical matchup</h2>
        {data.h2h_games && data.h2h_games.length > 0 ? (
          <>
            <div className="flex gap-6 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{data.h2h_wins_home ?? 0}</div>
                <div className="text-xs text-on-surface-variant">{homeName} wins</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-on-surface-variant">–</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-700 dark:text-indigo-300">{data.h2h_wins_away ?? 0}</div>
                <div className="text-xs text-on-surface-variant">{awayName} wins</div>
              </div>
              <div className="text-xs text-on-surface-variant self-center ml-2">(last {data.h2h_games.length} meetings)</div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low">
                    <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Date</th>
                    <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Matchup</th>
                    <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Score</th>
                    <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Winner</th>
                  </tr>
                </thead>
                <tbody>
                  {data.h2h_games.map((g, i) => (
                    <tr key={i} className="border-t border-outline/20">
                      <td className="py-1.5 px-2 text-on-surface-variant">{g.date}</td>
                      <td className="py-1.5 px-2 text-on-surface-variant">{g.away} @ {g.home}</td>
                      <td className="py-1.5 px-2 text-right font-medium text-on-surface">
                        {g.home_score} – {g.away_score}
                      </td>
                      <td className={`py-1.5 px-2 text-right font-semibold ${g.winner === data.home ? 'text-emerald-600 dark:text-emerald-400' : 'text-indigo-600 dark:text-indigo-400'}`}>
                        {g.winner}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-on-surface-variant">No recent matchup history found for this season.</p>
        )}
      </section>

      <div className="mt-6 text-center">
        <Link to="/" className="text-sm font-medium text-emerald-600 dark:text-emerald-400 hover:underline">← Back to Dashboard</Link>
      </div>
    </div>
  )
}
