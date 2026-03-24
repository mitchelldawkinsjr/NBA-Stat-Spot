import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { apiFetch } from '../utils/api'

type GameRecord = {
  date: string
  game_id: string
  matchup: string
  predicted_winner: string
  actual_winner: string | null
  home_score: number | null
  away_score: number | null
  correct: boolean | null
  status: 'pending' | 'graded'
  confidence_pct?: number | null
  insight_summary?: string | null
}

type PickRecord = {
  date: string
  player_name: string
  stat_type: string
  line_value: number
  suggestion: string
  actual_value: number | null
  hit: boolean | null
  push: boolean | null
  confidence: number | null
  status?: 'graded' | 'pending'
}

type AccuracyResponse = {
  from_date: string
  to_date: string
  model_version?: string | null
  combined_accuracy?: {
    accuracy_pct: number | null
    correct: number
    total: number
    game_settled?: number
    ai_pick_graded_non_push?: number
  }
  game_predictions: {
    total: number
    total_settled?: number
    correct: number
    incorrect?: number
    pending?: number
    accuracy_pct: number | null
    records: GameRecord[]
  }
  pick_of_the_day: {
    total: number
    settled?: number
    pending?: number
    hits: number
    misses: number
    pushes: number
    hit_rate_pct: number | null
    mae?: number | null
    rmse?: number | null
    win_rate?: number | null
    records: PickRecord[]
  }
}

export default function AccuracyPage() {
  const [data, setData] = useState<AccuracyResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await apiFetch(`api/v1/accuracy/history?days=${days}`)
        if (cancelled) return
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          setError((body as { detail?: string }).detail || 'Failed to load accuracy history')
          return
        }
        const json = await res.json()
        setData(json)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error loading accuracy')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [days])

  return (
    <div className="container mx-auto px-3 md:px-4 max-w-5xl pb-8">
      <nav className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        <Link to="/" className="hover:text-gray-700 dark:hover:text-gray-300">Home</Link>
        <span className="mx-1">/</span>
        <span className="text-gray-700 dark:text-gray-300 font-medium">Prediction accuracy</span>
      </nav>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-slate-100">
          Prediction accuracy
        </h1>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-400">Last</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Match predictions are saved when game predictions are cached. AI pick of the day is saved when the pick is first loaded (cache miss) or when Admin warms the dashboard. Run <strong>Settle accuracy</strong> in Admin after games to grade both (or use the daily cron).
      </p>

      {loading && (
        <div className="mt-6 text-center py-8 text-gray-500 dark:text-gray-400">Loading…</div>
      )}
      {error && (
        <div className="mt-6 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          {data.model_version && (
            <div className="mt-4 rounded-lg bg-slate-100 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 px-3 py-2 text-sm text-slate-700 dark:text-slate-300">
              <span className="font-medium">ML model version:</span> <code className="text-xs">{data.model_version}</code>
              <span className="ml-2 text-slate-500 dark:text-slate-400">(last retrain)</span>
            </div>
          )}
          {/* Summary cards: matches, AI pick, combined */}
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1">Match predictions</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Game winner: predicted vs actual (settled games only)</p>
              {data.game_predictions.total === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No games recorded in this range.</p>
              ) : (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-gray-900 dark:text-slate-100">
                      {data.game_predictions.total_settled ? (data.game_predictions.accuracy_pct ?? '—') : '—'}
                      {data.game_predictions.total_settled ? '%' : ''}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {data.game_predictions.total_settled ? 'accuracy' : 'no settled yet'}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600 dark:text-gray-400">
                    <span>Recorded: <strong className="text-gray-900 dark:text-slate-100">{data.game_predictions.total}</strong></span>
                    <span>Settled: <strong className="text-gray-900 dark:text-slate-100">{data.game_predictions.total_settled ?? 0}</strong></span>
                    <span>Correct: <strong className="text-emerald-600 dark:text-emerald-400">{data.game_predictions.correct}</strong></span>
                    <span>Wrong: <strong className="text-rose-600 dark:text-rose-400">{data.game_predictions.incorrect ?? 0}</strong></span>
                    <span className="col-span-2">Pending: <strong className="text-amber-600 dark:text-amber-400">{data.game_predictions.pending ?? 0}</strong></span>
                  </div>
                </>
              )}
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1">AI pick of the day</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Prop O/U vs actual (pushes excluded from win rate)</p>
              {data.pick_of_the_day.total === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">No picks recorded in this range. Open the dashboard or warm cache so picks are saved.</p>
              ) : (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-gray-900 dark:text-slate-100">
                      {(data.pick_of_the_day.settled ?? 0) > 0 && (data.pick_of_the_day.hits + data.pick_of_the_day.misses) > 0
                        ? (data.pick_of_the_day.hit_rate_pct ?? '—')
                        : '—'}
                      {(data.pick_of_the_day.settled ?? 0) > 0 && (data.pick_of_the_day.hits + data.pick_of_the_day.misses) > 0 ? '%' : ''}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {(data.pick_of_the_day.settled ?? 0) > 0 && (data.pick_of_the_day.hits + data.pick_of_the_day.misses) > 0
                        ? `${data.pick_of_the_day.hits}W – ${data.pick_of_the_day.misses}L`
                        : 'awaiting grade'}
                      {data.pick_of_the_day.pushes > 0 && ` (${data.pick_of_the_day.pushes} push)`}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                    <span>Recorded: <strong className="text-gray-900 dark:text-slate-100">{data.pick_of_the_day.total}</strong></span>
                    <span className="mx-2">·</span>
                    <span>Settled: <strong className="text-gray-900 dark:text-slate-100">{data.pick_of_the_day.settled ?? 0}</strong></span>
                    <span className="mx-2">·</span>
                    <span>Pending: <strong className="text-amber-600 dark:text-amber-400">{data.pick_of_the_day.pending ?? 0}</strong></span>
                  </div>
                  {(data.pick_of_the_day.mae != null || data.pick_of_the_day.rmse != null) && (
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      MAE: <strong className="text-gray-700 dark:text-slate-300">{data.pick_of_the_day.mae ?? '—'}</strong>
                      {' · '}
                      RMSE: <strong className="text-gray-700 dark:text-slate-300">{data.pick_of_the_day.rmse ?? '—'}</strong>
                    </div>
                  )}
                </>
              )}
            </div>
            <div className="rounded-xl bg-white dark:bg-slate-800 border border-violet-200 dark:border-violet-800/50 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-1">Combined</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Every settled match + every graded AI pick (non-push) counts as one trial</p>
              {data.combined_accuracy && data.combined_accuracy.total > 0 ? (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-violet-700 dark:text-violet-300">
                      {data.combined_accuracy.accuracy_pct ?? 0}%
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {data.combined_accuracy.correct} / {data.combined_accuracy.total} correct
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                    Matches: <strong>{data.combined_accuracy.game_settled ?? 0}</strong> graded
                    <span className="mx-2">·</span>
                    AI props: <strong>{data.combined_accuracy.ai_pick_graded_non_push ?? 0}</strong> graded (excl. push)
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">No combined trials yet (need at least one settled match or graded pick).</p>
              )}
            </div>
          </div>

          {/* Win rate by stat type (Pick of the day) */}
          {data.pick_of_the_day.records.length > 0 && (() => {
            const byStat: Record<string, { hits: number; total: number }> = {}
            for (const r of data.pick_of_the_day.records) {
              if (r.status === 'pending' || r.push) continue
              const st = r.stat_type || 'PTS'
              if (!byStat[st]) byStat[st] = { hits: 0, total: 0 }
              byStat[st].total += 1
              if (r.hit) byStat[st].hits += 1
            }
            const chartData = Object.entries(byStat).map(([stat, v]) => ({ stat, winRate: v.total ? Math.round(100 * v.hits / v.total) : 0, hits: v.hits, total: v.total }))
            if (chartData.length === 0) return null
            return (
              <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-3">Win rate by stat (pick of the day)</h2>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <XAxis dataKey="stat" tick={{ fontSize: 12 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                      <Tooltip formatter={(value: number) => [`${value}%`, 'Win rate']} labelFormatter={(label) => `Stat: ${label}`} />
                      <Bar dataKey="winRate" fill="rgb(34 197 94)" name="Win rate" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            )
          })()}

          {/* Game prediction history table (recent prediction history) */}
          <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-3">Recent prediction history</h2>
            {data.game_predictions.records.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No records.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs sm:text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-slate-700">
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Date</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Matchup</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Predicted</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300 text-right">Conf.</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Actual</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300 text-right">Score</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.game_predictions.records.map((r, i) => (
                      <tr key={`${r.date}-${r.game_id}-${i}`} className="border-t border-gray-100 dark:border-slate-700">
                        <td className="py-1.5 px-2 text-gray-600 dark:text-gray-400">{r.date}</td>
                        <td className="py-1.5 px-2 font-medium text-gray-900 dark:text-slate-100">{r.matchup}</td>
                        <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{r.predicted_winner}</td>
                        <td className="py-1.5 px-2 text-right text-gray-500 dark:text-gray-400">{r.confidence_pct != null ? `${r.confidence_pct}%` : '—'}</td>
                        <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{r.actual_winner ?? '—'}</td>
                        <td className="py-1.5 px-2 text-right text-gray-600 dark:text-gray-400">{r.home_score != null && r.away_score != null ? `${r.home_score}–${r.away_score}` : '—'}</td>
                        <td className="py-1.5 px-2 text-center">
                          {r.status === 'pending' ? (
                            <span className="text-amber-600 dark:text-amber-400 font-medium">Pending</span>
                          ) : r.correct ? (
                            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Correct</span>
                          ) : (
                            <span className="text-rose-600 dark:text-rose-400 font-semibold">Incorrect</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Pick of the day history table */}
          <section className="mt-6 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 shadow-sm p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-3">AI pick of the day history</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              Rows appear when a pick is first generated for that date. <strong>Pending</strong> clears after Admin <strong>Settle accuracy</strong> for that date.
            </p>
            {data.pick_of_the_day.records.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No picks on file in this range.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs sm:text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-slate-700">
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Date</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Player</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Prop</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Line</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300">Actual</th>
                      <th className="py-2 px-2 font-semibold text-gray-600 dark:text-gray-300 text-center">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pick_of_the_day.records.map((r, i) => (
                      <tr key={`${r.date}-${r.player_name}-${i}`} className="border-t border-gray-100 dark:border-slate-700">
                        <td className="py-1.5 px-2 text-gray-600 dark:text-gray-400">{r.date}</td>
                        <td className="py-1.5 px-2 font-medium text-gray-900 dark:text-slate-100">{r.player_name}</td>
                        <td className="py-1.5 px-2 text-gray-700 dark:text-gray-300">{r.stat_type} {r.suggestion}</td>
                        <td className="py-1.5 px-2 text-gray-600 dark:text-gray-400">{r.line_value}</td>
                        <td className="py-1.5 px-2 text-gray-600 dark:text-gray-400">{r.actual_value ?? '—'}</td>
                        <td className="py-1.5 px-2 text-center">
                          {r.status === 'pending' || (r.actual_value == null && r.hit == null && !r.push) ? (
                            <span className="text-amber-600 dark:text-amber-400 font-medium">Pending</span>
                          ) : r.push ? (
                            <span className="text-amber-600 dark:text-amber-400 font-semibold">Push</span>
                          ) : r.hit ? (
                            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Hit</span>
                          ) : r.hit === false ? (
                            <span className="text-rose-600 dark:text-rose-400 font-semibold">Miss</span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
        <p>Match predictions and AI picks are saved when caches are warmed or when the pick-of-the-day endpoint runs (cache miss). Run <strong>Settle accuracy</strong> in Admin to grade a date (default: yesterday). A daily cron can run this automatically after games.</p>
      </div>
      <div className="mt-4">
        <Link to="/admin" className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline">Go to Admin</Link>
        <span className="mx-2">·</span>
        <Link to="/" className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline">Back to Dashboard</Link>
      </div>
    </div>
  )
}
