import { useQuery } from '@tanstack/react-query'
import { QuickPropLab } from './QuickPropLab'
import { DailyPropsPanel } from './DailyPropsPanel'
import { useSeason } from '../context/SeasonContext'

async function fetchToday() {
  const res = await fetch('/api/v1/games/today')
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

async function fetchDaily(minConfidence?: number) {
  const url = minConfidence ? `/api/v1/props/daily?min_confidence=${minConfidence}` : '/api/v1/props/daily'
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

async function fetchFeaturedPlayers() {
  const res = await fetch('/api/v1/players/featured')
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export function GoodBetsDashboard() {
  const { season } = useSeason()
  const { data, isLoading, error } = useQuery({ queryKey: ['games-today'], queryFn: fetchToday })
  const { data: daily } = useQuery({ queryKey: ['daily-props-count'], queryFn: () => fetchDaily(60) })
  const { data: featured } = useQuery({ queryKey: ['players-featured'], queryFn: fetchFeaturedPlayers })
  const games = data?.games ?? []
  const dailyCount = (daily?.items || []).length
  const featuredCount = (featured?.items || []).length || 0
  return (
    <div>
      <h2 className="text-xl font-semibold mb-3">Dashboard</h2>
      {/* Flowbite-like stat tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4 mb-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-sm text-gray-500">Today's Games</div>
          <div className="mt-1 text-2xl font-semibold">{isLoading ? '—' : games.length}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-sm text-gray-500">Daily Props (≥60% conf)</div>
          <div className="mt-1 text-2xl font-semibold">{dailyCount}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-sm text-gray-500">Featured Players</div>
          <div className="mt-1 text-2xl font-semibold">{featuredCount}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-sm text-gray-500">Season</div>
          <div className="mt-1 text-2xl font-semibold">{season}</div>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-4 lg:gap-6 lg:[grid-template-columns:minmax(360px,420px)_1fr] items-start">
        <div>
          <QuickPropLab />
        </div>
        <div className="grid gap-3 md:gap-4">
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Today's Games</div>
            {isLoading ? <div>Loading…</div> : error ? <div>Error loading schedule</div> : (
              games.length === 0 ? <div>No games available.</div> : (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 md:gap-4">
                  {games.map((g: any, idx: number) => (
                    <div key={idx} className="p-4 md:p-5" style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff' }}>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>{new Date(g.gameTimeUTC).toLocaleString()}</div>
                      <div style={{ marginTop: 6, fontWeight: 600 }}>{g.away} @ {g.home}</div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
          <DailyPropsPanel />
        </div>
      </div>
    </div>
  )
}
