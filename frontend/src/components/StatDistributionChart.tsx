import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { apiFetch } from '../utils/api'

type DistributionResponse = {
  mean: number
  std: number
  p_over: number
  p_under: number
  percentile_line: number
  distribution: string
  simulated_percentiles?: { p5: number; p25: number; p50: number; p75: number; p95: number }
  line?: number
  n_games_used?: number
  error?: string
}

type StatDistributionChartProps = {
  playerId: number
  stat: string
  line: number
  season?: string
}

export function StatDistributionChart({ playerId, stat, line, season }: StatDistributionChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stat-distribution', playerId, stat, line, season],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('stat', stat)
      params.set('line', String(line))
      if (season) params.set('season', season)
      const res = await apiFetch(`api/v1/props/distribution/${playerId}?${params.toString()}`)
      if (!res.ok) throw new Error('Failed to load distribution')
      return res.json() as Promise<DistributionResponse>
    },
    enabled: !!playerId && !!stat && line > 0,
  })

  if (!playerId || line <= 0) return null
  if (isLoading) return <div className="text-sm text-gray-500 dark:text-gray-400 py-4">Loading distribution…</div>
  if (error || data?.error) {
    return (
      <div className="text-sm text-amber-600 dark:text-amber-400 py-2">
        {data?.error ?? (error instanceof Error ? error.message : 'Could not load probability view')}
      </div>
    )
  }
  if (!data || data.distribution === 'insufficient_data') {
    return <div className="text-sm text-gray-500 dark:text-gray-400 py-2">Not enough games for distribution.</div>
  }

  const pctOver = Math.round((data.p_over ?? 0) * 100)
  const pctUnder = Math.round((data.p_under ?? 0) * 100)
  const percentiles = data.simulated_percentiles
  const chartData = percentiles
    ? [
        { x: 'p5', value: percentiles.p5 },
        { x: 'p25', value: percentiles.p25 },
        { x: 'p50', value: percentiles.p50 },
        { x: 'p75', value: percentiles.p75 },
        { x: 'p95', value: percentiles.p95 },
      ]
    : []

  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <span className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          P(OVER) = {pctOver}% · P(UNDER) = {pctUnder}%
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Line {data.line ?? line} · {data.distribution} · {data.n_games_used ?? 0} games
        </span>
      </div>
      {chartData.length > 0 && (
        <div className="h-32 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="distFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgb(59 130 246)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="rgb(59 130 246)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="x" tick={{ fontSize: 10 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(value: number) => [value.toFixed(1), 'Value']} />
              <ReferenceLine y={data.line ?? line} stroke="rgb(234 179 8)" strokeDasharray="3 3" />
              <Area type="monotone" dataKey="value" stroke="rgb(59 130 246)" fill="url(#distFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

type CollapsibleProbabilityViewProps = {
  playerId: number
  defaultStat?: string
  defaultLine?: number
  season?: string
}

export function CollapsibleProbabilityView({ playerId, defaultStat = 'pts', defaultLine, season }: CollapsibleProbabilityViewProps) {
  const [open, setOpen] = useState(false)
  const [stat, setStat] = useState(defaultStat)
  const [line, setLine] = useState(defaultLine ?? 20)

  return (
    <section className="mt-4 rounded-xl bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full px-4 py-3 flex items-center justify-between text-left text-sm font-semibold text-gray-900 dark:text-slate-100 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <span>Probability view (distribution vs line)</span>
        <span className="text-gray-500 dark:text-gray-400">{open ? '▼' : '▶'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-0 border-t border-gray-100 dark:border-slate-700">
          <div className="flex flex-wrap gap-3 items-center mt-3">
            <label className="text-xs text-gray-500 dark:text-gray-400">
              Stat
              <select
                value={stat}
                onChange={(e) => setStat(e.target.value)}
                className="ml-1 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 text-sm px-2 py-1"
              >
                <option value="pts">PTS</option>
                <option value="reb">REB</option>
                <option value="ast">AST</option>
                <option value="tpm">3PM</option>
                <option value="pra">PRA</option>
              </select>
            </label>
            <label className="text-xs text-gray-500 dark:text-gray-400">
              Line
              <input
                type="number"
                step="0.5"
                min={0}
                value={line}
                onChange={(e) => setLine(Number(e.target.value) || 0)}
                className="ml-1 w-20 rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 text-sm px-2 py-1"
              />
            </label>
          </div>
          <div className="mt-3">
            <StatDistributionChart playerId={playerId} stat={stat} line={line} season={season} />
          </div>
        </div>
      )}
    </section>
  )
}
