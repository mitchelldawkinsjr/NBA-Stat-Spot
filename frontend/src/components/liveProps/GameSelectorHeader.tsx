import type { LivePropsGameSummary } from '../../types/liveProps'

interface Props {
  games: LivePropsGameSummary[]
  selectedId: string | null
  onSelect: (gameId: string) => void
}

export function GameSelectorHeader({ games, selectedId, onSelect }: Props) {
  if (!games.length) {
    return (
      <section className="rounded-lg bg-surface-container-low px-4 py-3 text-sm text-on-surface/60">
        No games on today&apos;s slate.
      </section>
    )
  }

  return (
    <section className="flex gap-4 overflow-x-auto pb-2 no-scrollbar">
      {games.map(g => {
        const active = g.game_id === selectedId
        const label = `${g.away_team} @ ${g.home_team}`
        const statusLabel =
          g.is_final ? 'FINAL' : g.is_live ? `Q${g.quarter} ${g.time_remaining}` : 'Scheduled'
        const sub =
          g.is_live && !g.is_final
            ? 'Live props'
            : g.is_final
              ? 'Odds locked'
              : 'Pre-match'

        return (
          <button
            key={g.game_id}
            type="button"
            onClick={() => onSelect(g.game_id)}
            className={`flex-shrink-0 min-w-[240px] flex justify-between items-center px-4 py-3 text-left transition-opacity ${
              active
                ? 'bg-primary-container/10 border-l-4 border-primary-container'
                : 'bg-surface-container-low opacity-70 hover:opacity-100'
            }`}
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-sm tracking-tighter">{label}</span>
                {g.is_live && !g.is_final ? (
                  <span className="flex h-2 w-2 rounded-full bg-primary-container animate-pulse" aria-hidden />
                ) : null}
              </div>
              <p className="text-[10px] font-bold text-primary tracking-widest uppercase opacity-80">{statusLabel}</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-bold">
                {g.away_score} - {g.home_score}
              </p>
              <p className="text-[10px] text-on-surface/40 uppercase">{sub}</p>
            </div>
          </button>
        )
      })}
    </section>
  )
}
