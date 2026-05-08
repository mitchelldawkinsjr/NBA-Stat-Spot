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

type PropBucket = {
  hits: number
  misses: number
  pushes: number
  settled: number
  pending: number
  hit_rate_pct: number | null
  graded_non_push?: number
}

type TopPickRecordRow = {
  id: number
  date: string
  player_id: number
  player_name: string
  stat_type: string
  direction: string
  line_value: number
  confidence: number | null
  tier: string
  confidence_band: string
  actual_value: number | null
  error: number | null
  hit: boolean | null
  push: boolean
  status: string
}

type TopPicksBlock = {
  overall: PropBucket & { total?: number; lock_hit_rate_pct?: number | null }
  by_tier: Record<string, PropBucket>
  by_confidence_band: Record<string, PropBucket>
  by_stat: Record<string, PropBucket>
  by_direction: Record<string, PropBucket>
  tier_x_stat: Record<string, Record<string, PropBucket>>
  tier_x_direction: Record<string, Record<string, PropBucket>>
  records: TopPickRecordRow[]
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
  top_picks?: TopPicksBlock
}

type AccuracyTabId = 'match' | 'ai' | 'top' | 'combined'

const TIER_ORDER = ['lock', 'strong', 'lean'] as const
const BAND_ORDER = ['95-100', '90-94', '85-89', '80-84', '75-79', '70-74', '65-69', '<65', 'unknown'] as const

export default function AccuracyPage() {
  const [data, setData] = useState<AccuracyResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(7)
  const [tab, setTab] = useState<AccuracyTabId>('match')

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

  const tabBtnClass = (id: AccuracyTabId) =>
    `flex-1 min-w-[8rem] sm:min-w-0 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900 ${
      tab === id
        ? 'bg-blue-600 text-white shadow-sm'
        : 'bg-gray-100 dark:bg-surface-container-high/80 text-gray-700 dark:text-on-surface hover:bg-gray-200 dark:hover:bg-surface-container-highest'
    }`

  return (
    <div className="bg-background min-h-screen px-4 md:px-8 pb-8 max-w-5xl mx-auto">
      <div className="pt-6 flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-4xl font-black uppercase italic tracking-tighter text-on-surface">
            PREDICTION <span className="text-primary-container">ACCURACY</span>
          </h1>
          <p className="text-on-surface-variant text-sm mt-1">Performance ledger for all model predictions</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-on-surface-variant">Last</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-surface-container-high text-on-surface text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      <p className="mt-1 text-sm text-on-surface-variant">
        Match predictions are saved when game predictions are cached. AI pick of the day is saved when the pick is first loaded (cache miss) or when Admin warms the dashboard. Top Picks rows are saved when the homepage loads Top Picks (first request per day). Run <strong>Settle accuracy</strong> in Admin after games to grade matches, AI pick, and Top Picks (or use the daily cron).
      </p>

      {loading && (
        <div className="mt-6 text-center py-8 text-on-surface-variant">Loading…</div>
      )}
      {error && (
        <div className="mt-6 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          {data.model_version && (
            <div className="mt-4 rounded-lg bg-slate-100 dark:bg-surface-container-high/50 border border-slate-200 dark:border-slate-600 px-3 py-2 text-sm text-slate-700 dark:text-on-surface-variant">
              <span className="font-medium">ML model version:</span> <code className="text-xs">{data.model_version}</code>
              <span className="ml-2 text-slate-500 dark:text-slate-400">(last retrain)</span>
            </div>
          )}

          <div className="mt-6" role="tablist" aria-label="Accuracy by bet type">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                role="tab"
                id="accuracy-tab-match"
                aria-selected={tab === 'match'}
                aria-controls="accuracy-panel-match"
                onClick={() => setTab('match')}
                className={tabBtnClass('match')}
              >
                Match predictions
              </button>
              <button
                type="button"
                role="tab"
                id="accuracy-tab-ai"
                aria-selected={tab === 'ai'}
                aria-controls="accuracy-panel-ai"
                onClick={() => setTab('ai')}
                className={tabBtnClass('ai')}
              >
                AI pick of the day
              </button>
              <button
                type="button"
                role="tab"
                id="accuracy-tab-top"
                aria-selected={tab === 'top'}
                aria-controls="accuracy-panel-top"
                onClick={() => setTab('top')}
                className={tabBtnClass('top')}
              >
                Top Picks
              </button>
              <button
                type="button"
                role="tab"
                id="accuracy-tab-combined"
                aria-selected={tab === 'combined'}
                aria-controls="accuracy-panel-combined"
                onClick={() => setTab('combined')}
                className={tabBtnClass('combined')}
              >
                Combined
              </button>
            </div>
          </div>

          {/* —— Match predictions —— */}
          <div
            role="tabpanel"
            id="accuracy-panel-match"
            aria-labelledby="accuracy-tab-match"
            hidden={tab !== 'match'}
            className="mt-4 space-y-6"
          >
            <div className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-1">Match predictions</h2>
              <p className="text-xs text-on-surface-variant mb-3">Game winner: predicted vs actual (settled games only)</p>
              {data.game_predictions.total === 0 ? (
                <p className="text-sm text-on-surface-variant">No games recorded in this range.</p>
              ) : (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-on-surface">
                      {data.game_predictions.total_settled ? (data.game_predictions.accuracy_pct ?? '—') : '—'}
                      {data.game_predictions.total_settled ? '%' : ''}
                    </span>
                    <span className="text-sm text-on-surface-variant">
                      {data.game_predictions.total_settled ? 'accuracy' : 'no settled yet'}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-on-surface-variant">
                    <span>Recorded: <strong className="text-on-surface">{data.game_predictions.total}</strong></span>
                    <span>Settled: <strong className="text-on-surface">{data.game_predictions.total_settled ?? 0}</strong></span>
                    <span>Correct: <strong className="text-emerald-600 dark:text-emerald-400">{data.game_predictions.correct}</strong></span>
                    <span>Wrong: <strong className="text-rose-600 dark:text-rose-400">{data.game_predictions.incorrect ?? 0}</strong></span>
                    <span className="col-span-2">Pending: <strong className="text-amber-600 dark:text-amber-400">{data.game_predictions.pending ?? 0}</strong></span>
                  </div>
                </>
              )}
            </div>

            <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-3">Recent prediction history</h2>
              {data.game_predictions.records.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No records.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs sm:text-sm text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-container-high">
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Date</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Matchup</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Predicted</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant text-right">Conf.</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Actual</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant text-right">Score</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.game_predictions.records.map((r, i) => (
                        <tr key={`${r.date}-${r.game_id}-${i}`} className="border-t border-gray-100 dark:border-outline-variant/30">
                          <td className="py-1.5 px-2 text-on-surface-variant">{r.date}</td>
                          <td className="py-1.5 px-2 font-medium text-on-surface">{r.matchup}</td>
                          <td className="py-1.5 px-2 text-on-surface">{r.predicted_winner}</td>
                          <td className="py-1.5 px-2 text-right text-on-surface-variant">{r.confidence_pct != null ? `${r.confidence_pct}%` : '—'}</td>
                          <td className="py-1.5 px-2 text-on-surface">{r.actual_winner ?? '—'}</td>
                          <td className="py-1.5 px-2 text-right text-on-surface-variant">{r.home_score != null && r.away_score != null ? `${r.home_score}–${r.away_score}` : '—'}</td>
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
          </div>

          {/* —— AI pick of the day —— */}
          <div
            role="tabpanel"
            id="accuracy-panel-ai"
            aria-labelledby="accuracy-tab-ai"
            hidden={tab !== 'ai'}
            className="mt-4 space-y-6"
          >
            <div className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-1">AI pick of the day</h2>
              <p className="text-xs text-on-surface-variant mb-3">Prop O/U vs actual (pushes excluded from win rate)</p>
              {data.pick_of_the_day.total === 0 ? (
                <p className="text-sm text-on-surface-variant">No picks recorded in this range. Open the dashboard or warm cache so picks are saved.</p>
              ) : (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-on-surface">
                      {(data.pick_of_the_day.settled ?? 0) > 0 && (data.pick_of_the_day.hits + data.pick_of_the_day.misses) > 0
                        ? (data.pick_of_the_day.hit_rate_pct ?? '—')
                        : '—'}
                      {(data.pick_of_the_day.settled ?? 0) > 0 && (data.pick_of_the_day.hits + data.pick_of_the_day.misses) > 0 ? '%' : ''}
                    </span>
                    <span className="text-sm text-on-surface-variant">
                      {(data.pick_of_the_day.settled ?? 0) > 0 && (data.pick_of_the_day.hits + data.pick_of_the_day.misses) > 0
                        ? `${data.pick_of_the_day.hits}W – ${data.pick_of_the_day.misses}L`
                        : 'awaiting grade'}
                      {data.pick_of_the_day.pushes > 0 && ` (${data.pick_of_the_day.pushes} push)`}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-on-surface-variant">
                    <span>Recorded: <strong className="text-on-surface">{data.pick_of_the_day.total}</strong></span>
                    <span className="mx-2">·</span>
                    <span>Settled: <strong className="text-on-surface">{data.pick_of_the_day.settled ?? 0}</strong></span>
                    <span className="mx-2">·</span>
                    <span>Pending: <strong className="text-amber-600 dark:text-amber-400">{data.pick_of_the_day.pending ?? 0}</strong></span>
                  </div>
                  {(data.pick_of_the_day.mae != null || data.pick_of_the_day.rmse != null) && (
                    <div className="mt-2 text-xs text-on-surface-variant">
                      MAE: <strong className="text-gray-700 dark:text-on-surface-variant">{data.pick_of_the_day.mae ?? '—'}</strong>
                      {' · '}
                      RMSE: <strong className="text-gray-700 dark:text-on-surface-variant">{data.pick_of_the_day.rmse ?? '—'}</strong>
                    </div>
                  )}
                </>
              )}
            </div>

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
                <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                  <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-3">Win rate by stat (pick of the day)</h2>
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

            <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-3">AI pick of the day history</h2>
              <p className="text-xs text-on-surface-variant mb-3">
                Rows appear when a pick is first generated for that date. <strong>Pending</strong> clears after Admin <strong>Settle accuracy</strong> for that date.
              </p>
              {data.pick_of_the_day.records.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No picks on file in this range.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs sm:text-sm text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-container-high">
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Date</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Player</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Prop</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Line</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant">Actual</th>
                        <th className="py-2 px-2 font-semibold text-on-surface-variant text-center">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.pick_of_the_day.records.map((r, i) => (
                        <tr key={`${r.date}-${r.player_name}-${i}`} className="border-t border-gray-100 dark:border-outline-variant/30">
                          <td className="py-1.5 px-2 text-on-surface-variant">{r.date}</td>
                          <td className="py-1.5 px-2 font-medium text-on-surface">{r.player_name}</td>
                          <td className="py-1.5 px-2 text-on-surface">{r.stat_type} {r.suggestion}</td>
                          <td className="py-1.5 px-2 text-on-surface-variant">{r.line_value}</td>
                          <td className="py-1.5 px-2 text-on-surface-variant">{r.actual_value ?? '—'}</td>
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
                              <span className="text-on-surface-variant">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          {/* —— Top Picks —— */}
          <div
            role="tabpanel"
            id="accuracy-panel-top"
            aria-labelledby="accuracy-tab-top"
            hidden={tab !== 'top'}
            className="mt-4 space-y-6"
          >
            <div className="rounded-xl bg-surface-container border border-teal-200 dark:border-teal-800/50 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-1">Top Picks of the Day</h2>
              <p className="text-xs text-on-surface-variant mb-3">Homepage props (lock / strong / lean tiers from confidence)</p>
              {data.top_picks && (data.top_picks.overall.total ?? data.top_picks.records.length) > 0 ? (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-on-surface">
                      {(data.top_picks.overall.hits + data.top_picks.overall.misses) > 0
                        ? (data.top_picks.overall.hit_rate_pct ?? '—')
                        : '—'}
                      {(data.top_picks.overall.hits + data.top_picks.overall.misses) > 0 ? '%' : ''}
                    </span>
                    <span className="text-sm text-on-surface-variant">
                      overall (excl. push)
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-teal-700 dark:text-teal-300">
                    Lock tier hit:{' '}
                    <strong>
                      {data.top_picks.overall.lock_hit_rate_pct != null
                        ? `${data.top_picks.overall.lock_hit_rate_pct}%`
                        : '—'}
                    </strong>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-on-surface-variant">
                    <span>Rows: <strong className="text-on-surface">{data.top_picks.overall.total ?? data.top_picks.records.length}</strong></span>
                    <span>Settled: <strong className="text-on-surface">{data.top_picks.overall.settled}</strong></span>
                    <span>Hits / Miss: <strong className="text-emerald-600 dark:text-emerald-400">{data.top_picks.overall.hits}</strong>
                      {' / '}
                      <strong className="text-rose-600 dark:text-rose-400">{data.top_picks.overall.misses}</strong>
                    </span>
                    <span>Pushes: <strong className="text-amber-600 dark:text-amber-400">{data.top_picks.overall.pushes}</strong></span>
                    <span className="col-span-2">Pending: <strong className="text-amber-600 dark:text-amber-400">{data.top_picks.overall.pending}</strong></span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-on-surface-variant">No Top Picks rows in this range. Load the home dashboard on game days so picks are recorded.</p>
              )}
            </div>

            {data.top_picks && data.top_picks.records.length > 0 && (() => {
              const tp = data.top_picks
              const tierChart = TIER_ORDER
                .map((t) => {
                  const b = tp.by_tier[t]
                  if (!b || (b.hits + b.misses) < 1) return null
                  return {
                    label: t,
                    winRate: b.hit_rate_pct ?? 0,
                    n: b.hits + b.misses,
                  }
                })
                .filter((x) => x != null)
              const bandChart = BAND_ORDER
                .map((band) => {
                  const b = tp.by_confidence_band[band]
                  if (!b || (b.hits + b.misses) < 1) return null
                  return { band, winRate: b.hit_rate_pct ?? 0, n: b.hits + b.misses }
                })
                .filter((x) => x != null)
              return (
                <>
                  <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                    <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-3">Top Picks — hit rate by tier</h2>
                    <p className="text-xs text-on-surface-variant mb-3">Lock ≥78, Strong ≥62, Lean &lt;62 confidence (same as homepage)</p>
                    {tierChart.length === 0 ? (
                      <p className="text-sm text-on-surface-variant">No graded non-push picks in this range.</p>
                    ) : (
                      <div className="h-52 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={tierChart} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                            <Tooltip formatter={(value: number) => [`${value}%`, 'Hit rate']} labelFormatter={(l) => `Tier: ${l}`} />
                            <Bar dataKey="winRate" fill="rgb(20 184 166)" name="Hit rate" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </section>
                  <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                    <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-3">Top Picks — hit rate by confidence band</h2>
                    {bandChart.length === 0 ? (
                      <p className="text-sm text-on-surface-variant">No graded data by band.</p>
                    ) : (
                      <div className="h-56 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={bandChart} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                            <XAxis dataKey="band" tick={{ fontSize: 11 }} interval={0} angle={-25} textAnchor="end" height={48} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                            <Tooltip formatter={(value: number) => [`${value}%`, 'Hit rate']} />
                            <Bar dataKey="winRate" fill="rgb(59 130 246)" name="Hit rate" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </section>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                      <h3 className="text-base font-semibold text-on-surface mb-2">By stat type</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left border-collapse">
                          <thead>
                            <tr className="bg-surface-container-high">
                              <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Stat</th>
                              <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Hit %</th>
                              <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Graded</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(tp.by_stat).map(([k, b]) => (
                              <tr key={k} className="border-t border-gray-100 dark:border-outline-variant/30">
                                <td className="py-1.5 px-2 text-on-surface">{k}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hit_rate_pct != null ? `${b.hit_rate_pct}%` : '—'}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hits + b.misses}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                    <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                      <h3 className="text-base font-semibold text-on-surface mb-2">By direction</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left border-collapse">
                          <thead>
                            <tr className="bg-surface-container-high">
                              <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Side</th>
                              <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Hit %</th>
                              <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Graded</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(tp.by_direction).map(([k, b]) => (
                              <tr key={k} className="border-t border-gray-100 dark:border-outline-variant/30">
                                <td className="py-1.5 px-2 text-on-surface uppercase">{k}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hit_rate_pct != null ? `${b.hit_rate_pct}%` : '—'}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hits + b.misses}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  </div>
                  <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                    <h3 className="text-base font-semibold text-on-surface mb-2">Tier × stat</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead>
                          <tr className="bg-surface-container-high">
                            <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Tier</th>
                            <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Stat</th>
                            <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Hit %</th>
                            <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Graded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {TIER_ORDER.flatMap((tier) => {
                            const inner = tp.tier_x_stat[tier]
                            if (!inner) return []
                            return Object.entries(inner).map(([st, b]) => (
                              <tr key={`${tier}-${st}`} className="border-t border-gray-100 dark:border-outline-variant/30">
                                <td className="py-1.5 px-2 text-on-surface capitalize">{tier}</td>
                                <td className="py-1.5 px-2 text-on-surface">{st}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hit_rate_pct != null ? `${b.hit_rate_pct}%` : '—'}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hits + b.misses}</td>
                              </tr>
                            ))
                          })}
                        </tbody>
                      </table>
                    </div>
                  </section>
                  <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                    <h3 className="text-base font-semibold text-on-surface mb-2">Tier × direction</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead>
                          <tr className="bg-surface-container-high">
                            <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Tier</th>
                            <th className="py-1.5 px-2 font-semibold text-on-surface-variant">Direction</th>
                            <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Hit %</th>
                            <th className="py-1.5 px-2 text-right font-semibold text-on-surface-variant">Graded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {TIER_ORDER.flatMap((tier) => {
                            const inner = tp.tier_x_direction[tier]
                            if (!inner) return []
                            return Object.entries(inner).map(([d, b]) => (
                              <tr key={`${tier}-${d}`} className="border-t border-gray-100 dark:border-outline-variant/30">
                                <td className="py-1.5 px-2 text-on-surface capitalize">{tier}</td>
                                <td className="py-1.5 px-2 text-on-surface uppercase">{d}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hit_rate_pct != null ? `${b.hit_rate_pct}%` : '—'}</td>
                                <td className="py-1.5 px-2 text-right text-on-surface-variant">{b.hits + b.misses}</td>
                              </tr>
                            ))
                          })}
                        </tbody>
                      </table>
                    </div>
                  </section>
                  <section className="rounded-xl bg-surface-container border border-gray-200 dark:border-outline-variant/30 shadow-sm p-4 sm:p-6">
                    <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-3">Top Picks history</h2>
                    <p className="text-xs text-on-surface-variant mb-3">
                      One row per saved pick. <strong>Pending</strong> clears after <strong>Settle accuracy</strong> for that date.
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs sm:text-sm text-left border-collapse">
                        <thead>
                          <tr className="bg-surface-container-high">
                            <th className="py-2 px-2 font-semibold text-on-surface-variant">Date</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant">Player</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant">Prop</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant text-right">Conf.</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant">Tier</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant">Band</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant text-right">Line</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant text-right">Actual</th>
                            <th className="py-2 px-2 font-semibold text-on-surface-variant text-center">Result</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tp.records.map((r) => (
                            <tr key={r.id} className="border-t border-gray-100 dark:border-outline-variant/30">
                              <td className="py-1.5 px-2 text-on-surface-variant whitespace-nowrap">{r.date}</td>
                              <td className="py-1.5 px-2 font-medium text-on-surface">{r.player_name}</td>
                              <td className="py-1.5 px-2 text-on-surface whitespace-nowrap">
                                {r.stat_type} {r.direction}
                              </td>
                              <td className="py-1.5 px-2 text-right text-on-surface-variant">
                                {r.confidence != null ? `${Math.round(r.confidence * 10) / 10}%` : '—'}
                              </td>
                              <td className="py-1.5 px-2 text-on-surface capitalize">{r.tier}</td>
                              <td className="py-1.5 px-2 text-on-surface-variant text-xs">{r.confidence_band}</td>
                              <td className="py-1.5 px-2 text-right text-on-surface-variant">{r.line_value}</td>
                              <td className="py-1.5 px-2 text-right text-on-surface-variant">{r.actual_value ?? '—'}</td>
                              <td className="py-1.5 px-2 text-center">
                                {r.status === 'pending' ? (
                                  <span className="text-amber-600 dark:text-amber-400 font-medium">Pending</span>
                                ) : r.push ? (
                                  <span className="text-amber-600 dark:text-amber-400 font-semibold">Push</span>
                                ) : r.hit ? (
                                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Hit</span>
                                ) : r.hit === false ? (
                                  <span className="text-rose-600 dark:text-rose-400 font-semibold">Miss</span>
                                ) : (
                                  <span className="text-on-surface-variant">—</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </>
              )
            })()}
          </div>

          {/* —— Combined —— */}
          <div
            role="tabpanel"
            id="accuracy-panel-combined"
            aria-labelledby="accuracy-tab-combined"
            hidden={tab !== 'combined'}
            className="mt-4 space-y-6"
          >
            <div className="rounded bg-surface-container border border-primary-container/30 shadow-sm p-4 sm:p-6">
              <h2 className="text-lg font-black text-on-surface uppercase tracking-tight mb-1">Combined</h2>
              <p className="text-xs text-on-surface-variant mb-3">Every settled match + every graded AI pick (non-push) counts as one trial</p>
              {data.combined_accuracy && data.combined_accuracy.total > 0 ? (
                <>
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-3xl font-bold text-primary-container">
                      {data.combined_accuracy.accuracy_pct ?? 0}%
                    </span>
                    <span className="text-sm text-on-surface-variant">
                      {data.combined_accuracy.correct} / {data.combined_accuracy.total} correct
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-on-surface-variant">
                    Matches: <strong>{data.combined_accuracy.game_settled ?? 0}</strong> graded
                    <span className="mx-2">·</span>
                    AI props: <strong>{data.combined_accuracy.ai_pick_graded_non_push ?? 0}</strong> graded (excl. push)
                  </div>
                </>
              ) : (
                <p className="text-sm text-on-surface-variant">No combined trials yet (need at least one settled match or graded pick).</p>
              )}
            </div>
            <p className="text-sm text-on-surface-variant">
              Use the other tabs for per–bet-type breakdowns, charts, and row-level history.
            </p>
          </div>
        </>
      )}

      <div className="mt-6 text-sm text-on-surface-variant">
        <p>Match predictions, AI picks, and Top Picks rows are saved when caches are warmed or when the dashboard loads Top Picks for that day. Run <strong>Settle accuracy</strong> in Admin to grade a date (default: yesterday), including Top Picks props. A daily cron can run this automatically after games.</p>
      </div>
      <div className="mt-4">
        <Link to="/admin" className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline">Go to Admin</Link>
        <span className="mx-2">·</span>
        <Link to="/" className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline">Back to Dashboard</Link>
      </div>
    </div>
  )
}
