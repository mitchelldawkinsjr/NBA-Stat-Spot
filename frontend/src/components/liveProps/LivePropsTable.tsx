import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { HitPeriod, LivePropsPlayerRow } from '../../types/liveProps'
import { HitRateTrendCell } from './HitRateTrendCell'

const PERIODS: HitPeriod[] = ['L5', 'L10', 'L20']

function orderTeamKeys(
  keys: string[],
  awayTeam: string | null | undefined,
  homeTeam: string | null | undefined
): string[] {
  if (awayTeam && homeTeam) {
    const out: string[] = []
    if (keys.includes(awayTeam)) out.push(awayTeam)
    if (keys.includes(homeTeam)) out.push(homeTeam)
    const rest = keys.filter(k => k !== awayTeam && k !== homeTeam).sort((a, b) => a.localeCompare(b))
    return [...out, ...rest]
  }
  return [...keys].sort((a, b) => a.localeCompare(b))
}

interface Props {
  players: LivePropsPlayerRow[]
  /** Matchup order: away column first, then home (team abbreviations from API) */
  awayTeam?: string | null
  homeTeam?: string | null
  hitPeriod: HitPeriod
  onHitPeriod: (p: HitPeriod) => void
  rotationOnly: boolean
  onRotationOnly: (v: boolean) => void
  onAddToSlip: (leg: {
    playerId: number
    label: string
    odds: string
    trendNote: string
  }) => void
}

export function LivePropsTable({
  players,
  awayTeam,
  homeTeam,
  hitPeriod,
  onHitPeriod,
  rotationOnly,
  onRotationOnly,
  onAddToSlip,
}: Props) {
  const navigate = useNavigate()
  const rows = rotationOnly ? players.filter(p => p.rotation_tier) : players

  const playersByTeam = useMemo(() => {
    const withProp = rows.filter(p => p.props[0])
    const map = new Map<string, LivePropsPlayerRow[]>()
    for (const p of withProp) {
      const abbr = p.team || '—'
      if (!map.has(abbr)) map.set(abbr, [])
      map.get(abbr)!.push(p)
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.name.localeCompare(b.name))
    }
    const keys = orderTeamKeys([...map.keys()], awayTeam, homeTeam)
    return keys.map(team => ({ team, players: map.get(team)! }))
  }, [rows, awayTeam, homeTeam])

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2">
        <h3 className="text-xl font-black tracking-tighter italic uppercase text-primary-container">
          Live player props
        </h3>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center bg-surface-container-low rounded-lg p-1 border border-outline-variant/20">
            {PERIODS.map(p => (
              <button
                key={p}
                type="button"
                onClick={() => onHitPeriod(p)}
                className={`px-3 py-1 text-[10px] font-bold uppercase rounded transition-colors ${
                  hitPeriod === p
                    ? 'bg-primary-container text-on-primary'
                    : 'text-on-surface/50 hover:text-on-surface'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onRotationOnly(false)}
              className={`px-3 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase ${
                !rotationOnly
                  ? 'bg-surface-container-highest text-secondary'
                  : 'bg-surface-container-low border border-outline-variant/30 text-on-surface/40'
              }`}
            >
              All players
            </button>
            <button
              type="button"
              onClick={() => onRotationOnly(true)}
              className={`px-3 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase ${
                rotationOnly
                  ? 'bg-surface-container-highest text-secondary'
                  : 'bg-surface-container-low border border-outline-variant/30 text-on-surface/40'
              }`}
            >
              Rotation
            </button>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-lg overflow-hidden border border-outline-variant/10 overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[860px]">
          <thead>
            <tr className="bg-surface-container-low text-[10px] font-bold tracking-widest text-on-surface/50 uppercase">
              <th className="px-4 py-3 whitespace-nowrap">Player</th>
              <th className="px-4 py-3 text-center whitespace-nowrap">Stats (P/R/A)</th>
              <th className="px-4 py-3 whitespace-nowrap">Live prop line</th>
              <th className="px-4 py-3 whitespace-nowrap">Progression</th>
              <th className="px-4 py-3 border-l border-outline-variant/10 whitespace-nowrap">Trend analysis</th>
              <th className="px-4 py-3 whitespace-nowrap">Action</th>
            </tr>
          </thead>
          {rows.length === 0 ? (
            <tbody>
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-on-surface/50 text-sm">
                  No players match this filter.
                </td>
              </tr>
            </tbody>
          ) : playersByTeam.length === 0 ? (
            <tbody>
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-on-surface/50 text-sm">
                  No prop lines for the current filter.
                </td>
              </tr>
            </tbody>
          ) : (
            playersByTeam.map(({ team, players: teamPlayers }) => (
              <tbody key={team} className="divide-y divide-outline-variant/5">
                <tr className="bg-surface-container-low/90 border-t border-outline-variant/15">
                  <td
                    colSpan={6}
                    className="px-4 py-2.5 text-[10px] font-black tracking-[0.2em] text-primary-container uppercase"
                  >
                    <span className="text-on-surface/70 mr-2">{team}</span>
                    {team === awayTeam ? (
                      <span className="text-on-surface/40 font-bold normal-case tracking-normal">Away</span>
                    ) : team === homeTeam ? (
                      <span className="text-on-surface/40 font-bold normal-case tracking-normal">Home</span>
                    ) : null}
                    <span className="text-on-surface/35 font-semibold normal-case tracking-normal ml-2">
                      ({teamPlayers.length} {teamPlayers.length === 1 ? 'player' : 'players'})
                    </span>
                  </td>
                </tr>
                {teamPlayers.map(player => {
                  const prop = player.props[0]!
                  const { progression, trend, line, suggestion, odds_over, odds_under } = prop
                  const odds = suggestion === 'under' ? odds_under : odds_over
                  const paceGood =
                    suggestion === 'over' ? progression.pace >= line : progression.pace <= line
                  const barPct = Math.min(100, Math.max(0, progression.completion_pct))
                  const barClass =
                    barPct >= 85 ? 'bg-betting-green' : barPct >= 45 ? 'bg-secondary-container' : 'bg-primary-container'

                  return (
                    <tr key={player.player_id} className="hover:bg-surface-container-high transition-colors group">
                      <td className="px-4 py-4 whitespace-nowrap">
                        <button
                          type="button"
                          className="flex items-center gap-3 text-left"
                          onClick={() => navigate(`/player/${player.player_id}`)}
                        >
                          <div className="w-10 h-10 rounded bg-surface-container-highest flex-shrink-0 overflow-hidden border border-outline-variant/20">
                            <img
                              src={player.headshot_url}
                              alt=""
                              className="object-cover w-full h-full grayscale group-hover:grayscale-0 transition-all"
                              onError={e => {
                                const el = e.target as HTMLImageElement
                                el.style.display = 'none'
                              }}
                            />
                          </div>
                          <div>
                            <p className="text-sm font-black tracking-tighter leading-tight">{player.name}</p>
                            <p className="text-[10px] text-on-surface/40 font-bold uppercase">
                              {player.position}
                            </p>
                          </div>
                        </button>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex justify-center gap-2 text-xs font-mono font-bold">
                          <span className="text-primary-container">{player.live_stats.pts}</span>
                          <span className="text-on-surface/30">/</span>
                          <span className="text-on-surface/80">{player.live_stats.reb}</span>
                          <span className="text-on-surface/30">/</span>
                          <span className="text-on-surface/80">{player.live_stats.ast}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="text-[10px] font-bold text-on-surface/40 uppercase">O/U points</span>
                          <span className="text-sm font-black text-secondary">{line} PTS</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 min-w-[140px] whitespace-nowrap">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[9px] font-black uppercase tracking-tighter gap-2">
                            <span>{progression.completion_pct}% vs line</span>
                            <span className={paceGood ? 'text-betting-green' : 'text-betting-red'}>
                              Pace: {progression.pace}
                            </span>
                          </div>
                          <div className="w-full bg-surface-variant h-1.5 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${barClass}`} style={{ width: `${barPct}%` }} />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 border-l border-outline-variant/10 whitespace-nowrap">
                        <HitRateTrendCell trend={trend} period={hitPeriod} />
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() =>
                            onAddToSlip({
                              playerId: player.player_id,
                              label: `${player.name.split(' ').pop() ?? player.name} ${suggestion} ${line} PTS`,
                              odds,
                              trendNote: `${hitPeriod}: ${trend[hitPeriod]?.hits ?? 0}/${trend[hitPeriod]?.total ?? 0} hits`,
                            })
                          }
                          className="bg-secondary-container text-on-secondary-container px-3 py-2 rounded-lg text-[10px] font-black uppercase tracking-tighter hover:bg-secondary transition-all active:scale-95 whitespace-nowrap"
                        >
                          + Slip ({odds})
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            ))
          )}
        </table>
      </div>
    </div>
  )
}
