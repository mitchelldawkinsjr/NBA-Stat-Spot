import { useQuery } from '@tanstack/react-query'

async function fetchToday() {
  const res = await fetch('/api/v1/games/today')
  if (!res.ok) throw new Error('Failed to load')
  return res.json()
}

export function GoodBetsDashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['games-today'], queryFn: fetchToday })
  if (isLoading) return <div>Loading…</div>
  if (error) return <div>Error loading schedule</div>
  const games = data?.games ?? []
  return (
    <div>
      <h2>Good Bets (Next 24h)</h2>
      {games.length === 0 ? <div>No games available.</div> : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          {games.map((g: any, idx: number) => (
            <div key={idx} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, background: '#fff' }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{new Date(g.gameTimeUTC).toLocaleString()}</div>
              <div style={{ marginTop: 6, fontWeight: 600 }}>{g.away} @ {g.home}</div>
              {g.edge && (
                <div title="Aggregated model edge" style={{ marginTop: 6, fontSize: 12, color: g.edge > 0 ? '#065f46' : '#b91c1c' }}>
                  Edge: {g.edge.toFixed(1)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
