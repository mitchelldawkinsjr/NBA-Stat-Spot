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
      <div className="grid grid-cols-1 gap-4 lg:gap-6 lg:[grid-template-columns:minmax(360px,420px)_1fr] items-start">
        <div>
          <QuickPropLab />
        </div>
        <div className="grid gap-3 md:gap-4">
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Today's Games</div>
            {isLoading ? <div>Loading…</div> : error ? <div>Error loading schedule</div> : (
              games.length === 0 ? <div>No games available.</div> : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>Time</th>
                        <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', padding: '6px 8px' }}>Matchup</th>
                      </tr>
                    </thead>
                    <tbody>
                      {games.map((g: any, idx: number) => (
                        <tr key={idx}>
                          <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', fontSize: 12, color: '#6b7280' }}>{new Date(g.gameTimeUTC).toLocaleString()}</td>
                          <td style={{ borderBottom: '1px solid #f3f4f6', padding: '6px 8px', fontWeight: 600 }}>{g.away} @ {g.home}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
