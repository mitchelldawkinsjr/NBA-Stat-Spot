import type { ReactNode } from 'react'
import type { LivePropsConfidenceCard, LivePropsMarketSentiment } from '../../types/liveProps'

export interface SlipLeg {
  id: string
  playerId: number
  label: string
  odds: string
  trendNote: string
}

interface Props {
  confidence: LivePropsConfidenceCard[]
  sentiment: LivePropsMarketSentiment | null
  slip: SlipLeg[]
  onClearSlip: () => void
  stake: string
  onStakeChange: (v: string) => void
  /** Rendered above Market sentiment (e.g. hot streak callout). */
  hotStreak?: ReactNode
}

function americanToDecimal(odds: string): number {
  const o = odds.trim()
  if (!o) return 2
  if (o.startsWith('+')) {
    const n = parseInt(o.slice(1), 10)
    if (Number.isNaN(n)) return 2
    return 1 + n / 100
  }
  const n = parseInt(o.replace('-', ''), 10)
  if (Number.isNaN(n) || n === 0) return 2
  return 1 + 100 / n
}

function estimatedPayout(stake: number, legs: SlipLeg[]): number {
  if (!legs.length || stake <= 0) return 0
  let mult = 1
  for (const leg of legs) {
    mult *= americanToDecimal(leg.odds)
  }
  return Math.round(stake * mult * 100) / 100
}

export function LiveConfidencePanel({
  confidence,
  sentiment,
  slip,
  onClearSlip,
  stake,
  onStakeChange,
  hotStreak,
}: Props) {
  const stakeNum = parseFloat(stake.replace(',', '.')) || 0
  const payout = estimatedPayout(stakeNum, slip)

  return (
    <div className="space-y-6">
      <div className="glass-panel rounded-lg p-6 border border-outline-variant/10">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-black tracking-tighter italic uppercase text-on-surface flex items-center gap-2">
            Live confidence
            <span className="material-symbols-outlined text-betting-green text-lg">verified</span>
          </h3>
          <span className="text-[9px] font-bold text-on-surface/40 uppercase tracking-widest">Real-time data</span>
        </div>

        {confidence.length === 0 ? (
          <p className="text-sm text-on-surface/50">No confidence cards for this slate.</p>
        ) : (
          confidence.map((c, idx) => {
            const isLock = c.tier === 'lock'
            const isRisk = c.tier === 'risk'
            return (
              <div
                key={`${c.player_id}-${idx}`}
                className={`mb-6 pb-6 ${idx < confidence.length - 1 ? 'border-b border-outline-variant/10' : ''}`}
              >
                <div className="flex justify-between items-start mb-3 gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {isLock ? (
                      <span className="bg-betting-green text-[#001d35] text-[9px] font-black px-2 py-0.5 rounded shrink-0">
                        LOCK
                      </span>
                    ) : isRisk ? (
                      <span className="bg-betting-red text-on-surface text-[9px] font-black px-2 py-0.5 rounded shrink-0">
                        RISK
                      </span>
                    ) : (
                      <span className="bg-surface-container-highest text-on-surface/70 text-[9px] font-black px-2 py-0.5 rounded shrink-0">
                        WATCH
                      </span>
                    )}
                    <p className="text-xs font-black uppercase truncate">{c.label}</p>
                  </div>
                  <span
                    className={`font-mono font-bold text-xs shrink-0 ${isRisk ? 'text-betting-red' : isLock ? 'text-betting-green' : 'text-on-surface/70'}`}
                  >
                    {c.confidence_pct}%
                  </span>
                </div>
                <div className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant/10">
                  <p className="text-[11px] leading-relaxed text-on-surface/70 font-medium">
                    <span className="text-primary-container font-bold uppercase">Trend match:</span>{' '}
                    {c.rationale || `L5 hit rate ${c.trend_L5_hit}% vs model confidence.`}
                  </p>
                </div>
              </div>
            )
          })
        )}

        <div className="space-y-4">
          <div className="flex justify-between items-center text-[10px] font-bold tracking-widest uppercase text-on-surface/40">
            <span>Live slip ({slip.length})</span>
            <button type="button" onClick={onClearSlip} className="hover:text-primary transition-colors">
              Clear
            </button>
          </div>
          {slip.length === 0 ? (
            <p className="text-xs text-on-surface/40">Add legs from the table (+ Slip).</p>
          ) : (
            slip.map(leg => (
              <div
                key={leg.id}
                className="bg-surface-container-high p-4 rounded-lg flex justify-between items-center border border-primary-container/20 gap-2"
              >
                <div className="min-w-0">
                  <p className="text-xs font-black tracking-tight truncate">{leg.label}</p>
                  <p className="text-[10px] text-on-surface/40 uppercase truncate">{leg.trendNote}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs font-mono font-bold text-secondary">{leg.odds}</p>
                </div>
              </div>
            ))
          )}
          <div className="flex gap-2">
            <div className="flex-grow bg-surface-container-highest rounded-lg px-4 flex items-center border border-outline-variant/30">
              <span className="text-on-surface/40 text-xs font-bold">$</span>
              <input
                className="bg-transparent border-none focus:ring-0 text-sm font-mono font-bold w-full text-right text-on-surface"
                type="text"
                value={stake}
                onChange={e => onStakeChange(e.target.value)}
                inputMode="decimal"
                aria-label="Stake amount"
              />
            </div>
            <button
              type="button"
              className="bg-primary-container text-on-primary p-3 rounded-lg flex items-center justify-center"
              aria-label="Trending up"
            >
              <span className="material-symbols-outlined text-[20px]">trending_up</span>
            </button>
          </div>
          <button
            type="button"
            className="w-full bg-primary-container text-on-primary py-4 rounded-lg font-black tracking-tighter text-sm uppercase hover:bg-primary transition-all active:scale-95 shadow-lg shadow-primary-container/20"
          >
            Place live bet • ${payout.toFixed(2)} est. return
          </button>
        </div>
      </div>

      {hotStreak}

      {sentiment ? (
        <div className="bg-surface-container-low p-6 rounded-lg border border-outline-variant/10">
          <h4 className="text-[10px] font-black tracking-widest text-on-surface/40 uppercase mb-4">
            Market sentiment
          </h4>
          <div className="flex items-end gap-1 h-12 mb-2">
            {sentiment.bars.map((h, i) => (
              <div
                key={i}
                className="flex-grow rounded-sm bg-primary-container/40"
                style={{
                  height: `${Math.min(100, h)}%`,
                  opacity: 0.35 + (i / sentiment.bars.length) * 0.4,
                }}
              />
            ))}
          </div>
          <p className="text-[10px] text-on-surface/60 font-bold uppercase text-center">
            Flow toward <span className="text-primary-container">{sentiment.headline_team}</span>
          </p>
          <p className="text-[9px] text-on-surface/40 text-center mt-1">{sentiment.spread_note}</p>
        </div>
      ) : null}
    </div>
  )
}
