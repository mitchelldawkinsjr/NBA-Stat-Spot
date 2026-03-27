import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useSeason } from '../context/SeasonContext'
import { fetchLivePropsDashboard } from '../services/livePropService'
import type { HitPeriod } from '../types/liveProps'
import { GameSelectorHeader } from '../components/liveProps/GameSelectorHeader'
import { LivePropsTable } from '../components/liveProps/LivePropsTable'
import { LiveConfidencePanel, type SlipLeg } from '../components/liveProps/LiveConfidencePanel'

const PERIOD_STORAGE_KEY = 'livePropsHitPeriod'

function readStoredPeriod(): HitPeriod {
  try {
    const v = sessionStorage.getItem(PERIOD_STORAGE_KEY)
    if (v === 'L5' || v === 'L10' || v === 'L20') return v
  } catch {
    /* ignore */
  }
  return 'L5'
}

export default function LivePropDashboard() {
  const { season } = useSeason()
  const [searchParams] = useSearchParams()
  const phased = searchParams.get('phased') === '1'
  const skipCache = searchParams.get('nocache') === '1'
  const forceNoLiveBox = searchParams.get('live_box') === '0'

  const [gameId, setGameId] = useState<string | undefined>(undefined)
  const [hitPeriod, setHitPeriod] = useState<HitPeriod>(() => readStoredPeriod())
  const [rotationOnly, setRotationOnly] = useState(false)
  const [slip, setSlip] = useState<SlipLeg[]>([])
  const [stake, setStake] = useState('50.00')

  useEffect(() => {
    try {
      sessionStorage.setItem(PERIOD_STORAGE_KEY, hitPeriod)
    } catch {
      /* ignore */
    }
  }, [hitPeriod])

  const trendsQuery = useQuery({
    queryKey: ['live-props-dashboard', season, gameId ?? 'default', 'trends', skipCache],
    queryFn: () =>
      fetchLivePropsDashboard({
        gameId: gameId ?? null,
        season: season || undefined,
        liveBox: false,
        skipCache,
      }),
    enabled: phased,
    staleTime: 25_000,
  })

  const fullQuery = useQuery({
    queryKey: [
      'live-props-dashboard',
      season,
      gameId ?? 'default',
      'full',
      skipCache,
      forceNoLiveBox,
    ],
    queryFn: () =>
      fetchLivePropsDashboard({
        gameId: gameId ?? null,
        season: season || undefined,
        liveBox: !forceNoLiveBox,
        skipCache,
      }),
    enabled: !phased || (phased && (trendsQuery.isSuccess || trendsQuery.isError)),
    staleTime: 25_000,
    placeholderData: phased ? trendsQuery.data : undefined,
    refetchInterval: query => {
      const g = query.state.data?.games ?? []
      const anyLive = g.some(x => x.is_live && !x.is_final)
      return anyLive ? 30_000 : 60_000
    },
  })

  const data = fullQuery.data ?? (phased ? trendsQuery.data : undefined)
  const isLoading =
    !data &&
    (phased ? trendsQuery.isPending || fullQuery.isPending : fullQuery.isPending)
  const isError = fullQuery.isError || (phased && trendsQuery.isError && !fullQuery.data)
  const error = fullQuery.error ?? trendsQuery.error
  const isFetching = fullQuery.isFetching || trendsQuery.isFetching

  const refetch = useCallback(() => {
    void trendsQuery.refetch()
    void fullQuery.refetch()
  }, [trendsQuery, fullQuery])

  const players = useMemo(() => data?.players ?? [], [data?.players])
  const anyLive = useMemo(
    () => (data?.games ?? []).some(x => x.is_live && !x.is_final),
    [data?.games]
  )

  const hotPlayer = useMemo(() => {
    const withProp = players.filter(p => p.props[0])
    const perfect = withProp.find(p => p.props[0].trend.L5.hit_rate_percentage >= 100)
    return perfect ?? withProp[0]
  }, [players])

  const onAddToSlip = useCallback((leg: Omit<SlipLeg, 'id'>) => {
    const id = `${leg.playerId}-${leg.label}-${Date.now()}`
    setSlip(prev => [...prev, { ...leg, id }])
  }, [])

  const onClearSlip = useCallback(() => setSlip([]), [])

  const handleSelectGame = useCallback((id: string) => {
    setGameId(id)
  }, [])

  return (
    <div className="min-w-0 p-4 md:p-6 space-y-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-black italic uppercase tracking-tighter text-primary-container">
            Live prop terminal
          </h1>
          <p className="text-xs text-on-surface/50 mt-1">
            Points props with L5 / L10 / L20 hit trends and live box progression.
            {phased ? (
              <span className="ml-2 text-on-surface/40">
                Phased: <code className="text-[10px]">?phased=1</code> loads trends first, then ESPN box.
              </span>
            ) : null}
            {!phased && forceNoLiveBox ? (
              <span className="ml-2 text-on-surface/40">
                Fast mode: <code className="text-[10px]">live_box=0</code> (no ESPN box).
              </span>
            ) : null}
            {phased && fullQuery.isFetching && data?.live_box_applied === false ? (
              <span className="ml-2 text-tertiary-container">Loading live box…</span>
            ) : null}
            {isFetching && !isLoading ? <span className="ml-2 text-tertiary-container">Updating…</span> : null}
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="text-[10px] font-bold uppercase tracking-widest px-4 py-2 rounded-lg bg-surface-container-high border border-outline-variant/20 hover:bg-surface-container-highest"
        >
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="rounded-lg bg-surface-container-low p-8 text-center text-on-surface/60">Loading slate…</div>
      ) : null}

      {isError ? (
        <div className="rounded-lg border border-error-container/50 bg-error-container/10 p-4 text-sm text-error">
          {(error as Error)?.message ?? 'Failed to load live props.'}
        </div>
      ) : null}

      {!isLoading && data ? (
        <>
          <GameSelectorHeader
            games={data.games}
            selectedId={data.selected_game_id}
            onSelect={handleSelectGame}
          />

          {data.error ? (
            <p className="text-sm text-betting-red">{data.error}</p>
          ) : null}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-8 space-y-4">
              <LivePropsTable
                players={players}
                awayTeam={data.away_team ?? null}
                homeTeam={data.home_team ?? null}
                hitPeriod={hitPeriod}
                onHitPeriod={setHitPeriod}
                rotationOnly={rotationOnly}
                onRotationOnly={setRotationOnly}
                onAddToSlip={onAddToSlip}
              />
            </div>

            <div className="lg:col-span-4 space-y-6">
              <LiveConfidencePanel
                confidence={data.confidence}
                sentiment={data.market_sentiment}
                slip={slip}
                onClearSlip={onClearSlip}
                stake={stake}
                onStakeChange={setStake}
                hotStreak={
                  hotPlayer?.props[0] ? (
                    <div className="relative overflow-hidden min-h-[10rem] bg-surface-container-high rounded-lg p-5 flex items-center group">
                      <div className="z-10 relative max-w-full">
                        <h4 className="text-lg font-black italic tracking-tighter uppercase leading-none mb-2">
                          Hot streak signal
                        </h4>
                        <p className="text-xs text-on-surface/60 font-medium mb-4 line-clamp-4">
                          {hotPlayer.name}: L5 hit {hotPlayer.props[0].trend.L5.hit_rate_percentage}% on the fair PTS line (
                          {hotPlayer.props[0].line}). Model confidence {hotPlayer.props[0].confidence}%.
                        </p>
                        <Link
                          to={`/player/${hotPlayer.player_id}`}
                          className="inline-block bg-primary-container text-on-primary text-[10px] font-black py-2 px-4 rounded-lg uppercase tracking-widest"
                        >
                          Open player
                        </Link>
                      </div>
                      <div
                        className="absolute -right-10 -bottom-10 opacity-20 group-hover:opacity-35 transition-opacity duration-700 w-1/2 h-32 rounded-full bg-primary-container blur-3xl pointer-events-none"
                        aria-hidden
                      />
                    </div>
                  ) : null
                }
              />
            </div>
          </div>

          {!players.length && !data.error ? (
            <p className="text-sm text-on-surface/50 text-center py-8">
              No rotation players with enough game log data for this matchup.
            </p>
          ) : null}
        </>
      ) : null}

      {anyLive ? (
        <p className="text-[10px] text-on-surface/40 text-center uppercase tracking-widest">
          Live games refresh about every 30s
        </p>
      ) : null}
    </div>
  )
}
