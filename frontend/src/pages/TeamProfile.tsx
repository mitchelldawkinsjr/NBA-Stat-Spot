import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'
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
/** Convert rank (1=best) to "strength" (higher = better) for charting */
function rankToStrength(rank: number | null): number {
  if (rank == null) return 0
  return Math.max(0, NUM_TEAMS + 1 - rank)
}

type Team = {
  id: number
  full_name: string
  abbreviation: string
  city: string
  nickname: string
  conference?: string
  division?: string
}

type Player = {
  id: number
  name: string
  position?: string
  jersey_number?: string
}

type TeamStatsRanks = {
  def_rank_pts: number | null
  def_rank_reb: number | null
  def_rank_ast: number | null
  def_rank_3pm: number | null
  off_rank_pts: number | null
  off_rank_reb: number | null
  off_rank_ast: number | null
  off_rank_3pm: number | null
  pace_rank: number | null
  possessions_per_game: number | null
}

export default function TeamProfile() {
  const { id } = useParams()
  const { season } = useSeason()
  const [team, setTeam] = useState<Team | null>(null)
  const [roster, setRoster] = useState<Player[]>([])
  const [teamStats, setTeamStats] = useState<TeamStatsRanks | null>(null)
  const [teamStatsLoading, setTeamStatsLoading] = useState(true)
  const [teamStatsError, setTeamStatsError] = useState<boolean>(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTeam = async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
        const res = await apiFetch(`api/v1/teams/${id}`)
        if (!res.ok) {
          if (res.status === 404) {
            setError('Team not found')
          } else {
            setError('Failed to load team')
          }
          return
        }
        const data = await res.json()
        setTeam(data.team)
        setRoster(data.roster || [])
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Error loading team')
      } finally {
        setLoading(false)
      }
    }
    fetchTeam()
  }, [id])

  useEffect(() => {
    let cancelled = false
    const seasonToTry = season || '2025-26'

    const fetchTeamStats = async (retry = 0) => {
      if (!id) return
      setTeamStatsLoading(true)
      setTeamStatsError(false)
      try {
        const res = await apiFetch(`api/v1/teams/team-stats/ranks?season=${encodeURIComponent(seasonToTry)}`)
        if (cancelled) return
        if (!res.ok) {
          if (retry < 1) {
            setTimeout(() => fetchTeamStats(retry + 1), 1500)
            return
          }
          setTeamStatsError(true)
          setTeamStatsLoading(false)
          return
        }
        const data = await res.json()
        const item = (data.items || []).find((t: { id: number }) => Number(t.id) === Number(id))
        if (cancelled) return
        if (item) {
          setTeamStats({
            def_rank_pts: item.def_rank_pts ?? null,
            def_rank_reb: item.def_rank_reb ?? null,
            def_rank_ast: item.def_rank_ast ?? null,
            def_rank_3pm: item.def_rank_3pm ?? null,
            off_rank_pts: item.off_rank_pts ?? null,
            off_rank_reb: item.off_rank_reb ?? null,
            off_rank_ast: item.off_rank_ast ?? null,
            off_rank_3pm: item.off_rank_3pm ?? null,
            pace_rank: item.pace_rank ?? null,
            possessions_per_game: item.possessions_per_game ?? null,
          })
        }
      } catch {
        if (cancelled) return
        if (retry < 1) setTimeout(() => fetchTeamStats(retry + 1), 1500)
        else setTeamStatsError(true)
      } finally {
        if (!cancelled) setTeamStatsLoading(false)
      }
    }
    fetchTeamStats()
    return () => { cancelled = true }
  }, [id, season])

  const chartData = useMemo(() => {
    if (!teamStats) return []
    return [
      { stat: 'PTS', defense: rankToStrength(teamStats.def_rank_pts), offense: rankToStrength(teamStats.off_rank_pts), defRank: teamStats.def_rank_pts, offRank: teamStats.off_rank_pts },
      { stat: 'REB', defense: rankToStrength(teamStats.def_rank_reb), offense: rankToStrength(teamStats.off_rank_reb), defRank: teamStats.def_rank_reb, offRank: teamStats.off_rank_reb },
      { stat: 'AST', defense: rankToStrength(teamStats.def_rank_ast), offense: rankToStrength(teamStats.off_rank_ast), defRank: teamStats.def_rank_ast, offRank: teamStats.off_rank_ast },
      { stat: '3PM', defense: rankToStrength(teamStats.def_rank_3pm), offense: rankToStrength(teamStats.off_rank_3pm), defRank: teamStats.def_rank_3pm, offRank: teamStats.off_rank_3pm },
    ].filter((d) => d.defense > 0 || d.offense > 0)
  }, [teamStats])

  const radarData = useMemo(() => {
    if (!chartData.length) return []
    return chartData.map((d) => ({
      subject: d.stat,
      Defense: d.defense,
      Offense: d.offense,
      fullMark: NUM_TEAMS,
    }))
  }, [chartData])

  if (loading) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-7xl">
        <div className="text-center py-12">
          <div className="text-on-surface-variant transition-colors duration-200">Loading team...</div>
        </div>
      </div>
    )
  }

  if (error || !team) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-7xl">
        <div className="text-center py-12">
          <div className="text-red-600 dark:text-red-400 mb-4 transition-colors duration-200">{error || 'Team not found'}</div>
          <Link to="/explore" className="text-blue-600 dark:text-blue-400 hover:underline transition-colors duration-200">
            Return to Explore
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-3 md:px-4 max-w-7xl">
      {/* Breadcrumbs */}
      <nav className="relative z-10 mt-3" aria-label="Breadcrumb">
        <ol className="min-w-0 flex items-center gap-1 text-xs text-on-surface-variant overflow-hidden transition-colors duration-200">
          <li>
            <Link to="/" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-200">Home</Link>
          </li>
          <li aria-hidden="true" className="px-1">/</li>
          <li>
            <Link to="/explore" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-200">Explore</Link>
          </li>
          <li aria-hidden="true" className="px-1">/</li>
          <li className="flex-1 min-w-0 text-gray-700 dark:text-gray-300 font-medium truncate transition-colors duration-200">{team.full_name}</li>
        </ol>
      </nav>

      {/* Team Header */}
      <div className="relative overflow-hidden rounded-2xl bg-surface-container shadow-xl ring-1 ring-gray-200 dark:ring-slate-700 mt-3 mb-6 transition-colors duration-200">
        <div className="px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-on-surface mb-2 transition-colors duration-200">{team.full_name}</h1>
              {team.conference && (
                <div className="flex items-center gap-4 text-sm text-on-surface-variant transition-colors duration-200">
                  <span>{team.conference}</span>
                  {team.division && (
                    <>
                      <span>•</span>
                      <span>{team.division}</span>
                    </>
                  )}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-400 dark:text-gray-500 transition-colors duration-200">{team.abbreviation}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Team Stats (Defense & Offense Ranks) — loading, empty tip, and content */}
      {teamStatsLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 animate-pulse">
            <div className="h-5 bg-gray-200 dark:bg-surface-container-highest rounded w-32 mb-3" />
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-10 bg-gray-100 dark:bg-surface-container-high rounded-lg" />
              ))}
            </div>
          </div>
          <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 animate-pulse">
            <div className="h-5 bg-gray-200 dark:bg-surface-container-highest rounded w-28 mb-3" />
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-10 bg-gray-100 dark:bg-surface-container-high rounded-lg" />
              ))}
            </div>
          </div>
        </div>
      )}
      {!teamStatsLoading && (teamStatsError || !teamStats || (!teamStats.def_rank_pts && !teamStats.off_rank_pts)) && (
        <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">Defense &amp; offense ranks did not load</p>
          <p className="text-sm text-amber-800/90 dark:text-amber-200/90">
            The server has no cached rank data for <strong>{season || '2025-26'}</strong>. In <strong>Admin</strong> → Cache &amp; Data, run <strong>Refresh defensive ranks</strong> and <strong>Refresh offensive ranks</strong> for this season. After the jobs finish, reload this page.
          </p>
        </div>
      )}
      {!teamStatsLoading && teamStats && (teamStats.def_rank_pts != null || teamStats.off_rank_pts != null) && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-on-surface mb-3 transition-colors duration-200">Defense Ranks</h2>
              <p className="text-xs text-on-surface-variant mb-3 transition-colors duration-200">Lower rank = better defense (fewer points/stats allowed)</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'PTS', value: teamStats.def_rank_pts },
                  { label: 'REB', value: teamStats.def_rank_reb },
                  { label: 'AST', value: teamStats.def_rank_ast },
                  { label: '3PM', value: teamStats.def_rank_3pm },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-surface-container-high/50 rounded-lg">
                    <span className="text-sm text-on-surface-variant">{label}</span>
                    <span className="font-bold text-gray-900 dark:text-on-surface">{value != null ? `#${value}` : '—'}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-on-surface mb-3 transition-colors duration-200">Offense Ranks</h2>
              <p className="text-xs text-on-surface-variant mb-3 transition-colors duration-200">Rank 1 = best (most points/stats scored)</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'PTS', value: teamStats.off_rank_pts },
                  { label: 'REB', value: teamStats.off_rank_reb },
                  { label: 'AST', value: teamStats.off_rank_ast },
                  { label: '3PM', value: teamStats.off_rank_3pm },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-surface-container-high/50 rounded-lg">
                    <span className="text-sm text-on-surface-variant">{label}</span>
                    <span className="font-bold text-gray-900 dark:text-on-surface">{value != null ? `#${value}` : '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Pace Card */}
          {(teamStats.pace_rank != null || teamStats.possessions_per_game != null) && (
            <div className="mb-4 bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-on-surface mb-1 transition-colors duration-200">Pace of Play</h2>
              <p className="text-xs text-on-surface-variant mb-3 transition-colors duration-200">Possessions per game — rank 1 = fastest pace</p>
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-on-surface transition-colors duration-200">
                    {teamStats.possessions_per_game != null ? teamStats.possessions_per_game.toFixed(1) : '—'}
                  </div>
                  <div className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">Possessions/game</div>
                </div>
                <div>
                  <div className={`text-3xl font-bold transition-colors duration-200 ${teamStats.pace_rank != null && teamStats.pace_rank <= 5 ? 'text-orange-500 dark:text-orange-400' : teamStats.pace_rank != null && teamStats.pace_rank >= 26 ? 'text-blue-500 dark:text-blue-400' : 'text-gray-900 dark:text-on-surface'}`}>
                    {teamStats.pace_rank != null ? `#${teamStats.pace_rank}` : '—'}
                  </div>
                  <div className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">Pace rank</div>
                </div>
                {teamStats.pace_rank != null && (
                  <div className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors duration-200 ${teamStats.pace_rank <= 5 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' : teamStats.pace_rank <= 15 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}`}>
                    {teamStats.pace_rank <= 5 ? '🔥 Fast pace — favors counting stats' : teamStats.pace_rank <= 15 ? 'Average pace' : '🐢 Slow pace — fewer possessions'}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Insight bullets from ranks */}
          {(() => {
            const d = teamStats
            const insights: string[] = []
            if (d.def_rank_pts != null && d.def_rank_pts <= 8) insights.push(`Elite at limiting points (#${d.def_rank_pts} defense)`)
            if (d.def_rank_pts != null && d.def_rank_pts >= 23) insights.push(`Weak vs points (#${d.def_rank_pts} — prop-friendly for PTS)`)
            if (d.def_rank_3pm != null && d.def_rank_3pm >= 23) insights.push(`Allows a lot of 3PM (#${d.def_rank_3pm}) — 3PT over opportunity`)
            if (d.def_rank_reb != null && d.def_rank_reb <= 8) insights.push(`Strong on the glass defensively (#${d.def_rank_reb})`)
            if (d.off_rank_pts != null && d.off_rank_pts <= 5) insights.push(`Top-tier scoring offense (#${d.off_rank_pts})`)
            if (d.off_rank_pts != null && d.off_rank_pts >= 25) insights.push(`Low-scoring offense (#${d.off_rank_pts})`)
            if (d.pace_rank != null && d.pace_rank <= 5) insights.push(`Top-5 fastest pace — boosts all counting stats`)
            if (d.pace_rank != null && d.pace_rank >= 26) insights.push(`Bottom-5 pace — fewer possessions, consider unders`)
            if (insights.length === 0) return null
            return (
              <div className="mb-6 p-4 rounded-xl bg-slate-50 dark:bg-surface-container/80 ring-1 ring-slate-200 dark:ring-slate-600">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-on-surface mb-2">Insights</h3>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 dark:text-on-surface-variant">
                  {insights.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )
          })()}
        </>
      )}

      {/* Charts: Defense vs Offense comparison */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-on-surface mb-1 transition-colors duration-200">Defense vs Offense by stat</h2>
            <p className="text-xs text-on-surface-variant mb-4 transition-colors duration-200">Bar height = strength (rank 1 is best). Compare where this team excels.</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <XAxis dataKey="stat" tick={{ fill: 'currentColor', fontSize: 12 }} stroke="#94a3b8" />
                  <YAxis domain={[0, NUM_TEAMS]} tick={{ fill: 'currentColor', fontSize: 11 }} stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'var(--tw-bg-opacity, 1)', borderRadius: 8 }}
                    formatter={(value: number, name: string, item: unknown) => {
                      const payload = (item as { payload?: { defRank?: number; offRank?: number } })?.payload
                      const rank = name === 'Defense' ? payload?.defRank : payload?.offRank
                      return [rank != null ? `Rank #${rank} of 30` : `Strength ${value}`, name]
                    }}
                    labelFormatter={(label) => label}
                  />
                  <Legend />
                  <Bar dataKey="defense" name="Defense (allows)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="offense" name="Offense (scores)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-on-surface mb-1 transition-colors duration-200">Profile shape</h2>
            <p className="text-xs text-on-surface-variant mb-4 transition-colors duration-200">Same ranks as bars — shape shows balance across PTS, REB, AST, 3PM.</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} margin={{ top: 16, right: 16, bottom: 16, left: 16 }}>
                  <PolarGrid stroke="#64748b" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'currentColor', fontSize: 12 }} />
                  <PolarRadiusAxis angle={90} domain={[0, NUM_TEAMS]} tick={{ fill: 'currentColor', fontSize: 10 }} />
                  <Radar name="Defense" dataKey="Defense" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} strokeWidth={2} />
                  <Radar name="Offense" dataKey="Offense" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.4} strokeWidth={2} />
                  <Legend />
                  <Tooltip formatter={(value: number) => [`Rank strength ${value}`, '']} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Roster Section */}
      <div className="bg-surface-container rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-6 transition-colors duration-200">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-on-surface transition-colors duration-200">Roster</h2>
          <div className="text-sm text-on-surface-variant transition-colors duration-200">{roster.length} players</div>
        </div>
        {roster.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {roster.map((player) => (
              <Link
                key={player.id}
                to={`/player/${player.id}`}
                className="p-4 bg-gray-50 dark:bg-surface-container-high border border-gray-200 dark:border-slate-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900 dark:text-on-surface group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {player.name}
                    </div>
                    {player.position && (
                      <div className="text-xs text-on-surface-variant mt-1 transition-colors duration-200">{player.position}</div>
                    )}
                  </div>
                  {player.jersey_number && (
                    <div className="text-2xl font-bold text-gray-300 dark:text-gray-600 ml-3 transition-colors duration-200">#{player.jersey_number}</div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-on-surface-variant transition-colors duration-200">No players found</div>
        )}
      </div>
    </div>
  )
}

