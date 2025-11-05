import { useQuery } from '@tanstack/react-query'
import { QuickPropLab } from './QuickPropLab'
import { DailyPropsPanel } from './DailyPropsPanel'

async function fetchToday() {
  const res = await fetch('/api/v1/games/today')
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export function GoodBetsDashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['games-today'], queryFn: fetchToday })
  const games = data?.games ?? []
  return (
    <div>
      <h2>Dashboard</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 420px) 1fr', gap: 16, alignItems: 'start' }}>
        <div>
          <QuickPropLab />
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Today's Games</div>
            {isLoading ? <div>Loading…</div> : error ? <div>Error loading schedule</div> : (
              games.length === 0 ? <div>No games available.</div> : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                  {games.map((g: any, idx: number) => (
                    <div key={idx} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, background: '#fff' }}>
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
