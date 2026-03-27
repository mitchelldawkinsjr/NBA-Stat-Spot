import type { HitPeriod, LivePropTrend } from '../../types/liveProps'

interface Props {
  trend: LivePropTrend
  period: HitPeriod
}

export function HitRateTrendCell({ trend, period }: Props) {
  const slice = trend[period]
  if (!slice || !slice.total) {
    return <span className="text-on-surface/40 text-xs">—</span>
  }
  const { hit_rate_percentage, hits, total, results } = slice
  const good = hit_rate_percentage >= 50
  return (
    <div className="flex flex-col gap-1 min-w-[120px]">
      <div className="flex items-center justify-between gap-2">
        <span
          className={`text-[10px] font-black uppercase ${good ? 'text-betting-green' : 'text-betting-red'}`}
        >
          {hit_rate_percentage}% hit rate
        </span>
        <span className="text-[9px] text-on-surface/40 font-bold">
          {period}: {hits}/{total}
        </span>
      </div>
      <div className="flex flex-wrap gap-1 max-w-[200px]">
        {results.map((hit, i) => (
          <span
            key={`${period}-${i}`}
            className={`w-2.5 h-2.5 rounded-sm shrink-0 ${hit ? 'bg-betting-green' : 'bg-betting-red'}`}
            title={hit ? 'Hit' : 'Miss'}
          />
        ))}
      </div>
    </div>
  )
}
