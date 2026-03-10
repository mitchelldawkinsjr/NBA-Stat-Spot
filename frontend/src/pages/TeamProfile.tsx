import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
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
}

export default function TeamProfile() {
  const { id } = useParams()
  const [team, setTeam] = useState<Team | null>(null)
  const [roster, setRoster] = useState<Player[]>([])
  const [teamStats, setTeamStats] = useState<TeamStatsRanks | null>(null)
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
    const fetchTeamStats = async () => {
      if (!id) return
      try {
        const res = await apiFetch('api/v1/teams/team-stats/ranks?season=2025-26')
        if (!res.ok) return
        const data = await res.json()
        const item = (data.items || []).find((t: { id: number }) => Number(t.id) === Number(id))
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
          })
        }
      } catch {
        // Non-blocking; team stats are optional
      }
    }
    fetchTeamStats()
  }, [id])

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
          <div className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Loading team...</div>
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
        <ol className="min-w-0 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 overflow-hidden transition-colors duration-200">
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
      <div className="relative overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-xl ring-1 ring-gray-200 dark:ring-slate-700 mt-3 mb-6 transition-colors duration-200">
        <div className="px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-slate-100 mb-2 transition-colors duration-200">{team.full_name}</h1>
              {team.conference && (
                <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">
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

      {/* Team Stats (Defense & Offense Ranks) */}
      {teamStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-3 transition-colors duration-200">Defense Ranks</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 transition-colors duration-200">Lower rank = better defense (fewer points/stats allowed)</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'PTS', value: teamStats.def_rank_pts },
                { label: 'REB', value: teamStats.def_rank_reb },
                { label: 'AST', value: teamStats.def_rank_ast },
                { label: '3PM', value: teamStats.def_rank_3pm },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                  <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
                  <span className="font-bold text-gray-900 dark:text-slate-100">{value != null ? `#${value}` : '—'}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-3 transition-colors duration-200">Offense Ranks</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 transition-colors duration-200">Rank 1 = best (most points/stats scored)</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'PTS', value: teamStats.off_rank_pts },
                { label: 'REB', value: teamStats.off_rank_reb },
                { label: 'AST', value: teamStats.off_rank_ast },
                { label: '3PM', value: teamStats.off_rank_3pm },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
                  <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
                  <span className="font-bold text-gray-900 dark:text-slate-100">{value != null ? `#${value}` : '—'}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Charts: Defense & Offense strength */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">Defense & Offense by stat</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4 transition-colors duration-200">Higher bar = better (rank 1 → strength 30)</p>
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
                      return [rank != null ? `Rank #${rank} (strength ${value})` : `Strength ${value}`, name]
                    }}
                    labelFormatter={(label) => `Stat: ${label}`}
                  />
                  <Legend />
                  <Bar dataKey="defense" name="Defense" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="offense" name="Offense" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-5 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">Defense vs Offense profile</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4 transition-colors duration-200">Shape comparison across PTS, REB, AST, 3PM</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} margin={{ top: 16, right: 16, bottom: 16, left: 16 }}>
                  <PolarGrid stroke="#64748b" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'currentColor', fontSize: 12 }} />
                  <PolarRadiusAxis angle={90} domain={[0, NUM_TEAMS]} tick={{ fill: 'currentColor', fontSize: 10 }} />
                  <Radar name="Defense" dataKey="Defense" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} strokeWidth={2} />
                  <Radar name="Offense" dataKey="Offense" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.4} strokeWidth={2} />
                  <Legend />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'var(--tw-bg-opacity, 1)', borderRadius: 8 }}
                    formatter={(value: number) => [`Strength ${value}`, '']}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Roster Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-6 transition-colors duration-200">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Roster</h2>
          <div className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">{roster.length} players</div>
        </div>
        {roster.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {roster.map((player) => (
              <Link
                key={player.id}
                to={`/player/${player.id}`}
                className="p-4 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {player.name}
                    </div>
                    {player.position && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors duration-200">{player.position}</div>
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
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">No players found</div>
        )}
      </div>
    </div>
  )
}

