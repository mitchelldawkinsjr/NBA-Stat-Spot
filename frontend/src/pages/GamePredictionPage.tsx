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
function rankToStrength(rank: number | null): number {
  if (rank == null) return 0
  return Math.max(0, NUM_TEAMS + 1 - rank)
}

function teamLogoUrl(abbr: string): string {
  const a = (abbr || '').trim().toUpperCase()
  return a ? `https://a.espncdn.com/i/teamlogos/nba/500/${a}.png` : ''
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
}

export default function GamePredictionPage() {
  const { gameId } = useParams()
  const [data, setData] = useState<PredictionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!gameId) return
    let cancelled = false
    const run = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await apiFetch(`api/v1/games/predictions/${gameId}`)
        if (cancelled) return
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          setError((body as { error?: string }).error || 'Failed to load game prediction')
          return
        }
        const json = await res.json()
        if (json.error) {
          setError(json.error)
          return
        }
        setData(json)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error loading prediction')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [gameId])

  const comparisonBarData = useMemo(() => {
    if (!data) return []
    const home = data.home_full_name || data.home
    const away = data.away_full_name || data.away
    return [
      { metric: 'Offensive rank (strength)', home: rankToStrength(data.home_off_rank_pts ?? null), away: rankToStrength(data.away_off_rank_pts ?? null), homeLabel: home, awayLabel: away },
      { metric: 'Defensive rank (strength)', home: rankToStrength(data.home_def_rank_pts ?? null), away: rankToStrength(data.away_def_rank_pts ?? null), homeLabel: home, awayLabel: away },
      { metric: 'Pace', home: data.home_pace ?? 0, away: data.away_pace ?? 0, homeLabel: home, awayLabel: away },
      { metric: 'PPG', home: data.home_ppg ?? 0, away: data.away_ppg ?? 0, homeLabel: home, awayLabel: away },
    ].filter((d) => d.home > 0 || d.away > 0)
  }, [data])

  const radarData = useMemo(() => {
    if (!data || !comparisonBarData.length) return []
    const home = data.home_full_name || data.home
    const away = data.away_full_name || data.away
    return comparisonBarData.map((d) => ({
      subject: d.metric.replace(' (strength)', ''),
      [home]: d.home,
      [away]: d.away,
      fullMark: Math.max(30, Math.ceil(Math.max(d.home, d.away) * 1.2)),
    }))
  }, [data, comparisonBarData])

  if (loading) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-5xl">
        <div className="text-center py-12">
          <div className="text-gray-500 dark:text-gray-400">Loading game analysis...</div>
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

  return (
    <div className="container mx-auto px-3 md:px-4 max-w-5xl pb-8">
      <nav className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        <Link to="/" className="hover:text-gray-700 dark:hover:text-gray-300">Home</Link>
        <span className="mx-1">/</span>
        <span className="text-gray-700 dark:text-gray-300 font-medium">Game prediction</span>
      </nav>

      {/* Header: matchup + predicted winner */}
      <div className="mt-4 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 mb-4">
            <img src={teamLogoUrl(data.away)} alt={data.away} className="h-14 w-14 object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
            <span className="text-lg font-bold text-gray-700 dark:text-gray-300">@</span>
            <img src={teamLogoUrl(data.home)} alt={data.home} className="h-14 w-14 object-contain" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-center text-gray-900 dark:text-slate-100">
            {data.away_full_name || data.away} vs {data.home_full_name || data.home}
          </h1>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-3">
            <span className="px-3 py-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 font-semibold">
              Predicted winner: {data.predicted_winner_name || data.predicted_winner}
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-slate-200 font-bold">
              Win probability: {Math.round(winPct)}%
            </span>
          </div>
          {data.key_advantage_summary && (
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 text-center">
              Key advantage: {data.key_advantage_summary}
            </p>
          )}
        </div>
      </div>

      {/* Game outlook */}
      {outlook && (
        <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">Game outlook</h2>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{outlook}</p>
        </section>
      )}

      {/* Team comparison */}
      <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-4">Team comparison</h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Offensive/defensive strength: higher = better (derived from league rank). Pace and PPG are raw values.
        </p>
        {comparisonBarData.length > 0 ? (
          <div className="h-72 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonBarData} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="metric" width={140} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: number) => [value.toFixed(1), '']}
                  labelFormatter={(_, payload) => payload?.[0]?.payload?.metric}
                />
                <Legend />
                <Bar dataKey="home" name={data.home_full_name || data.home} fill="#10b981" radius={[0, 4, 4, 0]} />
                <Bar dataKey="away" name={data.away_full_name || data.away} fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">No comparison data available.</p>
        )}
      </section>

      {/* Radar (optional, when we have multiple dimensions) */}
      {radarData.length >= 3 && (
        <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-4">Strength radar</h2>
          <div className="h-72 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis tick={{ fontSize: 10 }} />
                <Radar name={data.home_full_name || data.home} dataKey={data.home_full_name || data.home} stroke="#10b981" fill="#10b981" fillOpacity={0.4} />
                <Radar name={data.away_full_name || data.away} dataKey={data.away_full_name || data.away} stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* Defensive matchup insights (placeholder) */}
      <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">Defensive matchup insights</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Points allowed by position, defensive efficiency by matchup, and opponent FG% by zone will be added as more data is integrated.
        </p>
      </section>

      {/* Player impact (placeholder) */}
      <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">Player impact</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Key player stats, usage trends, and last-5 performance will appear here in a future update.
        </p>
      </section>

      {/* Historical matchup (placeholder) */}
      <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-2">Historical matchup</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Last 5 meetings, average scoring margin, and head-to-head record will be added when historical data is available.
        </p>
      </section>

      <div className="mt-6 text-center">
        <Link to="/" className="text-sm font-medium text-emerald-600 dark:text-emerald-400 hover:underline">← Back to Dashboard</Link>
      </div>
    </div>
  )
}
